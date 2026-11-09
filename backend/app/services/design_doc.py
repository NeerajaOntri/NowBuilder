"""A plan as a technical design document (Word), the way a ServiceNow team hands a build over: one
section per component with its identification, settings, logic, checks, deployment evidence and how
to test it. Everything comes from the plan as built and deployed - nothing is invented here."""
from __future__ import annotations

import io
import json
from datetime import UTC, datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from ..ai.artifacts import spec
from . import application as apps

ACCENT = RGBColor(0x1F, 0x4E, 0x8C)
SKIP_FIELDS = {"script"}


def _table(doc: Document, rows: list[tuple[str, str]], header: tuple[str, str] = ("Field", "Value")) -> None:
    rows = [(k, v) for k, v in rows if str(v or "").strip()]
    if not rows:
        return
    t = doc.add_table(rows=1, cols=2)
    t.style = "Light Grid Accent 1"
    t.rows[0].cells[0].text, t.rows[0].cells[1].text = header
    for k, v in rows:
        cells = t.add_row().cells
        cells[0].text, cells[1].text = str(k), str(v)
    doc.add_paragraph()


def _code(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text.rstrip())
    run.font.name = "Consolas"
    run.font.size = Pt(8.5)


def _value(v) -> str:
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def _flow(doc: Document, generated: dict) -> None:
    steps = generated.get("steps") or []
    if not steps:
        return
    doc.add_heading("Flow steps", level=3)
    for s in steps:
        indent = "    " if s.get("inside") else ""
        line = f"{indent}{s.get('step')}. {s.get('name')} ({s.get('kind')})"
        extra = [f"condition: {s['condition']}" if s.get("condition") else "",
                 f"duration: {_value(s['duration'])}" if s.get("duration") else "",
                 f"inside step {s['inside']}" if s.get("inside") else ""]
        extra = " · ".join(e for e in extra if e)
        p = doc.add_paragraph(line + (f"  [{extra}]" if extra else ""), style="List Number" if not indent else None)
        if s.get("detail"):
            doc.add_paragraph(indent + "   " + str(s["detail"]))
        if s.get("inputs"):
            _table(doc, [(k, _value(v)) for k, v in s["inputs"].items()], ("Input", "Value"))


def _component(doc: Document, n: int, c: dict) -> None:
    sp = spec(c["type"])
    doc.add_heading(f"{n}. {c.get('name')}", level=2)
    gen = c.get("generated") or {}
    record = gen.get("record") or {}
    deploy = c.get("deploy") or {}
    _table(doc, [
        ("Component type", sp.label),
        ("Table", c.get("table") or record.get(sp.table_field or "") or ""),
        ("Action", "Change existing" if c.get("action") == "update" else "New"),
        ("Purpose", c.get("purpose") or ""),
        ("Depends on", ", ".join(c.get("dependsOn") or [])),
        ("Deployment", deploy.get("status") or "not deployed"),
        ("Record", deploy.get("url") or ""),
        ("Application", deploy.get("application") or ""),
        ("Note", deploy.get("application_note") or deploy.get("message") or ""),
    ])
    if record:
        doc.add_heading("Settings", level=3)
        _table(doc, [(k, _value(v)) for k, v in record.items() if k not in SKIP_FIELDS])
    for key in list(sp.children) + list(sp.extras):
        items = gen.get(key)
        if isinstance(items, list) and items and key != "steps":
            doc.add_heading(key.replace("_", " ").capitalize(), level=3)
            for item in items:
                _table(doc, [(k, _value(v)) for k, v in (item or {}).items()])
    if c["type"] == "flow":
        _flow(doc, gen)
    if gen.get("script"):
        doc.add_heading("Script", level=3)
        _code(doc, str(gen["script"]))
    problems = c.get("problems") or []
    if problems:
        doc.add_heading("Checks", level=3)
        for p in problems:
            doc.add_paragraph(f"{p.get('severity', '').capitalize()}: {p.get('message')}", style="List Bullet")


def build(plan: dict, instance_url: str = "") -> bytes:
    doc = Document()
    styles = doc.styles
    styles["Normal"].font.name = "Calibri"
    styles["Normal"].font.size = Pt(10)
    title = doc.add_heading(plan.get("title") or "Technical design", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in title.runs:
        run.font.color.rgb = ACCENT
    deployment = plan.get("deployment") or {}
    update_set = deployment.get("update_set") or {}
    doc.add_heading("1. Overview", level=1)
    _table(doc, [
        ("Summary", plan.get("summary") or ""),
        ("Application / scope", apps.label(plan.get("application") or "global")),
        ("Instance", instance_url),
        ("Status", plan.get("status") or ""),
        ("Story points", str(plan.get("story_points") or "")),
        ("Update set", update_set.get("name") or ""),
        ("Components", str(len(plan.get("components") or []))),
        ("Generated", datetime.now(UTC).strftime("%d %b %Y %H:%M UTC") + " by nowBuilder"),
    ])
    if plan.get("assumptions"):
        doc.add_heading("2. Assumptions and decisions", level=1)
        for a in plan["assumptions"]:
            doc.add_paragraph(str(a), style="List Bullet")
    doc.add_heading("3. Components", level=1)
    for n, c in enumerate(plan.get("components") or [], 1):
        _component(doc, n, c)
    doc.add_heading("4. Deployment", level=1)
    if deployment:
        _table(doc, [("Status", deployment.get("status") or ""), ("Update set", update_set.get("name") or ""),
                     ("Records written", str(len(deployment.get("records") or []))),
                     ("Message", deployment.get("message") or "")])
    else:
        doc.add_paragraph("Not deployed yet: select the rows on the plan card, click Approve, then Deploy.")
    doc.add_heading("5. Testing", level=1)
    tests = [c for c in plan.get("components") or [] if str(c.get("test") or "").strip()]
    if tests:
        for c in tests:
            doc.add_heading(str(c.get("name")), level=3)
            for line in str(c["test"]).splitlines():
                if line.strip():
                    doc.add_paragraph(line.strip())
    else:
        doc.add_paragraph("Test each component against its purpose above: create or update a record that meets "
                          "the condition, confirm the result on the record, in System Logs → Emails or in the "
                          "flow's execution details, and confirm nothing happens when the condition isn't met.")
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

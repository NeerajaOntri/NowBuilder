"""Chunk 3: Fix with AI.

A row the checks complained about is sent back to the model with its problems. The model returns
a corrected record and script; nowBuilder re-checks the result and keeps it as a **proposal**
until the user applies it, so nothing changes under them. Applying swaps the row over; rejecting
puts back exactly what was there.

The model sees the problems nowBuilder found, not just the script, so a fix answers the actual
complaint. If it can't fix something without knowing more, it asks a question instead of guessing.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from ..models import FixProposal, Plan
from ..services.servicenow import ServiceNowClient
from . import checks, usage
from .artifacts import label, spec
from .llm import LLM
from .skills import Skills
from .tasks import TaskError, run_json_task
from .tools import ToolRunner

MAX_ROWS_PER_FIX = 6


def fix_schema(types: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "One or two sentences: what you changed and why"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "question": {"type": "string",
                         "description": "Ask only when you cannot fix this without the user deciding something. "
                                        "Leave it empty otherwise."},
            "changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "The row id you are fixing"},
                        "reason": {"type": "string", "description": "Which problem this change answers"},
                        "record": {"type": "object", "description": "The complete record after the fix"},
                        "script": {"type": "string", "description": "The complete script after the fix; empty for a UI policy"},
                        "actions": {"type": "array", "items": {"type": "object"},
                                    "description": "A UI policy's field actions after the fix"},
                    },
                    "required": ["id", "reason", "record"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["summary", "confidence", "changes"],
    }


SYSTEM = """You are fixing ServiceNow artifacts that nowBuilder's checks rejected.

For each row you are given: what it is, its record, its script, and the exact problems found.
Fix every problem listed. Return the **complete** record and script after the fix, not a patch,
and change nothing the problems didn't ask you to change.

- A problem that says a field or table isn't in the instance means exactly that: read the real
  schema with get_table_schema and use a field that exists, or drop that part of the logic. Never
  keep a name the instance doesn't have.
- A problem about ES6 means rewrite in ES5: var, function, string joining with +.
- If a fix needs a decision only the user can make (which field to use, whether to change
  behaviour), set `question` and leave `changes` empty rather than guessing.
- Keep the record's name unless the problem is about the name."""


@dataclass
class FixResult:
    proposal: FixProposal | None
    message: str


def _rows_for(plan: Plan, ids: list[str]) -> list[dict]:
    return [c for c in plan.components if c["id"] in ids]


def _row_block(c: dict) -> str:
    data = c.get("generated") or {}
    sp = spec(c["type"])
    parts = [f'<row id="{c["id"]}" type="{c["type"]}" what="{sp.label}">',
             "Record:", json.dumps(data.get("record") or {}, indent=2)]
    if sp.has_script:
        parts += ["Script:", data.get("script") or "(empty)"]
    if data.get("actions"):
        parts += ["Field actions:", json.dumps(data["actions"], indent=2)]
    problems = c.get("problems") or []
    parts.append("Problems nowBuilder found:")
    parts += [f'- [{p["severity"]}] {p["message"]}' + (f' ({p["location"]})' if p.get("location") else "")
              for p in problems] or ["- (none; the row failed to generate)"]
    if c.get("error"):
        parts.append(f'- The row could not be generated: {c["error"]}')
    parts.append("</row>")
    return "\n".join(parts)


def propose(db, llm: LLM, skills: Skills, plan: Plan, ids: list[str], client: ServiceNowClient | None,
            instance_summary: str | None, on_status=lambda s: None) -> FixResult:
    """Ask the model to fix the given rows. Saves a pending FixProposal; nothing is applied yet."""
    rows = _rows_for(plan, ids[:MAX_ROWS_PER_FIX])
    if not rows:
        return FixResult(None, "Those rows aren't in this plan any more.")
    types = sorted({c["type"] for c in rows})
    prompt = skills.build_prompt("fix", artifact_types=types,
                                 text=" ".join(p["message"] for c in rows for p in c.get("problems") or []))
    schema = fix_schema(types)
    attempt = 1 + db.query(FixProposal).filter(FixProposal.plan_id == plan.id,
                                               FixProposal.target_id == rows[0]["id"]).count()
    context = "\n".join([
        f"# This plan\nTitle: {plan.title}\nSummary: {plan.summary}",
        f"Connected instance: {instance_summary or 'none'}",
        "Other rows in the plan: " + ", ".join(f'{c["id"]} ({label(c["type"])}) {c["name"]}'
                                               for c in plan.components if c["id"] not in ids) or "none",
    ])
    # Rows these depend on, or that depend on these: their real scripts, so a fix keeps both sides of a
    # contract (GlideAjax method and parameter names, event names, class names) in step.
    fixing = {c["id"] for c in rows}
    related = [c for c in plan.components if c["id"] not in fixing and str((c.get("generated") or {}).get("script") or "").strip()
               and (c["id"] in {d for r in rows for d in r.get("dependsOn") or []}
                    or fixing & set(c.get("dependsOn") or []))]
    if related:
        context += "\n\nRelated rows - keep the fix consistent with their scripts:\n" + "\n".join(
            f'{c["id"]} ({label(c["type"])}) {c["name"]}:\n```javascript\n{str(c["generated"]["script"])[:6000]}\n```'
            for c in related)
    user = "\n\n".join([SYSTEM, *[_row_block(c) for c in rows],
                        "Reply with one JSON object only, matching the schema you were given."])
    try:
        types = {c["id"]: c["type"] for c in rows}
        data = run_json_task(
            usage.tag(llm, "fix", plan.id),
            prompt.system + "\n\n# The JSON to reply with\n\n```json\n" + json.dumps(schema) + "\n```",
            context, user, prompt.tools, ToolRunner(skills, client), schema,
            on_status=on_status, extra_check=lambda d: _sanity(d, types),
        )
    except TaskError as e:
        return FixResult(None, str(e))

    changes = [c for c in data.get("changes") or [] if c.get("id") in ids]
    question = (data.get("question") or "").strip()
    status = "needs_user_input" if question and not changes else "pending"
    if not changes and not question:
        return FixResult(None, "The AI didn't suggest a change for those rows.")

    originals = {c["id"]: json.dumps(c.get("generated") or {}, indent=2, sort_keys=True) for c in rows}
    proposal = FixProposal(
        plan_id=plan.id, target_id=rows[0]["id"], group_ids=[c["id"] for c in rows],
        prior_statuses={c["id"]: c.get("status", "ready") for c in rows},
        status=status, summary=data.get("summary", ""), confidence=data.get("confidence"),
        question=question or None, changes=changes, original_files=originals,
        violations=[p for c in rows for p in (c.get("problems") or [])], attempt=attempt,
    )
    db.add(proposal)
    for c in rows:
        c["fix_status"] = status
    _touch(db, plan)
    return FixResult(proposal, "")


def _sanity(data: dict, types: dict[str, str]) -> list[str]:
    """A fix is held to the same rules as anything else: it can't trade one problem for another."""
    out = []
    for ch in data.get("changes") or []:
        cid = ch.get("id")
        if cid not in types:
            out.append(f'Row {cid} isn\'t one of the rows you were asked to fix ({", ".join(types)}).')
            continue
        if not isinstance(ch.get("record"), dict) or not ch["record"]:
            out.append(f"Row {cid} needs the complete record, not an empty object.")
            continue
        out += [f"Row {cid}: {m}" for m in checks.generation_problems(types[cid], ch)]
    return out


def apply(db, plan: Plan, proposal: FixProposal, client: ServiceNowClient | None) -> dict:
    """Swap the fixed record and script into the plan, then check the rows again."""
    if proposal.status not in ("pending", "needs_user_input"):
        raise ValueError("That fix has already been dealt with.")
    by_id = {c["id"]: c for c in plan.components}
    changed: list[str] = []
    for ch in proposal.changes:
        c = by_id.get(ch["id"])
        if c is None:
            continue
        data = dict(c.get("generated") or {})
        data["record"] = ch["record"]
        if spec(c["type"]).has_script and ch.get("script") is not None:
            data["script"] = ch["script"]
        if ch.get("actions"):
            data["actions"] = ch["actions"]
        c["generated"] = data
        c["status"] = "ready"
        c["error"] = None
        c["fix_status"] = "applied"
        changed.append(c["id"])
    proposal.status = "applied"
    plan.validation = {**checks.run(plan.components, client, only=changed, application=plan.application), "at": _now()}
    _touch(db, plan)
    return {"applied": changed}


def reject(db, plan: Plan, proposal: FixProposal) -> dict:
    """Put the rows back exactly as they were."""
    if proposal.status not in ("pending", "needs_user_input"):
        raise ValueError("That fix has already been dealt with.")
    by_id = {c["id"]: c for c in plan.components}
    for cid, status in (proposal.prior_statuses or {}).items():
        if (c := by_id.get(cid)) is not None:
            c["status"] = status
            c["fix_status"] = "rejected"
    proposal.status = "rejected"
    _touch(db, plan)
    return {"rejected": list(proposal.prior_statuses or {})}


def edit(db, plan: Plan, component_id: str, script: str | None, record: dict | None,
         client: ServiceNowClient | None) -> dict:
    """A person editing a row by hand. Checked the same way as anything the AI wrote."""
    c = next((x for x in plan.components if x["id"] == component_id), None)
    if c is None:
        raise ValueError("That row isn't in this plan.")
    data = dict(c.get("generated") or {})
    if not data:
        raise ValueError("That row hasn't been written yet, so there's nothing to edit.")
    if script is not None:
        if not spec(c["type"]).has_script:
            raise ValueError(f"A {label(c['type']).lower()} doesn't have a script.")
        data["script"] = script
    if record is not None:
        data["record"] = {**data.get("record", {}), **record}
    c["generated"] = data
    c["status"] = "ready"
    c["edited"] = True
    plan.validation = {**checks.run(plan.components, client, only=[component_id], application=plan.application),
                       "at": _now()}
    _touch(db, plan)
    return proposal_out_component(c)


def proposal_out_component(c: dict) -> dict:
    return c


def proposal_out(p: FixProposal) -> dict:
    return {"id": p.id, "plan_id": p.plan_id, "target_id": p.target_id, "group_ids": p.group_ids,
            "status": p.status, "summary": p.summary, "confidence": p.confidence, "question": p.question,
            "changes": p.changes, "original": p.original_files, "attempt": p.attempt,
            "created_at": p.created_at.isoformat()}


def save(db, plan: Plan) -> None:
    """Commit changes made inside a plan's `components` list (SQLAlchemy can't see them itself)."""
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(plan, "components")
    db.commit()


_touch = save   # the name used inside this module


def _now() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()

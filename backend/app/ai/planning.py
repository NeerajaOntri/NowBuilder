"""Chunk 2: plans.

The chat proposes a plan by calling the `propose_plan` tool: one row per artifact (business rule,
script include, client script, UI policy, UI action). The rows stream into the card as the model
writes them, then nowBuilder generates each artifact's record and script in dependency order.

When the connected instance allows it (`services/auto_deploy.py`: not Production, the member may
deploy, the instance's auto-deploy setting is on), the finished plan is deployed straight away, the
way Now Assist delivers: Table API artifacts into a new update set, flows with the ServiceNow SDK.
Otherwise the plan waits on the card for Approve and Deploy.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime

from ..models import Plan
from ..services.servicenow import ServiceNowClient
from . import checks, usage
from .artifacts import SPECS, TYPES, label, spec
from .llm import LLM, LLMError
from .skills import Skills
from .tasks import TaskError, run_json_task
from .tools import ToolRunner

log = logging.getLogger("nowbuilder.planning")

MAX_COMPONENTS = 12

PROPOSAL_SCHEMA = {
    "name": "propose_plan",
    "description": (
        "Propose an implementation plan: one row per ServiceNow artifact you will build or change. "
        "THIS IS HOW A BUILD OR CHANGE REQUEST IS ANSWERED. Call it once you know what to build, instead "
        "of writing the records, scripts or step-by-step instructions in your reply: nowBuilder then "
        "generates each record and script, checks them against the connected instance, and shows the user "
        "a plan card with Approve and Deploy. Read the instance first (table fields, artifacts already on "
        "the table). Include flows too: they are deployed with the ServiceNow SDK when the backend has an SDK "
        "project, otherwise the card marks them 'Build by hand'. When the instance allows automatic "
        "deployment, the plan is deployed into it as soon as it passes the checks and the tool result says "
        "exactly what went in. Use it for build and change requests only, never for questions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short name for the whole piece of work", "maxLength": 120},
            "application": {"type": "string", "maxLength": 80,
                            "description": ("The application scope every artifact in this plan is built in: 'global', or the "
                                            "scope name (x_…/sn_…) of an application on the instance. Take it from what "
                                            "the user or the document says (an 'Application' or 'Scope' field); template "
                                            "blanks in [brackets] don't count. 'global' when nothing says otherwise.")},
            "summary": {"type": "string", "description": "2-3 sentences: what this does and why it is built this way. The card already lists every row and its settings, so don't restate them here"},
            "story_points": {"type": "integer", "minimum": 1, "maximum": 21,
                             "description": "Fibonacci estimate for the whole plan: 1, 2, 3, 5, 8, 13 or 21"},
            "assumptions": {"type": "array", "maxItems": 8, "items": {"type": "string"},
                            "description": "What you assumed because the request or the instance didn't say"},
            "components": {
                "type": "array", "minItems": 1, "maxItems": MAX_COMPONENTS,
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Short id used by dependsOn, e.g. c1", "maxLength": 12},
                        "type": {"type": "string", "enum": list(TYPES)},
                        "name": {"type": "string", "description": "What this artifact is called, in words", "maxLength": 120},
                        "table": {"type": "string", "description": "Table it runs on; empty for a script include"},
                        "action": {"type": "string", "enum": ["create", "update"],
                                   "description": "update only when changing an artifact that already exists"},
                        "sys_id": {"type": "string", "description": "The existing artifact's sys_id when action is update"},
                        "purpose": {"type": "string", "description": "One line: why this artifact is in the plan", "maxLength": 300},
                        "test": {"type": "string", "maxLength": 600,
                                 "description": ("How to test this row once deployed, as short numbered steps with the "
                                                 "expected result (the design document's test section).")},
                        "dependsOn": {"type": "array", "items": {"type": "string"},
                                      "description": "ids of components this one needs (a rule that calls a script include)"},
                    },
                    "required": ["id", "type", "name", "purpose"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["title", "summary", "story_points", "components"],
    },
}


# ---------- the proposal the model sent ----------

def clean_proposal(raw: dict) -> dict:
    """Tidy what the model proposed: drop unknown types, give every row an id, keep dependsOn real."""
    components: list[dict] = []
    seen: set[str] = set()
    for i, c in enumerate(raw.get("components") or [], 1):
        if not isinstance(c, dict) or c.get("type") not in SPECS:
            continue
        cid = str(c.get("id") or f"c{i}").strip()[:12] or f"c{i}"
        while cid in seen:
            cid += "_"
        seen.add(cid)
        action = "update" if c.get("action") == "update" and c.get("sys_id") else "create"
        components.append({
            "id": cid, "type": c["type"], "name": str(c.get("name") or label(c["type"]))[:120],
            "table": str(c.get("table") or "").strip(), "action": action,
            "sys_id": str(c.get("sys_id") or "").strip() if action == "update" else "",
            "purpose": str(c.get("purpose") or "")[:300],
            "test": str(c.get("test") or "")[:600],
            "dependsOn": [str(d) for d in (c.get("dependsOn") or []) if isinstance(d, str)],
            "status": "planned",
        })
    ids = {c["id"] for c in components}
    for c in components:
        c["dependsOn"] = [d for d in c["dependsOn"] if d in ids and d != c["id"]]
    points = raw.get("story_points")
    return {
        "title": str(raw.get("title") or "Implementation plan")[:160],
        "application": _application(raw.get("application")),
        "summary": str(raw.get("summary") or "").strip(),
        "story_points": points if isinstance(points, int) and 1 <= points <= 21 else 0,
        "assumptions": [str(a) for a in (raw.get("assumptions") or []) if isinstance(a, str)][:8],
        "components": components[:MAX_COMPONENTS],
    }


def _application(value) -> str:
    from ..services.application import normalize
    return normalize(value)


def draft_from_snapshot(snapshot: dict) -> dict | None:
    """A partial proposal from a half-streamed tool input, for the live card. None if too early."""
    if not isinstance(snapshot, dict):
        return None
    rows = [c for c in (snapshot.get("components") or []) if isinstance(c, dict) and c.get("type") in SPECS]
    if not snapshot.get("title") and not rows:
        return None
    return {
        "title": str(snapshot.get("title") or "")[:160],
        "summary": str(snapshot.get("summary") or ""),
        "story_points": snapshot.get("story_points") if isinstance(snapshot.get("story_points"), int) else 0,
        "assumptions": [str(a) for a in (snapshot.get("assumptions") or []) if isinstance(a, str)],
        "components": [{"id": str(c.get("id") or f"c{i}"), "type": c["type"], "name": str(c.get("name") or ""),
                        "table": str(c.get("table") or ""), "action": c.get("action") or "create",
                        "purpose": str(c.get("purpose") or ""), "status": "planned"}
                       for i, c in enumerate(rows, 1)],
        "drafting": True,
    }


# ---------- storage ----------

def plan_out(plan: Plan) -> dict:
    return {
        "id": plan.id, "chat_id": plan.chat_id, "instance_id": plan.instance_id, "version": plan.version,
        "title": plan.title, "summary": plan.summary, "story_points": plan.story_points,
        "assumptions": plan.assumptions or [], "components": plan.components or [],
        "application": plan.application or "global",
        "status": plan.status, "busy": plan.busy, "progress": plan.progress,
        "validation": plan.validation, "approval": plan.approval, "deployment": plan.deployment, "git": plan.git,
        "created_at": plan.created_at.isoformat(),
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def component_out(c: dict) -> dict:
    """One row for the card: everything except the generated record's internals is already small."""
    return c


# ---------- generating one artifact ----------

def _context(instance_summary: str | None, plan: dict, component: dict) -> str:
    others = [f'- {c["id"]} ({label(c["type"])}): {c["name"]}' for c in plan["components"] if c["id"] != component["id"]]
    lines = [
        "# This plan",
        f'Title: {plan["title"]}',
        f'Summary: {plan["summary"]}',
        f"Connected instance: {instance_summary or 'none'}",
    ]
    if others:
        lines += ["Other artifacts in the same plan (already named, don't duplicate them):", *others]
    done = [c for c in plan["components"] if c.get("status") == "ready" and c["id"] in (component.get("dependsOn") or [])]
    for d in done:
        name = (d.get("generated") or {}).get("record", {}).get(spec(d["type"]).name_field, d["name"])
        lines.append(f'This artifact depends on {d["id"]}, which was generated as "{name}". Call it by that exact name.')
        script = str((d.get("generated") or {}).get("script") or "")
        if script.strip():
            # The real interface - method names, parameter names, return values - not just the name: a client
            # script must send exactly what the script include reads.
            lines += [f'Its script, which this artifact must match exactly (method names, sysparm_ parameter names, '
                      f'what it returns):', "```javascript", script[:6000], "```"]
    return "\n".join(lines)


def _user_content(component: dict, requirement: str) -> str:
    sp = spec(component["type"])
    parts = [
        f'Build this one artifact of the plan.',
        f'Type: {sp.label} ({sp.table})',
        f'Name it describes: {component["name"]}',
        f'Purpose: {component["purpose"]}',
    ]
    if component.get("table"):
        parts.append(f'Table: {component["table"]}')
    if component["action"] == "update" and component.get("sys_id"):
        parts.append(f'This changes the existing artifact {component["sys_id"]}: read it first with get_instance_artifact '
                     f'and return the complete record and script as they should be after the change.')
    if requirement:
        parts.append(f"\nWhat the user asked for:\n{requirement[:4000]}")
    parts.append("\nReply with one JSON object only, matching the schema you were given.")
    return "\n".join(parts)


class PlanBuilder:
    """Turns a proposal into a saved plan with generated records and scripts, yielding events."""

    def __init__(self, llm: LLM, skills: Skills, runner: ToolRunner, db, chat_id: str, instance_id: str | None,
                 instance_summary: str | None, requirement: str = "", client: ServiceNowClient | None = None,
                 deployer=None, no_deploy_reason: str = ""):
        self.llm, self.skills, self.runner, self.db = llm, skills, runner, db
        self.chat_id, self.instance_id, self.instance_summary = chat_id, instance_id, instance_summary
        self.requirement, self.client = requirement, client
        # services.auto_deploy.AutoDeployer when this chat may deploy straight into the instance
        self.deployer, self.no_deploy_reason = deployer, no_deploy_reason
        self.plan_id: str | None = None
        self.tool_result: str = ""

    # ----- the propose_plan tool call -----
    def build(self, raw: dict) -> Iterator[dict]:
        proposal = clean_proposal(raw)
        if not proposal["components"]:
            self.tool_result = ("No usable artifacts were in that plan. Tell the user what you need to know, "
                                "or answer without a plan.")
            yield {"type": "error", "message": "The plan had no artifacts nowBuilder can build."}
            return

        plan = self._create(proposal)
        self.plan_id = plan.id
        yield {"type": "plan", "plan": plan_out(plan)}

        components = plan.components
        try:
            order = Skills.deploy_order(components)
        except ValueError as e:  # a cycle: build in the order proposed
            log.info("Plan %s: %s", plan.id, e)
            order = list(components)

        built = 0
        for component in order:
            yield {"type": "status", "text": f'Writing the {label(component["type"]).lower()}: {component["name"]}'}
            self._set(plan, component, "generating")
            yield {"type": "component", "plan_id": plan.id, "component": component_out(component)}
            try:
                data = self._generate(plan, component)
                component["generated"] = data
                component["name"] = _best_name(component, data)
                if component["type"] == "flow":
                    # Whether the SDK can express this design, so the card can offer the source
                    # instead of making the user find out by trying.
                    from .flow_sdk import export_report
                    component["export"] = export_report(data)
                self._set(plan, component, "ready")
                built += 1
            except (TaskError, LLMError, ValueError) as e:
                component["error"] = str(e)
                self._set(plan, component, "failed")
                log.info("Plan %s component %s failed: %s", plan.id, component["id"], e)
            yield {"type": "component", "plan_id": plan.id, "component": component_out(component)}

        yield {"type": "status", "text": "Checking the scripts against the instance"}
        plan.validation = {**checks.run(plan.components, self.client, application=plan.application), "at": _now_iso()}
        plan.busy = None
        plan.busy_since = None
        plan.progress = None
        self._save(plan)
        self.tool_result = self._summary(plan, built)
        yield {"type": "plan_done", "plan": plan_out(plan)}
        if self.deployer is not None and built:
            yield from self._deploy(plan)

    # ----- deploying (automatically, or when the user asks in the chat) -----
    def _deploy(self, plan: Plan) -> Iterator[dict]:
        from ..services.auto_deploy import note
        plan.busy, plan.busy_since, plan.progress = "deploying", datetime.now(UTC), "Deploying into the instance"
        self._save(plan)
        try:
            yield from self.deployer.run(plan)
        finally:
            plan.busy = plan.busy_since = plan.progress = None
            self._save(plan)
        self.tool_result = note(self.deployer.result)

    def deploy_existing(self, plan_id: str | None) -> Iterator[dict]:
        """The `deploy_plan` tool: deploy a plan of this chat that is already on screen."""
        from sqlalchemy import select
        q = select(Plan).where(Plan.chat_id == self.chat_id)
        plan = self.db.get(Plan, plan_id) if plan_id else self.db.scalars(q.order_by(Plan.created_at.desc())).first()
        if plan is None or plan.chat_id != self.chat_id:
            self.tool_result = "There is no plan in this chat to deploy. Propose one first."
            return
        if self.deployer is None:
            self.tool_result = json.dumps({"deployed": False, "reason": self.no_deploy_reason or
                                           "Deploying from the chat isn't allowed here; use the plan card."})
            return
        self.plan_id = plan.id
        yield {"type": "status", "text": f"Deploying {plan.title}"}
        yield from self._deploy(plan)

    # ----- pieces -----
    def _create(self, proposal: dict) -> Plan:
        plan = Plan(chat_id=self.chat_id, instance_id=self.instance_id, title=proposal["title"],
                    summary=proposal["summary"], story_points=proposal["story_points"],
                    assumptions=proposal["assumptions"], components=proposal["components"],
                    application=proposal.get("application") or "global",
                    status="draft", busy="building", busy_since=datetime.now(UTC),
                    progress="Writing the artifacts")
        self.db.add(plan)
        self.db.commit()
        return plan

    def _set(self, plan: Plan, component: dict, status: str) -> None:
        component["status"] = status
        if status == "generating":
            plan.progress = f'Writing {component["name"]}'
        self._save(plan)

    def _save(self, plan: Plan) -> None:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(plan, "components")
        self.db.commit()

    def _generate(self, plan: Plan, component: dict) -> dict:
        sp = spec(component["type"])
        prompt = self.skills.build_prompt("generate", artifact_types=[component["type"]], text=component["purpose"])
        schema = sp.schema()
        llm = usage.tag(self.llm, "generate", plan.id)
        data = run_json_task(
            llm, prompt.system + "\n\n# The JSON to reply with\n\n```json\n" + json.dumps(schema) + "\n```",
            _context(self.instance_summary, plan_out(plan), component),
            _user_content(component, self.requirement),
            prompt.tools, self.runner, schema,
            extra_check=lambda d: checks.generation_problems(component["type"], d),
        )
        if component.get("table") and sp.table_field:
            data["record"].setdefault(sp.table_field, component["table"])
        return data

    def _summary(self, plan: Plan, built: int) -> str:
        rows = [{"id": c["id"], "type": c["type"], "name": c["name"], "status": c["status"],
                 "problems": len(c.get("problems") or []),
                 **({"error": c["error"]} if c.get("error") else {})}
                for c in plan.components]
        v = plan.validation or {}
        note = ("The user can see every record, script and check result in the plan card, so don't repeat them. "
                "Write two or three sentences: what the plan does, anything they should check or decide, and that "
                "they can approve it and deploy it into an update set from the card.")
        if self.no_deploy_reason:
            note += f" It was not deployed automatically: {self.no_deploy_reason}"
        if built < len(plan.components):
            note += " Say which artifacts couldn't be written and why."
        if v.get("errors"):
            note += " Some rows have problems the checks found; tell them they can use Fix with AI on those rows."
        from ..services.application import label as app_label
        note += (f" Every artifact, flows included, is built in the {app_label(plan.application or 'global')} "
                 "application; don't say otherwise.")
        return json.dumps({"plan_id": plan.id, "built": built, "application": app_label(plan.application or "global"),
                           "components": rows,
                           "checks": {"errors": v.get("errors", 0), "warnings": v.get("warnings", 0)}, "note": note})


def _best_name(component: dict, data: dict) -> str:
    rec = data.get("record") or {}
    return str(rec.get(spec(component["type"]).name_field) or component["name"])[:120]

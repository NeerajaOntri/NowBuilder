"""Now Assist-style delivery: a plan that has been written and checked goes straight into the
connected instance, without the user having to press Approve and Deploy.

Order of work, for one plan:

1. **Fix once.** Rows the checks rejected get one Fix with AI pass; the fix is applied only if it
   clears the problems (the checks run again), never on a guess.
2. **Table API artifacts** (business rules, script includes, client scripts, UI policies, UI actions,
   notifications) that pass the checks are approved and deployed into a new update set, exactly as
   the Deploy button does it: update set made current, each record written and read back, the
   user's previous update set restored (services/deploy.py).
3. **Flows** are installed with the ServiceNow SDK into the configured scoped application
   (services/sdk_deploy.py), after the rows they point at (`{{plan.<id>}}`) are deployed, then read
   back from sys_hub_flow. Without an SDK project on the backend a flow stays a design and the
   reply says so.

Guard rails: never on a Production instance, only for members allowed to deploy, and only when the
instance's `auto_deploy` setting is on. Rows with errors are never deployed. Every result reported
to the model and the user comes from what the instance returned.
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy.orm.attributes import flag_modified

from ..ai import checks, fixing
from ..ai.artifacts import label, spec
from ..ai.planning import plan_out
from ..models import Instance, Plan
from ..security import decrypt
from . import deploy as deploy_svc
from . import sdk_deploy
from .servicenow import ServiceNowClient, ServiceNowError

log = logging.getLogger("nowbuilder.auto_deploy")


def update_set_name(plan: Plan) -> str:
    title = re.sub(r"\s+", " ", plan.title or "nowBuilder change").strip()
    return f"nowBuilder - {title}"[:80]


def allowed(instance: Instance | None, can_deploy: bool) -> tuple[bool, str]:
    """Whether a plan may deploy itself into this instance, and why not. Off unless
    NOWBUILDER_AUTO_DEPLOY=true: plans normally wait for Approve and Deploy on the card."""
    from ..config import get_settings
    if not get_settings().auto_deploy:
        return False, ("Plans deploy when the user clicks Deploy on the plan card: they choose the rows, "
                       "Approve, then Deploy.")
    if instance is None:
        return False, "No ServiceNow instance is connected."
    if instance.instance_type == "Production":
        return False, f"{instance.name} is a production instance: deploy from the plan card after review."
    if not getattr(instance, "auto_deploy", True):
        return False, f"Automatic deployment is off for {instance.name}: deploy from the plan card."
    if not can_deploy:
        return False, "Your role in this workspace can't deploy; a workspace admin can deploy from the plan card."
    return True, ""


class AutoDeployer:
    def __init__(self, db, client: ServiceNowClient, instance: Instance, user_id: str,
                 llm=None, skills=None, instance_summary: str | None = None):
        self.db, self.client, self.instance, self.user_id = db, client, instance, user_id
        self.llm, self.skills, self.instance_summary = llm, skills, instance_summary
        self.result: dict = {}

    # ----- one plan -----
    def run(self, plan: Plan) -> Iterator[dict]:
        yield from self._fix_once(plan)
        ready = [c for c in plan.components if not checks.blocking(c)
                 and (c.get("deploy") or {}).get("status") != "deployed"]
        if not sdk_deploy.configured():
            for c in [c for c in ready if c["type"] == "flow"]:
                c["deploy"] = {"status": "design only", "message": sdk_deploy.why_not_configured()}
                ready.remove(c)
        held = [c for c in plan.components if checks.blocking(c)]
        table_result: dict | None = None
        if ready:
            yield {"type": "status", "text": f"Deploying {len(ready)} artifact(s) into {self.instance.name}"}
            try:
                deploy_svc.approve(self.db, plan, [c["id"] for c in ready], self.user_id)
                plan.approval = {**(plan.approval or {}), "auto": True}
                yield from run_streaming(lambda on_status: deploy_svc.deploy(
                    self.db, plan, self.client, self.instance, update_set_name(plan), self.user_id, on_status=on_status))
                table_result = plan.deployment
            except (deploy_svc.DeployError, ServiceNowError) as e:
                table_result = {"status": "failed", "message": str(e)}
                log.info("Auto-deploy of plan %s failed: %s", plan.id, e)
        flag_modified(plan, "components")
        self.db.commit()
        yield {"type": "plan", "plan": plan_out(plan)}
        self.result = self._summary(plan, table_result, [], held)

    def _fix_once(self, plan: Plan) -> Iterator[dict]:
        broken = [c["id"] for c in plan.components
                  if c.get("status") == "ready" and any(p["severity"] == checks.ERROR for p in c.get("problems") or [])]
        if not broken or self.llm is None or self.skills is None:
            return
        yield {"type": "status", "text": f"Fixing {len(broken)} row(s) the checks rejected"}
        try:
            result = fixing.propose(self.db, self.llm, self.skills, plan, broken[:fixing.MAX_ROWS_PER_FIX],
                                    self.client, self.instance_summary)
            if result.proposal is not None and result.proposal.status == "pending":
                fixing.apply(self.db, plan, result.proposal, self.client)
                yield {"type": "plan", "plan": plan_out(plan)}
        except Exception:  # noqa: BLE001 — a failed fix leaves the rows as they were; they just don't deploy
            log.warning("Automatic fix failed for plan %s", plan.id, exc_info=True)

    def _summary(self, plan: Plan, table_result: dict | None, flow_results: list[dict], held: list[dict]) -> dict:
        rows = []
        for c in plan.components:
            d = c.get("deploy") or {}
            rows.append({"id": c["id"], "type": label(c["type"]), "name": c["name"],
                         "deploy_status": d.get("status") or ("held: has problems" if c in held else "not deployed"),
                         **({"sys_id": d["sys_id"]} if d.get("sys_id") else {}),
                         **({"url": d["url"]} if d.get("url") else {}),
                         **({"active": d["active"]} if "active" in d else {}),
                         **({"message": d["message"]} if d.get("message") else {})})
        dep = plan.deployment or {}
        return {"instance": self.instance.url, "update_set": (dep.get("update_set") or {}),
                "captured_in_update_set": dep.get("captured"),
                "table_api_result": (table_result or {}).get("status") if table_result else "nothing to deploy",
                "message": (table_result or {}).get("message") or dep.get("message") or "",
                "rows": rows}


def run_streaming(work) -> Iterator[dict]:
    """Run `work(on_status)` in a thread and pass its progress on as it happens, so a long step (a
    flow install, the first SDK setup) never leaves the browser waiting in silence. Re-raises errors."""
    import queue
    import threading
    q: queue.Queue = queue.Queue()
    box: dict = {}

    def target() -> None:
        try:
            box["result"] = work(lambda text: q.put(text))
        except BaseException as e:  # noqa: BLE001 — handed back to the caller below
            box["error"] = e
        finally:
            q.put(None)

    threading.Thread(target=target, name="deploy", daemon=True).start()
    while True:
        try:
            item = q.get(timeout=15)
        except queue.Empty:
            yield {"type": "status", "text": "Still working…"}
            continue
        if item is None:
            break
        yield {"type": "status", "text": item}
    if "error" in box:
        raise box["error"]
    return box.get("result")


def note(result: dict) -> str:
    """What the model is told to do with the deployment result."""
    return json.dumps({"deployment": result, "note": (
        "These are the instance's own answers. Report, row by row, what is now live in the instance "
        "(with its link) and what isn't and why. Say which update set holds the Table API artifacts. "
        "Never call something deployed unless deploy_status is 'deployed'. For anything held, failed "
        "or design only, say what the user should do next.")})

"""Chunk 4: approve a plan, deploy it into a named update set, and roll it back.

Everything goes through the Table API as the connected user, so what nowBuilder writes is exactly
what that user could write by hand.

**How the update set capture works.** ServiceNow captures a change into whichever update set is
current *for the user making it*. There is no "put this record in that update set" parameter, so
nowBuilder:

1. creates a `sys_update_set` (state "in progress") in the instance,
2. points the connected user's `sys_update_set` preference at it (`sys_user_preference`),
3. writes the artifacts, which the instance captures into that set,
4. puts the user's previous current update set back, whatever happened.

Step 4 runs in a `finally`, so an interrupted deploy never leaves someone's session pointed at
nowBuilder's update set.

**Rollback** deletes what was created and puts back what was changed, newest first. The `before`
values are read from the instance *before* each update, so a rollback restores what was really
there, not what nowBuilder assumed. Rollback is itself captured in the update set.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..ai import checks
from ..ai.artifacts import label, spec, to_records
from ..ai.skills import Skills
from ..models import Instance, Plan
from .servicenow import ServiceNowClient, ServiceNowError

log = logging.getLogger("nowbuilder.deploy")

UPDATE_SET_TABLE = "sys_update_set"
PREFERENCE_TABLE = "sys_user_preference"
PREFERENCE_NAME = "sys_update_set"

# Update-set preferences are per connected ServiceNow user, not per request.
# Serialize deployments in this process to avoid redirecting concurrent writes.
_deployment_lock = threading.Lock()


class DeployError(Exception):
    """A problem the user can act on."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ---------- approve ----------

def approve(db, plan: Plan, ids: list[str], user_id: str) -> dict:
    """Lock in which rows may be deployed. Rows with errors, or rows nowBuilder can't write,
    can't be approved."""
    by_id = {c["id"]: c for c in plan.components}
    chosen = [i for i in ids if i in by_id]
    if not chosen:
        raise DeployError("Choose at least one artifact to approve.")
    by_hand = [by_id[i]["name"] for i in chosen if not _deployable(by_id[i])]
    if by_hand:
        from . import sdk_deploy
        raise DeployError("nowBuilder can't deploy these here, they're built by hand: " + ", ".join(by_hand) + ". "
                          + sdk_deploy.why_not_configured())
    blocked = [by_id[i]["name"] for i in chosen if checks.blocking(by_id[i])]
    if blocked:
        raise DeployError("These still have problems to fix first: " + ", ".join(blocked) + ".")
    plan.approval = {"at": _now(), "by": user_id, "ids": chosen}
    plan.status = "approved"
    db.commit()
    return plan.approval


def unapprove(db, plan: Plan) -> None:
    plan.approval = None
    plan.status = "deployed" if (plan.deployment or {}).get("status") == "deployed" else "draft"
    db.commit()


# ---------- deploy ----------

@dataclass
class DeployedRecord:
    component_id: str
    table: str
    sys_id: str
    action: str                      # create | update
    before: dict | None = None       # the fields as they were, for a rollback of an update
    children: list[dict] = field(default_factory=list)   # [{table, sys_id}]

    def as_dict(self) -> dict:
        return {"component_id": self.component_id, "table": self.table, "sys_id": self.sys_id,
                "action": self.action, "before": self.before, "children": self.children}


class Deployer:
    def __init__(self, client: ServiceNowClient, instance: Instance):
        self.client, self.instance = client, instance

    # ----- update set plumbing -----
    def create_update_set(self, name: str, description: str, application: str = "") -> dict:
        fields = {"name": name[:80], "description": description[:4000], "state": "in progress"}
        if application:
            fields["application"] = application          # an update set belongs to one application
        rec = self.client.insert(UPDATE_SET_TABLE, fields)
        if not rec.get("sys_id"):
            raise DeployError("The instance didn't return the update set it created.")
        return {"sys_id": rec["sys_id"], "name": rec.get("name") or name,
                "url": f"{self.client.url}/{UPDATE_SET_TABLE}.do?sys_id={rec['sys_id']}"}

    def _preference(self, name: str = PREFERENCE_NAME) -> dict | None:
        user_sys_id = self.instance.user_sys_id
        if not user_sys_id:
            return None
        rows = self.client.query(PREFERENCE_TABLE, f"name={name}^user={user_sys_id}",
                                 ["sys_id", "value"], limit=1)
        return rows[0] if rows else None

    def set_application(self, app_sys_id: str) -> tuple[str | None, str | None]:
        """Make this application the connected user's current one (the application picker), so the
        Table API creates every record in it. Returns (preference sys_id, previous value)."""
        from .application import PREFERENCE_NAME as APP_PREF
        if not self.instance.user_sys_id:
            raise DeployError("nowBuilder doesn't know which user it is signed in as on this instance. "
                              "Test the connection in Settings → ServiceNow instances, then try again.")
        pref = self._preference(APP_PREF)
        if pref:
            if str(pref.get("value") or "") != app_sys_id:
                self.client.update(PREFERENCE_TABLE, pref["sys_id"], {"value": app_sys_id})
            return pref["sys_id"], pref.get("value")
        created = self.client.insert(PREFERENCE_TABLE, {"name": APP_PREF, "user": self.instance.user_sys_id,
                                                        "value": app_sys_id, "type": "string"})
        return created.get("sys_id"), None

    def set_current(self, update_set_sys_id: str) -> tuple[str | None, str | None]:
        """Point the connected user at this update set. Returns (preference sys_id, previous value)."""
        if not self.instance.user_sys_id:
            raise DeployError("nowBuilder doesn't know which user it is signed in as on this instance. "
                              "Test the connection in Settings → ServiceNow instances, then try again.")
        pref = self._preference()
        if pref:
            self.client.update(PREFERENCE_TABLE, pref["sys_id"], {"value": update_set_sys_id})
            return pref["sys_id"], pref.get("value")
        created = self.client.insert(PREFERENCE_TABLE, {"name": PREFERENCE_NAME, "user": self.instance.user_sys_id,
                                                        "value": update_set_sys_id, "type": "string"})
        return created.get("sys_id"), None

    def verify_current(self, update_set_sys_id: str) -> None:
        """Nothing is written until the instance confirms the user's current update set moved.
        The message says what was actually found, because this is the step most likely to fail on
        a real instance and the user has to be able to act on it."""
        pref = self._preference()
        if not pref:
            raise DeployError(
                f"nowBuilder set the current update set for {self.instance.username}, but no "
                f"'{PREFERENCE_NAME}' preference came back for that user. Nothing was written. "
                f"Check that the connected user may read and write sys_user_preference.")
        found = str(pref.get("value") or "")
        if found != str(update_set_sys_id):
            raise DeployError(
                f"The current update set didn't move: the instance still reports "
                f"{found or '(empty)'} for {self.instance.username}, not the set nowBuilder just "
                f"created. Nothing was written. This usually means the connected user can't change "
                f"its own current update set, or another session changed it at the same time.")

    def restore_current(self, pref_sys_id: str | None, previous: str | None) -> None:
        if not pref_sys_id:
            return
        try:
            if previous is None:
                # The preference was created for this deployment; do not leave it behind.
                self.client.delete(PREFERENCE_TABLE, pref_sys_id)
            else:
                self.client.update(PREFERENCE_TABLE, pref_sys_id, {"value": previous})
        except ServiceNowError:
            log.warning("Couldn't put the user's previous update set back", exc_info=True)

    def captured(self, update_set_sys_id: str) -> int:
        """How many updates the instance actually captured (0 means nothing was recorded)."""
        try:
            rows = self.client.query("sys_update_xml", f"update_set={update_set_sys_id}", ["sys_id"], limit=200)
            return len(rows)
        except ServiceNowError:
            return -1   # the user can't read the table; not a reason to fail the deploy

    # ----- writing one artifact -----
    def write(self, component: dict, on_partial=None) -> DeployedRecord:
        type_ = component["type"]
        sp = spec(type_)
        if not sp.deployable:
            raise DeployError(f"{component['name']}: {sp.label} is design-only and cannot be written by this deployment adapter.")
        rows = to_records(type_, component["generated"])
        main = rows[0]
        if sp.aliases:                                       # this instance's column names
            from ..ai.artifacts import apply_aliases
            try:
                schema = self.client.table_schema(sp.table)
            except ServiceNowError:
                schema = {}
            columns = {f["name"].lower() for f in schema.get("fields", [])}
            main["fields"] = apply_aliases(type_, main["fields"], columns)
        for fld, (table, key) in sp.lookups.items():         # names in the design, sys_ids in the instance
            value = str(main["fields"].get(fld) or "").strip()
            if not value:
                continue
            found = self.client.query(table, f"{key}={value}", ["sys_id"], limit=1)
            if not found:
                raise DeployError(f'{component["name"]}: {fld} is {value}, which isn\'t in this instance\'s {table}.')
            main["fields"][fld] = found[0]["sys_id"]
        if component.get("action") == "update" and component.get("sys_id"):
            before = self.client.get(sp.table, component["sys_id"], fields=list(main["fields"]))
            if before is None:
                raise DeployError(f'{component["name"]}: the artifact it changes ({component["sys_id"]}) '
                                  f"isn't in this instance any more.")
            self.client.update(sp.table, component["sys_id"], main["fields"])
            record = DeployedRecord(component["id"], sp.table, component["sys_id"], "update", before=before)
        else:
            created = self.client.insert(sp.table, main["fields"])
            if not created.get("sys_id"):
                raise DeployError(f'{component["name"]}: the instance didn\'t return the record it created.')
            record = DeployedRecord(component["id"], sp.table, created["sys_id"], "create")
        # Register the parent before any child writes; child failures must remain rollbackable.
        if on_partial is not None:
            on_partial(record)
        # Track each created child immediately so a partial failure is visible for rollback.
        for child in rows[1:]:
            link = {child["parent_field"]: record.sys_id} if child.get("parent_field") else {}
            made = self.client.insert(child["table"], {**child["fields"], **link})
            if not made.get("sys_id"):
                raise DeployError(f'{component["name"]}: child record in {child["table"]} did not return a sys_id.')
            record.children.append({"table": child["table"], "sys_id": made["sys_id"]})
        return record


def _flows_deployable() -> bool:
    from . import sdk_deploy
    return sdk_deploy.configured()


def _deployable(c: dict) -> bool:
    """Table API types always; flows when the ServiceNow SDK can run on this backend."""
    return spec(c["type"]).deployable or (c["type"] == "flow" and _flows_deployable())


def deploy(db, plan: Plan, client: ServiceNowClient, instance: Instance, update_set_name: str,
           user_id: str, on_status=lambda s: None) -> dict:
    """Deploy the approved rows: Table API rows into a new update set (left as the connected user's
    current update set, so the instance's update set picker shows it), flows with the ServiceNow SDK.

    Deploying again only deploys approved rows that aren't in yet (a flow that waited for the SDK, a
    row fixed after a failure); what went in before stays recorded for rollback."""
    approval = plan.approval or {}
    if not approval.get("ids"):
        raise DeployError("Approve the plan before deploying it.")
    missing = set(approval["ids"]) - {c["id"] for c in plan.components}
    if missing:
        raise DeployError("Approved artifacts are missing from the plan. Review and approve the current plan again.")
    previous = plan.deployment or {}
    if previous.get("status") == "rollback_failed":
        raise DeployError("A rollback of this plan failed. Resolve it in the instance before deploying again.")
    if previous.get("status") in ("deployed", "partial") and previous.get("instance_id") not in (None, instance.id):
        raise DeployError("This plan is deployed to another instance. Roll it back there first.")
    by_id = {c["id"]: c for c in plan.components}
    chosen = [by_id[i] for i in approval["ids"] if i in by_id
              and (by_id[i].get("deploy") or {}).get("status") != "deployed"]
    if not chosen:
        raise DeployError("Everything approved in this plan is already deployed.")
    unsupported = [c["name"] for c in chosen if not _deployable(c)]
    if unsupported:
        from . import sdk_deploy
        raise DeployError("Can't deploy " + ", ".join(unsupported) + ": " + sdk_deploy.why_not_configured())
    blocked = [c["name"] for c in chosen if checks.blocking(c)]
    if blocked:
        raise DeployError("These have problems and can't be deployed: " + ", ".join(blocked) + ".")

    # A per-process lock avoids racing the same ServiceNow user's mutable preference.
    if not _deployment_lock.acquire(blocking=False):
        raise DeployError("Another deployment is running. Wait for it to finish before deploying again.")
    try:
        return _deploy_locked(db, plan, client, instance, update_set_name, user_id, on_status, chosen, previous)
    finally:
        _deployment_lock.release()


def _keep_update_set_current() -> bool:
    import os
    return os.getenv("NOWBUILDER_KEEP_UPDATE_SET_CURRENT", "true").strip().lower() not in ("false", "0", "no")


def _deploy_table_rows(deployer: "Deployer", client, rows: list[dict], update_set_name: str, plan: Plan,
                       on_status) -> dict:
    """Write Table API rows into a new update set. Returns status, update set, records, message, captured."""
    from . import application as apps
    target = apps.resolve(client, getattr(plan, "application", "") or "global")
    if target is None:
        raise DeployError(f"The application '{apps.label(plan.application)}' the plan is built for isn't on this "
                          "instance. Create it first, or ask nowBuilder to build the plan in Global.")
    on_status(f"Switching to the {target['name']} application")
    app_pref, app_prev = deployer.set_application(target["sys_id"])
    on_status("Creating the update set")
    update_set = deployer.create_update_set(update_set_name, f"nowBuilder: {plan.title}\n\n{plan.summary}".strip(),
                                            application=target["sys_id"])
    update_set["application"] = target["name"]
    pref_id, prev_value = None, None
    written: list[DeployedRecord] = []
    message = ""
    scope_notes: list[str] = []
    try:
        pref_id, prev_value = deployer.set_current(update_set["sys_id"])
        deployer.verify_current(update_set["sys_id"])
        # Tables before their fields, fields before what uses them; dependsOn still decides the rest.
        first = {"table": 0, "field": 1}
        for component in Skills.deploy_order(sorted(rows, key=lambda c: first.get(c["type"], 2))):
            on_status(f'Deploying the {label(component["type"]).lower()}: {component["name"]}')
            result = deployer.write(component, on_partial=written.append)
            # A successful POST/PATCH response is not enough: read the record back.
            on_status(f'Verifying the {label(component["type"]).lower()}: {component["name"]}')
            actual = client.get(result.table, result.sys_id)
            if actual is None or str(actual.get("sys_id", "")) != result.sys_id:
                raise DeployError(f'{component["name"]}: write returned a sys_id but the record could not be verified.')
            for child in result.children:
                if client.get(child["table"], child["sys_id"]) is None:
                    raise DeployError(f'{component["name"]}: child {child["table"]} could not be verified.')
            component["deploy"] = {"status": "deployed", "sys_id": result.sys_id, "verified": True,
                                   "url": f'{client.url}/{result.table}.do?sys_id={result.sys_id}',
                                   "application": target["name"]}
            actual_scope = apps.scope_of(actual)
            if actual_scope and target["sys_id"] and actual_scope != target["sys_id"]:
                note = (f"Created in another application ({actual_scope}), not {target['name']}: the instance "
                        "didn't apply the application switch to this record.")
                component["deploy"]["application_note"] = note
                scope_notes.append(f'{component["name"]}: {note}')
        status = "deployed"
    except Exception as e:
        # Persist partial writes even on unexpected exceptions.
        log.exception("Deployment interrupted")
        status = "partial" if written else "failed"
        message = str(e)
        done = {r.component_id for r in written}
        for component in rows:
            if component["id"] not in done:
                component["deploy"] = {"status": "not deployed", "message": message[:500]}
            elif component.get("deploy", {}).get("status") != "deployed":
                component["deploy"] = {"status": "verification failed", "sys_id": next(
                    (r.sys_id for r in written if r.component_id == component["id"]), None)}
    finally:
        # The new update set stays the user's current one (the instance's update set picker shows
        # it), unless nothing went in or NOWBUILDER_KEEP_UPDATE_SET_CURRENT=false.
        if not _keep_update_set_current() or not written:
            deployer.restore_current(pref_id, prev_value)
            deployer.restore_current(app_pref, app_prev)

    captured = deployer.captured(update_set["sys_id"])
    if status == "failed" and not message:
        message = "Deployment stopped before any artifact was written."
    if status == "deployed" and captured == 0:
        message = ("Every artifact was created and read back, but the instance captured none of them "
                   "into the update set, so there is nothing to promote to another instance. The "
                   "records are live in this instance. Check that the connected user may change its "
                   "own current update set, then roll this back and deploy again.")
    elif status == "deployed" and captured == -1:
        message = ("Every artifact was created and read back. nowBuilder couldn't check update set "
                   "capture because it can't read sys_update_xml on this instance — open the update "
                   "set in ServiceNow to confirm what it holds.")
    if scope_notes:
        message = " ".join([message, *scope_notes]).strip()
    return {"status": status, "update_set": update_set, "captured": captured, "written": written,
            "message": message, "current": bool(written) and _keep_update_set_current()}


def _scope_name(client: ServiceNowClient, scope_id) -> str:
    scope_id = str(scope_id or "")
    if not scope_id or scope_id == "global":
        return scope_id
    try:
        row = client.get("sys_scope", scope_id, fields=["scope"])
    except ServiceNowError:
        return ""
    return str((row or {}).get("scope") or "")


def deploy_flow(plan: Plan, c: dict, client: ServiceNowClient, instance: Instance, on_status=lambda s: None) -> dict:
    """Install one flow row with the ServiceNow SDK and read it back. Sets c["deploy"]; returns it."""
    from ..ai.flow_sdk import plan_refs, resolve_plan_refs
    from ..security import decrypt
    from . import sdk_deploy
    name = c.get("name") or "Flow"
    by_id = {x["id"]: x for x in plan.components}
    refs = plan_refs(c.get("generated") or {})
    sys_ids = {r: (by_id.get(r, {}).get("deploy") or {}).get("sys_id") for r in refs}
    missing = [r for r, v in sys_ids.items() if not v]
    if missing:
        c["deploy"] = {"status": "not deployed",
                       "message": "It uses " + ", ".join(by_id.get(r, {}).get("name", r) for r in missing)
                                  + ", which isn't deployed yet. Approve and deploy it too."}
        return c["deploy"]
    generated = resolve_plan_refs(c.get("generated") or {}, {k: v for k, v in sys_ids.items() if v})
    on_status(f"Deploying the flow: {name}")
    try:
        password = decrypt(instance.password_enc) if instance.password_enc else None
        from . import application as apps
        wanted = "global" if apps.is_global(getattr(plan, "application", "") or "global") else "scoped"
        installed = sdk_deploy.run_scoped_flow(generated, install=True, instance_url=instance.url,
                                               username=instance.username, password=password,
                                               client=client, on_status=on_status, application=wanted,
                                               release=instance.release or "") or {}
    except sdk_deploy.SDKSetupPending as e:
        c["deploy"] = {"status": "waiting for SDK setup", "message": str(e)}
        return c["deploy"]
    except sdk_deploy.SDKDeployError as e:
        c["deploy"] = {"status": "failed", "message": str(e)[:1500]}
        return c["deploy"]
    flow_name = str((generated.get("record") or {}).get("name") or name)
    on_status(f"Verifying the flow: {name}")
    try:
        found = sdk_deploy.read_back_flow(client, flow_name)
    except ServiceNowError:
        found = None
    if found is None:
        c["deploy"] = {"status": "verification failed", "via": "sdk",
                       "message": "The SDK install finished, but no flow with this name came back from sys_hub_flow."}
    else:
        # A Global application's records point sys_scope at the application record, whose scope is
        # "global"; only a scoped app has its own scope name there.
        scope_name = _scope_name(client, found.get("sys_scope"))
        in_global = scope_name == "global"
        c["deploy"] = {"status": "deployed", "via": "sdk", "verified": True, "sys_id": found["sys_id"],
                       "active": found["active"], "flow_status": found["status"], "url": found["url"],
                       "application": str(installed.get("application") or ("Global" if in_global else scope_name)
                                          or found.get("sys_scope") or "")}
        notes = [installed[k] for k in ("application_note", "body_note") if installed.get(k)]
        from ..ai.flow_sdk import has_static_pills, manual_pills
        if has_static_pills(generated) and not installed.get("body_note"):
            notes.append("The email body's record values are written as Flow Designer pill references "
                         "({{trigger.current.<field>}}): check that the first email shows the values.")
        if by_hand := manual_pills(generated):
            notes.append("Drag these data pills into the email body in Flow Designer (the SDK installs it as fixed "
                         "text): " + "; ".join(by_hand) + ".")
        if wanted == "global" and found.get("sys_scope") and not in_global:
            notes.append("The instance reports this flow outside Global.")
        # An earlier install of the same flow in nowBuilder's scoped app would run next to this one
        # and send everything twice: switch it off (it stays in the instance and can be reactivated).
        if in_global:
            for old in sdk_deploy.older_copies(client, flow_name, found["sys_id"]):
                try:
                    client.update("sys_hub_flow", old["sys_id"], {"active": "false"})
                    notes.append(f"Deactivated the earlier copy of this flow in {old['scope']} so it doesn't run twice.")
                except ServiceNowError:
                    notes.append(f"An earlier copy of this flow is still active in {old['scope']}: deactivate it in "
                                 "Flow Designer, or both will run.")
        if notes:
            c["deploy"]["application_note"] = " ".join(notes)
            c["deploy"]["message"] = " ".join(notes)
    return c["deploy"]


def _deploy_locked(db, plan, client, instance, update_set_name, user_id, on_status, chosen, previous):
    deployer = Deployer(client, instance)
    rows = [c for c in chosen if spec(c["type"]).deployable]
    flows = [c for c in chosen if c["type"] == "flow"]
    result = {"status": "deployed", "update_set": previous.get("update_set"), "captured": previous.get("captured"),
              "written": [], "message": "", "current": False}
    if rows:
        result = _deploy_table_rows(deployer, client, rows, update_set_name, plan, on_status)
    flow_results = []
    if flows and result["status"] != "failed":
        for c in flows:
            flow_results.append({"id": c["id"], "name": c.get("name"), **deploy_flow(plan, c, client, instance, on_status)})
    elif flows:
        for c in flows:
            c["deploy"] = {"status": "not deployed", "message": "Stopped: the rows before it didn't deploy."}

    # Everything this plan has in the instance, across deploys, for rollback.
    records = list(previous.get("records") or []) + [r.as_dict() for r in result["written"]]
    approved = [c for c in plan.components if c["id"] in (plan.approval or {}).get("ids", [])]
    states = [(c.get("deploy") or {}).get("status") for c in approved]
    if all(st == "deployed" for st in states):
        status = "deployed"
    elif records or any(st == "deployed" for st in states):
        status = "partial"
    else:
        status = "failed"
    messages = [m for m in (result["message"],) if m]
    messages += [f'{f["name"]}: {f.get("message")}' for f in flow_results if f.get("status") != "deployed" and f.get("message")]
    plan.deployment = {"status": status, "at": _now(), "by": user_id, "instance_id": instance.id,
                       "update_set": result["update_set"], "update_set_current": result["current"],
                       "captured": result["captured"],
                       "ids": [c["id"] for c in approved if (c.get("deploy") or {}).get("status") == "deployed"],
                       "records": records, "flows": flow_results or previous.get("flows", []),
                       "message": " ".join(messages)}
    plan.status = "deployed" if status == "deployed" else plan.status
    _touch(db, plan)
    if status == "failed":
        raise DeployError(plan.deployment["message"] or "Nothing could be deployed.")
    return plan.deployment


# ---------- rollback ----------

def rollback(db, plan: Plan, client: ServiceNowClient, user_id: str, on_status=lambda s: None) -> dict:
    """Undo what was deployed: delete what was created, put back what was changed."""
    deployment = plan.deployment or {}
    if deployment.get("status") not in ("deployed", "partial"):
        raise DeployError("There's nothing deployed to roll back.")
    by_id = {c["id"]: c for c in plan.components}
    undone, failed = [], []
    for row in reversed(deployment.get("records") or []):
        name = by_id.get(row["component_id"], {}).get("name", row["table"])
        on_status(f"Rolling back {name}")
        try:
            for child in reversed(row.get("children") or []):
                client.delete(child["table"], child["sys_id"])
            if row["action"] == "create":
                client.delete(row["table"], row["sys_id"])
            else:
                client.update(row["table"], row["sys_id"], row.get("before") or {})
            undone.append(row["component_id"])
            if (c := by_id.get(row["component_id"])) is not None:
                c["deploy"] = {"status": "rolled back"}
        except ServiceNowError as e:
            failed.append(f"{name}: {e}")
            if (c := by_id.get(row["component_id"])) is not None:
                c["deploy"] = {"status": "rollback failed", "message": str(e)}

    plan.deployment = {**deployment, "status": "rolled_back" if not failed else "rollback_failed",
                       "rolled_back_at": _now(), "rolled_back_by": user_id, "undone": undone,
                       "message": "; ".join(failed)}
    plan.status = "approved" if plan.approval else "draft"
    _touch(db, plan)
    if failed:
        raise DeployError("Some artifacts couldn't be rolled back: " + "; ".join(failed))
    return plan.deployment


def _touch(db, plan: Plan) -> None:
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(plan, "components")
    db.commit()


# ---------- Push to Git ----------

EXTENSION = {"business_rule": "js", "script_include": "js", "client_script": "js", "ui_action": "js",
             "scheduled_job": "js", "script_action": "js"}


def files_for(plan: Plan, ids: list[str] | None = None) -> dict[str, str]:
    """The plan as files for a pull request: each artifact's script beside its settings as JSON."""
    import json
    import re
    out: dict[str, str] = {}
    for c in plan.components:
        if ids is not None and c["id"] not in ids:
            continue
        data = c.get("generated") or {}
        if not data:
            continue
        sp = spec(c["type"])
        slug = re.sub(r"[^a-z0-9]+", "_", (data.get("record", {}).get(sp.name_field) or c["name"]).lower()).strip("_")[:60]
        base = f'servicenow/{c["type"]}/{slug or c["id"]}'
        settings = {k: v for k, v in (data.get("record") or {}).items()}
        if data.get("actions"):
            settings["actions"] = data["actions"]
        out[f"{base}.json"] = json.dumps(settings, indent=2, sort_keys=True) + "\n"
        if sp.has_script and data.get("script"):
            out[f'{base}.{EXTENSION.get(c["type"], "txt")}'] = data["script"].rstrip() + "\n"
    return out

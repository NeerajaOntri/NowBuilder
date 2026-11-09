"""Move a deployed update set to another connected instance (Dev → Test → Prod), the way ServiceNow's
own "Retrieve" does it: the source's customer updates (sys_update_xml) are copied into a new retrieved
update set (sys_remote_update_set, state "loaded") on the target. The target's admin then previews and
commits it there - ServiceNow's preview catches missing dependencies and conflicts, so nowBuilder never
commits on their behalf."""
from __future__ import annotations

from .servicenow import ServiceNowClient, ServiceNowError

XML_FIELDS = ["sys_id", "name", "type", "target_name", "action", "category", "payload", "application",
              "update_domain", "view", "table", "sys_recorded_at", "comments"]
MAX_UPDATES = 2000


class PromoteError(Exception):
    pass


def _text(v) -> str:
    if isinstance(v, dict):
        return str(v.get("value") or "")
    return str(v or "")


def preview(source: ServiceNowClient, update_set_id: str) -> dict:
    """What would move: the update set and its customer updates (names only)."""
    us = source.get("sys_update_set", update_set_id, fields=["sys_id", "name", "state", "description", "application"])
    if not us:
        raise PromoteError("That update set isn't on the source instance any more.")
    rows = source.query("sys_update_xml", f"update_set={update_set_id}^ORDERBYsys_recorded_at",
                        ["sys_id", "name", "type", "target_name", "action"], limit=MAX_UPDATES)
    return {"update_set": {"sys_id": update_set_id, "name": _text(us.get("name")), "state": _text(us.get("state"))},
            "updates": [{"name": _text(r.get("name")), "type": _text(r.get("type")),
                         "target": _text(r.get("target_name")), "action": _text(r.get("action"))} for r in rows]}


def promote(source: ServiceNowClient, target: ServiceNowClient, update_set_id: str, on_status=lambda s: None) -> dict:
    us = source.get("sys_update_set", update_set_id, fields=["sys_id", "name", "state", "description", "application"])
    if not us:
        raise PromoteError("That update set isn't on the source instance any more.")
    on_status("Reading the customer updates")
    rows = source.query("sys_update_xml", f"update_set={update_set_id}^ORDERBYsys_recorded_at", XML_FIELDS,
                        limit=MAX_UPDATES)
    if not rows:
        raise PromoteError("The update set has no customer updates to move.")
    name = _text(us.get("name"))
    on_status(f"Creating the retrieved update set on {target.url}")
    remote = target.insert("sys_remote_update_set", {
        "name": name, "description": _text(us.get("description")) or f"Moved from {source.url} by nowBuilder",
        "state": "loaded", "origin_sys_id": update_set_id, "remote_base_update_set": update_set_id,
        "application": _text(us.get("application")) or "global",
    })
    remote_id = remote.get("sys_id")
    if not remote_id:
        raise PromoteError("The target instance didn't create the retrieved update set.")
    copied = 0
    try:
        for r in rows:
            fields = {k: _text(r.get(k)) for k in XML_FIELDS if k != "sys_id" and _text(r.get(k))}
            fields["remote_update_set"] = remote_id
            target.insert("sys_update_xml", fields)
            copied += 1
            if copied % 25 == 0:
                on_status(f"Copied {copied} of {len(rows)} updates")
    except ServiceNowError as exc:
        try:
            target.delete("sys_remote_update_set", remote_id)
        except ServiceNowError:
            pass
        raise PromoteError(f"Copying stopped after {copied} of {len(rows)} updates ({exc}); nothing was left "
                           "on the target.") from exc
    found = target.query("sys_update_xml", f"remote_update_set={remote_id}", ["sys_id"], limit=MAX_UPDATES)
    return {"remote_update_set": remote_id, "name": name, "copied": copied, "verified": len(found),
            "url": f"{target.url}/sys_remote_update_set.do?sys_id={remote_id}",
            "next": "Open it on the target instance, click Preview Update Set, resolve any problems it lists, "
                    "then Commit Update Set."}

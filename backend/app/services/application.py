"""The application (scope) a plan's artifacts are built in.

A requirement or design document says where its artifacts belong ("Application: Global", "Scope:
x_acme_crm"). The plan keeps that value, the checks confirm the application exists on the instance,
and the deployment makes it the connected user's current application before writing, the same way
ServiceNow's application picker does, so every Table API record lands in it. Each record's
`sys_scope` is read back, so a mismatch is reported rather than assumed away.
"""
from __future__ import annotations

import re

from .servicenow import ServiceNowClient, ServiceNowError

GLOBAL = {"scope": "global", "sys_id": "global", "name": "Global"}
PREFERENCE_NAME = "apps.current_app"
_SCOPE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")


def normalize(value: object) -> str:
    """'Global', 'global scope', '' → 'global'; 'x_acme_crm' stays; template blanks ('[exact scope]') → 'global'."""
    text = str(value or "").strip()
    text = re.sub(r"\[[^\]]*\]", "", text).strip(" /|-")          # "SOMT / [exact scope]" → "SOMT"
    low = text.lower()
    if not low or low in ("global", "global scope", "global application", "the global scope"):
        return "global"
    m = re.search(r"\b(x_[a-z0-9_]+|sn_[a-z0-9_]+)\b", low)          # an explicit scope name wins
    if m:
        return m.group(1)
    return text[:80]                                              # an application's name, resolved on the instance


def label(value: str) -> str:
    return "Global" if normalize(value) == "global" else normalize(value)


def is_global(value: str) -> bool:
    return normalize(value) == "global"


def resolve(client: ServiceNowClient | None, value: str) -> dict | None:
    """{scope, sys_id, name} for the application, or None when the instance doesn't have it.
    Without a client (no instance) the value is trusted as written."""
    app = normalize(value)
    if app == "global":
        return dict(GLOBAL)
    if client is None:
        return {"scope": app, "sys_id": "", "name": app}
    queries = [f"scope={app}"] if _SCOPE.match(app) else []
    queries.append(f"name={app}")
    for q in queries:
        try:
            rows = client.query("sys_scope", q, ["sys_id", "scope", "name"], limit=1)
        except ServiceNowError:
            return None
        if rows:
            r = rows[0]
            return {"scope": str(r.get("scope") or app), "sys_id": str(r.get("sys_id") or ""),
                    "name": str(r.get("name") or app)}
    return None


def scope_of(record: dict | None) -> str:
    """The scope a record was created in, from its sys_scope value ('global' or a sys_scope sys_id)."""
    value = (record or {}).get("sys_scope")
    if isinstance(value, dict):
        value = value.get("value")
    return str(value or "")

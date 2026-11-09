"""Instance health check: read the connected instance's active custom scripts and report what breaks
ServiceNow best practice, with the same rules nowBuilder applies to what it writes (current.update() in
before/after rules, GlideRecord in client scripts, synchronous GlideAjax, hard-coded sys_ids, ES2021
syntax in global scripts …). Read-only: it never changes the instance."""
from __future__ import annotations

from ..ai import checks
from .servicenow import ServiceNowClient, ServiceNowError

# type -> (table, fields read, encoded query for "active and custom": not shipped by ServiceNow)
SOURCES = {
    "business_rule": ("sys_script", ["sys_id", "name", "collection", "when", "script", "sys_updated_on"],
                      "active=true^advanced=true^sys_policy=^sys_created_by!=system"),
    "client_script": ("sys_script_client", ["sys_id", "name", "table", "type", "script", "sys_updated_on"],
                      "active=true^sys_policy=^sys_created_by!=system"),
    "script_include": ("sys_script_include", ["sys_id", "name", "client_callable", "script", "sys_updated_on"],
                       "active=true^sys_policy=^sys_created_by!=system"),
    "ui_action": ("sys_ui_action", ["sys_id", "name", "table", "client", "script", "sys_updated_on"],
                  "active=true^sys_policy=^sys_created_by!=system"),
}
PER_TYPE = 200


def _text(v) -> str:
    if isinstance(v, dict):
        return str(v.get("value") or v.get("display_value") or "")
    return str(v or "")


def scan(client: ServiceNowClient, on_status=lambda s: None) -> dict:
    findings: list[dict] = []
    scanned = 0
    unreadable: list[str] = []
    for type_, (table, fields, query) in SOURCES.items():
        on_status(f"Reading {table}")
        try:
            rows = client.query(table, query + "^ORDERBYDESCsys_updated_on", fields, limit=PER_TYPE)
        except ServiceNowError as exc:
            unreadable.append(f"{table}: {exc}")
            continue
        for r in rows:
            scanned += 1
            script = _text(r.get("script"))
            when = _text(r.get("when")) if type_ == "business_rule" else ""
            try:
                problems = checks._script_problems(type_, script, when, False)
            except Exception:  # noqa: BLE001 - one odd script must not stop the scan
                continue
            for p in problems:
                d = p.as_dict()
                if d["severity"] not in (checks.ERROR, checks.WARNING):
                    continue
                findings.append({
                    "type": type_, "table": table, "sys_id": _text(r.get("sys_id")), "name": _text(r.get("name")),
                    "on": _text(r.get("collection") or r.get("table")), "severity": d["severity"],
                    "message": d["message"], "url": f"{client.url}/{table}.do?sys_id={_text(r.get('sys_id'))}",
                })
    findings.sort(key=lambda f: (f["severity"] != checks.ERROR, f["type"], f["name"]))
    errors = sum(1 for f in findings if f["severity"] == checks.ERROR)
    score = max(0, 100 - errors * 5 - (len(findings) - errors))
    return {"scanned": scanned, "findings": findings, "errors": errors, "warnings": len(findings) - errors,
            "score": score, "unreadable": unreadable}

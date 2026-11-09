"""Tools the model can call: reading the connected ServiceNow instance and skill files."""
from __future__ import annotations

import json
import re

from ..security import SecretUnreadable
from ..services.servicenow import ServiceNowClient, ServiceNowError
from .skills import Skills

MAX_TOOL_RESULT_CHARS = 60_000
_TABLE = re.compile(r"^[a-z][a-z0-9_]{0,79}$")
_FIELD = re.compile(r"^[a-z][a-z0-9_]{0,79}$")
# Read-only guardrails: restrict sensitive system tables; access is also controlled by ServiceNow ACLs.
_BLOCKED_TABLES = {"sys_user_has_role", "sys_user_role", "sys_user_preference", "sys_properties", "sys_auth_profile_basic", "sys_credentials", "sys_certificate", "sys_encryption_context", "sys_update_xml", "sys_update_set", "sys_attachment_doc", "sys_user_token"}

TYPE_LABELS = {"business_rule": "business rules", "script_include": "script includes", "client_script": "client scripts",
               "ui_policy": "UI policies", "ui_action": "UI actions", "notification": "notifications", "flow": "flows",
               "scheduled_job": "scheduled jobs", "data_policy": "data policies", "system_property": "system properties",
               "event": "event registrations", "script_action": "script actions",
               "table": "tables", "field": "fields"}
ONE_LABEL = {"business_rule": "business rule", "script_include": "script include", "client_script": "client script",
             "ui_policy": "UI policy", "ui_action": "UI action", "notification": "notification", "flow": "flow",
             "scheduled_job": "scheduled job", "data_policy": "data policy", "system_property": "system property",
             "event": "event registration", "script_action": "script action",
             "table": "table", "field": "field"}
NO_INSTANCE = "No ServiceNow instance is connected. The user can connect one in Settings → ServiceNow instances."


class ToolRunner:
    def __init__(self, skills: Skills, client: ServiceNowClient | None):
        self.skills, self.client = skills, client

    @staticmethod
    def describe(name: str, args: dict) -> str:
        if name == "query_instance_records":
            return f'Reading records from {args.get("table", "a table")} (read-only)'
        if name == "get_flow_actions":
            what = args.get("name_contains")
            return (f'Reading the “{what}” flow actions and their inputs' if what
                    else "Looking up the flow actions this instance has")
        if name == "get_table_schema":
            return f'Reading fields on {", ".join(args.get("tables") or []) or "tables"}'
        if name == "search_instance_artifacts":
            what = TYPE_LABELS.get(args.get("type", ""), "artifacts")
            on = f' on {args["table"]}' if args.get("table") else ""
            extra = f' matching “{args["name_contains"]}”' if args.get("name_contains") else ""
            return f"Looking for existing {what}{on}{extra}"
        if name == "get_instance_artifact":
            return f'Reading the {ONE_LABEL.get(args.get("type", ""), "artifact")}'
        if name == "search_servicenow_docs":
            return "Searching ServiceNow and Fluent SDK documentation"
        if name == "read_servicenow_doc":
            return "Reading ServiceNow documentation"
        if name == "get_skill_file":
            return f'Reading {args.get("path", "a reference")}'
        return "Working"

    def run(self, name: str, args: dict) -> tuple[str, bool]:
        try:
            if name in ("search_servicenow_docs", "read_servicenow_doc"):
                from .docs import search_docs, read_doc
                if name == "search_servicenow_docs":
                    return json.dumps(search_docs(str(args.get("query", ""))[:500], args.get("limit", 5))), False
                return json.dumps(read_doc(str(args.get("path", "")))), False
            if name == "get_skill_file":
                return self.skills.get_skill_file(args["skill"], args["path"])[:MAX_TOOL_RESULT_CHARS], False
            if name not in ("get_table_schema", "search_instance_artifacts", "get_instance_artifact",
                            "query_instance_records", "get_flow_actions"):
                return f"Unknown tool {name}", True
            if not self.client:
                return NO_INSTANCE, True
            if name == "query_instance_records":
                table = str(args.get("table", "")).strip()
                if not _TABLE.fullmatch(table) or table in _BLOCKED_TABLES or table.startswith("sys_oauth"):
                    raise ValueError("This table is not available for general record queries.")
                fields = args.get("fields") or []
                if not isinstance(fields, list) or len(fields) > 25 or any(not isinstance(f, str) or not _FIELD.fullmatch(f) for f in fields):
                    raise ValueError("Provide at most 25 valid field names.")
                limit = args.get("limit", 10)
                if type(limit) is not int or not 1 <= limit <= 100:
                    raise ValueError("limit must be between 1 and 100.")
                query = args.get("query", "")
                if not isinstance(query, str) or len(query) > 1000 or any(ord(c) < 32 for c in query):
                    raise ValueError("Invalid encoded query.")
                # Only reads; no insert/update/delete is exposed to the model.
                rows = self.client.query(table, query, fields or None, limit=limit)
                out = {"table": table, "count": len(rows), "limit": limit, "records": rows}
            elif name == "get_flow_actions":
                # Naming an action means the design is about to use it, so its inputs come back too.
                what = str(args.get("name_contains", ""))[:80]
                out = self.client.flow_actions(what, with_inputs=bool(what))
            elif name == "get_table_schema":
                out = [self.client.table_schema(t) for t in list(args.get("tables") or [])[:5]]
            elif name == "search_instance_artifacts":
                out = self.client.search_artifacts(args.get("type", ""), args.get("name_contains", ""), args.get("table", ""))
            else:
                out = self.client.get_artifact(args.get("type", ""), args.get("sys_id", ""))
        except (ServiceNowError, SecretUnreadable, ValueError, KeyError) as e:
            return f"{type(e).__name__}: {e}", True
        text = json.dumps(out, default=str)
        if len(text) > MAX_TOOL_RESULT_CHARS:
            text = text[:MAX_TOOL_RESULT_CHARS] + '…" [truncated: ask for fewer tables or a narrower search]'
        return text, False

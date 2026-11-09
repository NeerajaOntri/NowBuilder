"""An in-memory ServiceNow instance behind httpx.MockTransport: the Table API (GET/POST/PATCH/DELETE with a
small subset of encoded queries) and /oauth_token.do. Tests talk to it through the real ServiceNowClient."""
from __future__ import annotations

import base64
import itertools
import json
import re
from urllib.parse import parse_qs

import httpx

_ids = itertools.count(1)

# A few real action inputs, keyed by internal name, so tests exercise the input lookup.
ACTION_INPUTS: dict[str, list[tuple[str, str, str]]] = {
    "log": [("log_message", "Message", "string"), ("log_level", "Level", "choice")],
    "send_notification": [("notification_id", "Notification", "reference"),
                          ("record_id", "Record", "document_id")],
    "create_record": [("table_name", "Table", "table_name"), ("fields", "Fields", "json")],
    "update_record": [("record_id", "Record", "document_id"), ("fields", "Fields", "json")],
    "ask_for_approval": [("record_id", "Record", "document_id"), ("approvers", "Approvers", "glide_list")],
}


def sys_id() -> str:
    return f"{next(_ids):032x}"


class FakeInstance:
    def __init__(self, username: str = "admin", password: str = "pw", admin: bool = True):
        self.username, self.password = username, password
        self.client_id, self.client_secret = "cid", "csecret"
        self.tokens: dict[str, str] = {}
        self.refresh_tokens: set[str] = set()
        self.calls: list[tuple[str, str]] = []
        self.hibernating = False
        self.forbidden: set[str] = set()  # tables the user can't read
        user = sys_id()
        self.tables: dict[str, list[dict]] = {
            "sys_user": [{"sys_id": user, "user_name": username, "name": "System Administrator"}],
            "sys_user_has_role": [{"sys_id": sys_id(), "user": user, "role": r, "state": "active"}
                                  for r in (["admin", "itil"] if admin else ["itil"])],
            "sys_properties": [{"sys_id": sys_id(), "name": "glide.buildname", "value": "Yokohama"}],
            "sys_db_object": [],
            "sys_dictionary": [],
            "sys_script": [], "sys_script_include": [], "sys_script_client": [], "sys_ui_policy": [], "sys_ui_action": [],
            "sys_ui_policy_action": [],
            # update sets: the current one per user is a preference, and writes to tracked tables are captured
            "sys_update_set": [], "sys_user_preference": [], "sys_update_xml": [],
            "sysevent_email_action": [],
            "sys_hub_flow": [], "sys_hub_action_type_definition": [], "sys_hub_action_input": [],
            "sysauto_script": [], "sys_data_policy2": [], "sys_data_policy_rule": [],
            "sysevent_register": [{"sys_id": "e0" * 16, "event_name": "x.p1.opened", "table": "incident"}], "sysevent_script_action": [], "sys_choice": [],
            "sys_glide_object": [{"sys_id": sys_id(), "name": t} for t in (
                "string", "integer", "boolean", "decimal", "float", "glide_date", "glide_date_time", "glide_duration",
                "reference", "choice", "journal_input", "html", "email", "url", "currency", "price", "glide_list", "script")],
        }
        # Flow Designer actions a stock instance has. Which actions exist really does vary by
        # release and installed spokes, which is why nowBuilder reads them instead of assuming.
        for action, internal in (
            ("Ask for Approval", "ask_for_approval"), ("Create Record", "create_record"),
            ("Create Task", "create_task"), ("Delete Record", "delete_record"),
            ("Log", "log"), ("Look Up Record", "look_up_record"),
            ("Look Up Records", "look_up_records"), ("Send Notification", "send_notification"),
            ("Send Email", "send_email"), ("Update Record", "update_record"),
            ("Wait For Condition", "wait_for_condition"),
        ):
            rec = self.add("sys_hub_action_type_definition", name=action, internal_name=internal,
                           description=f"{action} action", active="true", sys_scope="global")
            # Inputs are read from the instance too, because their names differ between spokes.
            for order, (element, label, type_) in enumerate(ACTION_INPUTS.get(internal, []), 1):
                self.add("sys_hub_action_input", model=rec["sys_id"], element=element, label=label,
                         internal_type=type_, reference="", mandatory="true", order=str(order))
        self.user_sys_id = user
        self.captures = True   # set False to act like an instance that doesn't capture the changes
        # Close enough to a real instance that the checks can be trusted: task's fields are
        # inherited by incident, which adds its own.
        task = self.add_table("task", "Task")
        for name, label, type_, ref in (
            ("number", "Number", "string", ""), ("short_description", "Short description", "string", ""),
            ("description", "Description", "string", ""), ("active", "Active", "boolean", ""),
            ("state", "State", "integer", ""), ("priority", "Priority", "integer", ""),
            ("impact", "Impact", "integer", ""), ("urgency", "Urgency", "integer", ""),
            ("work_notes", "Work notes", "journal_input", ""), ("comments", "Additional comments", "journal_input", ""),
            ("assignment_group", "Assignment group", "reference", "sys_user_group"),
            ("assigned_to", "Assigned to", "reference", "sys_user"),
            ("opened_at", "Opened", "glide_date_time", ""), ("cmdb_ci", "Configuration item", "reference", "cmdb_ci"),
            ("opened_by", "Opened by", "reference", "sys_user"), ("closed_at", "Closed", "glide_date_time", ""),
            ("sys_created_on", "Created", "glide_date_time", ""),
        ):
            self.add_field("task", name, label, type_, reference=ref, mandatory=(name == "number"))
        self.add_table("incident", "Incident", extends=task)
        for name, label, type_, ref in (
            ("category", "Category", "string", ""), ("subcategory", "Subcategory", "string", ""),
            ("caller_id", "Caller", "reference", "sys_user"), ("close_code", "Resolution code", "string", ""),
            ("close_notes", "Resolution notes", "string", ""), ("hold_reason", "On hold reason", "integer", ""),
        ):
            self.add_field("incident", name, label, type_, reference=ref)
        self.add_table("sys_user_group", "Group")
        self.add_field("sys_user_group", "name", "Name", "string")
        # the notification table, so the columns nowBuilder writes are checked against something real
        self.add_table("sysevent_email_action", "Notification")
        for f in ("name", "collection", "active", "action_insert", "action_update", "action_delete", "event_name",
                  "condition", "advanced_condition", "recipient_fields", "recipient_users", "recipient_groups",
                  "subject", "message", "message_html", "weight", "send_self", "exclude_delegates", "content_type",
                  "type", "category", "importance", "style", "from", "reply_to", "include_attachments",
                  "generation_type"):
            self.add_field("sysevent_email_action", f, f.replace("_", " ").title(), "string")
        self.transport = httpx.MockTransport(self.handle)

    # ----- seeding -----
    def add_table(self, name: str, label: str, extends: str | None = None) -> str:
        rec = {"sys_id": sys_id(), "name": name, "label": label, "super_class": extends or "", "sys_scope": "global"}
        self.tables["sys_db_object"].append(rec)
        return rec["sys_id"]

    def add_field(self, table: str, element: str, label: str, type_: str, reference: str = "", mandatory: bool = False) -> None:
        self.tables["sys_dictionary"].append({"sys_id": sys_id(), "name": table, "element": element, "column_label": label,
                                              "internal_type": type_, "reference": reference, "mandatory": str(mandatory).lower(),
                                              "max_length": "40", "active": "true"})

    def add(self, table: str, **fields) -> dict:
        return self.add_record(table, fields)

    def add_record(self, table: str, fields: dict) -> dict:
        """add() with the fields in a dict, for records that have a field of their own called
        "table" (client scripts, UI policies, UI actions, flows)."""
        rec = {"sys_id": sys_id(), **fields}
        self.tables.setdefault(table, []).append(rec)
        return rec

    # ----- HTTP -----
    def handle(self, req: httpx.Request) -> httpx.Response:
        self.calls.append((req.method, req.url.path))
        if self.hibernating:
            return httpx.Response(200, html="<html><body>Your instance is hibernating</body></html>")
        if req.url.path == "/oauth_token.do":
            return self._oauth(parse_qs(req.content.decode()))
        if not self._authorised(req):
            return httpx.Response(401, json={"error": {"message": "User Not Authenticated", "detail": "Required to provide Auth information"}})
        m = re.match(r"^/api/now/table/([a-z0-9_]+)(?:/([0-9a-f]+))?$", req.url.path)
        if not m:
            return httpx.Response(400, json={"error": {"message": "Invalid path"}})
        table, rid = m.groups()
        if table in self.forbidden:
            return httpx.Response(403, json={"error": {"message": "User Not Authorized"}})
        if table not in self.tables:
            return httpx.Response(400, json={"error": {"message": "Invalid table " + table}})
        rows = self.tables[table]
        q = dict(req.url.params)
        display = q.get("sysparm_display_value", "false")
        fields = [f for f in q.get("sysparm_fields", "").split(",") if f]
        if req.method == "GET" and rid:
            rec = next((r for r in rows if r["sys_id"] == rid), None)
            if rec is None:
                return httpx.Response(404, json={"error": {"message": "No Record found"}})
            return httpx.Response(200, json={"result": self._shape(rec, fields, display)})
        if req.method == "GET":
            found = [r for r in rows if self._match(r, q.get("sysparm_query", ""))]
            order = re.search(r"ORDERBY(\w+)", q.get("sysparm_query", ""))
            if order:
                found.sort(key=lambda r: str(r.get(order.group(1), "")))
            limit = int(q.get("sysparm_limit", "10000"))
            return httpx.Response(200, json={"result": [self._shape(r, fields, display) for r in found[:limit]]})
        if req.method == "POST":
            # built here rather than through add(), because records have fields of their own
            # called "table" (client scripts, UI policies, UI actions)
            rec = {"sys_id": sys_id(), **json.loads(req.content)}
            self.tables.setdefault(table, []).append(rec)
            self._capture(table, rec["sys_id"], "INSERT_OR_UPDATE")
            return httpx.Response(201, json={"result": rec})
        rec = next((r for r in rows if r["sys_id"] == rid), None)
        if rec is None:
            return httpx.Response(404, json={"error": {"message": "No Record found"}})
        if req.method == "PATCH":
            rec.update(json.loads(req.content))
            self._capture(table, rid, "INSERT_OR_UPDATE")
            return httpx.Response(200, json={"result": rec})
        rows.remove(rec)
        self._capture(table, rid, "DELETE")
        return httpx.Response(204)

    # ----- update set capture -----
    TRACKED = ("sys_script", "sys_script_include", "sys_script_client", "sys_ui_policy", "sys_ui_policy_action",
               "sys_ui_action", "sysevent_email_action", "sysauto_script", "sys_data_policy2", "sys_data_policy_rule",
               "sys_properties", "sysevent_register", "sysevent_script_action", "sys_db_object", "sys_dictionary",
               "sys_choice")

    def current_update_set(self) -> str:
        pref = next((p for p in self.tables["sys_user_preference"]
                     if p.get("name") == "sys_update_set" and p.get("user") == self.user_sys_id), None)
        return (pref or {}).get("value") or ""

    def _capture(self, table: str, sys_id: str, action: str) -> None:
        """What a real instance does: a change to a tracked table lands in the current update set."""
        if not self.captures or table not in self.TRACKED:
            return
        update_set = self.current_update_set()
        if update_set:
            self.add("sys_update_xml", update_set=update_set, name=f"{table}_{sys_id}", action=action,
                     target_name=table, type=table)

    def _authorised(self, req: httpx.Request) -> bool:
        h = req.headers.get("authorization", "")
        if h.startswith("Basic "):
            return base64.b64decode(h[6:]).decode() == f"{self.username}:{self.password}"
        return h.startswith("Bearer ") and h[7:] in self.tokens

    def _oauth(self, form: dict) -> httpx.Response:
        f = {k: v[0] for k, v in form.items()}
        if f.get("client_id") != self.client_id or f.get("client_secret") != self.client_secret:
            return httpx.Response(401, json={"error": "invalid_client", "error_description": "access_denied"})
        if f.get("grant_type") == "password" and (f.get("username"), f.get("password")) != (self.username, self.password):
            return httpx.Response(401, json={"error": "access_denied", "error_description": "access_denied"})
        if f.get("grant_type") == "refresh_token" and f.get("refresh_token") not in self.refresh_tokens:
            return httpx.Response(401, json={"error": "invalid_grant", "error_description": "access_denied"})
        access, refresh = f"at{sys_id()}", f"rt{sys_id()}"
        self.tokens[access] = self.username
        self.refresh_tokens.add(refresh)
        return httpx.Response(200, json={"access_token": access, "refresh_token": refresh, "expires_in": 1799, "token_type": "Bearer"})

    @staticmethod
    def _shape(rec: dict, fields: list[str], display: str) -> dict:
        out = {k: rec.get(k, "") for k in fields} if fields else dict(rec)
        if display == "all":
            return {k: {"value": v, "display_value": v} for k, v in out.items()}
        return out

    @staticmethod
    def _match(rec: dict, query: str) -> bool:
        groups: list[list[str]] = []  # AND of ORs: "a=1^ORa=2^b=3" -> [[a=1, a=2], [b=3]]
        for part in [p for p in query.split("^") if p and not p.startswith("ORDERBY")]:
            if part.startswith("OR") and groups:
                groups[-1].append(part[2:])
            else:
                groups.append([part])
        return all(any(FakeInstance._cond(rec, c) for c in g) for g in groups)

    @staticmethod
    def _cond(rec: dict, c: str) -> bool:
        if m := re.match(r"^(\w+)ISNOTEMPTY$", c):
            return bool(rec.get(m.group(1)))
        if m := re.match(r"^(\w+)LIKE(.*)$", c):
            return m.group(2).lower() in str(rec.get(m.group(1), "")).lower()
        if m := re.match(r"^(\w+)IN(.*)$", c):
            return str(rec.get(m.group(1), "")) in m.group(2).split(",")
        if m := re.match(r"^(\w+)!=(.*)$", c):
            return str(rec.get(m.group(1), "")) != m.group(2)
        if m := re.match(r"^(\w+)=(.*)$", c):
            return str(rec.get(m.group(1), "")) == m.group(2)
        raise AssertionError(f"FakeInstance can't read the condition {c!r}")

"""ServiceNow connection (Chunk 1): sign-in, the Table API, and reading the instance.

Two ways to sign in, both over HTTPS with the instance's own REST API:
- basic: username + password on every request (Basic auth).
- oauth: OAuth password grant against /oauth_token.do with a client id/secret from the instance's
  Application Registry. nowBuilder keeps the refresh token (encrypted) and renews access tokens
  itself; no browser redirect is needed.

Everything nowBuilder reads or writes goes through `/api/now/table/<table>` (the Table API),
so the connected user needs the roles that the work needs: `admin` to create business rules,
script includes and the rest (Chunk 4); reading tables needs read access to the sys_ tables.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ..security import decrypt, encrypt

TIMEOUT = httpx.Timeout(60, connect=15)
DEFAULT_TRANSPORT = None  # tests point this at a fake instance (httpx.MockTransport)


class ServiceNowError(Exception):
    """A plain-language problem talking to the instance (shown to the user)."""


@dataclass
class InstanceInfo:
    url: str
    release: str | None
    user_sys_id: str | None
    user_display_name: str | None
    roles: list[str]
    is_admin: bool


def normalise_url(raw: str) -> str:
    """'dev410284' or 'dev410284.service-now.com' or 'https://dev410284.service-now.com/nav_to.do' →
    'https://dev410284.service-now.com'. Custom domains are kept as given (https only)."""
    u = (raw or "").strip()
    if not u:
        raise ServiceNowError("Enter the instance address, for example https://dev12345.service-now.com.")
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + (u if "." in u else f"{u}.service-now.com")
    m = re.match(r"^(https?)://([^/?#]+)", u, re.I)
    if not m:
        raise ServiceNowError("That doesn't look like an instance address. Use https://<name>.service-now.com.")
    scheme, host = m.group(1).lower(), m.group(2).lower()
    if scheme != "https":
        raise ServiceNowError("The instance address must start with https://.")
    return f"https://{host}"


def _plain_error(r: httpx.Response) -> str:
    try:
        body = r.json()
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict):
            msg = err.get("message") or ""
            detail = err.get("detail") or ""
            return f"{msg}. {detail}".strip(". ").strip() if detail and detail != msg else msg
        if isinstance(body, dict) and body.get("error_description"):
            return str(body["error_description"])
    except ValueError:
        pass
    return r.text[:200].strip()


def _http_problem(r: httpx.Response, what: str) -> ServiceNowError:
    if r.status_code == 401:
        return ServiceNowError("The instance didn't accept the username and password (or the OAuth client). Check them and try again.")
    if r.status_code == 403:
        return ServiceNowError(f"The connected user isn't allowed to {what}. Give it the roles it needs (for building: admin).")
    if r.status_code == 404:
        return ServiceNowError(f"The instance couldn't find what nowBuilder asked for ({what}).")
    if r.status_code == 429:
        return ServiceNowError("The instance is limiting requests right now. Wait a minute and try again.")
    if r.status_code >= 500 and "hibernat" in r.text.lower():
        return ServiceNowError("The instance is hibernating. Wake it at developer.servicenow.com, then try again.")
    return ServiceNowError(f"The instance answered with an error ({r.status_code}) while trying to {what}: {_plain_error(r) or 'no details'}.")


# ---------- OAuth ----------

def oauth_password_grant(url: str, client_id: str, client_secret: str, username: str, password: str, transport=None) -> dict:
    """Exchange the user's credentials for tokens (once, when connecting). Raises ServiceNowError."""
    data = {"grant_type": "password", "client_id": client_id, "client_secret": client_secret, "username": username, "password": password}
    return _token_request(url, data, transport)


def oauth_refresh(url: str, client_id: str, client_secret: str, refresh_token: str, transport=None) -> dict:
    data = {"grant_type": "refresh_token", "client_id": client_id, "client_secret": client_secret, "refresh_token": refresh_token}
    return _token_request(url, data, transport)


def _token_request(url: str, data: dict, transport) -> dict:
    try:
        with httpx.Client(timeout=TIMEOUT, transport=transport or DEFAULT_TRANSPORT) as http:
            r = http.post(f"{url}/oauth_token.do", data=data, headers={"Accept": "application/json"})
    except httpx.HTTPError as e:
        raise ServiceNowError(f"Couldn't reach {url}. Check the address and that the instance is awake.") from e
    if r.status_code >= 400:
        detail = _plain_error(r)
        if "invalid_client" in r.text or "client" in detail.lower():
            raise ServiceNowError("The instance didn't accept the OAuth client id or secret. Check them in System OAuth → Application Registry.")
        raise ServiceNowError(f"The instance refused the sign-in: {detail or r.status_code}.")
    body = r.json()
    if not body.get("access_token"):
        raise ServiceNowError("The instance didn't return an access token.")
    return body


# ---------- the client ----------

_renew_lock = threading.Lock()


class ServiceNowClient:
    """Table API calls for one saved instance. `db` is used to save renewed OAuth tokens."""

    def __init__(self, instance, db=None, transport=None):
        self.instance, self.db, self.transport = instance, db, transport or DEFAULT_TRANSPORT
        self.url = instance.url.rstrip("/")

    # ----- auth -----
    def _auth(self) -> dict:
        inst = self.instance
        if inst.auth_method == "oauth":
            return {"headers": {"Authorization": f"Bearer {self._access_token()}"}}
        return {"auth": (inst.username, decrypt(inst.password_enc))}

    def _access_token(self, force: bool = False) -> str:
        inst = self.instance
        exp = inst.token_expires_at
        if exp is not None and exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        if not force and inst.access_token_enc and exp and exp > datetime.now(UTC) + timedelta(seconds=60):
            return decrypt(inst.access_token_enc)
        with _renew_lock:  # one renewal at a time per process
            secret = decrypt(inst.client_secret_enc)
            try:
                if inst.refresh_token_enc:
                    tokens = oauth_refresh(self.url, inst.client_id, secret, decrypt(inst.refresh_token_enc), self.transport)
                else:
                    raise ServiceNowError("no refresh token")
            except ServiceNowError:
                # refresh token expired: sign in again with the saved password
                tokens = oauth_password_grant(self.url, inst.client_id, secret, inst.username, decrypt(inst.password_enc), self.transport)
            save_tokens(inst, tokens)
            if self.db is not None:
                self.db.commit()
            return tokens["access_token"]

    # ----- requests -----
    def request(self, method: str, path: str, what: str, **kw) -> Any:
        url = path if path.startswith("http") else f"{self.url}{path}"
        headers = {"Accept": "application/json", **kw.pop("headers", {})}
        for attempt in (1, 2):
            auth = self._auth()
            try:
                with httpx.Client(timeout=TIMEOUT, transport=self.transport) as http:
                    r = http.request(method, url, headers={**headers, **auth.get("headers", {})}, auth=auth.get("auth"), **kw)
            except httpx.HTTPError as e:
                raise ServiceNowError(f"Couldn't reach {self.url}. Check the address and that the instance is awake.") from e
            if r.status_code == 401 and attempt == 1 and self.instance.auth_method == "oauth":
                self._access_token(force=True)
                continue
            if r.status_code >= 400:
                raise _http_problem(r, what)
            if r.status_code == 204 or not r.content:
                return None
            ctype = r.headers.get("content-type", "")
            if "json" not in ctype:
                if "<html" in r.text[:500].lower():
                    raise ServiceNowError("The instance returned a web page instead of data. It may be hibernating: wake it at developer.servicenow.com.")
                raise ServiceNowError(f"The instance returned something unexpected while trying to {what}.")
            return r.json()
        raise ServiceNowError("The instance rejected the session.")

    def query(self, table: str, query: str = "", fields: list[str] | None = None, limit: int = 100, display_value: str = "false") -> list[dict]:
        params: dict[str, Any] = {"sysparm_limit": limit, "sysparm_display_value": display_value, "sysparm_exclude_reference_link": "true"}
        if query:
            params["sysparm_query"] = query
        if fields:
            params["sysparm_fields"] = ",".join(fields)
        body = self.request("GET", f"/api/now/table/{table}", f"read {table}", params=params)
        return (body or {}).get("result") or []

    def get(self, table: str, sys_id: str, fields: list[str] | None = None) -> dict | None:
        params: dict[str, Any] = {"sysparm_exclude_reference_link": "true"}
        if fields:
            params["sysparm_fields"] = ",".join(fields)
        try:
            body = self.request("GET", f"/api/now/table/{table}/{sys_id}", f"read {table}", params=params)
        except ServiceNowError as e:
            if "couldn't find" in str(e):
                return None
            raise
        return (body or {}).get("result")

    def insert(self, table: str, data: dict) -> dict:
        return (self.request("POST", f"/api/now/table/{table}", f"create a record in {table}", json=data) or {}).get("result") or {}

    def update(self, table: str, sys_id: str, data: dict) -> dict:
        return (self.request("PATCH", f"/api/now/table/{table}/{sys_id}", f"update a record in {table}", json=data) or {}).get("result") or {}

    def delete(self, table: str, sys_id: str) -> None:
        self.request("DELETE", f"/api/now/table/{table}/{sys_id}", f"delete a record in {table}")

    # ----- reading the instance -----
    def whoami(self) -> InstanceInfo:
        inst = self.instance
        users = self.query("sys_user", f"user_name={inst.username}", ["sys_id", "name", "user_name"], limit=1)
        user = users[0] if users else {}
        roles: list[str] = []
        if user.get("sys_id"):
            rows = self.query("sys_user_has_role", f"user={user['sys_id']}^state=active", ["role"], limit=500, display_value="true")
            roles = sorted({str(r.get("role") or "") for r in rows if r.get("role")})
        release = None
        try:
            props = self.query("sys_properties", "name=glide.buildname^ORname=glide.war", ["name", "value"], limit=2)
            by = {p.get("name"): p.get("value") for p in props}
            release = by.get("glide.buildname") or by.get("glide.war")
        except ServiceNowError:
            release = None  # some users can't read properties; not needed to connect
        return InstanceInfo(url=self.url, release=release, user_sys_id=user.get("sys_id"), user_display_name=user.get("name"),
                            roles=roles, is_admin="admin" in roles)

    def table_schema(self, table: str) -> dict:
        """A table's label, the tables it extends, and its fields including inherited ones
        (sys_db_object for the hierarchy, sys_dictionary for the fields)."""
        objs = self.query("sys_db_object", f"name={table}", ["sys_id", "name", "label", "super_class", "sys_scope"], limit=1)
        if not objs:
            return {"table": table, "exists": False}
        chain, cur = [objs[0]], objs[0]
        while cur.get("super_class") and len(chain) < 6:  # incident -> task, cmdb_ci_server -> cmdb_ci_computer -> ...
            parent = self.query("sys_db_object", f"sys_id={cur['super_class']}", ["sys_id", "name", "label", "super_class"], limit=1)
            if not parent:
                break
            cur = parent[0]
            chain.append(cur)
        names = [t["name"] for t in chain]
        rows = self.query("sys_dictionary", f"nameIN{','.join(names)}^elementISNOTEMPTY^active=true",
                          ["name", "element", "column_label", "internal_type", "reference", "mandatory", "max_length"], limit=1000)
        fields: dict[str, dict] = {}
        for t in names:  # the table's own definition wins over the parent's
            for f in rows:
                if f.get("name") == t and f.get("element") not in fields:
                    fields[f["element"]] = {"name": f["element"], "label": f.get("column_label"), "type": f.get("internal_type"),
                                            "reference": f.get("reference") or None, "mandatory": f.get("mandatory") == "true",
                                            **({"from": t} if t != table else {})}
        return {"table": table, "exists": True, "label": chain[0].get("label"), "extends": names[1:],
                "fields": sorted(fields.values(), key=lambda f: f["name"])}

    def search_artifacts(self, type_: str, name_contains: str = "", table: str = "", limit: int = 50) -> dict:
        """Existing artifacts of one type (no scripts: read one with get_artifact)."""
        if type_ not in ARTIFACT_TABLES:
            raise ServiceNowError(f"Unknown artifact type {type_}. Use one of: {', '.join(ARTIFACT_TABLES)}.")
        sn_table, fields = ARTIFACT_TABLES[type_]
        name_field = SEARCH_FIELDS.get(type_, ("name", "table"))[0]
        table_field = SEARCH_FIELDS.get(type_, ("name", "table"))[1]
        q = []
        if name_contains:
            q.append(f"{name_field}LIKE{name_contains}")
        if table and table_field and type_ != "script_include":
            q.append(f"{table_field}={table}")
        q.append(f"ORDERBY{name_field}")
        listed = [f for f in fields if f != "script"]
        rows = self.query(sn_table, "^".join(q), ["sys_id", *listed], limit=limit, display_value="all")
        out = [{k: _value(v) for k, v in r.items()} for r in rows]
        return {"type": type_, "table": sn_table, "count": len(out), "records": out,
                **({"note": f"Showing the first {limit}. Narrow the search for more."} if len(out) >= limit else {})}

    MAX_INPUT_LOOKUPS = 5

    def flow_actions(self, name_contains: str = "", limit: int = 100, with_inputs: bool = False) -> dict:
        """The Flow Designer actions this instance actually has (`sys_hub_action_type_definition`).

        Which actions exist depends on the release and on which spokes are installed and licensed,
        so this has to be read from the instance rather than assumed. A flow design that names an
        action the instance doesn't have is wrong, and `ai/checks.py` uses this to say so.

        With `with_inputs`, the inputs of the first few matches are read too (`sys_hub_action_input`),
        so a design can name the real input fields instead of guessing them.
        """
        q = ["active=true"]
        if name_contains:
            q.append(f"nameLIKE{name_contains}")
        q.append("ORDERBYname")
        rows = self.query("sys_hub_action_type_definition", "^".join(q),
                          ["sys_id", "name", "internal_name", "description", "sys_scope"],
                          limit=limit, display_value="all")
        actions = [{k: _value(v) for k, v in r.items()} for r in rows]
        truncated = len(actions) >= limit
        if with_inputs:
            for a in actions[:self.MAX_INPUT_LOOKUPS]:
                a["inputs"] = self.flow_action_inputs(a.get("sys_id", ""))
        note = ""
        if truncated:
            note = f"Showing the first {limit}. Narrow the search for more."
        elif with_inputs and len(actions) > self.MAX_INPUT_LOOKUPS:
            note = f"Inputs read for the first {self.MAX_INPUT_LOOKUPS} only. Search for one action by name for the rest."
        return {"table": "sys_hub_action_type_definition", "count": len(actions), "actions": actions,
                **({"note": note} if note else {})}

    def flow_actions_named(self, names: list[str]) -> set[str]:
        """Which of these action names the instance has, lowercased.

        Asked by name rather than by listing everything: an instance with spokes installed has far
        more actions than any one page, so a fetch-all-then-compare reports whatever fell off the
        end as missing. This asks only about the names a design actually used.
        """
        wanted = [n.strip() for n in dict.fromkeys(names) if n and n.strip()][:40]
        if not wanted:
            return set()
        if any("," in n or "^" in n for n in wanted):           # would break the encoded query
            wanted = [n for n in wanted if "," not in n and "^" not in n]
        rows = self.query("sys_hub_action_type_definition", f"active=true^nameIN{','.join(wanted)}",
                          ["name"], limit=len(wanted) * 4, display_value="false")
        return {str(r.get("name", "")).strip().lower() for r in rows}

    def flow_action_inputs(self, action_sys_id: str) -> list[dict]:
        """The inputs one Flow Designer action takes, as the designer shows them.

        Input names are not guessable and differ between spokes and releases, so they are read
        from the instance. Unreadable inputs come back empty rather than failing the lookup —
        knowing the action exists is still worth having.
        """
        if not action_sys_id:
            return []
        try:
            rows = self.query("sys_hub_action_input", f"model={action_sys_id}^ORDERBYorder",
                              ["element", "label", "internal_type", "reference", "mandatory"],
                              limit=40, display_value="all")
        except ServiceNowError:
            return []
        out = []
        for r in rows:
            f = {k: _value(v) for k, v in r.items()}
            if str(f.get("element", "")).startswith("__snc"):
                continue        # the engine's own plumbing, not something a design fills in
            out.append({"name": f.get("element", ""), "label": f.get("label", ""),
                        "type": f.get("internal_type", ""),
                        **({"reference": f["reference"]} if f.get("reference") else {}),
                        "mandatory": str(f.get("mandatory", "")).lower() == "true"})
        return out

    def get_artifact(self, type_: str, sys_id: str) -> dict:
        if type_ not in ARTIFACT_TABLES:
            raise ServiceNowError(f"Unknown artifact type {type_}. Use one of: {', '.join(ARTIFACT_TABLES)}.")
        sn_table, fields = ARTIFACT_TABLES[type_]
        body = self.request("GET", f"/api/now/table/{sn_table}/{sys_id}", f"read {sn_table}",
                            params={"sysparm_fields": ",".join(["sys_id", *fields]), "sysparm_display_value": "all",
                                    "sysparm_exclude_reference_link": "true"})
        rec = (body or {}).get("result") or {}
        return {"type": type_, "table": sn_table, "record": {k: _value(v) for k, v in rec.items()}}


def _value(v):
    """display_value=all gives {value, display_value}: keep one string, both when they differ (references)."""
    if isinstance(v, dict) and "value" in v:
        val, disp = v.get("value"), v.get("display_value")
        return val if not disp or disp == val else f"{disp} ({val})"
    return v


def save_tokens(instance, tokens: dict) -> None:
    instance.access_token_enc = encrypt(tokens["access_token"])
    if tokens.get("refresh_token"):
        instance.refresh_token_enc = encrypt(tokens["refresh_token"])
    seconds = int(tokens.get("expires_in") or 1800)
    instance.token_expires_at = datetime.now(UTC) + timedelta(seconds=seconds)


# Artifact tables the chat can look up (Chunk 1: reading; Chunk 2+: building these)
ARTIFACT_TABLES = {
    "business_rule": ("sys_script", ["name", "collection", "when", "order", "active", "action_insert", "action_update", "action_delete", "action_query", "condition", "filter_condition", "script", "sys_scope"]),
    "script_include": ("sys_script_include", ["name", "api_name", "client_callable", "access", "active", "description", "script", "sys_scope"]),
    "client_script": ("sys_script_client", ["name", "table", "type", "field_name", "ui_type", "active", "script", "sys_scope"]),
    "ui_policy": ("sys_ui_policy", ["short_description", "table", "conditions", "on_load", "reverse_if_false", "run_scripts", "active", "sys_scope"]),
    "ui_action": ("sys_ui_action", ["name", "table", "action_name", "client", "onclick", "condition", "form_button", "list_button", "active", "script", "sys_scope"]),
    "notification": ("sysevent_email_action", ["name", "collection", "active", "action_insert", "action_update", "event_name", "condition", "recipient_fields", "subject", "sys_scope"]),
    "flow": ("sys_hub_flow", ["name", "table", "description", "active", "status", "sys_scope"]),
    "scheduled_job": ("sysauto_script", ["name", "run_type", "run_time", "run_dayofweek", "run_dayofmonth", "run_period", "active", "script", "sys_scope"]),
    "data_policy": ("sys_data_policy2", ["short_description", "model_table", "conditions", "apply_import_set", "apply_soap", "enforce_ui", "active", "sys_scope"]),
    "system_property": ("sys_properties", ["name", "value", "type", "description", "sys_scope"]),
    "event": ("sysevent_register", ["event_name", "table", "fired_by", "description", "sys_scope"]),
    "script_action": ("sysevent_script_action", ["name", "event_name", "order", "condition_script", "active", "script", "sys_scope"]),
    "table": ("sys_db_object", ["name", "label", "super_class", "is_extendable", "sys_scope"]),
    "field": ("sys_dictionary", ["name", "element", "column_label", "internal_type", "max_length", "reference", "mandatory", "active", "sys_scope"]),
}

# Which column holds an artifact's name, and which holds the table it belongs to. Most types use
# (name, table); these don't.
SEARCH_FIELDS = {
    "ui_policy": ("short_description", "table"),
    "business_rule": ("name", "collection"),
    "notification": ("name", "collection"),
    "data_policy": ("short_description", "model_table"),
    "event": ("event_name", "table"),
    "scheduled_job": ("name", ""),
    "system_property": ("name", ""),
    "script_action": ("name", ""),
    "table": ("name", ""),
    "field": ("element", "name"),
}

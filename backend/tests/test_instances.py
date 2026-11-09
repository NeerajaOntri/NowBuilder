"""Chunk 1: connecting a ServiceNow instance (basic and OAuth), checking it, and the chat reading it."""
import json

import pytest

from app.ai.skills import get_skills
from app.models import Instance
from app.services.servicenow import ServiceNowError, normalise_url

from .conftest import connect_instance


@pytest.mark.parametrize("raw,url", [
    ("dev410284", "https://dev410284.service-now.com"),
    ("dev410284.service-now.com", "https://dev410284.service-now.com"),
    ("https://DEV410284.service-now.com/nav_to.do?uri=incident.do", "https://dev410284.service-now.com"),
    ("https://acme.servicenowservices.com/", "https://acme.servicenowservices.com"),
])
def test_instance_addresses_are_normalised(raw, url):
    assert normalise_url(raw) == url


def test_http_addresses_are_refused():
    with pytest.raises(ServiceNowError, match="https"):
        normalise_url("http://dev1.service-now.com")


def test_connect_with_basic_auth_reads_the_user_roles_and_release(client, auth, snow):
    r = connect_instance(client, auth)
    assert r.status_code == 201, r.text
    inst = r.json()
    assert inst["url"] == "https://dev410284.service-now.com" and inst["status"] == "connected"
    assert inst["release"] == "Yokohama" and inst["user_display_name"] == "System Administrator"
    assert inst["roles"] == ["admin", "itil"] and inst["is_admin"] and inst["is_selected"]
    assert "password" not in json.dumps(inst).lower().replace("password_enc", "")
    assert [i["name"] for i in client.get("/api/instances", headers=auth).json()] == ["Dev"]


def test_wrong_password_is_a_plain_message(client, auth, snow):
    r = connect_instance(client, auth, password="nope")
    assert r.status_code == 400 and "didn't accept the username and password" in r.json()["detail"]
    assert client.get("/api/instances", headers=auth).json() == []


def test_hibernating_instance_says_so(client, auth, snow):
    snow.hibernating = True
    r = connect_instance(client, auth)
    assert r.status_code == 400 and "hibernating" in r.json()["detail"]


def test_a_user_without_admin_connects_with_a_warning(client, auth):
    from app.services import servicenow
    from .fake_snow import FakeInstance
    fake = FakeInstance(admin=False)
    servicenow.DEFAULT_TRANSPORT = fake.transport
    try:
        inst = connect_instance(client, auth).json()
    finally:
        servicenow.DEFAULT_TRANSPORT = None
    assert inst["status"] == "connected" and not inst["is_admin"] and "admin role" in inst["status_message"]


def test_connect_with_oauth_keeps_tokens_and_renews_them(client, auth, snow, monkeypatch):
    from app.routers import instances
    monkeypatch.setattr(instances, "oauth_tokens", lambda *a: __import__("app.services.servicenow", fromlist=["x"]).oauth_password_grant(*a))
    r = connect_instance(client, auth, auth_method="oauth", client_id="cid", client_secret="csecret")
    assert r.status_code == 201, r.text
    assert r.json()["auth_method"] == "oauth" and r.json()["client_id"] == "cid"
    # the access token is revoked: the client signs in again with the refresh token and carries on
    snow.tokens.clear()
    inst_id = r.json()["id"]
    assert client.post(f"/api/instances/{inst_id}/test", headers=auth).json()["status"] == "connected"
    assert len(snow.tokens) == 1


def test_oauth_with_a_wrong_secret_names_the_application_registry(client, auth, snow):
    r = connect_instance(client, auth, auth_method="oauth", client_id="cid", client_secret="wrong")
    assert r.status_code == 400 and "Application Registry" in r.json()["detail"]


def test_same_name_or_address_twice_is_refused(client, auth, snow):
    connect_instance(client, auth)
    assert connect_instance(client, auth, url="dev999").status_code == 409
    assert connect_instance(client, auth, name="Other").status_code == 409


def test_instance_limit_per_workspace(client, auth, snow):
    assert connect_instance(client, auth, name="A", url="inst-a").status_code == 201
    assert connect_instance(client, auth, name="B", url="inst-b").status_code == 201
    r = connect_instance(client, auth, name="C", url="inst-c")
    assert r.status_code == 409 and "at most 2 ServiceNow instances" in r.json()["detail"]


def test_select_rename_check_and_remove(client, auth, snow):
    a = connect_instance(client, auth, name="Dev", url="inst-a").json()
    b = connect_instance(client, auth, name="Test", url="inst-b", instance_type="Test").json()
    assert not b["is_selected"]
    assert client.post(f"/api/instances/{b['id']}/select", headers=auth).json()["is_selected"]
    assert client.patch(f"/api/instances/{a['id']}", json={"name": "Dev 2"}, headers=auth).json()["name"] == "Dev 2"
    snow.password = "changed"
    checked = client.post(f"/api/instances/{a['id']}/test", headers=auth).json()
    assert checked["status"] == "error" and "username and password" in checked["status_message"]
    fixed = client.patch(f"/api/instances/{a['id']}", json={"password": "changed"}, headers=auth)
    assert fixed.status_code == 200 and fixed.json()["status"] == "connected"
    assert client.delete(f"/api/instances/{b['id']}", headers=auth).status_code == 204
    assert [i["name"] for i in client.get("/api/instances", headers=auth).json()] == ["Dev 2"]


def test_password_is_stored_encrypted(client, auth, snow):
    connect_instance(client, auth)
    from app.db import SessionLocal
    with SessionLocal() as db:
        inst = db.query(Instance).one()
        assert inst.password_enc and "pw" != inst.password_enc


# ---------- the client reading the instance ----------

def _client(snow):
    from app.security import encrypt
    from app.services.servicenow import ServiceNowClient
    inst = Instance(name="Dev", instance_type="Development", url="https://dev1.service-now.com", auth_method="basic",
                    username="admin", password_enc=encrypt("pw"), client_id="")
    return ServiceNowClient(inst)


def test_table_schema_includes_inherited_fields(snow):
    s = _client(snow).table_schema("incident")
    assert s["exists"] and s["label"] == "Incident" and s["extends"] == ["task"]
    by = {f["name"]: f for f in s["fields"]}
    assert by["category"].get("from") is None and by["short_description"]["from"] == "task"
    assert by["caller_id"]["reference"] == "sys_user" and by["number"]["mandatory"]
    assert _client(snow).table_schema("u_nope") == {"table": "u_nope", "exists": False}


def test_search_and_read_artifacts(snow):
    snow.add("sys_script", name="Set priority", collection="incident", when="before", order="100", active="true", script="current.priority = 1;")
    snow.add("sys_script", name="Notify on close", collection="change_request", when="after", active="true", script="gs.eventQueue('x');")
    c = _client(snow)
    found = c.search_artifacts("business_rule", table="incident")
    assert found["count"] == 1 and found["records"][0]["name"] == "Set priority" and "script" not in found["records"][0]
    one = c.get_artifact("business_rule", found["records"][0]["sys_id"])
    assert one["record"]["script"] == "current.priority = 1;"
    assert c.search_artifacts("business_rule", name_contains="notify")["count"] == 1
    with pytest.raises(ServiceNowError, match="Unknown artifact type"):
        c.search_artifacts("widget")


def test_unreadable_table_is_a_plain_message(snow):
    snow.forbidden.add("sys_script")
    with pytest.raises(ServiceNowError, match="isn't allowed to read sys_script"):
        _client(snow).search_artifacts("business_rule")


# ---------- skills and prompts ----------

def test_chat_prompt_has_rules_standards_and_matching_skills():
    p = get_skills().build_prompt("chat", text="Write a before business rule on incident that sets the priority")
    assert p.skills[0] == "servicenow-development-standards" and "servicenow-business-rules" in p.skills
    assert "nowBuilder: how you work in the chat" in p.system and "| business_rule | Business rule | sys_script |" in p.system
    assert {"get_table_schema", "search_instance_artifacts", "get_instance_artifact", "propose_plan"} <= {t["name"] for t in p.tools}


def test_every_artifact_type_points_at_real_skills():
    s = get_skills()
    names = set(s.names())
    assert len(names) == 32
    for t, d in s.artifact_types().items():
        assert set(d["skills"]) <= names, t


# ---------- the chat reads the instance ----------

class ScriptedLLM:
    """Plays back model turns: each is a list of content blocks."""

    def __init__(self, turns):
        self.turns, self.seen = list(turns), []

    def stream(self, system, context, messages, tools, **kw):
        self.seen.append({"system": system, "context": context, "messages": list(messages)})
        content = self.turns.pop(0)
        for b in content:
            if b["type"] == "text":
                yield {"kind": "text", "delta": b["text"]}
        stop = "tool_use" if any(b["type"] == "tool_use" for b in content) else "end_turn"
        yield {"kind": "message", "content": content, "stop_reason": stop, "usage": {}}


def _ready_ai(client, auth, monkeypatch, llm):
    from app.routers import chats
    from app.services import ai_provider
    monkeypatch.setattr(ai_provider, "verify", lambda *a, **k: None, raising=False)
    from app.db import SessionLocal
    from app.models import AIProviderConfig, Membership
    from app.security import encrypt
    me = client.get("/api/auth/me", headers=auth).json()
    with SessionLocal() as db:
        ws = db.query(Membership).filter_by(user_id=me["id"]).one().workspace_id
        db.add(AIProviderConfig(user_id=me["id"], workspace_id=ws, provider="anthropic", model="m", api_key_enc=encrypt("k"), api_key_last4="k", verified=True))
        db.commit()
    monkeypatch.setattr(chats, "llm_factory", lambda cfg: llm)


def _events(r):
    return [json.loads(line[6:]) for line in r.text.split("\n") if line.startswith("data: ")]


def test_chat_reads_the_instance_before_answering(client, auth, snow, monkeypatch):
    snow.add("sys_script", name="Set priority", collection="incident", when="before", active="true", script="current.priority = 1;")
    connect_instance(client, auth)
    llm = ScriptedLLM([
        [{"type": "tool_use", "id": "t1", "name": "search_instance_artifacts", "input": {"type": "business_rule", "table": "incident"}}],
        [{"type": "text", "text": "There is one business rule on incident: Set priority (before)."}],
    ])
    _ready_ai(client, auth, monkeypatch, llm)
    chat = client.post("/api/chats", headers=auth).json()
    r = client.post(f"/api/chats/{chat['id']}/messages", data={"text": "Which business rules run on incident?"}, headers=auth)
    ev = _events(r)
    assert {"type": "status", "text": "Looking for existing business rules on incident"} in ev
    done = ev[-1]
    assert done["type"] == "done" and "Set priority" in done["message"]["content"]
    assert done["message"]["activity"] == ["Looking for existing business rules on incident"]
    tool_result = llm.seen[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and "Set priority" in tool_result["content"]
    assert "Connected instance: Dev: Development instance at https://dev410284.service-now.com, release Yokohama" in llm.seen[0]["context"]
    assert "servicenow-business-rules" in llm.seen[0]["system"]
    saved = client.get(f"/api/chats/{chat['id']}", headers=auth).json()
    assert [m["role"] for m in saved["messages"]] == ["user", "assistant"] and saved["plans"] == []


def test_chat_without_an_instance_tells_the_model(client, auth, monkeypatch):
    llm = ScriptedLLM([
        [{"type": "tool_use", "id": "t1", "name": "get_table_schema", "input": {"tables": ["incident"]}}],
        [{"type": "text", "text": "Connect an instance first."}],
    ])
    _ready_ai(client, auth, monkeypatch, llm)
    chat = client.post("/api/chats", headers=auth).json()
    client.post(f"/api/chats/{chat['id']}/messages", data={"text": "fields on incident?"}, headers=auth)
    result = llm.seen[1]["messages"][-1]["content"][0]
    assert result["is_error"] and "No ServiceNow instance is connected" in result["content"]
    assert "Connected instance: none" in llm.seen[0]["context"]

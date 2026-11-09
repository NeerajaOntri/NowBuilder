"""Now Assist-style delivery: a prompt becomes a plan, and a plan that passes the checks is deployed
straight into the connected instance (update set for Table API artifacts, ServiceNow SDK for flows)."""
import json

import pytest

from app.ai.artifacts import to_records
from app.services import ai_provider, sdk_deploy

from .conftest import connect_instance
from .test_chat import events, send, text_turn, tool_turn, use_llm
from .test_plans import BR, json_turn, one_rule, plan_turn


@pytest.fixture(autouse=True)
def auto_deploy_on(monkeypatch):
    """These tests are about automatic deployment, which is off by default (Deploy button only)."""
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "auto_deploy", True)


@pytest.fixture
def auto(client, auth, snow, monkeypatch, auto_deploy_on):
    """A verified AI provider and a Development instance with automatic deployment on."""
    monkeypatch.setattr(ai_provider, "verify", lambda *a: ai_provider.VerifyResult(True, "ok"))
    client.put("/api/settings/ai-provider", json={"provider": "anthropic", "model": "claude-sonnet-5-5",
                                                  "api_key": "sk-ant-test-1234567890"}, headers=auth)
    r = connect_instance(client, auth, url="dev410284", auto_deploy=True)
    assert r.status_code == 201 and r.json()["auto_deploy"] is True
    return auth


def ask(client, auth, monkeypatch, turns, text="VIP callers should get priority 1"):
    llm = use_llm(monkeypatch, turns)
    chat = client.post("/api/chats", headers=auth).json()
    evs = events(send(client, auth, chat["id"], text))
    plan = client.get(f"/api/chats/{chat['id']}", headers=auth).json()["plans"][0]
    return llm, evs, plan


def tool_results(llm):
    out = []
    for call in llm.calls:
        for m in call["messages"]:
            if m["role"] == "user" and isinstance(m["content"], list):
                out += [b["content"] for b in m["content"] if b.get("type") == "tool_result"]
    return out


def test_a_prompt_is_planned_checked_and_deployed_into_the_instance(client, auto, snow, monkeypatch):
    llm, evs, plan = ask(client, auto, monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("Done.")])

    [rule] = snow.tables["sys_script"]
    assert rule["name"] == BR["record"]["name"] and rule["advanced"] == "true"
    [update_set] = snow.tables["sys_update_set"]
    assert update_set["name"] == "nowBuilder - VIP incidents"
    assert plan["status"] == "deployed" and plan["deployment"]["status"] == "deployed"
    assert plan["approval"]["auto"] is True
    assert plan["components"][0]["deploy"]["status"] == "deployed"
    # the browser saw the card update, and the model was told what the instance answered
    assert any(e["type"] == "status" and "update set" in e["text"] for e in evs)
    result = json.loads(tool_results(llm)[-1])
    row = result["deployment"]["rows"][0]
    assert row["deploy_status"] == "deployed" and row["sys_id"] == rule["sys_id"]
    assert result["deployment"]["instance"] == "https://dev410284.service-now.com"


def test_a_row_with_problems_is_not_deployed(client, auto, snow, monkeypatch):
    bad = {**BR, "record": {**BR["record"], "condition": "current.u_phantom == true"}}
    # the automatic fix pass gets no usable answer, so the row stays held
    llm, evs, plan = ask(client, auto, monkeypatch,
                         [plan_turn(one_rule()), json_turn(bad), text_turn("not json"), text_turn("not json"),
                          text_turn("not json"), text_turn("Held.")])
    assert "sys_script" not in snow.tables or not snow.tables["sys_script"]
    assert plan["deployment"] is None
    rows = json.loads(tool_results(llm)[-1])["deployment"]["rows"]
    assert rows[0]["deploy_status"].startswith("held")


def test_production_never_deploys_on_its_own(client, auth, snow, monkeypatch):
    monkeypatch.setattr(ai_provider, "verify", lambda *a: ai_provider.VerifyResult(True, "ok"))
    client.put("/api/settings/ai-provider", json={"provider": "anthropic", "model": "claude-sonnet-5-5",
                                                  "api_key": "sk-ant-test-1234567890"}, headers=auth)
    inst = connect_instance(client, auth, instance_type="Production", auto_deploy=True).json()
    assert inst["auto_deploy"] is False
    llm, _, plan = ask(client, auth, monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("Review it.")])
    assert "sys_script" not in snow.tables or not snow.tables["sys_script"]
    assert plan["status"] == "draft"
    assert "production instance" in tool_results(llm)[-1]


def test_asking_in_the_chat_deploys_a_plan_that_is_on_screen(client, auth, snow, monkeypatch):
    """Automatic deployment off: the plan waits, then 'deploy it' in the chat deploys it."""
    monkeypatch.setattr(ai_provider, "verify", lambda *a: ai_provider.VerifyResult(True, "ok"))
    client.put("/api/settings/ai-provider", json={"provider": "anthropic", "model": "claude-sonnet-5-5",
                                                  "api_key": "sk-ant-test-1234567890"}, headers=auth)
    inst = connect_instance(client, auth, auto_deploy=False).json()
    llm, _, plan = ask(client, auth, monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("Ready.")])
    assert plan["status"] == "draft" and not snow.tables.get("sys_script")

    # the member turns it on for this instance and asks in the same chat
    client.patch(f"/api/instances/{inst['id']}", json={"auto_deploy": True}, headers=auth)
    llm = use_llm(monkeypatch, [tool_turn("deploy_plan", {}), text_turn("It's in.")])
    chat_id = plan["chat_id"]
    evs = events(send(client, auth, chat_id, "deploy it"))
    assert evs[-1]["type"] == "done"
    assert len(snow.tables["sys_script"]) == 1
    assert json.loads(tool_results(llm)[-1])["deployment"]["rows"][0]["deploy_status"] == "deployed"


FLOW_ROWS = [
    {"id": "c1", "type": "notification", "name": "P1 opened", "table": "incident", "purpose": "email the caller"},
    {"id": "c2", "type": "flow", "name": "P1 escalation", "table": "incident", "purpose": "escalate P1s",
     "dependsOn": ["c1"]},
]
NOTIFICATION = {"record": {
    "name": "P1 opened", "collection": "incident", "active": "true", "action_insert": "false",
    "action_update": "false", "event_name": "x.p1.opened", "condition": "", "recipient_fields": "caller_id",
    "recipient_users": "", "recipient_groups": "", "subject": "P1 ${number}", "message_html": "<p>${URI_REF}</p>",
    "weight": "0", "send_self": "false", "exclude_delegates": "false", "content_type": "text/html"}}
FLOW = {"record": {"name": "P1 escalation", "table": "incident", "trigger": "Created", "trigger_condition": "priority=1",
                   "run_trigger": "once", "run_as": "System user", "schedule_time": "", "description": "Escalate P1s."},
        "steps": [{"step": 1, "kind": "action", "name": "Send Notification", "detail": "Send c1.",
                   "inputs": {"table_name": "incident", "record": "{{trigger.current.sys_id}}",
                              "notification": "{{plan.c1}}"}}]}


def test_without_an_sdk_project_a_flow_stays_a_design_and_says_so(client, auto, snow, monkeypatch):
    llm, _, plan = ask(client, auto, monkeypatch, [plan_turn(FLOW_ROWS), json_turn(NOTIFICATION), json_turn(FLOW),
                                                   text_turn("Done.")])
    by_id = {c["id"]: c for c in plan["components"]}
    assert by_id["c1"]["deploy"]["status"] == "deployed"
    assert snow.tables["sysevent_email_action"][0]["generation_type"] == "event"
    assert by_id["c2"]["deploy"]["status"] == "design only"
    assert "NOWBUILDER_SDK_AUTO_SETUP" in by_id["c2"]["deploy"]["message"]


def test_with_an_sdk_project_the_flow_is_installed_and_read_back(client, auto, snow, monkeypatch):
    installed = {}

    def fake_install(generated, *, install, instance_url, username, password, client=None, on_status=None,
                     application="scoped", release=""):
        installed.update(generated=generated, url=instance_url, user=username, pw=password, install=install)
        return {"status": "installed", "installed": True}

    monkeypatch.setattr(sdk_deploy, "configured", lambda: True)
    monkeypatch.setattr(sdk_deploy, "run_scoped_flow", fake_install)
    monkeypatch.setattr(sdk_deploy, "read_back_flow", lambda client, name: {
        "sys_id": "f" * 32, "active": True, "status": "published", "url": "https://x/flow"})
    llm, _, plan = ask(client, auto, monkeypatch, [plan_turn(FLOW_ROWS), json_turn(NOTIFICATION), json_turn(FLOW),
                                                   text_turn("Done.")])
    notification_id = snow.tables["sysevent_email_action"][0]["sys_id"]
    # the flow points at the notification that was just deployed, by its real sys_id
    assert installed["generated"]["steps"][0]["inputs"]["notification"] == notification_id
    assert installed["url"] == "https://dev410284.service-now.com" and installed["user"] == "admin"
    assert installed["pw"] == "pw" and installed["install"] is True
    flow = {c["id"]: c for c in plan["components"]}["c2"]
    assert flow["deploy"]["status"] == "deployed" and flow["deploy"]["active"] is True
    rows = {r["id"]: r for r in json.loads(tool_results(llm)[-1])["deployment"]["rows"]}
    assert rows["c2"]["deploy_status"] == "deployed" and rows["c2"]["sys_id"] == "f" * 32


def test_no_instance_is_built_in(client, auth):
    """Which instance nowBuilder works in comes from the connection, never from a fixed setting."""
    out = client.get("/api/instances/defaults", headers=auth).json()
    assert out["url"] == ""


def test_switching_instance_moves_the_chat_to_the_new_one(client, auth, snow, monkeypatch):
    """Connect a second instance and select it: the same chat now reads and deploys there,
    with no change to .env."""
    monkeypatch.setattr(ai_provider, "verify", lambda *a: ai_provider.VerifyResult(True, "ok"))
    client.put("/api/settings/ai-provider", json={"provider": "anthropic", "model": "claude-sonnet-5-5",
                                                  "api_key": "sk-ant-test-1234567890"}, headers=auth)
    first = connect_instance(client, auth, name="First", url="dev410284", auto_deploy=True).json()
    second = connect_instance(client, auth, name="Second", url="dev77777", auto_deploy=True).json()
    llm = use_llm(monkeypatch, [text_turn("Hi.")])
    chat = client.post("/api/chats", headers=auth).json()
    send(client, auth, chat["id"], "hi")
    assert "dev410284" in llm.calls[-1]["context"]

    client.post(f"/api/instances/{second['id']}/select", headers=auth)
    llm = use_llm(monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("Done.")])
    send(client, auth, chat["id"], "VIP callers should get priority 1")
    assert "dev77777" in llm.calls[0]["context"] and "dev410284" not in llm.calls[0]["context"]
    plan = client.get(f"/api/chats/{chat['id']}", headers=auth).json()["plans"][0]
    assert plan["instance_id"] == second["id"] and plan["deployment"]["instance_id"] == second["id"]
    assert first["id"] != second["id"]


# ---------- what ServiceNow needs on each record ----------

def test_records_carry_the_fields_servicenow_needs():
    [br] = to_records("business_rule", BR)
    assert br["fields"]["advanced"] == "true"
    [n] = to_records("notification", NOTIFICATION)
    assert n["fields"]["generation_type"] == "event"
    by_flow = {"record": {**NOTIFICATION["record"], "event_name": "", "triggered_by_flow": "true"}}
    assert to_records("notification", by_flow)[0]["fields"]["generation_type"] == "triggered"
    assert "triggered_by_flow" not in to_records("notification", by_flow)[0]["fields"]
    from app.ai.artifacts import check
    assert check("notification", by_flow) == []
    n2 = to_records("notification", {"record": {**NOTIFICATION["record"], "event_name": "", "action_insert": "true"}})
    assert n2[0]["fields"]["generation_type"] == "engine"
    policy = {"record": {"short_description": "x", "table": "incident", "conditions": "", "on_load": "true",
                         "reverse_if_false": "true", "run_scripts": "false", "active": "true"},
              "actions": [{"field": "category", "mandatory": "true", "visible": "true", "disabled": "false"}]}
    assert to_records("ui_policy", policy)[1]["fields"]["table"] == "incident"
    si = to_records("script_include", {"record": {"name": "A", "api_name": "global.A", "client_callable": "false",
                                                  "access": "public", "active": "true", "description": "d"},
                                       "script": "var A = Class.create();"})
    assert "api_name" not in si[0]["fields"]


# ---------- the types added on 3 Nov: scheduled jobs, data policies, properties, events ----------

def _example(type_):
    import re
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "skills" / "nowbuilder" / "examples" / f"{type_}.md").read_text()
    return json.loads(re.findall(r"```json\n(.*?)```", text, re.S)[0])


def test_a_nightly_job_with_its_setting_is_planned_and_deployed(client, auto, snow, monkeypatch):
    rows = [{"id": "c1", "type": "system_property", "name": "incident.autoclose.days", "purpose": "the threshold"},
            {"id": "c2", "type": "scheduled_job", "name": "Close resolved incidents", "purpose": "nightly",
             "dependsOn": ["c1"]}]
    llm, _, plan = ask(client, auto, monkeypatch,
                       [plan_turn(rows), json_turn(_example("system_property")), json_turn(_example("scheduled_job")),
                        text_turn("Done.")], text="Close incidents resolved for 7 days, every night at 1 AM")
    assert plan["deployment"]["status"] == "deployed", plan["deployment"]
    [job] = snow.tables["sysauto_script"]
    assert job["run_type"] == "daily" and job["run_time"] == "1970-01-01 01:00:00"
    assert "run_dayofweek" not in job                                   # empty settings aren't written
    assert any(p["name"] == "incident.autoclose.days" and p["value"] == "7" for p in snow.tables["sys_properties"])
    assert {r["deploy_status"] for r in json.loads(tool_results(llm)[-1])["deployment"]["rows"]} == {"deployed"}


def test_a_data_policy_takes_its_field_rules_with_it(client, auto, snow, monkeypatch):
    rows = [{"id": "c1", "type": "data_policy", "name": "Close notes required", "table": "incident", "purpose": "p"}]
    _, _, plan = ask(client, auto, monkeypatch, [plan_turn(rows), json_turn(_example("data_policy")), text_turn("Done.")],
                     text="close notes mandatory when resolved, for imports too")
    [policy] = snow.tables["sys_data_policy2"]
    rules = snow.tables["sys_data_policy_rule"]
    assert policy["model_table"] == "incident" and len(rules) == 2
    assert all(r["sys_data_policy"] == policy["sys_id"] and r["table"] == "incident" for r in rules)


def test_an_event_and_its_script_action_deploy_in_order(client, auto, snow, monkeypatch):
    rows = [{"id": "c1", "type": "event", "name": "incident.p1.escalated", "table": "incident", "purpose": "p"},
            {"id": "c2", "type": "script_action", "name": "Note P1 escalation", "purpose": "p", "dependsOn": ["c1"]}]
    _, _, plan = ask(client, auto, monkeypatch,
                     [plan_turn(rows), json_turn(_example("event")), json_turn(_example("script_action")), text_turn("Done.")],
                     text="fire an event on P1 escalation and note it")
    assert plan["deployment"]["status"] == "deployed"
    assert snow.tables["sysevent_register"][-1]["event_name"] == "incident.p1.escalated"
    assert snow.tables["sysevent_script_action"][0]["event_name"] == "incident.p1.escalated"


@pytest.mark.parametrize("type_,bad,expected", [
    ("scheduled_job", {"run_type": "weekly", "run_dayofweek": ""}, "run_dayofweek"),
    ("scheduled_job", {"run_type": "periodically", "run_period": ""}, "run_period"),
    ("system_property", {"name": "AutoCloseDays"}, "dot.notation"),
    ("system_property", {"type": "boolean", "value": "yes"}, "true or false"),
    ("event", {"event_name": "P1 escalated"}, "dot.notation"),
])
def test_new_types_reject_settings_servicenow_would_not_accept(type_, bad, expected):
    from app.ai.artifacts import check
    data = _example(type_)
    data["record"] = {**data["record"], **bad}
    assert expected in " ".join(check(type_, data))


def test_design_settings_are_not_reported_as_missing_columns():
    """triggered_by_flow is nowBuilder's own setting (it becomes generation_type); the column check
    looks at what is written, so a real instance doesn't reject the notification over it."""
    from app.ai import checks

    class Reader:
        def schema(self, table):
            return {"exists": True, "fields": [{"name": n} for n in (
                "name", "collection", "active", "action_insert", "action_update", "event_name", "condition",
                "recipient_fields", "recipient_users", "recipient_groups", "subject", "message_html", "weight",
                "send_self", "exclude_delegates", "content_type", "generation_type")]}

    record = {**NOTIFICATION["record"], "event_name": "", "triggered_by_flow": "true"}
    assert checks.own_table_problems("notification", record, Reader()) == []

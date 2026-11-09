"""Chunk 2: the chat proposes a plan, nowBuilder generates each record and script.

The model is scripted (tests/test_chat.py's ScriptedLLM); ServiceNow is the fake instance.
"""
import json

import pytest

from app.ai import artifacts, planning
from app.ai.skills import get_skills
from app.routers import chats

from .test_chat import ScriptedLLM, events, ready, send, text_turn, tool_turn, use_llm  # noqa: F401

# ---------- the pieces the model has to produce ----------

VIP_SCRIPT = ("(function executeRule(current, previous) {\n"
              "    current.setValue('priority', 1);\n"
              "})(current, previous);")

BR = {
    "record": {"name": "VIP callers get priority 1", "collection": "incident", "when": "before", "order": "100",
               "active": "true", "action_insert": "true", "action_update": "true", "action_delete": "false",
               "action_query": "false", "condition": "current.caller_id.vip == true", "filter_condition": "",
               "description": "Raises priority for VIP callers."},
    "script": VIP_SCRIPT,
}

SI = {
    "record": {"name": "VipUtils", "api_name": "global.VipUtils", "client_callable": "false", "access": "package_private",
               "active": "true", "description": "Shared VIP helpers."},
    "script": ("var VipUtils = Class.create();\n"
               "VipUtils.prototype = {\n"
               "    initialize: function () {},\n"
               "    isVip: function (userId) { return false; },\n"
               "    type: 'VipUtils'\n};"),
}


def plan_turn(components, tid="p1", **top):
    """A model turn that calls propose_plan, streaming the rows in as partial input first."""
    args = {"title": "VIP incidents", "summary": "Raise priority for VIP callers.", "story_points": 2,
            "assumptions": ["sys_user.vip marks VIPs"], "components": components, **top}
    partial = {"title": args["title"], "components": [{k: c[k] for k in ("id", "type", "name") if k in c} for c in components]}
    return [
        {"kind": "tool_input", "index": 0, "id": tid, "name": "propose_plan", "snapshot": {"title": args["title"]}},
        {"kind": "tool_input", "index": 0, "id": tid, "name": "propose_plan", "snapshot": partial},
        {"kind": "message", "content": [{"type": "tool_use", "id": tid, "name": "propose_plan", "input": args}],
         "stop_reason": "tool_use"},
    ]


def json_turn(data):
    """A generation turn: the model replies with one JSON object."""
    return text_turn(json.dumps(data))


def one_rule(**over):
    return [{"id": "c1", "type": "business_rule", "name": "VIP priority", "table": "incident",
             "purpose": "before update on incident when the caller is VIP", **over}]


def plan_of(client, auth, chat_id):
    return client.get(f"/api/chats/{chat_id}", headers=auth).json()["plans"]


# ---------- proposing and generating ----------

def test_plan_streams_rows_then_generates_each_artifact(client, ready, monkeypatch):
    llm = use_llm(monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("The rule is ready to copy.")])
    chat = client.post("/api/chats", headers=ready).json()
    evs = events(send(client, ready, chat["id"], "VIP callers should get priority 1"))

    kinds = [e["type"] for e in evs]
    assert kinds[0] == "start" and kinds[-1] == "done"
    # the card fills in while the model writes, then the plan is saved and each row is generated
    assert kinds.index("plan_draft") < kinds.index("plan") < kinds.index("component") < kinds.index("plan_done")
    draft = next(e for e in evs if e["type"] == "plan_draft")
    assert draft["plan"]["drafting"] and draft["plan"]["title"] == "VIP incidents"

    done = next(e for e in evs if e["type"] == "plan_done")["plan"]
    assert done["status"] == "draft" and done["busy"] is None and done["story_points"] == 2
    [c] = done["components"]
    assert c["status"] == "ready" and c["generated"]["record"]["when"] == "before"
    assert c["generated"]["script"] == VIP_SCRIPT
    assert c["name"] == "VIP callers get priority 1"      # the generated record names the row

    # the statuses the user sees: generating, then ready
    assert [e["component"]["status"] for e in evs if e["type"] == "component"] == ["generating", "ready"]
    # the model is told the plan exists, not the scripts
    result = llm.calls[2]["messages"][-1]["content"][0]
    assert not result.get("is_error") and done["id"] in result["content"] and VIP_SCRIPT not in result["content"]


def test_plan_is_saved_on_the_message_and_comes_back_with_the_chat(client, ready, monkeypatch):
    use_llm(monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("Ready.")])
    chat = client.post("/api/chats", headers=ready).json()
    send(client, ready, chat["id"], "VIP callers should get priority 1")

    full = client.get(f"/api/chats/{chat['id']}", headers=ready).json()
    [plan] = full["plans"]
    assert full["messages"][-1]["plan_id"] == plan["id"]
    assert plan["components"][0]["generated"]["record"]["collection"] == "incident"
    assert client.get(f"/api/plans/{plan['id']}", headers=ready).json()["title"] == "VIP incidents"


def test_generation_prompt_carries_the_type_skills_and_the_schema(client, ready, monkeypatch):
    llm = use_llm(monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("Ready.")])
    chat = client.post("/api/chats", headers=ready).json()
    send(client, ready, chat["id"], "VIP callers should get priority 1")

    gen = llm.calls[1]
    assert '<skill name="servicenow-business-rules">' in gen["system"]
    assert "Writing one artifact" in gen["system"] and '"action_insert"' in gen["system"]
    assert {"get_table_schema", "search_instance_artifacts", "get_instance_artifact", "get_skill_file"} <= set(gen["tools"])
    assert "VIP callers should get priority 1" in gen["messages"][0]["content"]   # the user's own words
    assert "Title: VIP incidents" in gen["context"] and "Connected instance: Dev" in gen["context"]


def test_dependencies_decide_the_order_and_the_name_is_passed_on(client, ready, monkeypatch):
    components = [
        {"id": "c1", "type": "business_rule", "name": "VIP priority", "table": "incident",
         "purpose": "calls the helper", "dependsOn": ["c2"]},
        {"id": "c2", "type": "script_include", "name": "VIP helper", "purpose": "shared VIP logic"},
    ]
    llm = use_llm(monkeypatch, [plan_turn(components), json_turn(SI), json_turn(BR), text_turn("Both ready.")])
    chat = client.post("/api/chats", headers=ready).json()
    evs = events(send(client, ready, chat["id"], "VIP priority with a helper"))

    # the script include is generated first, and the rule is told what it was called
    started = [e["component"]["id"] for e in evs if e["type"] == "component" and e["component"]["status"] == "generating"]
    assert started == ["c2", "c1"]
    assert "VipUtils" in llm.calls[2]["context"]
    assert [c["status"] for c in next(e for e in evs if e["type"] == "plan_done")["plan"]["components"]] == ["ready", "ready"]


def test_a_failed_artifact_leaves_the_rest_of_the_plan(client, ready, monkeypatch):
    bad = dict(BR, record=dict(BR["record"], when="before"), script="current.update();")  # breaks a rule in the skills
    use_llm(monkeypatch, [plan_turn(one_rule()), json_turn(bad), json_turn(bad), json_turn(bad), text_turn("One didn't work.")])
    chat = client.post("/api/chats", headers=ready).json()
    evs = events(send(client, ready, chat["id"], "VIP callers should get priority 1"))

    [c] = next(e for e in evs if e["type"] == "plan_done")["plan"]["components"]
    assert c["status"] == "failed" and "didn't pass" in c["error"]
    assert next(e for e in evs if e["type"] == "done")["message"]["plan_id"]   # the plan is still saved


def test_a_question_makes_no_plan(client, ready, monkeypatch):
    use_llm(monkeypatch, [text_turn("Before rules change the record in place.")])
    chat = client.post("/api/chats", headers=ready).json()
    evs = events(send(client, ready, chat["id"], "before vs after?"))
    assert not [e for e in evs if e["type"].startswith("plan")]
    assert plan_of(client, ready, chat["id"]) == []


def test_a_plan_with_no_usable_rows_is_reported_not_saved(client, ready, monkeypatch):
    llm = use_llm(monkeypatch, [plan_turn([{"id": "c1", "type": "acl", "name": "Read rule", "purpose": "x"}]),
                                text_turn("nowBuilder can't build ACLs.")])
    chat = client.post("/api/chats", headers=ready).json()
    evs = events(send(client, ready, chat["id"], "build an ACL"))
    assert [e for e in evs if e["type"] == "error"] and plan_of(client, ready, chat["id"]) == []
    assert llm.calls[1]["messages"][-1]["content"][0]["is_error"]


def test_another_members_plan_is_not_readable(client, ready, auth):
    other = client.post("/api/auth/register", json={"first_name": "Sam", "last_name": "Ray", "email": "sam@example.com",
                                                    "password": "secret123"}).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get("/api/plans/does-not-exist", headers=headers).status_code == 404


# ---------- the proposal is cleaned before it is saved ----------

def test_clean_proposal_drops_unknown_types_and_fixes_ids():
    out = planning.clean_proposal({
        "title": "T", "summary": "S", "story_points": 99,
        "components": [
            {"id": "c1", "type": "business_rule", "name": "A", "purpose": "p", "dependsOn": ["c1", "nope"]},
            {"id": "c1", "type": "script_include", "name": "B", "purpose": "p"},     # duplicate id
            {"id": "c3", "type": "flow_designer", "name": "C", "purpose": "p"},      # not a type we build
            {"id": "c4", "type": "ui_action", "name": "D", "purpose": "p", "action": "update"},  # update without a sys_id
        ],
    })
    assert [c["id"] for c in out["components"]] == ["c1", "c1_", "c4"]
    assert out["components"][0]["dependsOn"] == []        # itself and the unknown id are dropped
    assert out["components"][2]["action"] == "create"
    assert out["story_points"] == 0                        # 99 isn't a Fibonacci estimate


def test_draft_needs_something_to_show():
    assert planning.draft_from_snapshot({}) is None
    assert planning.draft_from_snapshot({"components": [{"type": "business_rule"}]})["components"][0]["name"] == ""


# ---------- what a generated artifact has to look like ----------

@pytest.mark.parametrize("type_,data,expected", [
    ("business_rule", BR, []),
    ("business_rule", {**BR, "record": {**BR["record"], "action_insert": "false", "action_update": "false"}},
     ["at least one of insert"]),
    # what a script may *do* is checked in ai/checks.py (tests/test_checks.py), not here
    ("business_rule", {**BR, "record": {**BR["record"], "when": "after", "action_query": "true"}},
     ["query business rule runs before the query"]),
    ("business_rule", {**BR, "script": "current.setValue('priority', 1);"}, ["Wrap the business rule's script"]),
    ("script_include", SI, []),
    ("script_include", {**SI, "record": {**SI["record"], "name": "Other"}}, ["they must match"]),
    ("script_include", {**SI, "record": {**SI["record"], "client_callable": "true"}}, ["AbstractAjaxProcessor"]),
    ("client_script", {"record": {"name": "n", "table": "incident", "type": "onChange", "field_name": "category",
                                  "ui_type": "10", "active": "true", "isolate_script": "true", "description": "d"},
                       "script": "function onChange(control, oldValue, newValue, isLoading) { }"}, []),
    ("client_script", {"record": {"name": "n", "table": "incident", "type": "onChange", "field_name": "",
                                  "ui_type": "10", "active": "true", "isolate_script": "true", "description": "d"},
                       "script": "function onChange() { var gr = new GlideRecord('sys_user'); }"},
     ["needs the field that triggers it", "must not use GlideRecord"]),
    ("ui_policy", {"record": {"short_description": "s", "table": "incident", "conditions": "", "on_load": "true",
                              "reverse_if_false": "true", "run_scripts": "false", "active": "true"},
                   "actions": [{"field": "u_x", "mandatory": "true", "visible": "false", "disabled": "ignore"}]},
     ["hidden field mandatory"]),
    ("ui_action", {"record": {"name": "Escalate", "table": "incident", "action_name": "escalate", "condition": "",
                              "form_button": "false", "form_link": "false", "list_button": "false", "client": "false",
                              "onclick": "", "order": "100", "active": "true", "comments": "c"}, "script": "x"},
     ["has to appear somewhere"]),
])
def test_check_catches_records_that_contradict_the_script(type_, data, expected):
    problems = " | ".join(artifacts.check(type_, data))
    for want in expected:
        assert want in problems, problems
    if not expected:
        assert problems == ""


def test_to_records_puts_the_script_in_and_lists_child_records():
    [main] = artifacts.to_records("business_rule", BR)
    assert main["table"] == "sys_script" and main["fields"]["script"] == VIP_SCRIPT

    policy = {"record": {"short_description": "s", "table": "incident", "conditions": "", "on_load": "true",
                         "reverse_if_false": "true", "run_scripts": "false", "active": "true"},
              "actions": [{"field": "u_vendor", "mandatory": "true", "visible": "true", "disabled": "false"}]}
    rows = artifacts.to_records("ui_policy", policy)
    assert [r["table"] for r in rows] == ["sys_ui_policy", "sys_ui_policy_action"]
    assert "script" not in rows[0]["fields"] and rows[1]["parent_field"] == "ui_policy"


def test_every_artifact_type_has_a_schema_and_skills():
    manifest_types = get_skills().artifact_types()
    assert set(manifest_types) == set(artifacts.TYPES)
    for name, spec in artifacts.SPECS.items():
        assert spec.table == manifest_types[name]["table"]
        schema = spec.schema()
        assert schema["properties"]["record"]["required"]
        assert ("script" in schema["required"]) == spec.has_script

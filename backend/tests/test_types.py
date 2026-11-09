"""Notifications (built and deployed) and flows (designed only), and the list of what
nowBuilder doesn't build at all."""
import pytest

from app.ai import checks
from app.ai.artifacts import SPECS, check, spec, to_records
from app.ai.skills import get_skills

from .test_chat import events, ready, send, text_turn, use_llm  # noqa: F401
from .test_checks import _client_for
from .test_deploy import approve, built_plan, deploy, final_plan
from .test_plans import json_turn, plan_turn

NOTIFICATION = {
    "record": {
        "name": "Incident opened confirmation", "collection": "incident", "active": "true",
        "action_insert": "true", "action_update": "false", "event_name": "", "condition": "",
        "recipient_fields": "opened_by", "recipient_users": "", "recipient_groups": "",
        "subject": "Incident ${number} has been created",
        "message_html": "<p>${short_description}</p><p>${URI_REF}</p>",
        "weight": "0", "send_self": "true", "exclude_delegates": "false", "content_type": "text/html",
    },
}

FLOW = {
    "record": {
        "name": "Major incident escalation", "table": "incident", "trigger": "Created or Updated",
        "trigger_condition": "priority=1", "run_trigger": "for each unique change", "run_as": "System user",
        "description": "Escalates P1 incidents and asks for approval to declare a major incident.",
    },
    "steps": [
        {"step": 1, "kind": "action", "name": "Look Up Records",
         "detail": "Table: Group. Condition: Name is Major Incident Managers."},
        {"step": 2, "kind": "action", "name": "Ask for Approval",
         "detail": "Record: Trigger → Incident Record. Approvers: the group from step 1."},
        {"step": 3, "kind": "flow logic", "name": "If",
         "detail": "Condition: step 2 Approval state is Approved."},
    ],
}

NOTIFICATION_ROW = [{"id": "c1", "type": "notification", "name": "Incident opened confirmation",
                     "table": "incident", "purpose": "email the creator when an incident is made"}]
FLOW_ROW = [{"id": "c1", "type": "flow", "name": "Major incident escalation", "table": "incident",
             "purpose": "approval flow for P1s"}]


# ---------- notifications ----------

def test_a_notification_is_planned_checked_and_deployed(client, ready, snow, monkeypatch):
    plan = built_plan(client, ready, monkeypatch, components=NOTIFICATION_ROW, generated=(NOTIFICATION,))
    assert plan["validation"]["errors"] == 0, plan["components"][0].get("problems")
    approve(client, ready, plan)
    _, evs = deploy(client, ready, plan["id"])

    [row] = snow.tables["sysevent_email_action"]
    assert row["collection"] == "incident" and row["recipient_fields"] == "opened_by"
    assert row["action_insert"] == "true" and "script" not in row       # notifications have no script
    assert final_plan(evs)["deployment"]["status"] == "deployed"


def test_the_fields_a_notification_sends_to_are_checked_against_the_table(snow):
    bad = {"record": {**NOTIFICATION["record"], "recipient_fields": "opened_by,u_ghost",
                      "subject": "About ${u_nothere}"}}
    problems = checks.instance_problems("notification", bad["record"], "", [],
                                        checks.InstanceReader(_client_for(snow)), set())
    messages = " | ".join(p.message for p in problems)
    assert "no field called u_ghost" in messages and "no field called u_nothere" in messages
    assert "opened_by" not in messages and "number" not in messages


@pytest.mark.parametrize("over,expected", [
    ({"action_insert": "false", "action_update": "false"}, "needs something to trigger it"),
    ({"event_name": "incident.opened"}, "not both"),
    ({"recipient_fields": "", "recipient_users": "", "recipient_groups": ""}, "needs someone to send to"),
    ({"collection": "task"}, "can't be built on the task table"),
])
def test_notification_settings_that_contradict_each_other(over, expected):
    problems = " | ".join(check("notification", {"record": {**NOTIFICATION["record"], **over}}))
    assert expected in problems, problems


def test_a_wrong_column_name_is_caught_before_the_deploy_fails(snow):
    """nowBuilder's own field names are checked against sysevent_email_action in the instance."""
    bad = {"record": {**NOTIFICATION["record"], "recipients": "opened_by"}}
    del bad["record"]["recipient_fields"]
    [problem] = checks.own_table_problems("notification", bad["record"], checks.InstanceReader(_client_for(snow)))
    assert "sysevent_email_action has no field called recipients" in problem.message


# ---------- flows: designed, not deployed ----------

def test_a_flow_is_designed_with_steps_but_marked_build_by_hand(client, ready, snow, monkeypatch):
    plan = built_plan(client, ready, monkeypatch, components=FLOW_ROW, generated=(FLOW,))
    [row] = plan["components"]
    assert row["status"] == "ready" and row["generated"]["steps"][1]["name"] == "Ask for Approval"
    assert row["generated"]["record"]["run_as"] == "System user"
    assert not spec("flow").deployable              # never through the Table API
    assert not checks.blocking(row)                 # but it can be approved: the SDK installs it


def test_a_flow_cannot_be_approved_or_deployed(client, ready, snow, monkeypatch):
    plan = built_plan(client, ready, monkeypatch, components=FLOW_ROW, generated=(FLOW,))
    r = approve(client, ready, plan)
    assert r.status_code == 409 and "built by hand" in r.json()["detail"]
    assert snow.tables["sys_hub_flow"] == [] if "sys_hub_flow" in snow.tables else True


def test_a_plan_can_mix_a_flow_with_things_that_do_deploy(client, ready, snow, monkeypatch):
    from .test_plans import BR, one_rule
    rows = [*one_rule(), {"id": "c2", "type": "flow", "name": "Escalation", "table": "incident", "purpose": "p"}]
    plan = built_plan(client, ready, monkeypatch, components=rows, generated=(BR, FLOW))
    approved = approve(client, ready, plan, ids=["c1"]).json()
    assert approved["approval"]["ids"] == ["c1"]
    _, evs = deploy(client, ready, plan["id"])
    out = final_plan(evs)
    assert out["deployment"]["ids"] == ["c1"] and len(snow.tables["sys_script"]) == 1
    assert out["components"][1].get("deploy") is None          # the flow was never touched


def test_flow_steps_have_to_be_numbered_in_order():
    muddled = {**FLOW, "steps": [{**FLOW["steps"][0], "step": 2}, {**FLOW["steps"][1], "step": 1}]}
    assert "Number the flow's steps" in " | ".join(check("flow", muddled))
    assert check("flow", FLOW) == []


def test_a_design_only_type_writes_no_records():
    assert to_records("flow", FLOW) == [{"table": "sys_hub_flow", "fields": FLOW["record"], "role": "main"}]
    assert not spec("flow").deployable                      # never through the Table API
    assert "ServiceNow SDK" in spec("flow").build_note and "Flow Designer" in spec("flow").build_note


# ---------- what nowBuilder doesn't build at all ----------

def test_the_limits_are_one_list_in_the_manifest_and_reach_the_prompt():
    skills = get_skills()
    limits = skills.limits()
    for phrase in ("Form and list layouts", "ACLs", "Scripted REST APIs", "Email templates", "classic workflows",
                   "Service Portal", "ATF", "Import sets", "Reports", "Virtual Agent"):
        assert phrase in limits, phrase
    prompt = skills.build_prompt("chat", text="add a field to incident")
    assert "What nowBuilder can't build" in prompt.system
    # and the catalog says which types the user builds themselves
    assert "deployed with the ServiceNow SDK" in prompt.system


def test_every_type_in_the_manifest_has_a_spec_and_the_other_way_round():
    assert set(get_skills().artifact_types()) == set(SPECS)
    for name, sp in SPECS.items():
        assert sp.table == get_skills().artifact_types()[name]["table"]
        assert sp.deployable or sp.build_note, f"{name} is design-only so it needs a build_note"


# ---------- flows: checked against the instance's own actions ----------

def _flow_problems(snow, steps):
    return checks.instance_problems("flow", FLOW["record"], "", [],
                                    checks.InstanceReader(_client_for(snow)), set(), steps=steps)


def test_a_flow_step_naming_an_action_the_instance_does_not_have_is_an_error(snow):
    """Which actions exist depends on the installed spokes. Without this check nobody finds out
    until they open Flow Designer and the action isn't in the list."""
    steps = [*FLOW["steps"], {"step": 4, "kind": "action", "name": "Post to Microsoft Teams",
                              "detail": "Channel: Major incidents."}]
    messages = " | ".join(p.message for p in _flow_problems(snow, steps))
    assert "no Flow Designer action called 'Post to Microsoft Teams'" in messages
    assert "Look Up Records" not in messages and "Ask for Approval" not in messages


def test_the_actions_the_instance_does_have_pass(snow):
    assert _flow_problems(snow, FLOW["steps"]) == []


def test_a_made_up_logic_block_is_a_warning_not_an_error(snow):
    steps = [{"step": 1, "kind": "flow logic", "name": "Repeat Until", "detail": "Until approved."}]
    [problem] = _flow_problems(snow, steps)
    assert problem.severity == checks.WARNING and "logic blocks" in problem.message


def test_flow_steps_are_not_judged_when_the_instance_cannot_be_read(snow):
    """The same rule as tables and fields: say nothing rather than guess."""
    snow.forbidden.add("sys_hub_action_type_definition")
    steps = [{"step": 1, "kind": "action", "name": "Whatever This Is", "detail": "d"}]
    assert _flow_problems(snow, steps) == []


def test_action_inputs_are_read_from_the_instance(snow):
    """Input names differ between spokes and releases, so a design can't guess them."""
    out = _client_for(snow).flow_actions("notif", with_inputs=True)
    [action] = out["actions"]
    assert action["name"] == "Send Notification"
    assert [i["name"] for i in action["inputs"]] == ["notification_id", "record_id"]
    assert action["inputs"][0]["mandatory"] is True


def test_the_full_action_list_comes_back_without_input_lookups(snow):
    out = _client_for(snow).flow_actions()
    assert out["count"] == 11 and all("inputs" not in a for a in out["actions"])


def test_existing_flows_and_notifications_can_be_searched(snow):
    snow.add_record("sys_hub_flow", {"name": "Major incident escalation", "table": "incident",
                                     "description": "d", "active": "true", "status": "published",
                                     "sys_scope": "global"})
    client_ = _client_for(snow)
    assert client_.search_artifacts("flow", table="incident")["count"] == 1
    assert client_.search_artifacts("flow", name_contains="nothing like this")["count"] == 0
    snow.add("sysevent_email_action", name="Incident opened", collection="incident", active="true",
             action_insert="true", action_update="false", event_name="", condition="",
             recipient_fields="opened_by", subject="s", sys_scope="global")
    assert client_.search_artifacts("notification", table="incident")["count"] == 1


def test_the_flow_rules_load_for_the_chat_and_for_a_flow_row_only():
    """Designing a flow needs its own rules; generating a business rule shouldn't carry them."""
    skills = get_skills()
    assert "# Flows" in skills.build_prompt("chat").system
    assert "# Flows" in skills.build_prompt("generate", ["flow"]).system
    assert "# Flows" not in skills.build_prompt("generate", ["business_rule"]).system
    # once, not twice, when a stage lists the file and the type asks for it too
    assert skills.build_prompt("chat", ["flow"]).system.count("# Flows") == 1


def test_the_flow_rules_send_the_model_to_the_instance_before_it_designs():
    system = get_skills().build_prompt("generate", ["flow"]).system
    assert "get_flow_actions" in system and "never name one from memory" in system


# ---------- flows: what the ServiceNow SDK can express ----------

FLOW_WITH_INPUTS = {
    "record": {**FLOW["record"], "trigger": "Created or Updated", "run_as": "User who initiated session"},
    "steps": [
        {"step": 1, "kind": "action", "name": "Look Up Record", "detail": "Find the group.",
         "inputs": {"table": "sys_user_group", "conditions": "name=Major Incident Managers"}},
        {"step": 2, "kind": "action", "name": "Log", "detail": "Say who was found.",
         "inputs": {"log_level": "info", "log_message": "Escalating to {{step1.Record.name}}."}},
    ],
}


def test_a_flow_row_says_whether_the_sdk_can_express_it(client, ready, snow, monkeypatch):
    plan = built_plan(client, ready, monkeypatch, components=FLOW_ROW, generated=(FLOW_WITH_INPUTS,))
    [row] = plan["components"]
    assert row["export"]["exportable"] is True
    assert row["export"]["steps_ready"] == 2 and row["export"]["sdk_version"]


def test_a_prose_only_flow_says_why_it_cannot_be_exported(client, ready, snow, monkeypatch):
    """The common case: a design good enough to build by hand, not structured enough to export."""
    plan = built_plan(client, ready, monkeypatch, components=FLOW_ROW, generated=(FLOW,))
    [row] = plan["components"]
    assert row["export"]["exportable"] is False
    assert "gives no inputs" in " ".join(row["export"]["blockers"])


def test_the_source_can_be_downloaded_for_a_flow_that_exports(client, ready, monkeypatch):
    plan = built_plan(client, ready, monkeypatch, components=FLOW_ROW, generated=(FLOW_WITH_INPUTS,))
    r = client.get(f'/api/plans/{plan["id"]}/components/c1/flow-source', headers=ready)
    assert r.status_code == 200 and "action.core.lookUpRecord" in r.text
    assert r.headers["X-NowBuilder-Deployment-Status"] == "source-only"


def test_the_source_route_refuses_a_design_it_cannot_express(client, ready, monkeypatch):
    plan = built_plan(client, ready, monkeypatch, components=FLOW_ROW, generated=(FLOW,))
    r = client.get(f'/api/plans/{plan["id"]}/components/c1/flow-source', headers=ready)
    assert r.status_code == 422 and "inputs" in r.json()["detail"]


def test_an_input_the_action_does_not_have_is_an_error_on_the_card(snow):
    """The catalogue and the instance are the same vocabulary, so a wrong input name is wrong
    in Flow Designer too — not only in the export."""
    steps = [{"step": 1, "kind": "action", "name": "Log", "detail": "d",
              "inputs": {"log_message": "hi", "colour": "red"}}]
    messages = " | ".join(p.message for p in _flow_problems(snow, steps))
    assert "Log has no input called colour" in messages


def test_a_missing_mandatory_input_is_an_error_on_the_card(snow):
    steps = [{"step": 1, "kind": "action", "name": "Create Record", "detail": "d",
              "inputs": {"table_name": "incident"}}]
    messages = " | ".join(p.message for p in _flow_problems(snow, steps))
    assert "Create Record needs values" in messages


def test_an_action_past_the_first_page_is_not_reported_missing(snow):
    """The 30 Oct regression: the checker fetched the first 200 actions in name order and treated
    that as everything the instance had, so every action past the cut was reported missing. A PDI
    with spokes installed has far more than one page of them."""
    for i in range(400):
        snow.add("sys_hub_action_type_definition", name=f"Spoke Action {i:03d}",
                 internal_name=f"spoke_{i}", active="true", sys_scope="global")
    steps = [{"step": 1, "kind": "action", "name": "Send Notification", "detail": "d"},
             {"step": 2, "kind": "action", "name": "Look Up Records", "detail": "d"}]
    assert _flow_problems(snow, steps) == []


def test_the_instance_is_asked_about_the_names_used_not_for_every_action(snow):
    """One bounded query per plan, so there is nothing to truncate."""
    reader = checks.InstanceReader(_client_for(snow))
    before = len(snow.calls)
    assert reader.flow_actions_exist(["Log", "Send Email", "Nope Not Real"]) == {"log", "send email"}
    assert len(snow.calls) - before == 1
    reader.flow_actions_exist(["Log", "Send Email"])            # already known, no second call
    assert len(snow.calls) - before == 1


def test_an_action_name_is_matched_with_the_spelling_the_design_used(snow):
    """`nameIN` matches exactly, so the design's own casing has to reach the instance."""
    assert checks.InstanceReader(_client_for(snow)).flow_actions_exist(["Create Record"]) == {"create record"}


def test_the_engines_own_inputs_are_not_treated_as_part_of_the_design(snow):
    """__snc_* inputs exist on the instance but aren't the SDK's vocabulary, so naming one is
    neither an error on the card nor something the exporter emits."""
    from app.ai.flow_sdk import export_report
    steps = [{"step": 1, "kind": "action", "name": "Log", "detail": "d",
              "inputs": {"log_message": "hi", "__snc_dont_fail_on_error": "true"}}]
    assert _flow_problems(snow, steps) == []
    design = {"record": {**FLOW_WITH_INPUTS["record"]}, "steps": steps}
    assert export_report(design)["exportable"] is True


def test_internal_inputs_are_hidden_from_the_model(snow):
    action = _client_for(snow).flow_actions("log", with_inputs=True)["actions"][0]
    snow.add("sys_hub_action_input", model=action["sys_id"], element="__snc_internal",
             label="Internal", internal_type="boolean", reference="", mandatory="false", order="9")
    again = _client_for(snow).flow_actions("log", with_inputs=True)["actions"][0]
    assert all(not i["name"].startswith("__snc") for i in again["inputs"])


def test_a_changes_condition_needs_the_updated_trigger():
    from app.ai.flow_sdk import export_report
    steps = [{"step": 1, "action": "Log", "inputs": {"log_level": "info", "log_message": "x"}}]
    for trigger, ok in (("Created", False), ("Created or Updated", False), ("Updated", True)):
        rep = export_report({"record": {"name": "Lead owner", "table": "incident", "trigger": trigger,
                                        "trigger_condition": "assigned_toVALCHANGES", "run_trigger": "once",
                                        "run_as": "System user"}, "steps": steps})
        assert any("changes" in b for b in rep["blockers"]) is not ok, trigger


def test_design_documents_are_read_in_the_chat_stage():
    from app.ai.skills import Skills
    prompt = Skills().build_prompt("chat", [], "use case")
    assert "Requirements written as a design document" in prompt.system


def test_a_flow_the_sdk_cannot_deploy_is_a_check_error_when_flows_deploy(monkeypatch):
    from app.ai import checks
    from app.services import sdk_deploy
    data = {"record": {"name": "Lead reminders", "table": "incident", "trigger": "Created", "trigger_condition": "",
                       "run_trigger": "once", "run_as": "System user"},
            "steps": [{"step": 1, "kind": "flow logic", "name": "Do The Following In Parallel"},
                      {"step": 2, "kind": "action", "name": "Log", "inside": 1,
                       "inputs": {"log_level": "info", "log_message": "x"}}]}
    monkeypatch.setattr(sdk_deploy, "configured", lambda: False)
    assert checks.flow_export_problems(data) == []                # design only: built by hand
    monkeypatch.setattr(sdk_deploy, "configured", lambda: True)
    errors = checks.flow_export_problems(data)
    assert errors and all(p.severity == checks.ERROR for p in errors)
    assert any("Do The Following In Parallel" in p.message for p in errors)


def test_the_flow_rules_teach_loops_inside_the_flow():
    from app.ai.skills import Skills
    system = Skills().build_prompt("chat", ["flow"], "repeat every 2 minutes until the stage closes").system
    assert "Do the following until" in system and "wfa.flowLogic.until" in system and "Wait for a duration" in system
    assert "eventQueueScheduled" not in system


def test_a_catalog_item_writes_the_item_and_its_variables():
    from app.ai.artifacts import to_records
    data = {"record": {"name": "Laptop", "short_description": "x", "description": "", "sc_catalogs": "Service Catalog",
                       "category": "", "active": "true"},
            "variables": [{"name": "who", "question_text": "Who?", "type": "reference", "mandatory": "true",
                           "order": "100", "reference": "sys_user", "help_text": ""},
                          {"name": "why", "question_text": "Why?", "type": "multi_line_text", "mandatory": "false",
                           "order": "200", "reference": "", "help_text": ""}]}
    rows = to_records("catalog_item", data)
    assert rows[0]["table"] == "sc_cat_item" and "category" not in rows[0]["fields"]
    assert [r["fields"]["type"] for r in rows[1:]] == ["8", "2"]            # item_option_new type codes
    assert all(r["table"] == "item_option_new" and r["parent_field"] == "cat_item" for r in rows[1:])
    assert "reference" not in rows[2]["fields"]


def test_a_client_scripts_trigger_field_uses_the_column_this_instance_has():
    """sys_script_client stores the onChange field as `field` on some instances, `field_name` on others."""
    from app.ai import checks
    from app.ai.artifacts import apply_aliases, to_records
    rec = {"name": "x", "table": "incident", "type": "onChange", "field_name": "category", "ui_type": "10",
           "active": "true", "isolate_script": "true", "description": "d"}
    fields = to_records("client_script", {"record": rec, "script": "function onChange(){}"})[0]["fields"]
    assert apply_aliases("client_script", fields, {"field", "name", "table"})["field"] == "category"
    assert "field_name" in apply_aliases("client_script", fields, {"field_name", "field"})   # both: keep it

    class Reader:
        def schema(self, table):
            cols = ["sys_id", "name", "table", "type", "field", "ui_type", "active", "isolate_script",
                    "description", "script"]
            return {"exists": True, "fields": [{"name": c} for c in cols]}
    assert checks.own_table_problems("client_script", rec, Reader()) == []

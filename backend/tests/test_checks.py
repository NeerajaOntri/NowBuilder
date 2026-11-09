"""Chunk 3: the checks that run over a generated artifact, and running them again from the API."""
import pytest

from app.ai import checks
from app.ai.checks import InstanceReader
from app.models import Plan
from app.services.servicenow import ServiceNowClient

from .test_chat import ready, send, text_turn, use_llm  # noqa: F401
from .test_plans import BR, SI, json_turn, one_rule, plan_turn

# ---------- script rules ----------

@pytest.mark.parametrize("type_,script,when,expected", [
    ("business_rule", "(function(c){ current.update(); })();", "before", "must not call current.update()"),
    ("business_rule", "(function(){ gs.log('hi'); })();", "after", "isn't available in a scoped application"),
    ("business_rule", "(function(){ var x = '6816f79cc0a8016401c5a33be04be441'; })();", "after", "sys_id written into it"),
    ("business_rule", "(function(){ var f = function () { return 1; }; })();", "after", None),
    ("business_rule", "(function(){ var f = () => 1; })();", "after", "Arrow functions are ES6"),
    ("business_rule", "(function(){ var s = `a${1}b`; })();", "after", "Template literals are ES6"),
    ("business_rule", "(function(){\n  const x = 1;\n})();", "after", "let and const are ES6"),
    ("business_rule", "(function(){ eval('x'); })();", "after", "eval() and new Function()"),
    ("business_rule", "(function(){ try { x(); } catch (e) {} })();", "after", "catch block hides the error"),
    ("business_rule", "(function(){ gr.setWorkflow(false); })();", "after", "skips business rules"),
    ("business_rule", "(function(){ gr.deleteMultiple(); })();", "after", "can't be undone"),
    ("client_script", "function onLoad() { var g = new GlideRecord('incident'); }", "", "must not use GlideRecord"),
    ("client_script", "function onLoad() { ga.getXMLWait(); }", "", "freezes the browser"),
    ("client_script", "function onLoad() { document.getElementById('x'); }", "", "DOM or jQuery"),
    ("client_script", "function onLoad() { g_form.getReference('caller_id'); }", "", "without a callback"),
])
def test_script_rules(type_, script, when, expected):
    found = " | ".join(p.message for p in checks._script_problems(type_, script, when, es2021=False))
    if expected is None:
        assert found == ""
    else:
        assert expected in found, found


def test_es2021_scopes_allow_modern_javascript():
    script = "(function(){ const f = () => `x`; })();"
    assert checks._script_problems("business_rule", script, "after", es2021=False)
    assert checks._script_problems("business_rule", script, "after", es2021=True) == []


def test_a_query_inside_a_loop_is_flagged_once():
    script = "(function(){ while (gr.next()) { var u = new GlideRecord('sys_user'); u.get(gr.caller_id); } })();"
    problems = checks._script_problems("business_rule", script, "after", es2021=False)
    assert sum("one query per row" in p.message for p in problems) == 1


def test_problems_carry_the_line_they_are_on():
    script = "(function () {\n    var x = 1;\n    current.update();\n})();"
    [p] = [p for p in checks._script_problems("business_rule", script, "before", False) if "current.update" in p.message]
    assert p.location == "line 3" and p.severity == "error"


# ---------- what an artifact says it uses ----------

def test_fields_used_reads_the_script_and_the_conditions():
    record = {"collection": "incident", "condition": "current.caller_id.vip == true", "filter_condition": "category=network^priority=1"}
    script = "(function(){ current.setValue('urgency', 1); var x = current.short_description; })();"
    assert checks.fields_used("business_rule", record, script) == {"caller_id", "category", "priority", "urgency", "short_description"}


def test_client_script_fields_come_from_g_form():
    record = {"table": "incident", "type": "onChange", "field_name": "category"}
    script = "function onChange() { g_form.setValue('subcategory', 'x'); g_form.setMandatory('u_vendor', true); }"
    assert checks.fields_used("client_script", record, script) == {"category", "subcategory", "u_vendor"}


def test_tables_and_classes_the_script_calls():
    script = "var gr = new GlideRecord('sys_user_group'); var u = new VipUtils(); var d = new GlideDateTime();"
    assert checks.tables_used(script) == {"sys_user_group"}
    assert checks.classes_used(script) == {"VipUtils"}      # GlideDateTime is the platform's


# ---------- against the connected instance ----------

def _reader(snow, inst_url="https://dev410284.service-now.com"):
    class Inst:
        url, auth_method, username, password_enc = inst_url, "basic", "admin", None
    return InstanceReader(_client_for(snow))


def _client_for(snow):
    from app.security import encrypt

    class Inst:
        url = "https://dev410284.service-now.com"
        auth_method, username = "basic", "admin"
        password_enc = encrypt("pw")
    return ServiceNowClient(Inst(), None, transport=snow.transport)


def test_unknown_field_and_table_are_errors(snow):
    record = {"name": "r", "collection": "incident", "condition": "current.u_not_here == true", "when": "after",
              "order": "100", "active": "true", "action_insert": "true", "action_update": "false",
              "action_delete": "false", "action_query": "false", "filter_condition": "", "description": "d"}
    script = "(function(){ var gr = new GlideRecord('u_missing_table'); })();"
    problems = checks.instance_problems("business_rule", record, script, [], InstanceReader(_client_for(snow)), set())
    messages = " | ".join(p.message for p in problems)
    assert "no field called u_not_here" in messages and "u_missing_table, which isn't in this instance" in messages
    assert all(p.severity == "error" for p in problems)


def test_inherited_fields_count_as_present(snow):
    record = {"collection": "incident", "condition": "current.short_description != ''"}   # short_description is on task
    assert checks.instance_problems("business_rule", record, "", [], InstanceReader(_client_for(snow)), set()) == []


def test_a_script_include_in_the_same_plan_is_not_missing(snow):
    script = "(function(){ new VipUtils().isVip(); })();"
    reader = InstanceReader(_client_for(snow))
    assert checks.instance_problems("business_rule", {"collection": "incident"}, script, [], reader, {"VipUtils"}) == []
    [p] = checks.instance_problems("business_rule", {"collection": "incident"}, script, [], reader, set())
    assert "neither in this plan nor in the instance" in p.message


def test_ui_policy_action_fields_are_checked(snow):
    record = {"table": "incident", "conditions": ""}
    actions = [{"field": "category", "mandatory": "true", "visible": "true", "disabled": "false"},
               {"field": "u_ghost", "mandatory": "ignore", "visible": "true", "disabled": "ignore"}]
    problems = checks.instance_problems("ui_policy", record, "", actions, InstanceReader(_client_for(snow)), set())
    assert len(problems) == 1 and "u_ghost" in problems[0].message


def test_an_unreadable_instance_is_said_plainly_not_guessed(snow):
    snow.forbidden.add("sys_db_object")
    components = [{"id": "c1", "type": "business_rule", "name": "r", "status": "ready",
                   "generated": {"record": {"collection": "incident", "condition": "current.u_nope == 1"}, "script": ""}}]
    out = checks.run(components, _client_for(snow))
    assert out["instance_checked"] is False and "couldn't read the instance" in out["message"]
    assert not [p for p in components[0]["problems"] if p["source"] == "instance"]


# ---------- running the checks over a plan ----------

def test_run_counts_errors_and_warnings_and_blocks_the_bad_rows(snow):
    components = [
        {"id": "c1", "type": "business_rule", "name": "ok", "status": "ready", "generated": BR},
        {"id": "c2", "type": "business_rule", "name": "bad", "status": "ready",
         "generated": {**BR, "script": "(function(){ current.update(); var x = '6816f79cc0a8016401c5a33be04be441'; })();"}},
    ]
    out = checks.run(components, _client_for(snow))
    assert out["status"] == "problems" and out["errors"] == 1 and out["warnings"] == 1
    assert checks.blocking(components[1]) and not checks.blocking(components[0])


def test_only_rechecks_the_rows_asked_for(snow):
    components = [
        {"id": "c1", "type": "business_rule", "name": "a", "status": "ready", "generated": BR,
         "problems": [{"source": "script", "severity": "error", "message": "stale", "location": ""}]},
        {"id": "c2", "type": "script_include", "name": "b", "status": "ready", "generated": SI},
    ]
    out = checks.run(components, _client_for(snow), only=["c2"])
    assert components[0]["problems"][0]["message"] == "stale"   # untouched
    assert components[1]["problems"] == [] and out["errors"] == 1


# ---------- the API ----------

def test_recheck_endpoint_updates_the_plan(client, ready, monkeypatch):
    use_llm(monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("Ready.")])
    chat = client.post("/api/chats", headers=ready).json()
    send(client, ready, chat["id"], "VIP callers should get priority 1")
    plan = client.get(f"/api/chats/{chat['id']}", headers=ready).json()["plans"][0]
    assert plan["validation"]["status"] == "passed" and plan["validation"]["instance_checked"]

    out = client.post(f"/api/plans/{plan['id']}/check", headers=ready).json()
    assert out["validation"]["errors"] == 0 and out["components"][0]["problems"] == []
    assert out["fixes"] == []


def test_generation_runs_the_checks_and_reports_them(client, ready, monkeypatch):
    bad = {**BR, "record": {**BR["record"], "condition": "current.u_phantom == true"}}
    use_llm(monkeypatch, [plan_turn(one_rule()), json_turn(bad), text_turn("One problem.")])
    chat = client.post("/api/chats", headers=ready).json()
    send(client, ready, chat["id"], "VIP callers should get priority 1")
    plan = client.get(f"/api/chats/{chat['id']}", headers=ready).json()["plans"][0]
    assert plan["validation"]["errors"] == 1
    [p] = plan["components"][0]["problems"]
    assert p["source"] == "instance" and "u_phantom" in p["message"]


def test_the_checks_flag_a_pill_in_an_email_body_on_the_card():
    from app.ai import checks
    steps = [{'step': 1, 'kind': 'action', 'name': 'Send Email', 'detail': 'd',
              'inputs': {'ah_to': 'a@b.c', 'ah_subject': 'x', 'ah_body': 'Hi {{step2.Record.name}}'}}]
    reader = checks.InstanceReader(None)
    problems = checks.flow_step_problems(steps, reader)
    # Another step's pill: a warning (it goes in as a placeholder); never an error.
    assert any(p.severity == checks.WARNING and "only takes fixed text" in p.message for p in problems)
    assert not any(p.severity == checks.ERROR for p in problems)
    steps[0]['inputs']['ah_body'] = 'Hi {{trigger.current.owner.name}}'     # the trigger record: no warning
    assert not any("only takes fixed text" in p.message for p in checks.flow_step_problems(steps, reader))


def test_send_email_recipients_must_be_email_addresses():
    """The instance rejected a group record pill: 'invalid recipient addresses: sys_user_group'."""
    steps = [{'step': 1, 'kind': 'action', 'name': 'Send Email', 'detail': 'x',
              'inputs': {'ah_to': '{{trigger.current.assignment_group}}', 'ah_subject': 'x', 'ah_body': 'x'}}]
    reader = checks.InstanceReader(None)
    warnings = [p for p in checks.flow_step_problems(steps, reader) if 'email addresses' in p.message]
    assert warnings and '{{trigger.current.assignment_group.email}}' in warnings[0].message
    from app.ai.flow_sdk import generate_flow_source             # and the flow is built with the .email pill
    src = generate_flow_source({'record': {'name': 'T', 'table': 'incident', 'trigger': 'Created',
                                           'run_as': 'System user'}, 'steps': steps})
    assert "ah_to: wfa.dataPill(params.trigger.current.assignment_group.email, 'string')" in src
    steps[0]['inputs']['ah_to'] = '{{trigger.current.assignment_group.email}}, ops@example.com'
    assert not [p for p in checks.flow_step_problems(steps, reader) if 'email addresses' in p.message]


def test_a_glideajax_call_must_match_the_script_include_it_calls():
    si = {"id": "c1", "type": "script_include", "name": "CallerIncidentCountAjax", "status": "ready",
          "generated": {"record": {"name": "CallerIncidentCountAjax"}, "script":
              "var CallerIncidentCountAjax = Class.create();\nCallerIncidentCountAjax.prototype = Object.extendsObject("
              "global.AbstractAjaxProcessor, {\n  getOpenIncidentCount: function () {\n"
              "    var c = this.getParameter('sysparm_caller_id'); var x = this.getParameter('sysparm_current_id');\n"
              "    return '1';\n  },\n  type: 'CallerIncidentCountAjax'\n});"}}
    cs = {"id": "c2", "type": "client_script", "name": "x", "status": "ready", "generated": {"script":
          "var ga = new GlideAjax('CallerIncidentCountAjax');\nga.addParam('sysparm_name', 'getOpenCount');\n"
          "ga.addParam('sysparm_caller', newValue);\nga.addParam('sysparm_exclude', g_form.getUniqueValue());"}}
    msgs = [p.message for p in checks.glideajax_problems(cs, [si, cs], None)]
    assert any("getOpenCount" in m and "getOpenIncidentCount" in m for m in msgs)
    assert any("sysparm_caller_id" in m and "sysparm_current_id" in m for m in msgs)
    cs["generated"]["script"] = ("var ga = new GlideAjax('CallerIncidentCountAjax');\n"
                                 "ga.addParam('sysparm_name', 'getOpenIncidentCount');\n"
                                 "ga.addParam('sysparm_caller_id', newValue);\nga.addParam('sysparm_current_id', 'x');")
    assert checks.glideajax_problems(cs, [si, cs], None) == []


def test_a_dependent_row_is_written_against_the_real_script_it_calls():
    from app.ai.planning import _context
    si = {"id": "c1", "type": "script_include", "name": "Ajax", "status": "ready",
          "generated": {"record": {"name": "Ajax"}, "script": "getOpenIncidentCount: function () {}"}}
    cs = {"id": "c2", "type": "client_script", "name": "x", "status": "planned", "dependsOn": ["c1"]}
    text = _context(None, {"title": "t", "summary": "s", "components": [si, cs]}, cs)
    assert "getOpenIncidentCount" in text and "must match exactly" in text


def test_a_script_that_doesnt_parse_is_caught():
    import shutil
    if not shutil.which("node"):
        return
    bad = checks.syntax_problems("function onLoad() {\n  var x = ;\n}")
    assert bad and bad[0].severity == checks.ERROR and "doesn't parse" in bad[0].message and bad[0].location == "line 2"
    assert checks.syntax_problems("var gr = new GlideRecord('incident');\nreturn gr.getRowCount();") == []


def test_an_event_that_isnt_registered_is_caught(client, auth, snow):
    from .conftest import connect_instance
    connect_instance(client, auth)
    from app.services.servicenow import ServiceNowClient
    from app.db import SessionLocal
    from app.models import Instance
    db = SessionLocal()
    inst = db.query(Instance).first()
    sn = ServiceNowClient(inst, db)
    snow.tables.setdefault("sysevent_register", []).append({"sys_id": "e" * 32, "event_name": "incident.vip"})
    rule = {"id": "c1", "type": "business_rule", "name": "x", "status": "ready",
            "generated": {"script": "gs.eventQueue('incident.vip', current);\ngs.eventQueue('incident.typo', current);"}}
    msgs = [p.message for p in checks.event_problems(rule, [rule], sn)]
    db.close()
    assert len(msgs) == 1 and "incident.typo" in msgs[0]
    planned = {"id": "c2", "type": "event", "name": "incident.typo", "generated": {"record": {"event_name": "incident.typo"}}}
    assert checks.event_problems(rule, [rule, planned], None) == []

"""The plan's application (scope): taken from the request or document, checked against the instance,
made the user's current application before Table API writes, and Global flows installed into a
Global SDK application (falling back to the scoped app with a note when the SDK can't)."""
import json

from app.ai import checks
from app.services import application as apps
from app.services import sdk_deploy

from .test_deploy_button import calls_app, fake_sdk, plan_from_chat, setup_ai
from .test_auto_deploy import FLOW, FLOW_ROWS, NOTIFICATION
from .test_chat import text_turn
from .test_deploy import approve, deploy, final_plan
from .test_plans import BR, json_turn, one_rule, plan_turn
from .test_sdk_deploy_bridge import PrefixClient, _auto_mode


def test_the_application_is_read_from_what_the_document_says():
    assert apps.normalize("Global") == "global"
    assert apps.normalize("") == "global"
    assert apps.normalize("SOMT / [exact scope]") == "SOMT"          # a template blank doesn't count
    assert apps.normalize("[exact scope]") == "global"
    assert apps.normalize("Customer app (x_acme_crm)") == "x_acme_crm"


def test_table_api_rows_go_into_the_plans_application_with_its_update_set(client, auth, snow, monkeypatch):
    setup_ai(client, auth, monkeypatch)
    _, plan = plan_from_chat(client, auth, monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("Ready.")],
                             "VIP callers get priority 1, in the Global application")
    assert plan["application"] == "global"
    approve(client, auth, plan)
    _, evs = deploy(client, auth, plan["id"])
    out = final_plan(evs)
    prefs = {p["name"]: p["value"] for p in snow.tables["sys_user_preference"]}
    assert prefs["apps.current_app"] == "global"                        # the application picker
    us = snow.tables["sys_update_set"][0]
    assert us["application"] == "global" and prefs["sys_update_set"] == us["sys_id"]
    assert out["components"][0]["deploy"]["application"] == "Global"


def test_an_application_the_instance_doesnt_have_is_a_check_error():
    c = {"id": "c1", "type": "business_rule", "status": "ready"}
    problems = checks.application_problems(c, "x_nope_app", None)
    assert problems and problems[0].severity == checks.ERROR and "isn't on this instance" in problems[0].message


def test_a_flow_cant_be_installed_into_someone_elses_scoped_app():
    flow = {"id": "c2", "type": "flow", "status": "ready"}
    target = {"scope": "x_acme_crm", "sys_id": "a" * 32, "name": "CRM"}
    assert checks.application_problems(flow, "x_acme_crm", target)[0].severity == checks.ERROR
    assert checks.application_problems(flow, "global", apps.GLOBAL) == []
    rule = {"id": "c1", "type": "business_rule", "status": "ready"}
    assert checks.application_problems(rule, "x_acme_crm", target) == []   # Table API rows can go there


def test_a_global_plan_asks_the_sdk_for_a_global_flow(client, auth, snow, monkeypatch):
    setup_ai(client, auth, monkeypatch)
    fake_sdk(monkeypatch, ["ok"])
    _, plan = plan_from_chat(client, auth, monkeypatch, [plan_turn(FLOW_ROWS), json_turn(NOTIFICATION), json_turn(FLOW),
                                                          text_turn("Ready.")], "email the caller on P1 with a flow")
    approve(client, auth, plan)
    deploy(client, auth, plan["id"])
    assert calls_app == ["global"]


def _global_setup(tmp_path, monkeypatch, fail_global):
    _auto_mode(tmp_path, monkeypatch)
    calls = []

    def fake(cwd, cmd, timeout, env=None, stdin=None, log=None, live=False):
        calls.append((cwd, cmd))
        if cmd[1:2] == ['install'] and 'npm' in cmd[0]:
            (cwd / 'node_modules' / '.bin').mkdir(parents=True)
        if fail_global and cwd.name in ('global', 'global_app') and cmd[-1] == 'build':
            raise sdk_deploy.SDKDeployError('`build` failed (exit 1): global applications need the Australia release')
        return 'ok'

    monkeypatch.setattr(sdk_deploy, '_execute', fake)
    return calls


def test_a_global_flow_is_built_and_installed_from_the_global_application(tmp_path, monkeypatch):
    calls = _global_setup(tmp_path, monkeypatch, fail_global=False)
    out = sdk_deploy.run_scoped_flow({'record': {'name': 'Flow'}}, install=True, client=PrefixClient(),
                                     instance_url='https://dev410284.service-now.com', username='admin', password='pw',
                                     application='global')
    from app.config import get_settings
    get_settings.cache_clear()
    project = tmp_path / 'data' / 'sdk' / 'dev410284_service_now_com'
    config = json.loads((project / 'global' / 'now.config.json').read_text())
    assert config['scope'] == 'global' and config['scopeId'] == 'global' and config['packageResolverVersion'] == '2.0.0'
    assert (project / 'global' / 'src' / 'fluent' / 'nowbuilder_flow.now.ts').is_file()
    assert not (project / 'src' / 'fluent' / 'nowbuilder_flow.now.ts').exists()
    assert out['application'] == 'Global' and out['installed'] and 'application_note' not in out
    assert any(cwd.name == 'global' and 'install' in cmd for cwd, cmd in calls)


def test_when_the_sdk_cant_do_global_the_flow_goes_to_the_scoped_app_and_says_why(tmp_path, monkeypatch):
    _global_setup(tmp_path, monkeypatch, fail_global=True)
    out = sdk_deploy.run_scoped_flow({'record': {'name': 'Flow'}}, install=True, client=PrefixClient(),
                                     instance_url='https://dev410284.service-now.com', username='admin', password='pw',
                                     application='global')
    from app.config import get_settings
    get_settings.cache_clear()
    project = tmp_path / 'data' / 'sdk' / 'dev410284_service_now_com'
    assert out['installed'] and out['application'] == 'x_1234567_nbuild'
    note = out['application_note']
    assert "Not installed straight into Global" in note and 'nowBuilder Global' in note and 'Australia' in note
    assert 'global applications need the Australia release' in note           # the SDK's own reason
    assert (project / 'global' / sdk_deploy.GLOBAL_UNSUPPORTED).is_file()   # not retried on every deploy
    assert (project / 'global_app' / sdk_deploy.GLOBAL_UNSUPPORTED).is_file()
    assert not (project / 'global' / 'src' / 'fluent' / 'nowbuilder_flow.now.ts').exists()


def test_the_sdk_probe_only_runs_local_explain_commands(tmp_path, monkeypatch):
    from app import sdk_probe
    project = tmp_path / 'p'
    (project / 'node_modules' / '@servicenow' / 'sdk-core').mkdir(parents=True)
    (project / 'node_modules' / '@servicenow' / 'sdk-core' / 'logic.d.ts').write_text(
        'export declare function waitForADuration(config: X, inputs: Y): void')
    ran = []
    monkeypatch.setattr(sdk_probe, '_run', lambda cwd, cmd: ran.append(cmd) or 'flow-api  flow-logic-guide')
    text = sdk_probe.probe(project)
    assert all(('explain' in c) or ('--version' in c) for c in ran)        # nothing that touches an instance
    assert any('explain' in c and 'flow-logic-guide' in c for c in ran)
    assert 'waitForADuration(config' in text


def test_a_flow_in_the_global_application_counts_as_global(client, auth, snow, monkeypatch):
    """A Global application's flow has sys_scope = the application record (scope 'global')."""
    setup_ai(client, auth, monkeypatch)
    fake_sdk(monkeypatch, ["ok"])
    snow.tables.setdefault("sys_scope", []).append({"sys_id": "b" * 32, "scope": "global", "name": "nowBuilder Global"})
    monkeypatch.setattr(sdk_deploy, "read_back_flow", lambda client, name: {
        "sys_id": "f" * 32, "active": True, "status": "published", "url": "https://x/flow", "sys_scope": "b" * 32})
    _, plan = plan_from_chat(client, auth, monkeypatch, [plan_turn(FLOW_ROWS), json_turn(NOTIFICATION), json_turn(FLOW),
                                                          text_turn("Ready.")], "email the caller on P1 with a flow")
    approve(client, auth, plan)
    _, evs = deploy(client, auth, plan["id"])
    flow = {c["id"]: c for c in final_plan(evs)["components"]}["c2"]["deploy"]
    assert flow["application"] == "Global" and "outside Global" not in (flow.get("message") or "")


def test_the_global_application_is_the_second_choice(tmp_path, monkeypatch):
    _global_setup(tmp_path, monkeypatch, fail_global=False)
    real = sdk_deploy._execute

    def fail_pure_global(cwd, cmd, timeout, env=None, stdin=None, log=None, live=False):
        if cwd.name == 'global' and cmd[-1] == 'build':
            raise sdk_deploy.SDKDeployError("`build` failed (exit 1): [now-sdk] Starting\nError: scopeId global not allowed")
        return real(cwd, cmd, timeout, env, stdin, log, live)

    monkeypatch.setattr(sdk_deploy, '_execute', fail_pure_global)
    out = sdk_deploy.run_scoped_flow({'record': {'name': 'Flow'}}, install=True, client=PrefixClient(),
                                     instance_url='https://dev410284.service-now.com', username='admin', password='pw',
                                     application='global')
    from app.config import get_settings
    get_settings.cache_clear()
    project = tmp_path / 'data' / 'sdk' / 'dev410284_service_now_com'
    assert out['application'] == 'nowBuilder Global' and out['installed']
    assert 'scopeId global not allowed' in out['application_note']
    cfg = json.loads((project / 'global_app' / 'now.config.json').read_text())
    assert cfg['scope'] == 'global' and len(cfg['scopeId']) == 32


def test_if_the_sdk_refuses_pill_references_the_body_falls_back_to_placeholders(tmp_path, monkeypatch):
    _global_setup(tmp_path, monkeypatch, fail_global=False)
    real = sdk_deploy._execute
    built = []

    def refuse_references(cwd, cmd, timeout, env=None, stdin=None, log=None, live=False):
        if cmd[-1] == 'build':
            src = (cwd / 'src' / 'fluent' / 'nowbuilder_flow.now.ts').read_text()
            built.append(src)
            if '{{trigger.current.number}}' in src:
                raise sdk_deploy.SDKDeployError('`build` failed (exit 1): Error TS228: ah_body must be static')
        return real(cwd, cmd, timeout, env, stdin, log, live)

    monkeypatch.setattr(sdk_deploy, '_execute', refuse_references)
    from app.ai import flow_sdk
    monkeypatch.setattr(sdk_deploy, 'generate_flow_source', flow_sdk.generate_flow_source)
    design = {'record': {'name': 'Flow', 'table': 'incident', 'trigger': 'Created', 'run_as': 'System user'},
              'steps': [{'step': 1, 'kind': 'action', 'name': 'Send Email', 'detail': 'x',
                         'inputs': {'ah_to': 'a@b.c', 'ah_subject': 'x', 'ah_body': 'No. {{trigger.current.number}}'}}]}
    out = sdk_deploy.run_scoped_flow(design, install=True, client=PrefixClient(),
                                     instance_url='https://dev410284.service-now.com', username='admin', password='pw',
                                     application='global')
    from app.config import get_settings
    get_settings.cache_clear()
    assert out['installed'] and out['application'] == 'Global'
    assert 'No. [Number]' in built[-1] and 'placeholders' in out['body_note']


def test_an_instance_older_than_australia_skips_straight_global(tmp_path, monkeypatch):
    calls = _global_setup(tmp_path, monkeypatch, fail_global=False)
    out = sdk_deploy.run_scoped_flow({'record': {'name': 'Flow'}}, install=True, client=PrefixClient(),
                                     instance_url='https://dev410284.service-now.com', username='admin', password='pw',
                                     application='global', release='glide-zurich-07-01-2025__patch2')
    from app.config import get_settings
    get_settings.cache_clear()
    assert out['application'] == 'nowBuilder Global'
    assert not any(cwd.name == 'global' for cwd, _ in calls)                 # no failed install left behind
    assert 'Zurich' in out['application_note'] and 'Global scope' in out['application_note']
    assert sdk_deploy.older_release('Australia') == '' and sdk_deploy.older_release('') == ''

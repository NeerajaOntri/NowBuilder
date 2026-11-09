"""Deploying happens when the user clicks Deploy on the plan card (the default): the chat never
deploys, the button deploys Table API rows into an update set that stays current and installs flows
with the ServiceNow SDK, and deploying again finishes rows that didn't go in."""
import json
from datetime import UTC, datetime, timedelta

from app.services import ai_provider, sdk_deploy

from .conftest import connect_instance
from .test_auto_deploy import FLOW, FLOW_ROWS, NOTIFICATION, tool_results
from .test_chat import events, send, text_turn, use_llm
from .test_deploy import approve, deploy, final_plan
from .test_plans import BR, json_turn, one_rule, plan_turn


def setup_ai(client, auth, monkeypatch):
    monkeypatch.setattr(ai_provider, "verify", lambda *a: ai_provider.VerifyResult(True, "ok"))
    client.put("/api/settings/ai-provider", json={"provider": "anthropic", "model": "claude-sonnet-5-5",
                                                  "api_key": "sk-ant-test-1234567890"}, headers=auth)
    connect_instance(client, auth)


def plan_from_chat(client, auth, monkeypatch, turns, text):
    llm = use_llm(monkeypatch, turns)
    chat = client.post("/api/chats", headers=auth).json()
    events(send(client, auth, chat["id"], text))
    return llm, client.get(f"/api/chats/{chat['id']}", headers=auth).json()["plans"][0]


def test_the_chat_never_deploys_even_when_the_prompt_says_deploy(client, auth, snow, monkeypatch):
    setup_ai(client, auth, monkeypatch)
    llm, plan = plan_from_chat(client, auth, monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("Ready.")],
                               "VIP callers get priority 1. Deploy it.")
    assert "deploy_plan" not in llm.calls[0]["tools"]           # the model has no way to deploy
    assert plan["deployment"] is None and plan["status"] == "draft"
    assert not snow.tables.get("sys_script")
    assert "clicks Deploy on the plan card" in tool_results(llm)[-1]


calls_app: list = []


def fake_sdk(monkeypatch, outcomes):
    """run_scoped_flow answers from `outcomes` in turn: 'ok' or 'pending'."""
    calls = []
    calls_app.clear()

    def run(generated, *, install, instance_url, username, password, client=None, on_status=None,
            application="scoped", release=""):
        calls_app.append(application)
        calls.append(generated)
        if outcomes.pop(0) == "pending":
            raise sdk_deploy.SDKSetupPending("The ServiceNow SDK is still being set up. Say 'deploy it' when done.")
        return {"status": "installed", "installed": True}

    monkeypatch.setattr(sdk_deploy, "configured", lambda: True)
    monkeypatch.setattr(sdk_deploy, "run_scoped_flow", run)
    monkeypatch.setattr(sdk_deploy, "read_back_flow", lambda client, name: {
        "sys_id": "f" * 32, "active": True, "status": "published", "url": "https://x/flow"})
    return calls


def test_the_deploy_button_installs_the_flow_and_its_notification(client, auth, snow, monkeypatch):
    setup_ai(client, auth, monkeypatch)
    calls = fake_sdk(monkeypatch, ["ok"])
    _, plan = plan_from_chat(client, auth, monkeypatch, [plan_turn(FLOW_ROWS), json_turn(NOTIFICATION), json_turn(FLOW),
                                                          text_turn("Ready.")], "email the caller on P1 with a flow")
    assert plan["deployment"] is None                           # nothing until the button
    assert approve(client, auth, plan).status_code == 200      # flows can be approved
    r, evs = deploy(client, auth, plan["id"], name="Lead email")
    out = final_plan(evs)
    by_id = {c["id"]: c for c in out["components"]}
    assert by_id["c1"]["deploy"]["status"] == "deployed" and by_id["c2"]["deploy"]["status"] == "deployed"
    notification = snow.tables["sysevent_email_action"][0]["sys_id"]
    assert calls[0]["steps"][0]["inputs"]["notification"] == notification
    assert out["deployment"]["status"] == "deployed" and out["deployment"]["update_set_current"] is True
    assert any(e["type"] == "status" and "flow" in e["text"].lower() for e in evs)   # progress was streamed


def test_deploying_again_finishes_a_flow_that_waited_for_the_sdk(client, auth, snow, monkeypatch):
    setup_ai(client, auth, monkeypatch)
    fake_sdk(monkeypatch, ["pending", "ok"])
    _, plan = plan_from_chat(client, auth, monkeypatch, [plan_turn(FLOW_ROWS), json_turn(NOTIFICATION), json_turn(FLOW),
                                                          text_turn("Ready.")], "email the caller on P1 with a flow")
    approve(client, auth, plan)
    _, evs = deploy(client, auth, plan["id"])
    first = final_plan(evs)
    assert first["deployment"]["status"] == "partial"
    assert {c["id"]: c for c in first["components"]}["c2"]["deploy"]["status"] == "waiting for SDK setup"
    _, evs = deploy(client, auth, plan["id"])                   # "Deploy the remaining 1…"
    second = final_plan(evs)
    assert second["deployment"]["status"] == "deployed"
    assert len(snow.tables["sysevent_email_action"]) == 1        # the notification wasn't written twice
    assert len(second["deployment"]["records"]) == 1             # and is still there for rollback


def test_a_plan_left_busy_by_a_stopped_backend_can_be_checked_again(client, auth, snow, monkeypatch):
    setup_ai(client, auth, monkeypatch)
    _, plan = plan_from_chat(client, auth, monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("Ready.")], "x")
    from app.db import SessionLocal
    from app.models import Plan
    db = SessionLocal()
    p = db.get(Plan, plan["id"])
    p.busy, p.busy_since = "deploying", datetime.now(UTC) - timedelta(hours=2)
    db.commit()
    db.close()
    r = client.post(f"/api/plans/{plan['id']}/check", headers=auth)
    assert r.status_code == 200 and r.json()["busy"] is None


def test_starting_the_backend_releases_busy_plans(client, auth, snow, monkeypatch):
    setup_ai(client, auth, monkeypatch)
    _, plan = plan_from_chat(client, auth, monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("Ready.")], "x")
    from app.db import SessionLocal, init_db
    from app.models import Plan
    db = SessionLocal()
    p = db.get(Plan, plan["id"])
    p.busy, p.busy_since = "deploying", datetime.now(UTC)
    db.commit()
    db.close()
    init_db()
    assert client.get(f"/api/plans/{plan['id']}", headers=auth).json()["busy"] is None

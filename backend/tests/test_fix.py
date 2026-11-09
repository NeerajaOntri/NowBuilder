"""Chunk 3: Fix with AI, and editing a row by hand."""
import json

from app.routers import chats

from .test_chat import ScriptedLLM, events, ready, send, text_turn, use_llm  # noqa: F401
from .test_plans import BR, json_turn, one_rule, plan_turn

GOOD_CONDITION = "current.caller_id.vip == true"
BAD = {**BR, "record": {**BR["record"], "condition": "current.u_phantom == true"}}
FIXED_RECORD = {**BR["record"], "condition": GOOD_CONDITION}


def fix_turn(changes, summary="Used caller_id, which the table has.", confidence="high", question=""):
    return json_turn({"summary": summary, "confidence": confidence, "question": question, "changes": changes})


def plan_with_a_problem(client, ready, monkeypatch, generated=BAD):
    """A plan whose one row fails the instance check (it uses a field incident doesn't have)."""
    llm = use_llm(monkeypatch, [plan_turn(one_rule()), json_turn(generated), text_turn("One problem.")])
    chat = client.post("/api/chats", headers=ready).json()
    send(client, ready, chat["id"], "VIP callers should get priority 1")
    plan = client.get(f"/api/chats/{chat['id']}", headers=ready).json()["plans"][0]
    return plan, llm


def fix(client, auth, plan_id, ids):
    r = client.post(f"/api/plans/{plan_id}/fix", json={"ids": ids}, headers=auth)
    return r, events(r)


def test_fix_sends_the_problems_to_the_model_and_waits_for_the_user(client, ready, monkeypatch):
    plan, _ = plan_with_a_problem(client, ready, monkeypatch)
    llm = use_llm(monkeypatch, [fix_turn([{"id": "c1", "reason": "u_phantom isn't on incident", "record": FIXED_RECORD,
                                           "script": BR["script"]}])])
    r, evs = fix(client, ready, plan["id"], ["c1"])
    assert r.status_code == 200 and evs[-1]["type"] == "done"
    sent = llm.calls[0]
    assert "u_phantom" in sent["messages"][0]["content"]          # the model is told the real problem
    assert "Fixing an artifact" in sent["system"]
    assert '<skill name="servicenow-business-rules">' in sent["system"]

    proposal = next(e for e in evs if e["type"] == "fix")["fix"]
    assert proposal["status"] == "pending" and proposal["confidence"] == "high"
    # nothing has changed in the plan yet
    after = client.get(f"/api/plans/{plan['id']}", headers=ready).json()
    assert after["components"][0]["generated"]["record"]["condition"] == "current.u_phantom == true"
    assert after["validation"]["errors"] == 1 and len(after["fixes"]) == 1


def test_applying_a_fix_swaps_the_row_over_and_checks_it_again(client, ready, monkeypatch):
    plan, _ = plan_with_a_problem(client, ready, monkeypatch)
    use_llm(monkeypatch, [fix_turn([{"id": "c1", "reason": "wrong field", "record": FIXED_RECORD, "script": BR["script"]}])])
    _, evs = fix(client, ready, plan["id"], ["c1"])
    fix_id = next(e for e in evs if e["type"] == "fix")["fix"]["id"]

    out = client.post(f"/api/plans/{plan['id']}/fixes/{fix_id}/apply", headers=ready).json()
    assert out["components"][0]["generated"]["record"]["condition"] == GOOD_CONDITION
    assert out["components"][0]["problems"] == [] and out["validation"]["errors"] == 0
    assert out["fixes"][0]["status"] == "applied"
    # applying twice is refused rather than repeated
    assert client.post(f"/api/plans/{plan['id']}/fixes/{fix_id}/apply", headers=ready).status_code == 409


def test_rejecting_a_fix_leaves_the_row_exactly_as_it_was(client, ready, monkeypatch):
    plan, _ = plan_with_a_problem(client, ready, monkeypatch)
    use_llm(monkeypatch, [fix_turn([{"id": "c1", "reason": "wrong field", "record": FIXED_RECORD, "script": BR["script"]}])])
    _, evs = fix(client, ready, plan["id"], ["c1"])
    fix_id = next(e for e in evs if e["type"] == "fix")["fix"]["id"]

    out = client.post(f"/api/plans/{plan['id']}/fixes/{fix_id}/reject", headers=ready).json()
    assert out["components"][0]["generated"]["record"]["condition"] == "current.u_phantom == true"
    assert out["components"][0]["status"] == "ready" and out["fixes"][0]["status"] == "rejected"


def test_a_fix_that_needs_a_decision_asks_instead_of_guessing(client, ready, monkeypatch):
    plan, _ = plan_with_a_problem(client, ready, monkeypatch)
    use_llm(monkeypatch, [fix_turn([], summary="I need to know which field marks a VIP.",
                                   confidence="low", question="incident has no u_phantom. Which field marks a VIP caller?")])
    _, evs = fix(client, ready, plan["id"], ["c1"])
    proposal = next(e for e in evs if e["type"] == "fix")["fix"]
    assert proposal["status"] == "needs_user_input" and "Which field" in proposal["question"]
    assert proposal["changes"] == []


def test_a_fix_that_breaks_another_rule_comes_straight_back(client, ready, monkeypatch):
    """The model's answer is checked before it is offered, so it can't trade one problem for another."""
    plan, _ = plan_with_a_problem(client, ready, monkeypatch)
    breaks_es5 = {**BR["record"], "condition": GOOD_CONDITION}
    bad_fix = fix_turn([{"id": "c1", "reason": "x", "record": breaks_es5,
                         "script": "(function(){ const f = () => 1; })();"}])
    good_fix = fix_turn([{"id": "c1", "reason": "x", "record": breaks_es5, "script": BR["script"]}])
    use_llm(monkeypatch, [bad_fix, good_fix])
    _, evs = fix(client, ready, plan["id"], ["c1"])
    fix_id = next(e for e in evs if e["type"] == "fix")["fix"]["id"]
    out = client.post(f"/api/plans/{plan['id']}/fixes/{fix_id}/apply", headers=ready).json()
    assert out["validation"]["errors"] == 0


def test_the_model_cannot_touch_rows_it_was_not_asked_to_fix(client, ready, monkeypatch):
    plan, _ = plan_with_a_problem(client, ready, monkeypatch)
    wrong_row = fix_turn([{"id": "c9", "reason": "x", "record": FIXED_RECORD, "script": BR["script"]}])
    right_row = fix_turn([{"id": "c1", "reason": "x", "record": FIXED_RECORD, "script": BR["script"]}])
    llm = use_llm(monkeypatch, [wrong_row, right_row])
    _, evs = fix(client, ready, plan["id"], ["c1"])
    assert "isn't one of the rows you were asked to fix" in llm.calls[1]["messages"][-1]["content"]
    assert next(e for e in evs if e["type"] == "fix")["fix"]["changes"][0]["id"] == "c1"


def test_a_waiting_fix_is_still_there_after_a_reload(client, ready, monkeypatch):
    plan, _ = plan_with_a_problem(client, ready, monkeypatch)
    use_llm(monkeypatch, [fix_turn([{"id": "c1", "reason": "wrong field", "record": FIXED_RECORD, "script": BR["script"]}])])
    fix(client, ready, plan["id"], ["c1"])
    chat_id = client.get(f"/api/plans/{plan['id']}", headers=ready).json()["chat_id"]
    [reloaded] = client.get(f"/api/chats/{chat_id}", headers=ready).json()["plans"]
    assert [f["status"] for f in reloaded["fixes"]] == ["pending"]


def test_fix_needs_the_build_role_and_an_ai_provider(client, ready, auth, monkeypatch):
    plan, _ = plan_with_a_problem(client, ready, monkeypatch)
    other = client.post("/api/auth/register", json={"first_name": "Sam", "last_name": "Ray", "email": "s@example.com",
                                                    "password": "secret123"}).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.post(f"/api/plans/{plan['id']}/fix", json={"ids": ["c1"]}, headers=headers).status_code == 404


# ---------- editing by hand ----------

def test_editing_a_script_rechecks_that_row(client, ready, monkeypatch):
    plan, _ = plan_with_a_problem(client, ready, monkeypatch)
    out = client.patch(f"/api/plans/{plan['id']}/components/c1",
                       json={"record": {"condition": GOOD_CONDITION}}, headers=ready).json()
    assert out["components"][0]["edited"] and out["validation"]["errors"] == 0

    broken = client.patch(f"/api/plans/{plan['id']}/components/c1",
                          json={"script": "(function(){ const x = () => 1; })();"}, headers=ready).json()
    assert broken["validation"]["errors"] >= 1
    assert any("ES6" in p["message"] for p in broken["components"][0]["problems"])


def test_editing_what_cannot_be_edited_is_a_plain_message(client, ready, monkeypatch):
    plan, _ = plan_with_a_problem(client, ready, monkeypatch)
    assert client.patch(f"/api/plans/{plan['id']}/components/nope", json={"script": "x"}, headers=ready).status_code == 400
    r = client.patch(f"/api/plans/{plan['id']}/components/c1", json={}, headers=ready)
    assert r.status_code == 400 and "script or the record" in r.json()["detail"]

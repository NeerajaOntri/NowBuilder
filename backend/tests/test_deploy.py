"""Chunk 4: approve, deploy into an update set, roll back, and push to Git."""
import pytest

from app.services import deploy as deploy_svc

from .conftest import connect_instance
from .test_chat import events, ready, send, text_turn, use_llm  # noqa: F401
from .test_plans import BR, SI, json_turn, one_rule, plan_turn

UI_POLICY = {
    "record": {"short_description": "Vendor shows for hardware", "table": "incident", "conditions": "category=hardware",
               "on_load": "true", "reverse_if_false": "true", "run_scripts": "false", "active": "true"},
    "actions": [{"field": "subcategory", "mandatory": "true", "visible": "true", "disabled": "false"}],
}


def built_plan(client, auth, monkeypatch, components=None, generated=(BR,)):
    turns = [plan_turn(components or one_rule()), *[json_turn(g) for g in generated], text_turn("Ready.")]
    use_llm(monkeypatch, turns)
    chat = client.post("/api/chats", headers=auth).json()
    send(client, auth, chat["id"], "VIP callers should get priority 1")
    return client.get(f"/api/chats/{chat['id']}", headers=auth).json()["plans"][0]


def approve(client, auth, plan, ids=None):
    return client.post(f"/api/plans/{plan['id']}/approve",
                       json={"ids": ids or [c["id"] for c in plan["components"]]}, headers=auth)


def deploy(client, auth, plan_id, name="STRY-1 VIP priority", **extra):
    r = client.post(f"/api/plans/{plan_id}/deploy", json={"update_set_name": name, **extra}, headers=auth)
    return r, (events(r) if r.status_code == 200 else [])


def rollback(client, auth, plan_id):
    r = client.post(f"/api/plans/{plan_id}/rollback", headers=auth)
    return r, (events(r) if r.status_code == 200 else [])


def final_plan(evs):
    return [e for e in evs if e["type"] == "plan"][-1]["plan"]


# ---------- approve ----------

def test_approve_locks_in_the_rows_and_blocks_ones_with_problems(client, ready, monkeypatch):
    bad = {**BR, "record": {**BR["record"], "condition": "current.u_phantom == true"}}
    plan = built_plan(client, ready, monkeypatch, generated=(bad,))
    r = approve(client, ready, plan)
    assert r.status_code == 409 and "problems to fix first" in r.json()["detail"]

    good = built_plan(client, ready, monkeypatch)
    out = approve(client, ready, good).json()
    assert out["status"] == "approved" and out["approval"]["ids"] == ["c1"]
    assert client.post(f"/api/plans/{good['id']}/unapprove", headers=ready).json()["status"] == "draft"


def test_only_a_reviewer_or_above_can_approve(client, ready, monkeypatch, db_viewer=None):
    plan = built_plan(client, ready, monkeypatch)
    other = client.post("/api/auth/register", json={"first_name": "Sam", "last_name": "Ray",
                                                    "email": "sam@example.com", "password": "secret123"}).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert approve(client, headers, plan).status_code == 404     # not in the workspace at all


# ---------- deploy ----------

def test_deploy_writes_into_a_new_update_set_and_leaves_it_current(client, ready, snow, monkeypatch):
    before = snow.add("sys_user_preference", name="sys_update_set", user=snow.user_sys_id, value="previous-set")
    plan = built_plan(client, ready, monkeypatch)
    approve(client, ready, plan)

    r, evs = deploy(client, ready, plan["id"])
    assert r.status_code == 200 and evs[-1]["type"] == "done"
    out = final_plan(evs)
    assert out["deployment"]["status"] == "deployed" and out["status"] == "deployed"

    # the artifact is in the instance
    [rule] = snow.tables["sys_script"]
    assert rule["name"] == "VIP callers get priority 1" and rule["script"] == BR["script"]
    # a new update set was made and the user's previous one is back
    [update_set] = snow.tables["sys_update_set"]
    assert update_set["name"] == "STRY-1 VIP priority" and update_set["state"] == "in progress"
    # the new set stays the user's current update set, so the instance's update set picker shows it
    assert before["value"] == update_set["sys_id"]
    assert out["deployment"]["update_set_current"] is True
    # the instance captured the change into that set
    assert out["deployment"]["captured"] == 1
    assert [x["update_set"] for x in snow.tables["sys_update_xml"]] == [update_set["sys_id"]]
    assert out["components"][0]["deploy"]["status"] == "deployed"



def test_the_previous_update_set_can_be_put_back_instead(client, ready, snow, monkeypatch):
    monkeypatch.setenv("NOWBUILDER_KEEP_UPDATE_SET_CURRENT", "false")
    before = snow.add("sys_user_preference", name="sys_update_set", user=snow.user_sys_id, value="previous-set")
    plan = built_plan(client, ready, monkeypatch)
    approve(client, ready, plan)
    deploy(client, ready, plan["id"])
    assert before["value"] == "previous-set"

def test_deploy_needs_approval_first(client, ready, monkeypatch):
    plan = built_plan(client, ready, monkeypatch)
    r, evs = deploy(client, ready, plan["id"])
    assert [e for e in evs if e["type"] == "error"][0]["message"] == "Approve the plan before deploying it."
    assert client.get(f"/api/plans/{plan['id']}", headers=ready).json()["deployment"] is None


def test_a_ui_policy_takes_its_field_actions_with_it(client, ready, snow, monkeypatch):
    rows = [{"id": "c1", "type": "ui_policy", "name": "Vendor policy", "table": "incident", "purpose": "show vendor"}]
    plan = built_plan(client, ready, monkeypatch, components=rows, generated=(UI_POLICY,))
    approve(client, ready, plan)
    _, evs = deploy(client, ready, plan["id"])

    [policy] = snow.tables["sys_ui_policy"]
    [action] = snow.tables["sys_ui_policy_action"]
    assert action["ui_policy"] == policy["sys_id"] and action["field"] == "subcategory"
    assert final_plan(evs)["deployment"]["records"][0]["children"][0]["table"] == "sys_ui_policy_action"


def test_dependencies_decide_the_deploy_order(client, ready, snow, monkeypatch):
    rows = [{"id": "c1", "type": "business_rule", "name": "rule", "table": "incident", "purpose": "p", "dependsOn": ["c2"]},
            {"id": "c2", "type": "script_include", "name": "helper", "purpose": "p"}]
    plan = built_plan(client, ready, monkeypatch, components=rows, generated=(SI, BR))
    approve(client, ready, plan)
    _, evs = deploy(client, ready, plan["id"])
    order = [e["text"] for e in evs if e["type"] == "status" and "Deploying" in e["text"]]
    assert "script include" in order[0] and "business rule" in order[1]


def test_changing_an_existing_artifact_updates_it_and_remembers_what_was_there(client, ready, snow, monkeypatch):
    existing = snow.add("sys_script", name="Old rule", collection="incident", script="// old", when="before",
                        order="100", active="true", action_insert="true", action_update="false",
                        action_delete="false", action_query="false", condition="", filter_condition="", description="")
    rows = one_rule(action="update", sys_id=existing["sys_id"])
    plan = built_plan(client, ready, monkeypatch, components=rows)
    approve(client, ready, plan)
    _, evs = deploy(client, ready, plan["id"])

    assert len(snow.tables["sys_script"]) == 1 and existing["script"] == BR["script"]
    record = final_plan(evs)["deployment"]["records"][0]
    assert record["action"] == "update" and record["before"]["script"] == "// old"

    _, revs = rollback(client, ready, plan["id"])
    assert existing["script"] == "// old"                      # put back as it was
    assert final_plan(revs)["deployment"]["status"] == "rolled_back"


def test_production_needs_confirming(client, ready, snow, monkeypatch):
    connect_instance(client, ready, name="Prod", url="prod99", instance_type="Production")
    instances = client.get("/api/instances", headers=ready).json()
    prod = next(o for o in instances if o["name"] == "Prod")
    client.post(f"/api/instances/{prod['id']}/select", headers=ready)

    plan = built_plan(client, ready, monkeypatch)
    approve(client, ready, plan)
    r, _ = deploy(client, ready, plan["id"])
    assert r.status_code == 400 and "production instance" in r.json()["detail"]
    r2, evs = deploy(client, ready, plan["id"], confirm_production=True)
    assert r2.status_code == 200 and final_plan(evs)["deployment"]["status"] == "deployed"


def test_an_instance_that_does_not_capture_the_change_is_reported(client, ready, snow, monkeypatch):
    snow.captures = False
    plan = built_plan(client, ready, monkeypatch)
    approve(client, ready, plan)
    _, evs = deploy(client, ready, plan["id"])
    deployment = final_plan(evs)["deployment"]
    # the artifacts did land, so this stays "deployed"; only the update set is in question
    assert deployment["status"] == "deployed" and deployment["captured"] == 0
    assert "captured none of them" in deployment["message"]
    assert len(snow.tables["sys_script"]) == 1
    assert [e["message"] for e in evs if e["type"] == "warning"]


def test_a_failure_part_way_keeps_what_went_in_and_says_so(client, ready, snow, monkeypatch):
    rows = [{"id": "c1", "type": "script_include", "name": "helper", "purpose": "p"},
            {"id": "c2", "type": "business_rule", "name": "rule", "table": "incident", "purpose": "p",
             "dependsOn": ["c1"]}]
    plan = built_plan(client, ready, monkeypatch, components=rows, generated=(SI, BR))
    approve(client, ready, plan)
    snow.forbidden.add("sys_script")                            # the rule can't be written
    _, evs = deploy(client, ready, plan["id"])

    out = final_plan(evs)
    assert out["deployment"]["status"] == "partial" and out["deployment"]["ids"] == ["c1"]
    assert len(snow.tables["sys_script_include"]) == 1
    statuses = {c["id"]: c["deploy"]["status"] for c in out["components"]}
    assert statuses == {"c1": "deployed", "c2": "not deployed"}
    assert [e for e in evs if e["type"] == "error"]

    snow.forbidden.clear()
    _, revs = rollback(client, ready, plan["id"])
    assert snow.tables["sys_script_include"] == []              # the part that went in is taken back out


def test_rollback_deletes_what_was_created(client, ready, snow, monkeypatch):
    rows = [{"id": "c1", "type": "ui_policy", "name": "Vendor policy", "table": "incident", "purpose": "p"}]
    plan = built_plan(client, ready, monkeypatch, components=rows, generated=(UI_POLICY,))
    approve(client, ready, plan)
    deploy(client, ready, plan["id"])
    assert snow.tables["sys_ui_policy"] and snow.tables["sys_ui_policy_action"]

    _, evs = rollback(client, ready, plan["id"])
    assert snow.tables["sys_ui_policy"] == [] and snow.tables["sys_ui_policy_action"] == []
    out = final_plan(evs)
    assert out["deployment"]["status"] == "rolled_back" and out["components"][0]["deploy"]["status"] == "rolled back"
    # rolling back twice is refused
    r, evs2 = rollback(client, ready, plan["id"])
    assert "nothing deployed to roll back" in [e for e in evs2 if e["type"] == "error"][0]["message"]


def test_deploying_twice_is_refused_until_it_is_rolled_back(client, ready, snow, monkeypatch):
    plan = built_plan(client, ready, monkeypatch)
    approve(client, ready, plan)
    deploy(client, ready, plan["id"])
    _, evs = deploy(client, ready, plan["id"])
    assert "already deployed" in [e for e in evs if e["type"] == "error"][0]["message"]
    assert len(snow.tables["sys_script"]) == 1                   # nothing written twice


def test_a_viewer_can_read_the_plan_but_not_deploy_or_approve(client, ready, snow, monkeypatch):
    from .test_workspace import join

    plan = built_plan(client, ready, monkeypatch)
    approve(client, ready, plan)
    viewer = join(client, ready, "v@example.com", "viewer")
    assert client.get(f"/api/plans/{plan['id']}", headers=viewer).status_code == 200
    assert deploy(client, viewer, plan["id"])[0].status_code == 403
    assert approve(client, viewer, plan).status_code == 403
    assert client.post(f"/api/plans/{plan['id']}/fix", json={"ids": ["c1"]}, headers=viewer).status_code == 403


# ---------- the files a plan becomes ----------

def test_files_for_a_plan_pair_each_script_with_its_settings(client, ready, monkeypatch):
    from app.models import Plan
    plan_row = Plan(chat_id="c", title="VIP", summary="s", components=[
        {"id": "c1", "type": "business_rule", "name": "VIP callers get priority 1", "generated": BR},
        {"id": "c2", "type": "ui_policy", "name": "Vendor policy", "generated": UI_POLICY},
        {"id": "c3", "type": "business_rule", "name": "not written", "generated": None},
    ])
    files = deploy_svc.files_for(plan_row)
    assert sorted(files) == [
        "servicenow/business_rule/vip_callers_get_priority_1.js",
        "servicenow/business_rule/vip_callers_get_priority_1.json",
        "servicenow/ui_policy/vendor_shows_for_hardware.json",
    ]
    assert files["servicenow/business_rule/vip_callers_get_priority_1.js"].endswith("\n")
    assert '"actions"' in files["servicenow/ui_policy/vendor_shows_for_hardware.json"]
    assert deploy_svc.files_for(plan_row, ids=["c2"]).keys() == {"servicenow/ui_policy/vendor_shows_for_hardware.json"}

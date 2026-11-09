"""Design document export, instance health check, and moving an update set to another instance."""
import io

from docx import Document

from .conftest import connect_instance
from .test_chat import text_turn
from .test_deploy import approve, deploy
from .test_deploy_button import plan_from_chat, setup_ai
from .test_plans import BR, json_turn, one_rule, plan_turn


def test_a_plan_downloads_as_a_design_document(client, auth, snow, monkeypatch):
    setup_ai(client, auth, monkeypatch)
    _, plan = plan_from_chat(client, auth, monkeypatch, [plan_turn(one_rule()), json_turn(BR), text_turn("Ready.")],
                             "VIP callers get priority 1")
    r = client.get(f"/api/plans/{plan['id']}/document", headers=auth)
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    text = "\n".join(p.text for p in Document(io.BytesIO(r.content)).paragraphs)
    cells = "\n".join(c.text for t in Document(io.BytesIO(r.content)).tables for row in t.rows for c in row.cells)
    assert "Components" in text and "Testing" in text
    assert plan["components"][0]["name"] in text and "Global" in cells


def test_the_health_check_reports_bad_practice_in_custom_scripts(client, auth, snow):
    inst = connect_instance(client, auth).json()
    snow.tables.setdefault("sys_script", []).append({
        "sys_id": "a" * 32, "name": "Bad rule", "collection": "incident", "when": "after", "active": "true",
        "advanced": "true", "sys_policy": "", "sys_created_by": "admin",
        "script": "(function executeRule(current, previous) {\n  current.state = 2;\n  current.update();\n})(current, previous);"})
    r = client.post(f"/api/instances/{inst['id']}/health", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["scanned"] >= 1
    bad = [f for f in body["findings"] if f["name"] == "Bad rule"]
    assert bad and "current.update" in " ".join(f["message"] for f in bad)
    assert bad[0]["url"].endswith("sys_script.do?sys_id=" + "a" * 32)


def test_an_update_set_moves_to_another_instance_as_a_retrieved_update_set(client, auth, snow):
    dev = connect_instance(client, auth).json()
    test_inst = connect_instance(client, auth, name="Test", url="dev999999", instance_type="Test").json()
    us = {"sys_id": "b" * 32, "name": "nowBuilder - VIP", "state": "in progress", "description": "", "application": "global"}
    snow.tables.setdefault("sys_update_set", []).append(us)
    snow.tables.setdefault("sys_remote_update_set", [])
    snow.tables.setdefault("sys_update_xml", []).append({
        "sys_id": "c" * 32, "update_set": "b" * 32, "name": "sys_script_" + "d" * 32, "type": "Business Rule",
        "target_name": "VIP", "action": "INSERT_OR_UPDATE", "payload": "<record_update/>", "category": "customer"})
    body = {"update_set_id": "b" * 32, "target_instance_id": test_inst["id"]}
    preview = client.post(f"/api/instances/{dev['id']}/promote", json=body, headers=auth).json()
    assert preview["updates"][0]["target"] == "VIP" and not snow.tables.get("sys_remote_update_set")
    r = client.post(f"/api/instances/{dev['id']}/promote", json={**body, "confirm": True}, headers=auth)
    assert r.status_code == 200, r.text
    done = r.json()
    assert done["copied"] == 1 and done["verified"] == 1 and "Preview" in done["next"]
    remote = snow.tables["sys_remote_update_set"][0]
    assert remote["state"] == "loaded" and remote["name"] == "nowBuilder - VIP"
    copies = [x for x in snow.tables["sys_update_xml"] if x.get("remote_update_set") == remote["sys_id"]]
    assert copies and copies[0]["payload"] == "<record_update/>"

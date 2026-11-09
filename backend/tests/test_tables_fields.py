"""The Tables topic: a prompt for a new table and its fields becomes table + field rows that deploy into
the instance (sys_db_object, sys_dictionary, sys_choice), and other rows can use the new fields."""
import json
import re
from pathlib import Path

import pytest

from app.ai import checks
from app.ai.artifacts import check, to_records

from .test_auto_deploy import ask, auto, auto_deploy_on, tool_results  # noqa: F401  (fixtures)
from .test_chat import text_turn
from .test_plans import json_turn, plan_turn

EXAMPLES = Path(__file__).resolve().parents[1] / "skills" / "nowbuilder" / "examples"


def examples(type_):
    return [json.loads(b) for b in re.findall(r"```json\n(.*?)```", (EXAMPLES / f"{type_}.md").read_text(), re.S)]


TABLE = examples("table")[0]                       # u_vendor_contract extends task
STATUS = examples("field")[3]                      # choice field with three values
VALUE = examples("field")[1]                       # currency
RULE = {"record": {"name": "Expire ended contracts", "collection": "u_vendor_contract", "when": "before", "order": "100",
                   "active": "true", "action_insert": "true", "action_update": "true", "action_delete": "false",
                   "action_query": "false", "condition": "", "filter_condition": "u_contract_status=active",
                   "description": "Sets expired when the end date has passed."},
        "script": "(function executeRule(current, previous) {\n    current.setValue('u_contract_status', 'expired');\n})(current, previous);"}


def test_a_table_its_fields_and_a_rule_on_them_deploy_in_order(client, auto, snow, monkeypatch):
    rows = [{"id": "c1", "type": "table", "name": "Vendor Contract", "purpose": "the table"},
            {"id": "c2", "type": "field", "name": "Contract status", "table": "u_vendor_contract", "purpose": "p", "dependsOn": ["c1"]},
            {"id": "c3", "type": "field", "name": "Contract value", "table": "u_vendor_contract", "purpose": "p", "dependsOn": ["c1"]},
            {"id": "c4", "type": "business_rule", "name": "Expire", "table": "u_vendor_contract", "purpose": "p",
             "dependsOn": ["c2"]}]
    llm, evs, plan = ask(client, auto, monkeypatch,
                         [plan_turn(rows), json_turn(TABLE), json_turn(STATUS), json_turn(VALUE), json_turn(RULE),
                          text_turn("Done.")], text="Create a table to track vendor contracts")
    # the rule uses fields that only exist once the plan is deployed: the checks know that
    assert plan["validation"]["errors"] == 0, [c.get("problems") for c in plan["components"]]
    assert plan["deployment"]["status"] == "deployed", plan["deployment"]
    table = next(t for t in snow.tables["sys_db_object"] if t["name"] == "u_vendor_contract")
    task = next(t for t in snow.tables["sys_db_object"] if t["name"] == "task")
    assert table["super_class"] == task["sys_id"]                  # the parent's sys_id, not its name
    fields = {f["element"]: f for f in snow.tables["sys_dictionary"] if f["name"] == "u_vendor_contract"}
    assert fields["u_contract_status"]["choice"] == "1" and fields["u_contract_value"]["internal_type"] == "currency"
    assert "reference" not in fields["u_contract_value"]          # empty settings aren't written
    choices = [c for c in snow.tables["sys_choice"] if c["name"] == "u_vendor_contract"]
    assert sorted(c["value"] for c in choices) == ["active", "draft", "expired"]
    assert all(c["element"] == "u_contract_status" and c["language"] == "en" for c in choices)
    order = [e["text"] for e in evs if e["type"] == "status" and e["text"].startswith("Deploying the ")]
    assert "table" in order[0] and "business rule" in order[-1]
    captured = {x["target_name"] for x in snow.tables["sys_update_xml"]}
    assert {"sys_db_object", "sys_dictionary", "sys_choice", "sys_script"} <= captured


def test_a_field_on_an_existing_table_deploys(client, auto, snow, monkeypatch):
    rows = [{"id": "c1", "type": "field", "name": "VIP caller", "table": "incident", "purpose": "flag"}]
    _, _, plan = ask(client, auto, monkeypatch, [plan_turn(rows), json_turn(examples("field")[4]), text_turn("Done.")],
                     text="add a VIP caller checkbox to incident")
    assert plan["deployment"]["status"] == "deployed"
    assert any(f["name"] == "incident" and f["element"] == "u_vip_caller" for f in snow.tables["sys_dictionary"])


def test_rollback_removes_the_fields_before_the_table(client, auto, snow, monkeypatch):
    rows = [{"id": "c1", "type": "table", "name": "Vendor Contract", "purpose": "t"},
            {"id": "c2", "type": "field", "name": "Status", "table": "u_vendor_contract", "purpose": "p", "dependsOn": ["c1"]}]
    _, _, plan = ask(client, auto, monkeypatch, [plan_turn(rows), json_turn(TABLE), json_turn(STATUS), text_turn("Done.")])
    from .test_chat import events
    evs = events(client.post(f"/api/plans/{plan['id']}/rollback", headers=auto))
    assert evs[-1]["type"] == "done"
    assert not any(t["name"] == "u_vendor_contract" for t in snow.tables["sys_db_object"])
    assert not any(f["name"] == "u_vendor_contract" for f in snow.tables["sys_dictionary"])


@pytest.mark.parametrize("type_,over,expected", [
    ("table", {"name": "vendor_contract"}, "named u_"),
    ("table", {"super_class": "sys_choice"}, "sys_choice"),
    ("field", {"element": "contract_value"}, "named u_"),
    ("field", {"internal_type": "reference", "reference": ""}, "needs the table it references"),
    ("field", {"mandatory": "true", "read_only": "true", "default_value": ""}, "needs a default value"),
])
def test_designs_servicenow_would_reject_are_caught(type_, over, expected):
    data = json.loads(json.dumps(TABLE if type_ == "table" else VALUE))
    data["record"].update(over)
    assert expected in " ".join(check(type_, data))


def test_a_choice_field_needs_choices_and_a_dropdown():
    data = json.loads(json.dumps(STATUS))
    data["record"]["choice"] = ""
    assert "choice 1" in " ".join(check("field", data))


def test_instance_checks_catch_duplicates_and_unknown_types(snow):
    from app.models import Instance
    from app.services.servicenow import ServiceNowClient
    inst = Instance(url="https://dev410284.service-now.com", username="admin", auth_method="basic")
    from app.security import encrypt
    inst.password_enc = encrypt("pw")
    reader = checks.InstanceReader(ServiceNowClient(inst, None))
    dup = {**VALUE["record"], "name": "incident", "element": "priority"}
    assert any("already has a field called priority" in p.message for p in checks._field_problems(dup, reader))
    bad_type = {**VALUE["record"], "internal_type": "glide_unicorn"}
    assert any("no field type called glide_unicorn" in p.message for p in checks._field_problems(bad_type, reader))
    assert any("already exists" in p.message for p in checks._table_problems({"name": "incident"}, reader))


def test_choice_records_are_linked_by_table_and_field():
    rows = to_records("field", STATUS)
    assert [r["table"] for r in rows] == ["sys_dictionary", "sys_choice", "sys_choice", "sys_choice"]
    assert rows[1]["parent_field"] is None and rows[1]["fields"]["name"] == "u_vendor_contract"

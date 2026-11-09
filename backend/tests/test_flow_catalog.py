"""The flow catalogue is generated from the SDK, so these tests guard the shape the rest of the
code relies on — run them after regenerating it with tools/build_flow_catalog.py."""
import json

from app.ai import flow_catalog
from app.ai.flow_sdk import NESTABLE, RUN_AS, STANDALONE, UNSUPPORTED_WRAPPERS


def test_every_action_has_an_api_name_and_typed_inputs():
    for name, a in flow_catalog.catalog()["actions"].items():
        assert a["api"].startswith("action.core."), name
        assert a["sys_id"] and len(a["sys_id"]) == 32, name
        for key, f in a["inputs"].items():
            assert f["type"], f"{name}.{key} has no type"
            assert isinstance(f["mandatory"], bool), f"{name}.{key}"


def test_every_trigger_maps_to_a_real_fluent_path():
    for name, t in flow_catalog.catalog()["triggers"].items():
        assert t["api"].split(".")[0] == "trigger" and len(t["api"].split(".")) == 3, name


def test_the_logic_blocks_the_exporter_knows_are_all_in_the_catalogue():
    """A typo in these sets would silently let a design through that the SDK can't express."""
    keys = set(flow_catalog.catalog()["logic"].values())
    for group in (NESTABLE, STANDALONE, UNSUPPORTED_WRAPPERS):
        assert group <= keys, group - keys


def test_run_as_matches_what_the_fluent_api_accepts():
    """The Flow API documents exactly two values: system and user."""
    assert set(RUN_AS.values()) == {"system", "user"}


def test_lookups_ignore_case_and_spacing():
    assert flow_catalog.action("  look up records  ")["api"] == "action.core.lookUpRecords"
    assert flow_catalog.action("Not An Action") is None
    assert flow_catalog.logic("end flow") == "endFlow"


def test_the_prompt_summary_stays_small_and_marks_mandatory_inputs():
    text = flow_catalog.summary_for_prompt(["Create Record", "Log"])
    assert "table_name*" in text and "values*" in text and "log_message" in text
    assert len(text) < 1000


def test_the_catalogue_file_is_valid_json_with_a_version():
    data = json.loads(flow_catalog.CATALOG_PATH.read_text(encoding="utf-8"))
    assert data["sdk_version"] and "tools/build_flow_catalog.py" in data["note"]

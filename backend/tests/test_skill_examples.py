"""The worked examples in skills/nowbuilder are what the model copies, so each one has to pass the
same checks a generated artifact does, and reach the prompt for its own type only."""
import json
import re
from pathlib import Path

import pytest

from app.ai import checks
from app.ai.flow_sdk import generate_flow_source
from app.ai.skills import get_skills

EXAMPLES = Path(__file__).resolve().parents[1] / "skills" / "nowbuilder" / "examples"


def blocks(path: Path) -> list[dict]:
    return [json.loads(b) for b in re.findall(r"```json\n(.*?)```", path.read_text(encoding="utf-8"), re.S)]


def type_of(file_type: str, data: dict) -> str:
    rec = data["record"]
    if "client_callable" in rec:
        return "script_include"
    if str(rec.get("type", "")).startswith("on"):
        return "client_script"
    return file_type


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.md")), ids=lambda p: p.stem)
def test_every_example_passes_the_generation_checks(path):
    found = blocks(path)
    assert found, f"{path.name} has no example"
    for data in found:
        assert checks.generation_problems(type_of(path.stem, data), data) == [], data["record"]


def test_every_flow_example_exports_to_fluent_source():
    flows = Path(__file__).resolve().parents[1] / "skills" / "nowbuilder" / "flows.md"
    exported = [generate_flow_source(d) for d in blocks(flows) if "record" in d]
    assert len(exported) >= 3


@pytest.mark.parametrize("type_", ["business_rule", "script_include", "client_script", "ui_policy", "ui_action", "notification"])
def test_each_type_gets_its_own_examples_and_not_the_others(type_):
    heading = {"business_rule": "business rule", "script_include": "script include", "client_script": "client script",
               "ui_policy": "UI policy", "ui_action": "UI action", "notification": "notification"}
    system = get_skills().build_prompt("generate", [type_]).system
    assert f"# Example: {heading[type_]}" in system
    for other in {"business_rule", "ui_policy", "ui_action", "notification"} - {type_}:
        assert f"# Example: {heading[other]}\n" not in system

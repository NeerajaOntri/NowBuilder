"""The Flow Designer vocabulary the ServiceNow SDK (Fluent) can express.

`data/flow_catalog.json` is generated from the SDK's own built-in definitions by
`tools/build_flow_catalog.py` — input names are not guessable and change between releases, so they
are read from the SDK rather than written by hand. Everything here is keyed by the display name
Flow Designer shows, which is also what `sys_hub_action_type_definition.name` holds, so a design,
the connected instance and the exporter all speak the same words.
"""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent / "data" / "flow_catalog.json"


@cache
def catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _by_lower(section: str) -> dict[str, str]:
    return {name.lower(): name for name in catalog()[section]}


@cache
def _action_index() -> dict[str, str]:
    return _by_lower("actions")


@cache
def _logic_index() -> dict[str, str]:
    return _by_lower("logic")


@cache
def _trigger_index() -> dict[str, str]:
    return _by_lower("triggers")


def sdk_version() -> str:
    return catalog().get("sdk_version", "")


def action(name: str) -> dict | None:
    """One action by its Flow Designer name, spelled however the design spelled it."""
    key = _action_index().get(str(name or "").strip().lower())
    return catalog()["actions"][key] if key else None


def action_names() -> list[str]:
    return sorted(catalog()["actions"])


def logic(name: str) -> str | None:
    """The wfa.flow_logic key for a logic block, e.g. 'If' -> 'if'."""
    key = _logic_index().get(str(name or "").strip().lower())
    return catalog()["logic"][key] if key else None


def logic_names() -> list[str]:
    return sorted(catalog()["logic"])


def trigger(name: str) -> dict | None:
    key = _trigger_index().get(str(name or "").strip().lower())
    return catalog()["triggers"][key] if key else None


def inputs_for(name: str) -> dict:
    return (action(name) or {}).get("inputs") or {}


def internal(key: str) -> bool:
    """`__snc_*` inputs are the flow engine's own plumbing. They exist on the instance but aren't
    part of the SDK's vocabulary and aren't something a design fills in, so they are ignored rather
    than reported as wrong."""
    return str(key).startswith("__snc")


# Input types the SDK build only accepts as fixed text. Learned from SDK 4.14.0:
#   TS228 "Datapills are not allowed in the ah_body field of sendEmail action. Please use a static string value."
# ah_body is the only Html-typed input in the core catalogue; the rule follows the type, not the action name.
STATIC_ONLY_TYPES = {"Html"}


def static_only_inputs(name: str) -> set[str]:
    """Inputs of this action that must be fixed text in Fluent source (no data pills)."""
    return {k for k, f in inputs_for(name).items() if f.get("type") in STATIC_ONLY_TYPES}


def missing_inputs(name: str, given: dict) -> list[str]:
    """Mandatory inputs of this action that the design didn't fill."""
    have = {k.lower() for k in (given or {})}
    return sorted(k for k, f in inputs_for(name).items() if f.get("mandatory") and k.lower() not in have)


def unknown_inputs(name: str, given: dict) -> list[str]:
    known = {k.lower() for k in inputs_for(name)}
    return sorted(k for k in (given or {}) if k.lower() not in known and not internal(k))


def summary_for_prompt(names: list[str] | None = None, limit: int = 12) -> str:
    """The actions and their inputs, small enough to put in a prompt."""
    chosen = [n for n in (names or action_names()) if action(n)][:limit]
    lines = []
    for n in chosen:
        a = action(n)
        bits = [f"{k}{'*' if f.get('mandatory') else ''}" for k, f in (a["inputs"] or {}).items()]
        outs = ", ".join((a["outputs"] or {}).keys())
        lines.append(f"- {n} — inputs: {', '.join(bits) or 'none'}" + (f"; outputs: {outs}" if outs else ""))
    return "\n".join(lines)

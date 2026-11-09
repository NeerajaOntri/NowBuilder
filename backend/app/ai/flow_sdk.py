"""Exports a flow design as ServiceNow SDK (Fluent) source, ready for `now-sdk build` / `now-sdk install`.

What the SDK can express is not a guess: `flow_catalog.py` reads it out of the SDK's own built-in
definitions, so every action name, input name and type here came from `@servicenow/sdk-core`. A
step the catalogue doesn't cover, or one the design left unstructured, fails closed and is named in
the report rather than quietly dropped.

Shape of the generated source (ServiceNow Fluent Flow API, Australia release docs):

    import { action, Flow, wfa, trigger } from '@servicenow/sdk/automation'
    export const my_flow = Flow({ $id, name, description, runAs },
        wfa.trigger(trigger.record.created, { $id }, { table, condition }),
        (params) => {
            const step1 = wfa.action(action.core.lookUpRecord, { $id }, { ...inputs })
            wfa.flowLogic.if({ $id, condition: `${wfa.dataPill(params.trigger.current.priority, 'string')}=1` },
                () => { ...steps inside the If })
            wfa.flowLogic.forEach(step2.Records, { $id }, (item) => { ...steps inside the loop })
        })

Nesting: a design step may say `inside: <step number>` to sit inside an earlier If / Else If /
Else / For Each step. If and Else If carry a `condition`; For Each carries `items` (a pill such as
`{{step2.Records}}`), and steps inside the loop read the current record as `{{item.<field>}}`.

A value of `{{plan.<component id>}}` is a reference to another row of the same plan (for example the
notification a Send Notification step selects). It is replaced by that row's deployed sys_id before
the source is generated (`resolve_plan_refs`); one left unresolved blocks the export.
"""
from __future__ import annotations

import contextvars
import copy
import json
import re

from . import flow_catalog

# Flow Designer's "Run as" setting, as the Fluent API spells it.
RUN_AS = {"System user": "system", "User who initiated session": "user"}

# Logic blocks that wrap other steps and that this exporter can write (Fluent Flow Logic API, SDK 4.14:
# wfa.flowLogic.if / elseIf / else / forEach, and doTheFollowing(..., () => { ...; wfa.flowLogic.until(cond) })
# for Flow Designer's "Do the following until").
NESTABLE = {"if", "elseIf", "else", "forEach", "doTheFollowingUntil"}
# Logic blocks that wrap other steps but aren't written by this exporter yet.
UNSUPPORTED_WRAPPERS = {"tryCatch", "doInParallel"}
# Logic that stands alone and needs no inputs.
STANDALONE = {"endFlow", "exitLoop", "skipIteration"}
# Logic that stands alone with its own settings: wfa.flowLogic.waitForADuration({ $id, durationType:
# 'explicit_duration', duration: Duration({ minutes: 2 }) }).
WAIT = "waitForADuration"
DURATION_UNITS = {"day": "days", "hour": "hours", "hr": "hours", "minute": "minutes", "min": "minutes",
                  "second": "seconds", "sec": "seconds"}

# {{trigger.current.sys_id}}, {{step2.Record.email}}, {{item.sys_id}}
PILL = re.compile(r"\{\{\s*(trigger\.[\w.]+|step\s*(\d+)\.[\w.]+|item(?:\.[\w.]+)?)\s*\}\}")
PLAN_REF = re.compile(r"\{\{\s*plan\.([\w-]+)\s*\}\}")
TIME = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")

REFERENCE_TYPES = {"Reference", "DocumentId", "Record", "Records"}
# Common reference fields on task, user and group tables: typed as references inside a condition.
REFERENCE_FIELDS = {"assignment_group", "assigned_to", "caller_id", "opened_by", "requested_for", "requested_by",
                    "manager", "cmdb_ci", "parent", "parent_incident", "problem_id", "company", "location",
                    "department", "business_service", "service_offering", "user", "group", "request_item"}
NUMBER_TYPES = {"Integer", "Decimal"}


class UnsupportedFlow(ValueError):
    pass


def _literal(value) -> str:
    return json.dumps(value, ensure_ascii=True)


def duration_parts(value) -> dict | None:
    """'2 minutes', '1 hour 30 minutes', '00:02:00', {"minutes": 2} -> {"minutes": 2}; None if unreadable."""
    if isinstance(value, dict):
        out = {k: int(v) for k, v in value.items() if k in ("days", "hours", "minutes", "seconds")
               and str(v).strip().lstrip("-").isdigit() and int(v) >= 0}
        return out if any(out.values()) else None
    text = str(value or "").strip().lower()
    m = re.fullmatch(r"(?:(\d+)\s+)?(\d{1,2}):(\d{2})(?::(\d{2}))?", text)
    if m:
        d, h, mi, sec = m.groups()
        out = {"days": int(d or 0), "hours": int(h), "minutes": int(mi), "seconds": int(sec or 0)}
        out = {k: v for k, v in out.items() if v}
        return out or None
    found = re.findall(r"(\d+)\s*(days?|hours?|hrs?|minutes?|mins?|seconds?|secs?)\b", text)
    if not found:
        return None
    out: dict[str, int] = {}
    for n, unit in found:
        key = DURATION_UNITS[unit.rstrip("s") if unit not in ("hrs", "mins", "secs") else unit[:-1]]
        out[key] = out.get(key, 0) + int(n)
    return out if any(out.values()) else None


PILL_LIST = re.compile(r"(\{\{[^}]+\}\})\s*(NOT IN|IN)\s*([^^]+)")


def expand_pill_lists(condition: str) -> str:
    """`{{step4.Record.stage}}IN a,b` -> `{{…}}=a^OR{{…}}=b` (NOT IN -> `!=` joined by `^`).

    A flow-logic condition whose left side is a data pill only accepts the comparison operators at run
    time: the instance reported "{0}IN300_nurturing,… is not a valid conditional expression". The Fluent
    docs' pill examples use `=` joined by `^OR`, which is the same test."""
    def one(m: re.Match) -> str:
        pill, op, values = m.group(1), m.group(2), [v.strip() for v in m.group(3).split(",") if v.strip()]
        if not values:
            return m.group(0)
        if op == "IN":
            return "^OR".join(f"{pill}={v}" for v in values)
        return "^".join(f"{pill}!={v}" for v in values)
    return PILL_LIST.sub(one, condition)


RECIPIENT_INPUTS = ("ah_to", "ah_cc", "ah_bcc", "to", "cc", "bcc")


def recipient_addresses(text: str) -> str:
    """Send Email's To / CC / BCC take email addresses. A pill of a user or group *record* sends its sys_id,
    which the instance rejects ("Email contained the following invalid recipient addresses: sys_user_group"),
    so a record pill is read through its email field: {{trigger.current.assignment_group}} ->
    {{trigger.current.assignment_group.email}} (users and groups both have one)."""
    def one(m: re.Match) -> str:
        path = re.sub(r"\s+", "", m.group(1))
        last = path.split(".")[-1].lower()
        if "email" in last or last in ("current", "record", "item") or path.startswith("plan."):
            return m.group(0)
        return "{{" + path + ".email}}"
    return PILL.sub(one, text)


def _identifier(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]+", "_", str(value).lower()).strip("_")[:55]
    if not cleaned or cleaned[0].isdigit():
        cleaned = "flow_" + cleaned
    return cleaned


def _step_var(step: int) -> str:
    return f"step{int(step)}"


def _kind(step: dict) -> str:
    return str(step.get("kind") or "").strip().lower()


def _logic_key(step: dict) -> str | None:
    return flow_catalog.logic(str(step.get("name") or "")) if _kind(step) == "flow logic" else None


def _pill_kind(path: str, field_type: str) -> str:
    """How to type a pill. The input's own type decides it where the catalogue knows it; otherwise a
    sys_id (or a whole record) is the reference it is, and anything else is read as a string."""
    if field_type in REFERENCE_TYPES:
        return "reference"
    if path.endswith(("sys_id", "Record")) or path == "item" or path.rsplit(".", 1)[-1] in REFERENCE_FIELDS:
        return "reference"
    return "string"


def _pill_expr(path: str) -> tuple[str, int | None]:
    """The JavaScript expression a pill path points at, and the step it reads (if any)."""
    path = re.sub(r"\s+", "", path)
    if path.startswith("trigger."):
        return f"params.{path}", None
    if path == "item" or path.startswith("item."):
        return path, None
    m = re.match(r"step(\d+)\.(.+)$", path)
    step = int(m.group(1))
    return f"{_step_var(step)}.{m.group(2)}", step


def _pills(text: str, field_type: str, used: set[int]) -> str:
    """A value with {{...}} placeholders becomes a template literal with wfa.dataPill() in it."""

    def one(m: re.Match, kind: str | None = None) -> str:
        expr, step = _pill_expr(m.group(1))
        if step is not None:
            used.add(step)
        k = kind or _pill_kind(re.sub(r"\s+", "", m.group(1)), "")
        return f"${{wfa.dataPill({expr}, '{k}')}}"

    whole = PILL.fullmatch(text.strip())
    if whole:
        # The whole value is one pill: pass it through rather than wrapping it in a string, and
        # type it properly. A pill surrounded by text is being concatenated, so it stays in a string.
        return one(whole, _pill_kind(re.sub(r"\s+", "", whole.group(1)), field_type))[2:-1]
    # Neutralise the template literal's own syntax in the design's text *before* the pills go in,
    # so a value containing a backtick or ${...} is data, not code.
    safe = text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    return "`" + PILL.sub(one, safe) + "`"


def _value(raw, field: dict, used: set[int], indent: str) -> str:
    field_type = str(field.get("type") or "")
    if isinstance(raw, dict):           # a Fields/values map, e.g. on Create Record or Update Record
        # One column per line: this is source a person reads before installing it.
        inner = {"type": "TemplateValue"}
        pairs = [f"{indent}  {_literal(k)}: {_value(v, inner, used, indent + '  ')}," for k, v in raw.items()]
        return "\n".join(["TemplateValue({", *pairs, indent + "})"])
    if isinstance(raw, bool):
        return "true" if raw else "false"
    if isinstance(raw, (int, float)):
        return json.dumps(raw)
    text = str(raw)
    if PILL.search(text):
        return _pills(text, field_type, used)
    if field_type == "Boolean" and text.lower() in ("true", "false"):
        return text.lower()
    if field_type in NUMBER_TYPES and re.fullmatch(r"-?\d+", text):
        return text
    return _literal(text)


# ---------- plan references ----------

def plan_refs(generated: dict) -> set[str]:
    """Component ids this design points at with {{plan.<id>}}."""
    return set(PLAN_REF.findall(json.dumps(generated.get("steps") or [])))


def resolve_plan_refs(generated: dict, sys_ids: dict[str, str]) -> dict:
    """A copy of the design with {{plan.<id>}} replaced by that row's deployed sys_id."""
    out = copy.deepcopy(generated)

    def sub(value):
        if isinstance(value, str):
            return PLAN_REF.sub(lambda m: sys_ids.get(m.group(1), m.group(0)), value)
        if isinstance(value, dict):
            return {k: sub(v) for k, v in value.items()}
        if isinstance(value, list):
            return [sub(v) for v in value]
        return value

    out["steps"] = sub(out.get("steps") or [])
    return out


# ---------- what can be exported ----------

def step_problem(step: dict, by_number: dict[int, dict] | None = None) -> str | None:
    """Why this step can't be exported, or None when it can."""
    by_number = by_number or {}
    name = str(step.get("name") or "").strip()
    kind = _kind(step)
    inside = step.get("inside")
    if inside not in (None, "", 0):
        parent = by_number.get(inside) if isinstance(inside, int) else None
        if parent is None or _logic_key(parent) not in NESTABLE:
            return f"{name}: 'inside' must name an earlier If, Else If, Else, For Each or Do the following until step."
        if int(inside) >= int(step.get("step") or 0):
            return f"{name}: it sits inside step {inside}, which has to come before it."
    if kind == "subflow":
        return f"{name}: subflows aren't exported."
    if kind == "flow logic":
        key = flow_catalog.logic(name)
        if not key:
            return f"{name} isn't one of Flow Designer's logic blocks."
        if key in UNSUPPORTED_WRAPPERS:
            return f"{name} isn't exported yet; build it in Flow Designer."
        if key in ("if", "elseIf") and not str(step.get("condition") or "").strip():
            return f"{name} needs its condition."
        if key == "forEach" and not PILL.fullmatch(str(step.get("items") or "").strip()):
            return f"{name} needs the records to loop over, e.g. {{{{step2.Records}}}}."
        if key == "doTheFollowingUntil" and not str(step.get("condition") or "").strip():
            return (f"{name} needs its 'until' condition (an encoded query, e.g. "
                    "{{step3.Record.state}}IN6,7), checked after each pass.")
        if key == WAIT:
            return None if duration_parts(step.get("duration")) else \
                f"{name} needs a duration, e.g. \"2 minutes\" or \"00:02:00\"."
        if key not in NESTABLE and key not in STANDALONE:
            return f"{name} isn't exported yet; build it in Flow Designer."
        return None
    spec = flow_catalog.action(name)
    if not spec:
        return f"The SDK has no core action called '{name}'."
    inputs = step.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        return f"{name}: the design gives no inputs, only a description."
    if unknown := flow_catalog.unknown_inputs(name, inputs):
        return f"{name}: no input called {', '.join(unknown)}."
    if missing := flow_catalog.missing_inputs(name, inputs):
        return f"{name}: {', '.join(missing)} is required." if len(missing) == 1 else \
               f"{name}: {', '.join(missing)} are required."
    return None


def pills_in_static_inputs(name: str, inputs: dict) -> list[str]:
    """Inputs the ServiceNow SDK only takes as fixed text (Send Email's ah_body: "does NOT support data pills",
    Fluent action API) that the design fills with pills."""
    static = {k.lower() for k in flow_catalog.static_only_inputs(name)}
    return sorted(k for k, v in (inputs or {}).items() if k.lower() in static and PILL.search(str(v)))


def placeholder(path: str) -> str:
    """{{trigger.current.owner.name}} -> [Owner name]: what to drag in by hand."""
    parts = [p for p in re.sub(r"\s+", "", path).split(".") if p not in ("trigger", "current", "Record", "item")]
    parts = [re.sub(r"^step\d+$", "", p) for p in parts]
    words = " ".join(p.replace("_", " ") for p in parts if p).strip() or "value"
    return "[" + words[:1].upper() + words[1:] + "]"


def with_placeholders(text: str) -> str:
    return PILL.sub(lambda m: placeholder(m.group(1)), text)


TRIGGER_PATH = re.compile(r"trigger\.current(\.[A-Za-z0-9_]+)+")


def with_pill_references(text: str) -> str:
    """A static-only input (Send Email's body) with the trigger record's pills written the way Flow Designer
    itself stores a data pill in an input value: {{trigger.current.<field>}} (dot-walks included). The
    SDK takes it as fixed text; the flow engine resolves the references when it runs. Pills from other
    steps have no stable reference name, so they stay [placeholders]."""
    def one(m: re.Match) -> str:
        path = re.sub(r"\s+", "", m.group(1))
        return "{{" + path + "}}" if TRIGGER_PATH.fullmatch(path) else placeholder(path)
    return PILL.sub(one, text)


_STATIC_PILLS = contextvars.ContextVar("static_pills", default="references")


def static_pill_message(name: str, keys: list[str]) -> str:
    return (f"{name}: {', '.join(keys)} only takes fixed text in the ServiceNow SDK (Fluent action API: \"ah_body "
            "does NOT support data pills\"). Values from other steps can't be carried there: read the same fields "
            "from the trigger record ({{trigger.current.<field>}}, dot-walks allowed) - nowBuilder writes those as "
            "Flow Designer pill references the flow resolves when it runs - or they go in as [placeholders].")


def manual_pill_keys(value) -> list[str]:
    """Pills in a static-only value that can't be written as references (not the trigger record's)."""
    return [m.group(1) for m in PILL.finditer(str(value or ""))
            if not TRIGGER_PATH.fullmatch(re.sub(r"\s+", "", m.group(1)))]


def manual_pills(generated: dict) -> list[str]:
    """For the deploy result: which steps need pills dragged in by hand, and which."""
    out = []
    for step in generated.get("steps") or []:
        name = str(step.get("name") or "")
        for key in pills_in_static_inputs(name, step.get("inputs") or {}):
            holders = sorted({placeholder(m.group(1)) for m in PILL.finditer(str(step["inputs"][key]))
                              if not TRIGGER_PATH.fullmatch(re.sub(r"\s+", "", m.group(1)))})
            if holders:
                out.append(f"Step {step.get('step')} {name} {key}: {', '.join(holders)}")
    return out


# VALCHANGES, CHANGESFROM, CHANGESTO: "changes", "changes from", "changes to".
CHANGES_OPERATOR = re.compile(r"(VALCHANGES|CHANGESFROM|CHANGESTO)")


def _trigger_problems(rec: dict) -> list[str]:
    out: list[str] = []
    trigger = flow_catalog.trigger(str(rec.get("trigger") or ""))
    if not trigger:
        return [f"The SDK has no {rec.get('trigger') or 'empty'} trigger."]
    api = trigger["api"]
    if api.startswith("trigger.record.") and not re.fullmatch(r"[a-z][a-z0-9_]*", str(rec.get("table") or "")):
        out.append("A record trigger needs a valid table.")
    if api == "trigger.scheduled.daily" and not TIME.fullmatch(str(rec.get("schedule_time") or "").strip()):
        out.append("A daily trigger needs schedule_time as HH:MM.")
    if api.startswith("trigger.scheduled.") and api != "trigger.scheduled.daily":
        out.append(f"{rec.get('trigger')} schedules aren't exported yet; use Daily or build it in Flow Designer.")
    if api in ("trigger.record.created", "trigger.record.createdOrUpdated") and \
            CHANGES_OPERATOR.search(str(rec.get("trigger_condition") or "")):
        out.append(f"The trigger condition uses a 'changes' operator, which only works with an Updated trigger "
                   f"(Flow Designer shows 'Operator is unrecognized' on {rec.get('trigger')}). Use the Updated "
                   "trigger, or drop the 'changes' part for a Created trigger.")
    return out


def export_report(generated: dict) -> dict:
    """Whether this design exports, and what stops it. Never raises: the card shows it."""
    rec = generated.get("record") or {}
    steps = generated.get("steps") or []
    blockers = _trigger_problems(rec)
    if str(rec.get("run_as") or "User who initiated session") not in RUN_AS:
        blockers.append(f"Unrecognised run-as setting {rec.get('run_as')!r}.")
    if not steps:
        blockers.append("A flow needs at least one step.")
    by_number = {s.get("step"): s for s in steps if isinstance(s.get("step"), int)}
    per_step = [(s.get("step"), step_problem(s, by_number)) for s in steps]
    blockers += [f"Step {n}: {why}" for n, why in per_step if why]
    blockers += _else_problems(steps)
    return {"exportable": not blockers, "blockers": blockers,
            "steps_ready": sum(1 for _, why in per_step if not why), "steps": len(steps),
            "sdk_version": flow_catalog.sdk_version()}


def _else_problems(steps: list[dict]) -> list[str]:
    """An Else If or Else has to follow an If (or Else If) at the same level."""
    out = []
    prev_by_parent: dict = {}
    for s in steps:
        key = _logic_key(s)
        parent = s.get("inside") or None
        prev = prev_by_parent.get(parent)
        if key in ("elseIf", "else") and (prev is None or _logic_key(prev) not in ("if", "elseIf")):
            out.append(f"Step {s.get('step')}: {s.get('name')} has to come straight after an If or Else If at the same level.")
        prev_by_parent[parent] = s
    return out


# ---------- writing the source ----------

def _block(step: dict, identifier: str, children: dict, used: set[int], depth: int) -> list[str]:
    """One step (and anything inside it) as source lines."""
    pad = "    " * depth
    number = int(step.get("step") or 0)
    sid = _literal(f"{identifier}_step_{number}")
    annotation = _literal(str(step.get("detail") or "")[:200])
    key = _logic_key(step)
    if key is not None:
        inner: list[str] = []
        for child in children.get(number, []):
            inner += _block(child, identifier, children, used, depth + 2)
        if key in ("if", "elseIf"):
            text = expand_pill_lists(str(step.get("condition")))
            cond = _pills(text, "", used) if PILL.search(text) else _literal(text)
            return [f"{pad}wfa.flowLogic.{key}(",
                    f"{pad}    {{ $id: Now.ID[{sid}], condition: {cond}, annotation: {annotation} }},",
                    f"{pad}    () => {{", *inner, f"{pad}    }}",
                    f"{pad});"]
        if key == "else":
            return [f"{pad}wfa.flowLogic.else(",
                    f"{pad}    {{ $id: Now.ID[{sid}], annotation: {annotation} }},",
                    f"{pad}    () => {{", *inner, f"{pad}    }}",
                    f"{pad});"]
        if key == "doTheFollowingUntil":
            until = expand_pill_lists(str(step.get("condition")))
            until = _pills(until, "", used) if PILL.search(until) else _literal(until)
            label = _literal(str(step.get("label") or step.get("name") or "Do the following until")[:80])
            return [f"{pad}wfa.flowLogic.doTheFollowing(",
                    f"{pad}    {{ $id: Now.ID[{sid}], label: {label}, annotation: {annotation} }},",
                    f"{pad}    () => {{", *inner,
                    f"{pad}        wfa.flowLogic.until({until});",
                    f"{pad}    }}",
                    f"{pad});"]
        if key == WAIT:
            parts = duration_parts(step.get("duration")) or {}
            dur = ", ".join(f"{k}: {v}" for k, v in parts.items())
            return [f"{pad}wfa.flowLogic.waitForADuration({{ $id: Now.ID[{sid}], durationType: 'explicit_duration', "
                    f"duration: Duration({{ {dur} }}), annotation: {annotation} }});"]
        if key == "forEach":
            expr, ref = _pill_expr(PILL.fullmatch(str(step.get("items")).strip()).group(1))
            if ref is not None:
                used.add(ref)
            return [f"{pad}wfa.flowLogic.forEach(",
                    f"{pad}    {expr},",
                    f"{pad}    {{ $id: Now.ID[{sid}], annotation: {annotation} }},",
                    f"{pad}    (item) => {{", *inner, f"{pad}    }}",
                    f"{pad});"]
        return [f"{pad}wfa.flowLogic.{key}({{ $id: Now.ID[{sid}], annotation: {annotation} }});"]

    spec = flow_catalog.action(str(step.get("name") or ""))
    fields = spec["inputs"]
    pairs = []
    for k, raw in (step.get("inputs") or {}).items():
        if flow_catalog.internal(k):      # engine plumbing; the SDK sets its own
            continue
        real = next(f for f in fields if f.lower() == k.lower())
        if real.lower() in RECIPIENT_INPUTS and isinstance(raw, str):
            raw = recipient_addresses(raw)
        static = {x.lower() for x in flow_catalog.static_only_inputs(str(step.get("name") or ""))}
        if real.lower() in static and isinstance(raw, str) and PILL.search(raw):
            fill = with_pill_references if _STATIC_PILLS.get() == "references" else with_placeholders
            pairs.append(f"{pad}        {real}: {_literal(fill(raw))},")
            continue
        pairs.append(f"{pad}        {real}: {_value(raw, fields[real], used, pad + '        ')},")
    return [f"{pad}wfa.action(",
            f"{pad}    {spec['api']},",
            f"{pad}    {{ $id: Now.ID[{sid}], annotation: {annotation} }},",
            f"{pad}    {{", *pairs, f"{pad}    }}",
            f"{pad});"]


def _trigger_inputs(rec: dict, trigger: dict) -> list[str]:
    api = trigger["api"]
    if api == "trigger.scheduled.daily":
        h, m, s = TIME.fullmatch(str(rec.get("schedule_time")).strip()).groups()
        return [f"        time: Time({{ hours: {int(h)}, minutes: {int(m)}, seconds: {int(s or 0)} }}),"]
    inputs: dict[str, str] = {}
    if "table" in trigger["inputs"]:
        inputs["table"] = str(rec.get("table") or "")
    if "target_table" in trigger["inputs"] and rec.get("table"):
        inputs["target_table"] = str(rec.get("table"))
    condition = str(rec.get("trigger_condition") or "")
    if condition:
        if "condition" in trigger["inputs"]:
            inputs["condition"] = condition
        elif "email_conditions" in trigger["inputs"]:
            inputs["email_conditions"] = condition
    run_trigger = {"once": "once", "for each unique change": "unique_changes", "always": "always"}
    if str(rec.get("run_trigger") or "") in run_trigger and "trigger_strategy" in trigger["inputs"]:
        inputs["trigger_strategy"] = run_trigger[str(rec.get("run_trigger"))]
    if "run_flow_in" in trigger["inputs"] and api.startswith("trigger.record."):
        inputs["run_flow_in"] = "background"
    return [f"        {k}: {_literal(v)}," for k, v in inputs.items()]


def generate_flow_source(generated: dict, static_pills: str = "references") -> str:
    """The Fluent source for a flow design, or UnsupportedFlow saying exactly what stopped it.
    `static_pills`: "references" (pill references in static-only inputs) or "placeholders" ([Field])."""
    token = _STATIC_PILLS.set(static_pills)
    try:
        return _generate(generated)
    finally:
        _STATIC_PILLS.reset(token)


def has_static_pills(generated: dict) -> bool:
    return any(pills_in_static_inputs(str(s.get("name") or ""), s.get("inputs") or {})
               for s in generated.get("steps") or [])


def _generate(generated: dict) -> str:
    report = export_report(generated)
    if not report["exportable"]:
        raise UnsupportedFlow(" ".join(report["blockers"]))
    if unresolved := plan_refs(generated):
        raise UnsupportedFlow("The flow points at plan rows that haven't been deployed yet: "
                              + ", ".join(sorted(unresolved)) + ". Deploy them first.")

    rec = generated.get("record") or {}
    steps = generated.get("steps") or []
    name = str(rec.get("name") or "").strip()
    if not name:
        raise UnsupportedFlow("A flow needs a name.")
    identifier = _identifier(name)
    trigger = flow_catalog.trigger(str(rec.get("trigger")))
    run_as_api = RUN_AS[str(rec.get("run_as") or "User who initiated session")]
    condition = str(rec.get("trigger_condition") or "")
    if any(c in condition for c in ("\n", "\r", "\x00")):
        raise UnsupportedFlow("The trigger condition has control characters in it.")

    children: dict[int, list[dict]] = {}
    top: list[dict] = []
    for s in steps:
        parent = s.get("inside")
        (children.setdefault(int(parent), []) if parent else top).append(s)

    # Build the body first: it tells us which steps are read later and so need a variable.
    used: set[int] = set()
    body: list[str] = []
    for s in top:
        body += _block(s, identifier, children, used, 2)
    # Give a variable to every step a later step reads from.
    for i, line in enumerate(body):
        m = re.match(r"^(\s*)wfa\.action\($", line)
        if not m:
            continue
        sid = re.search(r'_step_(\d+)"', body[i + 2])
        if sid and int(sid.group(1)) in used:
            body[i] = f"{m.group(1)}const {_step_var(int(sid.group(1)))} = wfa.action("

    header = [f"// Generated by nowBuilder for the ServiceNow SDK (Fluent) {flow_catalog.sdk_version()}.",
              "// Review before installing: now-sdk build && now-sdk install",
              "// Fluent Flow API: wfa.trigger / wfa.action / wfa.flowLogic (servicenow.github.io/sdk/api/flow).",
              "// @ts-nocheck"]
    if run_as_api == "system":
        header.append("// Runs as the system user: this flow bypasses ACLs. Confirm that is intended.")
    description = str(rec.get("description") or "")
    return "\n".join([
        *header,
        "",
        "import { action, Flow, wfa, trigger } from '@servicenow/sdk/automation';",
        "",
        f"export const {identifier} = Flow(",
        "    {",
        f"        $id: Now.ID[{_literal(identifier)}],",
        f"        name: {_literal(name)},",
        f"        description: {_literal(description)},",
        f"        runAs: '{run_as_api}',",
        "    },",
        "    wfa.trigger(",
        f"        {trigger['api']},",
        f"        {{ $id: Now.ID[{_literal(identifier + '_trigger')}] }},",
        "        {",
        *["    " + ln for ln in _trigger_inputs(rec, trigger)],
        "        }",
        "    ),",
        "    (params) => {",
        *body,
        "    }",
        ");",
        "",
    ])

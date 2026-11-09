"""Chunk 3: checking a generated artifact before anyone deploys it.

Three kinds of problem, all reported the same way:

- **record**   the record and its script contradict each other (`artifacts.check`).
- **script**   a rule from the ServiceNow skills broken in the script: `current.update()` in a
               before rule, GlideRecord in a client script, a hard-coded sys_id, ES6 in a scope
               that runs ES5.
- **instance** a table or field the artifact uses that the connected instance doesn't have, or a
               script include it calls that is neither in the plan nor in the instance.

Errors block a deploy; warnings don't. Nothing here calls the model: checks are plain code, so
they are fast, free and the same every time.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from ..services.servicenow import ServiceNowClient, ServiceNowError
from . import flow_catalog
from .artifacts import check as record_check
from .artifacts import spec

ERROR, WARNING = "error", "warning"


@dataclass
class Problem:
    source: str      # record | script | instance
    severity: str    # error | warning
    message: str
    location: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


# ---------- script rules ----------

@dataclass(frozen=True)
class Rule:
    pattern: re.Pattern
    severity: str
    message: str
    types: tuple[str, ...] = ()          # artifact types it applies to; empty = all
    when: tuple[str, ...] = ()           # business rule "when" values it applies to
    skip_if: re.Pattern | None = None    # don't fire if this also matches


SERVER_TYPES = ("business_rule", "script_include", "ui_action", "scheduled_job", "script_action")
CLIENT_TYPES = ("client_script",)

RULES: tuple[Rule, ...] = (
    Rule(re.compile(r"\bcurrent\.update\s*\("), ERROR,
         "A before business rule must not call current.update(): set the fields on current and let ServiceNow save them.",
         types=("business_rule",), when=("before",)),
    Rule(re.compile(r"\bcurrent\.update\s*\("), ERROR,
         "An after business rule must not call current.update(): it saves the record again and runs every rule "
         "a second time. Change the fields in a before rule instead.",
         types=("business_rule",), when=("after",)),
    Rule(re.compile(r"\beval\s*\(|new\s+Function\s*\("), ERROR,
         "eval() and new Function() run whatever they are given: build the logic instead."),
    Rule(re.compile(r"""['"][0-9a-f]{32}['"]"""), WARNING,
         "This has a sys_id written into it, which won't exist in the next instance. Look the record up by a stable "
         "field, or read the sys_id from a system property."),
    Rule(re.compile(r"\bgs\.log\s*\("), WARNING,
         "gs.log() isn't available in a scoped application: use gs.info(), gs.warn() or gs.error().",
         types=SERVER_TYPES),
    Rule(re.compile(r"\bnew\s+GlideRecord\s*\("), ERROR,
         "A client script must not use GlideRecord: call a client-callable script include with GlideAjax instead.",
         types=CLIENT_TYPES),
    Rule(re.compile(r"\bgetXMLWait\s*\("), ERROR,
         "getXMLWait() freezes the browser until the server answers: use getXMLAnswer() with a callback.",
         types=CLIENT_TYPES),
    Rule(re.compile(r"\bdocument\.(getElementById|querySelector)|\$\s*\(\s*['\"#.]"), ERROR,
         "Reaching into the page with the DOM or jQuery breaks in Workspace and the Service Portal: use g_form.",
         types=CLIENT_TYPES),
    Rule(re.compile(r"\bg_form\.getReference\s*\(\s*[^,)]+\)"), WARNING,
         "g_form.getReference() without a callback is synchronous: pass a callback so the form doesn't freeze.",
         types=CLIENT_TYPES),
    Rule(re.compile(r"\bsetWorkflow\s*\(\s*false\s*\)"), WARNING,
         "setWorkflow(false) skips business rules, notifications and audit: only do this deliberately, and say why in a comment.",
         types=SERVER_TYPES),
    Rule(re.compile(r"\b(deleteMultiple|updateMultiple)\s*\("), WARNING,
         "deleteMultiple() and updateMultiple() change every matching record at once and can't be undone: check the query first.",
         types=SERVER_TYPES),
    Rule(re.compile(r"\bcatch\s*\([^)]*\)\s*\{\s*\}"), WARNING,
         "This catch block hides the error. Log it with gs.error() or handle it."),
    Rule(re.compile(r"=>"), ERROR,
         "Arrow functions are ES6. Write ES5 (function () { … }) unless the application scope runs in ES2021 mode."),
    Rule(re.compile(r"`"), ERROR,
         "Template literals are ES6. Join strings with + unless the application scope runs in ES2021 mode."),
    Rule(re.compile(r"^\s*(let|const)\s+\w+", re.M), ERROR,
         "let and const are ES6. Use var unless the application scope runs in ES2021 mode."),
    Rule(re.compile(r"\baddInfoMessage\s*\(\s*['\"]"), WARNING,
         "Wrap text people read in gs.getMessage() so it can be translated.", types=SERVER_TYPES),
)

# A GlideRecord query inside a loop: one query per row adds up fast. The loop's condition may
# itself hold brackets (`while (gr.next())`), so one level of nesting is allowed on both.
_LOOP_QUERY = re.compile(
    r"(?:while|for)\s*\((?:[^()]|\([^()]*\))*\)\s*\{(?:[^{}]|\{[^{}]*\})*?new\s+GlideRecord\s*\(", re.S)


def line_of(script: str, index: int) -> int:
    return script.count("\n", 0, index) + 1


def script_problems(type_: str, script: str, es2021: bool = False) -> list[Problem]:
    rec_when = ""
    return _script_problems(type_, script, rec_when, es2021)


def _script_problems(type_: str, script: str, when: str, es2021: bool) -> list[Problem]:
    out: list[Problem] = []
    if not script.strip():
        return out
    es6 = ("Arrow functions", "Template literals", "let and const")
    for rule in RULES:
        if rule.types and type_ not in rule.types:
            continue
        if rule.when and when not in rule.when:
            continue
        if es2021 and rule.message.startswith(es6):
            continue
        m = rule.pattern.search(script)
        if m:
            out.append(Problem("script", rule.severity, rule.message, f"line {line_of(script, m.start())}"))
    if type_ in SERVER_TYPES and (m := _LOOP_QUERY.search(script)):
        out.append(Problem("script", WARNING,
                           "This queries the database inside a loop, which runs one query per row. Query once with an "
                           "IN condition, or use GlideAggregate to count.", f"line {line_of(script, m.start())}"))
    return out


# ---------- what the artifact says it uses ----------

_FIELD_CALLS = re.compile(r"\b(?:getValue|setValue|getDisplayValue|setDisplayValue)\s*\(\s*['\"]([a-z0-9_]+)['\"]", re.I)
_CURRENT_FIELD = re.compile(r"\bcurrent\.([a-z][a-z0-9_]*)\b")
_GFORM_FIELD = re.compile(r"\bg_form\.\w+\s*\(\s*['\"]([a-z0-9_]+)['\"]", re.I)
_ENCODED_FIELD = re.compile(r"(?:^|\^)(?:OR)?([a-z][a-z0-9_]*)(?:ISNOTEMPTY|ISEMPTY|LIKE|STARTSWITH|IN|!=|>=|<=|=|>|<)", re.I)
# ${number} in a notification's subject or body. ${URI_REF} and ${mail_script:…} aren't fields.
_SUBSTITUTION = re.compile(r"\$\{([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)*)\}")
_NEW_GLIDERECORD = re.compile(r"new\s+GlideRecord\s*\(\s*['\"]([a-z0-9_]+)['\"]")
_NEW_CLASS = re.compile(r"new\s+(?:[A-Za-z_][\w]*\.)?([A-Z][A-Za-z0-9_]*)\s*\(")

# Names that look like fields but aren't columns on the table
NOT_FIELDS = {"update", "insert", "setValue", "getValue", "setAbortAction", "isNewRecord", "operation",
              "getUniqueValue", "getTableName", "canWrite", "canRead", "addErrorMessage", "variables",
              "getDisplayValue", "setDisplayValue", "isValidField", "autoSysFields", "setWorkflow", "initialize"}
# Classes that are ServiceNow's, not a script include the plan has to provide
PLATFORM_CLASSES = {"GlideRecord", "GlideRecordSecure", "GlideAggregate", "GlideDateTime", "GlideDate", "GlideTime",
                    "GlideDuration", "GlideSchedule", "GlideSysAttachment", "GlideAjax", "GlideModal", "GlideDialogWindow",
                    "GlideQuery", "GlideFilter", "GlideEncrypter", "GlideSecurityManager", "GlideElement", "Class",
                    "Date", "Array", "Object", "String", "Number", "RegExp", "Error", "JSON", "Math"}


def fields_used(type_: str, record: dict, script: str) -> set[str]:
    """Field names the artifact uses on the table it runs on."""
    sp = spec(type_)
    found: set[str] = set()
    for key in ("condition", "filter_condition", "conditions", "trigger_condition"):
        for m in _ENCODED_FIELD.finditer(str(record.get(key) or "")):
            found.add(m.group(1).lower())
    if record.get("field_name"):
        found.add(str(record["field_name"]).lower())
    if type_ == "notification":
        # who it goes to, and the ${field} substitutions in the subject and body
        found |= {f.strip().lower().split(".")[0] for f in str(record.get("recipient_fields") or "").split(",") if f.strip()}
        for key in ("subject", "message_html", "message"):
            for m in _SUBSTITUTION.finditer(str(record.get(key) or "")):
                found.add(m.group(1).lower().split(".")[0])
        return {f for f in found if f}
    text = (script or "") + "\n" + str(record.get("condition") or "")
    if type_ in CLIENT_TYPES:
        found |= {m.group(1).lower() for m in _GFORM_FIELD.finditer(text)}
    else:
        found |= {m.group(1).lower() for m in _CURRENT_FIELD.finditer(text)}
        found |= {m.group(1).lower() for m in _FIELD_CALLS.finditer(text)}
    if sp.table_field:
        found.discard(str(record.get(sp.table_field) or "").lower())
    return {f for f in found if f and f not in {n.lower() for n in NOT_FIELDS}}


def tables_used(script: str) -> set[str]:
    return {m.group(1).lower() for m in _NEW_GLIDERECORD.finditer(script or "")}


def classes_used(script: str) -> set[str]:
    return {m.group(1) for m in _NEW_CLASS.finditer(script or "")} - PLATFORM_CLASSES


# ---------- checking against the connected instance ----------

class InstanceReader:
    """Reads the instance once per check run and remembers what it saw."""

    def __init__(self, client: ServiceNowClient | None, planned: dict | None = None):
        self.client = client
        self._schemas: dict[str, dict] = {}
        # Tables and fields this plan creates ({table: {"extends": parent, "fields": {...}}}): they
        # don't exist in the instance until deployed, so other rows may use them.
        self.planned = planned or {}
        self._types: dict[str, bool] = {}
        self._actions: dict[str, bool] = {}   # action name (lowercased) -> does this instance have it
        self.unreadable: str | None = None

    def schema(self, table: str) -> dict | None:
        if not self.client or self.unreadable:
            return None
        if table not in self._schemas:
            try:
                self._schemas[table] = self.client.table_schema(table)
            except ServiceNowError as e:
                self.unreadable = str(e)
                return None
        found = self._schemas[table]
        plan = self.planned.get(table)
        if not plan:
            return found
        # Overlay what the plan adds: a new table (with what it extends) or new fields on an existing one.
        fields = {f["name"]: f for f in (found.get("fields") or [])} if found.get("exists") else {}
        parent = plan.get("extends")
        if not found.get("exists"):
            for name in SYSTEM_FIELDS:
                fields.setdefault(name, {"name": name})
            if parent and (ps := self.schema(parent)) and ps.get("exists"):
                for f in ps.get("fields") or []:
                    fields.setdefault(f["name"], f)
        for name in plan.get("fields") or ():
            fields.setdefault(name, {"name": name, "planned": True})
        return {**found, "table": table, "exists": True, "fields": sorted(fields.values(), key=lambda f: f["name"])}

    def field_type_exists(self, internal_type: str) -> bool | None:
        """Whether this instance has the field type (sys_glide_object). None = couldn't tell."""
        if not self.client or self.unreadable or not internal_type:
            return None
        if internal_type not in self._types:
            try:
                rows = self.client.query("sys_glide_object", f"name={internal_type}", ["sys_id"], limit=1)
            except ServiceNowError:
                return None
            self._types[internal_type] = bool(rows)
        return self._types[internal_type]

    def flow_actions_exist(self, names: list[str]) -> set[str] | None:
        """Which of these Flow Designer actions the instance has, lowercased. None = couldn't be
        read, so don't judge.

        Asked by name, never by listing every action and comparing: an instance with spokes has
        more actions than one page holds, and a truncated list makes every action past the cut look
        missing.
        """
        if not self.client or self.unreadable:
            return None
        # `nameIN` matches exactly, so the instance is asked with the design's own spelling and
        # only the answer is folded to lowercase.
        wanted = {str(n).strip().lower(): str(n).strip() for n in names if str(n).strip()}
        if unasked := sorted(wanted.keys() - self._actions.keys()):
            try:
                found = self.client.flow_actions_named([wanted[n] for n in unasked])
            except ServiceNowError:
                return None
            self._actions.update({n: n in found for n in unasked})
        return {n for n in wanted if self._actions.get(n)}

    def script_include_exists(self, name: str) -> bool:
        if not self.client or self.unreadable:
            return True  # can't say it's missing
        try:
            found = self.client.search_artifacts("script_include", name_contains=name, limit=5)
        except ServiceNowError:
            return True
        return any(str(r.get("name", "")).split(" (")[0] == name for r in found.get("records", []))


def own_table_problems(type_: str, record: dict, reader: InstanceReader) -> list[Problem]:
    """Every field in the record has to be a real column of the artifact's own table (sys_script,
    sysevent_email_action …). This is what catches a field name nowBuilder got wrong, before a
    deploy fails on it. Design-only types are skipped: their fields describe the design, not a row."""
    sp = spec(type_)
    if not sp.deployable:
        return []
    schema = reader.schema(sp.table)
    if schema is None or not schema.get("exists"):
        return []
    known = {f["name"].lower() for f in schema.get("fields", [])}
    # The fields that are actually written: nowBuilder's own settings (a notification's
    # triggered_by_flow) become real columns (generation_type) in to_records, and aren't columns.
    from .artifacts import to_records
    from .artifacts import apply_aliases
    written = to_records(type_, {"record": record, "script": "x" if sp.has_script else None})[0]["fields"]
    written = apply_aliases(type_, written, known)
    return [Problem("instance", ERROR,
                    f"{sp.table} has no field called {name} in this instance, so {sp.label.lower()} "
                    f"can't be saved with it.", name)
            for name in sorted(written) if name.lower() not in known]


def flow_step_problems(steps: list[dict], reader: InstanceReader) -> list[Problem]:
    """A flow design has to be buildable: every action it names must exist on this instance, and
    the inputs it names must be that action's real ones. Which actions are available depends on the
    installed spokes, so the instance is the authority for what exists; `flow_catalog` (read out of
    the ServiceNow SDK) is the authority for the input names of the core actions."""
    wanted = [str(s.get("name") or "").strip() for s in steps or []
              if str(s.get("kind") or "").strip().lower() == "action"]
    available = reader.flow_actions_exist(wanted) if wanted else set()
    out: list[Problem] = []
    for step in steps or []:
        name = str(step.get("name") or "").strip()
        kind = str(step.get("kind") or "").strip().lower()
        where = f"step {step.get('step')}"
        if kind == "flow logic":
            if name and not flow_catalog.logic(name):
                out.append(Problem("instance", WARNING,
                                   f"Step {step.get('step')}: '{name}' isn't one of Flow Designer's logic blocks.",
                                   where))
            continue
        if kind != "action" or not name:
            continue
        if available is not None and name.lower() not in available:
            out.append(Problem("instance", ERROR,
                               f"Step {step.get('step')}: this instance has no Flow Designer action called "
                               f"'{name}'. Check the spoke is installed, or use an action it has.", where))
            continue
        # Inputs are only checked for the core actions, the ones the catalogue covers.
        given = step.get("inputs")
        if not flow_catalog.action(name) or not isinstance(given, dict) or not given:
            continue
        if unknown := flow_catalog.unknown_inputs(name, given):
            out.append(Problem("instance", ERROR,
                               f"Step {step.get('step')}: {name} has no input called {', '.join(unknown)}.", where))
        if missing := flow_catalog.missing_inputs(name, given):
            out.append(Problem("instance", ERROR,
                               f"Step {step.get('step')}: {name} needs {', '.join(missing)}.", where))
        out += _recipient_problems(step, given, where)
        from .flow_sdk import manual_pill_keys, pills_in_static_inputs, static_pill_message
        if pilled := [k for k in pills_in_static_inputs(name, given) if manual_pill_keys(given[k])]:
            out.append(Problem("instance", WARNING, f"Step {step.get('step')}: " + static_pill_message(name, pilled), where))
    return out


RECIPIENT_INPUTS = ("ah_to", "ah_cc", "ah_bcc")
_PILL = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def _recipient_problems(step: dict, given: dict, where: str) -> list[Problem]:
    """Send Email's To / CC / BCC take email addresses. A pill of a user or group *record* sends its sys_id,
    which the instance rejects ("Email contained the following invalid recipient addresses: sys_user_group")."""
    out = []
    for key, value in given.items():
        if key.lower() not in RECIPIENT_INPUTS:
            continue
        for m in _PILL.finditer(str(value or "")):
            path = re.sub(r"\s+", "", m.group(1))
            if "email" in path.split(".")[-1].lower():
                continue
            out.append(Problem("instance", WARNING,
                               f"Step {step.get('step')}: {key} gets {{{{{path}}}}}, a record, but Send Email needs email "
                               f"addresses, so it is sent to {{{{{path}.email}}}}. A group needs its Group email filled "
                               "in (check it with query_instance_records); to reach each member instead, use a "
                               "notification.", where))
    return out


def _table_problems(record: dict, reader: InstanceReader) -> list[Problem]:
    out: list[Problem] = []
    name, parent = str(record.get("name") or ""), str(record.get("super_class") or "")
    if reader.client is None or reader.unreadable:
        return out
    try:
        existing = reader.client.table_schema(name) if name else {"exists": False}
    except ServiceNowError:
        existing = {"exists": False}
    if existing.get("exists"):
        out.append(Problem("instance", ERROR, f"The table {name} already exists in this instance: add fields to it "
                                              f"instead of creating it again.", "name"))
    if parent and not reader.planned.get(parent, {}).get("new"):
        ps = reader.schema(parent)
        if ps is not None and not ps.get("exists"):
            out.append(Problem("instance", ERROR, f"The table to extend, {parent}, isn't in this instance.", "super_class"))
    return out


def _field_problems(record: dict, reader: InstanceReader) -> list[Problem]:
    out: list[Problem] = []
    table, element = str(record.get("name") or ""), str(record.get("element") or "")
    schema = reader.schema(table) if table else None
    if schema is not None and not schema.get("exists"):
        out.append(Problem("instance", ERROR, f"The table {table} isn't in this instance (or in this plan).", "name"))
    elif schema is not None and any(f["name"] == element and not f.get("planned") for f in schema.get("fields") or []):
        out.append(Problem("instance", ERROR, f"{table} already has a field called {element}: change that field "
                                              f"instead of adding it again.", "element"))
    kind = str(record.get("internal_type") or "")
    if reader.field_type_exists(kind) is False:
        out.append(Problem("instance", ERROR, f"This instance has no field type called {kind}.", "internal_type"))
    ref = str(record.get("reference") or "")
    if ref and not reader.planned.get(ref, {}).get("new"):
        rs = reader.schema(ref)
        if rs is not None and not rs.get("exists"):
            out.append(Problem("instance", ERROR, f"The referenced table {ref} isn't in this instance.", "reference"))
    return out


def instance_problems(type_: str, record: dict, script: str, actions: list[dict],
                      reader: InstanceReader, plan_classes: set[str],
                      steps: list[dict] | None = None) -> list[Problem]:
    sp = spec(type_)
    out: list[Problem] = own_table_problems(type_, record, reader)
    if type_ == "table":
        return out + _table_problems(record, reader)
    if type_ == "field":
        return out + _field_problems(record, reader)
    if type_ == "flow":
        out += flow_step_problems(steps or [], reader)
    table = str(record.get(sp.table_field) or "") if sp.table_field else ""
    if table:
        schema = reader.schema(table)
        if schema is None:
            return out
        if not schema.get("exists"):
            out.append(Problem("instance", ERROR, f"The table {table} isn't in this instance.", sp.table_field))
            return out
        known = {f["name"].lower() for f in schema.get("fields", [])}
        for field in sorted(fields_used(type_, record, script)):
            if field not in known:
                out.append(Problem("instance", ERROR, f"{table} has no field called {field} in this instance.", field))
        for a in actions or []:
            name = str(a.get("field") or "").lower()
            if name and name not in known:
                out.append(Problem("instance", ERROR, f"{table} has no field called {name} in this instance.", f"action {name}"))

    for other in sorted(tables_used(script)):
        schema = reader.schema(other)
        if schema is not None and not schema.get("exists"):
            out.append(Problem("instance", ERROR, f"The script reads the table {other}, which isn't in this instance.", other))

    for cls in sorted(classes_used(script)):
        if cls in plan_classes:
            continue
        if not reader.script_include_exists(cls):
            out.append(Problem("instance", ERROR,
                               f"The script calls {cls}, which is neither in this plan nor in the instance.", cls))
    return out


SYSTEM_FIELDS = ("sys_id", "sys_created_on", "sys_created_by", "sys_updated_on", "sys_updated_by", "sys_mod_count",
                 "sys_tags", "sys_class_name")


def planned_schema(components: list[dict]) -> dict:
    """The tables and fields the plan's own table and field rows create."""
    out: dict[str, dict] = {}
    for c in components:
        rec = (c.get("generated") or {}).get("record") or {}
        if c["type"] == "table" and rec.get("name"):
            entry = out.setdefault(rec["name"], {"fields": set()})
            entry["extends"] = rec.get("super_class") or None
            entry["new"] = True
        elif c["type"] == "field" and rec.get("name") and rec.get("element"):
            out.setdefault(rec["name"], {"fields": set()})["fields"].add(rec["element"])
    return out


# ---------- one component, and a whole plan ----------

def offline_problems(type_: str, data: dict, es2021: bool = False) -> list[Problem]:
    """Everything that can be judged without the instance: the record, and what the script does."""
    record, script = data.get("record") or {}, data.get("script") or ""
    out = [Problem("record", ERROR, m) for m in record_check(type_, data)]
    return out + _script_problems(type_, script, str(record.get("when") or ""), es2021)


def generation_problems(type_: str, data: dict, es2021: bool = False) -> list[str]:
    """The same rules as plain sentences, for the model to correct while it is still writing."""
    return [p.message for p in offline_problems(type_, data, es2021)]


def check_component(component: dict, reader: InstanceReader, plan_classes: set[str], es2021: bool = False) -> list[dict]:
    data = component.get("generated") or {}
    if not data:
        return []
    type_ = component["type"]
    record, script = data.get("record") or {}, data.get("script") or ""
    problems = offline_problems(type_, data, es2021)
    problems += instance_problems(type_, record, script, data.get("actions") or [], reader, plan_classes,
                                  steps=data.get("steps") or [])
    if type_ == "flow":
        problems += flow_export_problems(data)
    return [p.as_dict() for p in problems]


def flow_export_problems(data: dict) -> list[Problem]:
    """When flows deploy with the SDK, a design the SDK can't express can't be deployed, so it is an
    error the user (or Fix with AI) must fix - not a surprise at deploy time."""
    from ..services import sdk_deploy
    if not sdk_deploy.configured():
        return []                         # design only: the card offers "Build by hand"
    from .flow_sdk import export_report
    return [Problem("record", ERROR, f"Can't be deployed with the ServiceNow SDK: {b}", "flow")
            for b in export_report(data)["blockers"]]


# ---------- JavaScript syntax (node --check), any script type ----------

_SYNTAX_CACHE: dict[str, str] = {}


def _node() -> str | None:
    import shutil
    return shutil.which("node")


def syntax_problems(script: str) -> list[Problem]:
    """A real JavaScript parse of the script (Node.js, which the SDK setup already needs). Catches what the
    AI can get wrong in any script - a missing bracket, a stray character - before it reaches the instance.
    The script is wrapped in a function so a top-level `return` (scheduled jobs, inline scripts) is legal."""
    import hashlib, os, subprocess, tempfile
    if not script.strip():
        return []
    node = _node()
    if not node:
        return []
    key = hashlib.sha1(script.encode("utf-8")).hexdigest()
    if key not in _SYNTAX_CACHE:
        fd, path = tempfile.mkstemp(suffix=".js")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write("(function () {\n" + script + "\n});\n")
            out = subprocess.run([node, "--check", path], capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=15, check=False)
            _SYNTAX_CACHE[key] = "" if out.returncode == 0 else (out.stderr or out.stdout)
        except (OSError, subprocess.SubprocessError):
            _SYNTAX_CACHE[key] = ""
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    err = _SYNTAX_CACHE[key]
    if not err:
        return []
    m = re.search(r":(\d+)\s*\n", err)
    line = max(1, int(m.group(1)) - 1) if m else 0
    msg = next((ln.strip() for ln in err.splitlines() if "Error" in ln), "SyntaxError")
    return [Problem("script", ERROR, f"The script doesn't parse: {msg}. Fix the JavaScript syntax.",
                    f"line {line}" if line else "script")]


# ---------- events: every event fired or listened for must be registered ----------

_EVENT_QUEUE = re.compile(r"gs\.eventQueue(?:Scheduled)?\s*\(\s*['\"]([\w.\-]+)['\"]")


def event_problems(component: dict, components: list[dict], client: ServiceNowClient | None) -> list[Problem]:
    data = component.get("generated") or {}
    rec = data.get("record") or {}
    used = set(_EVENT_QUEUE.findall(str(data.get("script") or "")))
    if component["type"] in ("script_action", "notification") and str(rec.get("event_name") or "").strip() \
            and str(rec.get("triggered_by_flow")) != "true":
        used.add(str(rec["event_name"]).strip())
    if not used:
        return []
    planned = {str(((c.get("generated") or {}).get("record") or {}).get("event_name") or c.get("name") or "")
               for c in components if c["type"] == "event"}
    out = []
    for name in sorted(used - planned):
        found = None
        if client is not None:
            try:
                found = bool(client.query("sysevent_register", f"event_name={name}", ["sys_id"], limit=1))
            except ServiceNowError:
                found = None
        if found is False:
            out.append(Problem("instance", ERROR,
                               f"The event {name} isn't registered on this instance or in the plan. Add an event row "
                               "with exactly this name, or use the name of an event that exists.", name))
    return out


def names_in_plan(components: list[dict]) -> set[str]:
    """Script include class names the plan itself provides."""
    out = set()
    for c in components:
        if c["type"] == "script_include":
            rec = (c.get("generated") or {}).get("record") or {}
            out.add(str(rec.get("name") or c.get("name") or ""))
    return {n for n in out if n}


def application_problems(component: dict, application: str | None, target: dict | None) -> list[Problem]:
    """The plan names one application for every artifact. It must exist, and a flow can only go where
    the ServiceNow SDK can install it: Global, or nowBuilder's own scoped app."""
    from ..services import application as apps
    if application is None or component["type"] not in ("flow",) and not spec(component["type"]).deployable:
        return []
    name = apps.label(application)
    if target is None:
        return [Problem("instance", ERROR, f"The plan builds in the application '{name}', which isn't on this instance. "
                        "Create the application first, or ask for the plan to be built in Global.", "application")]
    if component["type"] == "flow" and not apps.is_global(application) and \
            not re.fullmatch(r"x_[a-z0-9]+_nbuild\d*", target["scope"]):
        return [Problem("record", ERROR,
                        f"The ServiceNow SDK can install a flow into Global or into nowBuilder's own app, but not into "
                        f"the existing application {name} (installing would take that application over). Build this "
                        f"flow by hand in {name}, or ask for the plan to be built in Global.", "application")]
    return []


_GA_NEW = re.compile(r"new\s+GlideAjax\s*\(\s*['\"]([\w.]+)['\"]")
_GA_PARAM = re.compile(r"\.addParam\s*\(\s*['\"](\w+)['\"]\s*,\s*([^)]*)\)")
_GET_PARAM = re.compile(r"getParameter\s*\(\s*['\"](\w+)['\"]")


def _ajax_script(name: str, components: list[dict], client: ServiceNowClient | None) -> str | None:
    short = name.split(".")[-1]
    for c in components:
        rec = (c.get("generated") or {}).get("record") or {}
        if c["type"] == "script_include" and str(rec.get("name") or c.get("name")) == short:
            return str((c.get("generated") or {}).get("script") or "")
    if client is None:
        return None
    try:
        rows = client.query("sys_script_include", f"name={short}^active=true", ["script"], limit=1)
    except ServiceNowError:
        return None
    if not rows:
        return None
    script = rows[0].get("script")
    return str(script.get("value") if isinstance(script, dict) else script or "")


def glideajax_problems(component: dict, components: list[dict], client: ServiceNowClient | None) -> list[Problem]:
    """A client script's GlideAjax call has to match the script include it calls - the method in
    sysparm_name must exist there, and every parameter the include reads must be sent."""
    script = str((component.get("generated") or {}).get("script") or "")
    out: list[Problem] = []
    for m in _GA_NEW.finditer(script):
        include = m.group(1)
        server = _ajax_script(include, components, client)
        if server is None:
            continue
        params = {p.group(1): p.group(2).strip().strip("'\"") for p in _GA_PARAM.finditer(script)}
        method = params.pop("sysparm_name", "")
        if method and not re.search(rf"\b{re.escape(method)}\s*:\s*function\b", server):
            defined = re.findall(r"\b(\w+)\s*:\s*function\b", server)
            defined = [d for d in defined if not d.startswith("_") and d not in ("initialize", "type")]
            out.append(Problem("script", ERROR,
                               f"The GlideAjax call asks {include} for the method {method}, which it doesn't have "
                               f"(it has: {', '.join(defined) or 'no public methods'}). Use the same method name in "
                               "both.", "GlideAjax"))
        read = sorted(set(_GET_PARAM.findall(server)) - {"sysparm_name"})
        missing = [r for r in read if r not in params]
        if missing and params:
            out.append(Problem("script", ERROR,
                               f"{include} reads {', '.join(missing)}, but the GlideAjax call sends "
                               f"{', '.join(sorted(params))}. Send the parameter names the script include reads.",
                               "GlideAjax"))
    return out


def run(components: list[dict], client: ServiceNowClient | None, es2021: bool = False,
        only: list[str] | None = None, application: str | None = None) -> dict:
    """Check the plan's rows in place. Returns a summary for `Plan.validation`."""
    from ..services import application as apps
    reader = InstanceReader(client, planned_schema(components))
    plan_classes = names_in_plan(components)
    target = apps.resolve(client, application) if application is not None else None
    errors = warnings = 0
    for c in components:
        if only is not None and c["id"] not in only:
            errors += sum(1 for p in c.get("problems") or [] if p["severity"] == ERROR)
            warnings += sum(1 for p in c.get("problems") or [] if p["severity"] == WARNING)
            continue
        problems = check_component(c, reader, plan_classes, es2021) if c.get("status") != "failed" else []
        if c.get("status") != "failed" and application is not None:
            problems += [p.as_dict() for p in application_problems(c, application, target)]
        if c.get("status") != "failed" and c["type"] in ("client_script", "ui_action"):
            problems += [p.as_dict() for p in glideajax_problems(c, components, client)]
        if c.get("status") != "failed":
            gen = c.get("generated") or {}
            if spec(c["type"]).has_script and str(gen.get("script") or "").strip():
                problems += [p.as_dict() for p in syntax_problems(str(gen["script"]))]
            problems += [p.as_dict() for p in event_problems(c, components, client)]
        c["problems"] = problems
        errors += sum(1 for p in problems if p["severity"] == ERROR)
        warnings += sum(1 for p in problems if p["severity"] == WARNING)
    # Flows don't go through the Table API: they deploy with the ServiceNow SDK, or are built by hand
    # when the backend can't run it. Say which, instead of a bare "everything checks out".
    from ..services import sdk_deploy
    flows = [c.get("name", c["type"]) for c in components if not spec(c["type"]).deployable]
    message = "Everything checks out." if not errors and not warnings else None
    if flows and not errors:
        message = ("Checked. Flows deploy with the ServiceNow SDK: " if sdk_deploy.configured()
                   else "Checked. Build by hand (the ServiceNow SDK can't run on this backend): ") + ", ".join(flows)
    if reader.unreadable:
        message = f"nowBuilder couldn't read the instance to check table and field names: {reader.unreadable}"
    return {"status": "problems" if errors else "passed", "errors": errors, "warnings": warnings,
            "message": message, "instance_checked": client is not None and not reader.unreadable}


def blocking(component: dict) -> bool:
    """True when this row must not be deployed: it isn't written, it has errors, or it is a kind
    nowBuilder designs but can't write (a flow)."""
    if component.get("status") != "ready":
        return True
    if not spec(component["type"]).deployable and component["type"] != "flow":
        return True                      # flows deploy with the SDK; deploy.approve checks it can run
    return any(p["severity"] == ERROR for p in component.get("problems") or [])

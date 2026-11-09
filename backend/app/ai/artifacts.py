"""What each artifact type is made of: the ServiceNow fields nowBuilder generates, the JSON
schema the model must answer with, and the checks a generated record has to pass.

One place describes each type, so generation (Chunk 2), checks (Chunk 3) and deploying into an
update set (Chunk 4) agree on the shape. Booleans are kept as the strings the Table API wants
("true" / "false"); order is a string of digits for the same reason.

`children` are the extra records an artifact needs beside its own row: a UI policy's field
actions live in `sys_ui_policy_action`, one record per field.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

BOOL = {"type": "string", "enum": ["true", "false"]}


def _str(desc: str, **kw) -> dict:
    return {"type": "string", "description": desc, **kw}


@dataclass(frozen=True)
class ArtifactSpec:
    type: str
    label: str
    table: str
    name_field: str
    table_field: str | None          # the field holding the table the artifact runs on
    properties: dict                 # JSON schema properties of `record`
    required: list[str]
    has_script: bool = True
    script_field: str = "script"
    children: dict = field(default_factory=dict)   # key → {"table", "parent_field", "schema"}
    extras: dict = field(default_factory=dict)     # key → {"schema"}: design data, never written
    # False = nowBuilder designs it but can't write it through the Table API (a Flow Designer flow
    # is spread over sys_hub_* records and a compiled snapshot). Those rows are built by hand.
    deployable: bool = True
    build_note: str = ""
    # field -> (table, key): a reference written by name in the design and stored as a sys_id, e.g. a
    # table's super_class ("task") is the sys_db_object record whose name is task. Resolved on deploy.
    lookups: dict = field(default_factory=dict)
    # A setting whose column name differs between releases: the first name the instance's table has wins.
    # sys_script_client's trigger field is `field_name` on some instances and `field` (label "Field name")
    # on others; the instance's own schema decides, never a guess.
    aliases: dict = field(default_factory=dict)

    def schema(self) -> dict:
        """The JSON schema for one generated artifact: {record, script?, children?, extras?}."""
        props: dict = {"record": {"type": "object", "properties": self.properties,
                                  "required": self.required, "additionalProperties": False}}
        required = ["record"]
        if self.has_script:
            props["script"] = _str("The complete script. ES5 unless the user said the scope runs ES2021.", minLength=1)
            required.append("script")
        for key, part in {**self.children, **self.extras}.items():
            props[key] = part["schema"]
            if part.get("required"):
                required.append(key)
        return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


VARIABLE_TYPES = {"yes_no": "1", "multi_line_text": "2", "single_line_text": "6", "checkbox": "7",
                  "reference": "8", "date": "9", "date_time": "10", "label": "11"}

VARIABLES = {
    "type": "array", "maxItems": 30,
    "description": "The form's variables (item_option_new), in order.",
    "items": {"type": "object", "properties": {
        "name": _str("Variable name: lowercase with underscores, e.g. business_justification",
                     pattern=r"^[a-z][a-z0-9_]{0,39}$"),
        "question_text": _str("The question users see"),
        "type": {"type": "string", "enum": list(VARIABLE_TYPES)},
        "mandatory": BOOL,
        "order": _str("Display order, digits: 100, 200 …", pattern=r"^\d{1,5}$"),
        "reference": _str("Reference variables only: table referenced, e.g. sys_user. Empty otherwise.", default=""),
        "help_text": _str("Optional help under the question. Empty if none.", default=""),
    }, "required": ["name", "question_text", "type", "mandatory", "order"], "additionalProperties": False},
}

UI_POLICY_ACTION = {
    "type": "array",
    "description": "One entry per field the policy changes (sys_ui_policy_action records).",
    "minItems": 1, "maxItems": 20,
    "items": {"type": "object", "properties": {
        "field": _str("Field name on the table, e.g. u_vendor"),
        "mandatory": {"type": "string", "enum": ["true", "false", "ignore"], "description": "'ignore' leaves it alone"},
        "visible": {"type": "string", "enum": ["true", "false", "ignore"]},
        "disabled": {"type": "string", "enum": ["true", "false", "ignore"], "description": "'true' = read only"},
    }, "required": ["field", "mandatory", "visible", "disabled"], "additionalProperties": False},
}

SPECS: dict[str, ArtifactSpec] = {
    "business_rule": ArtifactSpec(
        type="business_rule", label="Business rule", table="sys_script", name_field="name", table_field="collection",
        properties={
            "name": _str("What it does, in words: 'Set priority 1 for VIP callers'"),
            "collection": _str("Table it runs on, e.g. incident"),
            "when": {"type": "string", "enum": ["before", "after", "async", "display"],
                     "description": "A query rule is 'before' with action_query true (ServiceNow has no 'query' value)."},
            "order": _str("Execution order, digits only. 100 unless something must run before or after it.", pattern=r"^\d{1,5}$"),
            "active": BOOL,
            "action_insert": BOOL, "action_update": BOOL, "action_delete": BOOL, "action_query": BOOL,
            "condition": _str("Server-side condition script, e.g. current.caller_id.vip == true. Empty string if none."),
            "filter_condition": _str("Encoded query for the condition builder, e.g. priority=1^active=true. Empty string if none."),
            "description": _str("One line for the next developer."),
        },
        required=["name", "collection", "when", "order", "active", "action_insert", "action_update",
                  "action_delete", "action_query", "condition", "filter_condition", "description"],
    ),
    "script_include": ArtifactSpec(
        type="script_include", label="Script include", table="sys_script_include", name_field="name", table_field=None,
        properties={
            "name": _str("Class name, PascalCase, matching the script's Class.create and type"),
            "api_name": _str("Scope and name, e.g. global.VipUtils. Leave empty to let ServiceNow set it.", default=""),
            "client_callable": BOOL,
            "access": {"type": "string", "enum": ["package_private", "public"],
                       "description": "package_private = this application scope only"},
            "active": BOOL,
            "description": _str("One line: what it is for."),
        },
        required=["name", "client_callable", "access", "active", "description"],
    ),
    "client_script": ArtifactSpec(
        type="client_script", label="Client script", table="sys_script_client", name_field="name", table_field="table",
        properties={
            "name": _str("What it does, in words"),
            "table": _str("Table the form belongs to, e.g. incident"),
            "type": {"type": "string", "enum": ["onLoad", "onChange", "onSubmit", "onCellEdit"]},
            "field_name": _str("Field that triggers onChange; empty string for other types.", default=""),
            "ui_type": {"type": "string", "enum": ["0", "1", "10"],
                        "description": "0 desktop, 1 mobile, 10 all (use 10 so it works in Workspace and the portal)"},
            "active": BOOL,
            "isolate_script": BOOL,
            "description": _str("One line for the next developer."),
        },
        aliases={"field_name": ("field",)},
        required=["name", "table", "type", "field_name", "ui_type", "active", "isolate_script", "description"],
    ),
    "ui_policy": ArtifactSpec(
        type="ui_policy", label="UI policy", table="sys_ui_policy", name_field="short_description", table_field="table",
        properties={
            "short_description": _str("What the policy does, in words"),
            "table": _str("Table the form belongs to"),
            "conditions": _str("Encoded query for when it applies, e.g. category=hardware. Empty string = always."),
            "on_load": BOOL,
            "reverse_if_false": BOOL,
            "run_scripts": {"type": "string", "enum": ["true", "false"],
                            "description": "false unless the policy really needs scripts; actions come first"},
            "active": BOOL,
        },
        required=["short_description", "table", "conditions", "on_load", "reverse_if_false", "run_scripts", "active"],
        has_script=False,
        children={"actions": {"table": "sys_ui_policy_action", "parent_field": "ui_policy",
                              "schema": UI_POLICY_ACTION, "required": True}},
    ),
    "notification": ArtifactSpec(
        type="notification", label="Notification", table="sysevent_email_action",
        name_field="name", table_field="collection",
        properties={
            "name": _str("What the notification is, in words: 'Incident opened confirmation'"),
            "collection": _str("Table it watches, e.g. incident. Never task itself: notifications on task aren't supported."),
            "active": BOOL,
            "action_insert": {"type": "string", "enum": ["true", "false"], "description": "Send when a record is created"},
            "action_update": {"type": "string", "enum": ["true", "false"], "description": "Send when a record is updated"},
            "event_name": _str("Only when an event triggers it instead of insert/update; empty otherwise.", default=""),
            "triggered_by_flow": {"type": "string", "enum": ["true", "false"], "default": "false",
                                  "description": "true when only a flow's Send Notification step (or a script) sends it: "
                                                 "Send when = Triggered, with insert, update and event_name all off."},
            "condition": _str("Encoded query for when to send, e.g. priority=1. Empty string = whenever it is triggered."),
            "recipient_fields": _str(
                "Comma-separated fields on the table holding the people to send to, e.g. opened_by,caller_id. "
                "This is how you send to someone on the record."),
            "recipient_users": _str("Only for a fixed person every time; usually empty.", default=""),
            "recipient_groups": _str("Only for a fixed group every time; usually empty.", default=""),
            "subject": _str("Subject line. ${field} inserts a field, e.g. ${number}."),
            "message_html": _str("The body. ${field} inserts a field; ${URI_REF} is a link to the record."),
            "weight": _str("0 unless this should beat another notification with the same recipients.", pattern=r"^\d{1,3}$"),
            "send_self": {"type": "string", "enum": ["true", "false"],
                          "description": "Send to the person whose action triggered it"},
            "exclude_delegates": BOOL,
            "content_type": {"type": "string", "enum": ["text/html", "text/plain"]},
        },
        required=["name", "collection", "active", "action_insert", "action_update", "event_name", "condition",
                  "recipient_fields", "subject", "message_html", "weight", "send_self", "content_type"],
        has_script=False,
    ),
    "flow": ArtifactSpec(
        type="flow", label="Flow", table="sys_hub_flow", name_field="name", table_field="table",
        properties={
            "name": _str("What the flow does, in words"),
            "table": _str("Table the trigger watches (target table for Inbound Email); empty for a scheduled flow"),
            "trigger": {"type": "string",
                        "description": "Flow Designer trigger. Record triggers: Created, Updated, Created or Updated. "
                                       "Scheduled: Daily, Weekly, Monthly, Repeat, Run Once. Application: Service "
                                       "Catalog, Inbound Email, SLA Task.",
                        "enum": ["Created", "Updated", "Created or Updated", "Daily", "Weekly", "Monthly", "Repeat",
                                 "Run Once", "Service Catalog", "Inbound Email", "SLA Task"]},
            "trigger_condition": _str("Encoded query on the trigger table, e.g. priority=1^active=true. Empty = every record."),
            "run_trigger": {"type": "string", "enum": ["once", "for each unique change", "always"],
                            "description": "Only matters for Updated / Created or Updated triggers."},
            "run_as": {"type": "string", "enum": ["System user", "User who initiated session"]},
            "schedule_time": _str("Daily trigger only: time of day as HH:MM (instance time zone). Empty otherwise.", default=""),
            "description": _str("One line: what it automates."),
        },
        required=["name", "trigger", "trigger_condition", "run_trigger", "run_as", "description"],
        has_script=False, deployable=False,
        build_note="nowBuilder deploys this flow with the ServiceNow SDK (Fluent) into the plan's application. "
                   "Until the SDK is set up on the backend, build it in Flow Designer from the steps below: a flow "
                   "is spread across several sys_hub_ tables plus a compiled snapshot, so it can't be written "
                   "through the Table API.",
        extras={"steps": {"required": True, "schema": {
            "type": "array", "minItems": 1, "maxItems": 25,
            "description": "The flow's steps in the order they run, as they'd be added in Flow Designer.",
            "items": {"type": "object", "properties": {
                "step": {"type": "integer", "description": "1, 2, 3 … in the order they run"},
                "kind": {"type": "string", "enum": ["action", "flow logic", "subflow"]},
                "name": _str("Exact Flow Designer name, e.g. 'Look Up Record', 'Update Record', 'Send Notification', "
                             "'Send Email', 'If', 'Else If', 'Else', 'For Each', 'Do the following until', "
                             "'Wait for a duration', 'End Flow'"),
                "detail": _str("How to fill it in, in words: the inputs, and the data pills to drag into them"),
                "inside": {"type": "integer",
                           "description": "Step number of the If / Else If / Else / For Each / Do the following "
                                          "until this step sits inside. "
                                          "Omit for a top-level step."},
                "condition": _str("If / Else If: the condition, e.g. {{trigger.current.priority}}=1. Do the following "
                                  "until: the exit condition checked after each pass, e.g. "
                                  "{{step4.Record.stage}}IN<value>,<value> from a Look Up Record inside the loop"),
                "duration": _str("Wait for a duration only: how long, e.g. '2 minutes', '1 hour', '00:02:00'"),
                "label": _str("Optional display label for a Do the following until loop"),
                "items": _str("For Each only: the records to loop over, e.g. {{step2.Records}}. Steps inside the loop "
                              "read the current record as {{item.<field>}}."),
                "inputs": {"type": "object",
                           "description": "Action steps: the action's real input names and their values, from "
                                          "get_flow_actions. Refer to earlier data with {{trigger.current.<field>}}, "
                                          "{{step<n>.<Output>}} or {{item.<field>}}, and to another row of this plan "
                                          "(e.g. the notification to send) with {{plan.<row id>}}."},
            }, "required": ["step", "kind", "name", "detail"], "additionalProperties": False}}}},
    ),
    "scheduled_job": ArtifactSpec(
        type="scheduled_job", label="Scheduled job", table="sysauto_script", name_field="name", table_field=None,
        properties={
            "name": _str("What the job does, in words: 'Close resolved incidents after 7 days'"),
            "run_type": {"type": "string", "enum": ["daily", "weekly", "monthly", "periodically", "on_demand"],
                         "description": "How often it runs"},
            "run_time": _str("Time of day it runs, HH:MM:SS (instance time zone); for periodically the first run time.",
                             pattern=r"^\d{2}:\d{2}:\d{2}$"),
            "run_dayofweek": _str("weekly only: 1 = Monday … 7 = Sunday; empty otherwise", default=""),
            "run_dayofmonth": _str("monthly only: day of the month 1-31; empty otherwise", default=""),
            "run_period": _str("periodically only: interval HH:MM:SS, e.g. 01:00:00 for hourly; empty otherwise",
                               default=""),
            "active": BOOL,
        },
        required=["name", "run_type", "run_time", "active"],
        build_note="Runs as the user set on the job (System Administrator when empty). Test it with Execute Now.",
    ),
    "data_policy": ArtifactSpec(
        type="data_policy", label="Data policy", table="sys_data_policy2", name_field="short_description",
        table_field="model_table",
        properties={
            "short_description": _str("What the policy enforces, in words"),
            "model_table": _str("Table it applies to, e.g. incident"),
            "conditions": _str("Encoded query for when it applies, e.g. state=6. Empty string = always."),
            "apply_import_set": BOOL,
            "apply_soap": BOOL,
            "enforce_ui": {"type": "string", "enum": ["true", "false"],
                           "description": "true = also enforce on forms (Use as UI Policy on client)"},
            "inherit": BOOL,
            "active": BOOL,
        },
        required=["short_description", "model_table", "conditions", "apply_import_set", "apply_soap",
                  "enforce_ui", "inherit", "active"],
        has_script=False,
        children={"actions": {"table": "sys_data_policy_rule", "parent_field": "sys_data_policy", "required": True,
                              "schema": {
                                  "type": "array", "minItems": 1, "maxItems": 20,
                                  "description": "One rule per field (sys_data_policy_rule).",
                                  "items": {"type": "object", "properties": {
                                      "field": _str("Field name on the table"),
                                      "mandatory": {"type": "string", "enum": ["true", "false", "ignore"]},
                                      "disabled": {"type": "string", "enum": ["true", "false", "ignore"],
                                                   "description": "'true' = read only"},
                                  }, "required": ["field", "mandatory", "disabled"], "additionalProperties": False}}}},
    ),
    "system_property": ArtifactSpec(
        type="system_property", label="System property", table="sys_properties", name_field="name", table_field=None,
        properties={
            "name": _str("Lowercase dot.notation, e.g. incident.auto_close.days"),
            "value": _str("The value, as text"),
            "type": {"type": "string", "enum": ["string", "integer", "boolean", "choicelist", "color", "timezone", "uploaded_image"]},
            "description": _str("What it controls and the allowed values."),
        },
        required=["name", "value", "type", "description"],
        has_script=False,
    ),
    "event": ArtifactSpec(
        type="event", label="Event registration", table="sysevent_register", name_field="event_name", table_field="table",
        properties={
            "event_name": _str("Lowercase dot.notation, e.g. incident.p1.escalated"),
            "table": _str("Table the event's record belongs to, e.g. incident"),
            "fired_by": _str("What fires it, e.g. 'Business rule: Escalate P1 incidents'"),
            "description": _str("When it is fired and what listens to it."),
        },
        required=["event_name", "table", "fired_by", "description"],
        has_script=False,
    ),
    "script_action": ArtifactSpec(
        type="script_action", label="Script action", table="sysevent_script_action", name_field="name", table_field=None,
        properties={
            "name": _str("What it does when the event fires"),
            "event_name": _str("The registered event it runs on, e.g. incident.p1.escalated"),
            "order": _str("Execution order, digits", pattern=r"^\d{1,5}$"),
            "condition_script": _str("Optional server condition, e.g. current.active == true. Empty string if none."),
            "active": BOOL,
        },
        required=["name", "event_name", "order", "condition_script", "active"],
    ),
    "table": ArtifactSpec(
        type="table", label="Table", table="sys_db_object", name_field="name", table_field=None,
        properties={
            "name": _str("Table name: lowercase letters, digits and underscores, starting u_ (global), e.g. "
                         "u_vendor_contract. Max 80 characters.", pattern=r"^[a-z][a-z0-9_]{1,79}$"),
            "label": _str("The table's label, singular or plural as users say it, e.g. 'Vendor Contract'"),
            "super_class": _str("Table it extends, by name (task for work with assignment, state and SLAs; "
                                "cmdb_ci or a child class for configuration items). Empty string for a standalone table.",
                                default=""),
            "is_extendable": BOOL,
        },
        required=["name", "label", "super_class", "is_extendable"],
        has_script=False,
        lookups={"super_class": ("sys_db_object", "name")},
        build_note="The instance adds the system fields (sys_id, sys_created_on …) and, when it extends a "
                   "table, everything that table has. Access controls aren't created: add read/write ACLs "
                   "for the right role (security_admin).",
    ),
    "field": ArtifactSpec(
        type="field", label="Field", table="sys_dictionary", name_field="column_label", table_field="name",
        properties={
            "name": _str("Table the field is added to, e.g. incident or u_vendor_contract"),
            "element": _str("Column name: lowercase, starting u_ (global), e.g. u_contract_value. Max 80 characters.",
                            pattern=r"^[a-z][a-z0-9_]{1,79}$"),
            "column_label": _str("The label users see, e.g. 'Contract value'"),
            "internal_type": {"type": "string", "enum": ['string', 'integer', 'boolean', 'decimal', 'float', 'glide_date', 'glide_date_time', 'glide_duration', 'reference', 'choice', 'journal_input', 'html', 'email', 'url', 'currency', 'price', 'glide_list', 'script'],
                              "description": "Field type (sys_glide_object name). Checked against this instance."},
            "max_length": _str("Characters for string/choice/url/email fields, e.g. 40, 100, 255, 4000. Empty for other types.",
                               default=""),
            "reference": _str("Reference and glide_list fields: the table referenced, e.g. sys_user. Empty otherwise.",
                              default=""),
            "choice": {"type": "string", "enum": ["", "0", "1", "3"],
                       "description": "Choice list: 1 = dropdown with --None--, 3 = dropdown without --None--, "
                                      "empty / 0 = no choice list"},
            "mandatory": BOOL,
            "read_only": BOOL,
            "default_value": _str("Default value, as stored (a choice value, true/false, a number). Empty if none.", default=""),
            "active": BOOL,
        },
        required=["name", "element", "column_label", "internal_type", "mandatory", "read_only", "active"],
        has_script=False,
        children={"choices": {"table": "sys_choice", "parent_field": None, "required": False,
                              "copy": {"name": "name", "element": "element"},
                              "schema": {
                                  "type": "array", "maxItems": 50,
                                  "description": "Choice list values (sys_choice), only for choice fields.",
                                  "items": {"type": "object", "properties": {
                                      "value": _str("Stored value: lowercase, stable, e.g. pending"),
                                      "label": _str("What users see, e.g. Pending"),
                                      "sequence": _str("Order in the list, digits: 100, 200 …", pattern=r"^\d{1,5}$"),
                                  }, "required": ["value", "label", "sequence"], "additionalProperties": False}}}},
    ),
    "ui_action": ArtifactSpec(
        type="ui_action", label="UI action", table="sys_ui_action", name_field="name", table_field="table",
        properties={
            "name": _str("The button or link label the user sees"),
            "table": _str("Table the form or list belongs to"),
            "action_name": _str("Short unique name, lowercase with underscores, e.g. escalate_incident"),
            "condition": _str("Server-side condition deciding whether it shows, e.g. current.active == true. Empty string if none."),
            "form_button": BOOL, "form_link": BOOL, "list_button": BOOL,
            "client": {"type": "string", "enum": ["true", "false"], "description": "true only when onclick runs in the browser"},
            "onclick": _str("Client function to call when client is true; empty string otherwise.", default=""),
            "order": _str("Digits only, e.g. 100", pattern=r"^\d{1,5}$"),
            "active": BOOL,
            "comments": _str("One line for the next developer."),
        },
        required=["name", "table", "action_name", "condition", "form_button", "form_link", "list_button",
                  "client", "onclick", "order", "active", "comments"],
    ),
    "catalog_item": ArtifactSpec(
        type="catalog_item", label="Catalog item", table="sc_cat_item", name_field="name", table_field=None,
        properties={
            "name": _str("Item name users see in the catalog, e.g. 'Request a new laptop'"),
            "short_description": _str("One line under the name"),
            "description": _str("HTML description on the item page. Empty string if none.", default=""),
            "sc_catalogs": _str("Catalog title, e.g. 'Service Catalog' (looked up on the instance)"),
            "category": _str("Category title, e.g. 'Hardware' (looked up on the instance). Empty if none.", default=""),
            "active": BOOL,
        },
        required=["name", "short_description", "sc_catalogs", "active"],
        has_script=False,
        lookups={"sc_catalogs": ("sc_catalog", "title"), "category": ("sc_category", "title")},
        children={"variables": {"table": "item_option_new", "parent_field": "cat_item", "required": False,
                                "schema": VARIABLES}},
        build_note="Fulfilment: add a flow row with a Service Catalog trigger, or attach one in the item's "
                   "Process Engine tab. Select-box choices aren't created: use Yes/No, a reference, or add the "
                   "choices on the variable after deploying.",
    ),
    "record_producer": ArtifactSpec(
        type="record_producer", label="Record producer", table="sc_cat_item_producer", name_field="name",
        table_field="table_name",
        properties={
            "name": _str("Producer name users see, e.g. 'Report a facilities issue'"),
            "short_description": _str("One line under the name"),
            "table_name": _str("Table it creates a record in, e.g. incident"),
            "sc_catalogs": _str("Catalog title, e.g. 'Service Catalog' (looked up on the instance)"),
            "category": _str("Category title (looked up on the instance). Empty if none.", default=""),
            "active": BOOL,
        },
        required=["name", "short_description", "table_name", "sc_catalogs", "active"],
        script_field="script",
        lookups={"sc_catalogs": ("sc_catalog", "title"), "category": ("sc_category", "title")},
        children={"variables": {"table": "item_option_new", "parent_field": "cat_item", "required": False,
                                "schema": VARIABLES}},
        build_note="The script maps variables onto the new record: current.<field> = producer.<variable>; "
                   "don't call current.insert() - the producer inserts the record.",
    ),

}

TYPES = tuple(SPECS)


def spec(type_: str) -> ArtifactSpec:
    if type_ not in SPECS:
        raise ValueError(f"Unknown artifact type {type_}. Use one of: {', '.join(TYPES)}.")
    return SPECS[type_]


def label(type_: str) -> str:
    return SPECS[type_].label if type_ in SPECS else type_


# ---------- checks on what the model generated ----------

_CLASS_CREATE = re.compile(r"var\s+(\w+)\s*=\s*Class\.create\(\)")
_TYPE_PROP = re.compile(r"type\s*:\s*['\"](\w+)['\"]")


def check(type_: str, data: dict) -> list[str]:
    """Problems with a generated artifact, in plain words. Empty list = usable.

    These are structural only: required fields, settings that contradict each other, and a script
    that doesn't match its record. The rules about what a script may *do* live in ai/checks.py, so
    each rule has exactly one home; `checks.generation_problems` runs both sets together.
    """
    sp = spec(type_)
    rec, script = data.get("record") or {}, (data.get("script") or "")
    out: list[str] = []
    missing = [f for f in sp.required if not str(rec.get(f, "")).strip() and rec.get(f) != ""]
    if missing:
        out.append(f"record is missing {', '.join(missing)}.")

    if type_ == "business_rule":
        if rec.get("when") != "display" and not any(
                rec.get(f) == "true" for f in ("action_insert", "action_update", "action_delete", "action_query")):
            out.append("A business rule must run on at least one of insert, update, delete or query.")
        if rec.get("action_query") == "true" and rec.get("when") != "before":
            out.append("A query business rule runs before the query: set when to 'before' with action_query true.")
        if "(function" not in script:
            out.append("Wrap the business rule's script in (function executeRule(current, previous) { … })(current, previous);.")

    if type_ == "script_include":
        name = str(rec.get("name") or "")
        found = _CLASS_CREATE.search(script)
        if found and found.group(1) != name:
            out.append(f"The script creates {found.group(1)} but the record is named {name}: they must match.")
        type_prop = _TYPE_PROP.search(script)
        if found and not type_prop:
            out.append("A Class.create() script include needs type: '<Name>' as its last property.")
        elif type_prop and type_prop.group(1) != name:
            out.append(f"The script's type is '{type_prop.group(1)}' but the record is named {name}: they must match.")
        if rec.get("client_callable") == "true" and "AbstractAjaxProcessor" not in script:
            out.append("A client-callable script include must extend global.AbstractAjaxProcessor.")

    if type_ == "client_script":
        kind = rec.get("type")
        if kind and f"function {kind}" not in script:
            out.append(f"The script must declare function {kind}(…) to match the record's type.")
        if kind == "onChange" and not str(rec.get("field_name") or "").strip():
            out.append("An onChange client script needs the field that triggers it.")
        if kind != "onChange" and str(rec.get("field_name") or "").strip():
            out.append(f"Only onChange client scripts have a field; clear field_name for {kind}.")
        if re.search(r"\bnew\s+GlideRecord\s*\(", script):
            out.append("Client scripts must not use GlideRecord: call a client-callable script include with GlideAjax instead.")
        if "getXMLWait" in script:
            out.append("getXMLWait freezes the browser: use getXMLAnswer with a callback.")

    if type_ == "ui_policy":
        for i, a in enumerate(data.get("actions") or [], 1):
            if a.get("mandatory") == "true" and a.get("visible") == "false":
                out.append(f"Action {i} ({a.get('field')}) makes a hidden field mandatory, so the form can't be saved.")
        if not (data.get("actions") or []):
            out.append("A UI policy needs at least one field action.")

    if type_ == "notification":
        by_event = bool(str(rec.get("event_name") or "").strip())
        by_record = rec.get("action_insert") == "true" or rec.get("action_update") == "true"
        if rec.get("triggered_by_flow") == "true":
            if by_event or by_record:
                out.append("A notification sent by a flow (triggered_by_flow) can't also send on insert, update or an event.")
        elif not by_event and not by_record:
            out.append("A notification needs something to trigger it: insert, update, or an event name.")
        if by_event and by_record:
            out.append("A notification is triggered either by insert/update or by an event, not both.")
        if not any(str(rec.get(f) or "").strip() for f in ("recipient_fields", "recipient_users", "recipient_groups")):
            out.append("A notification needs someone to send to: a field on the record, a user, or a group.")
        if str(rec.get("collection") or "") == "task":
            out.append("Notifications can't be built on the task table itself: use the child table (incident, change_request…).")

    if type_ == "flow":
        steps = data.get("steps") or []
        if not steps:
            out.append("A flow design needs its steps.")
        if [s.get("step") for s in steps] != list(range(1, len(steps) + 1)):
            out.append("Number the flow's steps 1, 2, 3 … in the order they run.")
        if rec.get("trigger") in ("Created", "Updated", "Created or Updated") and not str(rec.get("table") or "").strip():
            out.append(f"A {rec.get('trigger')} trigger needs the table it watches.")
        numbers = {s.get("step") for s in steps}
        for s in steps:
            if s.get("inside") and s.get("inside") not in numbers:
                out.append(f"Step {s.get('step')} sits inside step {s.get('inside')}, which isn't in the flow.")

    if type_ == "table":
        name = str(rec.get("name") or "")
        if name and not name.startswith(("u_", "x_")):
            out.append(f"A custom table in the global scope is named u_…: call it u_{name}.")
        if name == str(rec.get("super_class") or ""):
            out.append("A table can't extend itself.")
        if str(rec.get("super_class") or "") == "sys_choice":
            out.append("Extending sys_choice isn't supported by ServiceNow.")

    if type_ == "field":
        element = str(rec.get("element") or "")
        kind = rec.get("internal_type")
        if element and not element.startswith(("u_", "x_")):
            out.append(f"A custom field in the global scope is named u_…: call it u_{element}.")
        if kind in ("reference", "glide_list") and not str(rec.get("reference") or "").strip():
            out.append(f"A {kind} field needs the table it references.")
        if kind not in ("reference", "glide_list") and str(rec.get("reference") or "").strip():
            out.append("Only reference and list fields reference a table; clear reference.")
        choices = data.get("choices") or []
        if choices and rec.get("choice") not in ("1", "3"):
            out.append("Choice values need choice 1 (dropdown with --None--) or 3 (without).")
        if kind == "choice" and not choices:
            out.append("A choice field needs its choice values.")
        if rec.get("mandatory") == "true" and rec.get("read_only") == "true" and not str(rec.get("default_value") or ""):
            out.append("A field that is mandatory and read only needs a default value, or nobody can save the form.")
        values = [str(c.get("value")) for c in choices]
        if len(values) != len(set(values)):
            out.append("Two choices have the same value.")

    if type_ == "scheduled_job":
        kind = rec.get("run_type")
        if kind == "weekly" and not re.fullmatch(r"[1-7]", str(rec.get("run_dayofweek") or "")):
            out.append("A weekly job needs run_dayofweek 1 (Monday) to 7 (Sunday).")
        if kind == "monthly" and not re.fullmatch(r"([1-9]|[12]\d|3[01])", str(rec.get("run_dayofmonth") or "")):
            out.append("A monthly job needs run_dayofmonth 1-31.")
        if kind == "periodically" and not re.fullmatch(r"\d{2}:\d{2}:\d{2}", str(rec.get("run_period") or "")):
            out.append("A periodic job needs run_period as HH:MM:SS, e.g. 01:00:00.")
        if not script.strip():
            out.append("A scheduled job needs its script.")

    if type_ == "data_policy":
        if not (data.get("actions") or []):
            out.append("A data policy needs at least one field rule.")
        for i, a in enumerate(data.get("actions") or [], 1):
            if a.get("mandatory") == "ignore" and a.get("disabled") == "ignore":
                out.append(f"Rule {i} ({a.get('field')}) changes nothing: set mandatory or read only.")

    if type_ == "system_property":
        if not re.fullmatch(r"[a-z0-9_]+(\.[a-z0-9_]+)+", str(rec.get("name") or "")):
            out.append("A property name is lowercase dot.notation, e.g. incident.auto_close.days.")
        if rec.get("type") == "boolean" and str(rec.get("value")) not in ("true", "false"):
            out.append("A boolean property's value is true or false.")
        if rec.get("type") == "integer" and not re.fullmatch(r"-?\d+", str(rec.get("value") or "")):
            out.append("An integer property's value must be a whole number.")

    if type_ == "event":
        if not re.fullmatch(r"[a-z0-9_]+(\.[a-z0-9_]+)+", str(rec.get("event_name") or "")):
            out.append("An event name is lowercase dot.notation, e.g. incident.p1.escalated.")

    if type_ == "script_action":
        if not str(rec.get("event_name") or "").strip():
            out.append("A script action needs the event it runs on.")

    if type_ == "ui_action":
        if not any(rec.get(f) == "true" for f in ("form_button", "form_link", "list_button")):
            out.append("A UI action has to appear somewhere: form button, form link or list button.")
        if rec.get("client") == "true" and not str(rec.get("onclick") or "").strip():
            out.append("A client UI action needs the onclick function to call.")
        if rec.get("client") == "false" and str(rec.get("onclick") or "").strip():
            out.append("onclick only applies to client UI actions; clear it or set client to true.")
    return out


# ---------- turning a generated artifact into Table API records ----------

def to_records(type_: str, data: dict) -> list[dict]:
    """[{table, fields, role}] ready for the Table API, parent first (used when deploying).

    Fields ServiceNow needs that the model shouldn't have to remember are set here:
    - a business rule with a script is `advanced` (the script tab only applies to advanced rules);
    - a notification's `generation_type` (Send when): engine (insert/update), event, or triggered (a flow);
    - each UI policy action / data policy rule carries the policy's table, as the form-built ones do;
    - a scheduled job's times are stored as 1970-01-01 HH:MM:SS (glide_date_time / glide_duration).
    """
    sp = spec(type_)
    fields = {k: v for k, v in (data.get("record") or {}).items() if v is not None}
    if sp.has_script:
        fields[sp.script_field] = data.get("script") or ""
    if type_ == "business_rule":
        fields["advanced"] = "true"
    if type_ == "script_include":
        fields.pop("api_name", None)          # computed by the instance from scope + name
    if type_ == "scheduled_job":
        # glide_date_time / glide_duration columns store a time of day as a date on 1970-01-01
        for key in ("run_time", "run_period"):
            value = str(fields.get(key) or "").strip()
            fields[key] = f"1970-01-01 {value}" if re.fullmatch(r"\d{2}:\d{2}:\d{2}", value) else value
        for key in ("run_dayofweek", "run_dayofmonth", "run_period"):
            if not str(fields.get(key) or "").strip():
                fields.pop(key, None)
    if type_ == "notification":
        triggered = str(fields.pop("triggered_by_flow", "false")) == "true"
        fields["generation_type"] = ("triggered" if triggered else
                                     "event" if str(fields.get("event_name") or "").strip() else "engine")
    if type_ in ("table", "field"):
        for key in ("super_class", "max_length", "reference", "choice", "default_value"):
            if not str(fields.get(key) or "").strip():
                fields.pop(key, None)                   # unset rather than written as empty
    if type_ in ("catalog_item", "record_producer"):
        for key in ("category", "description"):
            if not str(fields.get(key) or "").strip():
                fields.pop(key, None)
    out = [{"table": sp.table, "fields": fields, "role": "main"}]
    for key, child in sp.children.items():
        for item in data.get(key) or []:
            child_fields = dict(item)
            if "copy" in child:                          # linked by values, not by the parent's sys_id
                for to, frm in child["copy"].items():
                    child_fields[to] = fields.get(frm, "")
                if child["table"] == "sys_choice":
                    child_fields.setdefault("language", "en")
                    child_fields.setdefault("inactive", "false")
            elif child["table"] == "item_option_new":
                child_fields["type"] = VARIABLE_TYPES.get(str(child_fields.get("type")), str(child_fields.get("type")))
                for k in ("reference", "help_text"):
                    if not str(child_fields.get(k) or "").strip():
                        child_fields.pop(k, None)
                child_fields.setdefault("active", "true")
            elif sp.table_field and fields.get(sp.table_field):    # the policy's table on each field rule
                child_fields.setdefault("table", fields[sp.table_field])
            out.append({"table": child["table"], "fields": child_fields, "role": key,
                        "parent_field": child["parent_field"]})
    return out


def display_name(type_: str, data: dict) -> str:
    rec = data.get("record") or {}
    return str(rec.get(spec(type_).name_field) or "").strip()


def apply_aliases(type_: str, fields: dict, columns: set[str]) -> dict:
    """Rename settings to the column this instance's table actually has (see ArtifactSpec.aliases)."""
    sp = spec(type_)
    if not sp.aliases or not columns:
        return fields
    out = dict(fields)
    for name, others in sp.aliases.items():
        if name in out and name.lower() not in columns:
            for other in others:
                if other.lower() in columns:
                    out[other] = out.pop(name)
                    break
    return out

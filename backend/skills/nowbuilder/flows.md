# Flows

A flow row is deployed with the **ServiceNow SDK**: nowBuilder turns the design into ServiceNow
Fluent source (`Flow(...)`, `wfa.trigger(...)`, `wfa.action(...)`, `wfa.flowLogic...`), builds it
and installs it into the plan's application - Global (through nowBuilder's Global application) by
default, or nowBuilder's scoped app when the instance can't take a Global application (the result
says so) - then reads the flow back from `sys_hub_flow`, including the scope it landed in. When no SDK project is configured, or the design uses something the exporter
can't express, the row stays a design and the user builds it in Flow Designer from its steps. Either
way the design has to be exact: a step that names an action the instance doesn't have, or inputs the
action doesn't take, fails the install or wastes the user's time.

## Read the instance first

1. **`get_flow_actions`** with no filter: the actions this instance has. Which actions exist depends
   on the release and on which spokes are installed, so never name one from memory.
2. **`get_flow_actions` with `name_contains`** for each action you will use: it returns the action's
   real inputs. Input names differ between actions, so this is the only way to get them right.
3. **`search_instance_artifacts` with `type: "flow"`**: if a flow already does this, say so and
   propose changing it rather than adding a second one that fights it.
4. **`get_table_schema`** for the trigger table, as for any other artifact.

## The flow record

- `trigger`: `Created`, `Updated` or `Created or Updated` for a record trigger (there is no deleted
  trigger); `Daily` with `schedule_time` (HH:MM) for a daily schedule; `Service Catalog`,
  `Inbound Email`, `SLA Task` for application triggers. Weekly, Monthly, Repeat and Run Once are
  designed but built by hand.
- `table`: the trigger table (the target table for Inbound Email); empty for a schedule.
- `trigger_condition`: an encoded query on the trigger table (`priority=1^active=true`), empty for
  every record. Put the filter here, never in an `If` as the first step.
  A "changes" condition (`ownerVALCHANGES`, `stateCHANGESTO6`, "when the owner changes") only works
  with the **Updated** trigger: on Created or Created or Updated, Flow Designer shows "Operator is
  unrecognized". For "when X is set on create or changed later", use Updated with the changes
  condition, or Created or Updated with a plain condition (`ownerISNOTEMPTY`) and say which you chose.
- `run_trigger`: `once`, `for each unique change` (a field changing again runs it again) or `always`.
- `run_as`: `System user` when it must work whoever triggered it (bypasses ACLs - say so in the
  summary); `User who initiated session` when the user's ACLs should apply.

## The steps

- `name` is exactly what Flow Designer shows, spelled as `get_flow_actions` returned it:
  `Look Up Record`, `Look Up Records`, `Create Record`, `Update Record`, `Send Notification`,
  `Ask For Approval`, `Log`; logic is `If`, `Else If`, `Else`, `For Each`, `Do the following until`, `Wait for a duration`, `End Flow`.
- `kind`: `action`, `flow logic`, or `subflow`.
- Number the steps `1, 2, 3 …` in the order they run.
- **Nesting:** a step inside an If / Else If / Else / For Each / Do the following until sets `inside` to that step's number.
  An `Else If` or `Else` comes straight after its `If` (or `Else If`) at the same level.
- **If / Else If:** `condition` is the condition with pills, e.g. `{{trigger.current.priority}}=1`
  or `{{step1.Record.manager}}ISNOTEMPTY`.
- **For Each:** `items` is the records to loop over, e.g. `{{step2.Records}}` from a Look Up Records
  step; steps inside read the current record as `{{item.<field>}}`.
- `detail`: how to fill the step in, in words, so a person could build it by hand.
- `inputs`: the action's **real input names** mapped to values. Always fill it for actions - a step
  with only `detail` can't be deployed. Values may use:
  - `{{trigger.current.<field>}}` - the triggering record (`{{trigger.current.sys_id}}` for the record itself)
  - `{{step<n>.<Output>}}` - an earlier step's output (`{{step1.Record.email}}`, `{{step2.Records}}`)
  - `{{item.<field>}}` - the current record inside a For Each
  - `{{plan.<row id>}}` - another row of this plan, replaced by its sys_id once deployed (the
    notification a Send Notification step selects: `"notification": "{{plan.c1}}"`)
  - a Fields/values input takes an object of column names: `"values": {"state": "2", "work_notes": "..."}`

  ```json
  {"step": 2, "kind": "action", "name": "Update Record", "inside": 1,
   "detail": "Record: Trigger → Incident. Set state to In Progress and add a work note.",
   "inputs": {"table_name": "incident", "record": "{{trigger.current.sys_id}}",
              "values": {"state": "2", "work_notes": "Escalated to {{step1.Record.name}}."}}}
  ```

## Sending email from a flow

Follow what the user or document asks for. Both are deployable:

- **Send Email** recipients (`ah_to`, `ah_cc`, `ah_bcc`) are **email addresses**: a person is
  `{{trigger.current.caller_id.email}}`, a group is `{{trigger.current.assignment_group.email}}` (the
  group's *Group email*; check it's filled in with `query_instance_records`, and if it isn't, say so -
  a notification with the group as recipient reaches its members). A record pill on its own
  (`{{trigger.current.assignment_group}}`) sends a sys_id and the instance rejects the email.
- **Send Email** recipients (`ah_to`, `ah_cc`, `ah_bcc`) are email addresses: use the email field of a user
  or group (`{{trigger.current.assignment_group.email}}`, `{{trigger.current.owner.email}}`). A group
  needs its Group email filled in - check it with `query_instance_records`; if it's empty, say so and
  offer a notification, which can email each member.
- **Send Email** (`action.core.sendEmail`): `ah_to` and `ah_subject` take pills; `table_name` + `record`
  link the email to the record. The Fluent action API says `ah_body` takes no data pills, so for the
  body read every value from the **trigger record** - `{{trigger.current.<field>}}`, dot-walks such as
  `{{trigger.current.owner.name}}` included. nowBuilder writes those the way Flow Designer stores a pill
  in an input value, so the flow fills them in when it runs (and falls back to [placeholders] if an
  SDK refuses that). A pill from another step in the body can't be carried: re-read the field from
  the trigger record instead. A record link: `<a href="/nav_to.do?uri=<table>.do?sys_id={{trigger.current.sys_id}}">`.
- **Send Notification** + a `notification` row (`triggered_by_flow` "true", `${field}` placeholders,
  `{{plan.<id>}}` in the step) carries record values with no manual step: offer it when the user hasn't
  said which, and use it when they want a notification.
- When the document says "Send Email only, no notification", never add a notification row.

## Waiting, loops and repeats (inside the flow)

The ServiceNow SDK writes these logic blocks (Fluent Flow Logic API, SDK 4.14): **If, Else If, Else,
For Each, Do the following until, Wait for a duration, End Flow, Exit Loop, Skip Iteration**.
Do the following in parallel and Try / Catch aren't exported yet.

- **Do the following until** (`wfa.flowLogic.doTheFollowing` + `wfa.flowLogic.until`): steps inside set
  `inside` to its number. Its `condition` is the exit condition, an encoded query checked **after each
  pass** (the body always runs once). To stop on a field changing (Stage, State), put a **Look Up Record**
  of the trigger record (`sys_id={{trigger.current.sys_id}}`) inside the loop and use its output in the
  condition: `{{step4.Record.stage}}IN300_nurturing,400_closed_won,500_closed_lost`. Use the field's real
  choice **values** (read them from `sys_choice` with `query_instance_records`), not the labels.
  A pill compared with a list (`IN a,b,c`) is written as `=a^OR…=b` for the instance, which rejects
  IN after a data pill in flow logic.
- **Wait for a duration**: `{"kind": "flow logic", "name": "Wait for a duration", "duration": "2 minutes"}`
  (also "00:02:00" or `{"minutes": 2}`).
- "Repeat every N minutes until X" is one loop: Wait for a duration → Look Up Record → the repeated
  action(s), `until` X. Every loop needs a real exit condition; if the request has none, ask, or end it
  on the record being closed and say so in `assumptions`.
- Order inside a loop: `until` comes last automatically; every step inside sets `inside`.

A whole flow, "email the lead owner now and every 2 minutes until the stage closes":

```json
{"record": {"name": "Lead owner email", "table": "sn_lead_mgmt_core_lead", "trigger": "Created or Updated",
            "trigger_condition": "ownerISNOTEMPTY", "run_trigger": "always", "run_as": "System user",
            "description": "Emails the lead owner, then every 2 minutes until the lead's stage closes."},
 "steps": [
  {"step": 1, "kind": "action", "name": "Send Email", "detail": "Email the owner now.",
   "inputs": {"table_name": "sn_lead_mgmt_core_lead", "record": "{{trigger.current.sys_id}}",
              "ah_to": "{{trigger.current.owner.email}}", "ah_subject": "New Lead Assignment - {{trigger.current.number}}",
              "ah_body": "<p>Hi {{trigger.current.first_name}},</p><p>Owner: {{trigger.current.owner.name}}</p>"}},
  {"step": 2, "kind": "flow logic", "name": "Do the following until", "detail": "Repeat until the stage closes.",
   "condition": "{{step4.Record.stage}}IN300_nurturing,400_closed_won,500_closed_lost"},
  {"step": 3, "kind": "flow logic", "name": "Wait for a duration", "inside": 2, "duration": "2 minutes",
   "detail": "Wait 2 minutes."},
  {"step": 4, "kind": "action", "name": "Look Up Record", "inside": 2, "detail": "Re-read the lead.",
   "inputs": {"table": "sn_lead_mgmt_core_lead", "conditions": "sys_id={{trigger.current.sys_id}}"}},
  {"step": 5, "kind": "action", "name": "Send Email", "inside": 2, "detail": "Send the email again.",
   "inputs": {"table_name": "sn_lead_mgmt_core_lead", "record": "{{trigger.current.sys_id}}",
              "ah_to": "{{trigger.current.owner.email}}", "ah_subject": "New Lead Assignment - {{trigger.current.number}}",
              "ah_body": "<p>Hi {{trigger.current.first_name}},</p><p>Owner: {{trigger.current.owner.name}}</p>"}}]}
```

## Rows around the flow

- A `Send Notification` step needs a **notification** row in the same plan; the flow `dependsOn`
  it and points at it with `{{plan.<id>}}`. Set that notification's `triggered_by_flow` to `"true"`
  (Send when: Triggered) with insert, update and `event_name` off, so it is sent only by the flow
  and not a second time on save.
- Logic too involved for flow steps belongs in a **script include** the flow calls.
- Anything the flow reads that doesn't exist yet (a group, a property) goes in `assumptions`.

## What to say

Report what the tool result says for the flow: deployed (with its Flow Designer link, whether it
is active and the application it is in - repeat any `application_note`), design only (build it in Flow Designer, or set up the SDK project), or failed (the
error, and what to change). Never call a flow deployed or active without that result.

## Worked examples (copy this shape exactly)

**Prompt:** "Create a flow 'SF - Incident created log': when an incident is created, log an info
message with the incident number and short description."

Plan row: `{"id": "c1", "type": "flow", "name": "NB - Incident created log", "table": "incident",
"purpose": "On incident created, log number and short description"}`

Generated flow:
```json
{"record": {"name": "NB - Incident created log", "table": "incident", "trigger": "Created",
            "trigger_condition": "", "run_trigger": "once", "run_as": "System user", "schedule_time": "",
            "description": "Logs every new incident."},
 "steps": [{"step": 1, "kind": "action", "name": "Log",
            "detail": "Level info; message: Incident created + number + short description pills.",
            "inputs": {"log_level": "info",
                       "log_message": "Incident created: {{trigger.current.number}} - {{trigger.current.short_description}}"}}]}
```

**Prompt:** "When a P1 incident is created, look up its assignment group; if the group has a
manager add a work note naming them, otherwise log a warning."

```json
{"record": {"name": "NB - P1 manager alert", "table": "incident", "trigger": "Created",
            "trigger_condition": "priority=1", "run_trigger": "once", "run_as": "System user",
            "schedule_time": "", "description": "Names the group manager on new P1 incidents."},
 "steps": [
   {"step": 1, "kind": "action", "name": "Look Up Record", "detail": "Group of the incident.",
    "inputs": {"table": "sys_user_group", "conditions": "sys_id={{trigger.current.assignment_group}}"}},
   {"step": 2, "kind": "flow logic", "name": "If", "detail": "Group has a manager",
    "condition": "{{step1.Record.manager}}ISNOTEMPTY"},
   {"step": 3, "kind": "action", "name": "Update Record", "inside": 2, "detail": "Work note with the manager.",
    "inputs": {"table_name": "incident", "record": "{{trigger.current.sys_id}}",
               "values": {"work_notes": "Escalated: {{step1.Record.name}} has a manager assigned."}}},
   {"step": 4, "kind": "flow logic", "name": "Else", "detail": "No manager"},
   {"step": 5, "kind": "action", "name": "Log", "inside": 4, "detail": "Warn.",
    "inputs": {"log_level": "warn", "log_message": "No manager for {{trigger.current.number}}"}}]}
```

**Prompt:** "When a P1 incident is created, email the caller." (asked for as a flow)

Plan rows: `c1` notification (`triggered_by_flow` "true", `recipient_fields` "caller_id") and `c2`
flow with `"dependsOn": ["c1"]`. The flow's step:
```json
{"step": 1, "kind": "action", "name": "Send Notification", "detail": "Send the c1 notification.",
 "inputs": {"table_name": "incident", "record": "{{trigger.current.sys_id}}", "notification": "{{plan.c1}}"}}
```

**Prompt:** "When an incident's priority changes to 1, set every child incident to priority 1."

```json
{"record": {"name": "NB - Escalate child incidents", "table": "incident", "trigger": "Updated",
            "trigger_condition": "priority=1^priorityVALCHANGES", "run_trigger": "for each unique change",
            "run_as": "System user", "schedule_time": "", "description": "Raises children of P1 incidents."},
 "steps": [
   {"step": 1, "kind": "action", "name": "Look Up Records", "detail": "Child incidents.",
    "inputs": {"table": "incident", "conditions": "parent_incident={{trigger.current.sys_id}}^active=true"}},
   {"step": 2, "kind": "flow logic", "name": "For Each", "detail": "Each child", "items": "{{step1.Records}}"},
   {"step": 3, "kind": "action", "name": "Update Record", "inside": 2, "detail": "Raise priority.",
    "inputs": {"table_name": "incident", "record": "{{item.sys_id}}",
               "values": {"impact": "1", "urgency": "1", "work_notes": "Parent became P1"}}}]}
```
Note: priority is calculated from impact and urgency, so set those, not `priority`.

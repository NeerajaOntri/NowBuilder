---
name: servicenow-flow-designer
description: Building ServiceNow flows, subflows and custom actions in Flow Designer (Workflow Studio) and as ServiceNow Fluent source with the ServiceNow SDK - triggers, flow logic, data pills, run-as context, error handling, script steps, IntegrationHub spokes and REST steps, testing and execution details. Use when automating a process with a flow, choosing between a flow and a Business Rule, writing a flow in Fluent, or debugging a flow that didn't run or ran too often.
license: Apache-2.0
metadata:
  category: automation
  version: "1.1"
---

# Flow Designer

## When to use
- Multi-step, business-readable automation: approvals, task creation, notifications, integrations.
- Replacing legacy Workflow Editor workflows.
- Packaging reusable steps as **actions** and **subflows**.

## Building blocks
| Block | What it is |
|---|---|
| **Flow** (`sys_hub_flow`, type flow) | Trigger + sequence of actions and logic |
| **Trigger** | Record: *Created*, *Updated*, *Created or Updated*. Scheduled: *Daily*, *Weekly*, *Monthly*, *Repeat*, *Run Once*. Application: *Service Catalog*, *Inbound Email*, *SLA Task* and others. There is no "record deleted" trigger |
| **Action** | Reusable unit with inputs and outputs (core, spoke or custom); definitions in `sys_hub_action_type_definition` |
| **Subflow** (`sys_hub_flow`, type subflow) | Reusable sequence with inputs/outputs, called from flows |
| **Flow logic** | If / Else If / Else, For Each, Do the following until, Do the following in parallel, Wait for a duration, Try / Catch, Set flow variables, Exit loop, Skip iteration, End flow |
| **Data pill** | Reference to the trigger record, an action output or a flow variable |

## Core action names (exactly as Flow Designer shows them)
*Look Up Record*, *Look Up Records*, *Create Record*, *Update Record*, *Create or Update Record*, *Update Multiple Records*, *Delete Record*, *Create Task*, *Ask For Approval*, *Wait For Condition*, *Send Notification*, *Send Email*, *Send SMS*, *Log*, *Fire Event*, *Get Catalog Variables*, *Create Catalog Task*, *Copy Attachment*, *Get Attachments on Record*. Spoke actions depend on what is installed and licensed - read the instance's action list rather than naming one from memory.

## Rules
1. **Trigger precisely.** Record triggers need a tight condition and the right run setting (*Run trigger*: *Once*, *For each unique change*, *Always*). Avoid "Updated" with no condition on busy tables - it fires on every save.
2. **Run as:** *System user* for automation that must succeed regardless of who triggered it (it bypasses ACLs); *User who initiated session* when ACLs should apply. Choose deliberately.
3. Put reusable sequences in **subflows**, single operations in **actions**. Flows should read like the business process.
4. **Error handling:** wrap risky steps (REST, record updates on other tables) in *Try* or use the flow's error handler; on failure, set a status field, add a work note and notify an owner.
5. Prefer OOB actions and **spokes** over Script steps. If you need a script step, keep it short and call a Script Include.
6. Integrations: use the **REST step** with a **Connection & Credential alias** (IntegrationHub; check licensing) - never credentials in inputs.
7. Use **flow variables** for values computed mid-flow; name them clearly.
8. Avoid long *Wait for condition* on high-volume records; use SLAs, timers or events.
9. **Test** with the *Test* button against a real record, then read **Flow execution details**; report failed executions on a dashboard.
10. Flows are captured in update sets / the application; activate only after testing; deactivate old versions.
11. For catalog items, attach the flow on the item and use **Get Catalog Variables** to read variables.
12. A *Send Notification* step selects an existing notification record (`sysevent_email_action`) - create that notification first.

## Writing a flow as source: ServiceNow Fluent (ServiceNow SDK)
A flow can't be created by inserting a `sys_hub_flow` row through the Table API: its trigger, action instances, data-pill bindings and compiled snapshot live across several `sys_hub_*` tables. The supported code route is a **scoped** ServiceNow SDK application (`now-sdk init`, scope `x_<prefix>_<app>`) with the flow in a `.now.ts` file, then `now-sdk build` and `now-sdk install` (flows are activated on install unless `--skip-flow-activation` is set).

```typescript
import { action, Flow, wfa, trigger } from '@servicenow/sdk/automation'

export const p1EscalationFlow = Flow(
    { $id: Now.ID['p1_escalation_flow'], name: 'P1 escalation', description: 'Escalates new P1 incidents', runAs: 'system' },
    wfa.trigger(trigger.record.created, { $id: Now.ID['p1_trigger'] },
        { table: 'incident', condition: 'priority=1', run_flow_in: 'background' }),
    (params) => {
        const group = wfa.action(action.core.lookUpRecord, { $id: Now.ID['find_group'] }, {
            table: 'sys_user_group',
            conditions: `sys_id=${wfa.dataPill(params.trigger.current.assignment_group, 'reference')}`,
        })
        wfa.flowLogic.if(
            { $id: Now.ID['has_manager'], condition: `${wfa.dataPill(group.Record.manager, 'reference')}ISNOTEMPTY` },
            () => {
                wfa.action(action.core.updateRecord, { $id: Now.ID['note_manager'] }, {
                    table_name: 'incident',
                    record: wfa.dataPill(params.trigger.current.sys_id, 'reference'),
                    values: TemplateValue({ work_notes: `Escalated to ${wfa.dataPill(group.Record.name, 'string')}` }),
                })
            })
    })
```
- Triggers: `trigger.record.created | updated | createdOrUpdated` (`table`, `condition`, `trigger_strategy`: `once`, `unique_changes`, `always`), `trigger.scheduled.daily` (`time: Time({ hours, minutes, seconds })`), `trigger.application.serviceCatalog`, `trigger.application.inboundEmail`.
- Actions: `action.core.<camelCase name>` with the action's real input names (`table_name`, `record`, `values` for Update Record; `table`, `conditions` for Look Up Record(s); `table_name`, `record`, `notification` for Send Notification; `log_level`, `log_message` for Log).
- Logic: `wfa.flowLogic.if / elseIf / else / forEach / endFlow`; `forEach(stepN.Records, { $id }, (item) => { ... })`.
- Static-only inputs: Html-typed inputs (Send Email's `ah_body`) must be fixed strings - the build fails
  with TS228 on a data pill. Put record values in a notification and use `action.core.sendNotification`.
- Pills: `wfa.dataPill(<path>, '<type>')` - `params.trigger.current.<field>`, `<step>.Record.<field>`, `item.<field>`.
- `runAs` is `system` or `user`; `$id` values must be unique in the application.

## Example: incident triage flow (designer steps)
1. Trigger: Incident **Created**, condition *Assignment group is empty*.
2. Action: *Look Up Record* on `sys_user_group` for the category's group (from a property or decision table).
3. If *a group was found*:
   - *Update Record*: set the assignment group from step 2.
4. Else:
   - *Update Record*: add a work note that no group matched.
5. Try/error handler: log, add a work note, notify the owning group.

## Anti-patterns
- Flow on `task` "Created or Updated" with no condition.
- Business logic duplicated in both a Business Rule and a flow.
- Script steps that are 100 lines long.
- Hard-coded group sys_ids in actions (use lookups or properties).
- Inserting `sys_hub_flow` records through the Table API and calling that a flow.

## Review checklist
- [ ] Narrow trigger, right run setting
- [ ] Run-as context chosen
- [ ] Error handling and owner notification
- [ ] Subflows/actions for reuse; minimal script steps
- [ ] Credentials via aliases
- [ ] Tested; execution details reviewed; activated deliberately

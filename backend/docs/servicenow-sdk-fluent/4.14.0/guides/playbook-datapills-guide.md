Version: 4.14.0

# Playbook datapills guide

Practical guide for configuring datapills in playbook, which allows you to reference runtime values during playbook execution.

## When to Use

- You have an activity input or experience property that needs to be set to the output, state, or sysId of another activity

- You have an activity input or experience property that gets its value from a playbook input

- You have an activity input or experience property that gets its value from a field in the parent record

- You are providing a playbook parent record from a trigger record

- You are setting a playbook input value based on a field in the trigger record

- You have an activity input or experience property that needs to match the activity's label or description

- You have an activity input or experience property that needs the value of the playbook state

- You have a condition to run that uses the output of a previous activity

### wfa.playbook.dataPill()

Creates runtime references to playbook data for use in trigger mappers, activity inputs, experience properties, conditions, and timer fields.

```
wfa.playbook.dataPill(reference: DataReference): string
```

#### Pill Sources

| Source | Example |
| `params.inputs.*` | `wfa.playbook.dataPill(params.inputs.record.number)` |
| `params.state` | `wfa.playbook.dataPill(params.state)` |
| `params.parentRecord.*` | `wfa.playbook.dataPill(params.parentRecord.short_description)` |
| `trigger.current` / `trigger.current.*` (mapper only) | `wfa.playbook.dataPill(trigger.current.short_description)` |
| Activity outputs (same lane) | `wfa.playbook.dataPill(validate.outputs.record.state)` |
| Activity outputs (cross-lane) | `wfa.playbook.dataPill(intake.enrich.outputs.support_tier)` |
| Activity state | `wfa.playbook.dataPill(validate.state)` |
| Activity sysId | `wfa.playbook.dataPill(validate.sysId)` |
| Current activity label | `wfa.playbook.dataPill(wfa.playbook.currentActivity.label)` |
| Current activity description | `wfa.playbook.dataPill(wfa.playbook.currentActivity.description)` |
| Automation plan output | `wfa.playbook.dataPill(wfa.playbook.automationPlan().outputs.record)` |
| Automation plan input | `wfa.playbook.dataPill(wfa.playbook.automationPlan().inputs.table_name)` |
| Automation plan output, specific step | `wfa.playbook.dataPill(wfa.playbook.automationPlan('<uiId>').outputs.record)` |
| Automation plan input, specific step | `wfa.playbook.dataPill(wfa.playbook.automationPlan('<uiId>').inputs.record)` |

`trigger.current` and `trigger.current.*` are only available inside the optional `playbookInputs` mapper callback passed to `wfa.playbook.trigger(...)`. They are not available in lane/activity fields like `params.inputs.*` and `params.parentRecord.*`.

#### Pill Format Reference

Standard format (activity inputs, experience properties, `startWithDelay` timer fields):

| Fluent expression | Platform format |
| `params.inputs.varName` | `{{pd.inputs.varName}}` |
| `params.inputs.varName.field` | `{{pd.inputs.varName.field}}` |
| `params.state` | `{{pd.state}}` |
| `params.parentRecord` | `{{pd.inputRecord}}` |
| `params.parentRecord.field` | `{{pd.inputRecord.field}}` |
| `activityVar.outputs.field` | `{{act.<sysId>.outputs.field}}` |
| `activityVar.state` | `{{act.<sysId>.state}}` |
| `activityVar.sysId` | `{{act.<sysId>.outputs.sys_id}}` |
| `wfa.playbook.currentActivity.label` | `{{act.<sysId>.label}}` |
| `wfa.playbook.currentActivity.description` | `{{act.<sysId>.description}}` |
| `wfa.playbook.automationPlan().outputs.field` | `{{vl.<backing flow/action label>./end.field}}` |
| `wfa.playbook.automationPlan().inputs.field` | `{{vl.<backing flow/action label>./start.field}}` |
| `wfa.playbook.automationPlan('<uiId>').outputs.field` | `{{vl.<backing flow/action label>.<uiId>./end.field}}` |
| `wfa.playbook.automationPlan('<uiId>').inputs.field` | `{{vl.<backing flow/action label>.<uiId>./start.field}}` |

Condition format (`conditionToRun` on lanes/activities, Decision branch `condition`):

| Fluent expression | Platform format |
| `params.inputs.varName` | `inputs.varName` |
| `params.inputs.varName.field` | `inputs.varName.field` |
| `params.parentRecord.field` | `input_record.field` |
| `activityVar.outputs.field` | `activity_<sysId>.outputs.field` |
| `activityVar.state` | `activity_<sysId>.state` |

Note: `activityVar.sysId` is not available in condition format.

#### Pill Validation Matrix

| Target field | Format | `params.inputs.*` | `params.state` | `params.parentRecord.*` | Activity outputs | Activity state | Activity sysId | Current activity label/desc | Automation plan |
| Activity inputs | Standard | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No |
| Activity experience properties | Standard | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| `startWithDelay` fields | Standard | Yes | Yes | Yes | Yes | Yes | Yes | No | No |
| Activity `conditionToRun` | Condition | Yes | No | Yes | Yes | Yes | No | No | No |
| Lane `conditionToRun` | Condition | Yes | No | Yes | Yes | Yes | No | No | No |
| Decision branch `condition` | Condition | Yes | No | Yes | Yes | Yes | No | No | No |

A diagnostic error is emitted if a `wfa.playbook.dataPill()` call is used in any field not listed above.

#### wfa.playbook.currentActivity

Allows an activity's inputs or experience properties to reference its own `label` or `description`. Use this instead of the activity variable to avoid "variable used before declaration" TypeScript errors:

```
const myActivity = wfa.playbook.activity(
    ActivityDefinitions.Core.RecordForm,
    { $id: Now.ID['my_form'], label: 'Review Incident', ... },
    { /* inputs */ },
    {
        title: wfa.playbook.dataPill(wfa.playbook.currentActivity.label),
        description: wfa.playbook.dataPill(wfa.playbook.currentActivity.description),
    }
)
```

Only `label` and `description` are valid after `wfa.playbook.currentActivity`. Any other property access produces a diagnostic error.

#### wfa.playbook.automationPlan()

A reference to an input or output on the current activity's own backing flow or action (the `Subflow(...)`/`Action(...)` behind the activity definition's `flow`/`action`). There is no "which activity" argument — it always resolves relative to whichever activity instance the pill is defined on. Only usable inside `Activity().experienceProperties`.

```
const updateRecord = wfa.playbook.activity(
    ActivityDefinitions.Core.RecordForm,
    { $id: Now.ID['my_form'], label: 'Review Incident', ... },
    { /* inputs */ },
    {
        experience_status_record: wfa.playbook.dataPill(
            wfa.playbook.automationPlan('e17e6678-8e97-4584-a903-cfa6e47fd378').outputs.record
        ),
    }
)
```

The optional `uiId: string` argument identifies a specific step (action or subflow) within the backing flow when it is itself composed of multiple steps; omit it to reference the backing flow/action's own inputs/outputs directly. `uiId` must be a string literal — a variable or other expression produces a diagnostic error. `uiId` is only valid when the activity definition is backed by a Subflow; it produces a diagnostic error when the definition is backed by an Action, since an Action has no sub-steps to reference.
uiId can be found for a step by going to the instance and looking up the action step in `sys_hub_action_instance_v2` or `sys_hub_action_instance`, or the subflow step in `sys_hub_sub_flow_instance_v2` or `sys_hub_sub_flow_instance` table. The field is `ui_id`.
Only `inputs` and `outputs` are valid in the return of `wfa.playbook.automationPlan`, from which a specific input or output can be selected. An input or output that is a reference type can be dot-walked (for example, `outputs.record.user.name`).

### _tableName pill

`_tableName` is a property that is appended to pill sources to have the data pill reference the table name of a record
reference. For example, `wfa.playbook.dataPill(params.parentRecord._tableName)` will reference the table name of the
record referenced by `params.parentRecord`.

`_tableName` is not available in condition pills, and only applicable to references, not primitive values.

#### Examples of _tableName usage

```
wfa.playbook.dataPill(params.parentRecord._tableName)
wfa.playbook.dataPill(params.parentRecord.subRecord._tableName)
wfa.playbook.dataPill(params.inputs.recordInput._tableName)
wfa.playbook.dataPill(params.inputs.recordInput.subRecord._tableName)
wfa.playbook.dataPill(trigger.current._tableName)
wfa.playbook.dataPill(trigger.current.subRecord._tableName)
wfa.playbook.dataPill(activityVar.outputs.record._tableName)
wfa.playbook.dataPill(activityVar.outputs.record.subRecord._tableName)
wfa.playbook.dataPill(wfa.playbook.automationPlan().outputs.record._tableName)
wfa.playbook.dataPill(wfa.playbook.automationPlan().inputs.record._tableName)
```

#### Examples of disallowed _tableName usage (using it with primitives)

```
wfa.playbook.dataPill(params.parentRecord.active._tableName)
wfa.playbook.dataPill(params.inputs.boolInput._tableName)
wfa.playbook.dataPill(trigger.current.active._tableName)
wfa.playbook.dataPill(activityVar.outputs.boolOutput._tableName)
wfa.playbook.dataPill(wfa.playbook.currentActivity.label._tableName)
wfa.playbook.dataPill(activityVar.state._tableName)
```

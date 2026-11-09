Version: 4.14.0

# Playbook Activities Guide

An activity is a single step inside a playbook lane — present a form to a user, send an email, update a record,
branch on a condition, and so on. Every step a playbook performs is an activity. This guide covers a representative
subset of the built-in activities shipped with the SDK: interactive activities (Instruction, RecordForm,
KnowledgeArticle, ChecklistTask, …), automation activities (UpdateRecord, CreateNewRecord, SendEmail, …), approval
activities, the Decision branching activity, the RecordList display activity, experience properties, how to read a
built-in definition's backing flow/action and activity type files, AI agent configuration on supported form
activities, and the stage-level Decision pattern (a Decision placed at the lanes body level rather than inside a
lane). The full set of exports lives under `src/api/playbook/built-ins/activity-definitions/`; for
`wfa.playbook.activity` signatures and the data pill validation matrix see `playbook-api`.

## When to Use

- You need to present an interactive step to a user — a form, checklist, knowledge article, or instruction

- You need to run automation as part of a workflow step — update a record, create a record, send email

- You need to branch execution based on data values using a Decision activity

- You need to configure how a step appears in the playbook UI (title, description, icon)

- You need to pass runtime values between activities using data pills

## Activity call shape

Every activity is a 4-argument call. The fourth argument controls UI presentation and is optional for non-interactive activities.

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

const welcome = wfa.playbook.activity(
    ActivityDefinitions.Core.Instruction,
    {
        $id: Now.ID['act_welcome'],
        label: 'Welcome',
        order: 1,
        startRule: wfa.playbook.run.Immediately(),
        restartRule: 'RUN_ONLY_ONCE',
    },
    {
        message: 'Welcome! Please review the details below.',
        wait: 'yes',
    },
    {
        tagline: 'Getting Started',
        title: 'Welcome',
        description: 'Follow the instructions to complete this task.',
        icon: 'info-circle-outline',
    },
)
```

| Parameter | Required | Purpose |
| `activityDefinition` | Yes | `ActivityDefinitions.Core.*` — which activity to instantiate |
| `config` | Yes | Identity, ordering, execution and restart rules |
| `inputs` | No | Data passed to the underlying flow/action |
| `experienceProperties` | No | UI presentation (tagline, title, icon, form view, …) |

Activities are declared as `const` variables and returned from the lane's `activities` callback. An activity must be declared before it can be referenced in another activity's `wfa.playbook.run.After()`.

## Core Activity Definitions

All definitions are accessed via `ActivityDefinitions.Core.*`. Import `ActivityDefinitions` and `wfa` from `@servicenow/sdk/automation`.

### Interactive activities

| Definition | Purpose | Key inputs |
| `Instruction` | Display a message to the user | `message` , `wait` ( `'yes'` / `'no'` ) |
| `TwoStepInstruction` | Two-phase instruction (initial + done) | `initial_message` , `completed_message` , `skipped_message` |
| `RecordForm` | Present a record form for editing | `assigned_to` , `assignment_group` |
| `NewRecordForm` | Create a new record via form | `table` , `form_view` , `template_fields` |
| `AutocompletingRecordForm` | Record form that auto-completes on condition | `table` , `record` , `completion_condition` |
| `KnowledgeArticle` | Present a knowledge article | `title` , `knowledge_article` , `wait` |
| `ChecklistTask` | Present a checklist task to the user | `assigned_to` , `assignment_group` |

### Automation activities

| Definition | Purpose | Key inputs |
| `UpdateRecord` | Update field values on a record | `table_name` , `record` , `values` |
| `CreateNewRecord` | Create a new record | `table_name` , `values` |
| `NewRecordFormWithList` | Create multiple records in one step | `table_name` , `values` |
| `SendEmail` | Send email (automated) | `to` , `cc` , `bcc` , `subject` , `body` |
| `EmailForm` | Send email with user input | `to` , `cc` , `subject` , `body` , `wait` |
| `WaitForCondition` | Pause until a condition is met | `table` , `record` , `completion_condition` |
| `SetPlaybookOutputs` | Assign values to the playbook's declared outputs | `playbook_outputs` |
| `Placeholder` | Empty placeholder (no behavior) | — |

### Approval activities

| Definition | Purpose | Key inputs |
| `RequestManagerApproval` | Request approval from the requester's manager | `requester` , `record` |
| `RequestAdHocApproval` | Request approval from one or more named approvers | `approvers` , `record` |
| `AskForMultiLevelApproval` | Request approval through multiple sequential levels | `approval_levels` , `record` |

### Branching activities

| Definition | Purpose | Key inputs |
| `Decision` | Conditional branching with `match_first` or `match_all` | `type` , `branches` |

### Control flow activities

| Definition | Purpose | Key inputs |
| `GoBack` | Restart the playbook at an earlier activity, stage, or the start of the playbook | `target_type` , `go_back_to_target_activity` , `go_back_to_target_stage` |

### List activities

| Definition | Purpose | Key inputs |
| `RecordList` | Display a list of records to the user | `assignment_group` , `assigned_to` , `wait` |

Each activity definition has one backing flow or action (never both) and one activity type. The two pieces drive different parts of the activity's surface:

- The flow / action determines which inputs (and outputs) exist; the definition's `inputDisplayPreferences` filter which of those are settable.

- The activity type (e.g., `Core.List`, `Core.Decision`, `Core.Form`) determines which experience properties exist; the definition's `experienceDisplayPreferences` filter which of those are settable.

Two definitions sharing the same activity type can expose different experience properties (different filters), and two definitions sharing the same backing flow/action can expose different inputs. See the definition source under `src/api/playbook/built-ins/activity-definitions/` for the exact backing flow/action, activity type, and filters applied to each built-in.

## Reading a Built-In Activity Definition

Every entry under `ActivityDefinitions.Core.*` is assembled from up to three files. To fully understand what an activity
accepts and how it behaves, trace all three:

| File | Location | Declares |
| Definition | `src/api/playbook/built-ins/activity-definitions/<name>.now.ts` | The `ActivityDefinition({...})` call — identity, which flow/action and activity type back it, and which of their fields are author-facing |
| Backing flow/action | `src/api/playbook/built-ins/backing-flows/<name>.now.ts` or `backing-actions/<name>.now.ts` | The `Subflow({...})` / `Action({...})` behind `flow` / `action` — the real `inputs` / `outputs` schema |
| Activity type | `src/api/playbook/built-ins/activity-types/<name>.now.ts` | The `ActivityType({...})` behind `activityType` — the real `experienceProperties` schema |

### Definition-level properties

Every field on an `ActivityDefinition({...})` call, using `RecordForm`'s definition as a worked example:

```
export const RecordForm = ActivityDefinition({
    $id: 'c9839e38b701311004c164fdde11a904',
    label: 'Record Form',
    flow: manualActivity,
    activityType: ActivityTypes.Core.Record,
    enableAiAgent: 'on',
    aiAgentObjective: '...',
    aiAgentRunAs: 'playbook_user',
    aiAgentExecutionMode: 'on',
    aiAgentFieldDisplayPreferences: { enable_ai_agent: 'all', /* ... */ },
    inputDisplayPreferences: { assigned_to: 'standard', assignment_group: 'standard' },
    experienceDisplayPreferences: { associated_table: 'all', /* ... */ },
    defaultExperienceProperties: { description: '{{act.act_instance.description}}', /* ... */ },
})
```

- `$id` — sys_id of the real `sys_pd_activity_definition` platform record. Every built-in's `$id` matches an
existing platform record; this is how Fluent maps `ActivityDefinitions.Core.RecordForm` back to a real activity type
when transforming XML.

- `label` — display name shown in Playbook Designer.

- `flow` or `action` — exactly one is set, never both. Points at a `Subflow(...)` (from `backing-flows/`) or
`Action(...)` (from `backing-actions/`) that declares the activity's real `inputs`/`outputs` schema — see Tracing
the backing flow/action below.

- `activityType` — points at an `ActivityType(...)` (from `activity-types/`) that declares the real
`experienceProperties` schema — see Tracing the activity type below.

- `inputDisplayPreferences` — a `Record<inputName, 'all' | 'standard' | 'advanced'>` naming exactly which of the
backing flow/action's inputs an author is allowed to set. Anything not listed here is internal-only, even though it
exists on the backing flow/action. See Finding Input and Experience Property Names below.

- `experienceDisplayPreferences` — the same idea for `experienceProperties`, filtering the activity type's full
schema down to what's author-facing.

- `defaultInputs` / `defaultExperienceProperties` — values applied automatically when an author omits that
field. See Activity Definition Defaults below.

- `enableAiAgent`, `aiAgentObjective`, `aiAgentObjAdditionalDetail`, `aiAgentRunAs`, *
*`aiAgentExecutionMode`**, `aiAgentFieldDisplayPreferences` — only present on AI-capable built-ins (`RecordForm`,
`NewRecordForm`, `EmailForm`, `AutocompletingRecordForm`). See AI Agent Configuration below.

### Tracing the backing flow/action

Open the file under `backing-flows/` or `backing-actions/` referenced by `flow`/`action`. It's a `Subflow({...})` or
`Action({...})` (from `../helpers/flow`) with `inputs` and `outputs` objects, each field a `Column` call carrying a
`label`, a `sysId` (the platform variable's sys_id), and type-specific options. `RecordForm`'s backing flow (
`backing-flows/manual-activity.now.ts`):

```
export const manualActivity = Subflow({
    $id: 'cb18ceef1b230010affd0e55cc4bcbf2',
    name: 'Manual Activity',
    inputs: {
        assigned_to: ReferenceColumn({ label: 'Assigned To', sysId: '...', referenceTable: 'sys_user' }),
        assignment_group: ReferenceColumn({ label: 'Assignment Group', sysId: '...', referenceTable: 'sys_user_group' }),
        wait: ChoiceColumn({ label: 'Wait for user input', sysId: '...', choices: { yes: { label: 'Yes' }, no: { label: 'No' } } }),
    },
    outputs: {
        record: ReferenceColumn({ label: 'Record', referenceTable: 'sys_flow_data' }),
        automated: BooleanColumn({ label: 'Automated' }),
    },
})
```

This is the complete set of inputs the underlying flow supports — cross-reference against the definition's
`inputDisplayPreferences` to see which of these (`assigned_to`, `assignment_group`) are actually author-facing on
`RecordForm` (`wait` isn't listed, so it's internal-only for this activity even though the flow itself declares it).

### Tracing the activity type

Open the file under `activity-types/` referenced by `activityType`. It's an `ActivityType({...})` with an
`experienceProperties` object, same `Column`-based schema. An excerpt from `RecordForm`'s activity type (
`activity-types/record.now.ts`):

```
export const RecordActivityType = ActivityType({
    $id: 'e12af577871333003058d1a936cb0ba4',
    experienceProperties: {
        associated_table: TableNameColumn({ label: 'Associated Table', sysId: '...', columnType: 'string' }),
        associated_record: DocumentIdColumn({ label: 'Associated Record', sysId: '...', columnType: 'string', dependent: 'associated_table' }),
        record_fields: FieldListColumn({ label: 'Record Fields', sysId: '...', columnType: 'field_list', dependent: 'associated_table' }),
        // ...
    },
})
```

The `dependent` option marks a field that only makes sense once another field is set — e.g. `associated_record`/
`record_fields` are `dependent: 'associated_table'` because you can't pick a record or field list until the table is
known. Designer greys these out until their dependency is set; TypeScript typing and Fluent compilation enforces this
relationship for known tables, and will error if a record from the wrong table is provided.

Activity types are shared across definitions — several built-ins reference the same `ActivityType`, each filtering it
down to a different author-facing subset via their own `experienceDisplayPreferences`.

### Mandatory fields

Some backing flow/action inputs and activity type `experienceProperties` are marked `mandatory: true` on their
`Column` definition — e.g. New Record Form's `table` input. Fluent validates these at build time: the effective
value (your explicit `inputs`/`experienceProperties` value, or the activity definition's own `defaultInputs`/
`defaultExperienceProperties` when you omit the property entirely) must not be empty, or the build fails.

- An explicit value always wins over the definition default, even if that explicit value is itself empty — so
passing `table: ''` still errors even though omitting `table` entirely might resolve to a non-empty default on
activities that declare one (e.g. Checklist Task's `checklist_items` defaults to `'Item 1\nItem 2\nItem 3'`).

- A `wfa.playbook.dataPill(...)` value is never flagged as empty, since its concrete value is only known at runtime.

- The check runs against the backing flow/action's or activity type's full column schema, independent of
`inputDisplayPreferences`/`experienceDisplayPreferences`. Built-ins only set `mandatory: true` on columns that are
actually author-facing (not `display: false`/internal-only on the platform), so this shouldn't surface on a field
you can't set in the first place — see Finding Input and Experience Property Names below.

### Column type reference

Every `inputs`/`outputs`/`experienceProperties` field is one of these `Column` types (imported from
`@servicenow/sdk-core/db` in the backing flow/action/activity-type files — you won't import these yourself, but
recognizing them tells you the value format an activity's input/experience property expects):

| Column type | Required Fluent value format | Example |
| `StringColumn` / `HtmlColumn` | Plain string | `'incident'` |
| `BooleanColumn` | String `'yes'` or `'no'` (activity inputs) | `'yes'` |
| `ChoiceColumn` | One of the column's declared `choices` keys, as a string | `'yes'` |
| `ReferenceColumn` | sys_id string (or a data pill) of a record on `referenceTable` | `'62826bf0...'` |
| `DocumentIdColumn` | sys_id string (or a data pill) of a record on whatever table its `dependent` field resolves to | `wfa.playbook.dataPill(params.parentRecord)` |
| `TableNameColumn` | A table name string | `'incident'` |
| `FieldListColumn` | `FieldList<'table'>(['field1', 'field2'])` | `FieldList<'incident'>(['state', 'priority'])` |
| `TemplateValueColumn` | `TemplateValue({ field: value })` | `TemplateValue({ first_name: 'John' })` |

`FieldList` and `TemplateValue` are available globally in `.now.ts` files — do not import them.

For `TemplateValueColumn` inputs such as `values`, the field names inside `TemplateValue({...})` are database column
names from the table specified in that activity's `table` or `table_name` input. Fluent does not enforce this
relationship automatically — the field names must match the target table.

## Finding Input and Experience Property Names

Before setting any input or experience property value, check the definition file for the activity under `src/api/playbook/built-ins/activity-definitions/`. Each file declares `inputDisplayPreferences` and `experienceDisplayPreferences` — these are the authoritative lists of what the activity accepts. Do not infer input or experience property names from other activities; definitions share backing flows but expose different fields.

### Input names vary by definition

Some inputs share the same concept but use different names depending on the activity:

- `table_name` — used by `UpdateRecord`, `CreateNewRecord`, `NewRecordFormWithList`

- `table` — used by `NewRecordForm`, `AutocompletingRecordForm`, `WaitForCondition`

Always check the definition rather than assuming the name matches a similar activity.

Each input and experience property has a column type declared in the backing flow, action, or activity type file — see *
Column type reference* in Reading a Built-In Activity Definition above for the full list of column types and the
value format each expects.

## Examples

### Instruction

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

const welcome = wfa.playbook.activity(
    ActivityDefinitions.Core.Instruction,
    {
        $id: Now.ID['act_welcome'],
        label: 'Welcome',
        order: 1,
        startRule: wfa.playbook.run.Immediately(),
        restartRule: 'RUN_ONLY_ONCE',
    },
    {
        message: 'Welcome! Please review the details below.',
        wait: 'yes',
    },
    {
        tagline: 'Step 1',
        title: 'Welcome',
        description: 'Follow the instructions to complete this task.',
    },
)
```

Set `wait: 'yes'` when the playbook should pause for user acknowledgment; `'no'` for purely informational steps.

### RecordForm

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

declare const welcome: any

const review = wfa.playbook.activity(
    ActivityDefinitions.Core.RecordForm,
    {
        $id: Now.ID['act_review'],
        label: 'Review Record',
        order: 2,
        startRule: wfa.playbook.run.After(welcome),
        restartRule: 'RUN_ONLY_ONCE',
    },
    {
        assigned_to: '62826bf03710200044e0bfc8bcbe5df1',
    },
    {
        tagline: 'Step 2',
        title: 'Record Form',
        description: 'Update the record details below.',
        form_view: 'default',
        show_sla: false,
        show_checklist: true,
    },
)
```

### UpdateRecord

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

declare const params: any

const acknowledge = wfa.playbook.activity(
    ActivityDefinitions.Core.UpdateRecord,
    {
        $id: Now.ID['act_acknowledge'],
        label: 'Acknowledge Incident',
        order: 1,
        startRule: wfa.playbook.run.Immediately(),
        restartRule: 'RUN_ONLY_ONCE',
    },
    {
        table_name: 'incident',
        record: wfa.playbook.dataPill(params.parentRecord),
        values: TemplateValue({
            state: '2',
            work_notes: 'Acknowledged via playbook.',
        }),
    },
    {
        tagline: 'Step 1',
        title: 'Acknowledge',
        description: '<p>Incident will move to In Progress state.</p>',
    },
)
```

### CreateNewRecord

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

const createChild = wfa.playbook.activity(
    ActivityDefinitions.Core.CreateNewRecord,
    {
        $id: Now.ID['act_create_child'],
        label: 'Create Child Incident',
        order: 1,
        startRule: wfa.playbook.run.Immediately(),
        restartRule: 'RUN_ONLY_ONCE',
    },
    {
        table_name: 'incident',
        values: TemplateValue({
            short_description: 'Child incident created by playbook.',
            priority: '2',
        }),
    },
)
```

### NewRecordFormWithList

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

const createIncident = wfa.playbook.activity(
     ActivityDefinitions.Core.NewRecordFormWithList,
     {
        $id: Now.ID['create_incident'],
        label: 'Create Incident',
        order: 1,
        startRule: wfa.playbook.run.Immediately(),
        restartRule: 'RUN_ONLY_ONCE',
     },
     {},
     {
        table: 'incident',
     },
)
```

### SetPlaybookOutputs

`SetPlaybookOutputs` writes values into the playbook's declared outputs so downstream consumers can read them via `pd.outputs.<name>` pills. Unlike other activities, its input schema is dynamic: the single `playbook_outputs` input is a `TemplateValue` whose keys are the output element names declared in the playbook's `outputs` (see the playbook config `outputs` in `playbook-api`). Values may be literals or data pills.

```
import { PlaybookDefinition, wfa, ActivityDefinitions } from '@servicenow/sdk/automation'
import { StringColumn } from '@servicenow/sdk/core'

PlaybookDefinition(
    {
        $id: Now.ID['pb_set_outputs'],
        label: 'Set Outputs Example',
        name: 'set_outputs_example',
        parentTable: 'incident',
        outputs: {
            resolutionNote: StringColumn({ label: 'Resolution Note', maxLength: 100, order: 100 }),
            resolvedBy: StringColumn({ label: 'Resolved By', maxLength: 100, order: 200 }),
        },
    },
    { triggers: [] },
    {
        lanes: (params) => {
            const lane_0 = wfa.playbook.lane({
                config: {
                    $id: Now.ID['set_outputs_lane'],
                    label: 'Main Lane',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => {
                    const set_outputs = wfa.playbook.activity(
                        ActivityDefinitions.Core.SetPlaybookOutputs,
                        {
                            $id: Now.ID['act_set_outputs'],
                            label: 'Set Playbook Outputs',
                            order: 1,
                            startRule: wfa.playbook.run.Immediately(),
                            restartRule: 'RUN_ONLY_ONCE',
                        },
                        {
                            // Keys MUST be output element names declared in `outputs` above.
                            playbook_outputs: TemplateValue({
                                resolutionNote: 'Resolved automatically by playbook.', // literal
                                resolvedBy: wfa.playbook.dataPill(params.parentRecord.assigned_to), // data pill
                            }),
                        },
                    )
                    return { set_outputs: set_outputs }
                },
            })
            return { lane_0: lane_0 }
        },
    },
)
```

Key points:

- Keys are output element names, not labels, and are case-sensitive. `resolutionNote` (the `outputs` key) matches; `ResolutionNote` would not.

- Setting an undeclared output is a build error. A `playbook_outputs` key that is not declared in the playbook's `outputs` fails the build with `'<key>' is not a declared output of this playbook`. (Intellisense cannot catch this — `TemplateValue` accepts any object — so it is enforced at build time.)

- You never set the dependent table. The backing subflow's second input, `playbook_outputs_var_table_name`, is auto-derived from the host playbook and is intentionally not part of the DSL.

- `outputs` does not require a `parentTable`. Unlike `inputs` (which need a parent table for the `parentRecord` mapper), a standalone playbook with no `parentTable` can still declare and write outputs.

### Decision (in-lane)

A Decision activity routes execution to branches. Downstream activities use `wfa.playbook.run.After(decision.branches.<id>)` to start when a specific branch matches.

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

declare const intake_form: any

const router = wfa.playbook.activity(
    ActivityDefinitions.Core.Decision,
    {
        $id: Now.ID['act_router'],
        label: 'Route by Assignment',
        order: 2,
        startRule: wfa.playbook.run.After(intake_form),
        restartRule: 'RUN_ONLY_ONCE',
    },
    {
        type: 'match_first',
        branches: [
            {
                id: 'has_assignee',
                label: 'Has Assignee',
                condition: `${wfa.playbook.dataPill(intake_form.outputs.record.assigned_to)}ISNOTEMPTY`,
            },
            {
                id: 'unassigned',
                label: 'Unassigned',
                condition: `${wfa.playbook.dataPill(intake_form.outputs.record.assigned_to)}ISEMPTY`,
            },
            { id: 'else', label: 'Else' },
        ] as const,
    },
)

const escalate = wfa.playbook.activity(
    ActivityDefinitions.Core.Instruction,
    {
        $id: Now.ID['act_escalate'],
        label: 'Escalate',
        order: 3,
        startRule: wfa.playbook.run.After(router.branches.unassigned),
        restartRule: 'RUN_ONLY_ONCE',
    },
    { message: 'No assignee — routing to on-call.' },
)
```

Branch structure:

| Property | Required | Description |
| `id` | Yes | Unique branch identifier, used in `decision.branches.<id>` |
| `label` | Yes | Display name |
| `condition` | No | Encoded query with data pills (omit for the `else` branch) |
| `isIdealPath` | No | Marks this branch as the preferred one at this decision (defaults to `false` ); requires Process Automation Designer 29.x+, see below |

Branch display order is taken from the array position — the first branch in the `branches` array has the lowest order, the last has the highest. There is no `order` field on individual branches.

Match modes:

- `'match_first'` — only the first matching branch executes (if/else if)

- `'match_all'` — all matching branches execute in parallel (multiple if statements)

Ideal path / golden path: setting `isIdealPath: true` marks a branch as the preferred route through its decision. Collectively, the ideal branches across every decision form the playbook's golden path — the end-to-end route Playbook Designer highlights on both its board and diagram canvases, and is intended to be the route the playbook follows at runtime.

Requires the Process Automation Designer (`sn_pa_designer`) store app at version 29.6.4 or later — on
earlier versions the flag is still written to the branch record, but Playbook Designer has no golden
path UI to render it and it has no effect at runtime; the SDK doesn't validate the installed version.

Two rules, both build-time errors if broken:

- Because only one branch of a `match_first` decision ever runs, `match_first` accepts at most one ideal branch; `match_all` accepts several.

- `else` and the conditional branches are mutually exclusive regardless of decision type: the golden path leaves a decision either through one or more conditional branches, or through `else` — never both. So `else` may be the ideal branch, just not at the same time as a conditional one.

```
{
    type: 'match_first',
    branches: [
        { id: 'has_assignee', label: 'Has Assignee', condition: '...', isIdealPath: true },
        { id: 'unassigned', label: 'Unassigned', condition: '...' },
        { id: 'else', label: 'Else' },
    ] as const,
}
```

The `else` branch has no `condition` and must be last. `as const` on the branches array is not required (the Decision overload infers literal branch IDs automatically), but is used by convention throughout the codebase — see `playbook-anti-patterns-guide`.

See `playbook-patterns-guide` for full `match_first`, `match_all`, and chained-decision examples.

### Go Back

`GoBack` restarts the playbook at an earlier activity, an earlier stage (lane), or the start of the playbook. It is
the only built-in that can create a real loop in a playbook — see `playbook-patterns-guide#retry-loop-with-go-back`
for why the author is responsible for making sure the loop can actually break out at runtime. Go Back is only valid as the terminal activity
of a `match_first` decision branch — never as a normal lane activity — and is placed the same way whether the
enclosing decision is in-lane or stage-level.

Requires the Process Automation Designer (`sn_pa_designer`) store app at version 29.3.0 or later — the
`sys_pd_activity_definition` record backing `ActivityDefinitions.Core.GoBack` doesn't exist on earlier versions;
the SDK doesn't validate the installed version.

`target_type` selects the jump target: `'go_back_to_target_activity'`, `'go_back_to_target_stage'`, or
`'start_of_playbook'` (no target field needed for the last one). Author
`go_back_to_target_activity`/`go_back_to_target_stage` as a raw reference to the target's own lane/activity
variable — the same style used by `Run.After()` (e.g. `go_back_to_target_activity: intake.review`). `GoBack`
has its own `ActivityFunction` overload so this form type-checks cleanly; see `playbook-api#go-back-activity`
for details.

In-lane placement — the Go Back is the last activity of a branch inside a lane, retrying an earlier activity in
the same lane:

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

wfa.playbook.lane({
    config: {
        $id: Now.ID['lane_intake'],
        label: 'Intake',
        order: 1,
        startRule: wfa.playbook.run.Immediately(),
        restartRule: 'RUN_ONLY_ONCE',
    },
    activities: () => {
        const intake_review = wfa.playbook.activity(
            ActivityDefinitions.Core.RecordForm,
            {
                $id: Now.ID['act_intake_review'],
                label: 'Intake Review',
                order: 1,
                startRule: wfa.playbook.run.Immediately(),
                restartRule: 'RUN_ONLY_ONCE',
            },
            { assigned_to: '' },
        )

        const rework_decision = wfa.playbook.activity(
            ActivityDefinitions.Core.Decision,
            {
                $id: Now.ID['rework_decision'],
                label: 'Needs Rework?',
                order: 2,
                startRule: wfa.playbook.run.After(intake_review),
                restartRule: 'RUN_ONLY_ONCE',
            },
            {
                type: 'match_first',
                branches: [
                    {
                        id: 'needs_rework',
                        label: 'Needs Rework',
                        condition: `${wfa.playbook.dataPill(intake_review.outputs.record.state)}=NEEDS_REWORK`,
                    },
                    {id: 'else', label: 'Else'},
                ],
            },
        )

        const retry_review = wfa.playbook.activity(
            ActivityDefinitions.Core.GoBack,
            {
                $id: Now.ID['act_retry_review'],
                label: 'Retry Intake Review',
                order: 3,
                startRule: wfa.playbook.run.After(rework_decision.branches.needs_rework),
                restartRule: 'RUN_ALWAYS',
            },
            {
                target_type: 'go_back_to_target_activity',
                go_back_to_target_activity: intake_review,
            },
        )

        return { intake_review: intake_review, rework_decision: rework_decision, retry_review: retry_review }
    }
})
```

Stage-level placement — a branch of a stage-level Decision runs a stage-level Go Back (an activity declared
between lanes, in no lane at all) that restarts an earlier stage:

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

lanes: (params) => {
    const intake = wfa.playbook.lane({
        config: {
            $id: Now.ID['lane_intake'],
            label: 'Intake',
            order: 1,
            startRule: wfa.playbook.run.Immediately(),
            restartRule: 'RUN_ONLY_ONCE',
        },
        activities: () => {
            const intake_review = wfa.playbook.activity(
                ActivityDefinitions.Core.RecordForm,
                {
                    $id: Now.ID['act_intake_review'],
                    label: 'Intake Review',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                { assigned_to: '' },
            )
            return { intake_review: intake_review }
        },
    })

    const rework_decision = wfa.playbook.activity(
        ActivityDefinitions.Core.Decision,
        {
            $id: Now.ID['rework_decision'],
            label: 'Needs Rework?',
            order: 2,
            startRule: wfa.playbook.run.After(intake),
            restartRule: 'RUN_ONLY_ONCE',
        },
        {
            type: 'match_first',
            branches: [
                {
                    id: 'needs_rework',
                    label: 'Needs Rework',
                    condition: `${wfa.playbook.dataPill(intake.intake_review.outputs.record.state)}=NEEDS_REWORK`,
                },
                {id: 'else', label: 'Else'},
            ],
        },
    )

    const restart_intake = wfa.playbook.activity(
        ActivityDefinitions.Core.GoBack,
        {
            $id: Now.ID['act_restart_intake'],
            label: 'Restart Intake',
            order: 3,
            startRule: wfa.playbook.run.After(rework_decision.branches.needs_rework),
            restartRule: 'RUN_ALWAYS',
        },
        {
            target_type: 'go_back_to_target_stage',
            go_back_to_target_stage: intake,
        },
    )

    return { intake: intake, rework_decision: rework_decision, restart_intake: restart_intake }
}
```

The Go Back must reach its decision through its own `Run.After` chain, within its own scope. There can be other
activities between the decision branch and the Go Back activity, chained by startRule, but they must all be in the same
stage (or stage-less if it is a stage-level decision). A Go Back cannot be the first activity of a stage that a
branch leads into: being inside that stage does not place it in the branch. Put the Go Back on the branch directly, as
above.

Validation rules. Rules 1–8 below are build errors; the playbook fails to build until fixed. Rule 9 is a
build warning — the playbook still builds, but the target (or the playbook itself, for
`start_of_playbook`) silently won't re-run on the jump back unless fixed.

- Must be inside a decision branch. Bad: Go Back placed as a plain lane activity outside any decision, or as
the first activity of a stage that a stage-level decision branch leads into. Good: Go Back is the last activity of a
`match_first` decision branch, reached through its own `Run.After` chain in its own scope (`else` branches are allowed).

- Target must resolve to a real, in-scope preceding activity/stage. Bad: no target field set, or one that
doesn't resolve to an earlier activity/stage in this playbook. An optional activity cannot be targeted.
Good: `go_back_to_target_activity: intake_review` referencing an activity declared earlier in the playbook.
If the playbook sets `evaluateVariantChildrenAfter` (see `playbook-api#wfaplaybookvariant`) and the Go Back's
enclosing decision runs after that evaluation point, the target must also run after it — a target that's
otherwise a valid preceding activity/stage but sits before the evaluation point gets the more specific "Select
a target after the variant evaluation point" error instead. Good: the target also runs after the evaluation
point.

- The enclosing decision must be `match_first`. Bad: the decision containing the Go Back branch uses
`type: 'match_all'`. Good: `type: 'match_first'`.

- At most one Go Back per branch. Bad: two Go Back activities chained one after another in the same branch.
Good: exactly one Go Back, as the branch's terminal activity.

- No parallel/`match_all` ancestor within the enclosing branch. Bad: the path from the branch start to the Go
Back forks into parallel activities upstream of it. Good: a single linear path from the branch start to the Go
Back.

- At least one branch of the enclosing decision must not dead-end in Go Back. Bad: every branch (including
`else`) ends in a Go Back, so the decision can never make forward progress. Good: at least one branch (often
`else`) proceeds to a normal downstream activity or lane.

- Must be the last activity in its branch. Bad: another activity is set to run after the Go Back, e.g.
`wfa.playbook.run.After(retry_review)`. Good: nothing depends on the Go Back — it has no successors.

- Target activity must not itself be a Go Back or the enclosing decision. Bad: `go_back_to_target_activity` points
at another Go Back activity or the decision whose branch the Go Back is immediately on. Good: it points at a normal
activity.

- (Warning) Target's `restartRule` should be `'RUN_ALWAYS'`. Bad: the target activity/stage keeps the default
`restartRule: 'RUN_ONLY_ONCE'`, so it's skipped instead of re-running when the playbook jumps back to it. Good:
`restartRule: 'RUN_ALWAYS'` on the target — or, for `target_type: 'start_of_playbook'`,
`restartable: 'RESTARTABLE_TRUE'` on the playbook config.

## Experience Properties

The fourth `wfa.playbook.activity` argument controls UI presentation. Experience properties are per-definition — each activity definition declares its own `experienceDisplayPreferences` in `src/api/playbook/built-ins/activity-definitions/`, and the available property set (and naming) varies. Below are properties commonly seen across interactive activities, but you should always check the specific definition to know exactly what's accepted:

| Property | Type | Typical use |
| `tagline` | string | Short label above the title |
| `title` | string | Main heading |
| `description` | string | Body text (supports HTML) |
| `icon` | string | Icon name (e.g., `'info-circle-outline'` ) |
| `is_automated` | boolean | Mark as automated (no user interaction) |

For activity-specific properties (form views, record fields, SLA display, list configuration, attachment options, pending-state titles, etc.), open the corresponding definition file and read its `experienceDisplayPreferences`.

Use `wfa.playbook.currentActivity.label` and `.description` inside experience properties to reference the activity's own label/description without triggering a "used before declaration" TypeScript error:

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

const myActivity = wfa.playbook.activity(
    ActivityDefinitions.Core.RecordForm,
    { $id: Now.ID['my_form'], label: 'Review Incident', order: 1, startRule: wfa.playbook.run.Immediately(), restartRule: 'RUN_ONLY_ONCE' },
    { /* inputs */ },
    {
        title: wfa.playbook.dataPill(wfa.playbook.currentActivity.label),
        description: wfa.playbook.dataPill(wfa.playbook.currentActivity.description),
    },
)
```

Only `label` and `description` are valid on `wfa.playbook.currentActivity` — any other property access produces a diagnostic error.

## Data Pills in Activities

Pass runtime values between activities with `wfa.playbook.dataPill()`. Pills can dot-walk through reference fields:

```
import { wfa } from '@servicenow/sdk/automation'

declare const intake_form: any
declare const params: any

wfa.playbook.dataPill(intake_form.outputs.record.assigned_to)
wfa.playbook.dataPill(intake_form.outputs.record.assignment_group)
wfa.playbook.dataPill(params.parentRecord.priority)
wfa.playbook.dataPill(params.inputs.record.short_description)
```

Pill source summary:

| Source | Example |
| Playbook inputs | `wfa.playbook.dataPill(params.inputs.record.number)` |
| Parent record | `wfa.playbook.dataPill(params.parentRecord.short_description)` |
| Activity outputs (same lane) | `wfa.playbook.dataPill(validate.outputs.record.state)` |
| Activity outputs (cross-lane) | `wfa.playbook.dataPill(intake.enrich.outputs.support_tier)` |
| Activity state | `wfa.playbook.dataPill(validate.state)` |
| Activity sys_id | `wfa.playbook.dataPill(validate.sysId)` |
| Current activity label / description | `wfa.playbook.dataPill(wfa.playbook.currentActivity.label)` |

`wfa.playbook.dataPill()` automatically picks the correct format for the target field (wrapped `{{...}}` for inputs and experience properties; unwrapped for `conditionToRun` and Decision branch conditions). See `playbook-api` for the full pill validation matrix listing which sources are valid in which fields.

### Same-lane and cross-lane output references

Activity outputs are accessed through variables, not through `params`:

- Same-lane: use local variables declared within the same `activities` callback.

- Cross-lane: use the lane variable returned from the `lanes` callback, then dot-walk to the activity and its outputs.

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

const body = {
    lanes: (params: any) => {
        const intake = wfa.playbook.lane({
            config: {
                $id: Now.ID['lane_intake'],
                label: 'Intake',
                order: 1,
                startRule: wfa.playbook.run.Immediately(),
                restartRule: 'RUN_ONLY_ONCE',
            },
            activities: () => {
                const review = wfa.playbook.activity(
                    ActivityDefinitions.Core.RecordForm,
                    { $id: Now.ID['act_review'], label: 'Review', order: 1, startRule: wfa.playbook.run.Immediately(), restartRule: 'RUN_ONLY_ONCE' },
                    { /* inputs */ },
                )
                return { review: review }
            },
        })

        const triage = wfa.playbook.lane({
            config: {
                $id: Now.ID['lane_triage'],
                label: 'Triage',
                order: 2,
                startRule: wfa.playbook.run.After(intake),
                restartRule: 'RUN_ONLY_ONCE',
            },
            activities: () => {
                const categorize = wfa.playbook.activity(
                    ActivityDefinitions.Core.UpdateRecord,
                    { $id: Now.ID['act_categorize'], label: 'Categorize', order: 1, startRule: wfa.playbook.run.Immediately(), restartRule: 'RUN_ONLY_ONCE' },
                    {
                        // Cross-lane: intake lane variable → review activity → outputs
                        record: wfa.playbook.dataPill(intake.review.outputs.record),
                    },
                )
                return { categorize: categorize }
            },
        })

        return { intake: intake, triage: triage }
    },
}
```

Cross-lane activity references in `startRule` are not supported — use a lane-level dependency on `config.startRule` instead. See `playbook-guide` for the full explanation.

## Stage-Level Decisions

A Decision activity placed at the `lanes` body level (not inside any lane) routes execution between lanes. Each downstream lane uses `wfa.playbook.run.After(decision.branches.<id>)` to start when its branch matches.

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

const body = {
    lanes: () => {
        const triage = wfa.playbook.lane({
            config: {
                $id: Now.ID['sd_triage'],
                label: 'Triage',
                order: 1,
                startRule: wfa.playbook.run.Immediately(),
                restartRule: 'RUN_ONLY_ONCE',
            },
            activities: () => {
                const review = wfa.playbook.activity(
                    ActivityDefinitions.Core.RecordForm,
                    {
                        $id: Now.ID['act_review'],
                        label: 'Review Incident',
                        order: 1,
                        startRule: wfa.playbook.run.Immediately(),
                        restartRule: 'RUN_ONLY_ONCE',
                    },
                    { assigned_to: '' },
                )
                return { review: review }
            },
        })

        const decision = wfa.playbook.activity(
            ActivityDefinitions.Core.Decision,
            {
                $id: Now.ID['sd_decision'],
                label: 'Route by Assignment',
                order: 2,
                startRule: wfa.playbook.run.After(triage),
                restartRule: 'RUN_ONLY_ONCE',
            },
            {
                type: 'match_first',
                branches: [
                    {
                        id: 'unassigned',
                        label: 'Unassigned',
                        condition: `${wfa.playbook.dataPill(triage.review.outputs.record.assigned_to)}ISEMPTY`,
                    },
                    {
                        id: 'has_group',
                        label: 'Has Group',
                        condition: `${wfa.playbook.dataPill(triage.review.outputs.record.assignment_group)}ISNOTEMPTY`,
                    },
                    { id: 'else', label: 'Else' },
                ] as const,
            },
        )

        const escalation = wfa.playbook.lane({
            config: {
                $id: Now.ID['sd_escalation'],
                label: 'Escalation',
                order: 3,
                startRule: wfa.playbook.run.After(decision.branches.unassigned),
                restartRule: 'RUN_ONLY_ONCE',
            },
            activities: () => {
                const page = wfa.playbook.activity(
                    ActivityDefinitions.Core.Instruction,
                    {
                        $id: Now.ID['act_page_oncall'],
                        label: 'Page On-Call',
                        order: 1,
                        startRule: wfa.playbook.run.Immediately(),
                        restartRule: 'RUN_ONLY_ONCE',
                    },
                    { message: 'Unassigned — paging on-call engineer.' },
                )
                return { page: page }
            },
        })

        return { triage: triage, decision: decision, escalation: escalation }
    },
}
```

Key differences from in-lane decisions:

- Return the decision in the lanes return object alongside the lanes.

- Use the `order` field on the decision config (consistent with lane `order`).

## Start With Delay

Like lanes, a regular activity's `ActivityConfig` accepts an optional `startWithDelay` to delay the activity's start after its `startRule` is satisfied:

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

const remindLater = wfa.playbook.activity(
    ActivityDefinitions.Core.Instruction,
    {
        $id: Now.ID['act_remind_todo'],
        label: 'Check Your To-Do List',
        order: 1,
        startRule: wfa.playbook.run.Immediately(),
        restartRule: 'RUN_ONLY_ONCE',
        startWithDelay: {
            type: 'explicit',
            duration: Duration({ hours: 2 }),
            timerSchedule: '30b99b3d93a0220050bef157b67ffb2e',
        },
    },
    { message: 'Reminder: check your to-do list.' },
)
```

`startWithDelay` supports the same `'explicit'`, `'relative'`, and `'percentage'` delay types on activities as it does on lanes — including the optional `timerSchedule` (a `cmn_schedule` sys_id or `Record<'cmn_schedule'>` reference that restricts the delay to the schedule's active hours). See "Start With Delay" in `playbook-lanes-guide` for the full type breakdown and examples, and `startWithDelay` in `playbook-api` for the type signature.

Note that optional activities do not accept `startWithDelay` — see the config comparison table below.

## Optional Activities

An activity can be marked optional: it only runs if a user triggers it during a running playbook, and skipping it doesn't block the rest of the playbook. Use `wfa.playbook.run.Manually()` as the `startRule` instead of `Immediately()` or `After(...)`.

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

const escalateManually = wfa.playbook.activity(
    ActivityDefinitions.Core.Instruction,
    {
        $id: Now.ID['act_manual_escalate'],
        label: 'Escalate (Optional)',
        startRule: wfa.playbook.run.Manually(),
        restartRule: 'RUN_ONLY_ONCE',
    },
    { message: 'Escalate this case if needed.' },
)
```

An optional activity's config is narrower than a regular `ActivityConfig`:

| Field | Regular activity | Optional activity |
| `order` | Required | Not accepted — an optional activity has no fixed position |
| `conditionToRun` | Optional | Not accepted — a person decides whether it runs, not a condition |
| `restartRule` | Any `RestartRule` | Must be `'RUN_ONLY_ONCE'` |
| `startRule` | `Immediately()` / `After(...)` | `Manually()` only |
| `startWithDelay` | Optional | Not accepted — Playbook Designer hides start-delay configuration for optional activities |
| `variant` | Optional | Not accepted — optional activities are not variant-scopable, only supported at the base playbook level |
| `variantOverrides` | Optional | Not accepted — see Variant Overrides and Variant-Only Activities below |

Declare it inside a lane for a lane-scoped optional activity (available only while that lane is active), or at the `lanes` body root (like a stage-level Decision) for a playbook-wide/global optional activity, available for the whole run:

```
import { wfa, ActivityDefinitions } from '@servicenow/sdk/automation'

const body = {
    lanes: () => {
        // Global — available for the entire playbook run.
        const globalEscalate = wfa.playbook.activity(ActivityDefinitions.Core.Instruction, {
            $id: Now.ID['act_global_escalate'],
            label: 'Escalate (Optional)',
            startRule: wfa.playbook.run.Manually(),
            restartRule: 'RUN_ONLY_ONCE',
        })

        const triage = wfa.playbook.lane({
            config: { $id: Now.ID['triage'], label: 'Triage', order: 1, startRule: wfa.playbook.run.Immediately(), restartRule: 'RUN_ONLY_ONCE' },
            activities: () => {
                // Lane-scoped — available only while the Triage lane is active.
                const requestInfo = wfa.playbook.activity(ActivityDefinitions.Core.Instruction, {
                    $id: Now.ID['act_request_info'],
                    label: 'Request More Info (Optional)',
                    startRule: wfa.playbook.run.Manually(),
                    restartRule: 'RUN_ONLY_ONCE',
                })
                return { requestInfo: requestInfo }
            },
        })

        return { globalEscalate: globalEscalate, triage: triage }
    },
}
```

An optional activity can't be depended on. Since it may never run, nothing may wait on it or reference it in a pill. Both are compile errors:

```
// Compile error — an optional activity may never run, so nothing can wait on it.
startRule: wfa.playbook.run.After(globalEscalate)

// Compile error — an optional activity has no referenceable fields.
message: wfa.playbook.dataPill(globalEscalate.outputs.record.state)
```

## Action Overrides

An activity can override the experience's Declarative Actions that appear at runtime on its Playbook Card, with a specific array of actions, along with their label and display order.

Pass `actionOverrides` on the activity's config — an array of `ActionOverride` objects:

```
wfa.playbook.activity(
    ActivityDefinitions.Core.Instruction,
    {
        $id: Now.ID['act_final_step'],
        label: 'Final Step',
        order: 2,
        startRule: wfa.playbook.run.After(intake),
        restartRule: 'RUN_ONLY_ONCE',
        actionOverrides: [
            {
                actionAssignment: '17218958ffb21010834953bd6338f138', // "Mark Complete"
                label: 'Finish this playbook',
                displayOrder: 1,
            },
        ],
    },
    { message: 'Complete the remaining tasks.' },
)
```

| Property | Type | Description |
| `actionAssignment` | `string | Record<'sys_declarative_action_assignment'>` | The declarative action assignment whose button to override, as a raw sys_id or a `Record<'sys_declarative_action_assignment'>` reference |
| `label` | `string` | Overridden button label |
| `displayOrder` | `number` | Overridden display order among the activity's action buttons |

For other buttons, pass either the raw sys_id or a `Record<'sys_declarative_action_assignment'>` reference — those rows are app/experience-specific platform configuration, not authored via Fluent. Ensure that the Declarative Actions are assigned to "Playbook Card", using the filter `model=ca57d12e730333004a905ee515f6a7b2`

Validation:

- Each override must resolve to an `actionAssignment` sys_id. An entry whose `actionAssignment` is missing or an empty string can't map to a `sys_declarative_action_assignment` row, so it is skipped during the build and the SDK emits a warning identifying the affected override (by its `label`) rather than dropping it silently.

- Duplicate `actionAssignment` values are warned — the platform coalesce key is `[activity, action_assignment]`, so duplicate entries would silently merge into one record. The SDK flags this so the author can see the collision.

- Duplicate `displayOrder` values are warned — two overrides with the same display order will have ambiguous button ordering at runtime.

See `ActionOverride` in `playbook-api` for the full type definition.

## Variant Overrides and Variant-Only Activities

An activity can behave differently per playbook variant (see `playbook-api#wfaplaybookvariant` for variants themselves), in two ways:

- `variantOverrides` — override this activity's `startRule` and/or `order` when a specific variant is selected, without changing its base behavior for the base playbook or other variants.

- `variant` — scope the activity to exist only within a single variant (a variant-only activity); it's omitted entirely from any other variant or the base playbook.

The two are mutually exclusive on the same activity — TypeScript rejects setting both.

```
// Inside a lane's `activities` callback — `params.variants.<name>` references a
// variant declared in the playbook's 2nd-argument `variants` callback directly, no
// wrapping call needed.
const activity_review = wfa.playbook.activity(ActivityDefinitions.Core.Placeholder, {
    $id: Now.ID['act_review'],
    label: 'Review',
    order: 2,
    startRule: wfa.playbook.run.Immediately(),
    restartRule: 'RUN_ONLY_ONCE',
    // Only changes startRule/order when the VIP variant is selected; behaves normally otherwise.
    variantOverrides: [{ variant: params.variants.variant_vip, order: 1 }],
})

// An override's startRule isn't limited to Run.Immediately() — it can reference a
// real predecessor via Run.After(), just like a base activity's startRule.
const activity_close = wfa.playbook.activity(ActivityDefinitions.Core.Placeholder, {
    $id: Now.ID['act_close'],
    label: 'Close',
    order: 3,
    startRule: wfa.playbook.run.After(activity_review),
    restartRule: 'RUN_ONLY_ONCE',
    // For the VIP variant, wait on activity_vip_greeting instead of activity_review.
    variantOverrides: [{ variant: params.variants.variant_vip, startRule: wfa.playbook.run.After(activity_vip_greeting) }],
})

const activity_vip_greeting = wfa.playbook.activity(ActivityDefinitions.Core.Placeholder, {
    $id: Now.ID['act_vip_greeting'],
    label: 'VIP Greeting',
    order: 1,
    startRule: wfa.playbook.run.Immediately(),
    restartRule: 'RUN_ONLY_ONCE',
    // Exists only when the VIP variant is selected; not present for other variants or the base playbook.
    variant: params.variants.variant_vip,
})
```

An override's `Run.After()` dependency can also reference an activity declared later in the same lane — a plain variable reference would violate declaration order, since that activity's `const` doesn't exist yet at this point in the file. Use `wfa.playbook.activityRef(Now.ID['<id>'])` instead (see `playbook-api#wfaplaybookactivityref`); it resolves by id, so declaration order doesn't matter. This also covers the case where the override direction reverses an existing base edge between the same two activities:

```
// Base: activity_close waits on activity_review (declared below). For the VIP
// variant, that's reversed — activity_review instead waits on activity_close.
// activity_close is declared later in this lane, so a plain `activity_close`
// reference here would be a forward reference to a not-yet-declared `const`.
const activity_review = wfa.playbook.activity(ActivityDefinitions.Core.Placeholder, {
    $id: Now.ID['act_review'],
    label: 'Review',
    order: 2,
    startRule: wfa.playbook.run.Immediately(),
    restartRule: 'RUN_ONLY_ONCE',
    variantOverrides: [
        {
            variant: params.variants.variant_vip,
            startRule: wfa.playbook.run.After(wfa.playbook.activityRef(Now.ID['act_close'])),
        },
    ],
})
const activity_close = wfa.playbook.activity(ActivityDefinitions.Core.Placeholder, {
    $id: Now.ID['act_close'],
    label: 'Close',
    order: 3,
    startRule: wfa.playbook.run.After(activity_review),
    restartRule: 'RUN_ONLY_ONCE',
    // Give activity_close its own override for the VIP variant, or it and
    // activity_review will deadlock on each other now that the edge is reversed.
})
```

Diagnostics:

| Rule | Level | Trigger |
| `variant` / `variantOverrides[].variant` isn't a variant reference | Error | The value isn't a `params.variants.<name>` reference at all (e.g. an unrelated reference like `params.parentRecord` , or a literal) |
| Undeclared variant reference | Error | `variant` or a `variantOverrides[].variant` references a `Now.ID` that doesn't resolve to a variant declared in this playbook's `variants` collection |
| `variant` and `variantOverrides` both set | TypeScript compile error, with a matching diagnostic for bypassed/untyped callers | An activity defines both fields at once — a variant-only activity's `variant` and per-variant `variantOverrides` are contradictory. `BaseActivityConfig` types the two fields as a discriminated union, so this is caught at the type level for normal Fluent authoring |
| Duplicate override | Error | Two entries in the same activity's `variantOverrides` target the same variant |
| No-op override | Warning | A `variantOverrides` entry sets neither `startRule` nor `order` — it has no effect |
| Variant-only activity not a guaranteed descendant of the evaluation point | Error | `evaluateVariantChildrenAfter` is set on the playbook config, and this variant-only activity isn't guaranteed (by the playbook's lane/activity `Run.After` ordering) to run after it — see `playbook-api#playbookconfig` |

Not available on optional (`Run.Manually()`) activities. `variantOverrides` has no fixed `order`/`startRule` to override on an optional activity, and `variant` is not variant-scopable on an optional activity — both are omitted from `ManualActivityConfig` entirely, and the diagnostics layer errors on either being set via a bypass. See Optional Activities above.

## Activity Definition Defaults

Each activity definition can contain a set of default values for inputs and experienceProperties. These default values can be found in the relevant activity definition file in `src/api/playbook/built-ins/activity-definitions/`, under the `defaultInputs` and `defaultExperienceProperties` properties. When a value is NOT provided in the activity call, the default value will be used if available. If a value is provided, it will take priority and the default will not be used. When a playbook is transformed into fluent, all its inputs and experienceProperties will be set in the activity call, so the default values will show up.

## AI Agent Configuration

The AI-agent fields on `ActivityConfig` (`enableAiAgent`, `aiAgentObjective`, `aiAgentObjAdditionalDetail`,
`aiAgentExecutionMode`, `aiAgentRunWithRoles`, `aiAgentSupportedActions`, `aiAgentRunAs`,
`conversationalAgents`) are only available on activity definitions that opt in. See `ActivityConfig` in
`playbook-api` for the field-by-field type overview — this section covers how to determine, for any given activity
definition, whether it supports AI agents, which of these fields it exposes, and how validation/inheritance behaves.

On the platform, AI agent configuration only takes effect when the `sn_genai_platform` store app is installed and
the `sn_pa_designer.enable_agentic_playbooks` system property is `true`. The Fluent SDK doesn't validate either of
these — the type-level rules and build-time behavior described in this section apply regardless of the target
instance's plugin/property state.

Every one of these fields other than `enableAiAgent` itself is only meaningful on an instance that also sets
`enableAiAgent: true`. The SDK doesn't enforce this with a build error/warning — a field can be set while
`enableAiAgent` is `false` or omitted — but the platform ignores it, and the XML → Fluent transform doesn't
reconstruct any AI field from a record whose `enable_ai_agent` is false.

### Determining AI-agent support for a definition

Check the definition file under `src/api/playbook/built-ins/activity-definitions/` for the activity you're using:

- `enableAiAgent: 'on'` on the definition is what exposes any AI-agent fields on `ActivityConfig` at all. If the
definition doesn't set it (the default is `'off'`), setting any AI-agent field on an activity built from it is a
TypeScript error.

- `aiAgentExecutionMode: 'on'` as a top-level property of the definition (separate from
`aiAgentFieldDisplayPreferences` — see below) is what makes Autonomous mode available to activity instances. If the
definition doesn't set this, instances built from it are restricted to Collaborative mode (`'off'`); setting
`aiAgentExecutionMode: 'on'` on such an instance is a build error.

- `aiAgentFieldDisplayPreferences` on the definition (mirrors `inputDisplayPreferences`/
`experienceDisplayPreferences`)
controls exactly which AI-agent fields an instance built from it may set. If the definition sets `enableAiAgent: 'on'`
but declares no `aiAgentFieldDisplayPreferences`, all AI-agent fields are exposed. Otherwise only the fields listed in
the map are — setting any other AI-agent field is a TypeScript error, even though the definition otherwise supports
AI agents. Exception: `enableAiAgent`, `aiAgentObjective`, `aiAgentExecutionMode`, and `aiAgentRunAs` are always settable regardless of what the map declares.

Do not infer a definition's AI-agent support or field set from another definition — two AI-capable definitions can
differ in whether Autonomous mode is available and in which non-required fields `aiAgentFieldDisplayPreferences`
exposes (e.g. one may omit `conversationalAgents` or `aiAgentRunWithRoles` while another includes them).

### What's allowed and what isn't

- `aiAgentObjective` is required once `enableAiAgent` is `true`. If it's omitted, the definition's own default (if
any — see below) is used. If it's omitted and the definition has no default, or if it's explicitly set to `''`, the
build errors: ``aiAgentObjective` is required when `enableAiAgent` is true.` An explicit empty string always
overrides the definition's default — it does not fall back silently.

- AI agent activities are not allowed in public playbooks. Setting `enableAiAgent: true` on an activity in a
playbook with `publicAccess: true` is a build error — see Public Playbooks in `playbook-api`.

- `aiAgentObjAdditionalDetail` only applies in Autonomous mode. If it's set while `aiAgentExecutionMode` is not
`'on'`, the build warns (
``aiAgentObjAdditionalDetail` only applies when `aiAgentExecutionMode` is `on`; it will be discarded.`) and
the value is discarded — it is not persisted.

- `aiAgentExecutionMode: 'on'` requires the definition to enable Autonomous mode. Check whether the activity
definition supports Autonomous mode by verifying that its own `aiAgentExecutionMode` property is set to `'on'` in the
definition file (see Determining AI-agent support for a definition above). Setting `aiAgentExecutionMode: 'on'`
on an instance whose definition doesn't support it is a build error:
``aiAgentExecutionMode` can only be `on` when the activity definition enables Autonomous mode.` Use `'off'`,
or switch to a definition that supports Autonomous mode.

- `aiAgentRunWithRoles` and `conversationalAgents` accept a mix of raw sys_id strings and typed references —
`Record<'sys_user_role'>` for roles, `Record<'sn_aia_agent'>` for conversational agents — rather than only strings.

- `aiAgentSupportedActions` only accepts `'update_record'`, `'create_record'`, and `'mark_complete'`. It lists the
actions the AI agent is permitted to take when completing the activity.

- `aiAgentRunAs` only accepts `'prior_activity_user'` or `'playbook_user'`. `'playbook_user'` runs the agent as
the user who triggered the playbook. `'prior_activity_user'` runs it as a specific user selected from a prior
activity; the platform tracks that selection internally rather than exposing it as a field playbook authors set
directly. When `aiAgentRunAs` is omitted or nullish, it falls back to the activity definition's own
`aiAgentRunAs` default (see below); if the definition declares none either, it defaults to `'playbook_user'`.

### Default-value inheritance from the activity definition

A definition can declare its own defaults for `aiAgentObjective`, `aiAgentObjAdditionalDetail`, `aiAgentRunAs`,
`conversationalAgents`, `aiAgentRunWithRoles`, and `aiAgentSupportedActions` as plain properties on the
`ActivityDefinition({...})` call itself
(not a separate `defaultAiAgent...`-style property, unlike `defaultInputs`/`defaultExperienceProperties`). When an
activity built on such a definition omits one of these fields entirely, the definition's default is used
automatically:

```
// Example: RecordForm declares its own aiAgentObjective/aiAgentRunAs defaults, so omitting
// them here inherits those — check the definition file to see what any given definition declares.
recordForm: wfa.playbook.activity(
        ActivityDefinitions.Core.RecordForm,
        {
           $id: Now.ID['review_record'],
           label: 'Review Record',
           order: 1,
           startRule: wfa.playbook.run.Immediately(),
           restartRule: 'RUN_ONLY_ONCE',
           enableAiAgent: true,
        }
)
```

An explicit value always takes priority over the definition's default — including an explicit empty string or empty
array, which is treated as "no value" rather than "use the default." Only truly omitting the field inherits the
definition's default.

`aiAgentFieldDisplayPreferences` interacts with this default-inheritance mechanism, and it's not the
same all-or-nothing gate it is for inputs/experience properties: if a definition excludes one of these AI
fields from its `aiAgentFieldDisplayPreferences` (so it isn't author-facing), setting it explicitly is a
TypeScript error, but the definition's own default for it still applies as long as the agent is enabled —
falling back to an empty value (`''` or `[]`) if the definition declares no default of its own either.
This lets a definition bake in a fixed value for a field without exposing it for authors to override.

Check the definition file to see which of these defaults, if any, it actually declares — a definition supporting AI
agents doesn't necessarily declare a default for every field eligible for inheritance.

## Best Practices

- Keep inputs minimal. Only set inputs that differ from the definition's defaults — omitting an input uses the definition's `defaultInputs` value.

- Check the definition source to determine input and experience property types. Each built-in definition file under `src/api/playbook/built-ins/activity-definitions/` declares the column type for every input and experience property. The column type determines the value format:

- `FieldListColumn` — pass a `FieldList` global: `FieldList<'table_name'>(['field1', 'field2'])`. The type parameter scopes the allowed field names to that table.

- `TemplateValueColumn` — pass a `TemplateValue` global: `TemplateValue({ field1: value1, field2: value2 })`. Values can be literals or data pills. Both `FieldList` and `TemplateValue` are available globally in `.now.ts` files — do not import them.

- Use `wfa.playbook.dataPill()` for runtime values. Never hardcode sys_ids or field values that should come from prior steps — pills resolve at runtime.

- Set `restartRule` intentionally. Use `'RUN_ONLY_ONCE'` for steps that should not repeat (data capture, approval); use `'RUN_ALWAYS'` for steps that should re-run on restart.

- Use `experienceProperties` for UI customization only. Keep workflow logic in inputs, not in experience properties.

- Declare activities in execution order. Top-to-bottom declaration order matches the execution flow and avoids "variable used before declaration" errors.

- Return every activity from the `activities` callback. Omitting an activity from the return silently drops it from the lane.

## Important Notes

- Activities must be declared as `const` variables and returned from the `activities` callback using explicit `key: value` form (e.g., `return { review: review }`) — the build transformer reads the property keys statically.

- An activity must be declared before it can be referenced in another activity's `wfa.playbook.run.After()` or in a sibling activity's `wfa.playbook.dataPill(...)` inside the same `activities` callback. TypeScript catches in-scope forward references as "variable used before declaration." Cross-lane references go through the lane variable (e.g., `intake.review.outputs.record`) — the lane itself still has to be declared before any other lane references it.

- Use the ordering fields supported by the config type — see `ActivityConfig` in `playbook-api`.

- Decision branch `id` values are used for `decision.branches.<id>` references — choose descriptive, snake_case identifiers.

- The `else` branch in a Decision has no `condition` and must be last.

- Cross-lane activity references in `wfa.playbook.run.After()` are not supported — use a lane-level dependency on the lane config instead. See `playbook-guide` for the explanation.

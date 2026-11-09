Version: 4.14.0

# PlaybookDefinition

Creates a ServiceNow Playbook: a guided multi-step process that operates on a record (`sys_pd_process_definition`). Composed of lanes, activities, triggers, inputs, and outputs with inline `startRule` ordering.

## Signature

```
PlaybookDefinition(
    config: PlaybookConfig,
    triggers: PlaybookTriggerDeclaration,
    body: PlaybookBody
)
```

## API Structure

The Playbook DSL follows a 3-argument pattern:

```
PlaybookDefinition(
    config,        // PlaybookConfig - top-level playbook properties, inputs, outputs
    triggers,      // PlaybookTriggerDeclaration - { triggers: [...] }
    body           // PlaybookBody - lanes and activities with inline startRule ordering
)
```

This pattern mirrors the Flow API while accommodating playbooks' need for multiple triggers. Declarative state (inputs, outputs) lives on the 1st-arg `config` alongside other top-level properties; the 2nd arg carries the playbook's triggers.

### Parameters

- 
config: `PlaybookConfig`
Top-level playbook properties, plus declarative `inputs` and `outputs`. See PlaybookConfig below.

- 
triggers: `PlaybookTriggerDeclaration`
Object containing a `triggers` array of `wfa.playbook.trigger(...)` instances. See PlaybookTriggerDeclaration below and wfa.playbook.trigger() for trigger construction.

- 
body: `PlaybookBody`
Object defining lanes and activities with inline startRule ordering. See PlaybookBody and PlaybookBodyParams below.

## Imports

```
import {
    // Main definition function
    PlaybookDefinition,

    // wfa namespace contains playbook helpers under wfa.playbook.*
    // (lane, activity, trigger, run, dataPill, currentActivity)
    wfa,

    // Trigger types (used as first argument to wfa.playbook.trigger())
    PlaybookTriggerTypes,

    // OOTB activity definitions
    ActivityDefinitions,
} from '@servicenow/sdk/automation'

import {
    // Column types for inputs/outputs
    StringColumn,
    ReferenceColumn,
    IntegerColumn,
    BooleanColumn,
    DateTimeColumn,
    // ... other column types
} from '@servicenow/sdk/core'
```

### PlaybookConfig

`PlaybookConfig`

Top-level playbook properties (maps to `sys_pd_process_definition`).
Properties:

- 
$id (required): `Now.Internal.ExplicitKey | string | number`
Unique identifier.

- 
label (required): `string`
Display name (max 240 chars).

- 
name (optional): `string`
Internal name. Must be unique across playbooks. If not provided, auto-generated from `label` by converting to lowercase and replacing non-alphanumeric characters with underscores. Acts as the record's stable identity — once a playbook is deployed, avoid changing `name` on subsequent edits, as a changed `name` is treated as a new record rather than an update to the existing one.

- 
description (optional): `string`
Description (max 1000 chars).

- 
restartable (optional): `'RESTARTABLE_TRUE' | 'RESTARTABLE_FALSE'`
Whether playbook can be restarted. Default: `'RESTARTABLE_FALSE'`.

- 
allowAsNested (optional): `boolean`
Can be used as a nested playbook. Default: `false`. Can only be `true` when `executionType` is `'on_demand'` — see Execution Types below.

- 
access (optional): `'package_private' | 'public'`
Visibility scope. Default: `'public'`.

- 
publicAccess (optional): `boolean`
Allows the playbook to be embedded on public pages and run by unauthenticated users. Default: `false`. See Public Playbooks below.

- 
runStrategy (optional): `'run_once' | 'run_if_not_running' | 'run_always'`
Execution strategy. Default: `'run_once'`.

- 
executionType (optional): `'record_driven' | 'on_demand'`
Execution type. Default: `'record_driven'`. `'on_demand'` playbooks are started explicitly rather than by a trigger and carry several related restrictions — see Execution Types below.

- 
processType (optional): `string`
Playbook type name. Must exist in the SDK process type mapping. Currently supported value is `'Standard playbook'`. Default: `'Standard playbook'`.

- 
parentTable (optional): `TableName`
Table whose records this playbook operates on. When set, auto-generates a `parent_record` process input typed as a Reference to this table. The triggering record is then accessible in the lanes callback via `params.parentRecord`, dot-walkable to all fields. Required for record-driven playbooks that need to read fields from the triggering record. Cannot be set when `executionType` is `'on_demand'` — see Execution Types below.

- 
inputs (optional): `Record<string, Column>`
Playbook input schema declared on the config object. Maps to `sys_pd_process_input`. See Inputs and Outputs below.

- 
outputs (optional): `Record<string, Column>`
Playbook output schema declared on the config object. Maps to `sys_pd_process_output`. See Inputs and Outputs below.

- 
dataRetentionPeriodOverride (optional): `'2_week' | '6_week' | '6_month' | '1_year'`
Data retention period override. Default: `'6_week'`.

- 
schemaVersion (optional): `number`
Schema version the playbook is generated against. Defaults to Fluent's safe fallback version
(`PLAYBOOK_DEFAULTS.MAX_SUPPORTED_SCHEMA_VERSION`, currently `3`) when omitted; preserved for
round-trip data integrity when transforming an existing playbook. See Schema Version
Compatibility below.

- 
evaluateVariantChildrenAfter (optional): `Now.Internal.ExplicitKey`
`$id` of an activity declared in `lanes`. Defers variant evaluation until that activity completes, instead of evaluating variants at playbook start. Only meaningful when at least one variant is declared — see wfa.playbook.variant() below for how this widens what a variant's `condition` can reference. Must reference an activity, not a lane — targeting a lane, or an activity whose `startRule` is `wfa.playbook.run.Manually()`, is an error.

#### Schema Version Compatibility

The highest `schema_version` an instance accepts depends on its release:

| Release | Highest supported schema version |
| Australia and older | 3 |
| Brazil and newer | 4 |

Fluent defaults `schemaVersion` to `3` so generated playbooks stay compatible with Australia and
older instances. If the target instance is on Brazil or newer, set `schemaVersion: 4` explicitly
to opt into the newer schema.

Don't infer the ceiling from the release name alone — confirm it against the target instance's
`com.glide.pad.core.model.maxSupportedSchemaVersion` system property before relying on it.

A `schema_version` below 3 predates the Fluent SDK entirely and is a hard limit, not a version to
opt into — see Legacy Schema Version in `playbook-unsupported-features-guide`.

#### Execution Types

`executionType` controls how a playbook starts:

- `'record_driven'` (default) — starts from one or more `triggers` reacting to record events or a schedule.

- `'on_demand'` — started explicitly (for example, via the on-demand launcher or a caller) rather than by a trigger. Also known as standalone playbook execution type.

Because an `'on_demand'` playbook has no triggering record, the following are enforced — at both the type level (a compile error) and at build time (a diagnostic, for JS/`as any`/untyped callers that bypass the type check) — whenever `executionType: 'on_demand'`:

- `triggers` is not configurable at all — omit it entirely.

- `parentTable` cannot be set.

- `allowAsNested` can be `true` or `false` for on-demand playbooks; can only be `false` for record-driven playbooks.

- `params.parentRecord` is unavailable in both the `lanes` callback (`PlaybookBodyParams`) and the `permissions` callback (`PermissionParams`) — referencing it is a compile error (`Property 'parentRecord' does not exist on type ...`), since there is no parent record without a `parentTable`.

- `launcherShowRecordForm`, `launcherRecordFormView`, and `launcherTemplateFields` cannot be set — on-demand playbooks aren't launched through this record-form launcher flow.

One additional restriction is enforced only as a build diagnostic (there is no type-level restriction on permission contents):

- At least one permission set must grant `launch: true`. Otherwise there is no way to launch the playbook. This applies whether or not a `permissions` callback is declared at all — omitting `permissions` entirely on an `'on_demand'` playbook still triggers this diagnostic. See Playbook permissions below and `playbook-permissions-guide`.

#### Launcher Configuration

The following optional fields configure the playbook's on-demand launcher UI.

- 
launcherTitle (optional): `string`
Title shown in the playbook on-demand launcher. Required by the on-demand launcher UI —
if any other launcher field is set and launcherTitle is omitted, it defaults to the
playbook's `label`.

- 
launcherDescription (optional): `string`
Description shown in the playbook on-demand launcher.

- 
launcherShowRecordForm (optional): `boolean`
When true, shows a create-new-record form in the launcher. Default: `false`. Cannot be set when `executionType` is `'on_demand'` — see Execution Types above.

- 
launcherRecordFormView (optional): `string | Record<'sys_ui_view'>`
Sys id or typed record representing the form view to use. Depends on `parentTable`. Cannot be set when `executionType` is `'on_demand'` — see Execution Types above.

- 
launcherTemplateFields (optional): `string | TemplateValueElement`
Pre-populated field values for the record form. Use `TemplateValue({ fieldName: value, ... })`. Depends on `parentTable`. Cannot be set when `executionType` is `'on_demand'` — see Execution Types above.

- 
launcherInputs (optional): `Partial<Record<keyof inputs, string | Record<'table'>>>`
Sets the value shown, in the on-demand launcher, for each of the playbook's own `inputs`. Requires `inputs` to be declared — keys are constrained to declared input names. For a `ReferenceColumn` input, pass a sys_id string or a typed `Record<'table'>` reference. If an input has a `default` and no `launcherInputs` value is set for it, the default is shown in the launcher automatically. Setting `launcherInputs` only changes what's shown in the launcher — it does not change the input's own `default` value. See the example below (`notes` overrides its own default).

Non-reference inputs: every non-reference input — including `BooleanColumn` and `IntegerColumn` — takes a string here, e.g. `isUrgent: 'true'` or `retryCount: '3'`, never a raw `true`/`3` literal. A raw literal fails to compile, so string is the only form that works. See the `isUrgent` / `retryCount` example below.

Diagnostic: Setting `launcherRecordFormView` or `launcherTemplateFields` without `launcherShowRecordForm: true` is a build error. Always set `launcherShowRecordForm: true` first when using either of those fields.

Diagnostic: Setting `launcherInputs` without declaring `inputs` is a build error, as is a `launcherInputs` key that doesn't match a declared input name.

Diagnostic: When `launcherShowRecordForm: true`, every `mandatory: true` input must resolve to a value — either a `default` or an explicit `launcherInputs` override — or it's a build error. This check only applies when `launcherShowRecordForm` is true; a mandatory input satisfied entirely through a trigger's input mapper (see `triggers`) is unaffected.

Note: When a playbook is deployed, changes are not applied to running instances automatically. To make new changes take effect at runtime, open Playbook Designer and activate the playbook again. The build/deploy output logs this reminder.

#### Public Playbooks

Setting `publicAccess: true` marks the playbook as eligible to be embedded on public pages and run by unauthenticated users. Because such a playbook is reachable without a session, the platform restricts what it may contain, and four of those restrictions are enforced at build time:

- `parentTable` is required. A public playbook must be tied to a record.

- `executionType: 'on_demand'` is disallowed. An on-demand (standalone) playbook has no parent record, so it can never be public. `publicAccess` is typed as `never` for on-demand playbooks.

- Every activity must come from a definition that allows public use. A definition opts in with `publicAccess: true`.

- No AI agent activities. No activity may set `enableAiAgent: true`. Some public-eligible definitions (the record forms) do support AI agents, so this combination is otherwise easy to reach.

`publicAccess: true` is not a single switch that makes a playbook publicly reachable. It sets `public_access` on the playbook and nothing else. Actually serving the playbook to unauthenticated users additionally requires configuration that lives outside Fluent — a public-facing page or experience that embeds the playbook component, and guest-user access to the parent table and the playbook's runtime records. Authoring side, editing a playbook that already has `public_access` set requires the `playbook.write.public_access` role; without it Playbook Designer opens the playbook read-only. Plan for that setup work before deploying a public playbook and expecting it to be usable.

Both `public_access` fields this relies on — on `sys_pd_process_definition` (the playbook) and on `sys_pd_activity_definition` (each activity's definition) — require the Process Automation Designer (`sn_pa_designer`) store app at version 29.0.0 or later (the Australia release); the fields don't exist on earlier versions. The SDK doesn't validate the installed version.

The definitions that allow it are the built-ins declaring `publicAccess: true`, so you can check without being connected to an instance — open the definition under `ActivityDefinitions.Core` and look for the flag.

Fluent enforces the four constraints above at build time. Playbook Designer re-runs them when the playbook is activated, so a playbook that builds cleanly should also activate.

### triggers

`PlaybookTriggerDeclaration`

The playbook's trigger instances.

Properties:

- triggers (required): `PlaybookTriggerInstance[]`
Trigger instances created with `wfa.playbook.trigger()`. Maps to `sys_pd_trigger_instance`. See wfa.playbook.trigger() below for trigger types, trigger inputs, and trigger mapper behavior.

The `triggers` array is required for record-driven playbooks, even when there are no triggers — pass an empty array explicitly:

```
{ triggers: [] }
```

When `executionType` is `'on_demand'`, `triggers` is not configurable at all — omit it entirely. On-demand playbooks have no triggering record, so this is enforced both as a type restriction and a build diagnostic. See Execution Types above.

Inputs and outputs are declared on the 1st-arg `config` (see Inputs and Outputs below), not here.

### variants

`(params: PlaybookBodyParams<I>) => Record<string, VariantDefinition>`

Properties:

- variants (optional): `(params: PlaybookBodyParams<I>) => Record<string, VariantDefinition>`
A function that receives `params` and returns a record of `wfa.playbook.variant()` definitions keyed by name. Variants let a playbook branch on a condition that's evaluated playbook-wide, independent of any specific lane or activity. See `wfa.playbook.variant()` below.

Declared here (alongside `triggers`), variants surface inside the 3rd-arg `body`'s `lanes`/`activities` callbacks via `params.variants.<name>` — see PlaybookBodyParams below. This is the only way to reference a variant from an activity; there is no separate `Ref()`-style indirection.

## Inputs and Outputs

Playbook inputs and outputs are declared on the 1st-arg `config` and use the same `Column` types as table fields. Inputs feed values into the playbook at launch time (from triggers or from a caller); outputs publish values when the playbook completes.

### Declaring inputs

Inputs are declared using the `inputs` object on the config. Each trigger can provide values for these inputs via its trigger mapper — the 4th argument to `wfa.playbook.trigger()` that maps trigger data or literal values to the declared input schema.

```
{
    $id: Now.ID['my_playbook'],
    label: 'My Playbook',
    parentTable: 'incident',
    inputs: {
        record: ReferenceColumn({
            label: 'Record',
            referenceTable: 'incident',
            mandatory: true,
        }),
        priority: IntegerColumn({
            label: 'Priority Override',
            default: 3,
        }),
        summary: StringColumn({
            label: 'Summary',
            maxLength: 1000,
        }),
    },
}
```

Column options:

- `label`: Display name shown in the designer.

- `mandatory`: When `true`, the playbook fails to launch if the input is unmapped. Build-time error fires if a trigger mapper omits a mandatory input.

- `default`: Default value applied when no caller value is provided.

- `maxLength`: Maximum length (string columns).

- `referenceTable`: Target table (reference columns).

- `referenceQual`: Optional encoded query filter applied to the reference picker (e.g. `active=true`). Omit to show all records on the target table.

### Declaring outputs

```
{
    $id: Now.ID['my_playbook'],
    label: 'My Playbook',
    outputs: {
        resolvedBy: ReferenceColumn({
            label: 'Resolved By',
            referenceTable: 'sys_user',
        }),
        closureCode: StringColumn({
            label: 'Closure Code',
            maxLength: 40,
        }),
    },
}
```

Outputs are declarative schema only at this layer — they describe the shape the platform will publish when the playbook completes. Values are assigned to them from inside an activity using the `ActivityDefinitions.Core.SetPlaybookOutputs` built-in activity (its single `playbook_outputs` input is a `TemplateValue` keyed by the playbook's declared output names) — see `playbook-activities-guide` for the full authoring pattern.

Outputs are also not consumable in the Fluent DSL at this time — you cannot reference them from activity inputs, experience properties, or conditions. Support for consuming outputs is planned as future work.

Declared inputs surface inside the `lanes` callback via `params.inputs.<name>`. See PlaybookBodyParams below for the callback shape and `playbook-datapills-guide` for valid pill usage and format.

Maps to: `sys_pd_process_input`, `sys_pd_process_output`

### body

`PlaybookBody`

A `PlaybookBody` object that declaratively defines lanes and activities. Execution ordering is declared inline on each lane and activity config via `startRule`.

```
interface PlaybookBody<I> {
    lanes: (params: PlaybookBodyParams<I>) => Record<string, LaneDefinition | ActivityInstance<any> | ManualActivityReference>
}
```

Properties:

- lanes (required): `(params: PlaybookBodyParams<I>) => Record<string, LaneDefinition | ActivityInstance<any>>`
A function that receives `params` and returns a record of lane definitions and/or stage-level activities (typically a `Decision`) keyed by name. Mixing lanes and stage-level activities in the same returned record is how stage-level Decision routing is expressed. The callback form is required — the plugin extracts the lane/activity definitions from the arrow function body, not from a plain record.

#### Lane input shape (`wfa.playbook.lane`)

`wfa.playbook.lane()` accepts an object with `config` (a plain `LaneConfig`) and `activities` (a callback that receives `params` and returns the activity instances).

```
type LaneFunction = <A extends Record<string, ActivityInstance<any> | ManualActivityReference>>(definition: {
    config: LaneConfig
    activities: (params: PlaybookBodyParams) => A
}) => LaneDefinition & LaneDataReference<A>
```

Properties:

- 
config: Lane configuration. Must be a plain `LaneConfig` object — the plugin reads its properties statically and does not invoke a callback.

- 
activities: Function receiving `params` (the same `PlaybookBodyParams` the `lanes` callback receives) and returning a record of activity instances keyed by name. Must use `const` + explicit-key `return { name: name, ... }` form so the build transformer can read the property keys statically.

The returned value carries the declared activity names via `LaneDataReference<A>`, which is how cross-lane references like `intake.review.outputs.record` type-check. `LaneDefinition` itself is a marker interface; the developer-visible surface lives on `LaneDataReference<A>`.

#### LaneConfig

```
interface LaneConfig {
    $id: Now.Internal.ExplicitKey | string | number
    label: string
    name?: string                  // Optional internal name (auto-generated from label if not provided)
    order: number
    startRule: LaneExecutionRule       // Required - wfa.playbook.run.Immediately() or wfa.playbook.run.After(...)
    restartRule: RestartRule           // Required - 'RUN_ALWAYS' | 'RUN_ONLY_ONCE' | 'RUN_ONLY_ON_RESTART'
    description?: string
    conditionToRun?: string
    startWithDelay?: StartWithDelay    // Optional delay before the lane starts
    permissions?: LanePermissions      // Access control for this lane - see Permissions below
}
```

Properties:

- 
$id (required): `Now.Internal.ExplicitKey | string | number`
Unique identifier.

- 
label (required): `string`
Display name shown in Playbook Designer. Also used to auto-generate `name`.

- 
order (required): `number`
Display position in Playbook Designer. Controls visual layout only — use `startRule` for execution order.

- 
startRule (required): `LaneExecutionRule`
When this lane starts. `wfa.playbook.run.Immediately()`: no dependencies; `wfa.playbook.run.After(...deps)`: starts after all listed dependencies complete.

- 
restartRule (required): `'RUN_ONLY_ONCE' | 'RUN_ALWAYS' | 'RUN_ONLY_ON_RESTART'`
Re-execution behavior when the playbook is restarted. `'RUN_ONLY_ONCE'`: skipped on restart; `'RUN_ALWAYS'`: re-runs on restart; `'RUN_ONLY_ON_RESTART'`: skipped on first run, runs only on restart.

- 
name (optional): `string`
Internal name. If provided, it is used verbatim. If omitted, the `name` is auto-generated by slugifying the `label`; when sibling lanes produce duplicate slugs, a suffix is appended: `lane_name`, `lane_name_1`, `lane_name_2`, etc. The `name` is the lane's stable identity — once deployed, ideally do not change it on subsequent edits, as a changed `name` is treated as a new lane rather than an update to the existing one.

- 
description (optional): `string`
Optional description.

- 
conditionToRun (optional): `string`
Encoded query evaluated at runtime. The lane is skipped when the condition is false. Use `wfa.playbook.dataPill()` to interpolate runtime values.

- 
startWithDelay (optional): `StartWithDelay`
Optional delay applied after `startRule` is satisfied. See `startWithDelay` below.

- 
permissions (optional): `LanePermissions`
Access control for this lane, grouped by reference kind. See Permissions below and `playbook-permissions-guide`.

#### startWithDelay

Optionally delays the start of a lane or activity after its `startRule` is satisfied. Maps to a `sys_pd_timer_attributes` descendant record. Discriminated by `type`.

```
import { Record } from '@servicenow/sdk/core'

export type StartWithDelay =
    | { type: 'explicit'; duration: Duration; timerSchedule?: string | Record<'cmn_schedule'> }
    | { type: 'relative'; duration: Duration; relativeDatetime: string; relativeOperator: 'before' | 'after'; timerSchedule?: string | Record<'cmn_schedule'> }
    | { type: 'percentage'; percentage: number; percentageDatetime: string; timerSchedule?: string | Record<'cmn_schedule'> }

type Duration = {
    days?: number
    hours?: number
    minutes?: number
    seconds?: number
}
```

`type: 'explicit'` — Fixed delay specified as a duration.

Properties:

- 
type (required): `'explicit'`
Discriminator.

- 
duration (required): `Duration`
How long to delay. Accepts either:

- `Duration()` helper: `Duration({ days: 4, hours: 3, minutes: 2, seconds: 1 })` (preferred — generated code always uses this form)

- Raw object: `{ days: 4, hours: 3, minutes: 2, seconds: 1 }` (days, hours, minutes, seconds all optional)

Also accepts a data pill.

`type: 'relative'` — Delay relative to a datetime, before or after it.

Properties:

- 
type (required): `'relative'`
Discriminator.

- 
duration (required): `Duration`
How far before or after `relativeDatetime` to start. Accepts either:

- `Duration()` helper: `Duration({ days: 1, hours: 2 })` (preferred — generated code always uses this form)

- Raw object: `{ days: 1, hours: 2 }` (days, hours, minutes, seconds all optional)

Also accepts a data pill.

- 
relativeDatetime (required): `string`
Reference datetime in `'yyyy-MM-dd HH:mm:ss'` format. Accepts a data pill.

- 
relativeOperator (required): `'before' | 'after'`
Whether the delay falls before or after `relativeDatetime`.

`type: 'percentage'` — Delay as a percentage of the time window up to a reference datetime.

Properties:

- 
type (required): `'percentage'`
Discriminator.

- 
percentage (required): `number`
Percentage of the time window (exclusive 0, inclusive 100; decimals allowed, e.g. `10.5`). Accepts a data pill.

- 
percentageDatetime (required): `string`
Reference datetime in `'yyyy-MM-dd HH:mm:ss'` format. Accepts a data pill.

- 
timerSchedule (optional): `string | Record<'cmn_schedule'>`
A `cmn_schedule` that pauses the delay outside its active hours and resumes counting once the schedule is active again — useful for business-hours-only reminders or SLA-aware timers. Available on `'explicit'`, `'relative'`, and `'percentage'` delays. Pass a `sys_id` string to reference an existing `cmn_schedule` record, or a `Record<'cmn_schedule'>` reference if the app declares/owns the schedule itself. See "Scheduling delays" in `playbook-lanes-guide` for examples.

Duration properties:

- 
days (optional): `number`
Days component.

- 
hours (optional): `number`
Hours component.

- 
minutes (optional): `number`
Minutes component.

- 
seconds (optional): `number`
Seconds component.

All `Duration` fields are optional. Generated code emits `Duration({ seconds: 0 })` when the platform record has no delay configured (an empty or unset `timer_duration`); this is a valid zero-length delay and safe to change or leave as-is.

#### PlaybookBodyParams

The `params` object available inside the `lanes` callback closure:

```
interface PlaybookBodyParams<I, V> {
    inputs: { [K in keyof I]: InputReference }
    state: string
    parentRecord: DataReference
    variants: { readonly [K in keyof V]: VariantReference }
}
```

Properties:

- 
params.inputs.* : References to declared playbook inputs (dot-walkable for data pills).

- 
params.state : Reference to the playbook's state field (dot-walkable for data pills).

- 
params.parentRecord : Reference to the parent record (available when `parentTable` is set on config). Dot-walkable for data pills referencing fields on the parent record. Not present at all when `executionType` is `'on_demand'` — referencing it is a compile error. See Execution Types above.

- 
params.variants.* : References to variants declared in the 2nd-arg `variants` callback (see variants above), keyed by name. Pass directly as an activity's `variant` or `variantOverrides[].variant` field — no wrapping call needed. See wfa.playbook.variant() below.

#### Activity Output References

Same-lane outputs use local variables within the `activities` callback; cross-lane outputs use the lane variable from the `lanes` callback (e.g. `intake.review.outputs.record`). See `playbook-activities-guide` for the full pattern with examples.

## Permissions

Playbooks and lanes can grant access to users, user groups, roles, and user criteria — covering who can view, launch, restart, and manage the playbook, and who can act on its stages/lanes and activities.

- Playbook permissions are declared in the 2nd `PlaybookDefinition` argument as a `permissions` callback alongside `triggers`: `permissions: (params) => ({ users: [...], userGroups: [...], roles: [...], userCriterias: [...] })`. Each permission set requires `view`, which gates the other options.

- Lane permissions are declared on the lane's `config.permissions` object with a reduced set of options that are independent (no `view` gate).

References can be sysIds or `wfa.playbook.dataPill(...)` pills — including `params.parentRecord` and `wfa.playbook.activityRef(...)` activity-output references. `params.parentRecord` is unavailable (compile error) when `executionType` is `'on_demand'` — see Execution Types above.

See `playbook-permissions-guide` for the full set of options, reference kinds, and pill usage.

### wfa.playbook.activityRef()

An activity reference that takes as input the ID of any activity defined in the playbook.

```
wfa.playbook.dataPill(
    wfa.playbook.activityRef(Now.ID['cra_acknowledgment_form']).outputs.email.direct
)
```

Supported in pills within permissions, allowing the permission to reference an activity that is defined later in the file. Also supported in a variant's `condition` once `evaluateVariantChildrenAfter` is set on the playbook config — see wfa.playbook.variant() below — to reference an activity guaranteed to have completed by that evaluation point. Also supported as a `Run.After()` dependency inside a `variantOverrides` entry's `startRule`, when the target activity is declared later in the same lane than the activity being overridden — a forward reference that a plain variable can't express without violating declaration order; `activityRef()` resolves by id instead, so declaration order doesn't matter. Do not use `wfa.playbook.activityRef()` outside these three contexts.

## Helper Functions

### wfa.playbook.trigger()

Creates a trigger instance with a 4-argument pattern.

```
wfa.playbook.trigger(
    triggerType: PlaybookTriggerType,
    config: TriggerConfig,
    triggerInputs: TriggerInputs,
    playbookInputs?: (trigger: TriggerOutputs) => Record<string, unknown>
): PlaybookTriggerInstance
```

#### TriggerConfig

```
interface TriggerConfig {
    $id: Now.ID
    label?: string
}
```

Properties:

- 
$id (required): `Now.Internal.ExplicitKey | string | number`
Unique identifier.

- 
label (optional): `string`
Display label.

#### PlaybookTriggerType

```
PlaybookTriggerTypes.RecordCreate          // Triggered when a record is created
PlaybookTriggerTypes.RecordUpdate          // Triggered when a record is updated
PlaybookTriggerTypes.RecordCreateOrUpdate  // Triggered on create or update
PlaybookTriggerTypes.Scheduled             // Triggered on a schedule
```

#### TriggerInputs

The 3rd argument specifies the table the trigger monitors and optional filtering conditions. Each trigger monitors a single table (record-based triggers can additionally include its extended tables via `runTriggerOnExtendedTables`). The structure varies by trigger type:

Record-based triggers (RecordCreate, RecordUpdate, RecordCreateOrUpdate) accept these properties:

RecordTriggerInputs properties (all record-based triggers):

- 
table (required): `string`
Table to monitor (for example, `'incident'`).

- 
condition (optional): `string`
GlideRecord encoded query condition used to filter matching records.

- 
runTriggerOnExtendedTables (optional): `boolean`
Whether the trigger also applies to extended tables. Default: `false`.

Additional properties on `RecordUpdate` and `RecordCreateOrUpdate` only:

- triggerOnUniqueChange (optional): `boolean`
Fires only when a watched field's value uniquely changes, rather than on every update. See `playbook-triggers-guide`.

Scheduled triggers use these base properties:

ScheduledTriggerInputsBase properties:

- 
table (required): `string`
Table to query on each scheduled run.

- 
condition (optional): `string`
GlideRecord encoded query condition used to filter the scheduled record set.

- 
limit (required): `number`
Maximum number of records processed per run (1-1000).

- 
startDateAndTime (required): `string`
Timestamp for when the schedule starts, in `yyyy-MM-dd HH:mm:ss` format.

- 
timeZone (optional): `string`
Time zone for the schedule. Defaults to the system time zone.

Additional schedule-specific fields depend on the schedule type:

- `once` — runs a single time

- `daily` — adds frequency and end fields

- `weekly` — adds frequency, `daysOfTheWeek` (for example, `'12345'`), and end fields

- `monthly` — adds frequency, `daySelection` (`fixed_day` or `relative_weekday`), and end fields

- `yearly` — adds `repeatMonth`, `daySelection`, and end fields

- `periodically` — adds `repeat` (`dd HH:mm:ss`) and end fields

#### playbookInputs

The optional 4th argument is only used when the playbook declares inputs or the trigger table differs from the playbook's `parentTable`. It maps declared playbook inputs and `parentRecord` from trigger data or hardcoded literal values:

```
wfa.playbook.trigger(
    PlaybookTriggerTypes.RecordCreate,
    { $id: Now.ID['trig_1'], label: 'On Incident Created' },
    { table: 'incident', condition: 'priority=1' },
    (trigger) => ({
        parentRecord: wfa.playbook.dataPill(trigger.current.assigned_to),
        record: wfa.playbook.dataPill(trigger.current),
        priority: wfa.playbook.dataPill(trigger.current.priority),
        status: 'in_progress', // hardcoded literal
    })
)
```

Use `(trigger) => ({ ... })` when the mapper reads from `trigger.current`. Use `() => ({ ... })` when every mapped value is hardcoded. Omit the 4th argument entirely when the playbook has no declared inputs and the trigger table matches the playbook's `parentTable`.

Mapper keys must match declared playbook input names or `parentRecord`. To map values from the triggering record, wrap `trigger.current` references in `wfa.playbook.dataPill(...)`.

See `playbook-triggers-guide` for detailed mapper examples, whole-record pills, template literals, dot-walk usage, and diagnostics.

Maps to: `sys_pd_trigger_instance`

### wfa.playbook.activity()

Creates an activity instance. Returns an `ActivityInstance` — a plain data object with `.outputs` and `.branches` properties but no builder methods.

```
wfa.playbook.activity(
    activityDefinition: ActivityDefinition,
    config: ActivityConfig,
    inputs?: Record<string, unknown>,
    experienceProperties?: Record<string, unknown>
): ActivityInstance<TBranches>
```

#### Parameters

Properties:

- 
activityDefinition (required): `ActivityDefinition`
The activity definition to instantiate.

- 
config (required): `ActivityConfig`
Activity configuration (ID, label, order, startRule, etc.).

- 
inputs (optional): `Record<string, unknown>`
Automation inputs passed to the underlying flow/action.

- 
experienceProperties (optional): `Record<string, unknown>`
UI component configuration — controls how the activity is rendered and what data is displayed to users.

Diagnostic: Some `inputs`/`experienceProperties` columns are marked `mandatory: true` on the backing flow/action
or activity type (e.g. New Record Form's `table`). Their effective value — your explicit value, or the activity
definition's `defaultInputs`/`defaultExperienceProperties` when omitted — must not be empty, or it's a build error.
An explicit value always wins over the default, even an empty one. A `wfa.playbook.dataPill(...)` value is never
treated as empty. See `playbook-activities-guide` for the full behavior and examples.

#### ActivityConfig

```
interface ActivityConfig {
    $id: Now.Internal.ExplicitKey | string | number
    label: string
    name?: string            // Optional internal name (auto-generated from label if not provided)
    order: number           // Required - display order within the parent scope (lane or lanes body)
    startRule: ActivityExecutionRule  // Required - wfa.playbook.run.Immediately() or wfa.playbook.run.After(...)
    description?: string
    conditionToRun?: string
    restartRule: 'RUN_ALWAYS' | 'RUN_ONLY_ONCE' | 'RUN_ONLY_ON_RESTART'  // Required
    startWithDelay?: StartWithDelay // Optional delay before the activity starts
    variantOverrides?: VariantOverride[] // Optional per-variant startRule/order overrides
    variant?: VariantReference      // Optional - scopes this activity to a single variant
    // variantOverrides and variant are mutually exclusive - setting both is a TypeScript compile error
}
```

Note: If `restartRule` is left unset, it defaults to `'RUN_ONLY_ONCE'` — matching Playbook Designer's own default.

Properties:

- 
$id (required): `Now.Internal.ExplicitKey | string | number`
Unique identifier.

- 
label (required): `string`
Display name.

- 
order (required): `number`
Display order within the parent scope (lane for in-lane activities, lanes body for stage-level Decision activities).

- 
startRule (required): `ActivityExecutionRule`
`wfa.playbook.run.Immediately()` — no dependencies; `wfa.playbook.run.After(...deps)` — starts after all listed dependencies complete.

- 
restartRule (required): `'RUN_ONLY_ONCE' | 'RUN_ALWAYS' | 'RUN_ONLY_ON_RESTART'`
`'RUN_ONLY_ONCE'`: skipped on restart; `'RUN_ALWAYS'`: re-runs on restart; `'RUN_ONLY_ON_RESTART'`: skipped on first run, runs only on restart.

- 
name (optional): `string`
Internal name. If provided, used verbatim; otherwise auto-generated from `label`. See Field notes below for details.

- 
description (optional): `string`
Description.

- 
conditionToRun (optional): `string`
Encoded query evaluated at runtime.

- 
startWithDelay (optional): `StartWithDelay`
Same shape as `LaneConfig.startWithDelay` — delays the activity start after `startRule` is satisfied.

- 
actionOverrides (optional): `ActionOverride[]`
Overrides the declarative actions (buttons), their labels, and display order (from `sys_declarative_action_assignment`) shown on this activity's Playbook Card. Each entry maps to a `sys_pd_activity_action_override` record. See ActionOverride below. Requires the Process Automation Designer (`sn_pa_designer`) store app at version 29.4 or later — on earlier versions the `sys_pd_activity_action_override` records are still written but have no effect; the SDK doesn't validate the installed version.

- 
variantOverrides (optional): `VariantOverride[]`
Per-variant overrides of `startRule`/`order`, applied when the referenced variant is selected at runtime. See VariantOverride below. Not available on `ManualActivityConfig` — see Optional Activities below. Mutually exclusive with `variant`; setting both is a TypeScript compile error.

- 
variant (optional): `VariantReference`
Scopes this activity to exist only within the given variant (a variant-only activity). Omit for a base activity shared across all variants. Reference the variant directly as `params.variants.<name>` — see params.variants.* under PlaybookBodyParams above. Mutually exclusive with `variantOverrides`; setting both is a TypeScript compile error.

AI Agent configuration (only available when the activity definition declares `enableAiAgent: 'on'` — see
`ActivityDefinitions`/`ActivityDefinition`). On the platform, AI agent configuration only takes effect when the
`sn_genai_platform` store app is installed and the `sn_pa_designer.enable_agentic_playbooks` system property is
`true`; the SDK doesn't validate either.

Every field below other than `enableAiAgent` itself is only meaningful on an instance that also sets `enableAiAgent: true` — the SDK doesn't block setting them otherwise (no build error/warning), but the platform ignores their values
when the agent isn't enabled on that instance, and the XML → Fluent transform doesn't reconstruct any of them from a
record whose `enable_ai_agent` is false.

This is a high-level field overview only — see `playbook-activities-guide`
for which built-in definitions support AI agents, per-field constraints, default-value inheritance, and validation
errors.

- 
enableAiAgent (optional): `boolean`
Turns AI agent support on/off for this activity instance.

- 
aiAgentExecutionMode (optional): `string`
`'off'`: Collaborative mode; `'on'`: Autonomous mode.

- 
aiAgentObjective (optional): `string`
Instructions telling the AI agent its responsibilities in Collaborative mode. Required once `enableAiAgent` is true;
if omitted, the activity definition's default is used when available.

- 
aiAgentObjAdditionalDetail (optional): `string`
Additional instructions used in Autonomous mode i.e. when `aiAgentExecutionMode` is `'on'`. Filtered by the activity
definition's `aiAgentFieldDisplayPreferences` like `aiAgentRunWithRoles`, `aiAgentSupportedActions`, and
`conversationalAgents` below — unlike the other fields on this list, these four are only available when the
definition's preferences include them (or the definition declares no preferences at all).

- 
aiAgentRunWithRoles (optional): `string[] | Record<'sys_user_role'>[]`
Roles the AI agent runs with for this activity instance. Accepts a list of sys_id strings for `sys_user_role` records,
a list of typed `Record<'sys_user_role'>` references, or a mix of both.

- 
aiAgentSupportedActions (optional): `('update_record' | 'create_record' | 'mark_complete')[]`
Actions the AI agent is permitted to take when completing this activity. If omitted, falls back to the activity
definition's own `aiAgentSupportedActions` default when available.

- 
aiAgentRunAs (optional): `'playbook_user' | 'prior_activity_user'`
Whose identity the AI agent runs under. `'playbook_user'` — the user who triggered the playbook.
`'prior_activity_user'` — a specific user selected from a prior activity. If
omitted or nullish, falls back to the activity definition's own `aiAgentRunAs` default, then to `'playbook_user'`
if the definition declares none either.

- 
conversationalAgents (optional): `string[] | Record<'sn_aia_agent'>[]`
AI agents (from AI Agent Studio) attached to this activity instance. Accepts a list of sys_id strings for
`sn_aia_agent` records, a list of typed `Record<'sn_aia_agent'>` references, or a mix of both.

#### ActionOverride

Contains a list of specific declarative actions, each with an overridden label and display order, which are shown in this activity's card at runtime.
Maps to a `sys_pd_activity_action_override` record. Requires the Process Automation Designer (`sn_pa_designer`) store app at version 29.4 or later; the SDK doesn't validate the installed version.

```
interface ActionOverride {
    actionAssignment: string | Record<'sys_declarative_action_assignment'>
    label: string
    displayOrder: number
}
```

Properties:

- 
actionAssignment (required): `string | Record<'sys_declarative_action_assignment'>`
Identifies the `sys_declarative_action_assignment` record whose button this overrides. Those rows are app/experience-specific platform configuration (not authored via Fluent). Pass the raw sys_id or a `Record<'sys_declarative_action_assignment'>` reference.

- 
label (required): `string`
Overridden button label shown on the Playbook Card.

- 
displayOrder (required): `number`
Overridden display order among the activity's action buttons.

Validation:

- An entry with a missing or empty `actionAssignment` is skipped and a warning is emitted.

- Duplicate `actionAssignment` values across entries are warned — the platform coalesce key `[activity, action_assignment]` would silently merge them into one record.

- Duplicate `displayOrder` values across entries are warned — ambiguous button ordering at runtime.

```
import { ActivityDefinitions } from '@servicenow/sdk/automation'
import { wfa } from '@servicenow/sdk/automation'

const step = wfa.playbook.activity(
    ActivityDefinitions.Core.Instruction,
    {
        $id: Now.ID['act_step'],
        label: 'Final Step',
        order: 1,
        startRule: wfa.playbook.run.Immediately(),
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

Field notes:

- `name` — Optional internal name. If provided, it is used verbatim. If omitted, it is slugified from `label` and deduplicated across sibling activities within the same lane. The `name` is the activity's stable identity — once deployed, ideally do not change it on subsequent edits, as a changed `name` is treated as a new activity rather than an update to the existing one.

- `lane` — Automatically set to the parent lane's sys_id.

- `process_definition` — Automatically set to the playbook's sys_id.

- `active` — Defaults to `true`.

#### Decision Activity

The Decision activity evaluates an ordered list of branch conditions and routes execution to matching branches.

```
wfa.playbook.activity(
    ActivityDefinitions.Core.Decision,
    { $id: Now.ID['decision_route'], label: 'Route by Priority', order: 1, startRule: wfa.playbook.run.Immediately() },
    {
        type: 'match_first',    // 'match_first' | 'match_all'
        branches: [
            { id: 'critical', label: 'Critical', condition: `${wfa.playbook.dataPill(params.inputs.record.priority)}=1` },
            { id: 'high',     label: 'High',     condition: `${wfa.playbook.dataPill(params.inputs.record.priority)}=2` },
            { id: 'else',     label: 'Else' },   // ELSE branch - must be last, no condition
        ],
    },
)
```

DecisionInputs properties:

- 
type (required): `'match_first' | 'match_all'`
Branch selection mode. `match_first` runs only the first matching branch; `match_all` runs every matching branch in parallel.

- 
branches (required): `DecisionBranch[]`
Ordered list of branches. Branch display order follows array position.

DecisionBranch properties:

- 
id (required): `string`
Unique identifier within the decision. Used in `decision.branches.<id>` references in `wfa.playbook.run.After()`. `'else'` is reserved for the fallback branch.

- 
label (required): `string`
Display name. For the `else` branch this must be the exact string `'Else'`.

- 
condition (optional): `string`
Encoded query with optional data pills. Omit for the `else` branch.

- 
isIdealPath (optional): `boolean`
Marks this branch as the preferred branch at this decision. Defaults to `false`. The ideal branches across every decision together form the playbook's golden path — the end-to-end route highlighted on both of Playbook Designer's canvases, and intended to be the route the playbook follows at runtime. Requires the Process Automation Designer (`sn_pa_designer`) store app at version 29.6.4 or later — on earlier versions the flag is still written to the branch record but is ignored (no golden path UI, no runtime effect); the SDK doesn't validate the installed version. Two rules, both enforced as build-time errors:

- A `match_first` decision allows at most one ideal branch.

- `else` and the conditional branches are mutually exclusive at every decision type — mark one or more conditional branches, or `else`, never both.

ELSE branch: `id: 'else'`, `label: 'Else'` (exact string), must be the last entry in `branches`, no `condition`. May set `isIdealPath`, but not alongside a conditional branch.

Branch IDs are typed automatically in `wfa.playbook.run.After(...)`. See `playbook-anti-patterns-guide` for the `as const` convention and `playbook-guide` for branching examples.

#### Go Back Activity

The Go Back activity restarts the playbook at an earlier activity, an earlier stage (lane), or the start of the
playbook. It is only valid as the terminal activity of a `match_first` decision branch — see
`playbook-activities-guide#go-back` for the full set of build-time diagnostics this places on where it can go and
what it can target.

Requires the Process Automation Designer (`sn_pa_designer`) store app at version 29.3.0 or later — the
`sys_pd_activity_definition` record backing `ActivityDefinitions.Core.GoBack` doesn't exist on earlier versions, so
deploying a playbook that uses it against an older instance fails; the SDK doesn't validate the installed version.

```
wfa.playbook.activity(
    ActivityDefinitions.Core.GoBack,
    {
        $id: Now.ID['act_retry'],
        label: 'Retry',
        order: 3,
        startRule: wfa.playbook.run.After(router.branches.needs_retry),
        restartRule: 'RUN_ALWAYS',
    },
    {
        target_type: 'go_back_to_target_activity',
        go_back_to_target_activity: intake.review,
    },
)
```

GoBackInputs properties:

- 
target_type (required): `'go_back_to_target_activity' | 'go_back_to_target_stage' | 'start_of_playbook'`
Which of the other two fields (if any) supplies the jump target.

- 
go_back_to_target_activity (required when `target_type` is `'go_back_to_target_activity'`; absent
otherwise — enforced at the type level by `GoBackInputs`): a raw reference to the target activity's own
variable — the same-lane activity variable itself (e.g. `intake_review`), or a cross-lane dot-walk reference
(e.g. `intake.review`). The earlier activity to restart at.

- 
go_back_to_target_stage (required when `target_type` is `'go_back_to_target_stage'`; absent otherwise
— enforced at the type level by `GoBackInputs`): a raw reference to the target lane's own variable (e.g.
`intake`). The earlier stage (lane) to restart at.

Neither target field is set when `target_type` is `'start_of_playbook'`.

If the playbook sets `evaluateVariantChildrenAfter` (see `wfa.playbook.variant()` below)
and the Go Back's enclosing decision runs after that evaluation point, the target must also run after it — see
`playbook-activities-guide#go-back` rule 2.

#### Optional Activities

`wfa.playbook.run.Manually()` marks an activity as optional — it only runs if a user manually triggers it during a running playbook, and skipping it doesn't block the rest of the playbook. It's activity-only (not valid as a lane's `startRule`). When used, `order`, `conditionToRun`, `startWithDelay`, `variantOverrides`, and `variant` cannot be set, `restartRule` must be `'RUN_ONLY_ONCE'`, and nothing else may wait on it or reference it.

```
wfa.playbook.activity(
    ActivityDefinitions.Core.Instruction,
    {
        $id: Now.ID['act_escalate'],
        label: 'Escalate (Optional)',
        startRule: wfa.playbook.run.Manually(),
        restartRule: 'RUN_ONLY_ONCE',
    },
    { message: 'Escalate this case if needed.' },
)
```

See `playbook-activities-guide#optional-activities` for the full authoring guide, including lane-scoped vs. global placement.

#### VariantOverride

Overrides an activity's `startRule` and/or `order` when a specific variant is selected at runtime. Maps to a `sys_pd_activity_override` record.

```
interface VariantOverride {
    variant: VariantReference
    startRule?: ActivityExecutionRule
    order?: number
}
```

Properties:

- 
variant (required): `VariantReference`
The variant this override applies within. Reference it directly as `params.variants.<name>` — see params.variants.* under PlaybookBodyParams above.

- 
startRule (optional): `ActivityExecutionRule`
Overrides this activity's execution rule when `variant` is selected. Omit to leave the base `startRule` unchanged for that variant.

- 
order (optional): `number`
Overrides this activity's display order when `variant` is selected. Omit to leave the base `order` unchanged for that variant.

Setting `startRule`/`order` is optional, but an entry that sets neither has no effect — it's a no-op, not an error, and triggers a non-blocking diagnostic warning rather than a build failure.

```
// Inside a lane's `activities` callback.
const activity_review = wfa.playbook.activity(ActivityDefinitions.Core.Placeholder, {
    $id: Now.ID['act_review'],
    label: 'Review',
    order: 2,
    startRule: wfa.playbook.run.Immediately(),
    restartRule: 'RUN_ONLY_ONCE',
    // Overrides start rule/order only when the VIP variant is selected.
    variantOverrides: [{ variant: params.variants.variant_vip, order: 1 }],
})
```

`startRule` in an override isn't limited to `Run.Immediately()` — it can be any `ActivityExecutionRule`, including `Run.After()` with a real predecessor:

```
// Normally starts right after `activity_review`, but for the VIP variant it
// waits on `activity_vip_check` instead.
const activity_close = wfa.playbook.activity(ActivityDefinitions.Core.Placeholder, {
    $id: Now.ID['act_close'],
    label: 'Close',
    order: 3,
    startRule: wfa.playbook.run.After(activity_review),
    restartRule: 'RUN_ONLY_ONCE',
    variantOverrides: [{ variant: params.variants.variant_vip, startRule: wfa.playbook.run.After(activity_vip_check) }],
})
```

An override's `Run.After()` dependency can reference an activity declared later in the same lane — including an activity whose base `startRule` depends on the very activity being overridden here, effectively reversing that edge for the selected variant. A plain variable reference can't express this without violating declaration order (the later activity's `const` doesn't exist yet at this point in the file), so use `wfa.playbook.activityRef(Now.ID[...])` instead — it resolves by id, so declaration order doesn't matter:

```
// Base: activity_close waits on activity_review (declared below). For the VIP
// variant, that's reversed — activity_review instead waits on activity_close,
// which is declared later in this lane, so it's referenced via activityRef()
// rather than the (not-yet-declared) `activity_close` variable.
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
    // For the VIP variant, activity_review now waits on activity_close (see above) — so
    // activity_close must stop waiting on activity_review for that variant, or the two
    // deadlock on each other. Point it at a different real predecessor instead.
    variantOverrides: [
        { variant: params.variants.variant_vip, startRule: wfa.playbook.run.After(activity_vip_check) },
    ],
})
```

Reversing the direction like this means, for the VIP variant, `activity_close`'s own base `startRule` (waiting on `activity_review`) is now also on the other side of the same edge — as shown above, give `activity_close` its own `variantOverrides` entry to point it elsewhere for that variant, or the two will deadlock on each other.

#### Variant-Only Activities

Setting an activity's `variant` field scopes it to exist only within that variant (maps to `sys_pd_activity.variant`) — it's omitted entirely from the playbook when a different variant (or the base playbook) is selected. Omit `variant` for a base activity shared across all variants.

```
const activity_vip_greeting = wfa.playbook.activity(ActivityDefinitions.Core.Placeholder, {
    $id: Now.ID['act_vip_greeting'],
    label: 'VIP Greeting',
    order: 1,
    startRule: wfa.playbook.run.Immediately(),
    restartRule: 'RUN_ONLY_ONCE',
    variant: params.variants.variant_vip,
})
```

When `evaluateVariantChildrenAfter` is set (see PlaybookConfig above), every variant-only activity must be a guaranteed descendant of that evaluation point, given the playbook's lane/activity `Run.After` ordering — otherwise it's a build-time diagnostic error. This is separate from the condition-pill ancestor check described under wfa.playbook.variant() below: that one checks what a variant's `condition` may reference; this one checks where a variant-only activity itself may be placed. The check is skipped entirely when `evaluateVariantChildrenAfter` is unset, since variants are then evaluated at playbook start and every activity trivially satisfies it. See `playbook-activities-guide#variant-overrides-and-variant-only-activities` for the full authoring guide.

### wfa.playbook.variant()

Creates a variant. Variants let a playbook branch on a condition that applies playbook-wide (not to a specific lane or activity), and can be arranged in a parent/child hierarchy. Evaluation is top-down and hierarchical: a child variant's `condition` is only ever evaluated if its parent's `condition` already matched — the runtime walks the tree from the base, at each level picking the first (lowest `order`) child whose `condition` is true, and stops at whichever level fails to find a matching child. The first variant matched wins; no other variants at that level are evaluated. So a child's `condition` does not need to restate its parent's logic (the parent match is already guaranteed by the time the child is reached), but it is also never reachable on its own — if the parent's `condition` is false, the child is skipped without being evaluated at all. Takes a flat `VariantConfig` object directly — there is no `activities` callback.

```
wfa.playbook.variant(config: VariantConfig): VariantDefinition & VariantReference
```

```
variants: (params) => ({
    approved: wfa.playbook.variant({
        $id: Now.ID['variant_approved'],
        label: 'Approved',
        condition: `${wfa.playbook.dataPill(params.inputs.record.approved)}=true`,
        order: 1,
    }),
})
```

Data pills in `condition` may only reference `params.inputs` or `params.parentRecord` by default — a variant can't reference activity output, since it isn't tied to a specific point in the flow. Setting `evaluateVariantChildrenAfter` on the playbook config (see PlaybookConfig above) widens this: once set, variant conditions may also reference the output of any activity guaranteed to have completed before that point (an "ancestor" of the evaluation point), via `wfa.playbook.activityRef(Now.ID[...]).outputs.<field>` — see the deferred-evaluation-point example below. Referencing an activity that isn't a guaranteed ancestor of the evaluation point is a build-time diagnostic error, as is setting `evaluateVariantChildrenAfter` without declaring at least one variant.

Declaring any variant requires `parentTable` on the playbook config. This is a build-time diagnostic error. A missing lane is also flagged, but only as a warning (lanes can be added later).

#### VariantConfig

```
interface VariantConfig {
    $id: Now.Internal.ExplicitKey | string | number
    label: string
    name?: string
    description?: string
    condition: string
    order: number
    color?: VariantColor
    parentVariant?: VariantReference
}
```

Properties:

- 
$id (required): `Now.Internal.ExplicitKey | string | number`
Unique identifier.

- 
label (required): `string`
Display name shown in Playbook Designer. Also used to auto-generate `name`.

- 
condition (required): `string`
Encoded query evaluated at runtime to decide whether this variant applies. Use `wfa.playbook.dataPill()` to interpolate `params.inputs` or `params.parentRecord` values. Unlike a lane/activity's `conditionToRun`, this is mandatory — the platform's `PROCESS_VARIANT_MISSING_CONDITION` rule requires every variant to have one.

- 
order (required): `number`
Sibling display order in the variant tree.

- 
name (optional): `string`
Internal name. If provided, used verbatim; otherwise slugified from `label`.

- 
description (optional): `string`
Optional description.

- 
color (optional): `VariantColor` (one of `'blue' | 'brown' | 'green' | 'magenta' | 'orange' | 'purple' | 'teal' | 'yellow'`)
Display color shown in Playbook Designer. If omitted, one of the 8 values is auto-assigned.

- 
parentVariant (optional): `VariantReference`
Reference to another variant definition, establishing this variant as its child in the variant hierarchy. The runtime only evaluates this variant's `condition` if the parent's `condition` already matched. Set directly to a sibling variant variable declared in the same `variants` callback:

```
variants: () => {
    const variant_vip = wfa.playbook.variant({
        $id: Now.ID['variant_vip'],
        label: 'VIP Customer',
        condition: 'priority=1',
        order: 1,
    })
    const variant_vip_critical = wfa.playbook.variant({
        $id: Now.ID['variant_vip_critical'],
        label: 'VIP Critical',
        condition: 'severity=1',
        order: 1,
        parentVariant: variant_vip,
    })
    return { variant_vip: variant_vip, variant_vip_critical: variant_vip_critical }
}
```

Activity-level overrides and variant-only activities reference a variant from an activity config via `params.variants.<name>` — see VariantOverride and Variant-Only Activities above, and params.variants.* under PlaybookBodyParams above. Variants are declared in the 2nd-arg `variants` callback (alongside `triggers`; see variants above), so `params.variants.<name>` is available from the 3rd-arg `body`'s `lanes`/`activities` callbacks directly:

```
PlaybookDefinition(
    { /* config */ },
    {
        triggers: [],
        variants: (params) => ({
            variant_vip: wfa.playbook.variant({
                $id: Now.ID['variant_vip'],
                label: 'VIP',
                condition: `${wfa.playbook.dataPill(params.inputs.record.priority)}=1`,
                order: 1,
            }),
        }),
    },
    {
        lanes: () => ({
            lane_0: wfa.playbook.lane({
                config: { ... },
                activities: (params) => ({
                    act_1: wfa.playbook.activity(ActivityDefinitions.Core.RecordForm, {
                        $id: Now.ID['act_1'],
                        label: 'VIP-only step',
                        order: 1,
                        startRule: wfa.playbook.run.Immediately(),
                        restartRule: 'RUN_ONLY_ONCE',
                        variant: params.variants.variant_vip,
                    }),
                }),
            }),
        }),
    }
)
```

### wfa.playbook.run Namespace

Execution rule helpers used in `startRule` properties on lane and activity configs. Accessed via the `wfa` namespace imported from `@servicenow/sdk/automation`.

```
import { wfa } from '@servicenow/sdk/automation'
```

#### wfa.playbook.run.Immediately()

Activity or lane starts immediately with no dependencies.

```
wfa.playbook.run.Immediately(): ExecutionRule
```

Use for the first activity in a lane or the first lane in a playbook.

#### wfa.playbook.run.After(...deps)

Activity or lane starts after all specified dependencies complete.

```
wfa.playbook.run.After(...deps: Dependency[]): ExecutionRule
```

Accepts varargs (not an array). Each argument can be an `ActivityInstance`, `ActivityReference`, `LaneReference`, or `BranchReference`.

```
// Single dependency
startRule: wfa.playbook.run.After(validate)

// Multiple dependencies (all must complete)
startRule: wfa.playbook.run.After(notify, log)

// Lane-level dependency
config: { ..., startRule: wfa.playbook.run.After(intake) }

// Branch dependency (Decision activity)
startRule: wfa.playbook.run.After(routeCase.branches.critical)
```

#### wfa.playbook.run.Manually()

Activity only — starts only when a user manually triggers it during a running playbook (an "optional activity"). See Optional Activities above.

```
wfa.playbook.run.Manually(): ManualActivityExecutionRule
```

### wfa.playbook.dataPill()

Creates runtime references to playbook data for use in trigger mappers, activity inputs, experience properties, conditions, and timer fields.

```
wfa.playbook.dataPill(reference: DataReference): string
```

See `playbook-datapills-guide` for additional details on usage, what is allowed in pills, and where pills are allowed.

## Type Definitions

### Run Namespace

```
declare namespace Run {
    function Immediately(): LaneExecutionRule & ActivityExecutionRule
    function After(...deps: Dependency[]): LaneExecutionRule & ActivityExecutionRule
    function Manually(): ManualActivityExecutionRule
}
```

`Immediately()`/`After()` return a value assignable to either `LaneConfig.startRule` or `ActivityConfig.startRule`. `Manually()` returns a distinct `ManualActivityExecutionRule` (see below) — activity-only, assignable only to `ManualActivityConfig.startRule`.

### ExecutionRule

```
interface LaneExecutionRule {
    readonly __laneExecutionRule: true
}

interface ActivityExecutionRule {
    readonly __activityExecutionRule: true
}

type ExecutionRule = LaneExecutionRule | ActivityExecutionRule
```

### ManualActivityExecutionRule

```
interface ManualActivityExecutionRule {
    readonly __manualActivityExecutionRule: true
}
```

Deliberately not part of `ExecutionRule` — incompatible with `LaneConfig.startRule` and `ActivityConfig.startRule` by design, so `Run.Manually()` can only be used with `ManualActivityConfig`.

### Dependency

```
type Dependency = ActivityInstance<any> | ActivityReference | LaneReference | BranchReference
```

### ActivityInstance

```
interface ActivityInstance<TBranches = never> extends ActivityReference {
    readonly branches: TBranches
}
```

`outputs`, `state`, and `sysId` come from `ActivityReference`. `branches` is `never` for non-Decision activities and a record of typed `BranchReference`s for Decision activities.

### ActivityReference

```
interface ActivityReference {
    readonly __activityRef: true
    readonly outputs: any
    readonly state: string
    readonly sysId: string
}
```

### LaneReference

```
interface LaneReference {
    readonly __laneRef: true
}
```

### VariantReference

```
interface VariantReference {
    readonly __variantRef: true
}
```

### BranchReference

```
interface BranchReference {
    readonly __branchRef: true
    readonly id: string
}
```

### PlaybookTriggerTypes Namespace

```
namespace PlaybookTriggerTypes {
    const RecordCreate: PlaybookTriggerType
    const RecordUpdate: PlaybookTriggerType
    const RecordCreateOrUpdate: PlaybookTriggerType
    const Scheduled: PlaybookTriggerType
}
```

### ActivityDefinitions Namespace

```
namespace ActivityDefinitions {
    namespace Core {
        // Interactive
        const Instruction: ActivityDefinition
        const TwoStepInstruction: ActivityDefinition
        const RecordForm: ActivityDefinition
        const NewRecordForm: ActivityDefinition
        const AutocompletingRecordForm: ActivityDefinition
        const KnowledgeArticle: ActivityDefinition
        const ChecklistTask: ActivityDefinition

        // Automation
        const UpdateRecord: ActivityDefinition
        const CreateNewRecord: ActivityDefinition
        const NewRecordFormWithList: ActivityDefinition
        const SendEmail: ActivityDefinition
        const EmailForm: ActivityDefinition
        const WaitForCondition: ActivityDefinition
        const Placeholder: ActivityDefinition
        const SetPlaybookOutputs: ActivityDefinition

        // Approval
        const RequestManagerApproval: ActivityDefinition
        const RequestAdHocApproval: ActivityDefinition
        const AskForMultiLevelApproval: ActivityDefinition

        // Branching
        const Decision: DecisionActivityDefinition

        // Control flow
        const GoBack: ActivityDefinition

        // List
        const RecordList: ActivityDefinition
    }
}
```

Definition source: `src/api/playbook/built-ins/activity-definitions/index.ts`.

## Data Model Mapping

| Fluent Concept | ServiceNow Table | Key Fields |
| `PlaybookDefinition` config | `sys_pd_process_definition` | label, name, description, status, run_strategy, etc. |
| `wfa.playbook.trigger()` | `sys_pd_trigger_instance` | trigger_type, trigger_inputs |
| Lane | `sys_pd_lane` | label, name, order, description, start_rule_name, starts_after_lanes, condition_to_run, restart_rule, permission |
| `wfa.playbook.variant()` | `sys_pd_process_variant` | label, name, description, condition, order, color, parent_variant, process_definition |
| Lane or Activity `startWithDelay` | `sys_pd_timer_attributes` | source (FK to lane or activity), source_type ( `sys_pd_lane` or `sys_pd_activity` ), duration_type, timer_duration, timer_relative_duration_datetime, etc. |
| `wfa.playbook.activity()` config | `sys_pd_activity` | activity_definition, label, name, order, lane (auto-set), process_definition (auto-set), start_rule, variant, enable_ai_agent, ai_agent_objective, ai_agent_obj_additional_detail, ai_agent_execution_mode, ai_agent_run_with_roles, ai_agent_supported_actions, ai_agent_run_as, conversational_agents, etc. |
| `wfa.playbook.activity()` `actionOverrides` | `sys_pd_activity_action_override` | activity, action_assignment, label, display_order |
| `ActivityConfig.variantOverrides[]` | `sys_pd_activity_override` | override_parent (FK to the base activity), variant, order, start_rule |
| `wfa.playbook.activity()` inputs/experienceProperties | `sys_variable_value` | document, document_key, variable, value |
| `wfa.playbook.dataPill()` in inputs/experienceProperties | `sys_element_mapping` | field, id, table, value |
| `inputs` | `sys_pd_process_input` | (extends var_dictionary) |
| `outputs` | `sys_pd_process_output` | (extends var_dictionary) |
| `launcherInputs` | `sys_variable_value` | document ( `sys_pd_process_definition` ), document_key (playbook sys_id), variable ( `sys_pd_process_input` sys_id), value |
| (preserved automatically, no Fluent config) | `sys_attachment` , `sys_attachment_doc` | An existing image attachment on the process definition is not settable through Fluent, but is preserved across pull/build round trips. See Image Attachments . |

## See

- ServiceNow Playbook Documentation

## Examples

### Example with 1 trigger

```
import { PlaybookDefinition, PlaybookTriggerTypes, ActivityDefinitions } from '@servicenow/sdk/automation'
import { wfa } from '@servicenow/sdk/automation'
import { ReferenceColumn, StringColumn, BooleanColumn, IntegerColumn } from '@servicenow/sdk/core'

PlaybookDefinition(
    {
        $id: Now.ID['p1_incident_notes'],
        label: 'P1 Incident Notes',
        name: 'p1_incident_notes',
        parentTable: 'incident',
        inputs: {
            // requestedBy is mandatory and has no default, so the on-demand launcher requires
            // a launcherInputs value for it — otherwise this playbook fails to build.
            requestedBy: ReferenceColumn({
                label: 'Requested By',
                referenceTable: 'sys_user',
                mandatory: true,
            }),
            notes: StringColumn({
                label: 'Notes',
                maxLength: 1000,
                default: 'Standard priority note',
            }),
            isUrgent: BooleanColumn({
                label: 'Is Urgent',
                default: false,
            }),
            retryCount: IntegerColumn({
                label: 'Retry Count',
                default: 0,
            }),
        },
        launcherTitle: 'Submit a request',
        launcherDescription: 'Fill out the form to start this playbook.',
        launcherShowRecordForm: true,
        launcherRecordFormView: 'Default view',
        launcherTemplateFields: TemplateValue({ active: true, assignment_group: '019ad92ec7230010393d265c95c260dd' }),
        launcherInputs: {
            // Satisfies the mandatory requestedBy input — a sys_id string, or a typed
            // Record<'sys_user'> reference, both resolve the same way.
            requestedBy: '62826bf03710200044e0bfc8bcbe5db4',
            // notes overrides its own default ('Standard priority note') in the launcher.
            notes: 'Priority 1 received',
            // BooleanColumn and IntegerColumn inputs also take a string here — 'true'/'3',
            // never a raw true/3 literal (that fails to compile).
            isUrgent: 'true',
            retryCount: '3',
        },
    },
    {
        triggers: [
            wfa.playbook.trigger(
                PlaybookTriggerTypes.RecordCreate,
                { $id: Now.ID['p1_trig'], label: 'On P1 Incident' },
                { table: 'incident', condition: 'priority=1' }
            ),
        ],
    },
    {
        lanes: (params) => ({
            stamp_note: wfa.playbook.lane({
                config: {
                    $id: Now.ID['p1_lane'],
                    label: 'Stamp Note',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => {
                    const stamp = wfa.playbook.activity(
                        ActivityDefinitions.Core.UpdateRecord,
                        {
                            $id: Now.ID['p1_act'],
                            label: 'Stamp Note',
                            order: 1,
                            startRule: wfa.playbook.run.Immediately(),
                            restartRule: 'RUN_ONLY_ONCE',
                        },
                        {
                            table_name: 'incident',
                            record: wfa.playbook.dataPill(params.parentRecord),
                            values: TemplateValue({ work_notes: 'Priority 1 received'}),
                        }
                    )
                    return { stamp: stamp }
                },
            }),
        }),
    }
)
```

### Example with 1 trigger and inputs and outputs

```
import { PlaybookDefinition, PlaybookTriggerTypes, ActivityDefinitions } from '@servicenow/sdk/automation'
import { wfa } from '@servicenow/sdk/automation'
import { ReferenceColumn, IntegerColumn, StringColumn } from '@servicenow/sdk/core'

PlaybookDefinition(
    {
        $id: Now.ID['p1_incident_notes_with_inputs_outputs'],
        label: 'P1 Incident Notes with Inputs and Outputs',
        name: 'p1_incident_notes_inputs_outputs',
        parentTable: 'incident',
        inputs: {
          record: ReferenceColumn({
              label: 'Record',
              referenceTable: 'incident',
              mandatory: true,
          }),
          priority: IntegerColumn({
              label: 'Priority Override',
              default: 3,
          }),
          summary: StringColumn({
              label: 'Summary',
              maxLength: 1000,
          }),
        },
        outputs: {
          resolvedBy: ReferenceColumn({
              label: 'Resolved By',
              referenceTable: 'sys_user',
          }),
          closureCode: StringColumn({
              label: 'Closure Code',
              maxLength: 40,
          }),
      },
    },
    {
        triggers: [
            wfa.playbook.trigger(
                PlaybookTriggerTypes.RecordCreate,
                { $id: Now.ID['p2_trig_inp_out'], label: 'On P2 Incident Creation' },
                { table: 'incident', condition: 'priority=2' }
            ),
        ],
    },
    {
        lanes: (params) => ({
            stamp_note: wfa.playbook.lane({
                config: {
                    $id: Now.ID['p2_lane'],
                    label: 'Stamp Note',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => {
                    const stamp = wfa.playbook.activity(
                        ActivityDefinitions.Core.UpdateRecord,
                        {
                            $id: Now.ID['p2_act'],
                            label: 'Stamp Note',
                            order: 1,
                            startRule: wfa.playbook.run.Immediately(),
                            restartRule: 'RUN_ONLY_ONCE',
                        },
                        {
                            table_name: 'incident',
                            record: wfa.playbook.dataPill(params.parentRecord),
                            values: TemplateValue({ work_notes: 'Priority 2 incident received'}),
                        }
                    )
                    return { stamp: stamp }
                },
            }),
        }),
    }
)
```

Version: 4.14.0

# Playbook Triggers Guide

Practical guide to the trigger types that can start a playbook — covers record-driven triggers (`RecordCreate`, `RecordUpdate`, `RecordCreateOrUpdate`), the time-based `Scheduled` trigger, all their inputs, and how `parentRecord` works when the trigger table differs from the playbook's `parentTable`. For the underlying `wfa.playbook.trigger` signature see `playbook-api`.

## When to Use

- You need to fire a playbook when a record is created, updated, or both

- You need to run a playbook on a time-based schedule (daily, weekly, monthly, etc.)

- You need to map trigger data to declared playbook inputs

- You need to configure `parentRecord` when the trigger table differs from the playbook's `parentTable`

- You need to filter which records start the playbook using an encoded query `condition`

## Trigger call shape

A trigger is created with `wfa.playbook.trigger(triggerType, config, triggerInputs, playbookInputs?)`. The fourth argument maps trigger data to declared playbook inputs and `parentRecord`. Omit it when the playbook has no declared inputs and the trigger table matches the playbook's `parentTable`; if the playbook has any mandatory inputs, the mapper must provide them.

```
import { wfa, PlaybookTriggerTypes } from '@servicenow/sdk/automation'

const trigger = wfa.playbook.trigger(
    PlaybookTriggerTypes.RecordCreate,
    { $id: Now.ID['trig_incident_create'], label: 'On Incident Created' },
    { table: 'incident', condition: 'priority<=2^active=true' },
)
```

`PlaybookTriggerTypes` and `wfa` are both imported from `@servicenow/sdk/automation`. A playbook can have multiple triggers — any one of them can start the playbook. Each trigger needs a unique `$id`.

## Mapping trigger data to playbook inputs (playbookInputs)

The playbook declares input values it needs via the `inputs` schema in the config. When a trigger fires, it needs to supply values for those inputs so the playbook can start with the necessary data. The fourth argument to `wfa.playbook.trigger()` — called the trigger mapper — is how you wire trigger data (or hardcoded values) into the playbook's declared inputs.

For example, if the playbook declares an input named `priority`, the trigger mapper must provide a value for it. You can pull that value from the triggering record (e.g., `trigger.current.priority`) or hardcode a static value (e.g., `'high'`). When the trigger fires, the mapper executes and populates all the declared inputs, allowing the playbook to launch with the data it needs.

### End-to-end example with declared inputs

This example shows all three pieces together: the playbook declares `inputs`, the trigger mapper populates them, and the body consumes them via `params.inputs.*`.

```
import {
    ActivityDefinitions,
    PlaybookDefinition,
    PlaybookTriggerTypes,
    wfa,
} from '@servicenow/sdk/automation'
import {
    Now,
    ReferenceColumn,
    StringColumn,
} from '@servicenow/sdk/core'

PlaybookDefinition(
    {
        $id: Now.ID['incident_triage'],
        label: 'Incident Triage',
        inputs: {
            record: ReferenceColumn({
                label: 'Record',
                referenceTable: 'incident',
                mandatory: true,
            }),
            summary: StringColumn({
                label: 'Summary',
                mandatory: true,
            }),
        },
    },
    {
        triggers: [
            wfa.playbook.trigger(
                PlaybookTriggerTypes.RecordCreate,
                { $id: Now.ID['trig_incident_create'], label: 'On Incident Created' },
                { table: 'incident' },
                (trigger) => ({
                    record: wfa.playbook.dataPill(trigger.current),
                    summary: wfa.playbook.dataPill(trigger.current.short_description),
                }),
            ),
        ],
    },
    {
        lanes: (params) => ({
            intake: wfa.playbook.lane({
                config: {
                    $id: Now.ID['lane_intake'],
                    label: 'Intake',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                },
                activities: () => {
                    const notify = wfa.playbook.activity(
                        ActivityDefinitions.Core.SendEmail,
                        {
                            $id: Now.ID['act_notify'],
                            label: 'Notify',
                            order: 1,
                            startRule: wfa.playbook.run.Immediately(),
                        },
                        {
                            recipient: wfa.playbook.dataPill(params.inputs.record.assigned_to.email),
                            body: wfa.playbook.dataPill(params.inputs.summary),
                        },
                    )
                    return { notify: notify }
                },
            }),
        }),
    },
)
```

The mapper keys (`record`, `summary`) match the input names declared on `config.inputs`, and those same names are what surface later on `params.inputs`.

### Basic field mapping

Use `wfa.playbook.dataPill(...)` to pull values from the triggering record. Provide `trigger` as the arrow-function parameter whenever the mapper reads from `trigger.current`:

```
wfa.playbook.trigger(
    PlaybookTriggerTypes.RecordCreate,
    { $id: Now.ID['trig_incident_create'], label: 'On Incident Created' },
    { table: 'incident' },
    (trigger) => ({
        record: wfa.playbook.dataPill(trigger.current),
        priority: wfa.playbook.dataPill(trigger.current.priority),
    })
)
```

### Whole-record pill

Pass the entire triggering record into an input by omitting the field path:

```
wfa.playbook.trigger(
    PlaybookTriggerTypes.RecordCreate,
    { $id: Now.ID['trig_incident_create'], label: 'On Incident Created' },
    { table: 'incident' },
    (trigger) => ({
        incidentRecord: wfa.playbook.dataPill(trigger.current),
    })
)
```

### Hardcoded values only

If every mapped value is hardcoded, omit the parameter with `() =>`:

```
wfa.playbook.trigger(
    PlaybookTriggerTypes.RecordCreate,
    { $id: Now.ID['trig_incident_create'], label: 'On Incident Created' },
    { table: 'incident' },
    () => ({
        status: 'In Progress',
    })
)
```

### Mixed pill and hardcoded values

If any value uses `dataPill`, use `(trigger) =>`:

```
(trigger) => ({
    priority: wfa.playbook.dataPill(trigger.current.priority),
    status: 'In Progress',
})
```

The parameter name `trigger` is required when `dataPill` references appear in the body — it is the object that exposes `trigger.current`. Use `()` when all values are hardcoded. The transform (XML → Fluent) mirrors this: `(trigger)` if any field is a pill, `()` if all are hardcoded.

### Template literal interpolation

Compose a string from multiple record fields by using template literals with embedded `wfa.playbook.dataPill(...)` calls:

```
(trigger) => ({
    title: `INC ${wfa.playbook.dataPill(trigger.current.number)}: ${wfa.playbook.dataPill(trigger.current.short_description)}`,
})
```

### Multi-level dot-walk

Reference fields on related records by chaining through reference columns:

```
(trigger) => ({
    assigneeEmail: wfa.playbook.dataPill(trigger.current.assigned_to.email),
})
```

When the trigger table is registered in `keys.ts`, `trigger.current` autocompletes the table's columns and supports reference-field dot-walk with typed completion up to 3 levels deep. Deeper paths still serialize correctly but lose column-level autocomplete past the third level.

### Mapper typing and validation

The mapper gets type-checked on both sides:

- Right side — `trigger.current.<field>` autocompletes columns from the trigger's table. Misspelled columns are flagged when the table is registered in `keys.ts`.

- Left side — mapper keys are constrained to the playbook's declared `inputs` schema. Using an undeclared key produces a TypeScript error, and required (`mandatory: true`) inputs must be present in the returned object.

### Mapper validation rules

The build validates the mapper and will flag these issues:

- Mapper key is not a declared playbook input — `"<key>" is not a declared playbook input`

- Mapper value is not a `wfa.playbook.dataPill(...)`, template literal, or hardcoded literal — `Mapper values must be wfa.playbook.dataPill() calls, template literals, or hardcoded values`

- Required (`mandatory: true`) input is not mapped — `Required playbook input "<name>" is not mapped...`

- `trigger.current.<field>` references a field that does not exist on the trigger's table (when the table is registered in `keys.ts`) — `Field "<field>" does not exist on table "<table>"`

## Record Triggers

| Trigger | Fires when |
| `PlaybookTriggerTypes.RecordCreate` | A new record is created |
| `PlaybookTriggerTypes.RecordUpdate` | An existing record is modified |
| `PlaybookTriggerTypes.RecordCreateOrUpdate` | A record is created or modified |

### RecordCreate inputs

| Input | Required | Type | Description |
| `table` | Yes | string | Table to monitor (e.g., `'incident'` ) |
| `condition` | No | string | Encoded query filter |
| `runTriggerOnExtendedTables` | No | boolean | Include child/extended tables |
| `parentRecord` | No | string | Sys_id of parent record (see `parentRecord` below) |

### RecordUpdate inputs

`RecordUpdate` adds one field on top of the create inputs:

| Input | Required | Type | Description |
| `triggerOnUniqueChange` | No | boolean | Fire only on unique field-value changes |

### RecordCreateOrUpdate inputs

Same inputs as `RecordUpdate` — includes `triggerOnUniqueChange`, and all the create inputs.

### Examples

Single trigger — incident created with priority 1:

```
import { wfa, PlaybookTriggerTypes } from '@servicenow/sdk/automation'

const declarations = {
    triggers: [
        wfa.playbook.trigger(
            PlaybookTriggerTypes.RecordCreate,
            { $id: Now.ID['trig_incident_create'], label: 'On Incident Created' },
            { table: 'incident', condition: 'priority=1' },
        ),
    ],
}
```

Update trigger — fire only on unique changes to in-progress tasks:

```
import { wfa, PlaybookTriggerTypes } from '@servicenow/sdk/automation'

const declarations = {
    triggers: [
        wfa.playbook.trigger(
            PlaybookTriggerTypes.RecordUpdate,
            { $id: Now.ID['trig_task_update'], label: 'On Task Updated' },
            {
                table: 'task',
                condition: 'state=2',
                triggerOnUniqueChange: true,
            },
        ),
    ],
}
```

Multiple triggers — create or update on the same table:

```
import { wfa, PlaybookTriggerTypes } from '@servicenow/sdk/automation'

const declarations = {
    triggers: [
        wfa.playbook.trigger(
            PlaybookTriggerTypes.RecordCreate,
            { $id: Now.ID['trig_create'], label: 'On Created' },
            { table: 'incident' },
        ),
        wfa.playbook.trigger(
            PlaybookTriggerTypes.RecordUpdate,
            { $id: Now.ID['trig_update'], label: 'On Updated' },
            { table: 'incident' },
        ),
    ],
}
```

### parentRecord

When a playbook sets `parentTable` and a trigger's `table` is a different table, supply `parentRecord` in the trigger's mapper. This tells the platform which record on `parentTable` the trigger should link to. `parentRecord` is a special key, do not declare it as a playbook input.

```
import { PlaybookDefinition, wfa, PlaybookTriggerTypes } from '@servicenow/sdk/automation'

PlaybookDefinition(
    {
        $id: Now.ID['ci_workflow'],
        label: 'CI Workflow',
        parentTable: 'incident',
    },
    {
        triggers: [
            wfa.playbook.trigger(
                PlaybookTriggerTypes.RecordCreate,
                { $id: Now.ID['ci_trigger'], label: 'On CMDB CI Create' },
                {
                    table: 'cmdb_ci',
                },
                (trigger) => ({
                    parentRecord: wfa.playbook.dataPill(trigger.current.correlation_id),
                })
            ),
        ],
    },
    { lanes: () => ({}) },
)
```

When the trigger's `table` matches the playbook's `parentTable`, `parentRecord` is not needed — the platform automatically links the triggering record as the parent.

### parentRecord validation rules

The build validates the parentRecord and will flag these issues:

- Declaring `parentRecord` or `parent_record` as a playbook input — `"parentRecord/parent_record is a reserved input name. Use parentRecord in the input mapper to set the parent record instead.`

- `parentRecord` not mapped when trigger table differs from `parentTable` - `Trigger table differs from playbook parentTable. parentRecord is required in the trigger's mapper callback.`

- Mapping `parentRecord` to anything other than a record reference or a raw sys_id — `parentRecord must be a bare wfa.playbook.dataPill() call or a plain sys_id string.`

- Mapping `parentRecord` to the trigger record itself — `parentRecord should not be the trigger record when the trigger table differs from the playbook parentTable.`

- Mapping `parentRecord` when the trigger table matches the `parentTable` — `parentRecord should not be specified when the trigger table matches the playbook parentTable.`

## Scheduled Trigger

`PlaybookTriggerTypes.Scheduled` fires the playbook on a time-based schedule. Unlike record triggers, the scheduled trigger has no "current" record — it processes records matching the trigger's `condition` up to a row `limit` on each run.

### Common fields

All scheduled triggers share these inputs regardless of `recurrence`:

| Field | Required | Type | Description |
| `table` | Yes | string | Table context for the scheduled run |
| `limit` | Yes | number | Max records to process per run (1–1000) |
| `startDateAndTime` | Yes | string | When the schedule begins ( `'yyyy-MM-dd HH:mm:ss'` ) |
| `recurrence` | Yes | string | Schedule type (see below) |
| `condition` | No | string | Encoded query filter for record selection |
| `timeZone` | No | string | e.g., `'America/Los_Angeles'` ; default is `'floating'` (system time zone) |

### Recurrence types

#### `'once'`

Runs a single time at `startDateAndTime`. No additional fields.

```
const opts = { table: 'incident', recurrence: 'once', limit: 100, startDateAndTime: '2026-05-15 14:00:00' }
```

#### `'daily'`

Repeats every N days.

| Field | Required | Description |
| `frequency` | Yes | Interval — e.g., `2` = every 2 days |

```
const opts = {
    table: 'incident',
    recurrence: 'daily',
    frequency: 1,
    limit: 500,
    startDateAndTime: '2026-04-01 08:00:00',
    end: 'no_end_date',
}
```

#### `'weekly'`

Repeats on selected days of the week.

| Field | Required | Description |
| `frequency` | Yes | Interval — e.g., `2` = every 2 weeks |
| `daysOfTheWeek` | Yes | Concatenated digit codes: `1` =Mon, `2` =Tue, …, `7` =Sun |

`daysOfTheWeek` is a string of concatenated digits with no separator. `'15'` = Monday and Friday. `'12345'` = weekdays.

```
const opts = {
    table: 'incident',
    recurrence: 'weekly',
    frequency: 1,
    daysOfTheWeek: '15',
    limit: 500,
    startDateAndTime: '2026-04-01 08:00:00',
    end: 'no_end_date',
}
```

#### `'monthly'`

Repeats on a specific day each month. Uses the `daySelection` discriminator (see Monthly day selection).

| Field | Required | Description |
| `frequency` | Yes | Interval — e.g., `2` = every 2 months |

```
const opts = {
    table: 'incident',
    recurrence: 'monthly',
    frequency: 1,
    daySelection: 'fixed_day',
    dayOfMonth: 1,
    limit: 500,
    startDateAndTime: '2026-04-01 09:00:00',
    timeZone: 'America/Los_Angeles',
    end: 'no_end_date',
}
```

#### `'yearly'`

Repeats on a specific day within a specific month each year. Uses `daySelection` like monthly.

| Field | Required | Description |
| `repeatMonth` | Yes | Month of the year (1=Jan, 12=Dec) |

```
const opts = {
    table: 'incident',
    recurrence: 'yearly',
    repeatMonth: 4,
    daySelection: 'fixed_day',
    dayOfMonth: 15,
    limit: 500,
    startDateAndTime: '2026-04-15 09:00:00',
    end: 'no_end_date',
}
```

#### `'periodically'`

Repeats at a custom duration interval.

| Field | Required | Description |
| `repeat` | Yes | Duration between repeats. Accepts `{ days?, hours?, minutes?, seconds? }` (preferred) or the equivalent platform string format |

```
const opts = {
    table: 'incident',
    recurrence: 'periodically',
    repeat: { days: 2, hours: 6 },
    limit: 500,
    startDateAndTime: '2026-04-01 09:00:00',
    end: 'no_end_date',
}
```

### End conditions

All recurring triggers (`daily`, `weekly`, `monthly`, `yearly`, `periodically`) support an optional end condition:

| `end` value | Additional field | Description |
| `'no_end_date'` | — | Repeats indefinitely |
| `'end_date'` | `endDateTime` | Stops at a specific date |
| (omitted) | — | Same as `'no_end_date'` |

```
const opts = {
    recurrence: 'daily',
    frequency: 1,
    end: 'end_date',
    endDateTime: '2026-12-31 23:59:59',
    // ...other fields
}
```

### Monthly day selection

Monthly and yearly triggers use `daySelection` to specify which day. Two variants:

Fixed day:

```
const opts = {
    daySelection: 'fixed_day',
    dayOfMonth: 15,   // 1-31
}
```

Relative weekday:

```
const opts = {
    daySelection: 'relative_weekday',
    relativeWeek: 2,      // 1=First, 2=Second, 3=Third, 4=Fourth
    relativeWeekday: 2,   // 1=Mon, 2=Tue, ..., 7=Sun
}
```

Example — second Tuesday of every month:

```
const opts = {
    table: 'incident',
    recurrence: 'monthly',
    frequency: 1,
    daySelection: 'relative_weekday',
    relativeWeek: 2,
    relativeWeekday: 2,
    limit: 500,
    startDateAndTime: '2026-04-01 09:00:00',
    end: 'no_end_date',
}
```

### Scheduled examples

Monthly review — 1st of every month, in a specific time zone:

```
import { wfa, PlaybookTriggerTypes } from '@servicenow/sdk/automation'

const declarations = {
    triggers: [
        wfa.playbook.trigger(
            PlaybookTriggerTypes.Scheduled,
            { $id: Now.ID['monthly_review'], label: 'First of Month' },
            {
                table: 'incident',
                recurrence: 'monthly',
                frequency: 1,
                daySelection: 'fixed_day',
                dayOfMonth: 1,
                startDateAndTime: '2026-04-01 09:00:00',
                timeZone: 'America/Los_Angeles',
                end: 'no_end_date',
                limit: 500,
            },
        ),
    ],
}
```

One-time cleanup:

```
import { wfa, PlaybookTriggerTypes } from '@servicenow/sdk/automation'

const declarations = {
    triggers: [
        wfa.playbook.trigger(
            PlaybookTriggerTypes.Scheduled,
            { $id: Now.ID['one_time_cleanup'], label: 'One-Time Cleanup' },
            {
                table: 'incident',
                recurrence: 'once',
                startDateAndTime: '2026-05-15 02:00:00',
                limit: 1000,
                condition: 'state=7^sys_updated_onRELATIVELT@year@ago@3',
            },
        ),
    ],
}
```

Every 6 hours:

```
import { wfa, PlaybookTriggerTypes } from '@servicenow/sdk/automation'

const declarations = {
    triggers: [
        wfa.playbook.trigger(
            PlaybookTriggerTypes.Scheduled,
            { $id: Now.ID['periodic_check'], label: 'Every 6 Hours' },
            {
                table: 'incident',
                recurrence: 'periodically',
                repeat: { hours: 6 },
                startDateAndTime: '2026-04-01 00:00:00',
                end: 'no_end_date',
                limit: 200,
            },
        ),
    ],
}
```

## Best Practices

- Filter triggers with `condition`. Encoded queries reduce noise and avoid firing the playbook on irrelevant records.

- Prefer `RecordCreate` or `RecordUpdate` over `RecordCreateOrUpdate`. Use the combined trigger only when both events should produce identical behavior.

- Use `triggerOnUniqueChange: true` on `RecordUpdate` when you only want the playbook to fire on meaningful changes — not every save.

- Keep `runTriggerOnExtendedTables` off by default. Only enable when you explicitly want triggers on child-table records.

- Always set `limit` on scheduled triggers. It's required and prevents runaway processing (max 1000).

- Schedule for off-peak hours when possible — scheduled runs can be expensive on large tables.

- Set `timeZone` explicitly for business-critical schedules — the default `'floating'` follows the system time zone, which may not match user expectations.

- Use `'once'` for one-time tasks rather than a daily schedule with `frequency: 1` and an immediate end date.

## Important Notes

- Condition syntax uses ServiceNow encoded query format: `=` not `==`, `^` for AND, `^OR` for OR.

- A playbook can have multiple triggers — any trigger can start the playbook independently.

- Each trigger needs a unique `$id`.

- For scheduled triggers, `startDateAndTime` must be in the future when the playbook is activated.

- Date format for `startDateAndTime` and `endDateTime`: `yyyy-MM-dd HH:mm:ss`.

- `daysOfTheWeek` is concatenated digit codes (`'135'`), not comma-separated names.

- `dayOfMonth` is validated against month length — can't exceed 29 for February or 30 for 30-day months.

- When a trigger's `table` matches the playbook's `parentTable`, omit `parentRecord` — the platform links the triggering record automatically.

- A playbook with `executionType: 'on_demand'` cannot have `triggers` configured at all — omit the key entirely. This is enforced both as a type restriction and a build diagnostic. See `playbook-api#execution-types` for this and related `on_demand` restrictions (`parentTable`, `allowAsNested`, `params.parentRecord`).

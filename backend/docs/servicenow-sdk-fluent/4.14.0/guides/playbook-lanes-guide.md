Version: 4.14.0

# Playbook Lanes Guide

Practical guide for configuring playbook lanes — covers restart rules, conditional execution, start delays, and common lane layouts. For the underlying type signatures see `playbook-api`; for execution-ordering concepts see `playbook-guide`.

## When to Use

- You need to configure whether a lane re-runs when the playbook is restarted (`restartRule`)

- You need to skip a lane conditionally at runtime based on a data pill (`conditionToRun`)

- You need to delay a lane's start after its dependencies complete (`startWithDelay`)

- You need a layout reference for sequential, parallel, or conditional lane structures

## Restart Rules

Every lane declares a `restartRule` that controls behavior when a playbook is restarted.

| Rule | Behavior |
| `'RUN_ONLY_ONCE'` | Lane runs on the first execution only; skipped on restart |
| `'RUN_ALWAYS'` | Lane runs on every execution, including restarts |
| `'RUN_ONLY_ON_RESTART'` | Lane is skipped on the first execution; runs only when the playbook is restarted |

Use `'RUN_ONLY_ONCE'` for setup or intake lanes that should not repeat. Use `'RUN_ALWAYS'` for resolution lanes that should re-evaluate state on restart. Use `'RUN_ONLY_ON_RESTART'` for cleanup or recovery lanes that only make sense after a prior run.

## Conditional Execution

Use `conditionToRun` to skip a lane at runtime based on a condition. The condition uses ServiceNow encoded query format; interpolate data pills with `wfa.playbook.dataPill()` and the helper handles formatting for you.

```
// Assumes the playbook declares a boolean input called `skipEnrichment`
const enrichment = wfa.playbook.lane({
    config: {
        $id: Now.ID['lane_enrichment'],
        label: 'Enrichment',
        order: 2,
        startRule: wfa.playbook.run.After(intake),
        restartRule: 'RUN_ALWAYS',
        conditionToRun: `${wfa.playbook.dataPill(params.inputs.skipEnrichment)}=false`,
    },
    activities: () => ({}),
})
```

Allowed pill sources in `conditionToRun`:

- `params.inputs.*` — playbook inputs

- `params.parentRecord.*` — the triggering record's fields

- Activity outputs from a lane that runs before this one

- Activity state from a lane that runs before this one

Not allowed in conditions: `params.state`, activity `sysId`, and `wfa.playbook.currentActivity.*` — the pill resolver emits a diagnostic error if you use any of these in a `conditionToRun` (or any other condition field).

Operators: Use encoded query syntax — `=` equals, `!=` not equals, `STARTSWITH`, `ENDSWITH`, `LIKE`, `ISEMPTY`, `ISNOTEMPTY`, `^` AND, `^OR` OR.

For conditional routing within a lane (rather than skipping the lane entirely), prefer a `Decision` activity. Use `conditionToRun` only when the whole lane should be skipped.

## Start With Delay

`startWithDelay` delays a lane's start after its `startRule` is satisfied. Three delay types are supported, discriminated by `type`.

### Explicit duration

Fixed delay specified as any combination of days, hours, minutes, and seconds:

```
const followup = wfa.playbook.lane({
    config: {
        $id: Now.ID['lane_followup'],
        label: 'Follow-Up',
        order: 2,
        startRule: wfa.playbook.run.After(intake),
        restartRule: 'RUN_ONLY_ONCE',
        startWithDelay: {
            type: 'explicit',
            duration: Duration({ days: 4, hours: 3, minutes: 2, seconds: 1 }),
        },
    },
    activities: () => ({}),
})
```

`duration` accepts the `Duration({ days, hours, minutes, seconds })` helper (preferred — generated code always uses this form), a data pill, or a raw `{ days, hours, minutes, seconds }` object.

### Relative duration

Delay relative to a datetime, before or after. Both `duration` and `relativeDatetime` accept data pills as well as literal values.

```
startWithDelay: {
    type: 'relative',
    duration: Duration({ days: 5, hours: 4 }),
    relativeDatetime: '2026-03-20 22:13:31',
    relativeOperator: 'after',
}
```

`relativeOperator` is `'before'` or `'after'`.

### Percentage duration

Delay as a percentage of time relative to a datetime:

```
startWithDelay: {
    type: 'percentage',
    percentage: 50,
    percentageDatetime: '2026-03-20 22:13:57',
}
```

`percentage` is greater than 0 and up to 100; decimals like `10.5` are allowed. Both `percentage` and `percentageDatetime` accept data pills as well as literals.

### Scheduling delays

All three delay types accept an optional `timerSchedule` — a `cmn_schedule` record that restricts the delay to that schedule's active hours (for example, business hours only). Outside the schedule's active hours the delay pauses and resumes counting once the schedule is active again. This is useful for SLA-aware timers or reminders that shouldn't fire outside business hours.

Pass either a raw `sys_id` string:

```
startWithDelay: {
    type: 'explicit',
    duration: Duration({ hours: 2 }),
    timerSchedule: '30b99b3d93a0220050bef157b67ffb2e',
}
```

or, if the app itself declares and owns the schedule record, a typed `Record<'cmn_schedule'>` reference:

```
import { Record } from '@servicenow/sdk/core'

const businessHours = Record({
    $id: Now.ID['business_hours_schedule'],
    table: 'cmn_schedule',
    data: { label: 'Business Hours', calendar_name: 'Business Hours', plural_label: 'Business Hours' },
})

startWithDelay: {
    type: 'explicit',
    duration: Duration({ hours: 2 }),
    timerSchedule: businessHours,
}
```

`timerSchedule` is available on `'explicit'`, `'relative'`, and `'percentage'` delays — see `startWithDelay` in `playbook-api` for the full type.

### When to use which

- Use `explicit` for fixed offsets ("start 1 hour after the previous lane completes").

- Use `relative` when the offset is computed against a known datetime, optionally from a data pill.

- Use `percentage` for SLA-style timing ("start when 50% of the SLA window has elapsed").

Prefer `startWithDelay` over inserting a timer activity as the first step of a lane — the platform handles the delay natively and the intent is clearer in the lane configuration.

## Common Lane Layouts

### Single lane — runs immediately

```
lanes: () => {
    const intake = wfa.playbook.lane({
        config: {
            $id: Now.ID['lane_intake'],
            label: 'Intake',
            order: 1,
            startRule: wfa.playbook.run.Immediately(),
            restartRule: 'RUN_ONLY_ONCE',
        },
        activities: () => ({}),
    })
    return { intake: intake }
}
```

### Sequential lanes — each waits for the previous

```
lanes: () => {
    const triage = wfa.playbook.lane({
        config: {
            $id: Now.ID['lane_triage'],
            label: 'Triage',
            order: 1,
            startRule: wfa.playbook.run.Immediately(),
            restartRule: 'RUN_ONLY_ONCE',
        },
        activities: () => ({}),
    })
    const resolution = wfa.playbook.lane({
        config: {
            $id: Now.ID['lane_resolution'],
            label: 'Resolution',
            order: 2,
            startRule: wfa.playbook.run.After(triage),
            restartRule: 'RUN_ALWAYS',
        },
        activities: () => ({}),
    })
    return { triage: triage, resolution: resolution }
}
```

### Convergence — one lane waits for two parallel lanes

```
lanes: () => {
    const team_a = wfa.playbook.lane({
        config: {
            $id: Now.ID['lane_team_a'],
            label: 'Team A',
            order: 1,
            startRule: wfa.playbook.run.Immediately(),
            restartRule: 'RUN_ONLY_ONCE',
        },
        activities: () => ({}),
    })
    const team_b = wfa.playbook.lane({
        config: {
            $id: Now.ID['lane_team_b'],
            label: 'Team B',
            order: 2,
            startRule: wfa.playbook.run.Immediately(),
            restartRule: 'RUN_ONLY_ONCE',
        },
        activities: () => ({}),
    })
    const merge = wfa.playbook.lane({
        config: {
            $id: Now.ID['lane_merge'],
            label: 'Merge Results',
            order: 3,
            startRule: wfa.playbook.run.After(team_a, team_b),
            restartRule: 'RUN_ONLY_ONCE',
        },
        activities: () => ({}),
    })
    return { team_a: team_a, team_b: team_b, merge: merge }
}
```

`wfa.playbook.run.After(team_a, team_b)` accepts varargs — the merge lane waits for both dependencies to complete.

### Conditional lane with delay

```
lanes: (params) => {
    const intake = wfa.playbook.lane({
        config: {
            $id: Now.ID['lane_intake'],
            label: 'Intake',
            order: 1,
            startRule: wfa.playbook.run.Immediately(),
            restartRule: 'RUN_ONLY_ONCE',
        },
        activities: () => ({}),
    })
    const triage = wfa.playbook.lane({
        config: {
            $id: Now.ID['lane_triage'],
            label: 'Triage',
            order: 2,
            startRule: wfa.playbook.run.After(intake),
            restartRule: 'RUN_ALWAYS',
            conditionToRun: `${wfa.playbook.dataPill(params.inputs.skipEnrichment)}=false`,
            startWithDelay: {
                type: 'explicit',
                duration: Duration({ hours: 1 }),
            },
        },
        activities: () => ({}),
    })
    return { intake: intake, triage: triage }
}
```

## Best Practices

- Declare lanes in dependency order. A lane must be assigned to a `const` before another lane can reference it in `wfa.playbook.run.After()`. TypeScript will catch out-of-order references as "variable used before declaration."

- Always return every lane variable. Each `const` lane must appear in the object returned by the `lanes` function — otherwise the lane is not registered.

- Use `order` for visual layout only. `order` controls display position in the designer; `startRule` controls execution order. They are independent.

- At least one lane should start with `wfa.playbook.run.Immediately()`. Otherwise nothing will run.

- Use `conditionToRun` only to skip the whole lane. For conditional routing inside a lane, use a Decision activity.

- Prefer `startWithDelay` over a leading timer activity. When the intent is "delay this lane's start," express it in the lane config rather than as a step.

- Use descriptive lane labels. Labels appear in the playbook UI and in restart prompts.

## Important Notes

- A lane with `wfa.playbook.run.After(a, b)` waits for all listed dependencies to complete.

- The `activities` callback must return an object. Use `() => ({})` for an empty lane.

- Cross-lane data references use the lane variable: `intake.enrich.outputs.support_tier`. Cross-lane activity references in an activity's `startRule` are not supported — use a lane-level dependency instead. See `playbook-guide` for the full explanation.

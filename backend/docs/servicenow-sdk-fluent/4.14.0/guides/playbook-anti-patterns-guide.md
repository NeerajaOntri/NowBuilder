Version: 4.14.0

# Playbook Anti-Patterns Guide

Wrong/correct code examples for the most common playbook mistakes. Pair this with `playbook-guide` (mental model + execution errors and gotchas) — that doc covers the conceptual errors; this one shows the structural mistakes that cause silent failures or compile errors.

## When to Use

- A build emits an error about a playbook's structure

- A playbook compiles but a lane or activity is silently missing at runtime

- You want to verify a new playbook doesn't have common structural mistakes before deploying

- Generated or AI-assisted playbook code needs to be audited for correctness

## Using Flow DSL Instead of Playbook DSL

Flows and playbooks are different APIs. Playbook requirements need `PlaybookDefinition`, not `Flow`.

Wrong:

```
import { Flow, wfa, trigger, action } from '@servicenow/sdk/automation'

Flow(
    { $id: Now.ID['my_process'], name: 'My Process' },
    wfa.trigger(trigger.record.created, ...),
    (_params) => {
        wfa.action(action.core.updateRecord, ...)
    },
)
```

Correct:

```
import { PlaybookDefinition, PlaybookTriggerTypes, wfa } from '@servicenow/sdk/automation'

PlaybookDefinition(
    { $id: Now.ID['my_process'], label: 'My Process' },
    {
        triggers: [
            wfa.playbook.trigger(
                PlaybookTriggerTypes.RecordCreate,
                { $id: Now.ID['trig_1'], label: 'On Create' },
                { table: 'incident' },
            ),
        ],
    },
    {
        lanes: () => {
            const main = wfa.playbook.lane({
                config: {
                    $id: Now.ID['main_lane'],
                    label: 'Main Lane',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => ({}),
            })
            return { main: main }
        },
    },
)
```

Key differences: Playbooks use `PlaybookDefinition` (not `Flow`); they take 3 arguments (config, triggers, body); they use `lanes` with `wfa.playbook.lane()` (not a callback with actions); and they use `wfa.playbook.trigger` (not `wfa.trigger`).

## Activities Outside of Lanes

Activities only exist inside a lane's `activities` callback. The body's top-level `lanes` object accepts lanes (and stage-level decisions) — nothing else.

Wrong:

```
PlaybookDefinition(
    { $id: Now.ID['pb'], label: 'My Playbook' },
    {},
    {
        // Activities cannot go here
        activities: () => ({
            myActivity: wfa.playbook.activity(...),
        }),
        lanes: () => ({}),
    },
)
```

Correct:

```
PlaybookDefinition(
    { $id: Now.ID['pb'], label: 'My Playbook' },
    {},
    {
        lanes: () => {
            const main = wfa.playbook.lane({
                config: {
                    $id: Now.ID['main_lane'],
                    label: 'Main',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => {
                    const myActivity = wfa.playbook.activity(/* ... */)
                    return { myActivity: myActivity }
                },
            })
            return { main: main }
        },
    },
)
```

The exception is a stage-level Decision activity placed alongside lanes — see `playbook-patterns-guide` for the stage-level pattern.

## Missing Lane Return

The `lanes` callback registers a lane only when it appears in the returned object. Forgetting the `return` silently drops the lane — the playbook compiles but the lane never runs.

Wrong:

```
{
    lanes: () => {
        const main = wfa.playbook.lane({
            config: {
                $id: Now.ID['main_lane'],
                label: 'Main',
                order: 1,
                startRule: wfa.playbook.run.Immediately(),
                restartRule: 'RUN_ONLY_ONCE',
            },
            activities: () => ({}),
        })
        // Missing return — lane is silently dropped
    }
}
```

Correct:

```
{
    lanes: () => {
        const main = wfa.playbook.lane({
            config: {
                $id: Now.ID['main_lane'],
                label: 'Main',
                order: 1,
                startRule: wfa.playbook.run.Immediately(),
                restartRule: 'RUN_ONLY_ONCE',
            },
            activities: () => ({}),
        })
        return { main: main }
    }
}
```

The same applies to activities — always return every activity variable from the `activities` callback, otherwise it won't appear on the lane.

## Out-of-Order Lane References

Because `wfa.playbook.run.After()` accepts lane variables by reference, a dependency must be declared before any lane that references it. TypeScript will catch this as "variable used before declaration."

Wrong:

```
{
    lanes: () => {
        const triage = wfa.playbook.lane({
            config: { ..., startRule: wfa.playbook.run.After(intake) },  // intake is not declared yet
            activities: () => ({}),
        })
        const intake = wfa.playbook.lane({
            config: { ..., startRule: wfa.playbook.run.Immediately() },
            activities: () => ({}),
        })
        return { triage: triage, intake: intake }
    }
}
```

Correct:

```
{
    lanes: () => {
        const intake = wfa.playbook.lane({
            config: { ..., startRule: wfa.playbook.run.Immediately() },
            activities: () => ({}),
        })
        const triage = wfa.playbook.lane({
            config: { ..., startRule: wfa.playbook.run.After(intake) },  // intake declared above
            activities: () => ({}),
        })
        return { intake: intake, triage: triage }
    }
}
```

The same rule applies inside an `activities` callback — an activity must be declared as a `const` before another activity can reference it in `wfa.playbook.run.After()`.

## Cross-Lane Activity Reference in `wfa.playbook.run.After()`

You can depend on an entire lane finishing, but you cannot depend on a single activity from another lane inside an activity's `startRule`. Cross-lane dependencies belong on the lane's `config.startRule`; cross-lane data is read via the lane variable.

Wrong:

```
// Activity in the enrichment lane trying to wait for an activity in the intake lane
const enrich = wfa.playbook.activity(
    /* ... */,
    {
        // Activity-level startRule cannot reference activities in other lanes
        startRule: wfa.playbook.run.After(intake.validate),
    },
)
```

Correct:

```
const intake = wfa.playbook.lane({
    config: { $id: Now.ID['lane_intake'], label: 'Intake', order: 1, startRule: wfa.playbook.run.Immediately(), restartRule: 'RUN_ONLY_ONCE' },
    activities: () => {
        const validate = wfa.playbook.activity(/* ... */)
        return { validate: validate }
    },
})

const enrichment = wfa.playbook.lane({
    // Lane-level dependency — wait for the entire intake lane
    config: { $id: Now.ID['lane_enrichment'], label: 'Enrichment', order: 2, startRule: wfa.playbook.run.After(intake), restartRule: 'RUN_ONLY_ONCE' },
    activities: () => {
        const enrich = wfa.playbook.activity(
            /* ... */,
            { /* config */ },
            {
                // Cross-lane data IS allowed via the lane variable
                data: wfa.playbook.dataPill(intake.validate.outputs.result),
            },
        )
        return { enrich: enrich }
    },
})
```

## Branch References — `as const` recommended

The Decision overload uses a `const` type parameter (`<const B extends readonly DecisionBranch[]>`), which means literal branch IDs should be inferred even without an explicit `as const`. In practice every example and test fixture in this repo still writes `as const` on the branches array, and it's the safest way to guarantee `decision.branches.<id>` type-checks across compiler versions and inference edge cases.

Recommended:

```
const decision = wfa.playbook.activity(
    ActivityDefinitions.Core.Decision,
    /* config */,
    {
        branches: [
            { id: 'critical', label: 'Critical', condition: '...' },
        ] as const,
    },
)

// Typed BranchReference — OK
const followup = wfa.playbook.activity(
    /* ... */,
    { startRule: wfa.playbook.run.After(decision.branches.critical) },
)
```

If you drop `as const` and `decision.branches.<id>` doesn't type-check, add it back.

## Passing an Array to `wfa.playbook.run.After()`

`wfa.playbook.run.After()` accepts varargs, not an array. Wrapping dependencies in `[]` causes a type error.

Wrong:

```
startRule: wfa.playbook.run.After([notify, log])
```

Correct:

```
startRule: wfa.playbook.run.After(notify, log)
```

## Targeting an Optional Activity with `wfa.playbook.run.After()`

An optional activity (`wfa.playbook.run.Manually()` as its `startRule`) may never run, so nothing may depend on it. `Run.After()` and output pills both reject it — this is a compile error, not just a lint warning.

Wrong:

```
const optionalStep = wfa.playbook.activity(ActivityDefinitions.Core.Instruction, {
    $id: Now.ID['optional_step'],
    label: 'Optional Step',
    startRule: wfa.playbook.run.Manually(),
    restartRule: 'RUN_ONLY_ONCE',
})

const next = wfa.playbook.activity(ActivityDefinitions.Core.Instruction, {
    $id: Now.ID['next'],
    label: 'Next',
    order: 2,
    startRule: wfa.playbook.run.After(optionalStep), // compile error — optionalStep may never run
    restartRule: 'RUN_ONLY_ONCE',
})
```

Correct: give the downstream step a start rule that doesn't target the optional activity — `Run.Immediately()`, or `Run.After()` targeting a different, non-optional activity or lane it should actually wait on.

```
const previousStep = wfa.playbook.activity(ActivityDefinitions.Core.Instruction, {
    $id: Now.ID['previous_step'],
    label: 'Previous Step',
    order: 1,
    startRule: wfa.playbook.run.Immediately(),
    restartRule: 'RUN_ONLY_ONCE',
})

const next = wfa.playbook.activity(ActivityDefinitions.Core.Instruction, {
    $id: Now.ID['next'],
    label: 'Next',
    order: 2,
    startRule: wfa.playbook.run.After(previousStep), // fine — depends on a non-optional activity
    restartRule: 'RUN_ONLY_ONCE',
})
```

See Optional Activities in the Activities Guide for the full set of restrictions.

## Related Topics

- `playbook-guide` — execution-ordering errors and gotchas (circular dependencies, decision merge points, etc.)

- `playbook-patterns-guide` — the right shape for common scenarios so anti-patterns don't sneak in

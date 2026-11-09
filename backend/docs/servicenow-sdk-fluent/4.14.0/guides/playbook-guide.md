Version: 4.14.0

# Playbook Guide

Conceptual guide for understanding how the Playbook DSL works, including execution ordering, decision branching, and common errors. For API signatures, interfaces, and type definitions see `playbook-api.md`.

Playbooks are created in a draft state and must be activated before they will execute. Activation is a manual step on the target instance — building or installing the project does not activate playbooks for you.

A note on terminology. "Lane" and "stage" are used interchangeably throughout this documentation and the broader project — both refer to the same execution path defined by `wfa.playbook.lane({...})`. "Stage-level Decision" is a separate concept: a Decision activity placed at the lanes body level rather than inside a lane.

## When to Use

Use a Playbook when a human will see and interact with the process as it runs — guided multi-step tasks with forms, approvals, or decisions surfaced through the playbook UI. Use a Flow instead when the automation runs invisibly in the background with no user-facing steps.

A request like "send an email when an incident is created" is ambiguous — clarify whether the user expects visible step-by-step guidance (playbook) or silent automation (flow) before choosing.

## Mental Model

The Playbook DSL is a declarative language for defining workflow structure. Rather than writing imperative code that executes step-by-step, you describe a dependency graph as a plain data structure that ServiceNow's Process Flow Engine will orchestrate at runtime.

### Inline Execution Ordering with `startRule`

Every activity and lane declares when it runs directly in its config via a `startRule` property. The ordering is colocated with the activity definition itself.

```
{
    lanes: (params) => ({
        intake: wfa.playbook.lane({
            config: { $id: Now.ID['lane_intake'], label: 'Intake', order: 1, startRule: wfa.playbook.run.Immediately() },
            activities: () => {
                const validate = wfa.playbook.activity(
                    ActivityDefinitions.Core.RecordForm,
                    { $id: Now.ID['act_validate'], label: 'Validate', order: 1, startRule: wfa.playbook.run.Immediately() },
                    { record: wfa.playbook.dataPill(params.inputs.record) },
                )
                const enrich = wfa.playbook.activity(
                    ActivityDefinitions.Core.RecordForm,
                    { $id: Now.ID['act_enrich'], label: 'Enrich', order: 2, startRule: wfa.playbook.run.After(validate) },
                    { table: 'customer_account' },
                )
                const notify = wfa.playbook.activity(
                    ActivityDefinitions.Core.SendEmail,
                    { $id: Now.ID['act_notify'], label: 'Notify', order: 3, startRule: wfa.playbook.run.After(enrich) },
                    { recipient: wfa.playbook.dataPill(params.inputs.record.assigned_to) },
                )
                return { validate: validate, enrich: enrich, notify: notify }
            },
        }),
    }),
}
```

Because each activity's `startRule` references earlier activities by variable, the dependency graph is visible at the point of definition. This lets the Process Flow Engine:

- Run independent activities in parallel

- Handle decision branches where multiple paths execute

- Restart playbooks from specific points

### Key Concepts

| Concept | Description |
| Activities | Individual workflow steps (send notification, update record, etc.) |
| Lanes | Groups of related activities that can depend on other lanes |
| `wfa.playbook.run.*` | `wfa.playbook.run.Immediately()` and `wfa.playbook.run.After(...)` declarations that define execution order |
| `startRule` | Required property on every activity and lane config that declares when it runs |

### A Simple Example

```
{
    lanes: (params) => ({
        main: wfa.playbook.lane({
            config: { $id: Now.ID['lane_main'], label: 'Main', order: 1, startRule: wfa.playbook.run.Immediately() },
            activities: () => {
                const validate = wfa.playbook.activity(
                    ActivityDefinitions.Core.RecordForm,
                    { $id: Now.ID['act_validate'], label: 'Validate', order: 1, startRule: wfa.playbook.run.Immediately() },
                )
                const notify = wfa.playbook.activity(
                    ActivityDefinitions.Core.SendEmail,
                    { $id: Now.ID['act_notify'], label: 'Notify', order: 2, startRule: wfa.playbook.run.After(validate) },
                )
                const log = wfa.playbook.activity(
                    ActivityDefinitions.Core.Placeholder,
                    { $id: Now.ID['act_log'], label: 'Log', order: 3, startRule: wfa.playbook.run.After(validate) },
                )
                const complete = wfa.playbook.activity(
                    ActivityDefinitions.Core.UpdateRecord,
                    { $id: Now.ID['act_complete'], label: 'Complete', order: 4, startRule: wfa.playbook.run.After(notify, log) },
                )
                return { validate: validate, notify: notify, log: log, complete: complete }
            },
        }),
    }),
}
```

This creates:

```
validate --> notify --+--> complete
         --> log   --+
```

The `notify` and `log` activities run in parallel after `validate`, and `complete` waits for both.

## Decision Branching

The Decision activity evaluates an ordered list of conditions and routes execution to matching branches.

### Setting Up a Decision

```
activities: () => {
    const routeCase = wfa.playbook.activity(
        ActivityDefinitions.Core.Decision,
        { $id: Now.ID['decision_route'], label: 'Route by Priority', order: 1, startRule: wfa.playbook.run.Immediately() },
        {
            type: 'match_first',
            branches: [
                { id: 'critical', label: 'Critical', condition: `${wfa.playbook.dataPill(params.inputs.record.priority)}=1` },
                { id: 'high',     label: 'High',     condition: `${wfa.playbook.dataPill(params.inputs.record.priority)}=2` },
                { id: 'else',     label: 'Else' },
            ],
        },
    )

    // Activities depend on specific branches via wfa.playbook.run.After(routeCase.branches.<id>)
    const escalate = wfa.playbook.activity(
        ActivityDefinitions.Core.UpdateRecord,
        { $id: Now.ID['act_escalate'], label: 'Escalate', order: 2, startRule: wfa.playbook.run.After(routeCase.branches.critical) },
    )
    const handleHigh = wfa.playbook.activity(
        ActivityDefinitions.Core.SendEmail,
        { $id: Now.ID['act_handle_high'], label: 'Handle High', order: 2, startRule: wfa.playbook.run.After(routeCase.branches.high) },
    )
    const handleStandard = wfa.playbook.activity(
        ActivityDefinitions.Core.Placeholder,
        { $id: Now.ID['act_handle_standard'], label: 'Handle Standard', order: 2, startRule: wfa.playbook.run.After(routeCase.branches.else) },
    )

    return { routeCase: routeCase, escalate: escalate, handleHigh: handleHigh, handleStandard: handleStandard }
},
```

### Merging Branches

To merge branches back together, pass the last activity of each branch to `wfa.playbook.run.After()`:

```
// Merge point - waits for whichever branch(es) ran
const afterRouting = wfa.playbook.activity(
    ActivityDefinitions.Core.UpdateRecord,
    {
        $id: Now.ID['act_after_routing'],
        label: 'After Routing',
        order: 10,
        startRule: wfa.playbook.run.After(
            pageOnCall,      // Last activity on critical branch
            handleHigh,      // Last activity on high branch
            handleStandard,  // Last activity on else branch
        ),
    },
)
```

### match_first vs match_all

match_first — Only the first matching branch executes:

```
                    +- [critical] --> escalate --> page -+
                    |                                    |
Decision ----------+- [high] ------> handleHigh --------+--> afterRouting
(match_first)      |                                    |
                    +- [else] ------> handleStandard ---+

Only ONE path executes (first condition that matches)
```

match_all — All matching branches execute in parallel:

```
                    +- [email] ---> sendEmail ---+
                    |                            |
Decision ----------+- [sms] -----> sendSms -----+--> (all complete)
(match_all)        |                            |
                    +- [slack] --> sendSlack ---+

Multiple paths can execute simultaneously (all conditions that match)
```

### Key Rules

- Only the first activity on a branch needs the branch reference in its `startRule`

- Subsequent activities on the same branch use the previous activity reference to chain

- Branch references in `wfa.playbook.run.After()` imply waiting for the decision activity itself

- The `else` branch must use `id: 'else'` and `label: 'Else'` (see `playbook-api` for the DecisionBranch fields)

## Common Errors and Gotchas

### Cross-Lane Activity Reference in wfa.playbook.run.After()

Problem: You cannot depend on an individual activity from another lane in an activity's `startRule`. Lane-level dependencies use lane variables in the lane config's `startRule`.

```
// Wrong - cross-lane activity in activity startRule
const processRecord = wfa.playbook.activity(
    ...,
    { ..., startRule: wfa.playbook.run.After(someOtherLaneActivity) },  // Error!
)

// Correct - use lane reference in lane config startRule
const process = wfa.playbook.lane({
    config: { ..., startRule: wfa.playbook.run.After(intake) },  // Waits for entire intake lane
    activities: () => {
        const processRecord = wfa.playbook.activity(
            ...,
            { ..., startRule: wfa.playbook.run.Immediately() },
            { data: wfa.playbook.dataPill(intake.validate.outputs.result) },  // Cross-lane data via lane variable
        )
        return { processRecord: processRecord }
    },
})
```

### Wrong Label on the ELSE Branch

Problem: The `else` branch label is type-enforced to the exact string `'Else'`. If you use any other label, the Decision overload fails to match and TypeScript falls through to the generic activity overload — the resulting error is about the activity definition type, not the branch label, so the real cause is easy to miss.

```
// Wrong - else label must be exactly 'Else'
{ branches: [
    { id: 'critical', label: 'Critical', condition: ... },
    { id: 'else',     label: 'Low / Planning' },  // type error!
]}
// Reported error:
//   No overload matches this call.
//   ...
//   Argument of type 'DecisionActivityDefinition' is not assignable
//   to parameter of type 'GenericActivityDefinition'.

// Correct
{ branches: [
    { id: 'critical', label: 'Critical', condition: ... },
    { id: 'else',     label: 'Else' },
]}
```

If you want a descriptive name for the fallback path, put it on the lane or activity that consumes `decision.branches.else`, not on the branch itself.

### Shorthand Property Assignment in Return Objects

Problem: Fluent files (`.now.ts`) do not allow shorthand property assignments. The build emits `TS304: Node kind "ShorthandPropertyAssignment" is not allowed in Fluent files`. This applies to every object literal in a Fluent file, including the records returned from `activities` callbacks and the top-level `lanes` callback.

```
// Wrong - shorthand property assignment
activities: () => {
    const review = wfa.playbook.activity(...)
    const notify = wfa.playbook.activity(...)
    return { review, notify }  // TS304 error
}

// Correct - explicit key: value form
activities: () => {
    const review = wfa.playbook.activity(...)
    const notify = wfa.playbook.activity(...)
    return { review: review, notify: notify }
}
```

Apply the same rule to the final `return { lane_a: lane_a, ... }` at the bottom of the `lanes` callback.

### Using Array Instead of Varargs in wfa.playbook.run.After()

Problem: `wfa.playbook.run.After()` takes varargs, not an array.

```
// Wrong
startRule: wfa.playbook.run.After([notify, log]),  // Error!

// Correct
startRule: wfa.playbook.run.After(notify, log),
```

### Missing startRule on Activity or Lane Config

Problem: `startRule` is required on both `ActivityConfig` and `LaneConfig`. Every activity and lane must declare when it runs.

```
// Wrong - missing startRule
const validate = wfa.playbook.activity(
    ActivityDefinitions.Core.RecordForm,
    { $id: Now.ID['act_validate'], label: 'Validate', order: 1 },  // Missing startRule!
)

// Correct
const validate = wfa.playbook.activity(
    ActivityDefinitions.Core.RecordForm,
    { $id: Now.ID['act_validate'], label: 'Validate', order: 1, startRule: wfa.playbook.run.Immediately() },
)
```

### Circular Dependencies

Problem: Creating circular dependencies (A depends on B, B depends on A). Because `startRule` references local variables, TypeScript typically catches this as "variable used before declaration".

```
// Wrong - TypeScript will catch this
const a = wfa.playbook.activity(
    ...,
    { ..., startRule: wfa.playbook.run.After(b) },  // Error: 'b' used before declaration
)
const b = wfa.playbook.activity(
    ...,
    { ..., startRule: wfa.playbook.run.After(a) },
)
```

Ensure dependencies form a DAG (Directed Acyclic Graph). Use Decision branching or lane ordering to break cycles.

### Mixing on_demand with Trigger-Only Fields

Problem: `executionType: 'on_demand'` playbooks have no triggering record, so several trigger/record-driven fields are disallowed: `triggers` (not configurable at all — must be omitted, not even `[]`), `parentTable`, the launcher's record-form fields (`launcherShowRecordForm`, `launcherRecordFormView`, `launcherTemplateFields`), and referencing `params.parentRecord` in `lanes` or `permissions`. `allowAsNested: true` is the inverse case — it's only permitted for `on_demand` playbooks.

```
// Wrong - parentTable and triggers are both disallowed once executionType is 'on_demand'
PlaybookDefinition(
    { $id: Now.ID['pb'], label: 'Request Form', executionType: 'on_demand', parentTable: 'incident' },  // Error!
    { triggers: [wfa.playbook.trigger(PlaybookTriggerTypes.RecordCreate, ..., { table: 'incident' })] },  // Error!
    { lanes: () => ({}) }
)

// Correct - triggers is omitted entirely, not set to []
PlaybookDefinition(
    { $id: Now.ID['pb'], label: 'Request Form', executionType: 'on_demand' },
    { permissions: () => ({ roles: [{ role: '...', view: true, launch: true }] }) },
    { lanes: () => ({}) }
)
```

See `playbook-api#execution-types` for the full list of `on_demand` restrictions.

## API Reference

See `playbook-api` for `PlaybookDefinition` signatures, `wfa.playbook.*` interfaces, type definitions, and the data model mapping.

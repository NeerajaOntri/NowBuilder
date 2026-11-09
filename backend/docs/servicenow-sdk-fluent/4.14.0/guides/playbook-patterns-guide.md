Version: 4.14.0

# Playbook Patterns Guide

Recipes for the most common playbook shapes — simple single-lane workflows, multi-lane sequential and parallel layouts, and decision-driven branching (including chained decisions and stage-level routing between lanes). Each pattern is shown end-to-end so it can be copied as a starting point. For activity and lane reference material see `playbook-activities-guide` and `playbook-lanes-guide`.

## When to Use

Refer to this guide when designing a new playbook and you need a proven structural starting point. Each pattern can be used as-is or adapted for specific requirements. For conceptual background on how execution ordering and decision branching work, see `playbook-guide`.

## Simple Pattern — Single Lane

Use when one lane is enough. Activities inside the lane can still be sequential, parallel, or branch on a Decision — what makes the pattern "simple" is that there's only one lane, so there's no cross-lane dependency or stage-level routing to coordinate.

Structure: Config → Trigger → Lane → Activities.

Minimal playbook (no triggers, no activities):

```
import { PlaybookDefinition, wfa } from '@servicenow/sdk/automation'

PlaybookDefinition(
    {
        $id: Now.ID['simple_playbook'],
        label: 'Simple Playbook',
        name: 'simple_playbook',
        description: '',
    },
    {},
    { lanes: () => ({}) },
)
```

Playbook with a trigger and one lane:

```
import { PlaybookDefinition, PlaybookTriggerTypes, wfa } from '@servicenow/sdk/automation'

PlaybookDefinition(
    {
        $id: Now.ID['incident_intake'],
        label: 'Incident Intake',
        name: 'incident_intake',
        description: 'Handles intake when a high-priority incident is created',
    },
    {
        triggers: [
            wfa.playbook.trigger(
                PlaybookTriggerTypes.RecordCreate,
                { $id: Now.ID['trig_incident_create'], label: 'On Incident Created' },
                { table: 'incident', condition: 'priority<=2^active=true' },
            ),
        ],
    },
    {
        lanes: () => {
            const intake = wfa.playbook.lane({
                config: {
                    $id: Now.ID['lane_intake'],
                    label: 'Intake Processing',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => ({}),
            })
            return { intake: intake }
        },
    },
)
```

Typical use cases: record validation on creation, simple intake/triage, single-team task processing, one-off automation tied to a record event.

## Multi-Lane Sequential

Use when work proceeds through clear stages — each stage waits for the previous to finish before it begins.

Structure: Lane 1 (Immediately) → Lane 2 (After Lane 1) → Lane 3 (After Lane 2) → …

```
import { PlaybookDefinition, wfa } from '@servicenow/sdk/automation'

PlaybookDefinition(
    {
        $id: Now.ID['sequential_playbook'],
        label: 'Sequential Processing',
        name: 'sequential_processing',
    },
    {},
    {
        lanes: () => {
            const intake = wfa.playbook.lane({
                config: {
                    $id: Now.ID['seq_intake'],
                    label: 'Intake',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => ({}),
            })
            const triage = wfa.playbook.lane({
                config: {
                    $id: Now.ID['seq_triage'],
                    label: 'Triage',
                    order: 2,
                    startRule: wfa.playbook.run.After(intake),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => ({}),
            })
            const investigation = wfa.playbook.lane({
                config: {
                    $id: Now.ID['seq_investigation'],
                    label: 'Investigation',
                    order: 3,
                    startRule: wfa.playbook.run.After(triage),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => ({}),
            })
            const resolution = wfa.playbook.lane({
                config: {
                    $id: Now.ID['seq_resolution'],
                    label: 'Resolution',
                    order: 4,
                    startRule: wfa.playbook.run.After(investigation),
                    restartRule: 'RUN_ALWAYS',
                },
                activities: () => ({}),
            })
            return { intake: intake, triage: triage, investigation: investigation, resolution: resolution }
        },
    },
)
```

Typical use cases: pipeline-style processing (triage → investigate → resolve), staged approvals, build/deploy/verify workflows.

## Multi-Lane Parallel with Convergence

Use when independent workstreams should run in parallel and then converge before a final stage.

Structure:

```
Lane A (Immediately) ─┐
                       ├─→ Lane C (After A, B)
Lane B (Immediately) ─┘
```

```
import { PlaybookDefinition, wfa } from '@servicenow/sdk/automation'

PlaybookDefinition(
    {
        $id: Now.ID['parallel_playbook'],
        label: 'Parallel Processing',
        name: 'parallel_processing',
    },
    {},
    {
        lanes: () => {
            const team_a = wfa.playbook.lane({
                config: {
                    $id: Now.ID['par_team_a'],
                    label: 'Team A Work',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => ({}),
            })
            const team_b = wfa.playbook.lane({
                config: {
                    $id: Now.ID['par_team_b'],
                    label: 'Team B Work',
                    order: 2,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => ({}),
            })
            const merge = wfa.playbook.lane({
                config: {
                    $id: Now.ID['par_merge'],
                    label: 'Merge and Finalize',
                    order: 3,
                    startRule: wfa.playbook.run.After(team_a, team_b),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => ({}),
            })
            return { team_a: team_a, team_b: team_b, merge: merge }
        },
    },
)
```

`wfa.playbook.run.After(team_a, team_b)` accepts varargs — the merge lane waits for both dependencies to complete. Add more parallel lanes by adding more arguments.

Typical use cases: multi-team case management, parallel approval and notification workstreams, independent data enrichment that converges for a final decision.

## Decision — `match_first`

Use `match_first` when execution should follow exactly one branch — the first condition that matches.

```
import { PlaybookDefinition, ActivityDefinitions, wfa } from '@servicenow/sdk/automation'

PlaybookDefinition(
    { $id: Now.ID['priority_routing'], label: 'Priority Routing', name: 'priority_routing' },
    {},
    {
        lanes: () => {
            const routing = wfa.playbook.lane({
                config: {
                    $id: Now.ID['routing_lane'],
                    label: 'Routing',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => {
                    const intake_form = wfa.playbook.activity(
                        ActivityDefinitions.Core.RecordForm,
                        {
                            $id: Now.ID['act_intake_form'],
                            label: 'Intake Form',
                            order: 1,
                            startRule: wfa.playbook.run.Immediately(),
                            restartRule: 'RUN_ONLY_ONCE',
                        },
                        { assigned_to: '' },
                    )

                    const router = wfa.playbook.activity(
                        ActivityDefinitions.Core.Decision,
                        {
                            $id: Now.ID['act_router'],
                            label: 'Route by State',
                            order: 2,
                            startRule: wfa.playbook.run.After(intake_form),
                            restartRule: 'RUN_ONLY_ONCE',
                        },
                        {
                            type: 'match_first',
                            branches: [
                                {
                                    id: 'pending',
                                    label: 'Pending',
                                    condition: `${wfa.playbook.dataPill(intake_form.outputs.record.state)}=PENDING`,
                                },
                                {
                                    id: 'in_progress',
                                    label: 'In Progress',
                                    condition: `${wfa.playbook.dataPill(intake_form.outputs.record.state)}=IN_PROGRESS`,
                                },
                                { id: 'else', label: 'Else' },
                            ] as const,
                        },
                    )

                    const handle_pending = wfa.playbook.activity(
                        ActivityDefinitions.Core.Instruction,
                        {
                            $id: Now.ID['act_handle_pending'],
                            label: 'Process Pending',
                            order: 3,
                            startRule: wfa.playbook.run.After(router.branches.pending),
                            restartRule: 'RUN_ONLY_ONCE',
                        },
                        { message: 'Record is pending — awaiting action.' },
                    )
                    const handle_in_progress = wfa.playbook.activity(
                        ActivityDefinitions.Core.Instruction,
                        {
                            $id: Now.ID['act_handle_in_progress'],
                            label: 'Process In Progress',
                            order: 4,
                            startRule: wfa.playbook.run.After(router.branches.in_progress),
                            restartRule: 'RUN_ONLY_ONCE',
                        },
                        { message: 'Record is in progress — monitoring.' },
                    )
                    const handle_default = wfa.playbook.activity(
                        ActivityDefinitions.Core.Instruction,
                        {
                            $id: Now.ID['act_handle_default'],
                            label: 'Default Processing',
                            order: 5,
                            startRule: wfa.playbook.run.After(router.branches.else),
                            restartRule: 'RUN_ONLY_ONCE',
                        },
                        { message: 'Processing with default workflow.' },
                    )

                    return { intake_form: intake_form, router: router, handle_pending: handle_pending, handle_in_progress: handle_in_progress, handle_default: handle_default }
                },
            })
            return { routing: routing }
        },
    },
)
```

The `else` branch has no `condition` and must be the last branch in the array. It runs only when none of the preceding branches matched — it is a fallback, not an "always runs" branch. `as const` on the `branches` array is not required (the Decision overload infers literal branch IDs automatically) but is used by convention throughout the codebase — see `playbook-anti-patterns-guide`.

## Decision — `match_all`

Use `match_all` when all matching branches should execute, in parallel. Each matching branch's downstream activities start together.

```
const triage_form = wfa.playbook.activity(
    ActivityDefinitions.Core.RecordForm,
    {
        $id: Now.ID['act_triage_form'],
        label: 'Triage Form',
        order: 1,
        startRule: wfa.playbook.run.Immediately(),
        restartRule: 'RUN_ONLY_ONCE',
    },
    { assigned_to: '' },
)

const decision = wfa.playbook.activity(
    ActivityDefinitions.Core.Decision,
    {
        $id: Now.ID['act_parallel_check'],
        label: 'Check Assignment and Automation',
        order: 2,
        startRule: wfa.playbook.run.After(triage_form),
        restartRule: 'RUN_ONLY_ONCE',
    },
    {
        type: 'match_all',
        branches: [
            {
                id: 'unassigned',
                label: 'No Assignee',
                condition: `${wfa.playbook.dataPill(triage_form.outputs.record.assigned_to)}ISEMPTY`,
            },
            {
                id: 'was_automated',
                label: 'Was Automated',
                condition: `${wfa.playbook.dataPill(triage_form.outputs.automated)}=true`,
            },
            { id: 'else', label: 'Else' },
        ] as const,
    },
)

const assign_oncall = wfa.playbook.activity(
    ActivityDefinitions.Core.Instruction,
    {
        $id: Now.ID['act_assign_oncall'],
        label: 'Assign to On-Call',
        order: 3,
        startRule: wfa.playbook.run.After(decision.branches.unassigned),
        restartRule: 'RUN_ONLY_ONCE',
    },
    { message: 'No assignee found — routing to on-call.' },
)

const log_automation = wfa.playbook.activity(
    ActivityDefinitions.Core.Instruction,
    {
        $id: Now.ID['act_log_automation'],
        label: 'Log Automation',
        order: 4,
        startRule: wfa.playbook.run.After(decision.branches.was_automated),
        restartRule: 'RUN_ONLY_ONCE',
    },
    { message: 'Activity was completed via automation.' },
)
```

If a record is both unassigned and was automated, both `assign_oncall` and `log_automation` execute in parallel.

## Chained Decisions

Feed one decision into another by starting the second decision after a specific branch of the first.

```
const check_assignee = wfa.playbook.activity(
    ActivityDefinitions.Core.Decision,
    {
        $id: Now.ID['act_check_assignee'],
        label: 'Check Assignee',
        order: 2,
        startRule: wfa.playbook.run.After(request_form),
        restartRule: 'RUN_ONLY_ONCE',
    },
    {
        branches: [
            {
                id: 'has_assignee',
                label: 'Has Assignee',
                condition: `${wfa.playbook.dataPill(request_form.outputs.record.assigned_to)}ISNOTEMPTY`,
            },
            { id: 'else', label: 'Else' },
        ] as const,
    },
)

// Second decision runs only when there IS an assignee
const check_group = wfa.playbook.activity(
    ActivityDefinitions.Core.Decision,
    {
        $id: Now.ID['act_check_group'],
        label: 'Check Assignment Group',
        order: 3,
        startRule: wfa.playbook.run.After(check_assignee.branches.has_assignee),
        restartRule: 'RUN_ONLY_ONCE',
    },
    {
        branches: [
            {
                id: 'has_group',
                label: 'Has Group',
                condition: `${wfa.playbook.dataPill(request_form.outputs.record.assignment_group)}ISNOTEMPTY`,
            },
            { id: 'else', label: 'Else' },
        ] as const,
    },
)

const route_to_queue = wfa.playbook.activity(
    ActivityDefinitions.Core.Instruction,
    {
        $id: Now.ID['act_route_to_queue'],
        label: 'Route to Queue',
        order: 4,
        startRule: wfa.playbook.run.After(check_assignee.branches.else),
        restartRule: 'RUN_ONLY_ONCE',
    },
    { message: 'No assignee — routing to unassigned queue.' },
)

const notify_group = wfa.playbook.activity(
    ActivityDefinitions.Core.Instruction,
    {
        $id: Now.ID['act_notify_group'],
        label: 'Notify Group',
        order: 5,
        startRule: wfa.playbook.run.After(check_group.branches.has_group),
        restartRule: 'RUN_ONLY_ONCE',
    },
    { message: 'Notifying assignment group.', wait: 'yes' },
)
```

## Stage-Level Decision — Route Between Lanes

Place a Decision at the `lanes` body level (not inside any lane) to route execution to different lanes. Each downstream lane uses `wfa.playbook.run.After(decision.branches.<id>)`.

```
import { PlaybookDefinition, ActivityDefinitions, wfa } from '@servicenow/sdk/automation'

PlaybookDefinition(
    { $id: Now.ID['incident_routing'], label: 'Incident Triage and Routing', name: 'incident_routing' },
    {},
    {
        lanes: () => {
            const triage = wfa.playbook.lane({
                config: {
                    $id: Now.ID['sl_triage'],
                    label: 'Triage',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => {
                    const review = wfa.playbook.activity(
                        ActivityDefinitions.Core.RecordForm,
                        {
                            $id: Now.ID['act_review_form'],
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
                    $id: Now.ID['sl_route_decision'],
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
                    $id: Now.ID['sl_escalation'],
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

            const group_route = wfa.playbook.lane({
                config: {
                    $id: Now.ID['sl_group_route'],
                    label: 'Group Routing',
                    order: 4,
                    startRule: wfa.playbook.run.After(decision.branches.has_group),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => {
                    const notify = wfa.playbook.activity(
                        ActivityDefinitions.Core.Instruction,
                        {
                            $id: Now.ID['act_notify_group'],
                            label: 'Notify Group',
                            order: 1,
                            startRule: wfa.playbook.run.Immediately(),
                            restartRule: 'RUN_ONLY_ONCE',
                        },
                        { message: 'Notifying assignment group.' },
                    )
                    return { notify: notify }
                },
            })

            const standard = wfa.playbook.lane({
                config: {
                    $id: Now.ID['sl_standard'],
                    label: 'Standard Processing',
                    order: 5,
                    startRule: wfa.playbook.run.After(decision.branches.else),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                activities: () => {
                    const queue = wfa.playbook.activity(
                        ActivityDefinitions.Core.Instruction,
                        {
                            $id: Now.ID['act_queue_task'],
                            label: 'Queue for Processing',
                            order: 1,
                            startRule: wfa.playbook.run.Immediately(),
                            restartRule: 'RUN_ONLY_ONCE',
                        },
                        { message: 'Added to standard processing queue.' },
                    )
                    return { queue: queue }
                },
            })

            return { triage: triage, decision: decision, escalation: escalation, group_route: group_route, standard: standard }
        },
    },
)
```

Stage-level differences:

- Return the decision in the lanes return object alongside the lanes.

## Conditional Restart with Go Back

`GoBack` is the only built-in that can jump a playbook backward, so it's the only way to build a real loop — a
decision branch that re-runs an earlier stage until it passes, instead of always moving forward. Because a loop can
in principle run forever, the author is responsible for making sure that re-running the target can actually change
which branch the decision takes next time. Going back only helps if whatever happens on the re-run (a human
edits the record, an automation updates a field, etc.) is capable of flipping the decision's outcome. If nothing
that happens on the target ever changes what the decision would pick, the same branch is selected every time and
the playbook loops forever, even though the build succeeds cleanly.

Structure:

```
Validate Submission (lane, restartRule RUN_ALWAYS — Go Back's target)
        │
        ▼
Validation Check (Decision, match_first)
  ├─ "Invalid — Retry"     (invalid, not flagged for escalation) ──▶ Go Back ──▶ Validate Submission
  ├─ "Invalid — Escalate"  (flagged for escalation)               ──▶ Escalate (forward path)
  └─ "Else"                (valid)                                 ──▶ Proceed (forward path)
```

```
PlaybookDefinition(
    {
        $id: Now.ID['retry_validation'],
        label: 'Retry Validation with Escalation',
        name: 'retry_validation',
        parentTable: 'incident',
    },
    {
        triggers: []
    },
    {
        lanes: () => {
            // Go Back's target — must run always so it re-executes on the jump back.
            const validate = wfa.playbook.lane({
                config: {
                    $id: Now.ID['stage_validate'],
                    label: 'Validate Submission',
                    order: 1,
                    startRule: wfa.playbook.run.Immediately(),
                    restartRule: 'RUN_ALWAYS',
                },
                activities: () => {
                    const review = wfa.playbook.activity(
                        ActivityDefinitions.Core.RecordForm,
                        {
                            $id: Now.ID['act_review_submission'],
                            label: 'Review Submission',
                            order: 1,
                            startRule: wfa.playbook.run.Immediately(),
                            restartRule: 'RUN_ONLY_ONCE',
                        },
                        { assigned_to: '' },
                    )
                    return { review: review }
                },
            })

            const validation_check = wfa.playbook.activity(
                ActivityDefinitions.Core.Decision,
                {
                    $id: Now.ID['act_validation_check'],
                    label: 'Validation Check',
                    order: 2,
                    startRule: wfa.playbook.run.After(validate),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                {
                    type: 'match_first',
                    branches: [
                        {
                            id: 'needs_retry',
                            label: 'Invalid — Retry',
                            condition: `${wfa.playbook.dataPill(validate.review.outputs.record.validation_state)}=INVALID^${wfa.playbook.dataPill(validate.review.outputs.record.needs_escalation)}=no`,
                        },
                        {
                            id: 'needs_escalation',
                            label: 'Invalid — Escalate',
                            condition: `${wfa.playbook.dataPill(validate.review.outputs.record.needs_escalation)}=yes`,
                        },
                        { id: 'else', label: 'Else' },
                    ] as const,
                },
            )

            // Terminal activity of "Invalid — Retry" — jumps back to Validate Submission.
            const retry_validation_step = wfa.playbook.activity(
                ActivityDefinitions.Core.GoBack,
                {
                    $id: Now.ID['act_retry_validation'],
                    label: 'Retry Validation',
                    order: 3,
                    startRule: wfa.playbook.run.After(validation_check.branches.needs_retry),
                    restartRule: 'RUN_ALWAYS',
                },
                {
                    target_type: 'go_back_to_target_stage',
                    go_back_to_target_stage: validate,
                },
            )

            // Terminal activity of "Invalid — Escalate" — a forward path, not another Go Back, so
            // the decision always has somewhere to go once the reviewer flags this for escalation.
            const escalate = wfa.playbook.activity(
                ActivityDefinitions.Core.Instruction,
                {
                    $id: Now.ID['act_escalate_validation'],
                    label: 'Escalate to Reviewer',
                    order: 4,
                    startRule: wfa.playbook.run.After(validation_check.branches.needs_escalation),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                { message: 'Flagged for manual escalation — routing for review.' },
            )

            const proceed = wfa.playbook.activity(
                ActivityDefinitions.Core.Instruction,
                {
                    $id: Now.ID['act_proceed_valid'],
                    label: 'Proceed',
                    order: 5,
                    startRule: wfa.playbook.run.After(validation_check.branches.else),
                    restartRule: 'RUN_ONLY_ONCE',
                },
                { message: 'Submission is valid — continuing.' },
            )

            return {
                validate: validate,
                validation_check: validation_check,
                retry_validation_step: retry_validation_step,
                escalate: escalate,
                proceed: proceed,
            }
        },
    },
)
```

Why this is on the author, not the build: `playbook-activities-guide#go-back` rule 6 only guarantees, at build
time, that the decision has some branch that doesn't dead-end in a Go Back — it's a structural check, not a
runtime guarantee. That branch still has to be reachable. In the example above, `needs_escalation` is a field
the reviewer sets on the record itself while working the retry form — nothing about it is special to Fluent, it's
just a normal field the Go Back's target (`Validate Submission`) gives the reviewer a chance to change before the
decision runs again. If the retry form never gave the reviewer (or some other automation) a way to change
`needs_escalation` or `validation_state`, "Invalid — Retry" would be selected every single time the playbook
restarts here, looping forever even though the build succeeds cleanly.

The rule of thumb: before wiring up a Go Back, trace what actually changes between one pass through the target
and the next. If the answer is "nothing, unless something outside the playbook intervenes," make sure that
something — a reviewer editing the record, a Business Rule, a Script Include, a timeout — is really wired up, not
just assumed.

## Optional Activity in a Real Scenario

Use when a step should only run if someone explicitly triggers it — not automatically as part of the flow. Common for "escalate," "request more info," or other steps that are the exception, not the rule. See `playbook-activities-guide.md#optional-activities` for the full type reference (config shape, restrictions, compile-time guarantees); this section shows it embedded in a realistic multi-lane workflow.

Lane-scoped — declared inside a lane's `activities()`, alongside the lane's regular steps:

```
const lane_1 = wfa.playbook.lane({
    config: { $id: Now.ID['cra_inspect_lane'], label: 'Inspect Change', order: 2, startRule: wfa.playbook.run.After(lane_0), restartRule: 'RUN_ONLY_ONCE' },
    activities: () => {
        // ...inspect_form, manager_approval, confirm_recommendation...
        const request_more_info = wfa.playbook.activity(
            ActivityDefinitions.Core.Instruction,
            {
                $id: Now.ID['cra_request_more_info'],
                label: 'Request Additional Documentation',
                startRule: wfa.playbook.run.Manually(),
                restartRule: 'RUN_ONLY_ONCE',
            },
            { message: 'Reach out to the requester for additional documentation or test evidence before finalizing your recommendation.' },
        )
        return { inspect_form: inspect_form, manager_approval: manager_approval, confirm_recommendation: confirm_recommendation, request_more_info: request_more_info }
    },
})
```

Global (playbook-wide) — declared directly in the `lanes` callback's return object, not nested in any lane, so it's available for the life of the playbook:

```
lanes: (params) => {
    // ...lane_0..lane_3...
    const escalate_to_cab_chair = wfa.playbook.activity(
        ActivityDefinitions.Core.Instruction,
        { $id: Now.ID['cra_escalate_cab_chair'], label: 'Escalate to CAB Chair', startRule: wfa.playbook.run.Manually(), restartRule: 'RUN_ONLY_ONCE' },
        { message: 'Escalate this change directly to the CAB chair for an out-of-band decision.' },
    )
    return { lane_0: lane_0, lane_1: lane_1, lane_2: lane_2, lane_3: lane_3, escalate_to_cab_chair: escalate_to_cab_chair }
}
```

Key restrictions (enforced at compile time — see `playbook-activities-guide.md` for details): no `order`, no `conditionToRun`, `restartRule` must be `RUN_ONLY_ONCE`, and nothing may reference it via `Run.After()` or a pill.

## Picking the Right Pattern

| If the requirement is… | Use |
| One execution path, no branching | Simple (single lane) |
| Stages that depend on each other | Multi-lane sequential |
| Independent work that joins before a final step | Multi-lane parallel with convergence |
| One-of-N routing based on a record field | Decision `match_first` |
| Several simultaneous side-effects based on conditions | Decision `match_all` |
| Routing that depends on a prior decision's result | Chained decisions |
| Conditional routing between whole lanes | Stage-level decision |
| Re-run an earlier stage/activity until it succeeds | Conditional restart with Go Back |

## Best Practices

- Build only the pattern requested. Don't add extra lanes, activities, or branches "just in case."

- Use descriptive branch IDs. `has_assignee`, `unassigned`, `critical_priority` are better than `branch_1`, `branch_2`.

- Always include an `else` branch. It catches unmatched conditions and prevents surprise stalls.

- Use `match_first` for exclusive routing, `match_all` for parallel side-effects.

- Chain decisions for multi-step routing instead of building one decision with many overlapping conditions.

- Use stage-level decisions only for lane routing — for in-lane branching, place the decision inside the lane.

- Reference prior activity outputs with `wfa.playbook.dataPill(activity.outputs.record.field)` — dot-walk through reference fields rather than splitting outputs across many fields.

## Important Notes

- Every lane must appear in the `return` object of the `lanes` callback — omitting a lane silently drops it.

- Every activity must appear in the `return` object of the `activities` callback — omitting an activity silently drops it from the lane.

- At least one lane must use `wfa.playbook.run.Immediately()` — otherwise nothing will run.

- `order` controls display position in Playbook Designer; `startRule` controls execution order. They are independent.

- Playbooks deploy in a draft state. Activate the playbook in Playbook Designer before it will execute.

Version: 4.14.0

# State Models

Guide for creating ServiceNow State Models using the Fluent API. A State Model defines the states a record can be in, the valid transitions between them, and the conditions that gate each transition — for example, blocking a Change from "Assess" to "Authorize" until an approval condition is met. A single `StateModel()` call creates the model record plus all of its state, transition, and condition records.

## ⚠️ CRITICAL RULE — never gate a transition with a Business Rule (any model, any table)

For every state model, on every table, the gate logic belongs in a State Model transition condition — never in hand-written Business Rule logic.

❌ Do not create a `BusinessRule` that calls `current.setAbortAction(true)` to block the move.

Who runs those conditions differs by table — but the gate logic is always the condition, never the BR:

- `change_request` / `problem` / `problem_task` — the platform ships OOB enforcement that evaluates your conditions automatically. You write no Business Rule at all.

- Any other table ( custom tables, …) — conditions still hold the gate logic, but nothing evaluates them until you add the generic `evaluateTransition` enforcement rule from Enforcing transitions at runtime. That one rule is plumbing — it calls `STTRMModel.evaluateTransition` and contains no gate-specific logic. Never write a per-transition "prevent" rule.

## When to Use

- Defining controlled state progression for a table (which states exist, and which moves between them are allowed)

- Gating state transitions on field values (encoded query) or server-side logic (script)

- Requiring a field before a particular move between states (a transition gate) — use a `'Mandatory Fields'` condition, not a Data Policy (see `data-policy-guide` When NOT to Use)

- Driving automatic transitions when conditions become true

- Creating a custom change/problem/problem-task model

Two outputs are mandatory (full detail in Instructions steps 6–7):

- Gate logic is always a transition condition, never a Business Rule — no `setAbortAction` to block a move.

- A `change_request` model with an `Assess`/`Authorize` state also needs a companion `Flow` that requests CAB approval, with its trigger scoped to this model (`chg_model`). A model without its Flow — or an unscoped Flow — is a bug.

### Transition gate vs. blanket state condition

The test: would the rule still apply if the record reached the target state some other way — import, script, direct write — not just via this move? If yes, it's a Data Policy condition on the state value. If it only applies to that specific move, it's a State Model transition condition. Wording like "before moving to X" or "in order to transition to X" is a hint, not a strict match — apply the test. See `data-policy-guide`.

Reach for a State Model — not a Business Rule — when a requirement reads like any of these (these are the patterns a planner will phrase, and they all map to a transition change, not a script):

- "Prevent records from being cancelled / reopened / reverted after reaching state X" — e.g. an emergency change in Implement or later can no longer be cancelled. Remove the disallowed transition out of the protected states.

- "Block backward transitions for a specific change type" — e.g. emergency changes can only move forward. Omit the reverse transitions for that model.

- "Ensure records can only move forward through the process" — model one-way (forward-only) progression by declaring only forward transitions.

- "Remove a valid state transition for a subset of records" — give that subset its own model (or edit the OOB model) with the transition omitted.

- "Prevent / block a transition to state X until `<some condition>` is met" — e.g. prevent moving to Review or Closed while open change tasks exist. This is a transition condition on that specific move: an encoded query (`condition`), a `'Mandatory Fields'` condition for presence checks, or a `conditionScript` for logic like counting open child tasks (see the `check-open-tasks.js` example). It is not a Business Rule (see `business-rule-guide` When NOT to Use).

Note: `StateModel` creates model metadata only — it does not assign the model, enforce transitions, or validate fields. Those are wired separately (see Prerequisites, Enforcing transitions at runtime, and Instructions step 12).

## Prerequisites — the target table needs a model reference field

A state model is only enforced at runtime if the target table has a reference field pointing to its model table. The platform reads that field to know which model governs each record. Without it, `StateModel` builds and installs cleanly but does nothing — the model metadata exists with no field to link it to a record.

- `change_request`, `problem`, and `problem_task` already ship with this field (`chg_model`, `prb_model`, `prb_task_model`) and assign the model out of the box — nothing to add.

- Custom tables do not have this field. Before creating a `StateModel` for a custom table you MUST:

- Add a reference field to `sttrm_model` — `ReferenceColumn({ referenceTable: 'sttrm_model' })` in the table's schema.

- Create a `BusinessRule` (before/insert) that assigns the model to new records (and, if needed, existing ones).

Skipping either step is the most common reason a built state model never takes effect. See the Custom table workflow example below for the full pattern.

## Instructions

- Confirm the table can hold a model: `change_request`, `problem`, and `problem_task` are ready to use. For a custom table, add a model reference field and an assigning `BusinessRule` first — see Prerequisites above, or the built model is never enforced.

- Pick the target table first: Set `table` to the table the model governs (`change_request`, `problem`, `problem_task`, or a custom table). The plugin auto-detects the model table (see Polymorphic model-table detection) — you never name the model table directly.

- Name your states with friendly keys: The keys of the `states` object (e.g. `new`, `assess`) are developer-chosen identifiers. Transitions reference states by these keys via `from`/`to` — never by sys_id.

- Mark exactly one initial state: Set `initial: true` on the single state new records start in.

- Reference only defined states: Every transition's `from` and `to` must be a key present in `states`. The plugin emits a build error otherwise.

- Gate with a condition, never a Business Rule: Every transition gate — block/prevent/require-before-moving — is a transition `condition`/`conditionScript`/`'Mandatory Fields'` on that move. NEVER emit a `BusinessRule` that calls `current.setAbortAction(true)` to block a state change. This is the single most-violated rule; see the CRITICAL RULE at the top and Transition gate vs. blanket state condition.

- Change model + `Assess`/`Authorize` state = model + Flow (both required): For a `change_request` model that includes an `Assess` (`-4`) or `Authorize` (`-3`) state, you MUST also emit a companion `Flow` that requests CAB approval when the record enters that state — regardless of whether a transition condition explicitly checks `approval`. `StateModel` never sets `approval` itself, so the model alone is inert and the record gets stuck. Scope the Flow's trigger to this model (`chg_model=<sys_id>`, or `chg_model.name=<model name>` when unique) so it fires only for records on the model you created — never for every change model on the table. Emitting such a model without the Flow, or a Flow that isn't scoped to the model, is a bug. See Approval-gated transition.

- Choose query OR script per condition: A condition uses `condition` (an encoded query) OR `conditionScript` (a server-side script) — never both. Setting both is a build error.

- Keep scripts in files: Use `Now.include('./check.js')` for `conditionScript` so the logic lives in a real `.js` file with IDE support. The script must return a boolean and must not use `gs.addErrorMessage`/`gs.addInfoMessage`.

- Order multiple conditions: When a transition has more than one condition, set `order` (lower runs first; default 100).

- Do not set computed fields: The state `label` you provide is the display label; never set platform-computed identity fields such as the transition name (there is no transition `name` property — see State keys vs state values).

- Wire up the rest separately: Use `BusinessRule` to assign the model, `UIPolicy`/`DataPolicy` for field rules, and `Choice` for trigger values. (Assignment/enforcement rules are fine — the never-a-BR rule is specifically about transition gating.)

## API Reference

See the `statemodel-api` topic for the full property reference.

## Key Concepts

### Polymorphic model-table detection

You always pass the target table (`change_request`, `problem`, etc.) — not the model table. The plugin selects the correct model subclass and sets `sys_class_name`:

| `table` | Model table written |
| `change_request` | `chg_model` |
| `problem` | `prb_model` |
| `problem_task` | `prb_task_model` |
| any other table | `sttrm_model` (base) |

Class-specific properties only apply to the table that has them:

- `availableInUI` and `recordPreset` → `change_request` (chg_model) only

- `taskType` → `problem_task` (prb_task_model) only — controls which kinds of tasks the model governs: `'general'` (standard), `'rca'` (root-cause-analysis), or `'model'` (template)

- `defaultModel` → maps to the class-specific flag (`default_change_model` / `default_prb_model` / `default_prb_task_model`)

- `description` → stored on the subclass tables (chg_model / prb_model / prb_task_model); on the base `sttrm_model` it has no backing column

### State keys vs state values

A state has both a developer-facing key (the `states` object key, e.g. `new`) and a value (`value`, e.g. `'-5'`) stored in the record's state field. Transitions wire states together by key; the plugin resolves keys to the generated `sttrm_state` records and writes their sys_ids into `from_state`/`to_state`. There is no transition `name` property — the platform's "Populate transition name" business rule does not fire on SDK install, so the plugin sets the name for you using the out-of-box convention `"{fromLabel} to {toLabel}"` (e.g. `"Assess to Authorize"`).

### Condition: encoded query vs script

Each condition gates a transition in one of two mutually-exclusive ways:

- `condition` — an encoded query evaluated against the record. The transition is allowed only when it matches (e.g. `approval=approved^EQ`).

- `conditionScript` — a server-side script returning a boolean (`true` = allow, `false` = block). Use `Now.include('./file.js')`. The script receives the `current` GlideRecord.

Conditions run across REST, Flow, and UI channels, so scripts must not contain UI-only code such as `gs.addErrorMessage`.

The platform's "Requires" field maps to `conditionType`. Set it to an out-of-box type name and the plugin resolves it to the matching `sttrm_condition_type` reference.

### Automatic transitions

Set `automatic: true` to make the platform move the record automatically once the transition's conditions are satisfied (otherwise the transition is user-initiated).

### User Criteria access control (advancedSecurity)

`readRoles`/`writeRoles` are role-based — anyone holding the role gets access. `advancedSecurity` unlocks a second, richer access layer built on User Criteria (`user_criteria`), which can match on company, department, group, location, role, user, or a custom script — not just role membership:

- `availableFor` — User Criteria that grant read access, in addition to `readRoles`.

- `writableFor` — User Criteria that grant write access, in addition to `writeRoles`.

- `notAvailableFor` — User Criteria explicitly excluded, overriding both the above and any matching roles.

All three are no-ops unless `advancedSecurity: true` is also set — the platform only evaluates them when advanced security is enabled. Pass a `user_criteria` sys_id string or a `Record<'user_criteria'>` reference for each entry.

### Enforcing transitions at runtime (non-change/problem/problem-task tables)

State model metadata is inert until something checks it when a record is saved. The platform ships enforcement business rules for `change_request`, `problem`, and `problem_task` only. For any other table — a custom table, etc. — you must add your own, or the model is never consulted and no transition is ever blocked.

Add a `BusinessRule` on the target table that:

- runs `when: 'before'`, `action: ['update']`, with a `filterCondition` that names the actual state column followed by `VALCHANGES^EQ` (e.g. `'stateVALCHANGES^EQ'`, or `'priorityVALCHANGES^EQ'` when the state field is `priority`) so it fires only when that field changes, and a low `order` (e.g. `50`) so it runs before other rules. The filter must match the real column name — a `state` field renamed to something else needs the new name here, or the rule never fires;

- queries `sttrm_model` for the active model on the table, calls `model.evaluateTransition(previousState, current)` through the `STTRMModel` script include, and on a blocked result calls `gs.addErrorMessage(...)` and `current.setAbortAction(true)`.

Three SDK-specific rules apply to that script:

- Inline the script as a string literal — do not use `Now.include()`. The build type-checks included `.js` files and rejects the `global.` namespace; a template-literal `script` avoids that while keeping correct runtime behavior.

- In a scoped app, qualify the script include as `global.STTRMModel`. Without `global.` it resolves to `undefined` at runtime.

- Do not interpolate `Now.ID[...]` into a script (or any string) field. `Now.ID` only resolves to a sys_id in value/reference positions (e.g. `$id`); inside a template literal it renders the raw key name, not the sys_id. Resolve the record you need at runtime instead (see the assign-model rules below).

A scoped app also needs cross-scope privileges: `write` on the target table (`sys_db_object`), `read` on `sttrm_model` / `sttrm_state` / `sttrm_state_transition` / `sttrm_transition_condition`, and `execute` on the `STTRMModel` script include (`sys_script_include`). See the `cross-scope-privilege` topic.

### Identity (`$id` is the sole mechanism)

`$id` is required on every row a `StateModel` produces — the model, every state, every transition, every condition, every state attribute, and every condition field. There is no coalesce fallback for any of them: the platform allows more than one record sharing what looks like a natural key (two states with the same `value`, an automatic and a manual transition between the same two states, two attribute links between the same state and attribute, and so on), so nothing except an explicit `$id` can safely stand in for identity.

Give app-owned rows a stable `Now.ID['...']` and keep reusing the same key across rebuilds — that's what makes rebuilds idempotent (the same key always resolves to the same generated sys_id). Changing which `Now.ID[...]` key a row uses creates a new record rather than updating the old one.

### Editing out-of-box models

To edit an out-of-box (OOB) row in place, use its real sys_id as `$id` — for the model itself, and for every state, transition, and condition you want to update rather than create. The build emits an `INSERT_OR_UPDATE` carrying that sys_id, so the install updates the existing row instead of creating a duplicate.

- Every row without an explicit OOB `$id` is always a new record. Give a new state/transition/condition a fresh `Now.ID['...']` and it inserts alongside the OOB rows — this is how you add to an existing OOB model. There's no shorthand for "just match by value/from/to" — the platform's own duplicate-permissive design means only an explicit `$id` is unambiguous.

- States are not exempt — a state you're only referencing (e.g. as a transition endpoint you aren't otherwise touching) still needs its real sys_id, or it will be created as a new state.

Use the `now-sdk query` CLI command (see the `query-guide` topic) to retrieve the exact sys_ids of the OOB models, states, transitions, and conditions you need, without manual lookup.

Every row you declare is fully re-written, so omitted fields reset to platform defaults. When editing OOB rows you must restate the values you want to keep, and declare only the rows you need to reach.

Delete an OOB record with `Now.del('<table>', '<sys_id>' | { ...keys })`. The keys form throws if more than one record matches — since the platform allows duplicate transitions between the same two states, prefer the exact sys_id when you know it. Note that `Now.del()` can only delete records that are not owned by a scope that your application cannot write to. OOB records in the global scope can be deleted from a global-scope app; scoped apps are restricted by the platform.

### Choosing which states to declare

Which states are available to declare depends on how the model resolves its state field, and that resolution works differently for the two model shapes:

#### Change, problem, and problem task models

These three tables have a dedicated model subclass (`chg_model` / `prb_model` / `prb_task_model`) and a conventional state field — `stateField` defaults to `'state'` and is effectively fixed. The states available to declare come straight from that one field's existing choice list on the target table: look it up with `now-sdk query`, or query `sys_choice` where `element=state` and `name=<table>`.

#### Custom (base `sttrm_model`) models

Every other table — including OOB tables you haven't built a dedicated model class for, not just your own custom tables — uses the base `sttrm_model`, and here the resolution is two levels deep. First, the target `table` determines which of that table's own columns are even eligible as `stateField` — the platform only offers columns it renders as a genuine Choice dropdown, not every column on the table. Once a `stateField` is picked, the states available to declare come from that specific field's choice list, the same way as above: query `sys_choice` where `element=<stateField>` and `name=<table>` — checking a parent table's choice list instead if the field is inherited rather than owned directly by the target table. For a field on a custom table, it's simply whatever `choices` you defined directly on that column.

In both cases, use `now-sdk query` to confirm current choice values for your instance rather than trusting hardcoded documentation, since OOB choices can be customized.

## Properties

The full property reference — including the nested `State`, `Transition`, `TransitionCondition`, and `StateAttribute` tables — lives in the `statemodel-api` topic. Two points that matter most for the patterns here:

- `table` (required) drives both model-table selection and which class-specific properties apply — see Polymorphic model-table detection.

- `states` and `transitions` are both optional — omit both for a model-only update (see Editing out-of-box models).

## Examples

### Minimal — linear progression

Required properties only; no conditions.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['state-model-basic'],
    name: 'Simple Change Model',
    table: 'change_request',
    stateField: 'state',
    states: {
        new: { $id: Now.ID['state-model-basic-new'], label: 'New', value: '-5', sequence: 0, initial: true },
        assess: { $id: Now.ID['state-model-basic-assess'], label: 'Assess', value: '-4', sequence: 1 }, // Assess/Authorize present → this change model REQUIRES a companion Flow (see 'Approval-gated transition')
        closed: { $id: Now.ID['state-model-basic-closed'], label: 'Closed', value: '3', sequence: 2 },
    },
    transitions: [
        { $id: Now.ID['state-model-basic-new-to-assess'], from: 'new', to: 'assess' },
        { $id: Now.ID['state-model-basic-assess-to-closed'], from: 'assess', to: 'closed' },
    ],
})
```

This change model has an `Assess` state, so a production build MUST also add the companion `Flow` (see Approval-gated transition). It is omitted here to keep the minimal example focused.

### Encoded-query conditions, and automatic transitions

Gate transitions on field values. `automatic: true` (see Automatic transitions in Key Concepts) is shown below on `assess`→`authorize`.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['state-model-with-conditions-example'],
    name: 'Field-Gated Change Model',
    table: 'change_request',
    stateField: 'state',
    states: {
        new: { $id: Now.ID['state-model-cond-new'], label: 'New', value: '-5', initial: true },
        assess: { $id: Now.ID['state-model-cond-assess'], label: 'Assess', value: '-4' }, // Assess/Authorize present → this change model REQUIRES a companion Flow (see 'Approval-gated transition')
        authorize: { $id: Now.ID['state-model-cond-authorize'], label: 'Authorize', value: '-3' },
    },
    transitions: [
        {
            $id: Now.ID['state-model-cond-new-to-assess'],
            from: 'new',
            to: 'assess',
            conditions: [
                {
                    $id: Now.ID['state-model-cond-required-fields'],
                    name: 'Required fields',
                    conditionType: 'Mandatory Fields',
                    fields: [{ $id: Now.ID['state-model-cond-required-fields-short-desc'], name: 'short_description' }],
                    order: 100,
                },
            ],
        },
        {
            $id: Now.ID['state-model-cond-assess-to-authorize'],
            from: 'assess',
            to: 'authorize',
            automatic: true,
            conditions: [
                { $id: Now.ID['state-model-cond-not-on-hold'], name: 'Not on hold', conditionType: 'Transition Condition', condition: 'on_hold=false^EQ', order: 100 },
            ],
        },
    ],
})
```

This change model has `Assess`/`Authorize` states, so a production build MUST also add the companion `Flow` (see Approval-gated transition), scoped to this model via `chg_model`. Omitted here to focus on the conditions.

### Approval-gated transition — pair the Change Model with a Flow

## ⚠️ REQUIRED — emit BOTH artifacts below. A change model (with an Assess or Authorize state) without its Flow is a bug.

This section produces two records that must ship together: (1) the `StateModel` with the approval condition, and (2) the `Flow` that requests the approval. Emitting only Artifact 1 is the single most common failure here — it leaves the record permanently stuck because nothing ever sets `approval=approved`. If you generate the model below, you MUST also generate the Flow below. The Flow's trigger MUST be scoped to this specific model via `chg_model` — an unscoped trigger fires for every change model on the table, not just the one you created.

For a `change_request` model, `StateModel` only defines the gate (`approval=approved^EQ`) — it never changes `approval` itself, so without the Flow an `automatic` transition stays put and a manual one is rejected the instant it's clicked, leaving the change stuck in `Assess`.

The real OOB `Emergency` and `Normal` change models pair their `Authorize` state with a companion Flow (`Change - Emergency - Authorize`, `Change - Normal - Authorize`) that requests CAB approval. The Fluent equivalent uses the built-in `askForApproval` action.

Artifact 1 — the State Model (the `assess`→`authorize` gate checks `approval`):

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['approval-gated-model'],
    name: 'Gated Change Model',
    recordPreset: 'type=emergency^EQ',
    table: 'change_request',
    stateField: 'state',
    states: {
        new: { $id: Now.ID['approval-gated-new'], label: 'New', value: '-5', sequence: 0, initial: true },
        assess: { $id: Now.ID['approval-gated-assess'], label: 'Assess', value: '-4', sequence: 1 },
        authorize: { $id: Now.ID['approval-gated-authorize'], label: 'Authorize', value: '-3', sequence: 2 },
        scheduled: { $id: Now.ID['approval-gated-scheduled'], label: 'Scheduled', value: '-2', sequence: 3 },
        implement: { $id: Now.ID['approval-gated-implement'], label: 'Implement', value: '-1', sequence: 4 },
        review: { $id: Now.ID['approval-gated-review'], label: 'Review', value: '0', sequence: 5 },
        closed: { $id: Now.ID['approval-gated-closed'], label: 'Closed', value: '3', sequence: 6 },
    },
    transitions: [
        { $id: Now.ID['approval-gated-new-to-assess'], from: 'new', to: 'assess' },
        {
            $id: Now.ID['approval-gated-assess-to-authorize'],
            from: 'assess',
            to: 'authorize',
            automatic: true,
            conditions: [
                { $id: Now.ID['approval-gated-cond-approved'], name: 'Approved', conditionType: 'Transition Condition', condition: 'approval=approved^EQ', order: 100 },
            ],
        },
        { $id: Now.ID['approval-gated-authorize-to-scheduled'], from: 'authorize', to: 'scheduled' },
        { $id: Now.ID['approval-gated-scheduled-to-implement'], from: 'scheduled', to: 'implement' },
        { $id: Now.ID['approval-gated-implement-to-review'], from: 'implement', to: 'review' },
        { $id: Now.ID['approval-gated-review-to-closed'], from: 'review', to: 'closed' },
    ],
})
```

Artifact 2 — the Flow that requests the approval. Fire it when the record first enters an approval state — `Assess` or `Authorize`, whichever it reaches first — and scope it to this model only. The trigger condition `stateIN-4,-3^approval=not requested^chg_model.name=Gated Change Model` does all three jobs:

- `stateIN-4,-3` — fires on entry to `Assess` (`-4`) or `Authorize` (`-3`). A model may have one or both; you don't need to know which.

- `approval=not requested` — the "whichever comes first" guard. `not requested` is the field's initial value (its stored value has a space; see `sys_choice`). Once the flow requests approval in the first approval state, `approval` becomes `requested`, so entering the second state won't fire it again — the record is asked once. Drop this clause only if you deliberately want a separate approval in each state.

- `chg_model.name=Gated Change Model` — required: scopes the flow to this model only; omit it and the flow fires for every change model on the table. Prefer `chg_model=<sys_id>` if the name isn't unique.

The `Assess`/`Authorize` exits may or may not carry an `approval=approved` transition condition: if they do, the approval gates the move (functional — the change can't advance until approved); if they don't, the flow still requests approval but the move isn't blocked. The trigger is identical either way — the Flow's job is only to request the approval.

```
import { action, Flow, wfa, trigger } from '@servicenow/sdk/automation'

export const requestChangeAuthorization = Flow(
    {
        $id: Now.ID['request-change-authorization-flow'],
        name: 'Request Change Authorization',
        description: 'Requests CAB approval when a change first reaches Assess or Authorize',
    },
    wfa.trigger(
        trigger.record.createdOrUpdated,
        { $id: Now.ID['request-change-authorization-trigger'] },
        {
            table: 'change_request',
            condition: 'stateIN-4,-3^approval=not requested^chg_model.name=Gated Change Model',
            run_flow_in: 'background',
            trigger_strategy: 'unique_changes',
        }
    ),
    (params) => {
        // Blocks until the approval reaches a terminal state (approved/rejected/cancelled/due-date auto-action) —
        // no separate waitForCondition step is needed after this.
        const approval = wfa.action(
            action.core.askForApproval,
            { $id: Now.ID['request-change-authorization-ask'], annotation: 'Request CAB approval' },
            {
                record: wfa.dataPill(params.trigger.current, 'reference'),
                table: 'change_request',
                approval_field: 'approval',
                journal_field: 'approval_history',
                approval_reason: 'Change authorization required',
                due_date: wfa.approvalDueDate({
                    action: 'reject',
                    dateType: 'actual',
                    date: '{}',
                    duration: 2,
                    durationType: 'days',
                    daysSchedule: '',
                }),
                approval_conditions: wfa.approvalRules({
                    conditionType: 'OR',
                    ruleSets: [
                        {
                            action: 'ApprovesRejects',
                            conditionType: 'AND',
                            rules: [[{ ruleType: 'Percent', percent: 50, users: [], groups: [wfa.dataPill(params.trigger.current.assignment_group, 'reference')], manual: false }]],
                        },
                    ],
                }),
            }
        )

        wfa.flowLogic.if(
            { $id: Now.ID['request-change-authorization-if-approved'], condition: `${wfa.dataPill(approval.approval_state, 'string')}=approved`, annotation: 'If approved' },
            () => {
                wfa.action(
                    action.core.log,
                    { $id: Now.ID['request-change-authorization-log'] },
                    { log_level: 'info', log_message: `${wfa.dataPill(params.trigger.current.number, 'string')} authorized` }
                )
            }
        )
    }
)
```

Once the flow resolves the approval, any transition gated on `approval=approved` can proceed. See the `wfa-flow-guide` and `wfa-flow-actions-guide` topics for the full `Flow`/`askForApproval` reference.

`availableInUI` variant: Set `availableInUI: true` (`chg_model`-only) on a model like this one to make it selectable from the Change Model dropdown on the form — the platform then handles assignment itself, so no assignment `BusinessRule` is required. Leave it `false`, or omit it on `problem`/`problem_task`/custom tables (where the property doesn't exist at all), and the model must be assigned programmatically instead — see the assign-model `BusinessRule` in Custom table workflow.

### Script-based condition (Now.include)

Use a server-side script for logic an encoded query cannot express.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['state-model-with-scripts-example'],
    name: 'Scripted Change Model',
    table: 'change_request',
    stateField: 'state',
    states: {
        implement: { $id: Now.ID['state-model-script-implement'], label: 'Implement', value: '-1', initial: true },
        review: { $id: Now.ID['state-model-script-review'], label: 'Review', value: '0' },
    },
    transitions: [
        {
            $id: Now.ID['state-model-script-implement-to-review'],
            from: 'implement',
            to: 'review',
            conditions: [
                {
                    $id: Now.ID['state-model-cond-no-open-tasks'],
                    name: 'No open tasks',
                    conditionType: 'Transition Script',
                    conditionScript: Now.include('./check-open-tasks.js'),
                    description: 'All change tasks must be closed',
                    order: 100,
                },
            ],
        },
    ],
})
```

The referenced `check-open-tasks.js` returns a boolean:

```
(function (current) {
    var task = new GlideRecord('change_task')
    task.addQuery('change_request', current.sys_id)
    task.addQuery('state', '!=', '3')
    task.setLimit(1)
    task.query()
    return !task.hasNext()
})(current)
```

### Multiple conditions per transition, with required fields

All active conditions must pass; `order` sets evaluation order (lower runs first). A `'Mandatory Fields'` condition lists required fields via `fields` — each name becomes a `sttrm_transition_condition_field` row.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['state-model-multi-condition-example'],
    name: 'Multi-Condition Change Model',
    table: 'change_request',
    stateField: 'state',
    states: {
        implement: { $id: Now.ID['state-model-multi-implement'], label: 'Implement', value: '-1', initial: true },
        closed: { $id: Now.ID['state-model-multi-closed'], label: 'Closed', value: '3' },
    },
    transitions: [
        {
            $id: Now.ID['state-model-multi-implement-to-closed'],
            from: 'implement',
            to: 'closed',
            conditions: [
                {
                    $id: Now.ID['state-model-cond-mandatory-fields'],
                    name: 'Required fields',
                    conditionType: 'Mandatory Fields',
                    fields: [
                        { $id: Now.ID['state-model-field-close-code'], name: 'close_code' },
                        { $id: Now.ID['state-model-field-close-notes'], name: 'close_notes' },
                    ],
                    order: 100,
                },
                {
                    $id: Now.ID['state-model-cond-no-open-tasks-2'],
                    name: 'No open tasks',
                    conditionType: 'Transition Script',
                    conditionScript: Now.include('./check-open-tasks.js'),
                    order: 200,
                },
            ],
        },
    ],
})
```

### Role and User Criteria-based security

Restrict who can read and write records using the model with plain roles (`readRoles`/`writeRoles`), and layer richer User Criteria-based access on top with `availableFor`/`writableFor`/`notAvailableFor` — the latter three only take effect with `advancedSecurity: true` (see User Criteria access control in Key Concepts).

```
import { StateModel, Record } from '@servicenow/sdk/core'

const itilStaff = Record({ $id: Now.ID['state-model-uc-itil-staff'], table: 'user_criteria', data: { name: 'ITIL Staff' } })
const formerEmployees = Record({
    $id: Now.ID['state-model-uc-former-employees'],
    table: 'user_criteria',
    data: { name: 'Former Employees' },
})

StateModel({
    $id: Now.ID['state-model-user-criteria-example'],
    name: 'User Criteria Secured Model',
    table: 'change_request',
    stateField: 'state',
    advancedSecurity: true,
    readRoles: ['itil'],
    writeRoles: ['change_manager'],
    availableFor: [itilStaff],
    notAvailableFor: [formerEmployees],
    states: {
        new: { $id: Now.ID['state-model-uc-new'], label: 'New', value: '-5', initial: true },
        closed: { $id: Now.ID['state-model-uc-closed'], label: 'Closed', value: '3' },
    },
    transitions: [{ $id: Now.ID['state-model-uc-new-to-closed'], from: 'new', to: 'closed' }],
})
```

### System-assigned model (problem table)

A `problem` model that is not selectable in the UI dropdown, with a gated transition. `availableInUI` is chg_model-only, so it is omitted here; control selectability on problem models through assignment logic instead. Unlike `change_request`, `problem` has no `chg_model_condition_type` subclass types (`'Authorized'`, `'Not On hold'`, `'Risk evaluation'`) available to it — gate with a plain `condition`/`conditionScript` (or `'Mandatory Fields'`, which isn't chg_model-specific) instead. Only `new`, `assess`, and `closed` are declared — the states this narrower problem workflow actually uses (see Choosing which states to declare); the real OOB `problem` model has 6 states in total, but this model doesn't need the other 3.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['state-model-problem-example'],
    name: 'Custom Problem Model',
    table: 'problem',
    stateField: 'state',
    description: 'Custom problem workflow',
    states: {
        new: { $id: Now.ID['state-model-problem-new'], label: 'New', value: '101', sequence: 0, initial: true },
        assess: { $id: Now.ID['state-model-problem-assess'], label: 'Assess', value: '102', sequence: 1 },
        rootCauseAnalysis: {
            $id: Now.ID['state-model-problem-rca'],
            label: 'Root Cause Analysis',
            value: '103',
            sequence: 2,
        },
        closed: { $id: Now.ID['state-model-problem-closed'], label: 'Closed', value: '107', sequence: 5 },
    },
    transitions: [
        {
            $id: Now.ID['state-model-problem-new-to-assess'],
            from: 'new',
            to: 'assess',
            conditions: [
                {
                    $id: Now.ID['state-model-cond-assignment-group'],
                    name: 'Assignment group required',
                    conditionType: 'Mandatory Fields',
                    fields: [{ $id: Now.ID['state-model-field-assignment-group'], name: 'assignment_group' }],
                },
            ],
        },
        {
            $id: Now.ID['state-model-problem-assess-to-rootCauseAnalysis'],
            from: 'assess',
            to: 'rootCauseAnalysis',
            conditions: [],
        },
        {
            $id: Now.ID['state-model-problem-assess-to-closed'],
            from: 'assess',
            to: 'closed',
            conditions: [
                {
                    $id: Now.ID['state-model-cond-no-open-problem-tasks'],
                    name: 'No open problem tasks',
                    conditionType: 'Transition Script',
                    conditionScript: Now.include('./check-open-problem-tasks.js'),
                    description: 'All problem tasks must be closed before the problem can close',
                },
            ],
        },
    ],
})
```

The referenced `check-open-problem-tasks.js` returns a boolean:

```
(function (current) {
    var task = new GlideRecord('problem_task')
    task.addQuery('problem', current.sys_id)
    task.addQuery('state', '!=', '3')
    task.setLimit(1)
    task.query()
    return !task.hasNext()
})(current)
```

### Problem task model

Targets `problem_task` (→ `prb_task_model`); `taskType` sets the kind of task the model governs. After generating this, the model must be registered on the "Problem Task" interceptor to appear in the New chooser — see Problem task models — tell the user to register the New-record interceptor.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['prb-task-rca-model'],
    name: 'Root Cause Analysis',
    table: 'problem_task',
    stateField: 'state',
    taskType: 'rca',
    description: 'Root-cause-analysis problem task workflow',
    states: {
        open: { $id: Now.ID['prb-task-rca-open'], label: 'Open', value: '1', sequence: 0, initial: true },
        wip: { $id: Now.ID['prb-task-rca-wip'], label: 'Work in Progress', value: '2', sequence: 1 },
        closed: { $id: Now.ID['prb-task-rca-closed'], label: 'Closed Complete', value: '3', sequence: 2 },
    },
    transitions: [
        {
            $id: Now.ID['prb-task-rca-open-to-wip'],
            from: 'open',
            to: 'wip',
            conditions: [
                {
                    $id: Now.ID['prb-task-rca-cond-assignee'],
                    name: 'Assignee required',
                    conditionType: 'Mandatory Fields',
                    fields: [{ $id: Now.ID['prb-task-rca-field-assigned-to'], name: 'assigned_to' }],
                },
            ],
        },
        {
            $id: Now.ID['prb-task-rca-wip-to-closed'],
            from: 'wip',
            to: 'closed',
            conditions: [
                {
                    $id: Now.ID['prb-task-rca-cond-close-notes'],
                    name: 'Close notes required',
                    conditionType: 'Mandatory Fields',
                    fields: [{ $id: Now.ID['prb-task-rca-field-close-notes'], name: 'close_notes' }],
                },
            ],
        },
    ],
})
```

## ⚠️ REQUIRED — after generating a `problem_task` model, tell the user to register it on the interceptor.

A `problem_task` model builds fine but will not appear in the New Problem Task chooser until a matching `sys_wizard_answer` is added to the OOB "Problem Task" interceptor — that list is hand-authored per model, not dynamic, and the SDK does not create it. So always surface a message like:

Action required: Model `<model name>` was created but won't show in the New Problem Task chooser. Open System Definition → Interceptors → "Problem Task" (`sys_wizard 34d12b0fb79c821041c2feb0be11a997`) and add an Answer with Type `Answer`, User Prompt `<model name>`, Target URL `problem_task.do?sys_id=-1&sysparm_query=prb_task_model=<model sys_id>`, Roles `problem_task_analyst,sn_problem_write,itil`, Order after existing entries (e.g. `300`), Active `true`. `<model sys_id>` is the generated `prb_task_model` sys_id (from the model's `$id`).

Not needed for `taskType: 'model'` (system-assigned template tasks).

### Change-only condition types

Beyond the generic `'Mandatory Fields'` / `'Transition Condition'` / `'Transition Script'`, `chg_model` transitions can use change-only condition types (mapped to `chg_model_condition_type`): `'Authorized'`, `'Not On hold'`, and `'Risk evaluation'` — plus the base `'Task is Approved'` / `'Task is Rejected'`. Use them like any other condition, e.g. `{ $id: Now.ID['authorized'], name: 'Authorized', conditionType: 'Authorized', order: 100 }`. These change-only types are not available on `problem`/`problem_task`/custom (`sttrm_model`) models.

### Custom table workflow

For custom tables, you must create the model reference field and use the base `sttrm_model` table. `stateField` can be any choice field on the target table — it doesn't have to be named `state`; this example tracks a `priority` column instead. A custom table also gets no OOB transition enforcement (that's exclusive to `change_request`/`problem`/`problem_task`) — step 4 below is required, not optional, or every transition condition is silently inert; see Enforcing transitions at runtime.

```
import { StateModel, BusinessRule, Table, StringColumn, ChoiceColumn, ReferenceColumn } from '@servicenow/sdk/core'

// 1. Custom table with mandatory model reference field
export const x_custom_workflow = Table({
    name: 'x_custom_workflow',
    label: 'Custom Workflow',
    schema: {
        name: StringColumn({ label: 'Name', maxLength: 100 }),
        priority: ChoiceColumn({
            label: 'Priority',
            choices: { low: 'Low', medium: 'Medium', high: 'High' },
            default: 'low',
            dropdown: 'dropdown_with_none',
        }),
        // REQUIRED: Reference field to sttrm_model for state model assignment
        model: ReferenceColumn({ label: 'Model', referenceTable: 'sttrm_model' }),
    },
})

// 2. State model for the custom table (creates base sttrm_model record)
StateModel({
    $id: Now.ID['custom_workflow_model'],
    name: 'Custom Workflow Model',
    table: 'x_custom_workflow', // Custom table → base sttrm_model
    stateField: 'priority',
    states: {
        low: { $id: Now.ID['custom_workflow_low'], label: 'Low', value: 'low', initial: true },
        medium: { $id: Now.ID['custom_workflow_medium'], label: 'Medium', value: 'medium' },
        high: { $id: Now.ID['custom_workflow_high'], label: 'High', value: 'high' },
    },
    transitions: [
        { $id: Now.ID['custom_workflow_low_to_medium'], from: 'low', to: 'medium' },
        { $id: Now.ID['custom_workflow_medium_to_high'], from: 'medium', to: 'high' },
    ],
})

// 3. BusinessRule to assign the model to new records. This table has a single active model, so
//    resolve it at runtime by table_name (do not interpolate Now.ID into the script string —
//    inside a template literal it renders the key name, not the sys_id).
BusinessRule({
    $id: Now.ID['assign_custom_workflow_model'],
    name: 'Assign Custom Workflow Model',
    table: 'x_custom_workflow',
    when: 'before',
    action: ['insert'],
    filterCondition: 'modelISEMPTY',
    script: `(function executeRule(current, previous) {
    var modelGr = new GlideRecord('sttrm_model');
    modelGr.addQuery('table_name', current.getTableName());
    modelGr.addActiveQuery();
    modelGr.orderBy('order');
    modelGr.setLimit(1);
    modelGr.query();
    if (modelGr.next()) {
        current.setValue('model', modelGr.getUniqueValue());
    }
})(current, previous);`,
})

// 4. For tables without OOB enforcement, a BusinessRule to enforce the model's transitions on save
// (see *Enforcing transitions at runtime* for what this script does and why it's inline rather than Now.include()).
BusinessRule({
    $id: Now.ID['enforce_custom_workflow_transitions'],
    name: 'Custom Workflow Model: Check State Transition',
    table: 'x_custom_workflow',
    when: 'before',
    action: ['update'],
    filterCondition: 'priorityVALCHANGES^EQ',
    order: 50,
    script: `(function executeRule(current, previous) {
    if (!previous) return;

    var modelGr = new GlideRecord('sttrm_model');
    modelGr.addQuery('table_name', current.getTableName());
    modelGr.addActiveQuery();
    modelGr.orderBy('order');
    modelGr.setLimit(1);
    modelGr.query();
    if (!modelGr.next()) return;

    var stateField = modelGr.getValue('state_field');
    var previousState = previous.getValue(stateField);
    var currentState = current.getValue(stateField);
    if (previousState === currentState) return;

    var model = new global.STTRMModel(modelGr);
    var result = model.evaluateTransition(previousState, current);
    if (!result.transition_available) {
        var msg = gs.getMessage("Model '{0}' prevented state transition from {1} to {2}",
            [modelGr.getDisplayValue('name'), previous.getDisplayValue(stateField), current.getDisplayValue(stateField)]);
        if (result.conditions) {
            var failed = result.conditions
                .filter(function (c) { return !c.passed && c.condition && c.condition.name; })
                .map(function (c) { return c.condition.name; });
            if (failed.length) {
                msg = gs.getMessage("Model '{0}' prevented state transition from {1} to {2} because these transition conditions failed: {3}",
                    [modelGr.getDisplayValue('name'), previous.getDisplayValue(stateField), current.getDisplayValue(stateField), failed.join(', ')]);
            }
        }
        gs.addErrorMessage(msg);
        current.setAbortAction(true);
    }
})(current, previous);`,
})
```

### Guided form UX: restrict the state dropdown and set mandatory fields dynamically

This is form polish, not required for the model to build or enforce transitions — generate it when the user actually asks for behavior like "only show valid next states in the dropdown" or "make fields mandatory based on the state being selected." Do not emit it automatically alongside every `StateModel`.

Two artifacts, continuing the `x_custom_workflow` example from Custom table workflow above:

- A `display` `BusinessRule` that computes the current record's valid next states, plus any `'Mandatory Fields'` condition on each of those transitions, and stores both on `g_scratchpad`.

- Two `ClientScript`s: an `onLoad` that narrows the state field's options to just the current value + valid next states, and an `onChange` (on the state field) that marks the right fields mandatory the instant the user picks a target state that requires them.

```
import { BusinessRule, ClientScript } from '@servicenow/sdk/core'

// Computes valid next states + their mandatory fields for the guided UX below
BusinessRule({
    $id: Now.ID['custom_workflow_populate_scratchpad'],
    name: 'Custom Workflow: Populate Scratchpad',
    table: 'x_custom_workflow',
    when: 'display',
    script: Now.include('./populate-scratchpad.js'),
})

// Narrows the state field's options to the current value + valid next states
ClientScript({
    $id: Now.ID['custom_workflow_show_valid_states'],
    name: 'Custom Workflow: Show valid states',
    table: 'x_custom_workflow',
    type: 'onLoad',
    script: Now.include('./show-valid-states.client.js'),
})

// Marks fields mandatory the instant the user picks a target state that requires them.
// `field` must be a literal here — it's the ClientScript record's own onChange binding, not
// something computed — so it must match whatever `stateField` this table's StateModel actually
// uses (here, 'priority'). Update it if you reuse this pattern on a table with a different state field.
ClientScript({
    $id: Now.ID['custom_workflow_mandatory_fields'],
    name: 'Custom Workflow: Mandatory fields on state change',
    table: 'x_custom_workflow',
    type: 'onChange',
    field: 'priority',
    script: Now.include('./mandatory-fields.client.js'),
})
```

`populate-scratchpad.js` — reads the model's own transition/condition records directly, no Change-specific script includes needed:

```
(function executeRule(current, previous) {
    if (current.model.nil()) return;

    // Read the state field from the model itself — never hardcode it. stateField can be any
    // choice field on the target table (see 'Choosing which states to declare'), so the client
    // scripts below read it from g_scratchpad instead of assuming a field name.
    var stateField = current.model.state_field.toString();
    g_scratchpad.state_field = stateField;

    var stateGr = new GlideRecord('sttrm_state');
    stateGr.addQuery('sttrm_model', current.model);
    stateGr.addQuery('state_value', current.getValue(stateField));
    stateGr.query();
    if (!stateGr.next()) return;

    var validStates = [current.getValue(stateField)];
    var mandatoryFields = {};

    var transGr = new GlideRecord('sttrm_state_transition');
    transGr.addQuery('from_state', stateGr.getUniqueValue());
    transGr.query();
    while (transGr.next()) {
        var toValue = transGr.to_state.state_value.toString();
        validStates.push(toValue);

        var fields = [];
        var condGr = new GlideRecord('sttrm_transition_condition');
        condGr.addQuery('sttrm_state_transition', transGr.getUniqueValue());
        condGr.addQuery('condition_type.name', 'Mandatory Fields');
        condGr.query();
        while (condGr.next()) {
            var fieldGr = new GlideRecord('sttrm_transition_condition_field');
            fieldGr.addQuery('transition_condition', condGr.getUniqueValue());
            fieldGr.query();
            while (fieldGr.next()) fields.push(fieldGr.getValue('name'));
        }
        mandatoryFields[toValue] = fields;
    }

    g_scratchpad.valid_states = validStates;
    g_scratchpad.mandatory_fields = mandatoryFields;
})(current, previous);
```

`show-valid-states.client.js`:

```
function onLoad() {
    if (!g_scratchpad.valid_states || !g_scratchpad.state_field) return;

    var stateField = g_scratchpad.state_field;

    // Only narrow the options if the field is actually editable
    // Rewriting options on a read-only
    // field is pointless and can behave inconsistently across UI16/Workspace/Service Portal.
    var isReadOnly = false;
    var stateControl = g_form.getControl(stateField);
    if (stateControl instanceof HTMLSelectElement) {
        var stateElement = g_form.getElement(stateField);
        isReadOnly = g_form.isReadOnly(stateElement, stateControl);
    } else {
        isReadOnly = g_form.isReadOnly(stateField); // Service Portal / Workspace
    }
    if (isReadOnly) return;

    var currentValue = g_form.getValue(stateField);
    g_form.clearOptions(stateField);
    g_scratchpad.valid_states.forEach(function (v) {
        g_form.addOption(stateField, v, v);
    });
    g_form.setValue(stateField, currentValue);
}
```

`mandatory-fields.client.js`:

```
function onChange(control, oldValue, newValue, isLoading, isTemplate) {
    if (isLoading || newValue === '' || !g_scratchpad.mandatory_fields) return;

    (g_scratchpad._mandatory_fields_set || []).forEach(function (f) {
        g_form.setMandatory(f, false);
    });

    var fields = g_scratchpad.mandatory_fields[newValue] || [];
    fields.forEach(function (f) {
        g_form.setMandatory(f, true);
    });
    g_scratchpad._mandatory_fields_set = fields;
}
```

### State attributes

Attach `sttrm_state_attribute` links to a state. Each link requires its own `$id` — the platform allows more than one link between the same state and attribute.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['state-model-state-attributes'],
    name: 'State Attribute Model',
    table: 'change_request',
    stateField: 'state',
    states: {
        implement: {
            $id: Now.ID['state-model-attr-implement'],
            label: 'Implement',
            value: '-1',
            initial: true,
            attributes: [
                { $id: Now.ID['state-model-attr-allow-implementation'], attribute: 'allowImplementation' },
                { $id: Now.ID['state-model-attr-allow-ci-modification'], attribute: 'allowCiModification', active: false },
            ],
        },
        review: { $id: Now.ID['state-model-attr-review'], label: 'Review', value: '0' },
    },
    transitions: [{ $id: Now.ID['state-model-attr-implement-to-review'], from: 'implement', to: 'review' }],
})
```

### Add a condition to an out-of-box transition

Declare each OOB row (model, states the transition connects, and the transition itself) with its real sys_id, and nest the new condition under it with a fresh `Now.ID[...]`. OOB field values (`availableInUI`, the states' `sequence`) are restated to avoid clobbering them. The new `pending_closure` state isn't an OOB row, so it gets a fresh `Now.ID[...]` too — that's what makes it a new insert rather than an edit.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: '007c4001c343101035ae3f52c1d3aeb2', // OOB "Normal" chg_model sys_id
    name: 'Normal',
    table: 'change_request',
    stateField: 'state',
    availableInUI: true, // restate OOB value — omitting resets it to default
    states: {
        impl: { $id: '2d0d4801c343101035ae3f52c1d3ae62', label: 'Implement', value: '-1', sequence: 4 }, // OOB Implement state sys_id
        review: { $id: '660d4801c343101035ae3f52c1d3ae4d', label: 'Review', value: '0', sequence: 5 },   // OOB Review state sys_id
        pending_closure: { $id: Now.ID['state-model-pending-closure'], label: 'Pending Closure', value: '-6', sequence: 6 }, // new — inserted
    },
    transitions: [
        {
            $id: '7a0d2ccdc343101035ae3f52c1d3ae2e', // OOB Implement → Review transition sys_id
            from: 'impl',
            to: 'review',
            conditions: [
                {
                    $id: Now.ID['state-model-cond-no-open-change-tasks'],
                    name: 'No open change tasks',
                    conditionScript: Now.include('./no-open-change-tasks.js'),
                    conditionType: 'Transition Script',
                },
            ],
        },
    ],
})
```

### Model-only update

Change a single model field without touching its states or transitions — omit `states`/`transitions`.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: 'aedc6a625323101034d1ddeeff7b1296', // OOB "Unauthorized Change" chg_model sys_id
    name: 'Unauthorized Change',
    table: 'change_request',
    stateField: 'state',
    recordPreset: 'type=emergency^unauthorized=true^EQ',
})
```

## Avoidance

Edge cases and anti-patterns — each with the wrong (❌) and right (✅) form.

### Both `condition` and `conditionScript` on one condition

They are mutually exclusive; setting both is a build error.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['avoid-both-conditions'],
    name: 'Both Conditions Model',
    table: 'change_request',
    stateField: 'state',
    states: {
        new: { $id: Now.ID['avoid-both-new'], label: 'New', value: '-5', initial: true },
        assess: { $id: Now.ID['avoid-both-assess'], label: 'Assess', value: '-4' },
    },
    transitions: [
        {
            $id: Now.ID['avoid-both-new-to-assess'],
            from: 'new',
            to: 'assess',
            // ✅ Use exactly one — here, an encoded query:
            conditions: [{ $id: Now.ID['avoid-both-cond-approved'], name: 'Approved', conditionType: 'Transition Condition', condition: 'approval=approved^EQ' }],
        },
    ],
})
```

❌ `conditions: [{ $id: Now.ID['x'], name: 'Approved', condition: 'approval=approved^EQ', conditionScript: Now.include('./x.js') }]` — build error: the two are mutually exclusive.

### Transition to an undefined state

`from`/`to` must reference a key in `states`.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['avoid-undefined-state'],
    name: 'Defined States Model',
    table: 'change_request',
    stateField: 'state',
    states: {
        new: { $id: Now.ID['avoid-undefined-new'], label: 'New', value: '-5', initial: true },
        // ✅ 'closed' must be declared before a transition can target it:
        closed: { $id: Now.ID['avoid-undefined-closed'], label: 'Closed', value: '3' },
    },
    transitions: [{ $id: Now.ID['avoid-undefined-new-to-closed'], from: 'new', to: 'closed' }],
})
```

❌ `transitions: [{ $id: Now.ID['x'], from: 'new', to: 'nonexistent' }]` — build error: `nonexistent` is not a key in `states`.

### Redundant defaults

Omit values equal to the platform default to keep code clean.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['avoid-redundant-defaults'],
    name: 'Clean Model',
    table: 'change_request',
    stateField: 'state',
    // ✅ active defaults to true, sequence to 0, condition order to 100 — omit them
    states: {
        new: { $id: Now.ID['avoid-redundant-new'], label: 'New', value: '-5', initial: true },
        assess: { $id: Now.ID['avoid-redundant-assess'], label: 'Assess', value: '-4' },
    },
    transitions: [{ $id: Now.ID['avoid-redundant-new-to-assess'], from: 'new', to: 'assess' }],
})
```

❌ `active: true`, `sequence: 0`, condition `order: 100` — redundant; these are the defaults and round-trip back as omitted.

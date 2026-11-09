Version: 4.14.0

# StateModel

Creates a State Model that defines states, transitions, and gating conditions for a table. A single `StateModel()` call produces the model record plus all of its state, transition, and condition records. The plugin auto-detects the model table from the target `table` (`change_request` → `chg_model`, `problem` → `prb_model`, `problem_task` → `prb_task_model`, any other table → the base `sttrm_model`).

## Signature

```
StateModel(config)
```

## Properties

| Property | Type | Description |
| `$id` | `Now.ID | string` | Identifier for the state model record. Use `Now.ID['...']` for app-owned models, or a raw sys_id string to edit an OOB model in place. |
| `name` | `string` | Name of the model (e.g. "Normal", "Emergency"). |
| `table` | `TableName` | Table the model applies to. Drives polymorphic model-table selection. |
| `stateField?` | `string` | Field on the table holding the state value. Defaults to `'state'` . |
| `active?` | `boolean` | Whether the model is active. Defaults to `true` . |
| `advancedSecurity?` | `boolean` | Enables User Criteria-based access control ( `availableFor` / `writableFor` / `notAvailableFor` ), in addition to `readRoles` / `writeRoles` . Defaults to `false` . |
| `readRoles?` | `(Role | string)[]` | Roles allowed to read records using this model. Pass `Role` references or role names. |
| `writeRoles?` | `(Role | string)[]` | Roles allowed to write records using this model. Pass `Role` references or role names. |
| `availableFor?` | `(string | Record<'user_criteria'>)[]` | User Criteria that grant read access, in addition to `readRoles` . Only takes effect when `advancedSecurity` is enabled. |
| `writableFor?` | `(string | Record<'user_criteria'>)[]` | User Criteria that grant write access, in addition to `writeRoles` . Only takes effect when `advancedSecurity` is enabled. |
| `notAvailableFor?` | `(string | Record<'user_criteria'>)[]` | User Criteria explicitly excluded from this model, overriding `availableFor` / `writableFor` and matching roles. Only takes effect when `advancedSecurity` is enabled. |
| `templateProposalAccess?` | `'read' | 'write'` | Who may propose new Templates ( `sttrm_template` records) for this model. `'read'` allows anyone with read access; `'write'` restricts proposal to those with write access. Applies to all model tables, independently of `advancedSecurity` . |
| `templateApprovalUsers?` | `(string | Record<'sys_user'>)[]` | Users who can approve a proposed Template before it is published. |
| `templateApprovalGroups?` | `(string | Record<'sys_user_group'>)[]` | Groups whose members can approve a proposed Template before it is published. |
| `availableInUI?` | `boolean` | Show the model in UI dropdowns. `change_request` (chg_model) only. Defaults to `true` . |
| `defaultModel?` | `boolean` | Default model for the table. Maps to the class-specific default flag. Defaults to `false` . |
| `description?` | `string` | Description. Stored only on subclass tables (chg_model / prb_model / prb_task_model). |
| `taskType?` | `'general' | 'rca' | 'model'` | Problem-task type. `problem_task` (prb_task_model) only. `'general'` for standard tasks, `'rca'` for root-cause-analysis tasks, `'model'` for template tasks. |
| `recordPreset?` | `string` | Template values applied when the model is assigned. `change_request` (chg_model) only. When set, the plugin automatically enables `apply_record_preset` so the platform applies the preset on model assignment. |
| `color?` | `string` | Background color shown in Change calendar/board views (e.g. `'green'` or `'#2E7D32'` ). `change_request` (chg_model) only. |
| `itilChangeProcess?` | `'standard' | 'normal' | 'emergency'` | ITIL change process classification. `change_request` (chg_model) only. |
| `protectionPolicy?` | `'read' | 'protected'` | Controls edit/view access for other developers after the application is installed. `'read'` : others can see the model but not change it. `'protected'` : others cannot change this record. Omit to allow other developers to customize it. |
| `states?` | `Record<string, State>` | Map of friendly state keys to state configs. Keys are referenced by transitions. Optional — omit (with `transitions` ) for a model-only update (see Editing an out-of-box model ). |
| `transitions?` | `Transition[]` | Valid transitions between states, with optional gating conditions. Optional — omit for a model-only update. |

### State

`$id` is required: the platform allows more than one state with the same `value` on the same model (tracked as separate records), so identity can never be safely derived from `value` alone.

| Property | Type | Description |
| `$id` | `Now.ID | string` | Identifier for the state record. Use `Now.ID['...']` for app-owned states, or a raw sys_id string to edit an OOB state in place. |
| `label` | `string` | Display label for the state. |
| `value` | `string | number` | Value stored in the state field. |
| `sequence?` | `number` | Display order. Defaults to `0` . |
| `initial?` | `boolean` | Marks the initial state for new records. Defaults to `false` . |
| `attributes?` | `StateAttribute[]` | Per-state attribute links ( `sttrm_state_attribute` ). |

### Transition

`$id` is required: the platform allows more than one transition between the same two states (e.g. one automatic, one manual, tracked as separate records), so identity can never be safely derived from `from`/`to` alone.

| Property | Type | Description |
| `$id` | `Now.ID | string` | Identifier for the transition record. Use `Now.ID['...']` for app-owned transitions, or a raw sys_id string to edit an OOB transition in place. |
| `from` | `string` | Source state key (must exist in `states` ). |
| `to` | `string` | Target state key (must exist in `states` ). |
| `automatic?` | `boolean` | Whether the transition happens automatically when conditions are met. Defaults to `false` . |
| `conditions?` | `TransitionCondition[]` | Conditions that gate the transition. |

### TransitionCondition

| Property | Type | Description |
| `$id` | `Now.ID | string` | Identifier for the condition record. Required — a condition's identity is never derived from `name` , since names are display/info text that can change without that change representing a new condition. Use `Now.ID['...']` for app-owned conditions, or a raw sys_id string to edit an OOB condition in place. |
| `name` | `string` | Name of the condition, shown in error messages. |
| `condition?` | `string` | Encoded query string. Mutually exclusive with `conditionScript` . |
| `conditionScript?` | `string` | Server-side script returning a boolean. Use `Now.include('./script.js')` for external files. Mutually exclusive with `condition` . |
| `conditionType?` | `ConditionType | string` | Platform "Requires" value. OOB type name ( `'Transition Condition'` , `'Transition Script'` , `'Authorized'` , `'Mandatory Fields'` , `'Not On hold'` , `'Risk evaluation'` , `'Task has been through Approval'` , `'Task is Approved'` , `'Task is Rejected'` ) or a custom `sttrm_condition_type` sys_id. Omitted → none. |
| `active?` | `boolean` | Whether the condition is active. Defaults to `true` . |
| `order?` | `number` | Evaluation order (lower first). Defaults to `100` . |
| `description?` | `string` | Description of what the condition validates. |
| `fields?` | `ConditionField[]` | Field names (on the model's target table) this condition references — written as `sttrm_transition_condition_field` rows (one per entry). Use with type-based conditions such as `'Mandatory Fields'` to list the required fields. |

### StateAttribute

`$id` is required: the platform allows more than one link between the same state and attribute (tracked as separate records), so identity can never be safely derived from `attribute` alone.

| Property | Type | Description |
| `$id` | `Now.ID | string` | Identifier for the state-attribute link record. |
| `attribute` | `StateAttributeName | string` | OOB attribute name ( `'allowImplementation'` , `'allowCiModification'` ) or a custom `sttrm_attribute` sys_id. |
| `active?` | `boolean` | Whether the attribute link is active. Defaults to `true` . |

### ConditionField

`$id` is required: the platform allows more than one field row with the same name on the same condition (tracked as separate records), so identity can never be safely derived from `name` alone.

| Property | Type | Description |
| `$id` | `Now.ID | string` | Identifier for the condition-field record. |
| `name` | `string` | Field name on the model's target table. |

## Editing an out-of-box model

`$id` is the sole identity mechanism for every row a `StateModel` produces — the model, every state, every transition, every condition, every state attribute, and every condition field. There is no coalesce fallback for any of them: the platform allows more than one record sharing what looks like a natural key (two states with the same `value`, an automatic and a manual transition between the same two states, and so on), so nothing except an explicit `$id` can safely stand in for identity.

To edit an out-of-box (OOB) model, set `$id` to the real OOB sys_id on the model and on every state, transition, and condition you want to update in place. The build emits an `INSERT_OR_UPDATE` carrying that sys_id, so the install updates the existing row instead of creating a duplicate. Use the `now-sdk query` CLI command (see the `query-guide` topic) to look up the exact sys_ids you need.

Any state, transition, or condition you declare without `$id` (using `Now.ID['...']`) is always treated as a new record — a fresh sys_id is minted and inserted alongside whatever OOB rows already exist. This is how you add a brand-new state or transition to an existing OOB model: give the new entry a fresh `Now.ID[...]`, and give the OOB entries it connects to their real sys_ids.

- Update a model field (e.g. `recordPreset`): declare just the model with its sys_id and omit `states`/`transitions`. Only that one row is written.

- Add a condition to an OOB transition: declare the model (with its real `$id`), include the state entries the transition connects (with their real `$id`s), and declare the transition with its real sys_id and the new condition (a fresh `Now.ID[...]`) nested under it.

⚠️ Clobber caveat. Every row you declare is fully re-written. Any field you omit is filled with its platform default, overwriting the OOB value. When editing OOB rows you must restate the OOB values of every field you don't want changed (e.g. the model's `availableInUI`/`defaultModel`, a state's `sequence`/`initial`, a transition's `automatic`). Declare only the rows you actually need to reach, to keep the blast radius small.

To delete an OOB transition (or any record), use `Now.del('<table>', '<sys_id>')`, or `Now.del('<table>', { ...keys })` to match by field values directly. The keys form throws if more than one record matches — since the platform allows duplicate transitions between the same two states, prefer the exact sys_id when you know it.

## See

- 
For behavior, edge cases, and the complete-workflow pattern, see the `state-model-guide` topic.

- 
https://docs.servicenow.com/csh?topicname=state-model.html&version=latest

## Examples

### Basic State Model

Linear progression with no conditions.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['statemodel-basic'],
    name: 'Simple Change Model',
    table: 'change_request',
    stateField: 'state',
    states: {
        new: { $id: Now.ID['statemodel-basic-new'], label: 'New', value: '-5', sequence: 0, initial: true },
        assess: { $id: Now.ID['statemodel-basic-assess'], label: 'Assess', value: '-4', sequence: 1 },
        closed: { $id: Now.ID['statemodel-basic-closed'], label: 'Closed', value: '3', sequence: 2 },
    },
    transitions: [
        { $id: Now.ID['statemodel-basic-new-to-assess'], from: 'new', to: 'assess' },
        { $id: Now.ID['statemodel-basic-assess-to-closed'], from: 'assess', to: 'closed' },
    ],
})
```

### State Model with Encoded Query Conditions

Gate transitions on field values.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['statemodel-with-conditions-example'],
    name: 'Conditional Change Model',
    table: 'change_request',
    stateField: 'state',
    states: {
        new: { $id: Now.ID['statemodel-cond-new'], label: 'New', value: '-5', initial: true },
        assess: { $id: Now.ID['statemodel-cond-assess'], label: 'Assess', value: '-4' },
        authorize: { $id: Now.ID['statemodel-cond-authorize'], label: 'Authorize', value: '-3' },
    },
    transitions: [
        {
            $id: Now.ID['statemodel-cond-new-to-assess'],
            from: 'new',
            to: 'assess',
            conditions: [
                {
                    $id: Now.ID['statemodel-cond-required-fields'],
                    name: 'Required fields',
                    conditionType: 'Transition Condition',
                    condition: 'short_descriptionISNOTEMPTY^EQ',
                    order: 100,
                },
            ],
        },
        {
            $id: Now.ID['statemodel-cond-assess-to-authorize'],
            from: 'assess',
            to: 'authorize',
            automatic: true,
            conditions: [
                { $id: Now.ID['statemodel-cond-approved'], name: 'Approved', conditionType: 'Transition Condition', condition: 'approval=approved^EQ', order: 100 },
            ],
        },
    ],
})
```

### State Model with Script-Based Conditions

Use a server-side script to gate a transition.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['statemodel-with-scripts-example'],
    name: 'Scripted Change Model',
    table: 'change_request',
    stateField: 'state',
    states: {
        implement: { $id: Now.ID['statemodel-script-implement'], label: 'Implement', value: '0', initial: true },
        review: { $id: Now.ID['statemodel-script-review'], label: 'Review', value: '-1' },
    },
    transitions: [
        {
            $id: Now.ID['statemodel-script-implement-to-review'],
            from: 'implement',
            to: 'review',
            conditions: [
                {
                    $id: Now.ID['statemodel-cond-no-open-tasks'],
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

### State Model with Role-Based Security

Restrict who can read and write records using the model.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['statemodel-with-security-example'],
    name: 'Secure Change Model',
    table: 'change_request',
    stateField: 'state',
    advancedSecurity: true,
    readRoles: ['itil', 'change_manager'],
    writeRoles: ['change_manager'],
    states: {
        draft: { $id: Now.ID['statemodel-security-draft'], label: 'Draft', value: '-6', initial: true },
        new: { $id: Now.ID['statemodel-security-new'], label: 'New', value: '-5' },
    },
    transitions: [{ $id: Now.ID['statemodel-security-draft-to-new'], from: 'draft', to: 'new' }],
})
```

### State Model with User Criteria Access Control

`availableFor`/`writableFor`/`notAvailableFor` only take effect when `advancedSecurity` is enabled — they layer User Criteria-based access on top of `readRoles`/`writeRoles`. Pass a `user_criteria` sys_id string or a `Record<'user_criteria'>` reference.

```
import { StateModel, Record } from '@servicenow/sdk/core'

const itilStaff = Record({ $id: Now.ID['statemodel-uc-itil-staff'], table: 'user_criteria', data: { name: 'ITIL Staff' } })
const formerEmployees = Record({
    $id: Now.ID['statemodel-uc-former-employees'],
    table: 'user_criteria',
    data: { name: 'Former Employees' },
})

StateModel({
    $id: Now.ID['statemodel-user-criteria-example'],
    name: 'User Criteria Secured Model',
    table: 'change_request',
    stateField: 'state',
    advancedSecurity: true,
    readRoles: ['itil'],
    writeRoles: ['change_manager'],
    availableFor: [itilStaff],
    writableFor: ['a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6'], // an existing user_criteria sys_id
    notAvailableFor: [formerEmployees],
    states: {
        new: { $id: Now.ID['statemodel-uc-new'], label: 'New', value: '-5', initial: true },
        closed: { $id: Now.ID['statemodel-uc-closed'], label: 'Closed', value: '3' },
    },
    transitions: [{ $id: Now.ID['statemodel-uc-new-to-closed'], from: 'new', to: 'closed' }],
})
```

### Advanced State Model

Combines security, automatic transitions, encoded-query and scripted conditions, and a system-assigned model.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['statemodel-advanced'],
    name: 'Advanced Change Model',
    table: 'change_request',
    stateField: 'state',
    active: true,
    availableInUI: false,
    description: 'Full-featured custom change model',
    readRoles: ['itil'],
    writeRoles: ['change_manager'],
    states: {
        new: { $id: Now.ID['statemodel-adv-new'], label: 'New', value: '-5', sequence: 0, initial: true },
        assess: { $id: Now.ID['statemodel-adv-assess'], label: 'Assess', value: '-4', sequence: 1 },
        authorize: { $id: Now.ID['statemodel-adv-authorize'], label: 'Authorize', value: '-3', sequence: 2 },
        closed: { $id: Now.ID['statemodel-adv-closed'], label: 'Closed', value: '3', sequence: 3 },
    },
    transitions: [
        {
            $id: Now.ID['statemodel-adv-new-to-assess'],
            from: 'new',
            to: 'assess',
            conditions: [
                {
                    $id: Now.ID['statemodel-adv-cond-required-fields'],
                    name: 'Required fields',
                    conditionType: 'Transition Condition',
                    condition: 'short_descriptionISNOTEMPTY^EQ',
                    order: 100,
                },
            ],
        },
        {
            $id: Now.ID['statemodel-adv-assess-to-authorize'],
            from: 'assess',
            to: 'authorize',
            automatic: true,
            conditions: [
                { $id: Now.ID['statemodel-adv-cond-approved'], name: 'Approved', conditionType: 'Transition Condition', condition: 'approval=approved^EQ', order: 100 },
                {
                    $id: Now.ID['statemodel-adv-cond-manager-signoff'],
                    name: 'Manager sign-off',
                    conditionType: 'Transition Script',
                    conditionScript: Now.include('./manager-signoff.js'),
                    order: 200,
                },
            ],
        },
        { $id: Now.ID['statemodel-adv-authorize-to-closed'], from: 'authorize', to: 'closed' },
    ],
})
```

### Condition with Required Fields

A `'Mandatory Fields'` condition that lists the fields the record must have set. Each name becomes a `sttrm_transition_condition_field` row.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['statemodel-mandatory-fields'],
    name: 'Mandatory Fields Model',
    table: 'change_request',
    stateField: 'state',
    states: {
        assess: { $id: Now.ID['statemodel-mandatory-assess'], label: 'Assess', value: '-4', initial: true },
        authorize: { $id: Now.ID['statemodel-mandatory-authorize'], label: 'Authorize', value: '-3' },
    },
    transitions: [
        {
            $id: Now.ID['statemodel-mandatory-assess-to-authorize'],
            from: 'assess',
            to: 'authorize',
            conditions: [
                {
                    $id: Now.ID['statemodel-cond-mandatory-fields'],
                    name: 'Required fields',
                    conditionType: 'Mandatory Fields',
                    fields: [
                        { $id: Now.ID['statemodel-field-justification'], name: 'justification' },
                        { $id: Now.ID['statemodel-field-risk'], name: 'risk' },
                        { $id: Now.ID['statemodel-field-implementation-plan'], name: 'implementation_plan' },
                    ],
                },
            ],
        },
    ],
})
```

### State with Attributes

Attach `sttrm_state_attribute` links to a state. Each link requires its own `$id` — the platform allows more than one link between the same state and attribute.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: Now.ID['statemodel-state-attributes'],
    name: 'State Attribute Model',
    table: 'change_request',
    stateField: 'state',
    states: {
        implement: {
            $id: Now.ID['statemodel-attr-implement'],
            label: 'Implement',
            value: '-1',
            initial: true,
            attributes: [
                { $id: Now.ID['statemodel-attr-allow-implementation'], attribute: 'allowImplementation' },
                { $id: Now.ID['statemodel-attr-allow-ci-modification'], attribute: 'allowCiModification', active: false },
            ],
        },
        review: { $id: Now.ID['statemodel-attr-review'], label: 'Review', value: '0' },
    },
    transitions: [{ $id: Now.ID['statemodel-attr-implement-to-review'], from: 'implement', to: 'review' }],
})
```

### Editing an Out-of-Box Model

Add a gating condition to the OOB "Normal" change model's Implement → Review transition. The model, the two states the transition connects, and the transition itself all carry their real OOB sys_ids. OOB field values (`availableInUI`, the states' `sequence`) are restated to avoid clobbering them.

```
import { StateModel } from '@servicenow/sdk/core'

StateModel({
    $id: '007c4001c343101035ae3f52c1d3aeb2', // OOB "Normal" chg_model sys_id
    name: 'Normal',
    table: 'change_request',
    stateField: 'state',
    availableInUI: true, // restate OOB value — omitting it would reset to default
    states: {
        impl: { $id: '2d0d4801c343101035ae3f52c1d3ae62', label: 'Implement', value: '-1', sequence: 4 }, // OOB Implement state sys_id
        review: { $id: '660d4801c343101035ae3f52c1d3ae4d', label: 'Review', value: '0', sequence: 5 },   // OOB Review state sys_id
    },
    transitions: [
        {
            $id: '7a0d2ccdc343101035ae3f52c1d3ae2e', // OOB Implement → Review transition sys_id
            from: 'impl',
            to: 'review',
            conditions: [
                {
                    $id: Now.ID['statemodel-oob-cond-no-open-change-tasks'],
                    name: 'No open change tasks',
                    conditionScript: Now.include('./no-open-change-tasks.js'),
                    conditionType: 'Transition Script',
                },
            ],
        },
    ],
})
```

### Model-Only Update

Update a single field on an OOB model without touching its states or transitions — omit `states`/`transitions` entirely.

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

### Deleting a Transition

Remove an OOB transition (or any record) with `Now.del`.

```
// By sys_id (preferred):
Now.del('sttrm_state_transition', '7a0d2ccdc343101035ae3f52c1d3ae2e')

// Or by field values directly:
Now.del('sttrm_state_transition', { from_state: '2d0d4801c343101035ae3f52c1d3ae62', to_state: '660d4801c343101035ae3f52c1d3ae4d' })
```

The field-values form throws if more than one record matches. Since the platform allows more than one transition between the same two states (e.g. one automatic, one manual), prefer the exact sys_id whenever you know it.

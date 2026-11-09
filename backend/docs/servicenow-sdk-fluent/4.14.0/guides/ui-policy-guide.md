Version: 4.14.0

# UI Policies

Guide for creating ServiceNow UI Policies using the Fluent API. UI Policies dynamically change form field properties (visibility, mandatory, read-only, cleared) and control related list visibility based on conditions evaluated when the form loads or field values change.

## When to Use

- Making fields mandatory based on another field's value (e.g., require `impact` when `priority` is Critical)

- Hiding or showing fields dynamically (e.g., show `asset` only for hardware incidents)

- Making fields read-only based on record state (e.g., lock `urgency` on critical incidents)

- Clearing field values when conditions change (e.g., clear resolution fields when reopened)

- Controlling related list visibility based on form state

- Running client-side scripts when conditions are met or unmet

### UI Policy vs Data Policy vs Client Script

| Aspect | UI Policy | Data Policy | Client Script |
| Execution | Client-side (browser) | Server-side | Client-side (browser) |
| Can be bypassed via API? | Yes | No | Yes |
| Applies to imports/REST/SOAP | No | Yes | No |
| Visibility control | Yes | No | Yes (via `g_form` ) |
| Field mandatory/read-only | Yes (form only) | Yes (all interfaces) | Yes (via `g_form` ) |
| Set/clear field values | Yes | No | Yes |
| Scripting support | Yes ( `scriptTrue` / `scriptFalse` ) | No | Yes (full script) |
| Field messages | Yes | No | Yes (via `g_form` ) |
| Condition-driven (no code) | Yes | Yes | No (requires script) |
| Event-driven (onChange, onSubmit) | No | No | Yes |

Use UI Policy when:

- You need no-code, condition-based form behavior — show/hide fields, set mandatory/read-only, clear values

- Enforcement is needed on forms only (not imports or APIs)

Use Data Policy instead when:

- Mandatory or read-only enforcement must apply across all interfaces (forms, imports, REST/SOAP)

- Server-side enforcement that cannot be bypassed is required

- See the data-policy-guide topic

Use Client Script instead when:

- You need event-driven logic (`onLoad`, `onChange`, `onSubmit`, `onCellEdit`)

- You need complex scripting, GlideAjax calls, or conditional logic beyond what encoded queries can express

- You need `onSubmit` validation that can cancel form submission

- See the client-script-guide topic

Use both UI Policy + Data Policy when:

- Server-side enforcement is needed (Data Policy) AND client-side UX like visibility or messages is also needed (UI Policy)

- Example: "Make vendor mandatory and show a warning message" → Data Policy (mandatory) + UI Policy (message)

## Instructions

- Ensure fields exist in table schema: Before creating UI Policies, verify that all fields referenced in actions are defined in the table schema using column definitions (e.g., `StringColumn`, `ChoiceColumn`).

- Define the condition: Use encoded query syntax (e.g., `'priority=1'`, `'state!=6^categoryLIKEhardware'`). For choice fields, use stored values, not display labels.

- Add field actions: Each action targets a field and sets `visible`, `readOnly`, `mandatory`, or `cleared`. Use `boolean` for definite states and `'ignore'` to leave unchanged.

- `onLoad` defaults to `true`: The policy evaluates when the form first loads. Set to `false` only if the policy should evaluate solely on field changes, not on form load.

- Use `reverseIfFalse`: When `true` (default), field actions reverse automatically when the condition becomes false — no need to create a second policy.

- Scripts are client-side only: `scriptTrue`/`scriptFalse` run in the browser. Module scripts (`import`/`export`) are not supported. Wrap scripts in `function onCondition() { }`.

- Enable scripts explicitly: Set `runScripts: true` to activate `scriptTrue`/`scriptFalse`. When `runScripts` is false, script properties are ignored.

- Use `relatedListActions` for related list visibility: To show or hide related lists based on conditions, use the `relatedListActions` array. Each entry needs a `list` identifier in `child_table.reference_field` format (e.g., `'x_myapp_task.parent'`) and a `visible` boolean. Do not include the `REL:` prefix — the plugin adds it automatically.

## API Reference

See the uipolicy-api topic for the full property reference, including `UiPolicyAction` and `UiPolicyRelatedListAction` types.

## Critical Requirements

### Table Schema Requirements

IMPORTANT: UI Policies control field behavior on forms. Before creating UI Policies:

- ✅ All fields must exist in the table schema — create columns using column definitions (e.g., `StringColumn`, `ChoiceColumn`)

- ✅ Field names in actions must match table field names — use exact field names from table schema

### Field Visibility Defaults

Understanding when to use `visible` property:

Default Behavior:

- Table fields are visible by default on forms

- UI Policies can hide them by setting `visible: false`

- UI Policies can show them by setting `visible: true`

When to use `visible: false`:

Use when you want to hide a field that is normally visible:

```
import { UiPolicy } from '@servicenow/sdk/core'

// Hide rejection fields when status is NOT rejected
UiPolicy({
    $id: Now.ID['hide-rejection-fields'],
    table: 'x_myapp_task',
    shortDescription: 'Hide rejection fields when not rejected',
    conditions: 'status!=rejected',
    onLoad: true,
    actions: [
        { field: 'rejection_reason', visible: false },
        { field: 'rejected_by', visible: false },
    ],
})
```

When to use `visible: true`:

Use when you want to show a field that is normally hidden:

```
import { UiPolicy } from '@servicenow/sdk/core'

// Show rejection fields when status IS rejected
UiPolicy({
    $id: Now.ID['show-rejection-fields'],
    table: 'x_myapp_task',
    shortDescription: 'Show rejection fields when rejected',
    conditions: 'status=rejected',
    onLoad: true,
    actions: [
        { field: 'rejection_reason', visible: true, mandatory: true },
        { field: 'rejected_by', visible: true, mandatory: true },
    ],
})
```

Best Practice for Conditional Visibility:

When fields should be hidden by default and shown only when a condition is met:

- Fields are visible by default on forms

- Create a UI Policy with `reverseIfFalse: true` (default) that shows them when condition is met

- The policy will automatically hide them when condition is false

```
import { UiPolicy } from '@servicenow/sdk/core'

// This policy shows asset when category=hardware
// and automatically hides it when category!=hardware (due to reverseIfFalse: true)
UiPolicy({
    $id: Now.ID['hardware-asset-visibility'],
    table: 'x_myapp_incident',
    shortDescription: 'Show asset for hardware category',
    conditions: 'category=hardware',
    onLoad: true,
    reverseIfFalse: true, // Default - automatically hides when condition is false
    actions: [
        { field: 'asset', visible: true, mandatory: true },
    ],
})
```

Common Mistake:

Creating two separate policies for show/hide logic:

```
// ❌ WRONG - Unnecessary duplication
UiPolicy({
    conditions: 'category=hardware',
    actions: [{ field: 'asset', visible: true }],
})

UiPolicy({
    conditions: 'category!=hardware',
    actions: [{ field: 'asset', visible: false }],
})

// ✅ CORRECT - Single policy with reverseIfFalse
UiPolicy({
    $id: Now.ID['hardware-asset-toggle'],
    table: 'x_myapp_incident',
    shortDescription: 'Show asset for hardware category',
    conditions: 'category=hardware',
    reverseIfFalse: true, // Automatically handles the reverse
    actions: [{ field: 'asset', visible: true }],
})
```

## Key Concepts

### Policy Definition Properties

See the uipolicy-api topic for the full property reference table, types, and defaults.

Usage examples:

```
// View-specific policy
UiPolicy({
    $id: Now.ID['it-view-policy'],
    table: 'incident',
    global: false,
    view: 'IT view',
    // ...
})

// Inherited policy for task and child tables
UiPolicy({
    $id: Now.ID['task-inherited-policy'],
    table: 'task',
    inherit: true,  // Applies to incident, problem, change, etc.
    // ...
})

// Control execution order
UiPolicy({
    $id: Now.ID['priority-policy'],
    table: 'incident',
    order: 50,  // Executes before default order 100
    // ...
})

// Example: Multiple policies with coordinated execution order
// Cost policy executes first (order: 50)
UiPolicy({
    $id: Now.ID['cost-threshold-policy'],
    table: 'x_myapp_change_request',
    shortDescription: 'Cost-based approval requirements',
    order: 50,  // Lower number = executes first
    conditions: 'cost>50000',
    actions: [
        { field: 'approval_required', value: 'true' },
        { field: 'approver', mandatory: true },
    ],
})

// Risk policy executes second (order: 100, default)
UiPolicy({
    $id: Now.ID['risk-based-policy'],
    table: 'x_myapp_change_request',
    shortDescription: 'Risk-based field requirements',
    order: 100,  // Higher number = executes after lower order policies
    conditions: 'risk=high',
    actions: [
        { field: 'cab_approval_date', visible: true, mandatory: true },
    ],
})

// Protect policy from modification after installation
UiPolicy({
    $id: Now.ID['protected-priority-policy'],
    table: 'x_myapp_incident',
    shortDescription: 'Lock fields on critical incidents',
    conditions: 'priority=1',
    protectionPolicy: 'read', // Others can view but not modify
    actions: [
        { field: 'urgency', readOnly: true },
    ],
})
```

### Action Properties

See the uipolicy-api topic for the full `UiPolicyAction` and `UiPolicyRelatedListAction` property tables.

Key behavioral notes:

- `visible`, `readOnly`, and `mandatory` accept `boolean | 'ignore'` — use `'ignore'` to leave the property unchanged, not `false` (which explicitly sets it)

- `cleared` only accepts `boolean` (no `'ignore'` option) and defaults to `false`

- The plugin automatically adds/removes the `REL:` prefix for related list identifiers during transformation

### Condition Syntax

Conditions use ServiceNow encoded query syntax. See the encoded-query-guide topic for the full operator reference, escaping rules, and dot-walking.

Quick examples: `'priority=1'`, `'state!=6^categoryLIKEhardware'`, `'stateIN1,2,3'`

Choice fields: Always use stored values, not display labels. Right-click the field → Show Choice List → check the "Value" column.

### Script Properties

Scripts are client-side only — they run in the browser using `g_form`:

```
runScripts: true,
uiType: 'all',  // 'desktop', 'mobile-or-service-portal', or 'all'
isolateScript: true,  // Recommended for security
scriptTrue: `function onCondition() {
    g_form.addInfoMessage('Condition is true');
}`,
scriptFalse: `function onCondition() {
    g_form.clearMessages();
}`,
```

Key properties:

- `runScripts` must be `true` for scripts to execute

- `uiType` controls where scripts run:

- `'desktop'` (default; only effective when `runScripts: true`): Desktop interface only

- `'mobile-or-service-portal'`: Mobile and Service Portal interfaces

- `'all'`: All interfaces

- `isolateScript` controls script isolation:

- `true` (recommended): Scripts run in isolated scope, preventing variable conflicts with other client scripts

- `false` (default): Scripts run in global scope

- Module scripts (`import`/`export`) are not supported — use string scripts only

### Client-Side APIs

UI Policy scripts (`scriptTrue`/`scriptFalse`) run in the browser and have access to `g_form`, `g_user`, `g_scratchpad`, and `g_modal`. See the client-side-api-guide topic for the full method reference, function signatures, and constraints.

### Property Mapping (Fluent → ServiceNow)

The plugin automatically converts between camelCase (Fluent) and snake_case (ServiceNow):

| Fluent (camelCase) | ServiceNow (snake_case) |
| `shortDescription` | `short_description` |
| `onLoad` | `on_load` |
| `reverseIfFalse` | `reverse_if_false` |
| `isolateScript` | `isolate_script` |
| `runScripts` | `run_scripts` |
| `scriptTrue` | `script_true` |
| `scriptFalse` | `script_false` |
| `readOnly` | `disabled` |
| `fieldMessage` | `field_message` |
| `fieldMessageType` | `field_message_type` |
| `modelId` | `model_id` |
| `modelTable` | `model_table` |
| `setValues` | `set_values` |
| `uiType` | `ui_type` |
| `valueAction` | `value_action` |
| `protectionPolicy` | `sys_policy` |

Notable: `readOnly` maps to `disabled` in ServiceNow (direct mapping, no logic inversion). `protectionPolicy` is auto-injected by the build framework — it is not mapped directly by the UI Policy plugin.

### Related List Identifier Formats

Two formats for identifying related lists in `relatedListActions`:

- `table.field` dotted string — a two-part dotted identifier (e.g., `'x_myapp_subtask.parent_task'`). The plugin validates exactly two non-empty parts separated by `.`

- GUID string — sys_id of a `sys_relationship` record (e.g., `'b9edf0ca0a0a0b010035de2d6b579a03'`). A `Record<'sys_relationship'>` reference is also accepted

Important: The plugin auto-adds the `REL:` prefix during transformation — developers must NOT include it.

Finding IDs: Two methods to find related list identifiers:

Method 1 - CLI Query: Query the `sys_ui_related_list_entry` table filtered by the parent table name to retrieve `related_list` and `position` values. See the query-guide topic for CLI usage.

Method 2 - ServiceNow Script:

```
// Find related lists by table name
var gr = new GlideRecord('sys_ui_related_list');
gr.addQuery('name', 'CONTAINS', 'your_table_name');
gr.query();
while (gr.next()) {
    gs.print(gr.name + ' -> ' + gr.sys_id);
}
```

Note: Related list actions only control visibility — they cannot modify data or behavior.

## Examples

### Make Fields Mandatory on High Priority

```
import { UiPolicy } from '@servicenow/sdk/core'

UiPolicy({
    $id: Now.ID['high-priority-policy'],
    table: 'x_myapp_request',
    shortDescription: 'Require impact and urgency for high priority',
    onLoad: true,
    conditions: 'priority=1',
    actions: [
        { field: 'impact', mandatory: true },
        { field: 'urgency', mandatory: true },
    ],
})
```

### Show/Hide Fields Based on Category

```
import { UiPolicy } from '@servicenow/sdk/core'

UiPolicy({
    $id: Now.ID['hardware-asset-policy'],
    table: 'x_myapp_request',
    shortDescription: 'Show asset field for hardware requests',
    onLoad: true,
    conditions: 'category=hardware',
    actions: [
        { field: 'asset', visible: true, mandatory: true },
    ],
})
```

### Lock Fields and Set Values on Critical Incidents

```
import { UiPolicy } from '@servicenow/sdk/core'

UiPolicy({
    $id: Now.ID['critical-incident-policy'],
    table: 'x_myapp_incident',
    shortDescription: 'Lock and set defaults for critical incidents',
    onLoad: true,
    conditions: 'priority=1',
    actions: [
        { field: 'assignment_group', mandatory: true },
        { field: 'urgency', value: '1', readOnly: true },
        { field: 'impact', value: '1', readOnly: true },
        {
            field: 'short_description',
            fieldMessage: 'Critical incident - provide detailed description',
            fieldMessageType: 'warning',
        },
    ],
})
```

### Client-Side Scripts with Field Actions

```
import { UiPolicy } from '@servicenow/sdk/core'

UiPolicy({
    $id: Now.ID['category-script-policy'],
    table: 'x_myapp_request',
    shortDescription: 'Show asset with custom messaging for hardware',
    onLoad: true,
    conditions: 'category=hardware',
    runScripts: true,
    uiType: 'all',
    scriptTrue: `function onCondition() {
    g_form.setVisible('asset', true);
    g_form.setMandatory('asset', true);
    g_form.addInfoMessage('Please specify the asset for this hardware request.');
}`,
    scriptFalse: `function onCondition() {
    g_form.setVisible('asset', false);
    g_form.setMandatory('asset', false);
    g_form.clearMessages();
}`,
    actions: [{ field: 'asset', visible: true, mandatory: true }],
})
```

### Related List Visibility Control

Show or hide related lists based on conditions. The `list` identifier uses `child_table.reference_field` format — where `reference_field` is the field on the child table that references the parent table.

```
import { UiPolicy } from '@servicenow/sdk/core'

UiPolicy({
    $id: Now.ID['security-related-lists'],
    table: 'x_myapp_incident',
    shortDescription: 'Control related lists for security incidents',
    onLoad: true,
    conditions: 'category=security^priorityIN1,2',
    actions: [
        { field: 'caller_id', readOnly: true },
        { field: 'work_notes', mandatory: true },
    ],
    relatedListActions: [
        // 'x_myapp_incident_task' is the child table, 'parent' is the reference field pointing back to x_myapp_incident
        { list: 'x_myapp_incident_task.parent', visible: true },
        { list: 'x_myapp_audit_log.incident', visible: true },
    ],
})
```

### State-Based Field Control — Read-Only on Closed

Make multiple fields read-only when incidents are closed to prevent modifications.

```
import { UiPolicy } from '@servicenow/sdk/core'

UiPolicy({
    $id: Now.ID['closed-readonly-policy'],
    table: 'x_myapp_incident',
    shortDescription: 'Lock fields when incident is closed',
    conditions: 'state=6^ORstate=7',
    onLoad: true,
    actions: [
        { field: 'urgency', readOnly: true },
        { field: 'impact', readOnly: true },
        { field: 'priority', readOnly: true },
        { field: 'assigned_to', readOnly: true },
    ],
})
```

### Field Clearing on Condition Change — Reopen Policy

Clear resolution fields when an incident is reopened.

```
import { UiPolicy } from '@servicenow/sdk/core'

UiPolicy({
    $id: Now.ID['reopen-clear-policy'],
    table: 'x_myapp_incident',
    shortDescription: 'Clear resolution fields when reopened',
    conditions: 'state!=6^state!=7',
    onLoad: true,
    actions: [
        { field: 'close_code', cleared: true },
        { field: 'close_notes', cleared: true },
        { field: 'resolved_by', cleared: true },
    ],
})
```

### Default Values with Validation Messages

Set default values and display warning messages when conditions are met.

```
import { UiPolicy } from '@servicenow/sdk/core'

UiPolicy({
    $id: Now.ID['default-value-policy'],
    table: 'x_myapp_incident',
    shortDescription: 'Set defaults for hardware category',
    conditions: 'category=hardware',
    onLoad: true,
    actions: [
        {
            field: 'assignment_group',
            value: 'Hardware Support',
            fieldMessage: 'Auto-assigned to Hardware Support team',
            fieldMessageType: 'warning',
        },
    ],
})
```

### Progressive Display — Show Related Lists Based on Field Value

Show related lists only when relevant based on form state.

```
import { UiPolicy } from '@servicenow/sdk/core'

UiPolicy({
    $id: Now.ID['progressive-display-policy'],
    table: 'x_myapp_incident',
    shortDescription: 'Show task list when in progress',
    conditions: 'state=2',
    onLoad: true,
    relatedListActions: [
        {
            list: 'x_myapp_incident_task.parent',
            visible: true,
        },
    ],
})
```

### User-Based Logic with Role Checks

Control form behavior based on user roles using `g_user.hasRole()` in scripts.

```
import { UiPolicy } from '@servicenow/sdk/core'

UiPolicy({
    $id: Now.ID['approver-policy'],
    table: 'x_myapp_change_request',
    shortDescription: 'Show approval fields for approvers only',
    onLoad: true,
    conditions: 'approval=requested',
    runScripts: true,
    isolateScript: true,
    uiType: 'all',
    scriptTrue: `function onCondition() {
    if (g_user.hasRole('approver_user')) {
        g_form.setVisible('approval_notes', true);
        g_form.setMandatory('approval_notes', true);
        g_form.showFieldMsg('approval_notes', 'Please provide approval notes', 'info');
    } else {
        g_form.setVisible('approval_notes', false);
        g_form.addInfoMessage('This change is pending approval.');
    }
}`,
    scriptFalse: `function onCondition() {
    g_form.setVisible('approval_notes', false);
    g_form.setMandatory('approval_notes', false);
    g_form.hideFieldMsg('approval_notes');
    g_form.clearMessages();
}`,
})
```

## Best Practices

Follow these guidelines for maintainable UI Policies:

- Prefer field actions over scripts for simple visibility/mandatory changes — more performant and easier to debug

- Use `'ignore'` to leave properties unchanged — not `false`, which explicitly sets the property

- Group related field actions in a single policy — easier to understand and maintain. Apply different action types to different fields in the same policy (e.g., one field mandatory, another visible, another read-only)

- Use `cleared: true` only when values should be wiped — not just hidden

- Test conditions with ServiceNow list filter before using in policies — ensures encoded query syntax is correct

- Keep scripts minimal — complex logic belongs in Business Rules or server-side code

- Use `isolateScript: true` when scripts may conflict with other client scripts — prevents variable collisions

- Document complex conditions — add comments explaining business logic

- Test policy interactions — verify how multiple policies interact when they affect the same fields. Test execution order and combined effects

- Document GUID relationships — when using GUIDs for related lists, add comments explaining what they represent for maintainability

- Consider mobile users — test policies on mobile and Service Portal interfaces. Use `uiType` to create mobile-specific policies when needed

- Use progressive disclosure — show fields only when relevant to improve user experience and reduce form complexity

### Script Performance

- Minimize DOM queries — cache field values in local variables instead of calling `g_form.getValue()` repeatedly

- Avoid `GlideAjax` in UI Policy scripts — server round-trips slow form interaction. Move complex lookups to Business Rules and pass data via `g_scratchpad`

- Keep scripts under 50 lines — if a script grows beyond this, consider splitting logic into multiple policies or using a UI Script for shared utility functions

- Cache user info — call `g_user.hasRole()` once and store the result rather than checking multiple times

## Avoidance

- CRITICAL: Never create UI Policies for fields that don't exist in the table schema — the policy will be created in the database but will have no effect. Always define columns using column definitions (e.g., `StringColumn`, `ChoiceColumn`) before creating UI Policies that reference them.

- Never use module scripts — `scriptTrue`/`scriptFalse` are client-side only. Use string scripts wrapped in `function onCondition() { }`.

- Never use display labels in conditions — choice fields store values that may differ from labels. Always use stored values (e.g., `category=hardware`, not `category=Hardware`).

- Never create duplicate policies for reverse logic — use `reverseIfFalse: true` (the default) to automatically reverse actions when the condition is false.

- Never set `readOnly` when you mean `visible` — `readOnly: true` disables the field but keeps it visible. Use `visible: false` to hide it entirely.

- Never use `cleared: 'ignore'` — the `cleared` property only accepts `boolean`, not `'ignore'`. It defaults to `false`.

- Never set `onLoad: false` unless intentional — with `onLoad: false`, the policy only evaluates when a field referenced in the condition changes, not when the form first loads. The default is `true`.

- Never omit `runScripts: true` when using scripts — scripts are ignored unless `runScripts` is explicitly set to `true`.

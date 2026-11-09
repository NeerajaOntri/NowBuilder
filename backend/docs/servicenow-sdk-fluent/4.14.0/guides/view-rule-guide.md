Version: 4.14.0

# View Rules

Guide for creating ServiceNow View Rules using the Record API. View rules automatically switch users to a specific view based on conditions, device type, or custom scripts — unlike manual view selection from the dropdown.

## When to Use

- Automatically switching to a mobile-optimized view on mobile devices

- Showing a specialized view for high-priority or critical records

- Routing users to different views based on their role (via advanced script)

- Overriding the user's manually selected view when conditions are met

- Combining device type and record conditions for targeted view selection

## Instructions

- Create the target view first: The view referenced by `data.view` must exist in `sys_ui_view`. Create it using a `Record({ table: 'sys_ui_view', ... })` before the view rule.

- Use the view `name`, not `title`: The `data.view` property must use the view's `name` field, not its `title`.

- End conditions with `^EQ`: All encoded query conditions in `data.condition` must terminate with `^EQ`.

- Set evaluation order: Lower `order` values are evaluated first. Use 100 as default, lower for higher priority rules.

- Choose condition vs advanced script: Use `data.condition` for simple field-based matching. Use `data.advanced: true` with a script for complex logic (role checks, multi-table queries).

- Consider `overrides_user_preference`: When `true` (default), the rule overrides the user's manual view selection. Set to `false` if the user's choice should take priority.

## Key Concepts

View rules are created using the `Record()` API with `table: 'sysrule_view'`. See the `record-api` topic for the Record wrapper (`$id`, `table`, `data`, `$meta`). The compiler validates properties at build time.

### Key Properties (set inside `data`)

| Property | Type | Required | Description |
| `name` | `string` | Yes | Descriptive name for the rule. |
| `table` | `string` | Yes | Target table where the rule applies. |
| `view` | `string` | Conditional | View `name` from `sys_ui_view` . Required unless using advanced script. |
| `condition` | `string` | No | Encoded query ending with `^EQ` for simple field-based matching. |
| `match_conditions` | `string` | No | `'ALL'` (default) or `'ANY'` . Controls whether all or any conditions must match. These are the platform-recognized values ( `sys_choice` ); the column accepts any string at the type level. |
| `device_type` | `string` | No | `'browser'` (default), `'mobile'` , or `'tablet'` . These are the platform-recognized values ( `sys_choice` ); the column accepts any string at the type level. |
| `active` | `boolean` | No | Whether the rule is active. Default: `true` . |
| `advanced` | `boolean` | No | Set `true` to enable custom script mode instead of condition-based matching. |
| `script` | `string` | No | JavaScript for complex logic (when `advanced: true` ). Must set the `answer` variable. If `advanced: false` , omit or set `script: ''` — the schema default IIFE is otherwise silently persisted to the record. |
| `overrides_user_preference` | `boolean` | No | When `true` (default), overrides the user's manual view selection. |
| `order` | `number` | No | Evaluation order (lower = first). Default: `100` . |

Warning: Never set `sys_id` in `data:` — let the SDK manage record identity via `$id`.

`sysrule_view` has no build-plugin (only `sys_ui_view` is registered in `view-plugin.ts`), so there is no coalesce key. Use stable `$id` values (e.g., `Now.ID['my-rule-name']`) to prevent duplicate view rules on redeploy.

For the full field schema (types, defaults, maxLengths), refer to the shipped SDK schema definition at `@servicenow/sdk` → `tables/sysrule_view.now.ts`, or query table `sys_dictionary` where `name=sysrule_view`, retrieving `element,column_label,internal_type,max_length,mandatory` (see the `query` topic).

### Condition Syntax

Conditions use ServiceNow encoded query syntax and must end with `^EQ`:

```
priority=1^EQ                    -- Priority is Critical
priority=1^ORpriority=2^EQ      -- Priority is Critical OR High
state!=6^category=hardware^EQ   -- Not Resolved AND Hardware category
```

Common operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `LIKE`, `STARTSWITH`, `ISEMPTY`, `ISNOTEMPTY`, `^` (AND), `^OR` (OR).

#### Common Mistakes in Conditions

| Mistake | Problem | Solution |
| Wrong casing | `Priority=1^EQ` | Use backend name: `priority=1^EQ` |
| Using labels | `state=Resolved^EQ` | Use value: `state=6^EQ` |
| Missing `^EQ` | `priority=1` | Always end with: `priority=1^EQ` |

#### Finding Backend Names

To find a field's backend name, query table `sys_dictionary` where `name=<table>^element=<field>`, retrieving fields `element,column_label` (see the `query` topic).

Example: table `incident`, field `priority`.

#### Finding Choice Values

To find choice field values, query table `sys_choice` where `name=<table>^element=<field>`, retrieving fields `label,value` (see the `query` topic).

Example: table `incident`, field `state`.

### Advanced Scripts

When `data.advanced: true`, the script must follow this IIFE structure:

```
script: `(function overrideView(view, is_list) {
    // view (string) - Current view name
    // is_list (boolean) - true for list, false for form
    // current - Current record (forms only, undefined for lists)
    // answer - Set to view name (string) or null

    answer = 'my_view_name';
})(view, is_list);`
```

- Set `answer` to the view `name` (not `title`) or `null` to skip

- `current` is only available for forms, not lists

- Always wrap in an IIFE with `(view, is_list)` parameters

### match_conditions

Controls how multiple conditions are evaluated:

- `'ALL'` (default): All conditions must be true (AND logic)

- `'ANY'`: At least one condition must be true (OR logic)

Use `'ANY'` when you want the rule to trigger if any of several conditions are met.

### Evaluation Order

View rules are evaluated in this 7-step sequence:

- Active check: Only active rules (`active: true`) are considered

- Device type match: If `device_type` is set, it must match the user's device

- Condition evaluation: If `condition` is set, it must evaluate to true

- Match conditions: If multiple conditions exist, `match_conditions` determines AND/OR logic

- Script execution: If `advanced: true`, the script runs and sets `answer`

- First match wins: The first rule that passes all checks is applied

- User preference override: If `overrides_user_preference: false`, user's manual selection takes priority

Lower `order` values are evaluated first within each step.

### One Advanced Rule Per Device Type

Important: When multiple advanced rules target the same `table` + `device_type` combination, only the rule with the lowest `order` value executes. Other rules are ignored.

Best practice: Combine all logic for a given table/device into a single advanced script instead of creating multiple advanced rules.

### Script Variables

Available variables in advanced scripts:

| Variable | Type | Scope | Description |
| `view` | `string` | All | Current view name |
| `is_list` | `boolean` | All | `true` for lists, `false` for forms |
| `current` | `GlideRecord` | Forms only | Current record (undefined for lists) |
| `answer` | `string | null` | All | Set to target view name or `null` |
| `gs` | `GlideSystem` | All | Server-side API access |

### GlideElement Methods

When accessing `current` record fields, use these methods:

- `.toString()` — Returns field value as string (e.g., `current.priority.toString()`)

- `.nil()` — Checks if field is empty (e.g., `current.assigned_to.nil()`)

- `.getDisplayValue()` — Returns display value for reference fields

- `.getValue()` — Returns raw value

Always use `.toString()` for comparisons: `current.priority.toString() === "1"`

### Debugging

Add logging to troubleshoot view rule execution:

```
script: `(function overrideView(view, is_list) {
    gs.info('View Rule Debug: view=' + view + ', is_list=' + is_list);
    
    if (!is_list && typeof current !== 'undefined') {
        gs.info('Current record priority: ' + current.priority.toString());
    }
    
    answer = 'my_view';
})(view, is_list);`
```

Use `gs.info()` for logging and wrap logic in try/catch for error handling:

```
script: `(function overrideView(view, is_list) {
    try {
        gs.info('View Rule Debug: view=' + view + ', is_list=' + is_list);

        var user = gs.getUser();
        gs.info('User: ' + gs.getUserName() + ', Has admin: ' + user.hasRole('admin'));

        if (user.hasRole('admin')) {
            answer = 'admin_view';
        } else {
            answer = null;
        }
    } catch (e) {
        gs.error('View Rule Error: ' + e.message);
        answer = null;
    }
})(view, is_list);`
```

Best practice: Always use try/catch in production view rules to prevent script errors from breaking form rendering. Set `answer = null` in the catch block to fall back to the default view.

### Common Mistakes

Avoid these frequent errors in view rule scripts:

- current unchecked: May be undefined → check `!is_list && typeof current !== 'undefined'`

- answer not set: Rule won't work → always set `answer = 'view_name'` or `null`

- Missing .toString(): Comparison fails → use `current.priority.toString() === "1"`

- Syntax errors: Script fails → fix quotes, semicolons, syntax

- Using view title: View not found → use view `name` field, not `title`

- Heavy GlideRecord queries: Slows performance → use `current` or cached data

- Wrong comparison operators: Use `===` for equality, not `=`

### Pre-Creation Checklist

Before creating any view rule, validate:

- Verify target view exists — query `sys_ui_view` with `name=<view_name>` to confirm the view is created

- Confirm backend names — all field names and values must be backend names from `sys_dictionary` / `sys_choice`, not UI labels

- Verify `^EQ` termination — every encoded query condition must end with `^EQ`

- Verify roles exist (for advanced scripts) — if the script uses `gs.hasRole('role_name')` or `user.hasRole('role_name')`, query `sys_user_role` with `name=<role>` to confirm the role exists before referencing it

### Performance Best Practices

- Minimize database queries — use the `current` record instead of new GlideRecord lookups

- Cache user info — use `gs.getUser()` (cached per request), not repeated queries

- Early returns — exit the script as soon as a condition is met

- Check context first — always verify `!is_list && typeof current !== 'undefined'` before accessing `current`

- Use session properties — prefer session data over repeated property lookups

## Examples

### Mobile-First with Fallback — View, Form, List, and Rule

Create a mobile-optimized experience: a lightweight view, a compact form, a slim list, and a view rule that auto-routes mobile users. Desktop users see the default view unaffected.

```
import '@servicenow/sdk/global'
import { Record, Form, List, default_view } from '@servicenow/sdk/core'

// Prerequisite: queried sys_ui_view where name='x_myapp_mobile'^ORtitle='Mobile View' — 0 results
const mobileView = Record({
    $id: Now.ID['task-mobile-view'],
    table: 'sys_ui_view',
    data: { name: 'x_myapp_mobile', title: 'Mobile View' },
})

Form({
    table: 'x_myapp_task',
    view: mobileView,
    sections: [
        {
            caption: 'Task',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { field: 'short_description', type: 'table_field' },
                        { field: 'state', type: 'table_field' },
                        { field: 'assigned_to', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})

List({
    table: 'x_myapp_task',
    view: mobileView,
    columns: [
        { element: 'number' },
        { element: 'short_description' },
        { element: 'state' },
    ],
})

Record({
    $id: Now.ID['task-mobile-rule'],
    table: 'sysrule_view',
    data: {
        name: 'Auto-Route Mobile Users',
        table: 'x_myapp_task',
        view: 'x_myapp_mobile',
        device_type: 'mobile',
        active: true,
        overrides_user_preference: true,
    },
})
```

### Priority-Based Triage — Condition Rule with Form

High-priority records automatically switch to a triage view that surfaces escalation fields. Lower-priority records continue to use the default view. The `order` property controls which rule wins when multiple rules match.

```
import '@servicenow/sdk/global'
import { Record, Form } from '@servicenow/sdk/core'

// Prerequisite: queried sys_ui_view where name='x_myapp_triage'^ORtitle='Triage View' — 0 results
const triageView = Record({
    $id: Now.ID['triage-view'],
    table: 'sys_ui_view',
    data: { name: 'x_myapp_triage', title: 'Triage View' },
})

Form({
    table: 'x_myapp_task',
    view: triageView,
    sections: [
        {
            caption: 'Triage',
            content: [
                {
                    layout: 'two-column',
                    leftElements: [
                        { field: 'short_description', type: 'table_field' },
                        { field: 'priority', type: 'table_field' },
                        { field: 'state', type: 'table_field' },
                    ],
                    rightElements: [
                        { field: 'assigned_to', type: 'table_field' },
                        { field: 'escalation', type: 'table_field' },
                        { field: 'assignment_group', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})

Record({
    $id: Now.ID['triage-rule'],
    table: 'sysrule_view',
    data: {
        name: 'Triage High-Priority Tasks',
        table: 'x_myapp_task',
        view: 'x_myapp_triage',
        condition: 'priority=1^ORpriority=2^EQ',
        device_type: 'browser',
        active: true,
        overrides_user_preference: true,
        order: 50,
    },
})
```

### Multi-Persona Routing — Advanced Script with Multiple Views

Route users to different views based on their role. Admins get a full dashboard, ITIL agents get an operational view, and everyone else stays on the default. Uses an advanced script with IIFE wrapper — the only option when logic requires role checks or multi-table queries.

```
import '@servicenow/sdk/global'
import { Record, Form, default_view } from '@servicenow/sdk/core'

// Prerequisite: queried sys_ui_view where name='x_myapp_admin'^ORtitle='Admin View' — 0 results
const adminView = Record({
    $id: Now.ID['admin-view'],
    table: 'sys_ui_view',
    data: { name: 'x_myapp_admin', title: 'Admin View', roles: ['admin'] },
})

// Prerequisite: queried sys_ui_view where name='x_myapp_agent'^ORtitle='Agent View' — 0 results
const agentView = Record({
    $id: Now.ID['agent-view'],
    table: 'sys_ui_view',
    data: { name: 'x_myapp_agent', title: 'Agent View', roles: ['itil'] },
})

Form({
    table: 'x_myapp_task',
    view: adminView,
    sections: [
        {
            caption: 'Admin Dashboard',
            content: [
                {
                    layout: 'two-column',
                    leftElements: [
                        { field: 'number', type: 'table_field' },
                        { field: 'priority', type: 'table_field' },
                    ],
                    rightElements: [
                        { field: 'escalation', type: 'table_field' },
                        { field: 'assignment_group', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})

Form({
    table: 'x_myapp_task',
    view: agentView,
    sections: [
        {
            caption: 'Work Details',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { field: 'short_description', type: 'table_field' },
                        { field: 'state', type: 'table_field' },
                        { field: 'assigned_to', type: 'table_field' },
                        { field: 'work_notes', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})

Record({
    $id: Now.ID['role-routing-rule'],
    table: 'sysrule_view',
    data: {
        name: 'Route by User Role',
        table: 'x_myapp_task',
        advanced: true,
        active: true,
        device_type: 'browser',
        overrides_user_preference: true,
        script: `(function overrideView(view, is_list) {
    var user = gs.getUser();
    if (user.hasRole('admin')) {
        answer = 'x_myapp_admin';
    } else if (user.hasRole('itil')) {
        answer = 'x_myapp_agent';
    } else {
        answer = null;
    }
})(view, is_list);`,
    },
})
```

### Complex Conditional Form Logic

Multi-field check on form records with proper `current` guard. Demonstrates checking multiple fields and setting different views based on combined conditions.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['complex-conditional-rule'],
    table: 'sysrule_view',
    data: {
        name: 'Complex Conditional Rule',
        table: 'incident',
        advanced: true,
        device_type: 'browser',
        active: true,
        script: `(function overrideView(view, is_list) {
            // CRITICAL: Check if form and current exists
            if (!is_list && typeof current !== 'undefined') {
                var priority = current.priority.toString();
                var state = current.state.toString();
                
                // Multi-field logic
                if (priority === '1' && state === '2') {
                    answer = 'critical_active_view';
                } else if (priority === '1' && state === '7') {
                    answer = 'critical_closed_view';
                } else {
                    answer = null; // Use default
                }
            } else {
                answer = null;
            }
        })(view, is_list);`,
    },
})
```

Key points:

- Always check `!is_list && typeof current !== 'undefined'` before accessing `current`

- Use `.toString()` for field comparisons

- Set `answer = null` to use default view

- Guard against list context where `current` is undefined

## Avoidance

- Never omit `^EQ` from conditions — encoded queries in view rules must end with `^EQ` or they will not evaluate correctly.

- Never use `title` as the view reference — always use the view's `name` field in `data.view` and in advanced scripts.

- Never create a view rule without creating the target view first — the view must exist in `sys_ui_view`.

- Never access `current` in list context — `current` is only available for form view rules, not list view rules. Check `is_list` in advanced scripts.

- Never forget the IIFE wrapper in advanced scripts — the script must be wrapped in `(function overrideView(view, is_list) { ... })(view, is_list);`.

- Never use view rules for access control — view rules switch layouts, not restrict access. Use `roles`/`group`/`user` on `sys_ui_view` for access control.

- Never create multiple advanced rules for the same table + device type — only the rule with the lowest `order` value executes. Combine all logic into a single advanced script.

- Never use field labels in encoded query conditions — use backend names from `sys_dictionary`. Query table `sys_dictionary` where `name=<table>^element=<field>`, retrieving `element` (see the `query` topic).

- Never access `current` without checking `!is_list && typeof current !== 'undefined'` — `current` may be undefined in list context or during evaluation.

- Never use Business Rules, Client Scripts, or UI Policies for view switching — always use View Rules (`sysrule_view`) for automatic view routing.

## See

- See the `view-guide` topic for full documentation on creating views, including uniqueness checks, access control patterns, and the `default_view` import.

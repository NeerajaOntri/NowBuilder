Version: 4.14.0

# Views

Guide for creating ServiceNow UI Views using the Record API. Views define custom layout variants for forms and lists, controlling which fields/columns are shown and who can access the layout.

## Uniqueness check - Mandatory

Do NOT write any `Record({ table: 'sys_ui_view' })` call until you have confirmed 0 results from a uniqueness query. `name` is the coalesce key — duplicate names silently overwrite existing views and destroy their `group`/`user`/`roles` fields on deploy. `title` collisions cause UX confusion (duplicate entries in the view selector dropdown) but not coalesce-level data loss.

For each view, query `sys_ui_view` where `name=<proposed_name>^ORtitle=<proposed_title>`, retrieving `sys_id,name,title,sys_scope` (see the `query` topic).

- 0 results → safe to proceed

- >0 results → change both `name` and `title`, re-query until 0

NEVER use `nameLIKE`, `name=` alone, or omit `title` — all three miss collisions.

## When to Use

- Creating a custom form layout different from the default (e.g., mobile view, admin dashboard)

- Restricting a layout to specific roles (e.g., ITIL agents, admins)

- Creating a hidden view for portal, API, or mobile app use only

- Providing group-specific or user-specific form/list layouts

- Defining a view that can be shared across `Form()` and `List()` calls

View names may contain letters, digits, underscores, and commas (`/^[a-zA-Z0-9_,]+$/`). No spaces or special characters.

Do not create a view for the standard/default layout — use `default_view` instead.

## Instructions

- Check if you need a custom view: If the user wants the default layout, import `default_view` from `@servicenow/sdk/core` and skip view creation entirely.

- Verify uniqueness (mandatory, per view): Query `sys_ui_view` where `name=<proposed_name>^ORtitle=<proposed_title>`, retrieving `sys_id,name,title,sys_scope` (see the `query` topic).

- 0 results → proceed

- >0 results → change both `name` and `title`, re-query until 0

- Choose the access pattern: Public (no restrictions), role-based, group-based, user-specific, or hidden.

- Verify roles exist (for role-based views): Query table `sys_user_role` where `name=<role>`, retrieving fields `sys_id,name` (see the `query` topic). All referenced roles must exist.

- Create the view Record: Use `Record({ table: 'sys_ui_view', ... })` and export as a const.

- Use the view const: Pass the same const to `Form({ view: myView })` and/or `List({ view: myView })`.

- Complete the solution: A view alone is non-functional — always create the form/list components that use it.

## Choosing the Right Approach

Before creating a view, determine if a view is the right solution for your use case:

Views vs View Rules vs UI Policies vs List Controls — choose based on scope:

| Scenario | Use |
| Whole form layout changes per role/group (different fields/sections) | View |
| Whole form layout switches automatically based on condition/device/state | View Rule |
| Specific fields hide/show/mandatory/read-only when condition met | UI Policy |
| Control list buttons (New/Edit) or disable pagination | List Control |

Views vs ACLs — choose based on intent:

| Intent | Use |
| Certain fields/sections should not appear in the form for some users | Views — fields absent from the form entirely |
| Restrict who can read/write/delete records or fields (data security) | ACLs — security enforcement |

## View Type Selection

Use this table to determine the correct view type from user intent. Match by meaning, not exact keywords.

| User Intent Signals | View Type | Action |
| "simple", "default", "basic", "normal" | Default View | `import { default_view } from '@servicenow/sdk/core'` — do not create a view Record |
| "admins", "ITIL", "role", generic function names (e.g., "managers", "agents") — title prefixes like CRO/CEO/CFO alone do NOT make it role-based if a specific person's name follows | Role-based | Set `roles` array with role name strings |
| "team", "department", "group", "assignment group", org-unit names — the word "group" after any term signals Group-based | Group-based | Query `sys_user_group` for sys_id, set `group` |
| "portal", "hidden", "API only", "not in dropdown", "mobile only" | Hidden | Set `hidden: true` |
| Named individual ("John", "Dr. Smith", "CEO Alice", "jane.admin") — a specific person's name is the signal, not the title prefix | User-specific | Query `sys_user` for sys_id, set `user` |
| "everyone", "all users", "public", "no restrictions" | Public | Omit all access fields ( `roles` , `group` , `user` , `hidden` ) |

## Key Concepts

Views are created using the `Record()` API with `table: 'sys_ui_view'`. See the `record-api` topic for the Record wrapper (`$id`, `table`, `data`, `$meta`). The compiler validates properties at build time.

### Key Properties (set inside `data`)

| Property | Type | Required | Description |
| `name` | `string` | Logically required | Technical identifier. This is the coalesce key — duplicate names silently overwrite. Not schema-mandatory ( `mandatory: false` ), but required for coalesce. |
| `title` | `string` | Logically required | Display name shown in the view selector dropdown. Not schema-mandatory, but recommended to avoid blank entries. Duplicates cause UX confusion but not data loss. |
| `roles` | `string[]` | No | Role name strings to restrict access (e.g., `['admin', 'itil']` ). `UserRolesColumn` — stored comma-joined, ≤100 chars total. |
| `group` | `string | Record<'sys_user_group'>` | No | sys_id string or Record reference of a `sys_user_group` to restrict to group members. |
| `user` | `string | Record<'sys_user'>` | No | sys_id string or Record reference of a `sys_user` to restrict to a single user. |
| `hidden` | `boolean` | No | If `true` , hidden from platform view selector (portal/API/mobile use only). |

For the full field schema (types, defaults, maxLengths), refer to the shipped SDK schema definition at `@servicenow/sdk` → `tables/sys_ui_view.now.ts`, or query table `sys_dictionary` where `name=sys_ui_view`, retrieving `element,column_label,internal_type,max_length,mandatory` (see the `query` topic).

### Access Control Patterns

| Pattern | Properties Set | Who Can Access |
| Public | None (no roles/user/group/hidden) | Everyone |
| Role-based | `roles: ['admin', 'itil']` | Users with specified roles |
| Group-based | `group: '<group_sys_id>'` | Members of the group |
| User-specific | `user: '<user_sys_id>'` | Only that specific user |
| Hidden | `hidden: true` | Not in dropdown — portal/API/mobile only. Warning: `hidden` is a UI visibility control only — it does NOT provide security. Admin users can still see and select hidden views. Always use `roles` , ACLs, and widget permissions for actual access control |

### Combining Hidden with Access Control

`hidden: true` can be combined with `roles`, `group`, or `user` for layered control — hidden from the dropdown AND restricted to specific users:

```
import { Record } from '@servicenow/sdk/core'

// Prerequisite: queried sys_ui_view where name='x_myapp_portal_admin'^ORtitle='Portal Admin View' — 0 results
const portalAdminView = Record({
    $id: Now.ID['portal-admin-view'],
    table: 'sys_ui_view',
    data: {
        name: 'x_myapp_portal_admin',
        title: 'Portal Admin View',
        hidden: true,
        roles: ['admin'],
    },
})
```

### Default View

For the standard layout, use `default_view` — no custom Record needed:

```
import { Form, default_view } from '@servicenow/sdk/core'

Form({ table: 'x_myapp_task', view: default_view, sections: [...] })
```

## Examples

### Complete Table Setup — View, Form, and List

Create a mobile view and wire it to both a compact form and a minimal list. A view alone is non-functional — always pair it with form/list components.

```
import '@servicenow/sdk/global'
import { Record, Form, List } from '@servicenow/sdk/core'

// Prerequisite: queried sys_ui_view where name='x_myapp_mobile'^ORtitle='Mobile View' — 0 results
const mobileView = Record({
    $id: Now.ID['mobile-view'],
    table: 'sys_ui_view',
    data: {
        name: 'x_myapp_mobile',
        title: 'Mobile View',
    },
})

Form({
    table: 'x_myapp_task',
    view: mobileView,
    sections: [
        {
            caption: 'Details',
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
```

### Multi-Persona Application — Admin vs Agent

Two views serve different audiences. The admin dashboard shows escalation fields and activity; the default view is a streamlined agent form. Each view drives its own form layout.

```
import '@servicenow/sdk/global'
import { Record, Form, List, default_view } from '@servicenow/sdk/core'

// Prerequisite: queried sys_ui_view where name='x_myapp_admin_dashboard'^ORtitle='Admin Dashboard' — 0 results
const adminView = Record({
    $id: Now.ID['admin-view'],
    table: 'sys_ui_view',
    data: {
        name: 'x_myapp_admin_dashboard',
        title: 'Admin Dashboard',
        roles: ['admin'],
    },
})

Form({
    table: 'x_myapp_task',
    view: adminView,
    sections: [
        {
            caption: 'Overview',
            content: [
                {
                    layout: 'two-column',
                    leftElements: [
                        { field: 'number', type: 'table_field' },
                        { field: 'state', type: 'table_field' },
                        { field: 'priority', type: 'table_field' },
                    ],
                    rightElements: [
                        { field: 'assigned_to', type: 'table_field' },
                        { field: 'assignment_group', type: 'table_field' },
                        { field: 'escalation', type: 'table_field' },
                    ],
                },
            ],
        },
        {
            caption: 'Activity',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { type: 'formatter', formatterRef: 'Activities_Filtered' },
                    ],
                },
            ],
        },
    ],
})

Form({
    table: 'x_myapp_task',
    view: default_view,
    sections: [
        {
            caption: 'Task Details',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { field: 'short_description', type: 'table_field' },
                        { field: 'state', type: 'table_field' },
                        { field: 'assigned_to', type: 'table_field' },
                        { field: 'description', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})

List({
    table: 'x_myapp_task',
    view: adminView,
    columns: [
        { element: 'number' },
        { element: 'short_description' },
        { element: 'state' },
        { element: 'priority' },
        { element: 'assigned_to' },
        { element: 'escalation' },
    ],
})
```

### Hidden View with View Rule — Portal Auto-Routing

Create a hidden view for portal/API consumers, then add a view rule so mobile users are automatically switched to it. Hidden views don't appear in the dropdown but are fully functional when accessed programmatically.

```
import '@servicenow/sdk/global'
import { Record, Form, List } from '@servicenow/sdk/core'

// Prerequisite: queried sys_ui_view where name='x_myapp_service_portal'^ORtitle='Service Portal View' — 0 results
const portalView = Record({
    $id: Now.ID['portal-view'],
    table: 'sys_ui_view',
    data: {
        name: 'x_myapp_service_portal',
        title: 'Service Portal View',
        hidden: true,
    },
})

Form({
    table: 'x_myapp_task',
    view: portalView,
    sections: [
        {
            caption: 'Request',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { field: 'short_description', type: 'table_field' },
                        { field: 'state', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})

List({
    table: 'x_myapp_task',
    view: portalView,
    columns: [
        { element: 'number' },
        { element: 'short_description' },
        { element: 'state' },
    ],
})

Record({
    $id: Now.ID['portal-mobile-rule'],
    table: 'sysrule_view',
    data: {
        name: 'Auto-Route Mobile to Portal View',
        table: 'x_myapp_task',
        view: 'x_myapp_service_portal',
        device_type: 'mobile',
        active: true,
        overrides_user_preference: true,
    },
})
```

### Group-Based View

Create a view restricted to members of a specific group. Always verify the group exists before creating the view.

```
import '@servicenow/sdk/global'
import { Record, Form } from '@servicenow/sdk/core'

// Verify group exists first: query table `sys_user_group` where `name=Facilities^active=true`, retrieving fields `sys_id,name` (see the `query` topic)

// Option A: Record reference (recommended)
const facilitiesGroup = Record({
    $id: Now.ID['facilities-group'],
    table: 'sys_user_group',
    data: {
        name: 'x_myapp_facilities',
        description: 'Facilities Team',
        active: true,
    },
})

// Prerequisite: queried sys_ui_view where name + title — 0 results
const facilitiesView = Record({
    $id: Now.ID['facilities-view'],
    table: 'sys_ui_view',
    data: {
        name: 'x_myapp_facilities',
        title: 'Facilities View',
        group: facilitiesGroup, // Record reference
    },
})

// Option B: sys_id string fallback (when group already exists on instance)
// Prerequisite: queried sys_ui_view where name + title — 0 results
const facilitiesViewBySysId = Record({
    $id: Now.ID['facilities-view-sysid'],
    table: 'sys_ui_view',
    data: {
        name: 'x_myapp_facilities_alt',
        title: 'Facilities View (Alt)',
        group: '<group_sys_id>', // sys_id from query result
    },
})

// Use the view in Form or List
Form({
    table: 'x_myapp_task',
    view: facilitiesView,
    sections: [
        {
            caption: 'Task Details',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { field: 'short_description', type: 'table_field' },
                        { field: 'assigned_to', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})
```

Access: Only members of the specified group can see and select this view.

### User-Specific View

Create a view restricted to a single user. Always verify the user exists before creating the view.

```
import '@servicenow/sdk/global'
import { Record, Form } from '@servicenow/sdk/core'

// Verify user exists first: query table `sys_user` where `user_name=jane.doe^active=true`, retrieving fields `sys_id,user_name` (see the `query` topic)

// Option A: Record reference (recommended)
const newUser = Record({
    $id: Now.ID['user-jane'],
    table: 'sys_user',
    data: {
        user_name: 'jane.smith',
        first_name: 'Jane',
        last_name: 'Smith',
        email: 'jane.smith@example.com',
        active: true,
    },
})

// Prerequisite: queried sys_ui_view where name + title — 0 results
const janePersonalView = Record({
    $id: Now.ID['jane-personal-view'],
    table: 'sys_ui_view',
    data: {
        name: 'incident_jane_smith_personal',
        title: "Jane Smith's Personal View",
        user: newUser, // Record reference
    },
})

// Option B: sys_id string fallback (when user already exists on instance)
// Prerequisite: queried sys_ui_view where name + title — 0 results
const janeView = Record({
    $id: Now.ID['jane-view'],
    table: 'sys_ui_view',
    data: {
        name: 'incident_jane_personal',
        title: "Jane's Personal View",
        user: '<user_sys_id>', // sys_id from query result
    },
})

// Use the view in Form or List
Form({
    table: 'incident',
    view: janePersonalView,
    sections: [
        {
            caption: 'My Incidents',
            content: [
                {
                    layout: 'two-column',
                    leftElements: [
                        { field: 'number', type: 'table_field' },
                        { field: 'short_description', type: 'table_field' },
                    ],
                    rightElements: [
                        { field: 'priority', type: 'table_field' },
                        { field: 'state', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})
```

Access: Only the specified user can see and select this view.

## Avoidance

- Never create a view Record for the default layout — use `import { default_view } from '@servicenow/sdk/core'` instead.

- Never use `nameLIKE<prefix>` to check view uniqueness — it misses title collisions. Always query with `name=<exact>^ORtitle=<exact>` per the "Uniqueness check - Mandatory" section.

- Never create a view without accompanying form/list components — a view alone is non-functional.

- Never create ACLs for view access — use the `roles`/`group`/`user` fields on `sys_ui_view`. ACLs are for table/record/field security.

- Never use `title` as the view reference — always use `name` when referencing views in view rules or other configurations.

- Never create many user-specific views when role-based views would work — prefer roles for maintainability and performance.

## See

- See the `view-rule-guide` topic for automatic view switching based on conditions, device type, or user roles.

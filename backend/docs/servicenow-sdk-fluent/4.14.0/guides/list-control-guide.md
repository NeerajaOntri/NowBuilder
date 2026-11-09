Version: 4.14.0

# List Controls

Guide for creating ServiceNow List Controls using the Record API. List controls configure the visibility and behavior of list UI elements — buttons (New, Edit), filters, links, inline editing, and pagination — based on roles or conditions.

## When to Use

- Hiding the New button on a list to prevent record creation

- Restricting the Edit button to specific roles (e.g., admins only)

- Hiding filters/breadcrumbs on a related list

- Disabling reference links in list columns

- Enabling inline editing (edit values directly in list cells)

- Omitting empty related lists from forms entirely

- Controlling list behavior for specific related lists vs top-level lists

## Instructions

- Each list control must have a unique `$id` using `Now.ID['value']` format.

- Set `table: 'sys_ui_list_control'` for all list control records.

- Provide valid `name` — the table name this list control applies to (not a display label).

- For related lists, always set `related_list` — without this field, the list control applies to the top-level list only, not any related list. Use format `'child_table.reference_field'` or `'REL:<sys_id>'`.

- Use condition scripts with `Now.include()` for external script files.

- Role fields accept arrays of role names: `["admin", "itil"]`.

### How to Configure

- Identify the target: Set `name` to the table name the list control applies to. For related lists, also set `related_list`.

- Choose what to control: Use `omit_*` boolean properties to hide UI elements (buttons, filters, links).

- Restrict by role: Use `*_roles` arrays to limit who sees specific buttons (New, Edit, filters, links).

- Add conditions: Use `*_condition` script properties for dynamic control based on record state.

- Configure inline editing: Use `list_edit_type` to enable row-by-row saving or disable inline editing entirely.

## Property Reference

List controls are created using the `Record()` API with `table: 'sys_ui_list_control'`. For complete property information:

- Record API: See the record-api topic for implementing records with the `Record()` function

- TypeScript schema: The shipped schema definition at `packages/core/src/fluent/tables/sys_ui_list_control.now.ts` in the SDK provides the authoritative property list

- Build-time validation: The compiler provides type checking and property validation based on the table schema

- Instance metadata: Query your ServiceNow instance dictionary for `sys_ui_list_control` to see all available fields and their descriptions

## Key Concepts

### Essential Properties

| Property | Type | Description |
| `name` | `table_name` | Table name this list control applies to. Validated as a table reference at runtime — must match an existing `sys_db_object.name` . For top-level lists: the table being viewed. For related lists: the parent table whose form displays the related list (required). Read-only on the platform after creation |
| `related_list` | `string` | Related list identifier in format `'child_table.reference_field'` or `'REL:<sys_id>'` . Required when controlling a related list — without it, the control applies to the top-level list only |
| `label` | `string` | Display label for the list (backed by `translated_field` for i18n). If not supplied, the default plural label for the table is used |

### Common UI Element Controls

| Property | Default | Description |
| `omit_new_button` | `false` | Hide the New button |
| `omit_edit_button` | `true` | Hide the Edit button. Fluent schema default is `true` ; platform dictionary default is `false` — when omitted from `data` , the platform default applies |
| `omit_links` | `false` | Hide reference field links |
| `omit_filters` | `false` | Hide filters/breadcrumbs |
| `omit_if_empty` | `false` | Hide related list entirely if no records |
| `omit_drilldown_link` | `false` | Disable first-column drill-down link |
| `omit_columns_if_empty` | `false` | For top-level lists: omit column headers AND filters/breadcrumbs when the list is empty |
| `omit_count` | `false` | Remove pagination count |
| `omit_count_views` | `false` | Remove pagination count for specific views only |
| `omit_count_views_list` | — | Comma-separated sys_ids of `sys_ui_view` records where pagination count is removed. Use with `omit_count_views: true` |
| `omit_related_list_count` | `false` | Hide the related list record count from displaying on initial load |

### Role Restrictions

Role properties accept `string[]` of role names. By platform convention, an empty role list means no role gate is applied (all users have access).

| Property | Description |
| `new_roles` | Roles that can see the New button |
| `edit_roles` | Roles that can see the Edit button |
| `filter_roles` | Roles that can see filters |
| `link_roles` | Roles that can see reference links |

### Condition Scripts

Condition scripts evaluate to `true` to hide the element. Use `Now.include()` for external script files.

| Property | Behavior |
| `new_condition` | If `true` , omit New button |
| `edit_condition` | If `true` , omit Edit button |
| `link_condition` | If `true` , omit reference links |
| `filter_condition` | If `true` , omit filter options |
| `empty_condition` | If `true` , omit list if empty |
| `columns_condition` | If `true` , omit column headers if empty |

### Related List Targeting

A list control without `related_list` applies to the top-level list only. To target a related list, you must set `related_list`:

- Reference-based: `'child_table.reference_field'` (e.g., `'incident.parent_incident'`)

- Custom relationship: `'REL:<sys_id>'` (e.g., `'REL:b9edf0ca0a0a0b010035de2d6b579a03'`)

Note: The related list must already be configured on the parent form for the list control to have a visible effect. The recommended approach is using `sys_ui_related_list` + `sys_ui_related_list_entry` records via the `Record()` API — see the `relationship-guide` topic. Alternatively, a `Form()` API embedded list section (`{ type: 'list', listType: '12M', listRef: 'child_table.reference_field' }`) also causes a related list to appear on the form, but note that this creates `sys_ui_element` records (not `sys_ui_related_list_entry` records) and does not properly configure the related list — use the `Record()` API approach for full control.

### Inline Editing

| Property | Type/Values | Description |
| `list_edit_type` | `'save_by_row'` | `'disabled'` | Save mode: row-by-row or disabled. To explicitly select cell-edit mode (Save immediately), use `'NULL_OVERRIDE'` — a platform `sys_choice` sentinel for cell-edit mode. At runtime, records store empty string; fluent emits `NULL_OVERRIDE` so the empty-string value takes effect rather than the schema default of `save_by_row` . Leave unset for platform default |
| `list_edit_insert_row` | `boolean` | Show empty row at bottom for inline record creation (default: `false` ) |
| `list_edit_ref_qual_tag` | `string` | Unique tag sent to reference qualifiers as the script variable `listEditRefQualTag` during list editing |
| `edit_default_filter` | `conditions` | Default filter applied when editing the list. Uses encoded query syntax (e.g., `'state=1^priority<3'` ) |

### Condition Script Mechanics

Condition scripts control list UI elements dynamically based on record state. Key mechanics:

- `parent` object: Access parent record fields in related list conditions (e.g., `parent.state`). For top-level (primary) lists, there is no `parent` record — do not use `parent` in top-level list conditions

- `answer` variable: Set to `true` to hide the element, `false` to show it

- OR logic: If both `omit_*` property and condition script are present, the element is hidden if either evaluates to true

- External scripts: Use `Now.include()` to reference external script files for reusability

### Additional Properties

| Property | Default | Description |
| `hierarchical_lists` | `false` | Enable hierarchical (tree) display for parent-child table relationships |
| `disable_nlq` | `false` | Disable Natural Language Query (NLQ) filter for this specific list |
| `sys_overrides` | — | Reference to another `sys_ui_list_control` record that this control overrides. Used for scope-based override hierarchies — typically when one scope's list control needs to override another's. Most authors will not need this |

### REL: Format for Explicit Relationships

For explicit relationships (custom `sys_relationship` records), use the `REL:` prefix format:

```
related_list: `REL:${record.$id}`
```

The `$id` token resolves to the relationship's `sys_id` at build time; fluent stores the literal `REL:<sys_id>` string in `related_list`, and the platform interprets the `REL:` prefix at runtime.

## Examples

### Read-Only Audit Trail — List Control with List and Form

Lock down an audit log: no creation, no editing, hidden if empty. Combine the list control with a list definition and embed as a related list on the parent form. The `related_list` field targets the specific relationship.

```
import '@servicenow/sdk/global'
import { Record, Form, List } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['audit-list-control'],
    table: 'sys_ui_list_control',
    data: {
        name: 'x_myapp_task',
        related_list: 'x_myapp_audit_log.task',
        label: 'Audit Trail',
        omit_new_button: true,
        omit_edit_button: true,
        list_edit_type: 'disabled',
        omit_links: true,
        omit_if_empty: true,
    },
})

List({
    table: 'x_myapp_audit_log',
    view: 'Default view',
    columns: [
        { element: 'sys_created_on' },
        { element: 'sys_created_by' },
        { element: 'action' },
        { element: 'description' },
    ],
})

Form({
    table: 'x_myapp_task',
    view: 'Default view',
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
        {
            caption: 'Audit',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { type: 'list', listType: '12M', listRef: 'x_myapp_audit_log.task' },
                    ],
                },
            ],
        },
    ],
})
```

### Role-Tiered Task Management — Top-Level and Related List Controls

Apply different controls to the same table depending on context. The top-level list restricts editing to admins while keeping the New button for everyone. The related list (subtasks on the parent form) hides filters and enables row-by-row inline editing for fast data entry.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['task-top-level-control'],
    table: 'sys_ui_list_control',
    data: {
        name: 'x_myapp_task',
        omit_edit_button: false,
        edit_roles: ['admin'],
    },
})

Record({
    $id: Now.ID['subtask-related-control'],
    table: 'sys_ui_list_control',
    data: {
        name: 'x_myapp_task',
        related_list: 'x_myapp_subtask.parent',
        omit_filters: true,
        list_edit_type: 'save_by_row',
        list_edit_insert_row: true,
    },
})
```

### Self-Service Portal List — Controls with Hidden View

Configure a list that hides administrative UI: no filters, no links, no edit. The hidden view controls which columns are displayed, while the list control restricts UI elements across all views of the table. Use this pattern for tables where all users should have a restricted, read-only list experience. For more on creating custom views, see the `platform-view-guide` and `platform-view-lists-guide` topics.

```
import '@servicenow/sdk/global'
import { Record, List } from '@servicenow/sdk/core'

const portalView = Record({
    $id: Now.ID['portal-view'],
    table: 'sys_ui_view',
    data: {
        name: 'x_myapp_portal',
        title: 'Portal View',
        hidden: true,
    },
})

List({
    table: 'x_myapp_request',
    view: portalView,
    columns: [
        { element: 'number' },
        { element: 'short_description' },
        { element: 'state' },
        { element: 'sys_created_on' },
    ],
})

Record({
    $id: Now.ID['portal-list-control'],
    table: 'sys_ui_list_control',
    data: {
        name: 'x_myapp_request',
        omit_new_button: true,
        omit_edit_button: true,
        omit_filters: true,
        omit_links: true,
        omit_drilldown_link: true,
        list_edit_type: 'disabled',
    },
})
```

### Condition Script — Hide New Button by Parent State

Hide the New button on a related list when the parent record is in a specific state (e.g., resolved or closed). Uses `Now.include()` for external script and demonstrates the `parent` object pattern.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['incident-child-conditional'],
    table: 'sys_ui_list_control',
    data: {
        name: 'incident',
        related_list: 'incident.parent_incident',
        new_condition: Now.include('../scripts/hideWhenResolved.js'),
        edit_condition: Now.include('../scripts/hideWhenResolved.js'),
    },
})
```

Condition script (`hideWhenResolved.js`):

```
var answer
if (parent.state == 6 || parent.state == 7) {
    answer = true // hide when Resolved (6) or Closed (7)
} else {
    answer = false // show otherwise
}
answer
```

How it works: The `parent` object provides access to the parent record's fields. Setting `answer = true` hides the button.

### Cross-Table Conditional List Control — Hide Buttons by Parent Status

Hide New and Edit buttons on a child table's related list based on the parent record's status. This is the most common pattern for cross-table relationships where the child table (e.g., Line Items) appears as a related list on the parent table's form (e.g., Purchase Requisition).

Prerequisite: The related list must be configured on the parent form before the list control can take effect. This example uses `sys_ui_related_list` + `sys_ui_related_list_entry` records (see the `relationship-guide` topic). Alternatively, an embedded list section in `Form()` also works.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

// Step 1: Register the related list on the parent form
const purchaseReqRelatedList = Record({
    $id: Now.ID['purchase-req-related-list'],
    table: 'sys_ui_related_list',
    data: {
        name: 'x_myapp_purchase_requisition',
        view: 'Default view',
    },
})

Record({
    $id: Now.ID['line-item-related-list-entry'],
    table: 'sys_ui_related_list_entry',
    data: {
        list_id: purchaseReqRelatedList,
        position: 0,
        related_list: 'x_myapp_line_item.purchase_requisition',
    },
})

// Step 2: Add the list control to conditionally hide buttons
Record({
    $id: Now.ID['line-item-list-control'],
    table: 'sys_ui_list_control',
    data: {
        name: 'x_myapp_purchase_requisition',
        related_list: 'x_myapp_line_item.purchase_requisition',
        new_condition: `var answer;
if (parent.approval_status == 'approved' || parent.approval_status == 'rejected') {
    answer = true;
} else {
    answer = false;
}
answer;`,
        edit_condition: `var answer;
if (parent.approval_status == 'approved' || parent.approval_status == 'rejected') {
    answer = true;
} else {
    answer = false;
}
answer;`,
    },
})
```

Key points:

- Related list must be configured first (via `sys_ui_related_list` + `sys_ui_related_list_entry` as shown above, or via Form API embedded list) — the list control only works if the related list is already on the parent form

- `name` is the parent table (`x_myapp_purchase_requisition`) — the table whose form displays the related list

- `related_list` is `'child_table.reference_field'` format — identifying which related list on the parent form to control

- Inline condition scripts use the `parent` object to access the parent record's fields directly

- Both `new_condition` and `edit_condition` hide their respective buttons when the parent's `approval_status` is `'approved'` or `'rejected'`

### Performance Controls — Large Table

Disable pagination count and related list count for large tables to improve performance. Useful when record counts are expensive to calculate.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['large-table-control'],
    table: 'sys_ui_list_control',
    data: {
        name: 'x_myapp_large_table',
        omit_count: true,
        omit_related_list_count: true,
    },
})
```

Result: Pagination shows "Previous/Next" without total count. Related lists show no record count badge.

### Performance Controls — View-Specific Count Omission

Remove pagination count only for specific views while keeping it for others. Useful when certain views have expensive queries but others need count information.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

const mobileView = Record({
    $id: Now.ID['mobile-view'],
    table: 'sys_ui_view',
    data: { name: 'x_myapp_mobile', title: 'Mobile View' },
})

const reportView = Record({
    $id: Now.ID['report-view'],
    table: 'sys_ui_view',
    data: { name: 'x_myapp_report', title: 'Report View' },
})

Record({
    $id: Now.ID['view-specific-count-control'],
    table: 'sys_ui_list_control',
    data: {
        name: 'x_myapp_large_table',
        omit_count_views: true,
        omit_count_views_list: `${mobileView.$id},${reportView.$id}`,
    },
})
```

Result: Pagination count is hidden only in Mobile View and Report View. Default view and other views still show the count.

### Filter & Link Role Restrictions

Restrict filters and reference links to specific roles. Useful for sensitive data where only certain users should navigate to related records.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['restricted-filter-link'],
    table: 'sys_ui_list_control',
    data: {
        name: 'x_myapp_sensitive_data',
        filter_roles: ['admin'],
        link_roles: ['admin', 'itil'],
    },
})
```

Result: Only admins see filters. Only admins and ITIL users see reference links in list columns.

### Hierarchical List

Enable hierarchical display for parent-child table relationships. Disables natural language query (NLQ) to prevent conflicts with hierarchy rendering.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['hierarchical-list'],
    table: 'sys_ui_list_control',
    data: {
        name: 'x_myapp_category',
        hierarchical_lists: true,
        disable_nlq: true,
    },
})
```

Result: List displays in tree structure with expand/collapse icons. NLQ search is disabled.

### Reference Qualifier Tag

Use reference qualifier tags to filter reference fields during inline list editing. The tag is evaluated when the user edits the field in the list.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['ref-qual-tag-control'],
    table: 'sys_ui_list_control',
    data: {
        name: 'incident',
        list_edit_ref_qual_tag: 'assignment_group_filter',
        list_edit_type: 'save_by_row',
    },
})
```

Note: The `list_edit_ref_qual_tag` applies to any inline-edit mode, including cell-edit (`NULL_OVERRIDE`) and `save_by_row` — it is not specific to row-based editing.

Use case: Filter assignment groups based on incident category during inline editing.

### Custom Relationship List Control

Target a custom relationship using the `REL:` prefix format. The relationship sys_id is resolved at build time.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

const customRelationship = Record({
    $id: Now.ID['custom-rel'],
    table: 'sys_relationship',
    data: {
        name: 'Custom Relationship',
        basic_apply_to: 'x_myapp_parent',
        basic_query_from: 'x_myapp_child',
    },
})

Record({
    $id: Now.ID['custom-rel-control'],
    table: 'sys_ui_list_control',
    data: {
        name: 'x_myapp_parent',
        related_list: `REL:${customRelationship.$id}`,
        omit_new_button: true,
    },
})
```

Result: List control applies to the custom relationship-based related list.

### Hide Links/Filters — Dedicated Example

Remove all links and filter options from a list. Useful for read-only data views where navigation and filtering should be restricted.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['restricted-list-control'],
    table: 'sys_ui_list_control',
    data: {
        name: 'x_myapp_sensitive_data',
        omit_links: true,
        omit_filters: true,
        omit_drilldown_link: true,
    },
})
```

Result:

- No reference links to other tables

- No filters or breadcrumbs

- First column is not clickable (no drilldown)

### Hide Related List if Empty

Hide a related list completely when it has no records. Reduces form clutter by removing empty sections.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['omit-if-empty-control'],
    table: 'sys_ui_list_control',
    data: {
        name: 'incident',
        related_list: 'incident.parent_incident',
        omit_if_empty: true,
    },
})
```

NOTE: The `related_list` field must be set to target a specific related list. Without it, the control applies to the top-level list.

Result: Related list header and section are completely hidden when there are no child incidents.

### Row Edit Mode — Save by Row

Enable row-based editing for incident priority updates where users might change multiple fields before saving.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['incident-row-edit'],
    table: 'sys_ui_list_control',
    data: {
        name: 'x_myapp_incident',
        list_edit_type: 'save_by_row',
    },
})
```

Use case: When users need to update multiple fields in a row before committing changes.

Behavior:

- User clicks a cell

- Edits multiple cells in the same row

- Changes saved when user navigates away from row OR clicks Save icon

- Allows bulk field updates before save

## Avoidance

- Never confuse `name` with a display label — `name` is the table name the control applies to, not a human-readable label. Use `label` for display text.

- Never use role restrictions and omit together — if you omit a button entirely (`omit_new_button: true`), role restrictions (`new_roles`) have no effect. Use one or the other.

- Never apply list controls without testing — controls affect all users viewing that list. Test with different roles to verify correct behavior.

- Never use `omit_if_empty` on top-level lists — this property is designed for related lists on forms, not standalone table lists.

- Never omit `related_list` when targeting a related list — without `related_list`, the control applies to the top-level list only, not any related list on a form.

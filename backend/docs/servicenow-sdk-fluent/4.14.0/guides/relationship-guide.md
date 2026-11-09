Version: 4.14.0

# Relationships and Related Lists

Guide for creating ServiceNow relationships and related lists using the Record API. Related lists display child or associated records on a parent form — for example, showing incident tasks on an incident form.

## When to Use

- Adding a related list to a form showing child records (e.g., subtasks on a task)

- Displaying records from a table that references the current record

- Creating custom relationships between tables that have no direct reference field

- Adding platform relationships (Attachments, Approval History) to a form

- Configuring multiple related lists on a single form

- Linking custom tables to global ServiceNow tables (e.g., custom notes on OOB incident table)

## Instructions

- Determine the relationship type:

- Reference field exists between tables → implicit relationship (no `sys_relationship` needed)

- No reference field → explicit relationship (create `sys_relationship` first)

- Platform relationship (Attachments, etc.) → use the known `REL:` ID directly

- Create the records in order using `Record()` API:

- Explicit: `sys_relationship` → `sys_ui_related_list` → `sys_ui_related_list_entry`

- Implicit/Platform: `sys_ui_related_list` → `sys_ui_related_list_entry`

- Important: Always use the `Record()` API to create these records. Do not use the Form API's `list` element type — it creates different records (`sys_ui_element`) and will not configure related lists properly.

- Set `related_list` format correctly:

- Implicit: `'child_table.reference_field'` (e.g., `'x_myapp_subtask.parent'`)

- Explicit: `'REL:${relationshipRecord.$id}'`

- Platform: `'REL:<known_sys_id>'`

- Use one container per table: Create one `sys_ui_related_list` per parent table, then add multiple `sys_ui_related_list_entry` records with sequential positions.

## Property Reference

Relationships and related lists are created using the `Record()` API with three tables. See the `record-api` topic for implementing records with the `Record()` function. The shipped schema definitions in `packages/core/src/fluent/tables/` provide the authoritative property list.

### sys_relationship

| Property | Type | Description |
| `name` | `string` (translated_text) | Name of the relationship |
| `basic_apply_to` | `string` (table_name) | Parent table name (basic mode) |
| `basic_query_from` | `string` (table_name) | Child table name (basic mode) |
| `reference_field` | `string` (field_name) | Reference field on child table pointing to parent |
| `query_with` | `string` (script_plain) | Script to refine the query (IIFE format recommended). Default: IIFE template |
| `advanced` | `boolean` | Use advanced script fields instead of basic table names (default: `false` ) |
| `simple_reference` | `boolean` | Mark as a simple reference relationship. Pair with `reference_field` for basic reference-based relationships |
| `apply_to` | `string` (script_plain) | Script to determine parent table dynamically (advanced mode) |
| `query_from` | `string` (script_plain) | Script to determine child table dynamically (advanced mode) |
| `insert_callback` | `string` (script_plain) | Script executed when a record is inserted through the related list |

### sys_ui_related_list

| Property | Type | Description |
| `name` | `string` (table_name) | Parent table name |
| `view` | `reference` (sys_ui_view) | View title (e.g., `'Default view'` ); the compiler resolves the title to the underlying sys_id at build time |
| `filter` | `conditions` | Encoded query to filter the related list (max 3500 chars) |
| `order_by` | `string` | Default sort field for the related list |
| `position` | `integer` | Display position |

### sys_ui_related_list_entry

| Property | Type | Description |
| `list_id` | `reference` (sys_ui_related_list) | Reference to the parent list container. Use `container.$id` |
| `related_list` | `string` | Related list identifier: `'child_table.ref_field'` or `'REL:<sys_id>'` |
| `position` | `integer` | Display order (0, 1, 2...) |
| `filter` | `conditions` | Encoded query to filter records in the related list |
| `order_by` | `string` | Default sort field for the related list |

## Key Concepts

### Relationship Types

| Type | When to Use | Records Needed |
| Implicit | Child table has a reference field pointing to parent | `sys_ui_related_list` + `sys_ui_related_list_entry` |
| Explicit | No reference field, or custom query logic needed | `sys_relationship` + `sys_ui_related_list` + `sys_ui_related_list_entry` |
| Platform | Well-known relationships (Attachments, Approvals) | `sys_ui_related_list` + `sys_ui_related_list_entry` |

### Related List Entry Format

| Relationship Type | `related_list` Value |
| Implicit (reference) | `'child_table.reference_field'` |
| Explicit (custom) | ``REL:${relationshipRecord.$id}`` |
| Platform (known) | `'REL:<hardcoded_sys_id>'` |

### Common Platform Relationship IDs

| Relationship | ID |
| Attachments | `REL:b9edf0ca0a0a0b010035de2d6b579a03` |
| Applications with Role | `REL:66c422fac0a80a880012fadcb8c2480e` |
| Approval History | `REL:247c6f15670303003b4687cb5685ef32` |

### query_with Script Format

The `query_with` field should use the IIFE wrapper (the column default and OOB convention). Bare statements such as `current.addQuery(...)` are also accepted by the platform, but the IIFE keeps complex scripts scoped and readable:

```
query_with: `(function refineQuery(current, parent) {
    current.addQuery('field_name', parent.field_name);
})(current, parent);`
```

- `current` = query on the child table

- `parent` = record on the parent form

### Multiple Related Lists Pattern

One `sys_ui_related_list` container per parent table, multiple `sys_ui_related_list_entry` records:

- Same parent table + multiple child relationships → one container, multiple entries

- Different parent tables → separate containers

- Use sequential `position` values (0, 1, 2...) for display order

### Optional Entry Fields

The `sys_ui_related_list_entry` table supports optional fields for filtering and sorting:

- filter — Encoded query string to filter records in the related list (e.g., `'active=true'`)

- order_by — Field name to sort the related list by default (e.g., `'sys_created_on'`)

### Naming Conventions

Follow these naming patterns for consistency:

| Record Type | Naming Pattern | Example |
| `sys_relationship` | `<parent>_to_<child>` | `task_to_audit_log` |
| `sys_ui_related_list` | `<parent_table>` | `incident` |
| `sys_ui_related_list_entry` | `<parent>_<child>_entry` | `incident_task_entry` |

Use descriptive names that clearly indicate the relationship direction and purpose.

### Basic vs Advanced Fields

Basic fields (simple reference-based relationships):

- `basic_apply_to` — parent table name

- `basic_query_from` — child table name

- `reference_field` — reference field name on child table pointing to parent

Advanced fields (script-based table resolution):

- `apply_to` — script to determine the parent table dynamically

- `query_from` — script to determine the child table dynamically

Common fields (used by both basic and advanced):

- `query_with` — script to refine the query (IIFE format recommended)

- `insert_callback` — script executed when a record is inserted through the related list

Use basic fields when tables are known at design time. Use advanced fields for dynamic table resolution (e.g., polymorphic relationships, context-dependent queries).

## Examples

`$id` values in the examples below are illustrative. Use unique IDs per record in your app to avoid coalesce collisions.

### Custom Table Linked to Global ServiceNow Table

Display custom table records on a global ServiceNow table form. For example, showing custom investigator notes on the out-of-box `incident` table.

Scenario: Create a custom notes table that references the global `incident` table, and display notes on the incident form.

```
import '@servicenow/sdk/global'
import { Record, Table, StringColumn, ReferenceColumn } from '@servicenow/sdk/core'

// Create custom notes table in your app scope
export const x_myapp_investigator_note = Table({
    name: 'x_myapp_investigator_note',
    label: 'Investigator Notes',
    schema: {
        note_content: StringColumn({
            label: 'Note Content',
            maxLength: 4000,
        }),
        incident_ref: ReferenceColumn({
            label: 'Incident',
            referenceTable: 'incident', // References global incident table
            mandatory: true,
        }),
    },
})

// Create related list container for incident table
const incidentRelatedList = Record({
    $id: Now.ID['incident-related-list'],
    table: 'sys_ui_related_list',
    data: {
        name: 'incident', // Global incident table
        view: 'Default view',
    },
})

// Add notes as related list entry on incident form (implicit relationship)
Record({
    $id: Now.ID['incident-notes-entry'],
    table: 'sys_ui_related_list_entry',
    data: {
        list_id: incidentRelatedList,
        position: 0,
        related_list: 'x_myapp_investigator_note.incident_ref', // Custom table.reference field
    },
})
```

Key points:

- Custom table (`x_myapp_investigator_note`) references global table (`incident`)

- Use implicit relationship format: `'custom_table.reference_field'`

- The `sys_ui_related_list` targets the global table name (`incident`)

- No `sys_relationship` needed because reference field exists

- This pattern works for any OOB ServiceNow table (incident, task, change_request, etc.)

### Implicit Relationship (Reference Field Exists)

Child table `x_myapp_subtask` has a `parent` field referencing `x_myapp_task`:

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

const taskRelatedList = Record({
    $id: Now.ID['task-related-list'],
    table: 'sys_ui_related_list',
    data: {
        name: 'x_myapp_task',
        view: 'Default view',
    },
})

Record({
    $id: Now.ID['subtask-entry'],
    table: 'sys_ui_related_list_entry',
    data: {
        list_id: taskRelatedList,
        position: 0,
        related_list: 'x_myapp_subtask.parent',
    },
})
```

### Explicit Relationship (No Reference Field)

Custom relationship between `x_myapp_project` and `x_myapp_resource`:

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

const projectResourceRel = Record({
    $id: Now.ID['project-resource-rel'],
    table: 'sys_relationship',
    data: {
        advanced: false,
        basic_apply_to: 'x_myapp_project',
        basic_query_from: 'x_myapp_resource',
        name: 'Project Resources',
        query_with: `(function refineQuery(current, parent) {
    current.addQuery('project_id', parent.sys_id);
})(current, parent);`,
        simple_reference: false,
    },
})

const projectRelatedList = Record({
    $id: Now.ID['project-related-list'],
    table: 'sys_ui_related_list',
    data: {
        name: 'x_myapp_project',
        view: 'Default view',
    },
})

Record({
    $id: Now.ID['resource-entry'],
    table: 'sys_ui_related_list_entry',
    data: {
        list_id: projectRelatedList,
        position: 0,
        related_list: `REL:${projectResourceRel}`,
    },
})
```

### Platform Relationship (Attachments)

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

const taskRelatedList = Record({
    $id: Now.ID['task-related-list'],
    table: 'sys_ui_related_list',
    data: {
        name: 'x_myapp_task',
        view: 'Default view',
    },
})

Record({
    $id: Now.ID['attachments-entry'],
    table: 'sys_ui_related_list_entry',
    data: {
        list_id: taskRelatedList,
        position: 0,
        related_list: 'REL:b9edf0ca0a0a0b010035de2d6b579a03',
    },
})
```

### Multiple Related Lists on One Table

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

const taskRelatedList = Record({
    $id: Now.ID['task-related-lists'],
    table: 'sys_ui_related_list',
    data: {
        name: 'x_myapp_task',
        view: 'Default view',
    },
})

Record({
    $id: Now.ID['subtask-entry'],
    table: 'sys_ui_related_list_entry',
    data: {
        list_id: taskRelatedList,
        position: 0,
        related_list: 'x_myapp_subtask.parent',
    },
})

Record({
    $id: Now.ID['comment-entry'],
    table: 'sys_ui_related_list_entry',
    data: {
        list_id: taskRelatedList,
        position: 1,
        related_list: 'x_myapp_comment.task',
    },
})

Record({
    $id: Now.ID['attachments-entry'],
    table: 'sys_ui_related_list_entry',
    data: {
        list_id: taskRelatedList,
        position: 2,
        related_list: 'REL:b9edf0ca0a0a0b010035de2d6b579a03',
    },
})
```

### Chained Relationships (Two-Hop Queries)

Display records from a child table on a parent form by traversing an intermediate reference field. For example, showing comments on a project form when comments reference tasks, and tasks reference projects.

When to use: Parent form needs to display records from a table that doesn't directly reference it, but references an intermediate table that does reference the parent.

Pattern: Create an explicit relationship with `query_with` using dot-notation to traverse the reference chain.

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

// Scenario: Show comments on project form
// Relationship chain: project <- task.project_ref <- comment.task_ref
// Comments reference tasks; tasks reference projects

const projectCommentsRel = Record({
    $id: Now.ID['project-comments-rel'],
    table: 'sys_relationship',
    data: {
        advanced: false,
        basic_apply_to: 'x_myapp_project',
        basic_query_from: 'x_myapp_comment',
        name: 'Project Comments (via Tasks)',
        query_with: `(function refineQuery(current, parent) {
    // Traverse: comment.task_ref -> task.project_ref = parent.sys_id
    current.addQuery('task_ref.project_ref', parent.sys_id);
})(current, parent);`,
        simple_reference: false,
    },
})

const projectRelatedList = Record({
    $id: Now.ID['project-related-list'],
    table: 'sys_ui_related_list',
    data: {
        name: 'x_myapp_project',
        view: 'Default view',
    },
})

// Tasks related list entry (implicit - direct reference exists)
Record({
    $id: Now.ID['project-tasks-entry'],
    table: 'sys_ui_related_list_entry',
    data: {
        list_id: projectRelatedList,
        position: 0,
        related_list: 'x_myapp_task.project_ref',
    },
})

// Comments related list entry (explicit - uses chained relationship)
Record({
    $id: Now.ID['project-comments-entry'],
    table: 'sys_ui_related_list_entry',
    data: {
        list_id: projectRelatedList,
        position: 1,
        related_list: `REL:${projectCommentsRel}`,
    },
})
```

Key points:

- Use dot-notation in `addQuery()` to traverse references: `'child_ref.parent_ref'`. Dot-walk follows reference columns on the child table — `task_ref` must be a reference field on `x_myapp_comment`, and `project_ref` must be a reference field on `x_myapp_task`

- The first field (`task_ref`) is on the child table (`x_myapp_comment`)

- The second field (`project_ref`) is on the intermediate table (`x_myapp_task`)

- Always use `REL:` format for explicit relationships

- Combine with implicit relationships on the same form (tasks use implicit, comments use explicit)

## Avoidance

- Never use Form API `list` elements to configure related lists — the Form API's `list` element type (`{ type: 'list', listType: '12M', listRef: '...' }`) creates `sys_ui_element` records, NOT `sys_ui_related_list_entry` records. These are fundamentally different record types. Always use the `Record()` API to create `sys_ui_related_list` and `sys_ui_related_list_entry` records — this is the only correct way to configure related lists, whether the related list appears at the bottom of the form or within a form section. The Form API `list` element does NOT properly configure related lists and must not be used for this purpose, even when the prompt asks for related lists in "separate sections" or "embedded in the form."

- Never mix basic and advanced relationship fields — use either `basic_apply_to`/`basic_query_from` or `apply_to`/`query_from`, not both.

- Prefer the IIFE wrapper in `query_with` scripts — the column default `(function refineQuery(current, parent) { ... })(current, parent);` scopes variables and matches OOB relationships. Bare `current.addQuery(...)` statements work but are harder to maintain in complex scripts.

- Never create a new `sys_relationship` without searching first — query `sys_relationship` using `now-sdk query sys_relationship --query 'basic_apply_to=<parent>^basic_query_from=<child>' --fields sys_id,name` to check if the relationship already exists. See the `query` topic for details.

- Never hardcode sys_id strings in record references — use `record.$id` variable references for portability across environments. Platform relationship IDs are the one exception.

- Never create `sys_ui_related_list_entry` without a `sys_ui_related_list` — the entry must reference a list container via `list_id`.

- Never create multiple `sys_ui_related_list` for the same table — use one container per parent table with multiple entries.

- Never create a `sys_relationship` for implicit relationships — if a reference field already exists between the tables, use `'child_table.reference_field'` format directly.

- Never forget the `REL:` prefix for explicit/platform relationships — entries referencing `sys_relationship` records must use `'REL:...'` format.

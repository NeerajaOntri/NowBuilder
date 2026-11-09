Version: 4.14.0

# Lists

Guide for creating ServiceNow list layouts using the `List` API. A list defines which columns appear when users view table records in list/table view. Each `List()` call creates a `sys_ui_list` record and its associated `sys_ui_list_element` records on the target instance.

## When to Use

- Defining which columns appear in a table's list view

- Creating view-specific list layouts (e.g., a mobile view with fewer columns, a manager view with different columns)

- Adding aggregate calculations (sum, average, min, max) to numeric columns — visible at the bottom of the list

- Displaying related record data via dot-walked fields (e.g., `assigned_to.department`)

- Configuring related list column layouts (columns shown in a related list embedded on a form)

## Instructions

- Bind to a view: Every list requires a view. Use `default_view` for the basic layout, or create a custom `Record({ table: 'sys_ui_view', ... })` and pass the const.

- Define columns: Add fields to the `columns` array. Each entry can be a plain string (field name only) or a `ListElement` object when you need position control or aggregates.

- Order columns: Column order defaults to array index. Use explicit `position` values only when you need to override the natural order.

- Scan the prompt for aggregate keywords: If any numeric field's description contains summary language, you MUST set the corresponding aggregate flag on that column. See the Aggregate Keyword Mapping table below.

- Use dot walking for references: Use `'field.related_field'` syntax to display data from referenced records (e.g., `'assigned_to.department'`).

- For related lists: Set `parent` to the parent table name. If the relationship is implicit (a reference field exists), no `relationship` property is needed. For custom/explicit relationships, also set `relationship` to the `sys_relationship` Record const.

## Aggregate Keyword Mapping

When the user prompt contains any of these keywords for a numeric field, set the corresponding aggregate property on that column's `ListElement`:

| Prompt Keywords | Property | Example |
| "total", "sum", "tally", "running total", "grand total" | `sum: true` | `{ element: 'effort_points', sum: true }` |
| "average", "mean", "avg" | `averageValue: true` | `{ element: 'cost', averageValue: true }` |
| "minimum", "lowest", "min", "floor" | `minValue: true` | `{ element: 'duration', minValue: true }` |
| "maximum", "highest", "max", "ceiling" | `maxValue: true` | `{ element: 'score', maxValue: true }` |

Rules:

- Aggregates only render on numeric column types: `IntegerColumn`, `DecimalColumn`, `FloatColumn`

- Fluent does not validate column types for aggregates — setting `sum: true` on a `StringColumn` builds and deploys without error, but the platform won't render the aggregate footer. Do not set them on `StringColumn`, `ReferenceColumn`, `DateTimeColumn`, etc.

- Multiple aggregates can be combined on a single column (e.g., `sum: true, averageValue: true`)

## API Reference

See the list-api topic for the full property reference, including `ListElement` type and `parent`/`relationship` properties for related lists.

## Key Concepts

### View Binding — One Table, Multiple List Layouts

A `List()` is bound to a specific `view`. The same table can have different list layouts for different views. Each `List()` call with a different view creates a separate `sys_ui_list` record.

```
List({ table: 'x_myapp_ticket', view: default_view, columns: [...] })     → default list layout
List({ table: 'x_myapp_ticket', view: receptionView, columns: [...] })    → reception-specific columns
List({ table: 'x_myapp_ticket', view: securityView, columns: [...] })     → security-specific columns
```

Use this pattern when the prompt asks for role-specific or persona-specific list views.

## Examples

### Basic List with Default View

```
import { List, default_view } from '@servicenow/sdk/core'

List({
    table: 'x_myapp_task',
    view: default_view,
    columns: [
        { element: 'number' },
        { element: 'short_description' },
        { element: 'state' },
        { element: 'priority' },
        { element: 'assigned_to' },
    ],
})
```

### String Columns Shorthand

Prompt: "Create a simple task list showing number, description, assignee, state, and priority — no special formatting needed."

No aggregates or custom positioning requested, so plain strings are sufficient. Column order follows array index.

```
import { List, default_view } from '@servicenow/sdk/core'

List({
    table: 'x_myapp_task',
    view: default_view,
    columns: ['number', 'short_description', 'assigned_to', 'state', 'priority'],
})
```

### List with Custom View and Dot Walking

```
import { Record, List } from '@servicenow/sdk/core'

const detailedView = Record({
    $id: Now.ID['detailed-view'],
    table: 'sys_ui_view',
    data: { name: 'x_myapp_detailed', title: 'Detailed View' },
})

List({
    table: 'x_myapp_task',
    view: detailedView,
    columns: [
        { element: 'number', position: 0 },
        { element: 'short_description', position: 1 },
        { element: 'assigned_to', position: 2 },
        { element: 'assigned_to.department', position: 3 },
        { element: 'state', position: 4 },
        { element: 'priority', position: 5 },
    ],
})
```

### List with Aggregate Columns

Prompt: "Create an expense tracker with total and average amount visible in the list."

```
import { List, default_view } from '@servicenow/sdk/core'

List({
    table: 'x_myapp_expense',
    view: default_view,
    columns: [
        { element: 'category' },
        { element: 'description' },
        { element: 'amount', sum: true, averageValue: true },
        { element: 'date' },
    ],
})
```

### List with Single Aggregate (Sum Only)

Prompt: "Show total effort points in the task list."

```
import { List, default_view } from '@servicenow/sdk/core'

List({
    table: 'x_myapp_task',
    view: default_view,
    columns: [
        { element: 'short_description' },
        { element: 'assigned_to' },
        { element: 'effort_points', sum: true },
        { element: 'priority' },
        { element: 'state' },
    ],
})
```

### Multiple Views for the Same Table

Prompt: "Reception staff should see arrival time and visitor name. Security should see status, badge number, and arrival time."

```
import { Record, List } from '@servicenow/sdk/core'

const receptionView = Record({
    $id: Now.ID['reception-view'],
    table: 'sys_ui_view',
    data: { name: 'x_myapp_reception', title: 'Reception View' },
})

const securityView = Record({
    $id: Now.ID['security-view'],
    table: 'sys_ui_view',
    data: { name: 'x_myapp_security', title: 'Security View' },
})

List({
    table: 'x_myapp_visitor',
    view: receptionView,
    columns: [
        { element: 'full_name' },
        { element: 'expected_arrival_time' },
        { element: 'host_name' },
    ],
})

List({
    table: 'x_myapp_visitor',
    view: securityView,
    columns: [
        { element: 'full_name' },
        { element: 'status' },
        { element: 'badge_number' },
        { element: 'expected_arrival_time' },
    ],
})
```

### Related List with Implicit Reference

When a reference field exists on the child table pointing to the parent table, the relationship is implicit — no `sys_relationship` record is needed.

```
import { List, default_view } from '@servicenow/sdk/core'

List({
    table: 'x_myapp_subtask',
    view: default_view,
    parent: 'x_myapp_task',
    columns: [
        { element: 'short_description' },
        { element: 'assigned_to' },
        { element: 'due_date' },
        { element: 'state' },
    ],
})
```

How it works: `parent: 'x_myapp_task'` tells ServiceNow this list configures the related list columns shown on the `x_myapp_task` form. The implicit relationship is derived from the reference field on `x_myapp_subtask` that points to `x_myapp_task`.

### Related List with Explicit Relationship

When no reference field exists between the tables, you must create a `sys_relationship` record and pass it to the list.

```
import { Record, List, default_view } from '@servicenow/sdk/core'

const matchedPlayersRel = Record({
    $id: Now.ID['matched-players-rel'],
    table: 'sys_relationship',
    data: {
        name: 'Matched Players',
        basic_apply_to: 'x_myapp_sports', // parent form where the related list appears
        basic_query_from: 'x_myapp_players', // child table whose rows are listed
    },
})

List({
    table: 'x_myapp_players',
    view: default_view,
    parent: 'x_myapp_sports',
    relationship: matchedPlayersRel,
    columns: [
        { element: 'first_name', position: 0 },
        { element: 'email', position: 1 },
        { element: 'skill_level', position: 2 },
        { element: 'experience_years', position: 3 },
        { element: 'active', position: 4 },
    ],
})
```

How it works: The `relationship` property binds this list to a custom `sys_relationship` record. This is required when there is no direct reference field between the child and parent tables. Note: `basic_apply_to` is the parent form where the related list appears, and `basic_query_from` is the child table whose rows are listed — the relationship's `name` ('Matched Players') describes the child set, not the parent.

## Avoidance

- Never omit the `view` property — every `List()` requires a view. Use `default_view` if no custom view is needed.

- Never set aggregate flags on non-numeric fields — `sum`, `averageValue`, `minValue`, `maxValue` only render on numeric column types. Setting them on `StringColumn` or `ReferenceColumn` builds without error but the platform won't render them.

- Never skip aggregates when the prompt asks for totals/averages — if the user says "total", "sum", "average", or similar keywords for a numeric field, you MUST set the corresponding aggregate flag.

- Never duplicate column elements — each field should appear only once in the columns array.

- Avoid dot walking beyond one level — the platform only renders one level of dot walking. `'assigned_to.department'` renders correctly; `'assigned_to.department.name'` passes type-checking but won't display.

- Never confuse group-by with aggregates — group-by is a `sys_user_preference` (personal setting), not deployable metadata. Use aggregates (`sum`, `averageValue`) for list-level calculations.

- Avoid adding `$id` to new lists — IDs are derived from `table + view + parent + relationship` automatically. Existing code with `$id` still builds but the value is ignored.

- Prefer Record consts over name strings for views managed by Fluent — pass the exported Record const (`view: myView`) instead of a raw string name. Using the const gives refactoring safety and avoids typos.

## See Also

- `field-styles-guide` — Apply CSS styling (background colors, text alignment, column widths) to list columns based on field values

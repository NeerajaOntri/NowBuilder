Version: 4.14.0

# List

Creates a list layout for a table (`sys_ui_list`) with column definitions (`sys_ui_list_element`).

Each `List()` call generates:

- One `sys_ui_list` record linking the table and view

- One `sys_ui_list_element` record per column entry

## Signature

```
List(config)
```

## Usage

```
import { List, default_view } from '@servicenow/sdk/core'

List({
    table: 'incident',
    view: default_view,
    columns: [
        { element: 'number' },
        { element: 'short_description' },
        { element: 'state' },
    ],
})
```

## Parameters

### config

`List<keyof Tables>`

an object containing the following properties:

Properties:

- 
$id (optional, deprecated): `string | number | ExplicitKey<string>`
Deprecated -- List IDs are now derived from other fields. You can omit `$id`.

- 
table (required): `keyof Tables`
Name of the table for the list

- 
columns (required): `(string | ListElement)[]`
An array of columns to display in the list. Each element can be:

- A string — field name only (position defaults to array index, no aggregates). Supports dot-walked fields (e.g., `'assigned_to.department'`).

- A ListElement object — for position control or aggregate flags:

- element (required): `TableSchemaDotWalk<T>` -- field name to display with dot-walk autocomplete. The platform only renders one level of dot walking (e.g., `'caller_id.name'`). Deeper paths pass type-checking but won't display correctly.

- position (optional): `number` -- column display order. Defaults to the element's index in the `columns` array.

- sum (optional): `boolean` -- show sum aggregate at the bottom of the column (numeric fields only)

- maxValue (optional): `boolean` -- show maximum value aggregate (numeric fields only)

- minValue (optional): `boolean` -- show minimum value aggregate (numeric fields only)

- averageValue (optional): `boolean` -- show average value aggregate (numeric fields only)

Deprecated aliases: `max_value`, `min_value`, and `average_value` are accepted but deprecated. Use `maxValue`, `minValue`, and `averageValue` instead.

Note: Fluent does not validate column types for aggregates. Setting `sum: true` on a non-numeric field builds and deploys without error, but the platform won't render the aggregate footer.

- 
view (required): `Record<'sys_ui_view'> | string`
The UI view (`sys_ui_view`) for this list layout. Use the built-in `default_view` for the default layout, or pass a `Record<'sys_ui_view'>` const for custom views. A plain string (view name) is resolved by name at build time but a Record reference is preferred for type safety.

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit/view access for other developers after the application is installed.

- read: Others can see the script logic but not change it.

- protected: Others cannot change this record.

- Omit to allow other developers to customize this record.

- 
$meta (optional): `object`

- installMethod: `'first install' | 'demo' | 'once'`
Map a record to an output folder that loads only in specific circumstances.
'first install' -> 'unload',
'demo' -> 'unload.demo',
'once' -> 'apply_once'

- 
parent (optional): `TableName`
The parent table name on which the related list appears. Set this when configuring related list column layouts — it identifies which parent form this list is embedded on.

- 
relationship (optional): `Record<'sys_relationship'> | string`
The relationship (`sys_relationship`) to apply to the related list. Required when no implicit reference field exists between the child and parent tables. Pass a `Record<'sys_relationship'>` const or a sys_id string. Unlike `view`, the string form is not resolved by relationship name — use the Record const if you only have the name.

- 
domain (optional): `string`
The domain (`sys_domain`) applied to the list. Defaults to `'global'` when omitted.

## See

- https://docs.servicenow.com/csh?topicname=list-api-now-ts.html&version=latest

- `$override` — set fields not directly supported by this API. See the `override-guide` topic.

## Examples

### Basic List with Default View

A list using the built-in default view with simple columns.

```
/**
 * @title Basic List with Default View
 * @description Create a list layout using the default view with standard columns
 */
import { List, default_view } from '@servicenow/sdk/core'

List({
    table: 'incident',
    view: default_view,
    columns: [
        { element: 'number', position: 0 },
        { element: 'short_description', position: 1 },
        { element: 'priority', position: 2 },
        { element: 'state', position: 3 },
        { element: 'assigned_to', position: 4 },
    ],
})
```

### String Columns Shorthand

When no aggregates or explicit positioning are needed, columns can be plain strings. Position defaults to array index order.

```
/**
 * @title String Columns Shorthand
 * @description Create a list using simple string column names for minimal configuration
 */
import { List, default_view } from '@servicenow/sdk/core'

List({
    table: 'x_myapp_task',
    view: default_view,
    columns: ['number', 'short_description', 'assigned_to', 'state', 'priority'],
})
```

### List with Aggregate Columns

A list with sum and average aggregates on a numeric column. Aggregates only work on numeric column types (`IntegerColumn`, `DecimalColumn`, `FloatColumn`).

```
/**
 * @title List with Aggregate Columns
 * @description Create a list with sum and average aggregates on a numeric column
 */
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

### Custom View with Dot Walking

A list on a custom view that includes dot-walked reference fields. The platform only renders one level of dot walking (e.g., `'assigned_to.department'` renders correctly; `'assigned_to.department.name'` passes type-checking but won't display).

```
/**
 * @title Custom View with Dot Walking
 * @description Create a list with a custom view and dot-walked reference fields
 */
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
    ],
})
```

### Related List with Implicit Reference

Configure columns for a related list where a reference field exists on the child table pointing to the parent table. No `relationship` property is needed — the platform derives the link from the reference field.

```
/**
 * @title Related List with Implicit Reference
 * @description Configure related list columns when a reference field exists between child and parent tables
 */
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

### Related List with Explicit Relationship

When no reference field exists between the tables, create a `sys_relationship` record and pass it to the list via the `relationship` property.

```
/**
 * @title Related List with Explicit Relationship
 * @description Configure related list columns using a custom sys_relationship record
 */
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

For scenario-focused examples showing multiple views, aggregate keyword mapping, and avoidance patterns, see the list-guide topic.

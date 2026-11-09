Version: 4.14.0

# DatabaseView

Creates a Database View (`sys_db_view`) — a read-only virtual table that joins two
or more real tables into a single reportable pseudo-table. A view stores no data
of its own; it is a live join definition consumed by reporting, lists, and other
queries.

## Signature

```
DatabaseView(config)
```

## Usage

In a customer scope (`x_*`), `name` must include the scope prefix; it must be
unique across all database views. Child table and field entries require
explicit `$id`s because the same table or field can appear more than once in a
single view.

```
import { DatabaseView } from '@servicenow/sdk/core'

DatabaseView({
    name: 'x_snc_incident_with_caller',
    label: 'Incidents With Caller',
    tables: [
        {
            $id: Now.ID['incident-table'],
            table: 'incident',
            variablePrefix: 'inc',
            fields: [
                { $id: Now.ID['incident-number'], field: 'number' },
                { $id: Now.ID['incident-short-description'], field: 'short_description' },
                { $id: Now.ID['incident-caller-id'], field: 'caller_id' },
            ],
        },
        {
            $id: Now.ID['caller-table'],
            table: 'sys_user',
            variablePrefix: 'usr',
            whereClause: 'inc_caller_id=usr_sys_id',
            fields: [
                { $id: Now.ID['caller-sys-id'], field: 'sys_id' },
                { $id: Now.ID['caller-name'], field: 'name' },
                { $id: Now.ID['caller-email'], field: 'email' },
            ],
        },
    ],
})
```

## Parameters

### config

`DatabaseViewConfig`

The Database View configuration object.

Properties:

- 
name (required): `string`
Name of the database view. This is the record's identity key: the platform
enforces uniqueness of the normalized name across all database views, so
`DatabaseView` intentionally omits a top-level `$id`. The platform silently
normalizes this value (lowercase, non-alphanumeric characters replaced with
`_`) before storing it, and the Fluent build coalesces on `name` across
rebuilds — supply an already-normalized name to avoid a duplicate view being
created on the next build.

In a customer scope (any scope starting with x_), name must also start with the scope prefix.
In the global scope, `name` must start with the custom `u_` prefix.

- 
label (optional, default: `''`): `string`
Display label shown in admin views.

- 
plural (optional, default: `''`): `string`
Plural display label.

- 
description (optional, default: `''`): `string`
Free-text description of the view's purpose.

- 
tables (required): `DatabaseViewTable[]`
The tables joined into this view, in join order. May be empty — ServiceNow
allows database views with no joined tables.

`DatabaseViewTable` properties:

- 
$id (required): `Now.ID['...']` - Explicit ID for the joined-table entry.
Required because no natural coalesce key exists.

- 
table (required): `TableName`
The table to join into the view. In a scoped app, prefer a table in the same
scope, or a scoped table that extends an out-of-box table, when targeting
platform data.

- 
variablePrefix (required): `string`
Disambiguates this table's fields inside `whereClause` (e.g. `usr` for
`sys_user`). The platform rejects prefixes containing an underscore or
exceeding 30 characters. Must be unique across every table in the same view —
a collision produces a broken or ambiguous join and is not caught by the
platform itself.

- 
leftJoin (optional, default: `false`): `boolean`
`false` produces an INNER JOIN — only rows with matches in every joined table
appear. `true` produces a LEFT OUTER JOIN — all rows from prior tables appear,
with empty values for unmatched columns from this table.

- 
order (optional, default: `100`): `number`
Join order relative to other tables in this view. Affects query performance
on large tables — put the most selective/smallest table first.

- 
whereClause (optional, default: `''`): `string`
A raw join/filter predicate using `variablePrefix`-qualified field names, e.g.
`usr_sys_id=role_user`. This is not an encoded query string.

- 
active (optional, default: `true`): `boolean`
Whether this joined table is active.

- 
fields (optional, default: `[]`): `Array<DatabaseViewField>`
Columns from `table` to expose in the view. Each entry is an object with a
required `$id` and a `field` name. The `$id` is the unique identifier for the
`sys_db_view_table_field` record, matching the platform's `sys_id`. Provide a
unique `$id` for every field; use distinct `$id`s when the same field must
appear more than once under the same view table. Many real views join a table
purely for filtering (via `whereClause`) without exposing any of its columns —
omit or leave empty in that case.

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit access for other developers after the application is installed.

- `'read'`: Others can view this record's configuration but cannot change it.

- `'protected'`: Others cannot change this record.

- Omit to allow other developers to customize this record.

## Identity Model

`DatabaseView` does not expose a top-level `$id`. The platform enforces that the
normalized `name` is unique across all `sys_db_view` records, so `name` is the stable identifier and the
Fluent build coalesces on it across rebuilds.

Child records — `DatabaseViewTable` and `DatabaseViewField` — still require
`$id` because the same table can be joined multiple times in the same view
under different `variablePrefix` values, which makes `(view, table)` an
unreliable coalesce key.

### `DatabaseViewField`

Field entry in `fields`.

- 
$id (required): `Now.ID['...']` - Explicit ID for the table field.

- 
field (required): `string` - Column name from the joined `table` to expose in the view. IDE autocomplete is available for fields of known tables.

## Validation Rules

- 
Name normalization: `name` must already be normalized (lowercase,
non-alphanumeric characters replaced with `_`) — the plugin emits a build error
if it isn't, since a mismatch would cause the next build to create a duplicate
view instead of updating this one.

- 
Scope prefix: in a customer scope (any scope starting with `x_`), `name`
must start with `${scope}_` — a build error if missing. In the global scope,
`name` must start with the custom `u_` prefix instead — also a build error if
missing.

- 
Variable prefix format: `variablePrefix` must not contain an underscore and
must be 30 characters or fewer.

- 
Unique variable prefix per view: two `tables[]` entries in the same view
must not share the same `variablePrefix` — this produces an ambiguous join and
is rejected with a build error.

## Examples

### Basic database view

The simplest valid view — a single joined table with no field selection. The
`name` must include the scope prefix and be unique; the joined table needs a
unique `$id`.

```
import { DatabaseView } from '@servicenow/sdk/core'

export const example = DatabaseView({
    name: 'x_snc_database_view_basic',
    tables: [{
        $id: Now.ID['database-view-basic-table'],
        table: 'incident',
        variablePrefix: 'inc',
    }],
})
```

### Database view with field selection

Selects specific columns from the joined table to expose in the view. Each
joined table and each field within a table needs a unique `$id`.

```
import { DatabaseView } from '@servicenow/sdk/core'

export const example = DatabaseView({
    name: 'x_snc_database_view_with_fields',
    label: 'Incidents With Selected Fields',
    tables: [
        {
            $id: Now.ID['database-view-with-fields-table'],
            table: 'incident',
            variablePrefix: 'inc',
            fields: [
                { $id: Now.ID['with-fields-number'], field: 'number' },
                { $id: Now.ID['with-fields-short-description'], field: 'short_description' },
                { $id: Now.ID['with-fields-priority'], field: 'priority' },
            ],
        },
    ],
})
```

### Database view with a left join

Joins a second table with leftJoin so rows with no match still appear.

```
import { DatabaseView } from '@servicenow/sdk/core'

export const example = DatabaseView({
    name: 'x_snc_database_view_left_join',
    description: 'Incidents joined to assignment group, including incidents with no group',
    tables: [
        { $id: Now.ID['database-view-left-join-incident-table'], table: 'incident', variablePrefix: 'inc', order: 100 },
        {
            $id: Now.ID['database-view-left-join-group-table'],
            table: 'sys_user_group',
            variablePrefix: 'grp',
            order: 200,
            leftJoin: true,
            whereClause: 'inc_assignment_group=grp_sys_id',
            fields: [
                { $id: Now.ID['left-join-group-sys-id'], field: 'sys_id' },
                { $id: Now.ID['left-join-group-name'], field: 'name' }
            ],
        },
    ],
})
```

### Advanced database view

Combines multiple joined tables, field selection, a left join, and a custom filter clause.

```
import { DatabaseView } from '@servicenow/sdk/core'

export const example = DatabaseView({
    name: 'x_snc_database_view_advanced',
    label: 'Incidents With Caller And Group',
    plural: 'Incidents With Caller And Group',
    description: 'Joins incidents to caller and assignment group for reporting',
    tables: [
        {
            $id: Now.ID['database-view-advanced-incident-table'],
            table: 'incident',
            variablePrefix: 'inc',
            order: 100,
            fields: [
                { $id: Now.ID['advanced-incident-number'], field: 'number' },
                { $id: Now.ID['advanced-incident-short-description'], field: 'short_description' },
                { $id: Now.ID['advanced-incident-caller-id'], field: 'caller_id' },
                { $id: Now.ID['advanced-incident-assignment-group'], field: 'assignment_group' },
            ],
        },
        {
            $id: Now.ID['database-view-advanced-caller-table'],
            table: 'sys_user',
            variablePrefix: 'usr',
            order: 200,
            whereClause: 'inc_caller_id=usr_sys_id',
            fields: [
                { $id: Now.ID['advanced-caller-sys-id'], field: 'sys_id' },
                { $id: Now.ID['advanced-caller-name'], field: 'name' },
                { $id: Now.ID['advanced-caller-email'], field: 'email' },
            ],
        },
        {
            $id: Now.ID['database-view-advanced-group-table'],
            table: 'sys_user_group',
            variablePrefix: 'grp',
            order: 300,
            leftJoin: true,
            whereClause: 'inc_assignment_group=grp_sys_id',
            fields: [
                { $id: Now.ID['advanced-group-sys-id'], field: 'sys_id' },
                { $id: Now.ID['advanced-group-name'], field: 'name' },
            ],
        },
    ],
})
```

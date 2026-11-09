Version: 4.14.0

# Table

Defines a database table (`sys_db_object`) in a scoped application with typed column schemas, auto-numbering, access controls, and table inheritance.

## Signature

```
Table(table)
```

## Parameters

### table

`T & Table<S, E>`

Note: The SDK no longer derives defaults for the access properties -- `actions`,
`allowClientScripts`, `allowConfiguration`, `allowNewFields`, `allowUiActions`, and
`allowWebServiceAccess`. Each one is written to the table's metadata only if you set it in Fluent or via `basePolicy`.

Properties:

- 
name (required unless `augments` is set): `string`
Name of the table. Must be lowercase and include the application scope prefix.

- 
schema (required): `Record<string, Column>`
Array of column references that define the table's schema

- 
accessibleFrom (optional): `'public' | 'package_private'`
Controls whether other application scopes can access the table. Default is `public`. Use `package_private` only when you need to restrict cross-scope read access. This will prevent the table from being selectable in some platform features such as Business Rules.

- 
actions (optional): `TableActionAccess`
Access options for the table. Only enable `create`, `update`, or `delete` if cross-scope write access is explicitly required. `TableActionAccess` has:

- read (optional): `boolean` — Allows records in the table to be read.

- update (optional): `boolean` — Allows records in the table to be updated.

- delete (optional): `boolean` — Allows records in the table to be deleted.

- create (optional): `boolean` — Allows records to be created in the table.

- 
allowClientScripts (optional): `boolean`
Indicates whether to allow design time configuration of client scripts on the table from other application scopes.

- 
allowConfiguration (optional): `boolean`
Indicates whether to allow design time configuration of the table itself from other application scopes. Corresponds to the "Allow configuration" field on the Application Access form. Left unset when omitted, so the platform inherits the value from the table's parent.

- 
allowNewFields (optional): `boolean`
Indicates whether to allow design time configuration of new fields on the table from other application scope.

- 
allowUiActions (optional): `boolean`
Indicates whether to allow design time configuration of UI Actions on the table from other application scopes.

- 
allowWebServiceAccess (optional): `boolean`
Indicates whether web services can make calls to the table. Must be set to `true` for the table to be accessible via the Table API (`/api/now/table`) or other REST integrations -- otherwise requests return 403.

- 
attributes (optional): `Record<string, string | number | boolean>`
Pairs of any supported dictionary attributes (sys_schema_attribute).

- 
audit (optional): `boolean`
Indicates whether to track the creation, update, and deletion of all records in the table.

- 
augments (optional): `string`
The name of an existing table to augment (e.g. `'incident'`) to augment by adding columns. When set, only `schema` and `index` are configurable, all other table-level properties (`name`, `extends`, `label`, `display`, `audit`, etc.) are not permitted. Use this to extend platform or cross-scope tables.

- 
autoNumber (optional): `object`
Auto-increment configuration for the tables with a 'number' column. Do not use if table does not have (or inherit) a 'number' column.

- 
number: `number`

- 
numberOfDigits: `number`

- 
prefix: `string`

- 
basePolicy (optional): `'public' | 'private'`
Default for access flags not set explicitly: `'public'` = true, `'private'` = false.

Note: `allowWebServiceAccess` defaults to true under either policy, and `allowConfiguration` is not affected.

- 
callerAccess (optional): `'none' | 'tracking' | 'restricted'`
Access level for cross-scope requests.

- 
display (optional): `string`
Default display column. Use a column name from the schema.

- 
extends (optional): `keyof Tables`
The name of any other table on which this table is based.

- 
extensible (optional): `boolean`
Indicates whether other tables can extend this table.

- 
index (optional): `object[]`
A list of column references to generate indexes in the metadata XML of the table. Each entry has:

- name (optional): `string` — Name of the index.

- unique (required): `boolean` — Whether the index enforces uniqueness.

- element (required): `string | string[]` — Column name(s) that make up the index.

- 
label (optional): `string | Documentation[]`
A unique label for the table on list and form views.

- 
licensingConfig (optional): `LicensingConfig`
Configuration for table licensing.

- 
liveFeed (optional): `boolean`
Indicates if live feeds are available for records in the table.

- 
readOnly (optional): `boolean`
Indicates whether users can edit fields in the table.

- 
scriptableTable (optional): `boolean`
Indicates whether the table is a remote table that uses data retrieved from an external source.

- 
sizeClass (optional): `number`
Size classification of the table. Used to indicate the expected size category of the table.

- 
dbObjectId (optional): `boolean`
Writes the table's `sys_id` to the `db_object_id` attribute of the generated bootstrap dictionary XML, pinning the `sys_db_object` record the platform creates for this table to that `sys_id` instead of letting it generate one. Set this when the table's `sys_id` must stay stable across installs, for example when other metadata references the `sys_db_object` record directly. Defaults to `false`. Not permitted alongside `augments`.

- 
createAccessControls (optional): `boolean`
Indicates whether to create access controls when the table is created.

- 
userRole (optional): `string | Role | Record<'sys_user_role'>`
Role used to wire the table's auto-generated access controls. Accepts a role name (created on-demand via the platform's `dynamic_creation` script if it does not yet exist) or a reference to an existing `sys_user_role` record. When omitted, the platform falls back to the parent application's `user_role`. Only takes effect when `createAccessControls` is `true`.

- 
textIndex (optional): `boolean`
Indicates whether search engines index the text in a table.

- 
createRoles (optional): `(string | Role)[]`
Roles that can create records in this table.

- 
readRoles (optional): `(string | Role)[]`
Roles that can read records in this table.

- 
writeRoles (optional): `(string | Role)[]`
Roles that can update records in this table.

- 
deleteRoles (optional): `(string | Role)[]`
Roles that can delete records from this table.

## See

- https://docs.servicenow.com/csh?topicname=table-api-now-ts.html&version=latest

## Examples

### To-Do Table Example

```
import { Table, StringColumn, DateColumn, IntegerColumn } from '@servicenow/sdk/core'

// Variable name MUST match the name property
export const x_snc_example_to_do = Table({
  name: 'x_snc_example_to_do',
  label: 'My To Do Table',
  display: 'title', // Use the 'title' column as the display column
  schema: {
    title: StringColumn({ mandatory: true }),
    deadline: DateColumn({ label: 'Deadline' }),
    status: StringColumn({
      label: 'Status',
      choices: {
        ready: 'Ready',
        in_progress: 'In Progress',
        completed: 'Completed',
      },
    }),
  },
})
```

### Extending Task Example

```
import { Table, StringColumn, DateColumn, IntegerColumn } from '@servicenow/sdk/core'

// Variable name MUST match the name property
export const x_snc_example_task = Table({
  name: 'x_snc_example_color_task',
  label: 'My Color Task',
  extends: 'task', // Inherit columns from the 'task' table
  schema: {
    color: StringColumn({
      label: 'Color',
      choices: {
        red: 'Red',
        blue: 'Blue',
        green: 'Green',
      },
    }),
  },

  // Configure auto-incrementation for the inherited 'number' column from the parent 'task' table (e.g. CLR0000001, CLR0000002, etc)
  autoNumber: {
    prefix: 'CLR',
    number: 2000,
    numberOfDigits: 7,
  },
})
```

### Cross-Scope Access Example

A table other scoped apps can read, create, and update.

```
import { Table, StringColumn } from '@servicenow/sdk/core'

export const x_snc_example_case = Table({
  name: 'x_snc_example_case',
  label: 'Example Case',
  extends: 'sn_customerservice_case',
  accessibleFrom: 'public',
  callerAccess: 'tracking',
  actions: { read: true, create: true, update: true },
  schema: {
    reason: StringColumn({ label: 'Reason' }),
  },
})
```

### Override Inherited Columns

```
/**
 * @title Override Inherited Columns
 * @description Examples of overriding inherited column properties in child tables
 */
import { Table, OverrideColumn, StringColumn, ReferenceColumn } from '@servicenow/sdk/core'

// Example 2: Override multiple properties
export const x_override_multiple = Table({
    name: 'x_override_multiple',
    extends: 'task',
    schema: {
        priority: OverrideColumn({
            baseTable: 'task',
            mandatory: true,
            default: '1',
        }),
        state: OverrideColumn({
            baseTable: 'task',
            mandatory: true,
            readOnlyOption: 'display_read_only',
        }),
        description: OverrideColumn({
            baseTable: 'task',
            display: false,
        }),
    },
})
```

For guidance on table creation, column types, relationships, and common pitfalls, see the `table-guide` topic.

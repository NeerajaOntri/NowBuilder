Version: 4.14.0

# DataLookup

Creates a Data Lookup definition (`dl_definition`) that automatically copies field
values from a matching record (the matcher) to a target record (the source)
when configurable match conditions are met.

## Signature

```
DataLookup(config)
```

## Usage

```
import { DataLookup } from '@servicenow/sdk/core'

DataLookup({
    $id: Now.ID['priority-impact-lookup'],
    name: 'Priority Impact Lookup',
    sourceTable: 'task',
    matcherTable: 'dl_u_priority',
    matchRules: [
        { $id: Now.ID['priority-impact-match-priority'], sourceField: 'priority', matcherField: 'priority', exactMatch: true },
    ],
    setRules: [
        { $id: Now.ID['priority-impact-set-impact'], targetField: 'impact', matcherField: 'impact', alwaysReplace: false },
    ],
})
```

## Parameters

### config

`DataLookupConfig<S extends TableName, M extends TableName>`

The Data Lookup configuration object.

Properties:

- 
$id (required): `NowId`
Stable identifier for this lookup definition. Used to track the record across
builds and prevent duplicates.

- 
name (required): `string`
Display name of the lookup definition. Must be 40 characters or fewer.

- 
sourceTable (required): `S`
The table whose records trigger the lookup and receive the copied field values. In
a scoped app (non-global, non-`sn_`/`now_`), must be in the same scope as the
data lookup definition (prefixed `<scope>_`). To target an OOB table such as
`incident` or `problem`, use a global-scope app or a scoped table that extends
the OOB table. Must be in the same scope as the data lookup definition —
a build error is emitted if a cross-scope matcher table is detected.

- 
matcherTable (required): `M`
The custom matcher table whose rows are searched to find a matching record. The
table must extend `dl_matcher` and must be created separately using `Table()`
before the Data Lookup Definition is deployed. Must be in the same scope as
the data lookup definition — a build error is emitted if a cross-scope matcher
table is detected. `x_` (customer/partner apps), `sn_`, and `now_`
(ServiceNow-built apps) are all treated as scoped prefixes.

- 
active (optional, default: `true`): `boolean`
Whether this lookup definition is active and evaluated during record operations.

- 
runOnInsert (optional, default: `true`): `boolean`
Whether the lookup runs when a source record is inserted.

- 
runOnUpdate (optional, default: `false`): `boolean`
Whether the lookup runs when a source record is updated. Defaults to `false` —
a common source of confusion when lookups appear not to fire on updates.

- 
runOnFormChange (optional, default: `true`): `boolean`
Whether the lookup runs on form change (client-side evaluation).

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit access for other developers after the application is installed.

- `'read'`: Others can view this record's configuration but cannot change it.

- `'protected'`: Others cannot change this record.

- Omit to allow other developers to customize this record.

- 
matchRules (optional): `DataLookupMatchRule<S, M>[]`
Rules that define when the lookup applies. Each rule compares a field on the
source record against a field on the matcher record. All match rules must pass
for the lookup to trigger. When omitted, all records match.

`DataLookupMatchRule` properties:

- 
$id (required): `NowId`
Stable identifier for this match rule. Each rule is stored as its own
`dl_definition_rel_match` record — provide a unique `Now.ID['...']` so the
same sys_id is preserved across builds and developer machines.

- 
sourceField (required): `keyof FullSchema<S> | SystemColumns | (string & {})`
The field name on the source table to compare.

- 
matcherField (required): `keyof FullSchema<M> | SystemColumns | (string & {})`
The field name on the matcher table to compare against.

- 
exactMatch (optional, default: `false`): `boolean`
When `true`, requires an exact value match. When `false`, allows partial or
range matching depending on field type.

- 
setRules (optional): `DataLookupSetRule<S, M>[]`
Rules that define which fields are copied from the matcher record to the source
record when the lookup applies. When omitted, no fields are copied.

`DataLookupSetRule` properties:

- 
$id (required): `NowId`
Stable identifier for this set rule. Each rule is stored as its own
`dl_definition_rel_set` record — provide a unique `Now.ID['...']` so the
same sys_id is preserved across builds and developer machines.

- 
targetField (required): `keyof FullSchema<S> | SystemColumns | (string & {})`
The field name on the source table to write the copied value into.

- 
matcherField (required): `keyof FullSchema<M> | SystemColumns | (string & {})`
The field name on the matcher table to read the value from.

- 
alwaysReplace (optional, default: `false`): `boolean`
When `true`, the field value is always overwritten even if already set.
When `false`, the field is only set if it is currently empty.

## Validation Rules

- 
Name length: The `name` property must be 40 characters or fewer. Names longer
than 40 characters cause a build error.

- 
Source and matcher table scope: In a scoped app (non-global, non-`sn_`/`now_`),
both `sourceTable` and `matcherTable` must be in the same scope as the data lookup
definition. The build plugin emits an error diagnostic for either table that
violates this constraint. To use OOB tables such as `incident` or `problem`, use a
global-scope app or a scoped extension table.

- 
Matcher Table Seed Data — active Field Required: Ensure that the `active` field is set to `true` for each record in the matcher table. This is because the Data Lookup engine queries the matcher table with an implicit `active=true` filter, and records where `active` is `null` or `false` will never match.

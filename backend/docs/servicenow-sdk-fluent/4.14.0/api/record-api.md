Version: 4.14.0

# Record

Create a record in any table. This is a low-level function typically used as
a fallback when the specific record type or metadata does not have its own
dedicated API. When possible, prefer using other, dedicated APIs to generate
metadata as those APIs will often have better type safety and will be easier
to use.

## Signature

```
Record(config)
```

## Parameters

### config

Type: `object`

Properties:

- 
$id (required): `string | number | ExplicitKey<string>`
`Now.ID` should be used to define the value. See the `keys-file` topic for more details.

- 
data (required): `{ [fieldName: string]: string | number | boolean | string[] | Record }`
Fields and their values in the table, keyed by the field name as it appears on the table specified by the `table` property.

- 
table (required): `string`
The name of the table to which the record belongs.

- 
$meta (optional): `object`

- installMethod: `'first install' | 'demo' | 'once'`
Map a record to an output folder that loads only in specific circumstances. Always use "demo" for sample/demo data.
'first install' - > 'unload',
'demo' -> 'unload.demo'

## Notes

The `Record` API does not populate fields with their platform default values
like the ServiceNow instance does when using Glide APIs or the UI.
Only fields explicitly listed under the `data` property are set on the
record — any field omitted from `data` will be left unset rather than populated
with the platform default.
If you need default values, you must specify them on the `data` object.

## See

- https://docs.servicenow.com/csh?topicname=record-api-now-ts.html&version=latest

## Examples

### Basic Example Record

Create a simple record on an example table

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['example-1'],
    table: 'sys_example_table',
    data: {
        name: 'John',
        age: 24,
        internal: true,
    },
})
```

### Incident Sample Record

Create a sample/demo record on the incident table

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['incident-1'],
    $meta: { installMethod: 'demo' },
    table: 'incident',
    data: {
        number: 'INC0010001',
        active: true,
        description: 'This is a sample incident description',
        priority: 3,
    },
})
```

### Cross-Record References Within the Same App

When a record references another record defined in the same app, pass the exported record variable directly in the `data` field.

Warning: Do not use `Now.ID["key"]` inside `data`. `Now.ID` only resolves to a hashed sys_id in the `$id` property. Inside `data`, the literal key string is written to the database, causing reference fields to appear blank.

For same-app records, pass the record variable directly. For platform records not in your app, use a sys_id string.

```
import { Record } from '@servicenow/sdk/core'

// Parent record
export const vendorAcme = Record({
    $id: Now.ID['vendor-acme'],
    table: 'x_snc_vendor_man_vendor',
    data: {
        name: 'Acme Corp',
        status: 'active',
    },
})

// Child record — references the parent record variable
export const contractAcme = Record({
    $id: Now.ID['contract-acme-1'],
    table: 'x_snc_vendor_man_vendor_contract',
    data: {
        vendor: vendorAcme, // CORRECT: resolves to hashed sys_id
        // vendor: Now.ID["vendor-acme"],      // WRONG: writes literal "vendor-acme" to DB
        contract_name: 'Annual Support Agreement',
        start_date: '2025-01-01',
        status: 'active',
    },
})
```

## Resolving View and Role References

For certain reference fields, `Record()` can resolve a `data` value to the
referenced record's coalesce key (e.g. a view or role's `name`) instead of
leaving it as a raw sys_id. This isn't about sys_id references being wrong
in general — most reference fields work fine as sys_ids. It matters for
tables like views (`sys_ui_view`) and roles (`sys_user_role`), where the
same logical record can have a different sys_id from instance to instance,
and where names are also more readable to work with (e.g. `view: 'my_view_name'` instead of a sys_id).

Resolving a reference field this way requires the SDK to know the schema of
the table you're writing to — that's what reveals which fields are
references and what table they point to. Schema information comes from
either a dedicated Fluent API (which already knows its own reference
fields) or a `Table()` definition the SDK has locally, whether bundled with
the SDK or downloaded into your project.

Without that schema information, the reference field is left as whatever
sys_id was in the source XML. For a view or role reference, that sys_id may
not point to the right record (or to anything at all) on another instance,
so the reference can silently break after install.

Fix: download the table's schema before authoring or converting records
against it:

```
now-sdk dependencies --add tables <table_name> --scope <scope>
```

This fetches the table into your project's generated types
(`@types/servicenow/fluent/`), teaching the compiler about its columns —
including which ones are references. That's a prerequisite for `Record()` to
resolve a reference field by name instead of a sys_id.

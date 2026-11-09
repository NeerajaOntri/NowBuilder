Version: 4.14.0

# Now.ref

`Now.ref()` creates a reference to a record in another table. Use it when a field needs to point to a record that isn't defined in the current file — for example, referencing a role, a flow, or any record identified by its sys_id or coalesce keys.

Note: `Now` is a global available in every `.now.ts` file — it does not need to be imported. Do not add `Now` to any `import { ... } from '@servicenow/sdk/core'` line; call `Now.ref()` directly.

## Syntax

```
// By coalesce keys — identifies the record by unique field values
Now.ref(table: string, keys: { [key: string]: string }): any

// By sys_id or Now.ID key — identifies the record by GUID
Now.ref(table: string, guid: string, keys?: { [key: string]: string }): any
```

## Examples

### Reference by coalesce keys

When you know the unique field values that identify a record:

```
import { Acl } from '@servicenow/sdk/core'

Acl({
    $id: Now.ID['incident-read-acl'],
    type: 'record',
    operation: 'read',
    table: 'incident',
    roles: [
        Now.ref('sys_user_role', { name: 'admin' }),
        Now.ref('sys_user_role', { name: 'itil' }),
    ],
})
```

### Reference by sys_id

When you have the record's sys_id:

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['my-catalog-item'],
    table: 'sc_cat_item',
    data: {
        name: 'Request Laptop',
        flow_designer_flow: Now.ref('sys_hub_flow', 'a1b2c3d4e5f67890abcdef1234567890'),
    },
})
```

### Reference by Now.ID key

If the target record is also defined in your Fluent project, you can use its `Now.ID` key as the guid:

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['my-catalog-item'],
    table: 'sc_cat_item',
    data: {
        name: 'Request Laptop',
        flow_designer_flow: Now.ref('sys_hub_flow', 'test_flow_for_service_catalog'),
    },
})
```

### Reference with fallback coalesce keys

Provide both a GUID and coalesce keys — the keys act as a fallback identifier:

```
Now.ref('sys_hub_flow', 'a1b2c3d4...', { name: 'My Flow' })
```

## When to use Now.ref vs direct references

| Scenario | Use |
| Record defined in same project | Return value of the API function (e.g., `const role = Role({...})` ) |
| Record on the instance, known sys_id | raw sys_id value or `Now.ref('table', 'sys_id')` |
| Record on the instance, known unique fields | `Now.ref('table', { field: 'value' })` |
| Record in same project, different file | Export from other file, and import as variable to use directly |

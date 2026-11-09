Version: 4.14.0

# Now.del

Marks a record for deletion. When the application is deployed, records marked with `Now.del()` will be removed from the target instance.

## Signatures

```
// Delete by coalesce keys
Now.del(table, keys)

// Delete by sys_id
Now.del(table, sysId)
```

## Parameters

### table

`string` (required)

The target table name (e.g., `'sys_user_role'`, `'sys_hub_flow'`).

### keys

`{ [key: string]: string }` (for coalesce keys signature)

An object of coalesce key-value pairs used to uniquely identify the record to delete.

### sysId

`string` (for sys_id signature)

A 32-character sys_id identifying the record to delete.

## Examples

### Delete by coalesce keys

Use this when you know the identifying fields of the record:

```
// Delete a role by its name
Now.del('sys_user_role', { name: 'x_myapp.obsolete_role' })

// Delete a property by its name
Now.del('sys_properties', { name: 'x_myapp.old_setting' })
```

### Delete by sys_id

Use this to delete OOB (out-of-box) records when you know the sys_id:

```
Now.del('sys_hub_flow', 'a1b2c3d4e5f6789012345678901234ab')
```

Note: For records created in Fluent, prefer removing the code instead of using `Now.del()`. Deletes are tracked automatically when you remove a record definition.

## Notes

- `Now.del()` is a top-level statement only; it cannot be used inline within other record definitions

- Deleted records are written to the `author_elective_update` directory with `action="DELETE"`

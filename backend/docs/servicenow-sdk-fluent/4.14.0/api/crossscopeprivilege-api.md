Version: 4.14.0

# CrossScopePrivilege

Creates a Cross Scope Privilege — a declaration that your application needs runtime access to resources owned by a different application scope (`sys_scope_privilege`). Required when your scripts read/write tables, call script includes, or use scriptable objects from other scopes.

## Signature

```
CrossScopePrivilege(config)
```

## Parameters

### config

`CrossScopePrivilege`

an object containing the following properties:

Properties:

- 
$id (required): `string | number | ExplicitKey<string>`

- 
operation (required): `'read' | 'delete' | 'create' | 'execute' | 'write'`
The operation being requested on the target.

- 
status (required): `'requested' | 'allowed' | 'denied'`
The authorization status of the privilege request. Can be 'requested', 'allowed', or 'denied'.

- 
$meta (optional): `object`

- installMethod: `'first install' | 'demo' | 'once'`
Map a record to an output folder that loads only in specific circumstances.
'first install' - > 'unload',
'demo' -> 'unload.demo'

- 
targetName (required): `string`
The name of the table, script include, or script object being requested.

- 
targetScope (required): `string`
The application scope whose resources are being requested.

- 
targetType (required): `'sys_db_object' | 'sys_script_include' | 'scriptable'`
The type of target being requested

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit/view access for other developers after the application is installed.

- read: Others can see the privilege logic but not change it.

- protected: Others cannot change this privilege.

- Omit to allow other developers to customize this privilege.

Constraint: `operation: 'execute'` requires `targetType: 'sys_script_include' | 'scriptable'`. CRUD operations (`create`, `read`, `write`, `delete`) require `targetType: 'sys_db_object'`.

## See

- https://docs.servicenow.com/csh?topicname=c_CrossScopePrivilegeRecord.html&version=latest

## Examples

### Execute Script Include Privilege

Allow executing a script include from another scope

```
/**
 * @title Execute Script Include Privilege
 * @description Allow executing a script include from another scope
 */
import { CrossScopePrivilege } from '@servicenow/sdk/core'

CrossScopePrivilege({
    $id: Now.ID['6d109a82ff54b210fd87ffffffffff8e'],
    operation: 'execute',
    status: 'allowed',
    targetName: 'GlideQuery',
    targetScope: 'global',
    targetType: 'sys_script_include',
})
```

### Read Table Privilege

Allow reading records from a table in another scope

```
/**
 * @title Read Table Privilege
 * @description Allow reading records from a table in another scope
 */
import { CrossScopePrivilege } from '@servicenow/sdk/core'
CrossScopePrivilege({
    $id: Now.ID['read_privilege'],
    operation: 'read',
    status: 'allowed',
    targetName: 'cmdb_ci_computer',
    targetScope: 'global',
    targetType: 'sys_db_object',
})
```

### Write Table Privilege

Allow writing records to a table in another scope

```
/**
 * @title Write Table Privilege
 * @description Allow writing records to a table in another scope
 */
import { CrossScopePrivilege } from '@servicenow/sdk/core'
CrossScopePrivilege({
    $id: Now.ID['write_privilege'],
    operation: 'write',
    status: 'allowed',
    targetName: 'incident',
    targetScope: 'global',
    targetType: 'sys_db_object',
})
```

For guidance on configuring cross-scope access, see the `cross-scope-privilege-guide` topic.

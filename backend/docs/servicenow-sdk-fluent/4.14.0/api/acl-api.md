Version: 4.14.0

# Acl

Creates an Access Control List (ACL) record that secures parts of an application (`sys_security_acl`).

## Signature

```
Acl(config)
```

## Usage

```
import { Acl } from '@servicenow/sdk/core'

Acl({
    $id: Now.ID['incident_read'],
    type: 'record',
    table: 'incident',
    operation: 'read',
})
```

## Parameters

### config

`Acl<keyof Tables, 'pd_action' | 'record' | 'client_callable_flow_object' | 'client_callable_script_include' | 'processor' | 'ui_page' | 'ux_data_broker' | 'graphql' | 'rest_endpoint' | 'ux_page' | 'ux_route' | 'aiux_page' | 'aiux_widget' | 'aiux_experience' | string>`

Configuration for the ACL record

Properties:

- 
$id (required): `string | number | ExplicitKey<string>`

- 
operation (required): `'read' | 'delete' | 'create' | 'execute' | 'write' | 'conditional_table_query_range' | 'data_fabric' | 'query_match' | 'query_range' | 'edit_task_relations' | 'edit_ci_relations' | 'save_as_template' | 'add_to_list' | 'report_on' | 'list_edit' | 'report_view' | 'personalize_choices'`
The operation this ACL rule secures

- 
type (required): `'pd_action' | 'record' | 'client_callable_flow_object' | 'client_callable_script_include' | 'processor' | 'ui_page' | 'ux_data_broker' | 'graphql' | 'rest_endpoint' | 'ux_page' | 'ux_route' | 'aiux_page' | 'aiux_widget' | 'aiux_experience' | string`
Type of the resource being secured

- 
$meta (optional): `object`

- installMethod: `'first install' | 'demo' | 'once'`
Map a record to an output folder that loads only in specific circumstances.
'first install' - > 'unload',
'demo' -> 'unload.demo'

- 
active (optional): `boolean`
Whether the ACL rule is enabled or not

- 
adminOverrides (optional): `boolean`
Whether users with admin role automatically pass the permissions check for this ACL rule

- 
condition (optional): `string`
Filter query specifying fields and values that must be true for access

- 
decisionType (optional): `'allow' | 'deny'`
Whether the ACL should allow or deny access

- 
description (optional): `string`
Description of the object or permissions this ACL rule secures

- 
localOrExisting (optional): `'Local' | 'Existing'`
Type of security attribute: 'Local' for condition-based or 'Existing' to reference an attribute

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit/view access for other developers after the application is installed.

- read: Others can see the ACL logic but not change it.

- protected: Others cannot change this ACL.

- Omit to allow other developers to customize this ACL.

- 
roles (optional): `(string | Role | { role: string | Role, protectionPolicy?: '' | 'read' | 'protected' })[]`
Array of roles that have access to the object. Each role can be a sys_id, a `Role` reference, or an
object with a `role` and a per-role `protectionPolicy` override. The platform normally propagates the
ACL's own `protectionPolicy` to each of its roles, so the object form is only needed when a specific
role's protection should diverge from the ACL as a whole:

```
Acl({
    $id: Now.ID['incident_read'],
    type: 'record',
    table: 'incident',
    operation: 'read',
    protectionPolicy: 'protected',
    roles: [
        'itil', // inherits the ACL's own protectionPolicy ('protected')
        { role: 'admin', protectionPolicy: 'read' }, // overridden to 'read'
    ],
})
```

Empty string is valid as a `none` value, and this needs to be written in code to avoid inheriting parent behavior

- 
script (optional): `string | (current: any, dependencies: any[]) => boolean`
Script that defines the permissions required to access the object

- 
securityAttribute (optional): `'user_is_authenticated' | 'has_admin_role' | string | Record<'sys_security_attribute'>`
Pre-defined conditions or security attributes to use for access control

Variant Properties:

When `Type extends keyof typeof AclRecordTypes`:

- 
table (required): `T`
The table this ACL rule applies to

- 
field (optional): `keyof FullSchema<T> | SystemColumns | '*'`
Optional field within the table to secure, or '*' for all fields

- 
appliesTo (optional): `string`
Additional filter to specify which records this ACL applies to

When `Type extends Exclude<keyof typeof AclNamedTypes, 'ux_route' | 'ux_page'>`:

- name (required): `string`
Name of the resource being secured

When `Type extends keyof typeof AclDataBrokerType`:

- 
dataBroker (optional): `Record<'sys_ux_data_broker'> | string`
Reference to the UX data broker this ACL applies to

- 
table (optional): `T`
The table this ACL rule applies to

- 
field (optional): `keyof FullSchema<T> | SystemColumns | '*'`
Optional field within the table to secure, or '*' for all fields

Otherwise:

- 
name (optional): `string`
Name of the resource being secured

- 
table (optional): `T`
The table this ACL rule applies to

- 
field (optional): `keyof FullSchema<T> | SystemColumns | '*'`
Optional field within the table to secure, or '*' for all fields

- 
appliesTo (optional): `string`
Additional filter to specify which records this ACL applies to

## ACL Object Types

| Type | Secures |
| `record` | Table rows and fields (default) |
| `rest_endpoint` | REST API endpoints |
| `ui_page` | UI Pages |
| `processor` | Processors |
| `graphql` | GraphQL endpoints |
| `pd_action` | Predictive Decision actions |
| `ux_data_broker` | UX data broker scripts |
| `ux_page` | UX pages |
| `ux_route` | UX routes (use for workspace ACLs) |
| `aiux_page` | AIUX pages |
| `aiux_widget` | AIUX widgets |
| `aiux_experience` | AIUX experiences |
| `client_callable_flow_object` | Client-callable flows |
| `client_callable_script_include` | Client-callable script includes |

## See

- https://docs.servicenow.com/csh?topicname=acl-api-now-ts.html&version=latest

## Examples

### Advanced ACL with Script

Create an ACL with a custom script for complex permission logic

```
/**
 * @title Advanced ACL with Script
 * @description Create an ACL with a custom script for complex permission logic
 */

import { Acl, Role } from '@servicenow/sdk/core'

export const managerRole = Role({
    $id: Now.ID['manager_role'],
    name: 'manager',
})

export const incidentWithScript = Acl({
    $id: Now.ID['incident_with_script'],
    type: 'record',
    table: 'incident',
    operation: 'write',
    decisionType: 'allow',
    roles: [managerRole],
    script: `
        // Check if user is the assigned manager
        return current.assigned_to == gs.getUserID();
    `,
    description: 'Allow managers to write incidents they are assigned to',
    adminOverrides: false,
})
```

### Basic ACL Example

Create access control rules for incident table with role-based permissions

```
/**
 * @title Basic ACL Example
 * @description Create access control rules for incident table with role-based permissions
 */

import { Acl, Role } from '@servicenow/sdk/core'

export const itilRole = Role({
    $id: Now.ID['itil_role'],
    name: 'itil',
})

export const adminRole = Role({
    $id: Now.ID['admin_role'],
    name: 'admin',
})

export const incidentDenyUnlessItil = Acl({
    $id: Now.ID['incident_deny_unless_itil'],
    type: 'record',
    table: 'incident',
    operation: 'read',
    decisionType: 'deny',
    roles: [itilRole],
    description: 'Deny access to incidents unless user has itil role',
    adminOverrides: true,
})

export const incidentAllowRead = Acl({
    $id: Now.ID['incident_allow_read'],
    type: 'record',
    table: 'incident',
    operation: 'read',
    decisionType: 'allow',
    roles: [itilRole],
    adminOverrides: true,
})
```

### REST Endpoint ACL

Create an ACL for protecting a REST API endpoint with role-based access

```
/**
 * @title REST Endpoint ACL
 * @description Create an ACL for protecting a REST API endpoint with role-based access
 */
import { Acl, Role } from '@servicenow/sdk/core'

export const sampleAdmin = Role({
    name: 'x_acl_sample.admin',
})
Acl({
    $id: Now.ID['rest_acl'],
    name: 'sample_api',
    type: 'rest_endpoint',
    operation: 'execute',
    roles: [sampleAdmin],
    securityAttribute: 'user_is_authenticated',
})
```

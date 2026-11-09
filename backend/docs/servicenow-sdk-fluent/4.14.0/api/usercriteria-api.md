Version: 4.14.0

# UserCriteria

Creates a User Criteria record -- a named, reusable access condition that determines which users can view catalog items, knowledge articles, service portal topics, and other platform content (`user_criteria`).

User Criteria controls content visibility (who can see/order items), not database-level security. For database operations (read/write/delete), use ACLs instead.

## Signature

```
Record({
    $id: Now.ID['key'],
    table: 'user_criteria',
    data: { /* properties */ }
})
```

## Usage

```
import { Record } from '@servicenow/sdk/core'

export const itStaff = Record({
    $id: Now.ID['uc_it_staff'],
    table: 'user_criteria',
    data: {
        name: 'IT Staff',
        active: true,
        role: 'itil_role_sys_id',
    },
})
```

## Parameters

### config

Type: `object`

Properties:

- 
$id (required): `string | number | ExplicitKey<string>`
`Now.ID` should be used to define the value. See the `keys-file-guide` topic for more details.

- 
table (required): `'user_criteria'`
Must be set to `'user_criteria'`.

- 
data (required): `object`
User criteria configuration with the following properties:

- name (required): `string`
Display name for the criteria (max 100 chars).

- active (required): `boolean`
Must be explicitly set to `true`. The Fluent `Record` API does not apply platform defaults, so omitting this field results in `null`, causing the criteria to be silently skipped during evaluation.

- match_all (optional): `boolean`

- `false` (default): OR logic - any condition matches

- `true`: AND logic - all set conditions must match

- advanced (optional): `boolean`

- `true`: enables scripted evaluation via the `script` field

- `false` (default): uses field-based conditions only

- script (optional): `string`
Server-side JavaScript for custom evaluation logic. Only used when `advanced: true`. Must set `answer = true` or `answer = false`. Use `user_id` variable (target user's sys_id), NOT `gs.getUserID()`.

- user, group, role, department, location, company (optional): `string | string[]`
Reference fields for sys_user, sys_user_group, sys_user_role, cmn_department, cmn_location, core_company. All stored as comma-separated lists with 1024 char max.

- short_description (optional): `string`
Additional description (max 4000 chars).

- 
$meta (optional): `object`

- installMethod: `'first install' | 'demo' | 'once'` — Maps to output folder: 'first install' → 'unload', 'demo' → 'unload.demo'

## See

- https://docs.servicenow.com/csh?topicname=user-criteria.html&version=latest

## Examples

/**

- @title Basic Role-Based Criteria

- @description Create user criteria that grants access to users with a specific role.
*/

```
import { Record } from '@servicenow/sdk/core'

export const itilUsers = Record({
    $id: Now.ID['uc_itil_users'],
    table: 'user_criteria',
    data: {
        name: 'ITIL Users',
        active: true,
        role: 'itil_role_sys_id', // sys_id of existing role
    },
})
```

/**

- @title AND Logic — All Conditions Must Match

- @description Create user criteria requiring users to match ALL specified conditions using match_all.
*/

```
import { Record } from '@servicenow/sdk/core'

// Only users who have the itil role AND are located in New York qualify
export const nyItilCriteria = Record({
    $id: Now.ID['uc_ny_itil'],
    table: 'user_criteria',
    data: {
        name: 'New York ITIL Users',
        active: true,
        role: 'itil_sys_id',
        location: 'new_york_location_sys_id',
        match_all: true,
    },
})
```

For comprehensive examples including cross-file references, mixing new and existing records, and complex multi-criteria patterns, see the `user-criteria-examples-guide` topic. For common mistakes and edge cases, see the `user-criteria-guide` topic.

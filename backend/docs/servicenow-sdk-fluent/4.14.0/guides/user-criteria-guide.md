Version: 4.14.0

# User Criteria

User Criteria (`user_criteria`) are named, reusable access conditions that determine which users can view catalog items, knowledge articles, service portal topics, and other platform content. Required for controlling Service Catalog item visibility—always use instead of ACLs or the `roles` property for who can see/order catalog items. Unlike ACLs—which control read/write/delete operations on database records—User Criteria define audience membership based on combinations of users, groups, roles, departments, locations, companies, and optional scripts.

## When to Use

- Controlling who can see or order a catalog item — this is the ONLY recommended mechanism for catalog item visibility. Any prompt mentioning "only [role/group/department] should see/submit/access this catalog item" requires User Criteria. Do not use the `roles` property on `CatalogItem`.

- Controlling who can read a knowledge article (`can_read_user_criteria`, `cannot_read_user_criteria` on `kb_knowledge`)

- Restricting service portal topics to specific audiences

- Building named, reusable audience definitions shared across multiple catalog items or knowledge bases

- Combining multiple attributes in one rule (e.g., must have a role AND be in a specific location → use `match_all: true`)

- When role/group membership alone is insufficient and custom script logic is needed

## Plan Decision Matrix

| User says... | Plan step should be... |
| "Only IT staff can see/submit the item" | Create User Criteria + set `availableFor` |
| "Only managers can order this" | Create User Criteria + set `availableFor` |
| "Hide from non-IT users" | Create User Criteria + set `notAvailableFor` |
| "Restrict table record access" | → Use ACLs (see `security-guide` ) |
| "Prevent API access to table data" | → Use ACLs (see `security-guide` ) |

Key distinction: "See/submit catalog item" → User Criteria. "Read/write/delete table records" → ACLs. Never mix these up in a plan.

## Instructions

- Decide the access rule type: simple field-based conditions (`user`, `group`, `role`, `department`, `location`, `company`) or scripted evaluation (`advanced: true` + `script`).

- Create a `Record({ table: 'user_criteria', ... })` in a `.now.ts` file and assign a `$id` using `Now.ID['your_key']`.

- Always set `active: true` explicitly — the Fluent `Record` API does not apply platform defaults; omitting `active` results in `null` and the criteria is silently skipped during evaluation.

- For multi-condition criteria, choose `match_all: false` (OR logic, default) or `match_all: true` (AND logic — user must satisfy every set condition type).

- For scripted criteria: provide a `script` string and set `advanced: true`. Always use `user_id` for the target user's sys_id — never `gs.getUserID()` or `gs.getUser()`.

- Export the criteria variable with `export const` if it will be imported from another file.

- Declare the criteria record before its consumer (catalog item, KB article, etc.) in the same file — forward `Now.ID` references fail to resolve at deploy time.

- Reference the criteria from consumer fields: `CatalogItem.availableFor`, `CatalogItem.notAvailableFor`, `kb_knowledge.can_read_user_criteria`, or `cannot_read_user_criteria`.

- For pre-existing instance records (roles, groups, catalogs, etc.), always query the instance Table API to retrieve the real sys_id before writing code — never use placeholder strings in source files.

## API Reference

For full property definitions, types, and basic examples, see the `usercriteria-api` topic.

For comprehensive, scenario-based examples including cross-file references, mixing new and existing records, and complex multi-criteria patterns, see the `user-criteria-examples-guide` topic.

## Important Rules

- Always set `active: true` — omitting results in `null` and silent failures

- Use `user_id` in scripts — never `gs.getUserID()` (returns session user, not target)

- `notAvailableFor` always overrides `availableFor`

- Export criteria for cross-file use — requires `export const`

- Declare before consumers — forward references fail at deploy

- Reference project records: `Now.ref('table', 'now_id_key')` for groups/users/locations/departments/companies; `Now.ref('sys_user_role', { name: 'role_name' })` for roles

- Reference instance records: sys_id strings — single: `role: 'sys_id'`, multiple: `role: ['sys_id1', 'sys_id2']`

- Specify at least one condition — empty criteria matches no users

## Key Concepts

### Match All vs Match Any

`match_all: false` (default — OR logic): a user qualifies if they match at least one of the populated conditions.

`match_all: true` (AND logic): a user must match at least one entry in every condition type that is set.

| `match_all` | Conditions set | Who qualifies |
| `false` | `role: A` , `group: B` | Users with role A or in group B |
| `true` | `role: A` , `location: X` | Users with role A and in location X |
| `true` | `role: A` (only) | Users with role A (AND with only one type is the same as OR) |

When `match_all: true`, any condition type that is not set is ignored. Only set condition types participate in AND evaluation.

Note: When using `advanced: true` with a script, the script is treated as another condition and follows the same `match_all` logic. See "Simple vs Advanced (Scripted) Criteria" below for details.

### Multi-Criteria Arrays and Collision Precedence

When a consumer (e.g. `CatalogItem`) references multiple criteria in one field, the array uses OR logic — matching any one criteria in the array grants (or denies) access:

```
availableFor: [criteriaA, criteriaB]  // user matching A OR B → granted
notAvailableFor: [criteriaX, criteriaY]  // user matching X OR Y → denied
```

`notAvailableFor` always wins over `availableFor` — this is a hard platform precedence rule:

| User matches | `availableFor` | `notAvailableFor` | Access |
| A only | criteriaA | criteriaX | ✅ granted |
| X only | criteriaA | criteriaX | ❌ denied |
| Both A and X | criteriaA | criteriaX | ❌ denied — exclusion wins |
| Neither | criteriaA | criteriaX | ❌ denied |

Empty or omitted arrays:

- `availableFor: []` (or omitted) — no access restriction by criteria; all users can see the item (subject to other controls like ACLs).

- `notAvailableFor: []` (or omitted) — no exclusion; no users are explicitly blocked.

### Simple vs Advanced (Scripted) Criteria

Simple (`advanced: false`, default): populate any combination of `user`, `group`, `role`, `department`, `location`, `company`. No scripting.

Advanced (`advanced: true`): enables the `script` field for custom evaluation logic. The script is evaluated alongside any standard field conditions based on the `match_all` setting:

- `match_all: false` (default): script OR any field condition → user matches if script passes OR any field matches

- `match_all: true`: script AND all field conditions → user must pass script AND satisfy all populated fields

### Script Behavioral Rules

These rules are enforced by the platform and cannot be worked around:

- Not cached: scripted criteria evaluate on every access check. A slow script degrades performance every time a user loads a catalog page or knowledge search. Keep scripts efficient and use indexed queries.

- Use `user_id`: the platform provides `user_id` as the sys_id of the user being evaluated. This is the target user—not the logged-in session user.

- Do NOT use `gs.getUserID()` or `gs.getUser()`: these return the currently executing session user, not the user being evaluated. Using them will grant or deny access based on whoever is running the check (often an admin or service account), not the intended user.

- Check roles using GlideRecord queries: query `sys_user_has_role` to check if the target user has specific roles. This approach works in both global and scoped apps — unlike `gs.hasRole()`, which checks the session user's roles:

```
var gr = new GlideRecord('sys_user');
if (gr.get(user_id)) {
    var roleGr = new GlideRecord('sys_user_has_role');
    roleGr.addQuery('user', gr.sys_id);
    roleGr.addQuery('role.name', 'itil');
    roleGr.query();
    answer = roleGr.hasNext();
}
```

- Do NOT use `current`: no record context is available in user criteria scripts.

- Set `answer`: populate `answer = true` to grant access or `answer = false` to deny. The script can also evaluate to a boolean expression.

- Scope: the script runs in the application scope where the user criteria is defined.

- Max length: script field has a maximum length of 8000 characters.

- Coupled with `advanced`: when using scripts, both `advanced: true` and `script` must be set together. Setting `advanced: true` without a script leaves the criteria non-functional. Conversely, you may omit `advanced` when providing a non-empty script (the platform auto-sets it), but explicit is clearer.

### Active Flag

Only criteria with `active: true` appear in the reference qualifier filters used by catalog items (`active=true^EQ`), knowledge articles, and portal topics. Deactivating a criteria (`active: false`) silently removes it from all content selection lists—users who relied on it for access will lose visibility without any warning.

### Performance and Caching

Critical: Scripts are NEVER cached. Scripted user criteria (`advanced: true`) evaluate on every access check with no caching. This impacts performance every time a user loads a catalog page, searches knowledge articles, or accesses portal widgets.

Field-based criteria (no script) may have platform-level caching for role/group membership, but this is not guaranteed or documented. Always assume no caching and design for performance.

Performance impact examples:

- Catalog page load: Evaluates criteria for every visible item

- Knowledge search: Evaluates criteria for every article in results

- Service Portal: Evaluates criteria for every widget/instance (configurable via `glide.service_portal.sp_user_criteria.cache_enabled`)

Best practices:

- 
Prefer field-based criteria over scripts when possible:

```
// ✅ GOOD - simple field check (may be cached)
data: { name: 'IT Staff', active: true, role: 'itil_role_sys_id' }

// ❌ AVOID - script doing the same thing (never cached)
data: { 
    name: 'IT Staff', 
    active: true, 
    advanced: true,
    script: `
    var gr = new GlideRecord('sys_user');
    if (gr.get(user_id)) {
        var roleGr = new GlideRecord('sys_user_has_role');
        roleGr.addQuery('user', gr.sys_id);
        roleGr.addQuery('role.name', 'itil');
        roleGr.query();
        answer = roleGr.hasNext();
    }`
}
```

- 
Keep scripts lightweight - avoid heavy queries:

```
// ❌ BAD - counts records on every evaluation
script: `
var gr = new GlideRecord('incident');
gr.addQuery('assigned_to', user_id);
gr.query();
answer = gr.getRowCount() > 0;  // Runs every time!
`

// ✅ BETTER - use indexed role check
script: `
var gr = new GlideRecord('sys_user');
if (gr.get(user_id)) {
    var roleGr = new GlideRecord('sys_user_has_role');
    roleGr.addQuery('user', gr.sys_id);
    roleGr.addQuery('role.name', 'incident_manager');
    roleGr.query();
    answer = roleGr.hasNext();
}
`
```

- 
Use indexed queries if scripts are necessary:

- Query on indexed fields only

- Avoid `getRowCount()` on large tables

- Use `hasNext()` instead of counting when checking existence

- 
Consider the evaluation frequency:

- 100 catalog items × 1000 users/day = 100,000 script executions

- A 50ms script = 5,000 seconds (83 minutes) of total execution time per day

Cache invalidation: User criteria records are re-read when `sys_updated_on` changes, but scripts still execute on every evaluation even after the record is cached.

## Properties

For the complete property reference table, see the `usercriteria-api` topic.

Key properties:

- `name` (required) — Criteria name

- `active` (required) — Must be explicitly set to `true` for evaluation; omitting results in `null` and silent failures

- `match_all` — `true` for AND logic, `false` for OR logic (default)

- `advanced` — Enables the `script` field

- `user`, `group`, `role`, `department`, `location`, `company` — Accept sys_id strings or arrays (max 1024 chars each)

- `script` — JavaScript evaluated when `advanced: true`; must set `answer` variable

Performance Note: Prefer field-based criteria over scripts when possible — field-based criteria (no script) may have platform-level caching, while scripts are NEVER cached and evaluate on every access check.

Referencing roles, groups, and users:

- For project records: Use `Now.ref('table_name', 'now_id_key')` for groups/users/locations/departments/companies, or `Now.ref('sys_user_role', { name: 'role_name' })` for roles — dynamically resolves to sys_id at deploy time

- For single instance record: Use sys_id string directly (e.g., `role: 'itil_sys_id'`)

- For multiple instance records: Use simple array of sys_id strings (e.g., `role: ['sys_id1', 'sys_id2']`)

Important: When creating project-defined roles, groups, users, locations, departments, or companies, always use unique and descriptive names that won't conflict with existing instance records. Use prefixes like your app scope (e.g., `x_myapp.manager`), creative names (e.g., `Nebula Forge Collective`), or suffixes (e.g., `ACME Global HQ`) to avoid collisions with standard ServiceNow records like `admin`, `IT Support`, or `Headquarters`.

```
// ✅ Same-project Role — use Now.ref() with coalesce key
Role({ $id: Now.ID['role_manager'], name: 'x_myapp.manager' })
export const myCriteria = Record({
    table: 'user_criteria',
    data: { name: 'My Criteria', active: true, role: Now.ref('sys_user_role', { name: 'x_myapp.manager' }) },
})

// ✅ Same-project Group — use Now.ref() with Now.ID key string
Record({ $id: Now.ID['my_group'], table: 'sys_user_group', data: { name: 'My Group' } })
export const groupCriteria = Record({
    table: 'user_criteria',
    data: { name: 'Group Criteria', active: true, group: Now.ref('sys_user_group', 'my_group') },
})

// ✅ Instance record by sys_id — single value
data: { role: 'itil_role_sys_id_from_instance' }

// ✅ Instance records by sys_id — multiple values (simple array)
data: { 
    role: ['itil_sys_id', 'admin_sys_id'],
    group: ['group_sys_id_1', 'group_sys_id_2'],
}
```

## Declaration Order and Exports

### Same-File Declaration Order

Fluent processes `Record()` calls in declaration order. Any `CatalogItem`, `kb_knowledge`, or other record that references a user criteria via `Now.ID` must appear after the criteria declaration in the same file. A forward reference will fail to resolve the ID at deploy time.

```
// ✅ CORRECT — criteria declared first
const itStaff = Record({
    table: 'user_criteria',
    $id: Now.ID['it_staff'],
    data: { name: 'IT Staff', active: true, role: 'role_sys_id' },
})

CatalogItem({
    $id: Now.ID['hardware_request'],
    name: 'Hardware Request',
    availableFor: [itStaff],  // resolved — declared above
})

// ❌ WRONG — forward reference
CatalogItem({
    availableFor: [itStaff],  // fails — itStaff not yet declared
})
const itStaff = Record({ ... })
```

### Cross-File References Require Export

When a user criteria will be referenced from another file, it must be exported using `export const`. Without the export, cross-file `Now.ID` references fail to resolve at deploy time.

```
// ✅ CORRECT — export so other files can import
export const itStaff = Record({
    table: 'user_criteria',
    $id: Now.ID['it_staff'],
    data: { name: 'IT Staff', active: true, role: 'role_sys_id' },
})

// ❌ WRONG — cannot be referenced from another file
Record({
    table: 'user_criteria',
    $id: Now.ID['it_staff'],
    data: { name: 'IT Staff', active: true, role: 'role_sys_id' },
})
```

## Where User Criteria Is Referenced

### Catalog Items

```
availableFor: [criteriaRecord]     // users matching any of these can see/order the item
notAvailableFor: [criteriaRecord]  // exclusion list; always overrides availableFor
```

Pass a Fluent `Record` instance (imported from the criteria file) or a raw sys_id string.

Note: Catalog items also have a `secondary_owners` field which references a user criteria record to grant editorial access (the ability to edit the catalog item) to users who are not catalog admins. This is separate from the ordering visibility controlled by `availableFor`/`notAvailableFor`.

### Knowledge Articles (`kb_knowledge`)

```
data: {
  can_read_user_criteria: criteriaRecord,     // users matching these can read the article
  cannot_read_user_criteria: criteriaRecord,  // users matching these cannot read the article
}
```

### Service Portal Topics

Portal topics reference user criteria for audience-based visibility. Only `active: true` criteria appear in the topic's user criteria selection field.

### Other Consumer Tables

User Criteria is also referenced by:

- Record Producers (`sc_cat_item_producer`): same `availableFor`/`notAvailableFor` pattern as catalog items

- Service Catalog Categories (`sc_category`): control category visibility

- Service Catalogs (`sc_catalog`): catalog-level visibility control

- Service Catalog Templates (`sc_template`): via `available_for` field (direct reference, no M2M)

- Knowledge Base Categories (`kb_category`): `can_read_user_criteria`, `cannot_read_user_criteria`

- Knowledge Bases (`kb_knowledge_base`): same read access fields as categories

## Examples

### Role-Based (OR Logic)

```
import { Record } from '@servicenow/sdk/core'

export const itilUsers = Record({
    $id: Now.ID['uc_itil_users'],
    table: 'user_criteria',
    data: { name: 'ITIL Users', active: true, role: 'itil_role_sys_id' },
})
```

### AND Logic — All Conditions Must Match

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

### Scripted Criteria (Advanced Mode)

```
import { Record } from '@servicenow/sdk/core'

export const seniorManagers = Record({
    $id: Now.ID['uc_senior_managers'],
    table: 'user_criteria',
    data: {
        name: 'Senior Managers',
        active: true,
        advanced: true,
        script: `
// user_id is the sys_id of the user being evaluated — NOT gs.getUserID()
var gr = new GlideRecord('sys_user');
gr.addQuery('manager', user_id);
gr.query();
answer = gr.getRowCount() >= 5;
`,
    },
})
```

### Detect Guest (Unauthenticated) Users

Use a script to block access for ServiceNow guest users (unauthenticated public sessions):

```
import { Record } from '@servicenow/sdk/core'

export const authenticatedUsers = Record({
    $id: Now.ID['uc_authenticated'],
    table: 'user_criteria',
    data: {
        name: 'Authenticated Users Only',
        active: true,
        advanced: true,
        script: `
// Deny access for guest (unauthenticated) users
var gr = new GlideRecord('sys_user');
if (gr.get(user_id)) {
    answer = gr.getValue('user_name') !== 'guest';
} else {
    answer = false;
}
`,
    },
})
```

### Plugin-Conditional Criteria

Grant access only when a specific ServiceNow plugin is active on the instance:

```
import { Record } from '@servicenow/sdk/core'

export const hrModuleUsers = Record({
    $id: Now.ID['uc_hr_module'],
    table: 'user_criteria',
    data: {
        name: 'HR Module Active',
        active: true,
        advanced: true,
        script: `
// Only evaluate when HR plugin is active; deny otherwise
// Query v_plugin table (works in both global and scoped apps)
var plugin = new GlideRecord('v_plugin');
plugin.addQuery('id', 'com.snc.human_resources'); // Get the system plugin from v_plugin table
plugin.addQuery('active', 'active');
plugin.query();
if (!plugin.hasNext()) {
    answer = false;
} else {
    var gr = new GlideRecord('sys_user');
    if (gr.get(user_id)) {
        var roleGr = new GlideRecord('sys_user_has_role');
        roleGr.addQuery('user', gr.sys_id);
        roleGr.addQuery('role.name', 'IN', 'sn_hr_core.admin,sn_hr_core.manager');
        roleGr.query();
        answer = roleGr.hasNext();
    } else {
        answer = false;
    }
}
`,
    },
})
```

### Used in Catalog Item

```
import { Record, CatalogItem } from '@servicenow/sdk/core'

const itilUsers = Record({
    $id: Now.ID['uc_itil'],
    table: 'user_criteria',
    data: { name: 'ITIL Users', active: true, role: 'itil_role_sys_id' },
})

const guestUsers = Record({
    $id: Now.ID['uc_guests'],
    table: 'user_criteria',
    data: { name: 'Guest Users', active: true, group: 'guest_group_sys_id' },
})

CatalogItem({
    $id: Now.ID['laptop_request'],
    name: 'Laptop Request',
    availableFor: [itilUsers],     // ITIL users can see and order
    notAvailableFor: [guestUsers], // Guests blocked even if they match itilUsers
})
```

Note: `notAvailableFor` always overrides `availableFor`. A user matching both is denied access.

### Multiple Values and Multiple Criteria

```
import { Record, Role, CatalogItem } from '@servicenow/sdk/core'

// --- Multiple values in one field (OR logic) ---
Role({ $id: Now.ID['role_catalog_admin'], name: 'sn_it_ops.catalog_admin' })
Role({ $id: Now.ID['role_catalog_designer'], name: 'sn_it_ops.catalog_designer' })

export const catalogTeamCriteria = Record({
    $id: Now.ID['uc_catalog_team'],
    table: 'user_criteria',
    data: {
        name: 'Catalog Team',
        active: true,
        role: [
            'e098ecf6c0a80165002aaec84d906014', // catalog (existing sys_id)
            Now.ref('sys_user_role', { name: 'sn_it_ops.catalog_admin' }), // project-defined
            Now.ref('sys_user_role', { name: 'sn_it_ops.catalog_designer' }), // project-defined
        ], // OR: user needs ANY ONE of these roles
    },
})

// --- Multiple criteria in availableFor (OR logic) ---
export const itDeptCriteria = Record({
    $id: Now.ID['uc_it_dept'],
    table: 'user_criteria',
    data: {
        name: 'IT Department',
        active: true,
        department: '221f79b7c6112284005d646b76ab978c', // IT dept sys_id
    },
})

CatalogItem({
    $id: Now.ID['catalog_tools'],
    name: 'Catalog Management Tools',
    availableFor: [
        catalogTeamCriteria, // has catalog role OR catalog_admin OR catalog_designer
        itDeptCriteria,      // in IT department
    ], // OR: matching ANY ONE of these criteria grants access
})
```

Key patterns:

- Multiple values in same field: OR logic — user needs ANY ONE match

- Multiple criteria in `availableFor`: OR logic — user matching ANY ONE criteria gets access

- Project-defined records: Use `Now.ref('table', 'now_id_key')` for groups/users/locations/departments/companies

- Multiple instance records: Use simple array of sys_id strings (e.g., `role: ['sys_id1', 'sys_id2']`)

For complete scenario-based examples including specific user lists, knowledge articles, location-based, company-based, multiple groups, referencing new users/groups, scripted with external files, cross-file references, and combining multiple criteria, see the `user-criteria-examples-guide` topic.

## Edge Cases and Common Mistakes

### ❌ Forgetting active: true

```
// WRONG - criteria will be silently ignored
data: { name: 'Broken', role: 'itil' }

// CORRECT - always set active explicitly
data: { name: 'Working', active: true, role: 'itil' }
```

### ❌ Empty Criteria

```
// WRONG - no conditions matches no users
data: { name: 'Empty', active: true }

// CORRECT - always specify at least one condition
data: { name: 'IT Staff', active: true, role: 'itil_role_sys_id' }
```

### ❌ Redundant match_all with Single Condition

```
// WRONG - match_all has no effect with single condition type
data: { name: 'IT Role', active: true, match_all: true, role: 'itil_sys_id' }

// CORRECT - only use match_all with multiple condition types
data: { 
    name: 'IT in HW Dept', 
    active: true, 
    match_all: true, 
    role: 'itil_sys_id', 
    department: 'hw_dept_sys_id' 
}
```

### ❌ Invalid Reference Syntax

```
// WRONG - placeholder sys_ids, Now.ID in data fields
data: { name: 'Bad', active: true, group: 'PLACEHOLDER_SYS_ID' }
data: { name: 'Bad', active: true, group: Now.ID['some_group'] }

// CORRECT - project records use Now.ref(), instance records use sys_id strings
Record({ $id: Now.ID['some_group'], table: 'sys_user_group', data: { name: 'My Group' } })
data: { name: 'Good', active: true, group: Now.ref('sys_user_group', 'some_group') }
data: { name: 'Good', active: true, group: 'actual_group_sys_id' }
data: { name: 'Good', active: true, group: ['sys_id_1', 'sys_id_2'] }
```

### ❌ Script Issues

```
// WRONG - gs.getUserID() returns session user, not target; advanced without script; heavy queries
script: `answer = gs.getUser().hasRole('itil');`
data: { name: 'Bad', active: true, advanced: true } // no script
script: `var gr = new GlideRecord('incident'); gr.query(); while(gr.next()) count++;` // heavy

// CORRECT - use user_id variable, provide script with advanced, use aggregates
script: `
var gr = new GlideRecord('sys_user_has_role');
gr.addQuery('user', user_id);
gr.addQuery('role.name', 'itil');
gr.query();
answer = gr.hasNext();
`
data: { name: 'Good', active: true, advanced: true, script: Now.include('check.js') }
script: `
var agg = new GlideAggregate('incident');
agg.addQuery('assigned_to', user_id);
agg.addAggregate('COUNT');
answer = agg.next() && parseInt(agg.getAggregate('COUNT')) > 100;
`
```

### ❌ Exceeding Max Length Limits

```
// WRONG - too many sys_ids may exceed 1024 char limit
data: { name: 'Many', active: true, group: ['sys_id_1', 'sys_id_2', /* ...50 more */ ] }

// CORRECT - split into multiple criteria
const groupsA = Record({ $id: Now.ID['groups_a'], table: 'user_criteria', data: { name: 'Groups A', active: true, group: ['sys_id_1', 'sys_id_2'] } })
const groupsB = Record({ $id: Now.ID['groups_b'], table: 'user_criteria', data: { name: 'Groups B', active: true, group: ['sys_id_3', 'sys_id_4'] } })
CatalogItem({ name: 'My Item', availableFor: [groupsA, groupsB] })
```

### ❌ Referencing Inactive Criteria

```
// WRONG - inactive criteria are silently ignored
const inactive = Record({ table: 'user_criteria', data: { name: 'Bad', active: false, role: 'itil' } })
Record({ table: 'kb_knowledge', data: { can_read_user_criteria: [inactive] } }) // Ignored!

// CORRECT - only reference active criteria
const active = Record({ table: 'user_criteria', data: { name: 'Good', active: true, role: 'itil' } })
Record({ table: 'kb_knowledge', data: { can_read_user_criteria: [active] } })
```

### Admin Users Always Have Access

Platform administrators (users with the `admin` role) bypass User Criteria evaluation entirely. Criteria defined in `availableFor` and `notAvailableFor` have no effect on admin users — they always see all content.

❌ Do not rely on `notAvailableFor` to restrict admins:

```
// This will NOT prevent admins from ordering the item
CatalogItem({
    $id: Now.ID['restricted_item'],
    name: 'Restricted Item',
    notAvailableFor: [nonAdminsOnly], // ❌ Admins still see this
})
```

If you need true access restriction for admins, use an ACL (`sys_security_acl`) on the underlying table, not User Criteria.

### `advanced` Flag Is Auto-Managed by a Business Rule

A "Save as advanced user criteria" business rule automatically sets `advanced = true` when the `script` field contains non-boilerplate content. When the script is cleared, a second "Clear user criteria script" business rule resets `advanced` back to `false`.

This means:

- You may omit `advanced` in Fluent when providing a populated `script` value — the platform sets it automatically on save.

- However, setting `advanced: true` explicitly is still recommended to make intent clear.

- If you set `advanced: true` but leave `script` empty or with only the default comment block, the BR may reset `advanced` to `false` on the next save.

✅ Preferred — always set both together:

```
data: {
    name: 'Tenure Check',
    active: true,
    advanced: true,            // explicit — makes intent clear
    script: Now.include('check-tenure.js'),
}
```

### Using Session User in Script

❌ Wrong — `gs.getUserID()` returns the session user, not the user being evaluated:

```
data: {
    name: 'Bad Script',
    active: true,
    advanced: true,
    script: `answer = gs.getUser().hasRole('itil');`, // ❌ Wrong user
}
```

✅ Correct — use `user_id` variable, which contains the target user's sys_id:

```
data: {
    name: 'Good Script',
    active: true,
    advanced: true,
    script: `
var gr = new GlideRecord('sys_user_has_role');
gr.addQuery('user', user_id);
gr.addQuery('role.name', 'itil');
gr.query();
answer = gr.hasNext();
`,
}
```

## User Criteria vs Other Access Controls

### User Criteria vs ACL

A common mistake is creating ACLs on `sc_cat_item` or `kb_knowledge` to control catalog or knowledge visibility. ACLs control database-level record access; User Criteria control content visibility in catalog, knowledge, and portal contexts.

| Aspect | User Criteria | ACL ( `sys_security_acl` ) |
| Controls | Who sees catalog/KB/portal content | Who can read/write/delete database records |
| Enforcement context | Catalog, knowledge base, service portal | GlideRecord API, forms, REST API |
| Operation model | Audience membership | CRUD operation per table/field |
| Script variable | `user_id` (target user) | `current` (the record being accessed) |
| Caching | Not cached when scripted | Platform-managed per session |
| Bypassed via API? | Yes — ACLs govern API access | No — ACLs enforce at the database layer |

Use ACL when controlling whether users can read, create, or modify records in a database table.
Use User Criteria when controlling which users can see or interact with content in the catalog, knowledge base, or service portal.

For detailed ACL usage, see the `security-guide` topic.

### User Criteria vs Roles

Roles (`sys_user_role`) define user personas; User Criteria define content visibility. Roles are inputs to User Criteria — reference roles in the `role` field, then use the criteria in `availableFor` for catalog visibility.

- Use Roles: Define personas (e.g., `x_myapp.manager`) referenced by ACLs or User Criteria

- Use User Criteria: Control who sees/orders catalog items or reads KB articles (supports role + group + location + script)

### User Criteria vs Groups

Groups (`sys_user_group`) are teams — static membership lists managed by team leads or HR. User Criteria are dynamic audience definitions evaluated at access-check time.

| Aspect | User Criteria | Group ( `sys_user_group` ) |
| Membership basis | Multi-attribute (role, location, company, script) | Direct member list |
| AND/OR logic | Yes — via `match_all` | No |
| Script evaluation | Yes (advanced mode) | No |
| Used for | Catalog/KB/portal visibility | Team assignment, approval, notifications |
| Admin model | Defined in source code | Managed in the instance |

Use Groups when the audience is a team managed by HR or IT ops, and membership is maintained by people, not code.
Use User Criteria when the audience is defined by attribute rules (role + location + department) or requires custom scripting.

## Anti-patterns

- Never use `gs.getUserID()` or `gs.getUser()` in scripts — these return the session user, not the user being evaluated. Use `user_id` variable set to the sys_id of the user record. For role checks, query `sys_user_has_role` with the target user's sys_id (works in both global and scoped apps).

- Never use `current` in scripts — no record context exists; the variable is undefined and will cause silent failures or errors.

- Never write expensive queries in scripts — scripted criteria run on every access check and are not cached. Unindexed queries on large tables will degrade platform performance for every user loading catalog or knowledge pages.

- Never set `advanced: true` without populating `script` — the script field defaults to a comment block; the platform may reset `advanced` back to `false` on save when the script is empty. Always set both together.

- Never rely on User Criteria to restrict admin users — platform admins bypass criteria evaluation entirely. If you need to restrict admins, use ACLs instead.

- Never explicitly set `active: false` in new criteria — omit `active` entirely or set it to `true`. Only use `active: false` when intentionally deactivating existing criteria. The Fluent `Record` API does not apply defaults, so omitting `active` results in `null` and silent evaluation failures.

- Never deactivate criteria without auditing downstream impact — `active: false` silently removes the criteria from catalog items and knowledge articles without notification. Users lose access invisibly.

- Never declare criteria after the consumer record — forward references fail to resolve at deploy time.

- Never forget to export criteria used in other files — cross-file references require `export const`.

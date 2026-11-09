Version: 4.14.0

# UserCriteria Examples Guide

This guide provides comprehensive, scenario-based examples for working with User Criteria in Fluent. For basic API usage and field definitions, see the `usercriteria-api` topic. For common mistakes and troubleshooting, see the `user-criteria-guide` topic.

## Table of Contents

- Basic Examples

- Basic Role-Based Criteria

- Multiple Conditions with OR Logic

- Scripted with External File

- Using notAvailableFor (Exclusion Lists)

- Used in Knowledge Article

- Location and Company Based

- Referencing Records

- Same File References

- Cross-File References

- Three-File Chain Example

- Mixing References

- New and Existing References

- Multiple Values in Single Field

- Advanced Scripted Criteria with Mixed Records

- Multiple Criteria Patterns

- Multiple Criteria in availableFor/notAvailableFor

## Examples

### Basic Examples

#### Basic Role-Based Criteria

Create user criteria for users with a specific role and use in catalog items.

`data.role` with a pre-existing role: Pass the sys_id string of an existing `sys_user_role` record on the target instance.

If you are creating a new `Role()` in the same project, use `Now.ref('sys_user_role', { name: 'role_name' })` — it dynamically resolves to the hashed sys_id.

```
import { Record, CatalogItem } from '@servicenow/sdk/core'

export const itilUsers = Record({
    $id: Now.ID['uc_itil_users'],
    table: 'user_criteria',
    data: {
        name: 'ITIL Users',
        active: true,
        role: 'itil_role_sys_id', // sys_id of existing role
    },
})

CatalogItem({ // Use criteria in catalog item
    $id: Now.ID['server_access'],
    name: 'Server Access Request',
    shortDescription: 'Request access to servers',
    availableFor: [itilUsers],
})
```

#### Multiple Conditions with OR Logic

Users matching ANY condition qualify (default behavior)

```
import { Record } from '@servicenow/sdk/core'

export const itSupportCriteria = Record({
    $id: Now.ID['uc_it_support'],
    table: 'user_criteria',
    data: {
        name: 'IT Support',
        active: true,
        group: 'it_support_group_sys_id', // OR logic: user needs ANY ONE
        role: 'itil_sys_id',
        department: 'it_department_sys_id',
    },
})
```

#### Scripted with External File

Reference external script file for better maintainability

```
import { Record } from '@servicenow/sdk/core'

export const seniorEmployees = Record({
    $id: Now.ID['uc_senior_employees'],
    table: 'user_criteria',
    data: {
        name: 'Senior Employees (5+ Years)',
        active: true,
        advanced: true,
        script: Now.include('scripts/check-employee-tenure.js'),
    },
})
```

`src/scripts/check-employee-tenure.js`:

```
var user = new GlideRecord('sys_user');
if (user.get(user_id)) {
    var hireDate = new GlideDateTime(user.getValue('hire_date'));
    var today = new GlideDateTime();
    var diffMs = today.getNumericValue() - hireDate.getNumericValue();
    var years = diffMs / (1000 * 60 * 60 * 24 * 365.25); // Account for leap years
    answer = years >= 5;
} else {
    answer = false;
}
```

#### Using notAvailableFor (Exclusion Lists)

Block specific users even if they match `availableFor` criteria. `notAvailableFor` always overrides `availableFor`.

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
    $id: Now.ID['server_access_item'],
    name: 'Server Access Request',
    availableFor: [itilUsers], // Grants access
    notAvailableFor: [guestUsers], // Blocks access (overrides availableFor)
})
```

Note: A user matching both lists is denied access.

#### Used in Knowledge Article

Control knowledge article visibility with user criteria

Article-level vs. KB-level access: This example sets access on a single article using the `can_read_user_criteria` list field. To control access for an entire Knowledge Base (Who Can Read / Who Can Contribute), see the `knowledge-base-access-guide` topic.

```
import { Record } from '@servicenow/sdk/core'

const itStaff = Record({
    $id: Now.ID['uc_it_staff'],
    table: 'user_criteria',
    data: { name: 'IT Staff', active: true, group: 'it_staff_group_sys_id' },
})

Record({
    $id: Now.ID['internal_runbook'],
    table: 'kb_knowledge',
    data: {
        short_description: 'Internal IT Runbook',
        kb_knowledge_base: 'it_kb_sys_id',
        can_read_user_criteria: [itStaff],
    },
})
```

#### Location and Company Based

Grant access based on user location or company

```
import { Record } from '@servicenow/sdk/core'

export const japanOffice = Record({ // Location-based
    $id: Now.ID['uc_japan'],
    table: 'user_criteria',
    data: { name: 'Japan Office', active: true, location: 'japan_location_sys_id' },
})

export const acmeEmployees = Record({ // Company-based
    $id: Now.ID['uc_acme'],
    table: 'user_criteria',
    data: { name: 'Acme Employees', active: true, company: 'acme_company_sys_id' },
})

export const americasRegion = Record({ // Multiple companies (OR)
    $id: Now.ID['uc_americas'],
    table: 'user_criteria',
    data: {
        name: 'Americas Region',
        active: true,
        company: ['north_america_sys_id', 'south_america_sys_id'],
    },
})

export const supportTeams = Record({ // Multiple groups (OR)
    $id: Now.ID['uc_support'],
    table: 'user_criteria',
    data: {
        name: 'All Support Teams',
        active: true,
        group: ['tier1_sys_id', 'tier2_sys_id', 'tier3_sys_id'],
    },
})
```

### Referencing Records

#### Same File References

When you define records in the same file, use `Now.ref('table_name', 'now_id_key')` to reference them. For roles, you can use `Now.ref('sys_user_role', { name: 'role_name' })` syntax. The build system dynamically resolves the reference to the hashed sys_id at deploy time.

```
import { Record, Role } from '@servicenow/sdk/core'

// Define project records
Role({ $id: Now.ID['role_app_manager'], name: 'x_myapp.manager' })
Record({ $id: Now.ID['group_vip_support'], table: 'sys_user_group', data: { name: 'VIP Support Team', description: 'Dedicated support for VIP customers' } })
Record({ $id: Now.ID['location_tokyo'], table: 'cmn_location', data: { name: 'Tokyo Office', country: 'Japan' } })

// Reference using Now.ref() - resolves to hashed sys_id at deploy time
export const tokyoVipManagers = Record({
    $id: Now.ID['uc_tokyo_vip_managers'],
    table: 'user_criteria',
    data: {
        name: 'Tokyo VIP Managers',
        active: true,
        role: Now.ref('sys_user_role', { name: 'x_myapp.manager' }), // Role uses { name }
        group: Now.ref('sys_user_group', 'group_vip_support'), // Group uses Now.ID key
        location: Now.ref('cmn_location', 'location_tokyo'), // Location uses Now.ID key
        // OR logic (default): user needs ANY ONE of these conditions
    },
})
```

Same file — User:

Demo/install users (created by the app) can be referenced directly. For existing instance users, use sys_id strings instead.

```
import { Record } from '@servicenow/sdk/core'

Record({ // Demo user created by the app — install data
    $id: Now.ID['user_demo_admin'],
    $meta: { installMethod: 'demo' },
    table: 'sys_user',
    data: {
        user_name: 'demo.admin',
        first_name: 'Demo',
        last_name: 'Admin',
        email: 'demo.admin@example.com',
        active: true,
    },
})

export const demoAdminCriteria = Record({
    $id: Now.ID['uc_demo_admin'],
    table: 'user_criteria',
    data: {
        name: 'Demo Admin User',
        active: true,
        user: Now.ref('sys_user', 'user_demo_admin'),
    },
})
```

#### Cross-File References

For records defined in a separate file, use `Now.ref()` to reference them by their Now.ID key string. No imports needed.

Cross-file — Role defined in `roles.now.ts`, criteria in `user-criteria.now.ts`:

`src/roles.now.ts`:

```
import { Role } from '@servicenow/sdk/core'

Role({
    $id: Now.ID['role_app_manager'],
    name: 'x_myapp.manager',
})
```

`src/user-criteria.now.ts`:

```
import { Record, CatalogItem } from '@servicenow/sdk/core'

export const appManagers = Record({
    $id: Now.ID['uc_app_managers'],
    table: 'user_criteria',
    data: {
        name: 'App Managers',
        active: true,
        role: Now.ref('sys_user_role', { name: 'x_myapp.manager' }),
    },
})

CatalogItem({
    $id: Now.ID['app_settings_item'],
    name: 'App Settings',
    shortDescription: 'Configure application settings',
    availableFor: [appManagers],
})
```

Cross-file — Group defined in `groups.now.ts`, criteria in `user-criteria.now.ts`:

`src/groups.now.ts`:

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['group_vip_support'],
    table: 'sys_user_group',
    data: {
        name: 'VIP Support Team',
        description: 'Dedicated support for VIP customers',
    },
})
```

`src/user-criteria.now.ts`:

```
import { Record } from '@servicenow/sdk/core'

export const vipSupportCriteria = Record({
    $id: Now.ID['uc_vip_support'],
    table: 'user_criteria',
    data: {
        name: 'VIP Support Access',
        active: true,
        group: Now.ref('sys_user_group', 'group_vip_support'),
    },
})
```

Cross-file — Company and Department together (AND logic):

`src/org.now.ts`:

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['company_hq'],
    table: 'core_company',
    data: { name: 'Headquarters' },
})

Record({
    $id: Now.ID['dept_engineering'],
    table: 'cmn_department',
    data: { name: 'Engineering' },
})
```

`src/user-criteria.now.ts`:

```
import { Record } from '@servicenow/sdk/core'

export const hqEngineers = Record({
    $id: Now.ID['uc_hq_engineers'],
    table: 'user_criteria',
    data: {
        name: 'HQ Engineering Staff',
        active: true,
        match_all: true,                    // must match BOTH conditions
        company: Now.ref('core_company', 'company_hq'),
        department: Now.ref('cmn_department', 'dept_engineering'),
    },
})
```

Pre-existing instance records (locations, departments, companies that already exist on the target instance) should use sys_id strings directly. Only use `Now.ref()` when your app is creating the referenced record.

#### Three-File Chain Example

Each concern lives in its own file. Each file exports what the next file needs.

`src/locations.now.ts`:

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['location_london'],
    table: 'cmn_location',
    data: {
        name: 'London Office',
        country: 'United Kingdom',
    },
})
```

`src/user-criteria.now.ts`:

```
import { Record } from '@servicenow/sdk/core'

export const londonStaff = Record({
    $id: Now.ID['uc_london_staff'],
    table: 'user_criteria',
    data: {
        name: 'London Office Staff',
        active: true,
        location: Now.ref('cmn_location', 'location_london'),
    },
})
```

`src/catalog.now.ts`:

```
import { CatalogItem } from '@servicenow/sdk/core'
import { londonStaff } from './user-criteria.now'

CatalogItem({
    $id: Now.ID['london_vpn_item'],
    name: 'London VPN Access',
    shortDescription: 'Request VPN access for the London office',
    availableFor: [londonStaff],            // imported from user-criteria.now
})
```

### Mixing References

#### New and Existing References

This example covers three reference patterns in one place — using them together in `availableFor` and `notAvailableFor`.

```
import { Record, Role, CatalogItem } from '@servicenow/sdk/core'

// Both new roles using Now.ref() - user needs either one (OR)
Role({ $id: Now.ID['role_developer'], name: 'x_myapp.developer' })
Role({ $id: Now.ID['role_qa'], name: 'x_myapp.qa' })

export const engineeringCriteria = Record({
    $id: Now.ID['uc_engineering'],
    table: 'user_criteria',
    data: {
        name: 'Engineering Team',
        active: true,
        // Reference roles using Now.ref() - resolves to hashed sys_ids
        role: [Now.ref('sys_user_role', { name: 'x_myapp.developer' }), Now.ref('sys_user_role', { name: 'x_myapp.qa' })],
    },
})

// One new role + existing ITIL role already on the instance
Role({ $id: Now.ID['role_app_manager'], name: 'x_myapp.manager' })

export const managersAndItil = Record({
    $id: Now.ID['uc_managers_itil'],
    table: 'user_criteria',
    data: {
        name: 'App Managers or ITIL',
        active: true,
        role: [
            Now.ref('sys_user_role', { name: 'x_myapp.manager' }), // project-defined
            'itil_existing_sys_id', // instance record by sys_id
        ],
    },
})

// Both existing sys_ids - no Fluent records needed
export const contractorGroups = Record({
    $id: Now.ID['uc_contractors'],
    table: 'user_criteria',
    data: {
        name: 'Contractor Groups',
        active: true,
        group: ['vendor_group_sys_id', 'external_staff_sys_id'], // both pre-existing
    },
})

// availableFor + notAvailableFor - contractors blocked even if they match
CatalogItem({
    $id: Now.ID['internal_tools_item'],
    name: 'Internal Tools Access',
    shortDescription: 'Request access to internal tooling',
    availableFor: [engineeringCriteria, managersAndItil], // OR — either criteria grants access
    notAvailableFor: [contractorGroups],                  // always overrides availableFor
})
```

Key rules illustrated:

- Multiple values in one field (`role: [a, b]`) → OR between them — user needs to match any one

- Multiple criteria in `availableFor` → also OR — matching any one criteria grants access

- For multiple existing records, use simple array of sys_id strings (e.g., `group: ['sys_id1', 'sys_id2']`)

- Mix project records (`Now.ref()`) and sys_id strings in the same array when needed

- `notAvailableFor` always wins — a contractor who also has the developer role is still blocked

#### Multiple Values in Single Field

Multiple values in the same field use OR logic — user needs to match ANY ONE value.

```
import { Record, Role, CatalogItem } from '@servicenow/sdk/core'

// Multiple roles in one criteria (OR logic) - define project roles
Role({ $id: Now.ID['role_catalog_designer'], name: 'sn_it_ops.catalog_designer' })
Role({ $id: Now.ID['role_catalog_publisher'], name: 'sn_it_ops.catalog_publisher' })

export const catalogManagementCriteria = Record({
    $id: Now.ID['uc_catalog_management'],
    table: 'user_criteria',
    data: {
        name: 'Catalog Management Access',
        active: true,
        role: [
            'e098ecf6c0a80165002aaec84d906014', // catalog (existing sys_id)
            'e09d16f2c0a8016501281264b989e1db', // catalog_admin (existing sys_id)
            Now.ref('sys_user_role', { name: 'sn_it_ops.catalog_designer' }), // project-defined
            Now.ref('sys_user_role', { name: 'sn_it_ops.catalog_publisher' }), // project-defined
        ],
    },
})

// Multiple groups in one criteria (OR logic)
Record({ $id: Now.ID['group_backend_eng'], table: 'sys_user_group', data: { name: 'Backend Engineering' } })
Record({ $id: Now.ID['group_frontend_eng'], table: 'sys_user_group', data: { name: 'Frontend Engineering' } })
Record({ $id: Now.ID['group_devops'], table: 'sys_user_group', data: { name: 'DevOps' } })

export const engineeringTeamsCriteria = Record({
    $id: Now.ID['uc_engineering_teams'],
    table: 'user_criteria',
    data: {
        name: 'Engineering Teams',
        active: true,
        group: [
            Now.ref('sys_user_group', 'group_backend_eng'),
            Now.ref('sys_user_group', 'group_frontend_eng'),
            Now.ref('sys_user_group', 'group_devops'),
        ],
    },
})

// Multiple locations in one criteria (OR logic)
Record({ $id: Now.ID['location_london'], table: 'cmn_location', data: { name: 'ACME London' } })
Record({ $id: Now.ID['location_singapore'], table: 'cmn_location', data: { name: 'ACME Singapore' } })

export const globalOfficesCriteria = Record({
    $id: Now.ID['uc_global_offices'],
    table: 'user_criteria',
    data: {
        name: 'Global Offices',
        active: true,
        location: [
            '0d9561b437d0200044e0bfc8bcbe5d32', // Japan (existing sys_id)
            '0e55153437d0200044e0bfc8bcbe5d9d', // North America (existing sys_id)
            Now.ref('cmn_location', 'location_london'), // project-defined
            Now.ref('cmn_location', 'location_singapore'), // project-defined
        ],
    },
})

CatalogItem({
    $id: Now.ID['platform_tools'],
    name: 'Platform Management Tools',
    availableFor: [catalogManagementCriteria, engineeringTeamsCriteria, globalOfficesCriteria],
})
```

#### Advanced Scripted Criteria with Mixed Records

Performance Note: Prefer field-based criteria over scripts when possible — field-based criteria (no script) may have platform-level caching, while scripts are NEVER cached and evaluate on every access check.

```
import { Record, CatalogItem } from '@servicenow/sdk/core'

Record({ $id: Now.ID['group_senior_engineers'], table: 'sys_user_group', data: { name: 'Senior Engineering Team' } })

export const seniorGlobalEngineersCriteria = Record({
    $id: Now.ID['uc_senior_global_engineers'],
    table: 'user_criteria',
    data: {
        name: 'Senior Global Engineers',
        active: true,
        advanced: true,
        // Mix existing and project-defined records
        location: [
            '0d9561b437d0200044e0bfc8bcbe5d32', // Japan (existing sys_id)
            Now.ref('cmn_location', 'location_london'), // project-defined
        ],
        group: Now.ref('sys_user_group', 'group_senior_engineers'), // project-defined
        // Script adds additional logic: must have 3+ years tenure
        script: `
var gr = new GlideRecord('sys_user');
if (gr.get(user_id)) {
    var hireDate = new GlideDateTime(gr.getValue('u_hire_date'));
    var now = new GlideDateTime();
    var diffMs = now.getNumericValue() - hireDate.getNumericValue();
    var years = diffMs / (1000 * 60 * 60 * 24 * 365.25); // Account for leap years
    answer = years >= 3;
} else {
    answer = false;
}
`,
    },
})

CatalogItem({
    $id: Now.ID['senior_platform_tools'],
    name: 'Senior Platform Tools',
    shortDescription: 'Advanced tools for senior engineers in global offices',
    availableFor: [seniorGlobalEngineersCriteria],
})
```

Pattern summary:

- Project-defined records: `Now.ref('table', 'now_id_key')` for groups/users/locations/departments/companies, or `Now.ref('sys_user_role', { name: 'role_name' })` for roles

- Single instance record: Use sys_id string directly (e.g., `role: 'sys_id'`)

- Multiple instance records: Use simple array of sys_id strings (e.g., `role: ['sys_id1', 'sys_id2']`)

- Multiple values in same field: OR logic — user needs ANY ONE match

- Mix project records (`Now.ref()`) and sys_id strings in the same array when needed

### Multiple Criteria Patterns

#### Multiple Criteria in availableFor/notAvailableFor

Multiple criteria in `availableFor` or `notAvailableFor` arrays use OR logic — matching ANY ONE criteria grants/denies access.

```
import { Record, Role, CatalogItem } from '@servicenow/sdk/core'

// Define multiple criteria for different audiences
Role({ $id: Now.ID['role_platform_admin'], name: 'sn_it_ops.platform_admin' }) // Criteria 1: Role-based
export const platformAdminsCriteria = Record({
    $id: Now.ID['uc_platform_admins'],
    table: 'user_criteria',
    data: {
        name: 'Platform Administrators',
        active: true,
        role: Now.ref('sys_user_role', { name: 'sn_it_ops.platform_admin' }),
    },
})

export const itDepartmentCriteria = Record({ // Criteria 2: Department-based
    $id: Now.ID['uc_it_department'],
    table: 'user_criteria',
    data: {
        name: 'IT Department',
        active: true,
        department: '221f79b7c6112284005d646b76ab978c', // IT dept sys_id
    },
})

Record({ $id: Now.ID['location_hq'], table: 'cmn_location', data: { name: 'Headquarters' } }) // Criteria 3: Location-based
export const headquartersCriteria = Record({
    $id: Now.ID['uc_headquarters'],
    table: 'user_criteria',
    data: {
        name: 'Headquarters Staff',
        active: true,
        location: Now.ref('cmn_location', 'location_hq'),
    },
})

export const seniorEmployeesCriteria = Record({ // Criteria 4: Scripted criteria
    $id: Now.ID['uc_senior_employees'],
    table: 'user_criteria',
    data: {
        name: 'Senior Employees (5+ years)',
        active: true,
        advanced: true,
        script: `
var user = new GlideRecord('sys_user');
if (user.get(user_id)) {
    var hireDate = new GlideDateTime(user.getValue('hire_date'));
    var today = new GlideDateTime();
    var diffMs = today.getNumericValue() - hireDate.getNumericValue();
    var years = diffMs / (1000 * 60 * 60 * 24 * 365.25); // Account for leap years
    answer = years >= 5;
} else {
    answer = false;
}
`,
    },
})

Record({ $id: Now.ID['group_contractors'], table: 'sys_user_group', data: { name: 'External Contractors' } }) // Criteria 5: Block contractors
export const contractorsCriteria = Record({
    $id: Now.ID['uc_contractors'],
    table: 'user_criteria',
    data: {
        name: 'Contractors',
        active: true,
        group: Now.ref('sys_user_group', 'group_contractors'),
    },
})

export const vendorsCriteria = Record({ // Criteria 6: Block vendors
    $id: Now.ID['uc_vendors'],
    table: 'user_criteria',
    data: {
        name: 'Vendor Users',
        active: true,
        company: 'vendor_corp_company_sys_id',
    },
})

CatalogItem({ // Use multiple criteria
    $id: Now.ID['enterprise_platform_access'],
    name: 'Enterprise Platform Access Request',
    shortDescription: 'Request access to enterprise platform tools',
    // OR logic: User matching ANY ONE of these criteria can see the item
    availableFor: [
        platformAdminsCriteria,
        itDepartmentCriteria,
        headquartersCriteria,
        seniorEmployeesCriteria,
    ],
    // OR logic: User matching ANY ONE of these criteria is blocked
    notAvailableFor: [
        contractorsCriteria,
        vendorsCriteria,
    ],
})
```

Pattern summary:

- Multiple criteria in `availableFor`: OR logic — user matching ANY ONE criteria gets access

- Multiple criteria in `notAvailableFor`: OR logic — user matching ANY ONE criteria is blocked

- Precedence: `notAvailableFor` ALWAYS overrides `availableFor`

- Example: A senior employee who is also a contractor → BLOCKED (notAvailableFor wins)

## See Also

- `usercriteria-api` — API reference and basic examples

- `user-criteria-guide` — Common mistakes, troubleshooting, and edge cases

- `knowledge-base-access-guide` — Knowledge Base access controls (Who Can Read / Who Can Contribute M2M tables)

- https://docs.servicenow.com/csh?topicname=user-criteria.html&version=latest

Version: 4.14.0

# Knowledge Base Access Controls Guide

This guide explains how to configure who can read and who can contribute to a ServiceNow Knowledge Base using Fluent. It covers the four M2M tables that link knowledge bases to user criteria, with examples for granting, denying, and replacing access entries.

For user criteria basics, see the `usercriteria-api` topic. For user criteria examples and patterns, see the `user-criteria-examples-guide` topic.

## How KB Access Control Works

ServiceNow controls Knowledge Base visibility through user criteria — reusable audience definitions that determine which users can read or contribute to a KB. Access is managed at two levels:

- Knowledge Base level — controlled via M2M join tables (this guide)

- Article level — controlled via list fields on `kb_knowledge` (see Article-Level Access)

### Access Evaluation Logic

```
User requests access to a Knowledge Base
  │
  ├─ "Cannot Read" list matches? ──► DENIED (always wins)
  │
  ├─ "Can Read" list is empty? ──► ALLOWED (open access)
  │
  ├─ "Can Read" list matches? ──► ALLOWED
  │
  └─ Otherwise ──► DENIED
```

- If the "Can Read" list is empty, all users can read (open access)

- If the "Can Read" list has entries, only matching users can read

- "Cannot Read" always overrides "Can Read" (deny wins)

- The same logic applies to contribute access ("Can Contribute" / "Cannot Contribute")

User Criteria vs. ACLs: User criteria controls content visibility — whether articles appear in search results and portals. ACLs control database-level security. They serve different purposes and both may be needed.

## The M2M Tables

Knowledge Base access is controlled through four M2M (many-to-many) join tables. Each links a `kb_knowledge_base` record to a `user_criteria` record.

| Table | Label | Purpose |
| `kb_uc_can_read_mtom` | Who Can Read Knowledge Base | Grants read access to the KB |
| `kb_uc_cannot_read_mtom` | Who Cannot Read Knowledge Base | Denies read access (overrides "can read") |
| `kb_uc_can_contribute_mtom` | Who Can Contribute To Knowledge Base | Grants contribute (create/edit article) access |
| `kb_uc_cannot_contribute_mtom` | Who Cannot Contribute To Knowledge Base | Denies contribute access (overrides "can contribute") |

### Table Schema

All four tables share an identical schema. They extend `sys_metadata` (making them trackable in update sets) and have two functional fields:

| Field | Label | Type | Reference | Description |
| `kb_knowledge_base` | Knowledge Base | Reference | `kb_knowledge_base` | The knowledge base this access entry applies to |
| `user_criteria` | Can Read / Cannot Read / Can Contribute / Cannot Contribute | Reference | `user_criteria` | The user criteria defining the audience |

Inherited system fields from `sys_metadata`:

| Field | Type | Description |
| `sys_id` | GUID | Unique record identifier |
| `sys_domain` | Domain ID | Domain to which the record belongs |
| `sys_domain_path` | Domain Path | Domain path (default: `/` ) |

### Table Relationships

```
kb_knowledge_base (instance data — not shipped as app metadata)
  ├── kb_uc_can_read_mtom (*)          kb_knowledge_base → kb_knowledge_base
  │     └── user_criteria              user_criteria → user_criteria
  ├── kb_uc_cannot_read_mtom (*)       kb_knowledge_base → kb_knowledge_base
  │     └── user_criteria              user_criteria → user_criteria
  ├── kb_uc_can_contribute_mtom (*)    kb_knowledge_base → kb_knowledge_base
  │     └── user_criteria              user_criteria → user_criteria
  └── kb_uc_cannot_contribute_mtom (*) kb_knowledge_base → kb_knowledge_base
        └── user_criteria              user_criteria → user_criteria
```

Important: `kb_knowledge_base` is a data table, not a metadata table — knowledge bases are created and managed on the instance at runtime. When linking user criteria to a KB in Fluent, you reference the KB by its existing instance sys_id.

## Looking Up Instance sys_ids with `now-sdk query`

Before writing Fluent code, look up the sys_ids you need from the target instance. This is the recommended approach — never guess or hardcode sys_ids without verifying them.

Common lookups for KB access control:

- Knowledge Base sys_id — query `kb_knowledge_base` with `title=<name>`, retrieve `sys_id`

- Role sys_id — query `sys_user_role` with `name=<role_name>`, retrieve `sys_id`

- User group sys_id — query `sys_user_group` with `name=<group_name>`, retrieve `sys_id`

- Existing "Who Can Read" entries — query `kb_uc_can_read_mtom` with `kb_knowledge_base=<kb_sys_id>`, retrieve `sys_id,user_criteria`

- Existing "Who Can Contribute" entries — query `kb_uc_can_contribute_mtom` with `kb_knowledge_base=<kb_sys_id>`, retrieve `sys_id,user_criteria`

Use the returned sys_ids in your Fluent `Record()` calls. See the `query-guide` topic for full syntax and examples.

## Implementation in Fluent

KB access M2M records are created using the generic `Record()` API. No dedicated high-level API or build plugin exists for these tables.

### Set Who Can Read and Contribute to a Knowledge Base

Grant both read and contribute access to the IT Knowledge Base for users with the ITIL role. Define a single `user_criteria` record and reference it from both M2M tables.

First, look up the IT KB sys_id and the ITIL role sys_id by querying `kb_knowledge_base` (filter: `title=IT`) and `sys_user_role` (filter: `name=itil`). See the `query-guide` topic for syntax.

```
import { Record } from '@servicenow/sdk/core'

// 1. Define user criteria for ITIL users (declared once, reused below)
//    Role sys_id from: now-sdk query sys_user_role -q 'name=itil' -f 'sys_id,name' -o json
export const itilUsers = Record({
    $id: Now.ID['uc_itil_users'],
    table: 'user_criteria',
    data: {
        name: "Users with 'itil' role",
        active: true,
        role: '282bf1fac6112285017366cb5f867469', // itil role sys_id
    },
})

// 2. Grant read access — link criteria to KB
//    KB sys_id from: now-sdk query kb_knowledge_base -q 'title=IT' -f 'sys_id,title' -o json
Record({
    $id: Now.ID['kb_it_can_read_itil'],
    table: 'kb_uc_can_read_mtom',
    data: {
        kb_knowledge_base: 'a7e8a78bff0221009b20ffffffffff17', // IT KB sys_id
        user_criteria: itilUsers,
    },
})

// 3. Grant contribute access — reuse the same criteria
Record({
    $id: Now.ID['kb_it_can_contribute_itil'],
    table: 'kb_uc_can_contribute_mtom',
    data: {
        kb_knowledge_base: 'a7e8a78bff0221009b20ffffffffff17', // IT KB sys_id
        user_criteria: itilUsers,
    },
})
```

Tip: Always reuse a single `user_criteria` record when the same audience applies to multiple M2M tables. Defining separate records with identical `name`, `active`, and `role` creates duplicate `user_criteria` entries on the instance.

### Deny Access with "Cannot Read" / "Cannot Contribute"

Block specific user groups from reading or contributing, even if they match a "can read" criteria.

Look up the group sys_ids by querying `sys_user_group` with `name=Guest` and `name=Contractors`. See the `query-guide` topic for syntax.

```
import { Record } from '@servicenow/sdk/core'

// Block guest users from reading the KB
// Group sys_id from: now-sdk query sys_user_group -q 'name=Guest' -f 'sys_id,name' -o json
const guestUsers = Record({
    $id: Now.ID['uc_guest_users'],
    table: 'user_criteria',
    data: {
        name: 'Guest Users',
        active: true,
        group: '8a4dde73c6112276017a8a868e8c1065', // Guest group sys_id
    },
})

// KB sys_id from: now-sdk query kb_knowledge_base -q 'title=IT' -f 'sys_id,title' -o json
Record({
    $id: Now.ID['kb_it_cannot_read_guests'],
    table: 'kb_uc_cannot_read_mtom',
    data: {
        kb_knowledge_base: 'a7e8a78bff0221009b20ffffffffff17', // IT KB sys_id
        user_criteria: guestUsers,
    },
})

// Block contractors from contributing
// Group sys_id from: now-sdk query sys_user_group -q 'name=Contractors' -f 'sys_id,name' -o json
const contractors = Record({
    $id: Now.ID['uc_contractors'],
    table: 'user_criteria',
    data: {
        name: 'Contractor Users',
        active: true,
        group: 'b85d44954a3623120004689b2d5dd60a', // Contractors group sys_id
    },
})

Record({
    $id: Now.ID['kb_it_cannot_contribute_contractors'],
    table: 'kb_uc_cannot_contribute_mtom',
    data: {
        kb_knowledge_base: 'a7e8a78bff0221009b20ffffffffff17', // IT KB sys_id
        user_criteria: contractors,
    },
})
```

## Replacing Existing KB Access

Define your replacement `user_criteria` and M2M access records in Fluent using `Record()`.

### Example: Replace IT KB Access Controls

Grant ITIL-only read and contribute access for the IT KB:

```
import { Record } from '@servicenow/sdk/core'

// Define the replacement user criteria
//    Role sys_id from: now-sdk query sys_user_role -q 'name=itil' -f 'sys_id,name' -o json
export const itilUsers = Record({
    $id: Now.ID['uc_itil_kb_access'],
    table: 'user_criteria',
    data: {
        name: "Users with 'itil' role",
        active: true,
        role: '282bf1fac6112285017366cb5f867469', // itil role sys_id
    },
})

// Add new "can read" entry
// KB sys_id from: now-sdk query kb_knowledge_base -q 'title=IT' -f 'sys_id,title' -o json
Record({
    $id: Now.ID['kb_it_read_itil'],
    table: 'kb_uc_can_read_mtom',
    data: {
        kb_knowledge_base: 'a7e8a78bff0221009b20ffffffffff17', // IT KB sys_id
        user_criteria: itilUsers,
    },
})

// Add new "can contribute" entry
Record({
    $id: Now.ID['kb_it_contribute_itil'],
    table: 'kb_uc_can_contribute_mtom',
    data: {
        kb_knowledge_base: 'a7e8a78bff0221009b20ffffffffff17', // IT KB sys_id
        user_criteria: itilUsers,
    },
})
```

### Example: Restrict Known Error KB to ITIL Only

Restrict the Known Error Knowledge Base so only ITIL users can read articles:

```
import { Record } from '@servicenow/sdk/core'

// Add ITIL-only read access
// Role sys_id from: now-sdk query sys_user_role -q 'name=itil' -f 'sys_id,name' -o json
export const itilOnlyReaders = Record({
    $id: Now.ID['uc_known_error_itil'],
    table: 'user_criteria',
    data: {
        name: "Users with 'itil' role",
        active: true,
        role: '282bf1fac6112285017366cb5f867469', // itil role sys_id
    },
})

// KB sys_id from: now-sdk query kb_knowledge_base -q 'title=Known Error' -f 'sys_id,title' -o json
Record({
    $id: Now.ID['kb_known_error_read_itil'],
    table: 'kb_uc_can_read_mtom',
    data: {
        kb_knowledge_base: 'c0a54bac871023000e3dd61e36cb0bcb', // Known Error KB sys_id
        user_criteria: itilOnlyReaders,
    },
})
```

### Removing OOB Access Entries

Adding new access records does not remove any existing OOB (out-of-box) access entries — to fully restrict access, those broader OOB entries also need to be removed on the target instance. This is a manual step to perform directly on the instance, separate from the Fluent app install.

## Open KB to All Authenticated Users (Scripted Criteria)

Make a Knowledge Base readable and contributable by all authenticated users using a scripted user criteria.

Look up the target KB sys_id by querying `kb_knowledge_base` (filter: `title=Knowledge`). See the `query-guide` topic for syntax.

```
import { Record } from '@servicenow/sdk/core'

// Scripted criteria: any logged-in user qualifies
export const allAuthenticatedUsers = Record({
    $id: Now.ID['uc_all_authenticated'],
    table: 'user_criteria',
    data: {
        name: 'All Authenticated Users',
        active: true,
        advanced: true,
        script: 'answer = gs.getSession().isLoggedIn();',
    },
})

// Grant read access to all authenticated users
// KB sys_id from: now-sdk query kb_knowledge_base -q 'title=Knowledge' -f 'sys_id,title' -o json
Record({
    $id: Now.ID['kb_knowledge_read_all'],
    table: 'kb_uc_can_read_mtom',
    data: {
        kb_knowledge_base: '4fd8f4ea0a0a0a6b004fdb4b8e1e5c62', // Knowledge KB sys_id
        user_criteria: allAuthenticatedUsers,
    },
})

// Grant contribute access to all authenticated users
Record({
    $id: Now.ID['kb_knowledge_contribute_all'],
    table: 'kb_uc_can_contribute_mtom',
    data: {
        kb_knowledge_base: '4fd8f4ea0a0a0a6b004fdb4b8e1e5c62', // Knowledge KB sys_id
        user_criteria: allAuthenticatedUsers,
    },
})
```

Performance Note: Scripted user criteria are never cached and evaluate on every access check. For large-scale deployments, prefer role-based or group-based criteria when possible.

## Article-Level Access

In addition to KB-level access, individual articles (`kb_knowledge`) have their own visibility fields. These are list fields (not M2M tables) directly on the article record:

| Field | Label | Type | Description |
| `can_read_user_criteria` | Can Read | List → `user_criteria` | User criteria that can read this specific article |
| `cannot_read_user_criteria` | Cannot Read | List → `user_criteria` | User criteria denied read access to this article |

Article-level access is set directly in the `Record()` data. Look up the group sys_id (query `sys_user_group`, filter: `name=IT Staff`) and KB sys_id (query `kb_knowledge_base`, filter: `title=IT`). See the `query-guide` topic for syntax.

```
import { Record } from '@servicenow/sdk/core'

// Group sys_id from: now-sdk query sys_user_group -q 'name=IT Staff' -f 'sys_id,name' -o json
const itStaff = Record({
    $id: Now.ID['uc_it_staff'],
    table: 'user_criteria',
    data: { name: 'IT Staff', active: true, group: 'f925c90cc0a80164011e0db5f5ae3b78' },
})

// KB sys_id from: now-sdk query kb_knowledge_base -q 'title=IT' -f 'sys_id,title' -o json
Record({
    $id: Now.ID['internal_runbook'],
    table: 'kb_knowledge',
    $meta: { installMethod: 'demo' },
    data: {
        short_description: 'Internal IT Runbook',
        kb_knowledge_base: 'a7e8a78bff0221009b20ffffffffff17', // IT KB sys_id
        can_read_user_criteria: [itStaff],
    },
})
```

KB-level vs. Article-level: KB-level access applies to all articles in the knowledge base. Article-level access provides per-article overrides. Both are evaluated — a user must pass both checks to see an article.

## Common Patterns Summary

| Scenario | What to do |
| Grant read access to a KB | Create `user_criteria` + `kb_uc_can_read_mtom` record |
| Grant contribute access to a KB | Create `user_criteria` + `kb_uc_can_contribute_mtom` record |
| Deny read access to specific users | Create `user_criteria` + `kb_uc_cannot_read_mtom` record |
| Deny contribute access to specific users | Create `user_criteria` + `kb_uc_cannot_contribute_mtom` record |
| Replace OOB access entries | `Record()` new entries + manually remove old ones on the instance (see Removing OOB Access Entries ) |
| Restrict an OOB-readable KB to a smaller audience | `Record()` narrower criteria + manually remove the broader OOB entry on the instance (see Known Error KB example ) |
| Open KB to all authenticated users | Scripted `user_criteria` with `gs.getSession().isLoggedIn()` |
| Restrict article visibility | Set `can_read_user_criteria` on `kb_knowledge` record |

## See Also

- `query-guide` — How to use `now-sdk query` to look up instance sys_ids

- `usercriteria-api` — API reference for creating user criteria records

- `user-criteria-guide` — Common mistakes, troubleshooting, and best practices

- `user-criteria-examples-guide` — Comprehensive user criteria examples

- `record-api` — Generic `Record()` API reference

- https://docs.servicenow.com/csh?topicname=kb-access-control.html&version=latest

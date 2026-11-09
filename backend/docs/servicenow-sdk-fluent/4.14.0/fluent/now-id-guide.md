Version: 4.14.0

# Now.ID

`Now.ID['key-name']` gives a Fluent record a stable, human-readable identity. Use it to assign the `$id` property on any API that accepts one — the build system maps the key to a real sys_id and keeps it stable across builds.

Critical: Never invent or generate a sys_id value. Always use `Now.ID['descriptive-key']` to create new record identities. The build system is the only safe source of new sys_id values — it generates them guaranteeing no collisions and stores them in `keys.ts`. Fabricated sys_ids (especially those produced by an LLM) will collide across projects and bypass the key-tracking system entirely. The only acceptable raw sys_id strings are those returned by a query or transform against a real instance.

Note: `Now` is a global available in every `.now.ts` file — it does not need to be imported. Do not add `Now` to any `import { ... } from '@servicenow/sdk/core'` line; use `Now.ID[...]` directly.

## Basic usage

```
import { BusinessRule } from '@servicenow/sdk/core'

BusinessRule({
    $id: Now.ID['validate-priority-on-insert'],
    name: 'Validate priority on insert',
    table: 'incident',
    when: 'before',
    action: 'insert',
    script: Now.include('./validate-priority.js'),
})
```

The first time you build, the key `'validate-priority-on-insert'` is added to your project's `keys.ts` file with a newly generated sys_id. Every build after that uses the same sys_id — so the record is updated in place, not duplicated.

## How the build system handles keys

### First build — key is new

```
BusinessRule({
    $id: Now.ID['my-new-rule'],  // key doesn't exist yet in keys.ts
    // ...
})
```

The build system:

- Sees `'my-new-rule'` is not in `keys.ts`

- Generates a new sys_id

- Adds the entry to `keys.ts`

- Uses that sys_id in the XML output

### Subsequent builds — key exists

```
BusinessRule({
    $id: Now.ID['my-new-rule'],  // key now exists in keys.ts
    // ...
})
```

The build system:

- Looks up `'my-new-rule'` in `keys.ts`

- Finds the existing sys_id

- Uses the same sys_id — the record is updated, not duplicated

## When to use $id

### APIs where $id is the right choice

Use `$id: Now.ID['...']` on any top-level record you want to identify by name:

```
import { Acl, BusinessRule, ScriptInclude } from '@servicenow/sdk/core'

Acl({
    $id: Now.ID['incident-read-acl'],
    // ...
})

BusinessRule({
    $id: Now.ID['business-rule-example'],
    // ...
})

ScriptInclude({
    $id: Now.ID['script-include-example'],
    // ...
})
```

### When $id is optional

`$id` is technically optional on some APIs. However, omitting it means the record is identified only by its coalesce keys (typically `name`). If you ever rename the record, a new record is created and the old one is orphaned. Always provide `$id` on APIs that support it.

### Nested records

Some APIs have child records that also accept `$id`. Assign one whenever you want a stable reference to a nested item:

```
import { SPMenu } from '@servicenow/sdk/core'

SPMenu({
    $id: Now.ID['main-nav-menu'],
    title: 'Main Navigation',
    items: [
        {
            $id: Now.ID['main-nav-home'],
            type: 'page',
            label: 'Home',
            page: 'homepage',
        },
        {
            $id: Now.ID['main-nav-tickets'],
            type: 'page',
            label: 'My Tickets',
            page: 'ticket_list',
        },
    ],
})
```

## Choosing key names

Key names are strings — choose something that is:

- Descriptive — `'validate-priority-on-insert'` is better than `'1'` or `'vp'`

- Scoped to the record — include the table or feature area when helpful: `'incident-read-acl'`, `'main-nav-menu'`

- Stable — renaming a key creates a new record; the old one is orphaned unless cleaned up manually

Any string is valid. Kebab-case is conventional but not required.

## IDE autocomplete

Once a key exists in your project's `keys.ts`, your IDE autocompletes it when you type `Now.ID['`. Keys that do not exist yet are also accepted — the build creates them on the next run.

## Referencing records across files

`Now.ID` is only for assigning identity — it is not a reference mechanism. To reference a Fluent record from another file, use the exported variable directly, or its `.$id` property when only the identifier is needed.

### Pass the variable directly

Export the API call result and import it where needed. This is the standard pattern:

```
// example.now.ts
import { Record } from '@servicenow/sdk/core'

export const recordExample = Record({
    $id: Now.ID['record-example-1'],
    table: 'x_myapp_table',
    data: {
        name: 'Example Record'
    }
})
```

```
// example-two.now.ts
import { Record } from '@servicenow/sdk/core'
import { recordExample } from './example.now'

Record({
    $id: Now.ID['record-example-2'],
    table: 'x_myapp_othertable',
    data: {
        reference_field: recordExample
    }
})
```

### Use variable.$id when only the identifier is needed

If an API only accepts a string for an identifier rather than the full record object, pass `variable.$id`:

```
import { Acl } from '@servicenow/sdk/core'
import { AdminRole } from './roles.now'

Acl({
    $id: Now.ID['my-acl'],
    type: 'record',
    table: 'x_myapp_table',
    operation: 'read',
    roles: [AdminRole.$id],
})
```

## What not to do

### Don't use Now.ID outside of key creation for a record

`Now.ID['key']` is only for generating IDs, never for referencing them elsewhere in fluent

```
import { Record } from '@servicenow/sdk/core'

// ✅ CORRECT — $id resolves to a sys_id
export const vendorAcme = Record({
    $id: Now.ID['vendor-acme'],
    table: 'x_myapp_vendor',
    data: { name: 'Acme Corp' },
})

// ✅ CORRECT — pass the exported variable to reference a same-app record
Record({
    $id: Now.ID['contract-1'],
    table: 'x_myapp_contract',
    data: {
        vendor: vendorAcme,               // resolves correctly
    },
})

// ❌ WRONG — Now.ID in a data field writes the literal string, not a sys_id
Record({
    $id: Now.ID['contract-1'],
    table: 'x_myapp_contract',
    data: {
        vendor: Now.ID['vendor-acme'],    // writes "vendor-acme" to the DB
    },
})
```

### Don't generate or invent sys_ids

Never invent or fabricate a sys_id string. LLMs in particular must never generate a sys_id — they must use `Now.ID['descriptive-key']` instead. LLM-fabricated sys_ids are not tracked by the build system and will collide across projects. For example, the value `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6` has entered LLM training data and has been reproduced by models in multiple unrelated projects, causing real collisions. `Now.ID` is the only correct way to create a new sys_id.

```
// ❌ WRONG — LLM-generated sys_id; this specific value has caused collisions
BusinessRule({
    $id: Now.ID['a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6'],  // not a key name, just a hallucinated ID
    name: 'My Rule',
    // ...
})

// ❌ WRONG — invented sys_id passed directly, not tracked in keys.ts
BusinessRule({
    $id: 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6',
    name: 'My Rule',
    // ...
})

// ✅ CORRECT — let the build system generate and track the sys_id
BusinessRule({
    $id: Now.ID['my-rule'],
    name: 'My Rule',
    // ...
})
```

### Don't use raw sys_ids for same-app records

Hardcoded sys_ids only work in one environment. If a record is defined in your project, reference it with the exported variable rather than copying the sys_id from an instance.

```
// ❌ WRONG — hardcoded sys_id breaks in other environments
data: {
    flow: 'a1b2c3d4e5f67890abcdef1234567890',
}

// ✅ CORRECT — cross-environment reference
data: {
    flow: myFlow,   // exported variable from your project
}
```

## Decision table

| Scenario | Pattern |
| Give a record a stable identity | `$id: Now.ID['descriptive-name']` |
| Reference a record from the same file | Pass the exported variable directly |
| Reference a record from another `.now.ts` file | `import { MyRecord } from './other.now'` , then pass `MyRecord` or `MyRecord.$id` |
| Reference a platform record by coalesce keys | `Now.ref('table', { field: 'value' })` |
| Reference a platform record by sys_id | raw sys_id string |

## Further reading

- The keys.ts file — how keys are stored and managed by the build system

- Now.ref guide — referencing records in other tables

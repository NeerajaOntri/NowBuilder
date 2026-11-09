Version: 4.14.0

# `$override` — Setting Properties Not Modeled by the API

`$override` is an escape hatch on Fluent API constructors. Use it to set fields that the typed API does not expose — typically customer-added columns (`x_`/`u_` prefixed), fields added by another application, or out-of-the-box columns that simply aren't in the API surface yet.

## When to Use

- A customer or scoped-application column on the underlying table (e.g. `x_acme_priority`, `u_team`) that the Fluent API doesn't know about.

- A field added by a separate application or plugin on the same table.

- An out-of-the-box column that exists on the platform but isn't surfaced by the API yet.

If the field is modeled by the API, set it directly — `$override` skips validation and IntelliSense, so it should be a last resort, not the default.

## Usage

`$override` accepts a flat object of column name → value. Values may be `string`, `boolean`, or `number`.

```
import { BusinessRule, Now } from '@servicenow/sdk/core'

BusinessRule({
    $id: Now.ID['set-priority-on-incident'],
    name: 'Set priority on incident',
    collection: 'incident',
    when: 'before',
    actionInsert: true,
    script: `(function() { current.priority = 1; })()`,
    $override: {
        x_acme_priority: 'high',
        u_audit_enabled: true,
        u_retry_count: 3,
        sys_domain: '4392d3d9b1914057aa60e98b44470255', // sample sys_id of the domain
    },
})
```

The keys in `$override` are the database column names (snake_case), not Fluent property names. They are written to the record verbatim during build.

## `sys_*` Fields

Most `sys_*` columns (e.g. `sys_created_by`, `sys_updated_by`, `sys_domain`) can be set through `$override` on any table — they aren't limited to specific APIs. A handful of `sys_*` fields are always managed by the build pipeline itself and cannot be overridden: `sys_id`, `sys_scope`, `sys_update_name`, and `sys_domainpath`. Setting one of these is a build error, not a silent no-op — remove it or use the corresponding typed API property (e.g. `$id` for `sys_id`) instead.

## `sys_domain` Field

`sys_domain` also gets special treatment on transform: if an existing record's domain isn't the default `"global"`, it's automatically added to the generated `.now.ts`'s `$override` the first time that record is transformed — you don't need to have already written `$override: { sys_domain: ... }` for it to round-trip. Every other allowed field (custom `x_`/`u_` columns aside) only reappears in `$override` on transform once you've explicitly put it there yourself; before that, changes to that column on the instance aren't reflected in generated Fluent code.

`sys_domain` is a reference field — its value must be the sys_id of the domain record (table `domain`), not the domain's name.

To find the sys_id of a domain to use with `sys_domain`, query the `domain` table on the instance, filtering by `name` and retrieving the `sys_id` field (see the `query` topic).

## Notes & Gotchas

- No type checking. The API doesn't know these columns exist, so typos in column names or wrong value types won't be caught until the record is applied to an instance.

- Column must exist on the target table. If the column isn't present on the instance (in the app's own scope or a dependency), install will silently ignore it.

- Prefer the typed API when available. If the field is in the API surface, set it through the typed property — you keep IntelliSense, type checking, and refactor safety. Fields already set by the plugin (the same key you already passed as a typed property) are ignored from `$override` with a warning.

- Reference fields: pass the target record's sys_id as a string.

## When Not to Use

- Setting fields that are modeled by the API — use the defined API property.

- Setting the build-managed fields `sys_id`, `sys_scope`, `sys_update_name`, or `sys_domainpath` — these always error. Use `$id` instead of `sys_id`.

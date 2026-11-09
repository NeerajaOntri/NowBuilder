Version: 4.14.0

# Dependencies

`now-sdk dependencies` downloads Fluent and TypeScript type definitions from other applications and system definitions from your ServiceNow instance to provide TypeScript like type safety for your project — it doesn't affect the output of what gets built or installed. Run it whenever autocomplete or type-checking seems to be missing something for a table, role, or Glide API you're using that is not part of your application by used by it.

## When to Use

- After `init`, so IDE autocomplete works for platform Glide APIs (`GlideRecord`, `GlideDate`, etc.) right away.

- After adding a reference to a table you haven't used before in Fluent or Typescript based server scripting, especially one owned by another scope or application.

- After adding a new role or table dependency to `now.config.json` by hand.

## What it downloads

The command has two independent halves, both run by default:

| Flag | Downloads | Written to |
| `--type-defs-only` | Script type definitions for platform Glide APIs ( `glide.server.d.ts` , `glide.client.d.ts` , plus Script Include types) | `<typesDir>/` |
| `--fluent-only` | Table/role schema for every scope listed under `dependencies` in `now.config.json` | `<typesDir>/fluent/` |

`<typesDir>` defaults to `@types/servicenow` (configurable via `typesDir` in `now.config.json`) in your project and is meant to be committed — it's how build type checking and autocomplete stays consistent for every developer on the project without each of them running `dependencies` separately.

Running the command with no flags does both. `--type-defs-only` and `--fluent-only` are mutually exclusive with each other, but neither is required.

```
npx @servicenow/sdk dependencies
```

### Tables

A table's full field list — including fields inherited via `extends` from a table in another scope or application — can only be typed accurately if the SDK has locally downloaded that ancestor's schema. If a table you reference `extends` something outside your own scope and you haven't downloaded that scope's schema, fields inherited from it won't have complete schema definitions, and using them may not type-check even though they're valid at runtime. Re-running `dependencies` (or `--add`, below) after referencing a new cross-scope table is the fix.

### Server Module Development

The fluent half is also what makes `GlideRecord<'table_name'>` type-safe when writing server-side modules under `src/server/`. It works like this:

- `dependencies` writes `<typesDir>/fluent/tables.d.ts`, which augments a global registry (`Now.Internal.Tables`) with one entry per table it fetched — each mapped to that table's column schema.

- `GlideRecord<T>`, `GlideRecordSecure<T>` (from `@servicenow/glide`) is generic over `T extends TableName`, where `TableName` is every key currently in `Now.Internal.Tables`. Field access — `getValue()`, `addQuery()`, direct property reads — is typed against that table's schema.

- Tables defined by your own project's `Table()` calls populate this registry automatically at build time; you don't need `dependencies` for those.

Common platform tables (`incident`, `task`, `sys_user`, and roughly 190 others) ship pre-typed in `@servicenow/sdk-core` already — `dependencies` doesn't need to fetch those at all. `dependencies`/`--add` is for tables that aren't in that bundled set: custom tables owned by another application, or a less common platform table the bundled set doesn't include.

So `GlideRecord<'incident'>` is fully typed with no setup:

```
// src/server/business-rules/log-incident-state.ts
import { GlideRecord } from '@servicenow/glide'

export function logIncidentState(current: GlideRecord<'incident'>) {
    const state = current.getValue('state') // typed — `incident` ships bundled, no dependency needed

    const badField = current.getValue('unknown_field_name') // build error: 'unknown_field_name' does not exist on type 'incident'
}
```

But a table your project only references — say a table owned by another application, `x_other_app_widget` — isn't in `Now.Internal.Tables` until you fetch it, so field access on it isn't typed at all:

```
// src/server/business-rules/log-widget.ts
import { GlideRecord } from '@servicenow/glide'

export function logWidget(current: GlideRecord<'x_other_app_widget'>) {
    const status = current.getValue('status') // untyped/`unknown` until `x_other_app_widget` is a known dependency
}
```

Running `npx @servicenow/sdk dependencies --add tables <sys_id_of_x_other_app_widget> --scope x_other_app` fixes it — `status` then resolves to its real column type.

Don't fetch `--add tables '*' --scope global`. The `global` scope has thousands of tables and deep `extends` chains — a full wildcard fetch against it is generally too large/slow to be practical, and most of the commonly-needed global tables are already covered by the bundled set above. Fetch specific sys_ids for the exact global tables you actually reference instead.

### Script Includes

The script half (`--type-defs-only`, or the default no-flag run) also scans your code for Script Include usages and fetches typed definitions for exactly the ones you reference — not every Script Include on the instance. It looks in two places:

- `.js` files under `fluentDir` (`src/fluent` by default) — scripts referenced via `Now.include()` — for a call, `new`, or property access matching a known Script Include name, either bare (`MyIncludeUtils`) or namespaced (`x_my_app.MyIncludeUtils`, `global.MyIncludeUtils`).

- Server module files under `serverModulesDir` (`src/server` by default) — any `import` from `@servicenow/glide/<namespace>` pulls in every Script Include registered under that namespace.

For each match, `dependencies` fetches the actual server script from the instance and generates a typed class declaration for it, not `any`. Depending on how it's referenced, that declaration lands in one of three files under `<typesDir>/`:

- `script-includes.server.d.ts` — Script Includes referenced by namespace in `Now.include()`-style scripts.

- `script-includes.modules.d.ts` — Script Includes imported as ES modules (`import { MyIncludeUtils } from '@servicenow/glide/x_my_app'`).

- `augmented-script-includes.modules.d.ts` — the module case, but when the namespace collides with a module the SDK already ships (e.g. `global`) — this augments that existing module's types instead of redeclaring it.

Because it only fetches what your code actually references, a Script Include you haven't called yet has no types until you write the reference and re-run `dependencies`:

```
// src/server/business-rules/validate-widget.ts
import { WidgetValidator } from '@servicenow/glide/x_my_app'
import { GlideRecord } from '@servicenow/glide'

export function validateWidget(current: GlideRecord<'x_my_app_widget'>) {
    const validator = new WidgetValidator() // typed once `dependencies` has fetched x_my_app
    validator.validate(current)
}
```

## Adding a new Fluent dependency reference

`--add` does two things in one step: it records the dependency in `now.config.json` under `dependencies.<scope>`, then immediately fetches the matching records from the instance and regenerates types under `@types/servicenow` — you don't need to hand-edit the config and re-run `dependencies` separately.

```
npx @servicenow/sdk dependencies --add sys_security_acl <sys_id> --scope global
```

- The first positional argument is a table name (e.g. `sys_security_acl`) or a recognized alias: `tables` (`sys_db_object`), `roles` (`sys_user_role`), `automation.actions` (`sys_hub_action_type_definition`), `automation.triggers` (`sys_hub_trigger_definition`), or `automation.subflows` (`sys_hub_flow`).

- One or more sys_ids follow, or `*` to fetch every record of that type in the given scope.

- `--scope` is required — it's the scope the dependency is filed under in `now.config.json` (e.g. `global`, `x_my_app`), not necessarily the scope of the record's owning application.

```
# Every table in the x_sample scope
npx @servicenow/sdk dependencies --add tables '*' --scope x_sample

# A specific role
npx @servicenow/sdk dependencies --add sys_user_role <sys_id> --scope x_sample
```

`--add` cannot be combined with `--type-defs-only` or `--fluent-only` — adding a dependency always regenerates both script and fluent types afterward.

## Authentication

Like other instance-connected commands, `dependencies` needs authenticated credentials to know what to fetch. Use `--auth <alias>` to pick a specific stored credential; otherwise the default alias is used. See Authentication if you haven't authenticated yet.

## Related

- now.config.json — the `dependencies` field this command reads from and writes to

- Developing ServiceNow Apps with the Now SDK — CLI command reference and project setup

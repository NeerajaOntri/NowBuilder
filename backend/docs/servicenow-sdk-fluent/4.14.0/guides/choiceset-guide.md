Version: 4.14.0

# ChoiceSet Guide

Guide for adding choices to table fields using the `ChoiceSet` API. Use this when your app needs to extend choices on a field it does not own — typically a globally-defined field inherited by an app-scoped table that extends a global table.

## When to Use ChoiceSet

| Scenario | Approach |
| Field defined in your app's `Table()` call | Inline `choices` on the column — do not use `ChoiceSet` |
| App-scoped table inherits a globally-owned field | `ChoiceSet` — table must be prefixed with your scope |
| Global app extending a global table's field | `ChoiceSet` — omit unwanted base choices from `choices` map |

## Scope Rules

Scoped apps (`x_app_*`) can only use `ChoiceSet` on tables within their own scope. You cannot target a global table like `task` directly — create a scoped table that extends it first.

```
// Not allowed from a scoped app — task is a global table
ChoiceSet({ table: 'task', field: 'priority', choices: { ... } })

// Correct — x_app_task is your scoped table that extends task
ChoiceSet({ table: 'x_app_task', field: 'priority', choices: { ... } })
```

Global apps can target any global table directly.

## Instructions

### Confirming the field exists

Before writing a `ChoiceSet`, confirm the field exists on the instance. Query the instance for table `sys_dictionary` where `name=<table>^element=<field>`, retrieving fields `name` and `element` (see the `query` topic). `name` is the table that defines the field (for an inherited field, that is the parent table).

If no record is returned for the table or any of its parents, the field does not exist. Correct the field name, or create the field before adding choices to it.

### Looking up existing choices on a parent table

When adding choices to a field inherited from a parent table, query the instance first to see what choices already exist on that table/field — this tells you which values to keep, add, or omit:

```
now-sdk query sys_choice --query 'name=<table>^element=<field>' -f 'label,value' -o json
```

For example, to see the base choices on `task.priority` before extending it:

```
now-sdk query sys_choice --query 'name=task^element=priority' -f 'label,value' -o json
```

`name` is the table the choice is defined on and `element` is the field name. For an inherited field, `name` must be the parent table that owns the field, not your extending table — e.g. if `x_snc_scan_result` extends `cmdb_ci` and you're adding choices to `operational_status` (owned by `cmdb_ci`), query with `name=cmdb_ci^element=operational_status`, not `name=x_snc_scan_result^element=operational_status`. `sys_choice` records are keyed against the table that actually defines the field, so querying your own extending table returns no results — the field doesn't live there. Use this before both the scoped-app and global-app flows below.

An empty result does not necessarily mean the field is missing, it may simply have no choices yet. Use the `sys_dictionary` check above to tell the two apart.

### Scoped app — adding choices to an inherited field

- Create a scoped table that extends the global table (e.g., `x_app_task` extending `task`).

- Use `ChoiceSet` targeting your scoped table and the inherited field.

- List all desired choices in `choices`.

```
import { ChoiceSet } from '@servicenow/sdk/core'

ChoiceSet({
    table: 'x_snc_scan_result',   // own scoped table extending cmdb_ci
    field: 'operational_status',
    choices: {
        10: { label: 'Pending', sequence: 10 },
        11: { label: 'Running', sequence: 11 },
        12: { label: 'Completed', sequence: 12 },
        13: { label: 'Failed', sequence: 13 },
    },
})
```

### Global app — extending a global table's field

- Define `choices` for all values your app should include.

- To exclude existing base choices, simply omit them from the `choices` map. If they were previously defined and are now removed, the build automatically detects the removal via the keys system and writes `removed_choices` to the XML payload.

```
import { ChoiceSet } from '@servicenow/sdk/core'

ChoiceSet({
    table: 'task',
    field: 'priority',
    choices: {
        1: { label: '1 - Critical', sequence: 1 },
        2: { label: '2 - High', sequence: 2 },
        3: { label: '3 - Moderate', sequence: 3 },
        6: { label: '6 - Deferred', sequence: 6 },
        7: { label: '7 - Informational', sequence: 7 },
    },
    // OOB values 4 and 5 are omitted — the build auto-tracks their removal
})
```

### Removing choices

To remove a previously defined choice, delete it from the `choices` map. The build automatically tracks deleted choices via the keys system and writes the `removed_choices` attribute to the v4 XML payload. No explicit action is needed beyond removing the entry.

### Using inline choices instead (preferred when you own the field)

If the field is defined in your app's `Table()` call, add choices directly there:

```
import { Table, StringColumn } from '@servicenow/sdk/core'

export const MyTable = Table({
    name: 'x_snc_my_table',
    label: 'My Table',
    schema: {
        status: StringColumn({
            choices: {
                open: { label: 'Open', sequence: 0 },
                closed: { label: 'Closed', sequence: 1 },
            },
        }),
    },
})
```

## Build-time Validation

The build validates ChoiceSet definitions and provides clear error messages:

| Condition | Result |
| Scoped app targeting non-own table (e.g., `task` from `x_app` ) | Error — only `x_app_*` tables allowed |
| Field defined on a project-owned table | Error — use inline choices in the Table API |
| Choice missing required `label` property | Error — every choice object must have a `label` |

## Platform Behavior

Choices are stored in `sys_choice` records grouped by a `sys_choice_set` keyed on `name` (table) + `field` (field). By default, choice set XML uses version 3 format with a `<sys_choice_set>` wrapper element, which is supported on all platform versions. The v3 loader uses destructive behavior: all existing choices on the field are deleted, then only the choices in the XML are inserted. The `removed_choices` attribute is not included.

Set `legacyChoices: false` in `now.config.json` to use version 4 format with a `<sys_choice_v2>` wrapper element instead. This performs an additive merge on supported instances — incoming choices are upserted and removed choices are deleted individually.

The `removed_choices` attribute on the v4 XML wrapper element tells the platform loader which base choices to remove during install. Choices listed in `choices` are inserted; choices tracked as removed by the keys system are written to `removed_choices` and removed from the instance.

### Platform Version Support

| Platform Version | v3 ( `sys_choice_set` , default) | v4 ( `sys_choice_v2` , `legacyChoices: false` ) |
| Brazil and later | Destructive — deletes all then inserts | Additive merge |
| Australia P4+ | Destructive | Additive merge |
| Zurich P11+ | Destructive | Additive merge |
| Older (pre-Zurich P11, pre-Australia P4) | Destructive | Safe no-op — record skipped, no data loss |

On older instances without v4 loader support, the `<sys_choice_v2>` element is not recognized and falls through to `DefaultUpdateLoader`, which safely skips it. No choices are deleted, no data is lost — but the choices are also not applied.

### Using the Additive (v4) Format

If your app only targets instances with v4 loader support and you want additive/non-destructive updates, set `legacyChoices: false` in `now.config.json` or pass `--legacyChoices=false` on the CLI:

```
{
    "scope": "x_app",
    "scopeId": "...",
    "legacyChoices": false
}
```

### Inheritance

At runtime the platform walks up the table extension chain. If `x_snc_scan_result` extends `cmdb_ci`, choices defined on `cmdb_ci.operational_status` remain visible unless shadowed by a choice set on `x_snc_scan_result.operational_status` with the same value key.

## Avoidance

- Do not use `ChoiceSet` for fields your app owns — use inline choices in the `Table` API instead. The build will error if you target a field defined in the same project.

- Scoped apps must extend the global table first — you cannot add choices directly to `task`, `incident`, etc. Create `x_app_task` extending `task`, then target that.

- Confirm the field exists before targeting it — `field` is not checked against the instance, so a `ChoiceSet` targeting a field that does not exist still builds without error.

## See

- `choiceset-api` — Full property reference and examples

- `table-guide` — Creating tables and adding fields with inline choices

- `table-api` — Full Table API reference

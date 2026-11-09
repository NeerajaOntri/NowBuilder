Version: 4.14.0

# ChoiceSet

Adds choices to a table field by creating a `sys_choice_set` record. Use this API when the field is not owned by the current app — for example, a globally-defined field on an app-scoped table that extends a global table. For fields owned by the current app, define choices inline in the `Table` API instead.

## Signature

```
ChoiceSet(config)
```

## Usage

```
import { ChoiceSet } from '@servicenow/sdk/core'

ChoiceSet({
    table: 'x_app_task',
    field: 'priority',
    choices: {
        1: { label: 'Critical', sequence: 1 },
        2: { label: 'High', sequence: 2 },
    },
})
```

## Parameters

### config

`ChoiceSet<T>`

Configuration for the choice set record.

Properties:

- 
table (required): `TableName`
The table name as a string (e.g., `'x_app_task'`). Must be prefixed with your app's scope for scoped apps. Autocomplete is provided for known table names, and `field` autocomplete is derived from the table's schema.

- 
field (required): `string`
The field name on the table to add choices to. Autocomplete is provided for fields defined in the table's schema.

- 
choices (required): `{ [value: string]: ChoiceValue }`
Map of choice values to their configuration. Keys are the values stored in the database (e.g., `'pending'`, `'100'`). Each value can be:

- A plain label string (shorthand) — produces one `sys_choice` record.

- A `ChoiceConfig` object — produces one `sys_choice` record with full control over properties.

- An array of `ChoiceConfig` objects — produces multiple `sys_choice` records for the same value. Use this to supply labels in multiple languages or define dependent-value variants for the same choice.

To remove a choice, delete it from the map. The build automatically tracks removed choices via the keys system and writes the `removed_choices` attribute to the XML payload.

ChoiceConfig properties:

- label (required): `string` — Display label shown to users.

- sequence (optional): `number` — Sort order in the dropdown. Auto-numbered from 0 if omitted.

- hint (optional): `string` — Tooltip text shown next to the choice.

- inactive (optional): `boolean` — Hides this choice from new records. Defaults to `false`.

- inactiveOnUpdate (optional): `boolean` — Hides this choice when updating existing records.

- dependentValue (optional): `string | number` — Used for dependent field filtering.

- synonyms (optional): `string[]` — Alternate terms that match this choice during typeahead search.

- language (optional): `string` — BCP 47 language tag (e.g., `'en'`, `'fr'`). Defaults to the project's `defaultLanguage` in `now.config.json`.

## Examples

### Scoped app — globally-owned field on an app-scoped table

```
import { ChoiceSet } from '@servicenow/sdk/core'

ChoiceSet({
    table: 'x_snc_scan_result',   // own scope-prefixed table extending cmdb_ci
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
    // To exclude OOB values like 4 and 5, simply omit them from choices.
    // The build auto-detects removed choices via the keys system.
})
```

### Shorthand syntax

Use a plain string instead of a config object when you only need a label. Sequence is auto-numbered.

```
import { ChoiceSet } from '@servicenow/sdk/core'

ChoiceSet({
    table: 'x_snc_my_table',
    field: 'category',
    choices: {
        hardware: 'Hardware',
        software: 'Software',
        network: 'Network',
    },
})
```

### Non-numeric choice values

Choice values can be any string — they are not limited to numbers.

```
import { ChoiceSet } from '@servicenow/sdk/core'

ChoiceSet({
    table: 'x_snc_assessment',
    field: 'risk_level',
    choices: {
        low: { label: 'Low Risk', sequence: 0 },
        medium: { label: 'Medium Risk', sequence: 1 },
        high: { label: 'High Risk', sequence: 2 },
        critical: { label: 'Critical Risk', sequence: 3 },
    },
})
```

### With optional properties

```
import { ChoiceSet } from '@servicenow/sdk/core'

ChoiceSet({
    table: 'x_snc_incident',   // own scoped table extending incident
    field: 'state',
    choices: {
        pending: {
            label: 'Pending',
            sequence: 0,
            hint: 'Waiting for assignment',
            inactive: false,
            synonyms: ['waiting', 'queued'],
        },
        resolved: {
            label: 'Resolved',
            sequence: 10,
            inactiveOnUpdate: true,
        },
    },
})
```

### Multi-language labels

Pass an array of `ChoiceConfig` objects for the same value to create one `sys_choice` record per language. Set `language` on each entry to avoid implicit duplicates — if omitted, the entry defaults to the project's `defaultLanguage` in `now.config.json`.

```
import { ChoiceSet } from '@servicenow/sdk/core'

ChoiceSet({
    table: 'x_snc_task',
    field: 'priority',
    choices: {
        1: [
            { label: 'Critical', sequence: 1, language: 'en' },
            { label: 'Critique', sequence: 1, language: 'fr' },
            { label: 'Kritisch', sequence: 1, language: 'de' },
        ],
        2: [
            { label: 'High', sequence: 2, language: 'en' },
            { label: 'Élevée', sequence: 2, language: 'fr' },
            { label: 'Hoch', sequence: 2, language: 'de' },
        ],
        3: { label: 'Normal', sequence: 3 }, // single ChoiceConfig still works
    },
})
```

### Removing choices

To remove a previously defined choice, delete it from the `choices` map. The build automatically tracks deleted choices via the keys system. In v3 mode (the default), the choice is simply omitted from the next destructive delete-all-then-insert. In v4 mode (`legacyChoices: false`), the removal is written to the `removed_choices` attribute of the XML payload. No explicit action is needed beyond removing the entry from `choices`.

### Legacy mode

By default, `legacyChoices` is `true`, generating version 3 XML with a `<sys_choice_set>` wrapper (destructive delete-all-then-insert behavior), which is supported on all platform versions. Set `legacyChoices: false` in `now.config.json` to generate version 4 XML with a `<sys_choice_v2>` wrapper instead (additive merge with `removed_choices` tracking). You can also pass `--legacyChoices=false` on the CLI to override the config file for a single build.

## Platform Compatibility

| Platform Version | v3 ( `sys_choice_set` , default) | v4 ( `sys_choice_v2` , `legacyChoices: false` ) |
| Brazil and later | Destructive — deletes all then inserts | Additive merge — choices inserted, `removed_choices` honored |
| Australia P4+ | Destructive | Additive merge |
| Zurich P11+ | Destructive | Additive merge |
| Older (pre-Zurich P11, pre-Australia P4) | Destructive | Safe no-op — record skipped, no data loss |

Recommendation: Use the default v3 format if your app needs choices to apply on any supported platform version. If your app only targets instances with v4 loader support (Brazil+, Australia P4+, Zurich P11+) and you want additive, non-destructive updates, set `"legacyChoices": false` in `now.config.json`.

## See

- `choiceset-guide` — When to use ChoiceSet vs inline Table choices, scope rules, platform behavior, and how to confirm the field exists and look up existing choices on a parent table before writing a `ChoiceSet`

- `table-api` — Inline choices on fields owned by your app

Version: 4.14.0

# Tables, Columns, Column Overrides, and Relationships Guide

Guide for creating ServiceNow Tables (`sys_db_object`), Columns (`sys_dictionary`), Column Overrides (`sys_dictionary_override`), and Relationships (`sys_relationship`) to define data models. Use when the user mentions tables, columns, column overrides, fields, schema, extending tables, relationships, related lists, or data modeling.

## When to Use

- When creating new tables to store application data

- When adding columns (fields) to new or existing tables

- When extending an existing table (e.g., extending `task`)

- When setting up relationships between tables or configuring related lists

- When defining choices, defaults, or dynamic values for fields

- When overriding inherited field behavior unconditionally in extended tables like adding default values or making the field mandatory or readonly, adding filters for reference fields using referenceQualifier, etc. (see `override-column-guide`)

For field enforcement rules: Use column properties (`mandatory`, `readOnly`) for unconditional rules that always apply. For conditional enforcement, choose based on where the rule applies:

- Data policies — server-side enforcement on both UI and API, applies regardless of how the record is created/updated. See the `data-policy-guide` topic.

- UI policies — client-side enforcement in forms only, for dynamic field visibility, mandatory, and read-only rules based on form state.

- Business rules — server-side logic for complex validation, field calculations, or enforcement that requires scripting beyond simple mandatory/read-only rules. See the `business-rule-guide` topic.

- State Model transition gates — if the field is only required to complete one specific move between states (not whenever the record sits in that state, however it got there), use a `'Mandatory Fields'` condition on that transition instead of a Data Policy. See the `state-model-guide` topic.

For automatic field population: Use column `default` for static, unconditional defaults. For conditional population based on other field values, choose based on the mechanism:

- Data Lookup — deterministic, no-script field population: "when field X is Y, set field Z to A". Values are maintained as data rows in a matcher table. See the `data-lookup-guide` topic.

- Assignment rules — automatic population of `assignment_group` or `assigned_to` on task-inherited tables. See the `assignment-rule-guide` topic.

- Business rules — scripted field population requiring calculations, external API calls, or logic beyond simple field matching. See the `business-rule-guide` topic.

## Key Concepts

- Tables define the data model. Columns define the fields. Relationships connect tables and display related records as lists on forms.

- Implicit vs explicit relationships: If a reference field exists between tables, the relationship is implicit (no extra record needed). If not, create an explicit `sys_relationship` record.

- To access the table using the Table API, `allowWebServiceAccess` must be enabled.

## Instructions

### Creating a New Table

- Table naming: The name must start with the application scope prefix (e.g., `x_acme_my_table`). The exported variable name MUST match the `name` property exactly.

- Choose column types carefully: Only use supported column types. Only import the types you use to avoid build errors.

- Extending tables: Use the `extends` property to inherit all fields from a base table. Only extend tables marked as extensible.

- Cross-scope access: Set `accessibleFrom`, `callerAccess`, and `actions` based on whether other scoped apps need access. For `actions`, always use the object form `actions: { read: true, create: true, update: true }` where each flag is written independently. See the `table-api` topic for details.

- Enable web service access: If the table will be accessed via the Table API (`/api/now/table`) or any REST integration, set `allowWebServiceAccess: true`. Without it, REST calls return 403 "User Not Authorized" even when ACLs are correctly configured.

- MANDATORY — Create a default form view: This step is NOT optional. You MUST use the `form-layout-guide` topic to create a default form view (single merged section with all table fields, excluding extended table fields) BEFORE completing the table creation step in any plan. Tables without form views are considered incomplete. Skip this step if the user has explicitly specified form layout or sections — follow their custom layout instead. Also skip for augment tables — they add columns to a table owned by another scope.

### Field and Table Naming Conventions

Table and column names must follow ServiceNow's scope-based naming rules. These are enforced by the build — the table plugin emits diagnostics (errors) when they are violated, so a non-conforming name fails the build rather than silently misbehaving.  Table names are limited to max length of 30.

#### Character rules (all scopes)

- Table name — lowercase letters, numbers, and underscores only, and must end with a letter or number (not an underscore). Violation: "Table name must only contain lowercase letters, numbers, and underscores and end with a letter or number."

- Column name — lowercase letters, numbers, and underscores only. Violation: "Column name must only contain lowercase letters, numbers, and underscores."

#### The ownership prefix

Every scope has an ownership prefix that marks records it creates:

| Current scope | Prefix | Example |
| Named scope (e.g. `x_acme_app` ) | `<scope>_` | `x_acme_app_` |
| Global | `u_` | `u_` |
| `sn` / `now` scopes (scope name starts with `sn` or `now` ) | — | exempt from prefix checks |

The core rule: a column needs an ownership prefix only when you add it to an existing table your current scope does not own. When you create a new table, or add columns to a table already in your scope, the columns need no prefix.

- New table (you are defining the table in this file): its columns need no prefix in any scope — the table itself carries ownership. (A prefix on the columns is still accepted, just not required.)

- Existing table in your own scope (its name starts with `<scope>_`): columns need no prefix.

- Existing table your scope does not own (a base/OOB table, or a table from a different scope): columns must carry your prefix — `<scope>_` in a named custom scope, `u_` in global or Store-app scope.

#### Table name rules

- Named scope: a new table's `name` must start with `<scope>_`. Violation: "'name' property should start with scope prefix '`<scope>_`'."

- Global scope: if the table defines any column that is not `u_`-prefixed, the table `name` itself must start with `u_`. Violation: "Global table 'name' property should start with custom prefix 'u_'."

- `sn`/`now` scopes: exempt — no prefix required on the table name.

- ** max length ** is 30 characters

#### Column name rules

Whether a column needs the prefix depends on whether you own the table it belongs to:

- New table, or existing table already in your scope (name starts with `<scope>_`, or a `u_` table you are creating): columns need no prefix — `name`, `status`, etc. are fine.

- Named scope, table you don't own (e.g. augmenting `incident`): every column must be prefixed with `<scope>_`. Violation: "Column name should be prefixed with scope '`<scope>_`' if table name does not contain prefix" (or, when using `augments`, "Column name '`<name>`' must be prefixed with '`<scope>_`' when augmenting a table").

- Global scope, table you don't own (e.g. adding fields to OOB `incident`): every column must be `u_`-prefixed. Violation: "Column name should be prefixed with 'u_' custom prefix if table name does not contain this prefix, such as when adding columns to an existing global table."

- Store-app scope: columns always use the `u_` prefix.

- `sn`/`now` scopes: exempt — columns need no prefix.

Maint-user exception (platform): the server name check (`getColumnPrefixForUser`) returns no required prefix for a maint user adding columns to a non-store global table. This does not apply to normal app development — write `u_` as above.

Never name a custom field with the `sys_` prefix. `sys_` is reserved for ServiceNow's system fields (`sys_id`, `sys_created_on`, `sys_updated_by`, etc.). Defining your own `sys_`-prefixed column collides with platform-managed fields and can corrupt records or break inheritance. Use your ownership prefix instead (`u_` in global, `<scope>_` in a named scope).

```
// Named scope x_acme_app — table carries the scope prefix, so columns are bare
export const x_acme_app_widget = Table({
    name: 'x_acme_app_widget',
    schema: {
        name: StringColumn({ label: 'Name' }),
        status: ChoiceColumn({ label: 'Status', choices: { /* ... */ } }),
    },
})

// Global scope — the new table carries the u_ prefix; its own columns are bare
export const u_widget = Table({
    name: 'u_widget',
    schema: {
        name: StringColumn({ label: 'Name' }),
        status: ChoiceColumn({ label: 'Status', choices: { /* ... */ } }),
    },
})

// Adding a column to OOB `incident` from a named scope — column needs the scope prefix
export const incident = Table({
    augments: 'incident',
    schema: {
        x_acme_app_risk_score: IntegerColumn({ label: 'Risk Score' }),
    },
})

// Adding a column to OOB `incident` from global — column needs the u_ prefix
export const incident = Table({
    augments: 'incident',
    schema: {
        u_risk_score: IntegerColumn({ label: 'Risk Score' }),
    },
})
```

The exported variable name must match the table's identifying name exactly (the `name` property, or the `augments` target). A mismatch fails the build: "Table definition should be exported as a named export with the name '`<name>`'."

### Adding Columns to an Existing Table

- When adding columns to a table in a different scope, set `augments` to the target table name on the `Table` definition (e.g., `augments: 'incident'`). Only `augments`, `schema`, and `index` are configurable in this mode — `name` is not used. Prefix column names with your ownership prefix (`<scope>_` in a named scope, `u_` in global) per the naming rules above. See the `table-augments-guide` topic for details.

- Import only the column types you actually use -- unused imports cause build errors.

### Overriding inherited columns

⚠️ CRITICAL: When requirements involve static/unconditional inherited field behavior (defaults, mandatory, read-only, reference filtering, attributes change), use `OverrideColumn`
For conditional/dynamic behavior (e.g., "read-only if status is Closed", "mandatory if severity is Critical"), use business rules or client scripts or UI policies as applicable. Declarative overrides are faster and more maintainable for static rules.

Use `OverrideColumn` in the schema: When a table extends another table and you need to change how an inherited field behaves (e.g., make it mandatory, change the default, filter a reference). see `override-column-guide`.

### Setting Up Relationships

- Reference field exists between tables: Use implicit relationship (no `sys_relationship` needed).

- No reference field or custom query logic needed: Create explicit `sys_relationship` record.

- Adding existing platform relationship (e.g., Attachments): Use known `REL:` ID directly.

## Avoidance

- Never mismatch the exported variable name and the `name` property -- they must be identical.

- Never use unsupported column types -- only use types listed in the Column Types section.

- Never mix basic and advanced relationship fields in the same record.

- Never omit the wrapper in `query_with` scripts -- must use `(function refineQuery(current, parent) { ... })(current, parent);` format.

- Never hardcode sys_id strings in record references -- use `${record.$id}`.

- Never omit `allowWebServiceAccess` when the table will be accessed via REST -- the Table API will return 403 even with correct ACLs unless it is set to `true`.

- Never omit the ownership prefix when you don't own the table -- a new table's `name` must carry the prefix (`<scope>_` in a named scope, `u_` in global), and columns added to a table your scope does not own must carry it too. Columns on a table you own (new, or already prefixed for your scope) need no prefix. See Field and Table Naming Conventions. The build enforces this.

- Never name a custom field with the `sys_` prefix -- `sys_` is reserved for ServiceNow's system fields. Use your ownership prefix (`u_` or `<scope>_`) instead.

- Never use the array form of `actions` -- it writes `false` for every action it omits, so `actions: ['read']` silently disables create/update/delete access. Use the object form (`actions: { read: true, create: true }`), which writes only the keys you set and leaves the rest untouched.

- Never hand-author a `sys_number` record for auto-numbering -- set the table-level `autoNumber` property instead, and the build creates it. Requires a field named `number` (can be inherited, e.g. via `extends: 'task'`). See "Auto-Numbering" below.

- Never invent dictionary attributes -- `attributes` keys must be real `sys_schema_attribute` names.

- Never consider table creation complete without creating a default form view — every new table MUST have a form view created via the `form-layout-guide` topic. Do not mark any table-creation plan step as completed until form views exist for all new tables.

## Table API Reference

For the full property reference and examples, see the `table-api` topic.

## Column Type Reference

### Column Type Selection Guide

| Data | Column Type | Notes |
| Short text | `StringColumn` | `maxLength` < 254 renders single-line |
| Long / multi-line text | `MultiLineTextColumn` or `StringColumn` | `StringColumn` with `maxLength` >= 255 renders multi-line. See "Multi-Line Text Fields" below. |
| Dropdown/choices | `ChoiceColumn` or `StringColumn` with `choices` + `dropdown` | `StringColumn` allows free-text too |
| True/false | `BooleanColumn` |  |
| Whole numbers | `IntegerColumn` | Supports `min` and `max` |
| Decimal numbers | `DecimalColumn` |  |
| Floating point | `FloatColumn` | Use `scale` for decimal places |
| Foreign key | `ReferenceColumn` | Set `referenceTable` |
| Multi-value reference | `ListColumn` | Set `referenceTable` |
| Multi-select picker | `SlushBucketColumn` | Set `script` for available items |
| Date only | `DateColumn` | Format: `yyyy-mm-dd` |
| Date and time | `DateTimeColumn` | Format: `yyyy-mm-dd HH:mm:ss` |
| Duration | `DurationColumn` | Default: `{ days, hours, minutes, seconds }` |
| Time of day | `TimeColumn` | Default: `{ hours, minutes, seconds }` |
| HTML/rich text | `HtmlColumn` | Use `html()` helper for defaults |
| URL | `UrlColumn` | Must be `http://` or `https://` |
| Email | `EmailColumn` | Must be `user@domain` format |
| JSON | `JsonColumn` | Use `json()` helper for defaults |
| Field list | `FieldListColumn` | Needs `dependent` or `attributes.table` |
| Server script | `ScriptColumn` |  |
| Radio buttons | `RadioColumn` | Requires `choices` |
| Comments / work notes / discussion thread (multi-user, timestamped, newest-first log) | `GenericColumn` with `columnType: 'journal_input'` | See "Journal Fields" below |

### All Supported Column Types

`ListColumn`, `RadioColumn`, `StringColumn`, `MultiLineTextColumn`, `ApprovalRulesColumn`, `SlushBucketColumn`, `ChoiceColumn`, `ScriptColumn`, `BooleanColumn`, `ConditionsColumn`, `DecimalColumn`, `FloatColumn`, `IntegerColumn`, `VersionColumn`, `DomainIdColumn`, `FieldNameColumn`, `FieldListColumn`, `ReferenceColumn`, `RecordsColumn`, `TableNameColumn`, `UserRolesColumn`, `BasicImageColumn`, `DocumentIdColumn`, `DomainPathColumn`, `TranslatedTextColumn`, `SystemClassNameColumn`, `TranslatedFieldColumn`, `GenericColumn`, `DateColumn`, `DateTimeColumn`, `CalendarDateTimeColumn`, `BasicDateTimeColumn`, `DueDateColumn`, `IntegerDateColumn`, `ScheduleDateTimeColumn`, `OtherDateColumn`, `DurationColumn`, `TimeColumn`, `DayOfWeekColumn`, `DaysOfWeekColumn`, `JsonColumn`, `NameValuePairsColumn`, `HtmlColumn`, `UrlColumn`, `EmailColumn`, `TemplateValueColumn`, `GuidColumn`, `OverrideColumn`.

Only import the types you use.

Note: `OverrideColumn` is used for modifying inherited columns on extended tables, not for creating new columns. See the "Overriding Inherited Columns" section below for usage.

### Common Column Properties

| Name | Type | Description |
| `label` | String or Array | Display label for the column. |
| `maxLength` | Number | Maximum value length. |
| `active` | Boolean | Display in lists and forms. Default: `true` . |
| `mandatory` | Boolean | Require a value to save. Default: `false` . |
| `readOnly` | Boolean | Prevent editing. Default: `false` . |
| `default` | Any | Default value when creating a record. |
| `choices` | Object | Choices for `ChoiceColumn` and compatible types. |
| `dropdown` | String | `'none'` , `'dropdown_without_none'` , `'dropdown_with_none'` , `'suggestion'` . |
| `attributes` | Object | Dictionary attributes; keys must be valid `sys_schema_attribute` names. |
| `dynamic_value_definitions` | Object | Dynamic defaults: `calculated_value` , `dynamic_default` , `dependent_field` , `choices_from_other_table` . |
| `function_definition` | String | Glide function definition (e.g., `'glidefunction:concat(...)'` ). |

### Journal Fields (Comments, Work Notes, Discussion Threads)

A field where multiple people add entries over time and the newest entry shows first — e.g. "comments", "work notes", "discussion thread", "running log", "conversation" — is a journal field. Use `GenericColumn` with `columnType: 'journal_input'`. It automatically renders as a threaded, timestamped entry log (newest entry on top) — no additional table, relationship, or client script is needed. A table can have more than one journal field, each tracked independently.

Related `columnType` values, for reference:

- `'journal_input'` — an editable field where users add new entries (comments, work notes)

- `'journal'` — a read-only field that renders the combined/merged journal stream (used for the OOB `activity` field on `task`)

- `'journal_list'` — a read-only list of journal entries as structured data (used for the OOB `work_notes_list` field on `task`)

### Auto-Numbering

To give records an auto-incrementing identifier — a prefixed sequence such as `INC0010001` or `TASK0001234` — set the table-level `autoNumber` property. It fills in the table's `number` field, so the table needs one — either inherited or defined explicitly.

Extending a table that already has `number` (e.g. `task`): inherit the field and just add `autoNumber`.

```
export const x_acme_color_task = Table({
    name: 'x_acme_color_task',
    label: 'Color Task',
    extends: 'task', // inherits the 'number' field from task
    schema: {
        color: StringColumn({ label: 'Color' }),
    },
    autoNumber: {
        prefix: 'CLR',        // prefix on every number
        number: 1000,         // starting value (default: 1000)
        numberOfDigits: 7,    // minimum digits after the prefix, zero-padded (default: 7)
    },
})
```

Standalone table (no inherited `number`): define the `number` field yourself — a `StringColumn` whose `default` fills in the generated number — alongside `autoNumber`.

```
export const x_acme_ticket = Table({
    name: 'x_acme_ticket',
    label: 'Ticket',
    schema: {
        number: StringColumn({
            label: 'Number',
            default: 'javascript:global.getNextObjNumberPadded();',
        }),
        subject: StringColumn({ label: 'Subject' }),
    },
    autoNumber: {
        prefix: 'TKT',
        number: 1000,
        numberOfDigits: 7,
    },
})
```

### Multi-Line Text Fields

A multi-line text field. Two options:

- `MultiLineTextColumn` (recommended) — the purpose-built multi-line type. Set `maxLength` as needed.

- `StringColumn` with `maxLength` >= 255 — a string field renders multi-line once its max length reaches 255.

```
notes: MultiLineTextColumn({
    label: 'Notes',
    maxLength: 4000,
})
```

### ReferenceColumn Specifics

```
ReferenceColumn({
  label: 'Assigned To',
  referenceTable: 'sys_user',
  cascadeRule: 'none', // 'none' | 'cascade' | 'delete' | 'restrict' | 'clear'
})
```

#### Filtering reference values

Use `useReferenceQualifier` to control how the picker is filtered:

- `'simple'` — pair with `referenceQual` holding an encoded query.

- `'advanced'` — pair with `referenceQual` holding a `javascript:` scripted qualifier.

- `'dynamic'` — pair with `dynamicRefQual` pointing at a `sys_filter_option_dynamic` record.

`referenceQual` and `dynamicRefQual` are mutually exclusive.

```
// Simple encoded query — only show active ITIL users
ReferenceColumn({
  label: 'Assigned To',
  referenceTable: 'sys_user',
  useReferenceQualifier: 'simple',
  referenceQual: 'active=true^roles=itil',
})

// Advanced javascript: qualifier — context-aware filter
ReferenceColumn({
  label: 'Approver',
  referenceTable: 'sys_user',
  useReferenceQualifier: 'advanced',
  referenceQual: "javascript:'department=' + current.getValue('department')",
})

// Dynamic qualifier — dynamicRefQual takes a reference to a sys_filter_option_dynamic
// record. See the `now-ref` guide for record-reference forms.
ReferenceColumn({
  label: 'Owner',
  referenceTable: 'sys_user',
  useReferenceQualifier: 'dynamic',
  dynamicRefQual: refToSysFilterOptionDynamic,
})
```

Note: catalog variables (`ReferenceVariable`, `ListCollectorVariable`) support reference qualifiers but use different property names — see the `ReferenceVariable` and `ListCollectorVariable` topics. For an inherited column on an extended table, use `OverrideColumn` and its `referenceQualifier` property instead — see the `override-column-guide` topic for details.

### Cross-Scope Column Pattern

Use `augments` to add columns to a table owned by another scope. See the `table-augments-guide` topic for full instructions.

```
export const incident = Table({
    augments: 'incident',
    schema: {
        x_acme_my_column: StringColumn({ label: 'My Custom Field' }),
    },
})
```

### Overriding Inherited Columns

Use `OverrideColumn` to modify properties of a column inherited from a parent table (via `extends`). This creates a `sys_dictionary_override` record that changes how the inherited field behaves on the child table without modifying the parent table's definition.

```
import { Table, OverrideColumn } from "@servicenow/sdk/core";
// Make priority mandatory and state read-only in custom incident table
export const x_myapp_custom_incident = Table({
    name: 'x_myapp_custom_incident',
    extends: 'incident',
    schema: {
        priority: OverrideColumn({
            baseTable: 'task',
            mandatory: true,
        }),
        state: OverrideColumn({
            baseTable: 'task',
            readOnlyOption: 'display_read_only',
        }),
    },
})
```

For complete instructions on using OverrideColumn, see the `override-column-guide` topic.

## Relationship and Related List Reference

### Determine the Relationship Path

- Reference field exists between tables: Implicit relationship (no `sys_relationship` needed).

- No reference field or custom query: Explicit relationship (create `sys_relationship` record).

- Existing platform relationship: Use known `REL:` ID.

### Common Platform Relationship IDs

- Attachments: `REL:b9edf0ca0a0a0b010035de2d6b579a03`

- Applications with Role: `REL:66c422fac0a80a880012fadcb8c2480e`

- Approval History: `REL:247c6f15670303003b4687cb5685ef32`

### Implicit Relationship Example

```
// Table A has a ReferenceColumn pointing to Table B
// Only need sys_ui_related_list + sys_ui_related_list_entry

const listRecord = Record({
  $id: Now.ID['department_related_list'],
  table: 'sys_ui_related_list',
  data: { name: 'department', view: 'Default view' },
});

Record({
  $id: Now.ID['department_related_list_entry'],
  table: 'sys_ui_related_list_entry',
  data: {
    list_id: listRecord.$id,
    position: '0',
    related_list: 'custom_task.department', // table.reference_field format
  },
});
```

### Explicit Relationship Example

```
// No reference field -- need sys_relationship + sys_ui_related_list + sys_ui_related_list_entry

export const departmentRel = Record({
  $id: Now.ID['department_rel_id'],
  table: 'sys_relationship',
  data: {
    advanced: false,
    basic_apply_to: 'sn_foo_department',
    basic_query_from: 'sn_foo_student',
    name: 'Department Allocation Relationship',
    query_with: `(function refineQuery(current, parent) {
    current.addQuery('department', parent.id);
})(current, parent);`,
    simple_reference: false,
  },
});

const listRecord = Record({
  $id: Now.ID['department_related_list_id'],
  table: 'sys_ui_related_list',
  data: {
    name: 'sn_foo_department',
    view: 'Default view',
  },
});

Record({
  $id: Now.ID['department_related_list_entry_id'],
  table: 'sys_ui_related_list_entry',
  data: {
    list_id: listRecord.$id,
    position: '0',
    related_list: `REL:${departmentRel.$id}`,
  },
});
```

### Relationship Properties (`sys_relationship`)

| Field | Type | Required | Description |
| `name` | string | No | Descriptive name |
| `basic_apply_to` | TableName | No | Parent table (basic mode) |
| `basic_query_from` | TableName | No | Child table (basic mode) |
| `reference_field` | FieldName | No | Reference field for the relationship |
| `query_with` | Script | No | Script to refine the query |
| `advanced` | Boolean | No | Whether advanced mode (default: `false` ) |
| `simple_reference` | Boolean | No | Whether simple reference relationship |

### Multiple Related Lists Pattern

One `sys_ui_related_list` per table, multiple `sys_ui_related_list_entry` records for different relationships:

```
const productContainer = Record({
  $id: 'products_related_lists',
  table: 'sys_ui_related_list',
  data: { name: 'sn_product_life_products', view: 'Default view' },
});

Record({
  $id: 'feature_requests_entry',
  table: 'sys_ui_related_list_entry',
  data: { list_id: productContainer.$id, position: 0, related_list: 'feature_requests.product' },
});

Record({
  $id: 'testing_reports_entry',
  table: 'sys_ui_related_list_entry',
  data: { list_id: productContainer.$id, position: 1, related_list: 'testing_reports.product' },
});
```

### query_with Script Format

```
(function refineQuery(current, parent) {
    current.addQuery('field', parent.field);
})(current, parent);
```

The `current` variable represents the child table query. The `parent` variable represents the record on the form where the related list appears.

## See Also

- `form-layout-guide` — Required after table creation. Create a default form view (single merged section with all table fields) or custom form layouts and sections for tables.

- `field-styles-guide` — Apply CSS styling (background colors, text formatting, column widths) to fields in list and form views

Version: 4.14.0

# ListColumn

A Column for a list type field.

## Signature

```
ListColumn(config)
```

## Parameters

### config

`C & ListColumnType<RefTable, TChoices, Dropdown, Type, Default>`

Properties:

- 
active (optional): `boolean`
Indicates whether to display the field in list and forms

- 
array (optional): `boolean`
Creates another table to store the info that will be captured by this field

- 
arrayDenormalized (optional): `boolean`
Keeps the off-row array table and also stores the values on the parent row as a comma-separated string.

- 
attributes (optional): `Record<string, string | number | boolean>`
Pairs of any supported dictionary attributes (sys_schema_attribute)

- 
audit (optional): `boolean`
Indicates whether to track the creation, update, and deletion of all records in the table.

- 
choices (optional): `Record<string | number, string | ChoiceConfig | ChoiceConfig[]>`
Choice values for this field. Keys are the stored values; values are a display label string, a `ChoiceConfig` object, or an array of `ChoiceConfig` objects. Use an array to produce multiple `sys_choice` records for the same value — for example, to supply labels in multiple languages or define dependent-value variants.

ChoiceConfig properties:

- `label` (required): `string` — Display label shown in the UI

- `sequence` (optional): `number` — Sort order for the choice

- `hint` (optional): `string` — Tooltip hint

- `inactive` (optional): `boolean` — Hides the choice from the selection list

- `language` (optional): `string` — BCP 47 language tag for the label (e.g., `'en'`, `'fr'`). Defaults to the project's `defaultLanguage` in `now.config.json`.

- `dependentValue` (optional): `string | number` — Only show when the `dependent` field equals this value

- `inactiveOnUpdate` (optional): `boolean` — Makes the choice inactive after selection

- `synonyms` (optional): `string[]` — Alternate terms that match this choice during typeahead search

- 
default (optional): `Default | string`
Default value of the field when creating a record

- 
dependent (optional): `string`
limit the values available to select based on the value of the dependent field

- 
dropdown (optional): `Dropdown | choiceDropdownType`
How a list of choices displays for users of your form

- 
elementReference (optional): `boolean`
Indicates if the value of this field connotes the "element type"

- 
functionDefinition (optional): `string`
Definition of a function that the field performs

- 
help (optional): `string`
Help information for the field

- 
hint (optional): `string`
Describes field in more verbose form

- 
label (optional): `string | Documentation[]`
Unique label for the column that appears on list headers and form fields

- 
mandatory (optional): `boolean`
Indicates whether the field must contain a value to save a record

- 
maxLength (optional): `number | string`
Maximum length of the field value

- 
plural (optional): `string`
Plural form of the field name

- 
primary (optional): `boolean`
Indicates the primary key for a table

- 
readOnly (optional): `boolean`
Indicates whether you can edit the field value

- 
readOnlyOption (optional): `readOnlyOptionType`
Specifies the read-only behavior for the field

- 
referenceTable (optional): `RefTable`
Table containing possible values for this list (for reference-based lists)

- 
spellCheck (optional): `boolean`
Enables spell check for this field

- 
tableReference (optional): `boolean`
Indicates if the value of this field is a reference to another table in the schema

- 
textIndex (optional): `boolean`
Enables a natural language search on this field

- 
unique (optional): `boolean`
Creates a unique index on this field

- 
widget (optional): `string`
Style for the element type such as "radio"

- 
xmlView (optional): `boolean`
Displays the field value as XML

- 
formula (optional): `string`
Formula script for a formula-type virtual field. Sets virtual=true and virtual_type='formula'. Mutually exclusive with dynamicValueDefinitions of type 'calculated_value', which uses virtual_type='script'.

- 
virtualType (optional): `'script' | 'formula'`
Specifies the type of virtual/calculated field. Derived automatically: 'formula' when formula is set, 'script' when dynamicValueDefinitions type is 'calculated_value'. Only set explicitly to override.

- 
createRoles (optional): `(string | Role)[]`
Roles that can create a value in this field.

- 
readRoles (optional): `(string | Role)[]`
Roles that can read this field.

- 
writeRoles (optional): `(string | Role)[]`
Roles that can write to this field.

- 
deleteRoles (optional): `(string | Role)[]`
Roles that can delete a value in this field.

- 
dynamicRefQual (optional): `Record<'sys_filter_option_dynamic'> | string`
Dynamic reference qualifier — a sys_id or reference to a Dynamic Filter Options record. Use with `useReferenceQualifier: 'dynamic'`. Mutually exclusive with `referenceQual`.

- 
referenceQual (optional): `string`
Filter condition for the reference picker. Can be an encoded query (e.g. `'active=true'`) or a `javascript:` expression. Mutually exclusive with `dynamicRefQual`. See `referencecolumn-api` for details.

- 
referenceQualCondition (optional): `string`
Condition builder value for the reference qualifier. Maps to `sys_dictionary.reference_qual_condition`.

- 
referenceTable (optional): `keyof Tables`
Table containing possible values for this list (for reference-based lists)

- 
useReferenceQualifier (optional): `'simple' | 'dynamic' | 'advanced'`
Controls the reference qualifier mode. `'simple'` with `referenceQual` for an encoded query, `'advanced'` with `referenceQual` for a `javascript:` qualifier, or `'dynamic'` with `dynamicRefQual`. See `referencecolumn-api` for details.

Warning: Do not use `referenceQualifier` (which is only valid on `OverrideColumn` for overriding inherited fields). Use `referenceQual` for new column definitions. Using the wrong property name will silently fail — the build succeeds but the condition is not applied.

## Usage

```
import { Table, ListColumn } from '@servicenow/sdk/core';

export default Table({
    name: 'x_myapp_request',
    label: 'Request',
    columns: {
        // Simple reference qualifier — only show active users
        members: ListColumn({
            label: 'Members',
            referenceTable: 'sys_user',
            referenceQual: 'active=true',
            useReferenceQualifier: 'simple',
        }),
        // Advanced reference qualifier — dynamic JavaScript expression
        reviewers: ListColumn({
            label: 'Reviewers',
            referenceTable: 'sys_user',
            referenceQual: "javascript:'active=true^department=' + current.getValue('department')",
            useReferenceQualifier: 'advanced',
        }),
    },
});
```

## See

- https://docs.servicenow.com/csh?topicname=table-api-now-ts.html&version=latest

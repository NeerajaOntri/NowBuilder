Version: 4.14.0

# ReferenceColumn

Defines a reference (foreign key) column that links a record to a row in another table. Use `referenceTable` to specify the target table and `cascadeRule` to control what happens to referencing records when the target is deleted.

## Signature

```
ReferenceColumn(config)
```

## Parameters

### config

`C & ReferenceColumnType<RefTable, Type, Default>`

Properties:

- 
referenceTable (required): `RefTable`
Reference a different table as string, escape with `` if definition not present locally (import from `@servicenow/sdk-core/global`)

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
cascadeRule (optional): `'none' | 'delete_no_workflow' | 'cascade' | 'delete' | 'restrict' | 'clear'`
Configure what happens to records that reference a record when that record is deleted.

- 
default (optional): `Default | string`
Default value of the field when creating a record

- 
dependent (optional): `string`
limit the values available to select based on the value of the dependent field

- 
dynamicCreation (optional): `boolean`
If a reference is not found for a reference field then it allows the creation of that target

- 
dynamicCreationScript (optional): `string`
Populate a new record from a reference field based on the field value

- 
dynamicRefQual (optional): `Record<'sys_filter_option_dynamic'> | string`
Reference to a `sys_filter_option_dynamic` record — see the `now-ref` guide for record-reference forms. Use with `useReferenceQualifier: 'dynamic'`. Mutually exclusive with `referenceQual`.

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
referenceFloats (optional): `boolean`
Referenced table's form has an "edit" button in the related list for the current table

- 
referenceKey (optional): `string`
Specifies a field on the referenced table to store in the database instead of sys_id. The field must be unique and required on the referenced table (e.g., `'email'` for `sys_user`).

- 
referenceQual (optional): `string`
Filter condition for the reference picker. Can be a simple encoded query
(e.g., `'active=true'`) or a JavaScript expression prefixed with `javascript:`
(e.g., `"javascript:'active=true^department=' + current.getValue('department')"`).
Mutually exclusive with `dynamicRefQual`. Maps to `sys_dictionary.reference_qual`.

- 
referenceQualCondition (optional): `string`
Condition builder value for the reference qualifier. Maps to `sys_dictionary.reference_qual_condition`.

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
useReferenceQualifier (optional): `'simple' | 'dynamic' | 'advanced'`
Controls the reference qualifier mode.

- `'simple'` — use with `referenceQual` for a plain encoded query (e.g., `'active=true'`).

- `'advanced'` — use with `referenceQual` for a `javascript:` scripted qualifier.

- `'dynamic'` — use with `dynamicRefQual` to point to a `sys_filter_option_dynamic` record.
When omitted, defaults to `'simple'`. Maps to `sys_dictionary.use_reference_qualifier`.

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

Warning: Do not use `referenceQualifier` (which is only valid on `OverrideColumn` for overriding inherited fields). Use `referenceQual` for new column definitions. Using the wrong property name will silently fail — the build succeeds but the condition is not applied.

## Usage

```
import { Table, ReferenceColumn, StringColumn } from '@servicenow/sdk/core';

export default Table({
    name: 'x_myapp_request',
    label: 'Request',
    columns: {
        assigned_to: ReferenceColumn({ label: 'Assigned To', referenceTable: 'sys_user' }),
        category: ReferenceColumn({
            label: 'Category',
            referenceTable: 'x_myapp_category',
            cascadeRule: 'none',
        }),
    },
});
```

## See

- https://docs.servicenow.com/csh?topicname=table-api-now-ts.html&version=latest

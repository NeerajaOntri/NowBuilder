Version: 4.14.0

# DaysOfWeekColumn

A Column for a days of week field.
Stores multiple days (1-7) as concatenated digits where 1=Monday, 2=Tuesday, ..., 7=Sunday.

## Signature

```
DaysOfWeekColumn(config)
```

## Usage

```
const daysOfWeek = DaysOfWeekColumn({
    label: 'Days of Week',
    default: '126', // Monday, Tuesday, Saturday
})

const weekdays = DaysOfWeekColumn({
    label: 'Weekdays',
    default: '12345', // Monday-Friday
})
```

## Parameters

### config

`C & DaysOfWeekColumnType<Type, Default>`

an object that can include all base `Column` properties

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
default (optional): `Default | string`
Default value of the field when creating a record

- 
dependent (optional): `string`
limit the values available to select based on the value of the dependent field

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

## See

- https://docs.servicenow.com/csh?topicname=table-api-now-ts.html&version=latest

Version: 4.14.0

# SingleLineTextVariable

Creates a single-line text input variable for service catalog forms. Use for short text fields like names, titles, or identifiers. The value is a plain string with optional regex validation and placeholder text. Add a `SingleLineTextVariable` to a `CatalogItem` or `VariableSet` via the `variables` property.

## Signature

```
SingleLineTextVariable(config)
```

## Parameters

### config

`SingleLineTextVariableType<string, string>`

Configuration for the single line text variable including:

Properties:

- 
question (required): `string`

- 
active (optional): `boolean`

- 
alwaysExpand (optional): `boolean`
Always expand

- 
attributes (optional): `string`
Attributes of the variable

- 
category (optional): `string`
Category

- 
conversationalLabel (optional): `string`

- 
createRoles (optional): `(string | Role)[]`

- 
defaultValue (optional): `string | Default`

- 
deliveryPlan (optional): `string`
Delivery plan

- 
dependentQuestion (optional): `string | ReturnType<typeof ReferenceVariable> | ReturnType<typeof RequestedForVariable>`
The `RequestedForVariable` or `ReferenceVariable` whose selected record is used as the source for the dynamic default. Accepts the variable's name as a string (e.g. `'requestedFor'`), or a dot-walk into an attached VariableSet's `variables` (e.g. `employeeSet.variables.requestedFor`). A direct reference to a variable's own const (e.g. `dependentQuestion: requestedForVar`) is not supported — use the string name or a VariableSet dot-walk instead. When the user selects a value in the dependent question variable, this variable auto-populates based on the `dotWalkPath`. For example, if `dependentQuestion: 'requestedFor'` and `dotWalkPath: 'first_name'`, selecting a user will auto-populate this field with that user's first name. Requires `useDynamicDefault: true`.

- 
description (optional): `string`
Description

- 
disableInitialSlotFill (optional): `boolean`

- 
dotWalkPath (optional): `string`
The dot-walk path from the dependent question's referenced record to retrieve the default value. For example, `'first_name'` retrieves the first_name field, `'department.name'` retrieves the department's name. Used together with `dependentQuestion` and `useDynamicDefault: true`.

- 
exampleText (optional): `string`

- 
field (optional): `string`
Field to map (required when mapToField is true)

- 
global (optional): `boolean`
Global

- 
helpTag (optional): `string`

- 
helpText (optional): `string`

- 
hidden (optional): `boolean`
Indicates whether the field is hidden. Cannot be true when mandatory is true.

- 
instructions (optional): `string`

- 
layout (optional): `'normal' | '2across' | '2down'`
Layout style for the container

- 
mandatory (optional): `boolean`
Indicates whether the field must contain a value. Cannot be true when hidden or readOnly is true.

- 
mapToField (optional): `boolean`
Map to field

- 
order (optional): `number`
Order in which the variable appears

- 
postInsertScript (optional): `string`
Post insert script

- 
pricingDetails (optional): `PricingDetail[]`
Pricing details

- 
pricingImplications (optional): `boolean`
Pricing implications

- 
readOnly (optional): `boolean`
Indicates whether the field is read-only. Cannot be true when mandatory is true.

- 
readRoles (optional): `(string | Role)[]`

- 
readScript (optional): `string`
Read script

- 
removeFromConversationalInterfaces (optional): `boolean`
Remove from Conversational Interfaces

- 
showHelp (optional): `boolean`

- 
tooltip (optional): `string`

- 
unique (optional): `boolean`
Unique value

- 
useDynamicDefault (optional): `boolean`
Use dynamic default

- 
validateRegex (optional): `string | Record<'question_regex'>`
Whether to validate the regex expression pattern

- 
visibility (optional): `'Always' | 'Bundle' | 'Standalone'`
Visibility

- 
visibleBundle (optional): `boolean`

- 
visibleGuide (optional): `boolean`
Indicates whether the variable is visible in guides

- 
visibleStandalone (optional): `boolean`
Indicates whether the variable is visible when standalone

- 
visibleSummary (optional): `boolean`
Indicates whether the variable is visible in summaries

- 
width (optional): `100 | 25 | 50 | 75`
Width of the variable

- 
writeRoles (optional): `(string | Role)[]`

## Examples

### Basic Single Line Text

```
import { CatalogItem, SingleLineTextVariable } from '@servicenow/sdk/core'

CatalogItem({
  $id: Now.ID['employee_name_lookup'],
  name: 'Employee Name Lookup',
  shortDescription: 'Collect an employee name',
  variables: {
    employeeName: SingleLineTextVariable({
      question: "Employee Name",
      order: 100,
      mandatory: true,
      exampleText: "John Smith",
    }),
  },
})
```

### Dynamic Default with dependentQuestion

Auto-populate a text field based on a reference variable:

```
import { CatalogItem, RequestedForVariable, SingleLineTextVariable } from '@servicenow/sdk/core'

CatalogItem({
  $id: Now.ID['first_name_auto_populate'],
  name: 'First Name Auto Populate',
  shortDescription: 'Auto-populate first name from requested for',
  variables: {
    requestedFor: RequestedForVariable({
      question: 'Requested For',
      order: 100,
      mandatory: true,
    }),
    firstName: SingleLineTextVariable({
      question: 'First Name',
      order: 200,
      useDynamicDefault: true,
      dependentQuestion: 'requestedFor',
      dotWalkPath: 'first_name',
    }),
  },
})
```

## See

- https://docs.servicenow.com/csh?topicname=variable-types.html&version=latest

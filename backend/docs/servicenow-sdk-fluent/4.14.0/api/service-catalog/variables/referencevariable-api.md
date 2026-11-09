Version: 4.14.0

# ReferenceVariable

Creates a reference lookup variable for service catalog forms. Use when users need to select a record from another table (e.g., a user, group, or configuration item) via a searchable lookup field. Add a `ReferenceVariable` to a `CatalogItem` or `VariableSet` via the `variables` property.

## Signature

```
ReferenceVariable(config)
```

## Parameters

### config

`ReferenceVariableType<keyof Tables, string | ExplicitKey<string> | Record<keyof Tables>>`

Configuration for the reference variable including:

Properties:

- 
question (required): `string`

- 
referenceTable (required): `RefTable`
Table that is being referenced by this variable

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
defaultValue (optional): `string | Type`

- 
deliveryPlan (optional): `string`
Delivery plan

- 
dependentQuestion (optional): `string | ReturnType<typeof ReferenceVariable> | ReturnType<typeof RequestedForVariable>`
The `RequestedForVariable` or `ReferenceVariable` whose selected record is used as the source for the dynamic default. Accepts the variable's name as a string (e.g. `'requestedFor'`), or a dot-walk into an attached VariableSet's `variables` (e.g. `employeeSet.variables.requestedFor`). A direct reference to a variable's own const (e.g. `dependentQuestion: requestedForVar`) is not supported — use the string name or a VariableSet dot-walk instead. When the user selects a value in the dependent question variable, this variable auto-populates based on the `dotWalkPath`. For example, if `dependentQuestion: 'requestedFor'` and `dotWalkPath: 'manager'`, selecting a user in "Requested For" will auto-populate this field with that user's manager. Requires `useDynamicDefault: true`.

- 
description (optional): `string`
Description

- 
disableInitialSlotFill (optional): `boolean`

- 
dotWalkPath (optional): `string`
The dot-walk path from the dependent question's referenced record to retrieve the default value. For example, `'manager'` retrieves the manager field, `'department.name'` retrieves the department's name. Used together with `dependentQuestion` and `useDynamicDefault: true`.

- 
dynamicRefQual (optional): `string | Record<'sys_filter_option_dynamic'>`
Dynamic reference qualifier (use with useReferenceQualifier='dynamic'). Mutually exclusive with referenceQualCondition and referenceQual.

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
referenceQual (optional): `string`
Advanced reference qualifier (use with useReferenceQualifier='advanced'). Mutually exclusive with referenceQualCondition and dynamicRefQual.

- 
referenceQualCondition (optional): `string`
Filter reference based on a filter condition (use without useReferenceQualifier or with 'simple'). Mutually exclusive with dynamicRefQual and referenceQual.

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
useReferenceQualifier (optional): `'advanced' | 'simple' | 'dynamic'`
Type of reference qualifier. Determines which qualifier field to use.

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

### Basic Reference Variable

```
import { CatalogItem, ReferenceVariable } from '@servicenow/sdk/core'

CatalogItem({
  $id: Now.ID['configuration_item_lookup'],
  name: 'Configuration Item Lookup',
  shortDescription: 'Select a configuration item',
  variables: {
    configurationItem: ReferenceVariable({
      question: "Configuration Item",
      referenceTable: "cmdb_ci",
      referenceQualCondition: "operational_status=1",
      order: 100,
      mandatory: true,
    }),
  },
})
```

### Dynamic Default with dependentQuestion

Auto-populate a manager field based on the selected user:

```
import { CatalogItem, RequestedForVariable, ReferenceVariable } from '@servicenow/sdk/core'

CatalogItem({
  $id: Now.ID['manager_auto_populate'],
  name: 'Manager Auto Populate',
  shortDescription: 'Auto-populate manager from requested for',
  variables: {
    requestedFor: RequestedForVariable({
      question: 'Requested For',
      order: 100,
      mandatory: true,
    }),
    manager: ReferenceVariable({
      question: 'Manager',
      order: 200,
      referenceTable: 'sys_user',
      useDynamicDefault: true,
      dependentQuestion: 'requestedFor',
      dotWalkPath: 'manager',
    }),
  },
})
```

## See

- https://docs.servicenow.com/csh?topicname=variable-types.html&version=latest

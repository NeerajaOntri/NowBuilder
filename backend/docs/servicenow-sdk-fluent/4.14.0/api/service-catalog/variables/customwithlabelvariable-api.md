Version: 4.14.0

# CustomWithLabelVariable

A CatalogItem variable for a custom UI component field with a displayed label. Like `CustomVariable`, it embeds a UI Macro, Service Portal Widget, Macroponent, or Virtual Agent Topic Block into a catalog form — but it also renders the `question` text as a visible label above the custom component.

The following properties are not supported for custom UI component variables:

- `mandatory`

- `hidden`

- `readOnly`

Use `CustomVariable` when no label is needed.

## Signature

```
CustomWithLabelVariable(config)
```

## Usage

Use `CustomWithLabelVariable` when you need a labeled custom component on the catalog form — for example, a custom date range picker, a formatted info panel, or a specialized selector that should appear with a question label like standard variables.

This variant accepts the same rendering-context properties as `CustomVariable` — see the `customvariable-api` topic for the per-context table and for how to reference a macro. The only difference is that the `question` text is displayed as a label on the form.

Catalog client script isolation: scoped catalog client scripts run with `window` as `null`, so a script that bridges to the macro through `window` fails at runtime. See the `ui-macro-guide` topic for the pattern to use instead.

## Parameters

### config

`CustomWithLabelVariableType`

Configuration for the custom UI component variable with label. Extends `CustomVariableType` — all Custom variable properties are available.

Properties:

- 
question (required): `string`
Question text displayed as the variable label on the catalog form.

- 
macro (optional): `string | Record<'sys_ui_macro'> | UiMacro`
Reference to a `sys_ui_macro` record that renders the variable on Platform UI catalog forms. Pass a `UiMacro` object from the same project, a `Now.ref()` reference, or a sys_id string. The macro's Jelly receives the variable context at render time.

- 
summaryMacro (optional): `string | Record<'sys_ui_macro'> | UiMacro`
Reference to a `sys_ui_macro` record that renders a read-only summary of the variable on confirmation and summary pages. Accepts the same reference types as `macro`. Omit to use the default summary rendering.

- 
widget (optional): `string | Record<'sp_widget'> | SPWidget`
Reference to a Service Portal widget (`sp_widget`) that renders the variable in Service Portal catalog pages. Pass an `SPWidget()` object from the same project, or a sys_id string for a widget outside the project.

- 
macroponent (optional): `string | Record<'sys_ux_macroponent'>`
Reference to a Next Experience macroponent (`sys_ux_macroponent`) that renders the variable in UI Builder / Next Experience workspaces.

- 
topicBlock (optional): `string | Record<'sys_cs_topic'>`
Reference to a Virtual Agent topic block (`sys_cs_topic`) used when the catalog item is requested through a conversational interface.

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
Dependent question for dynamic default value

- 
description (optional): `string`
Description

- 
disableInitialSlotFill (optional): `boolean`

- 
dotWalkPath (optional): `string`
Dot walk path for dynamic default value

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
instructions (optional): `string`

- 
layout (optional): `'normal' | '2across' | '2down'`
Layout style for the container

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

### Custom With Label Variable Using a Project-Defined UI Macro

Define a `UiMacro` and use it in a `CustomWithLabelVariable` so the question text appears as a label above the custom component.

```
import { CatalogItem, CustomWithLabelVariable, UiMacro } from '@servicenow/sdk/core'

const dateRangeMacro = UiMacro({
    $id: Now.ID['date-range-picker'],
    name: 'date_range_picker',
    description: 'Renders a custom date range picker. Parameters: none.',
    category: 'catalog',
    xml: Now.include('./date-range-picker.jelly.xml'),
})

export const travelRequest = CatalogItem({
    $id: Now.ID['travel-request'],
    name: 'Travel Request',
    shortDescription: 'Request travel arrangements',
    variables: {
        travel_dates: CustomWithLabelVariable({
            question: 'Select Travel Dates',
            macro: dateRangeMacro,
            order: 100,
        }),
    },
})
```

### Custom With Label Variable with a Summary Macro

Pair `macro` with a second, read-only `summaryMacro` so the variable renders differently on the request summary and confirmation pages than it does on the catalog form. The label from `question` is shown in both contexts.

```
import { CatalogItem, CustomWithLabelVariable, UiMacro } from '@servicenow/sdk/core'

const teamPickerMacro = UiMacro({
    $id: Now.ID['team-picker-macro'],
    name: 'team_picker',
    description: 'Renders a custom team picker component. Parameters: none.',
    category: 'catalog',
    xml: Now.include('./team-picker.jelly.xml'),
})

const teamSummaryMacro = UiMacro({
    $id: Now.ID['team-summary-macro'],
    name: 'team_picker_summary',
    description: 'Read-only list of the selected team members. Parameters: none.',
    category: 'catalog',
    xml: Now.include('./team-picker-summary.jelly.xml'),
})

export const projectSetup = CatalogItem({
    $id: Now.ID['project-setup'],
    name: 'Project Setup',
    shortDescription: 'Set up a new project with team assignments',
    variables: {
        team_selection: CustomWithLabelVariable({
            question: 'Select Team Members',
            macro: teamPickerMacro,
            summaryMacro: teamSummaryMacro,
            order: 100,
        }),
    },
})
```

## See

- `ui-macro-guide` — Jelly authoring, parameter passing, and form formatter patterns

- `uimacro-api` — full `UiMacro` property reference

- `service-catalog-variables-guide` — all variable types and catalog examples

- `customvariable-api` — same variable without a displayed label

- https://docs.servicenow.com/csh?topicname=variable-types.html&version=latest

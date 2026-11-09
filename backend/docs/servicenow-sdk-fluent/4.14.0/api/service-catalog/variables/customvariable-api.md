Version: 4.14.0

# CustomVariable

A CatalogItem variable for a custom UI component field. Custom variables embed a UI Macro, Service Portal Widget, Macroponent, or Virtual Agent Topic Block directly into a catalog form — replacing the standard input control with a fully custom rendering.

The variable does not display a label; use `CustomWithLabelVariable` when a label is needed. Neither type supports `mandatory`, `hidden`, or `readOnly`.

## Signature

```
CustomVariable(config)
```

## Usage

Use `CustomVariable` when you need to render a custom UI component inside a catalog item or record producer form — for example, an interactive search panel, a specialized picker, or a status display that no standard variable type provides.

Set the property for each context the item is ordered in. Every context property is optional and defaults to empty — the build does not require or diagnose at least one being set — but a variable with none set renders blank in every context. `macro` and `widget` can be combined, and `summaryMacro` pairs with `macro`:

| Property | Table | Rendering context |
| `macro` | `sys_ui_macro` | Classic UI / Platform UI forms (Jelly-based) |
| `summaryMacro` | `sys_ui_macro` | Read-only summary / confirmation pages |
| `widget` | `sp_widget` | Service Portal catalog pages |
| `macroponent` | `sys_ux_macroponent` | Next Experience / UI Builder workspaces |
| `topicBlock` | `sys_cs_topic` | Virtual Agent conversational interfaces |

A single Custom variable can specify both `macro` (for Platform UI) and `widget` (for Service Portal) so the correct component renders in each context. The `summaryMacro` is optional and provides a separate read-only rendering on the request summary page.

Reference a project-defined `UiMacro` by importing the macro object and passing it directly. `Now.ref('sys_ui_macro', 'my-macro-id')` resolves a `Now.ID` key only within the current build — it does not reach a macro defined in a separate project. For a macro that isn't part of this project (an existing platform macro, or one built by another app), use its real sys_id string instead.

Catalog client script isolation: scoped catalog client scripts run with `window` as `null`, so a script that bridges to the macro through `window` fails at runtime. See the `ui-macro-guide` topic for the pattern to use instead.

## Parameters

### config

`CustomVariableType`

Configuration for the custom UI component variable.

Properties:

- 
question (required): `string`
Question text displayed to the user. For Custom variables (no label), this is used as the internal label; it appears in the platform variable list but not on the form.

- 
macro (optional): `string | Record<'sys_ui_macro'> | UiMacro`
Reference to a `sys_ui_macro` record that renders the variable on Platform UI catalog forms. Pass a `UiMacro` object from the same project, a `Now.ref()` reference, or a sys_id string. The macro's Jelly receives the variable context at render time.

- 
summaryMacro (optional): `string | Record<'sys_ui_macro'> | UiMacro`
Reference to a `sys_ui_macro` record that renders a read-only summary of the variable on confirmation and summary pages. Accepts the same reference types as `macro`. Omit to use the default summary rendering.

- 
widget (optional): `string | Record<'sp_widget'> | SPWidget`
Reference to a Service Portal widget (`sp_widget`) that renders the variable in Service Portal catalog pages. Pass an `SPWidget()` object from the same project, or a sys_id string for a widget outside the project. Use when the catalog item is ordered through Service Portal.

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

### Custom Variable with a Project-Defined UI Macro

Define a `UiMacro` in the same project and reference it from the `CustomVariable`. The macro renders inline on the Platform UI catalog form.

```
import { CatalogItem, CustomVariable, UiMacro } from '@servicenow/sdk/core'

const searchMacro = UiMacro({
    $id: Now.ID['catalog-search-panel'],
    name: 'catalog_search_panel',
    description: 'Renders an inline search panel on a catalog form. Parameters: none.',
    category: 'catalog',
    xml: Now.include('./catalog-search-panel.jelly.xml'),
})

export const incidentRequest = CatalogItem({
    $id: Now.ID['incident-request'],
    name: 'Create Incident',
    shortDescription: 'Submit a new incident',
    variables: {
        search_results: CustomVariable({
            question: 'Search Results',
            macro: searchMacro,
            order: 100,
        }),
    },
})
```

### Custom Variable with a Summary Macro

Pair `macro` with a second, read-only `summaryMacro` so the variable renders differently on the request summary and confirmation pages than it does on the catalog form.

```
import { CatalogItem, CustomVariable, UiMacro } from '@servicenow/sdk/core'

const statusMacro = UiMacro({
    $id: Now.ID['request-status-macro'],
    name: 'request_status_display',
    description: 'Displays request status on Platform UI. Parameters: none.',
    category: 'catalog',
    xml: Now.include('./request-status-display.jelly.xml'),
})

const statusSummaryMacro = UiMacro({
    $id: Now.ID['request-status-summary'],
    name: 'request_status_summary',
    description: 'Read-only request status for summary pages. Parameters: none.',
    category: 'catalog',
    xml: Now.include('./request-status-summary.jelly.xml'),
})

export const serviceRequest = CatalogItem({
    $id: Now.ID['service-request'],
    name: 'Service Request',
    shortDescription: 'Request a service',
    variables: {
        status_display: CustomVariable({
            question: 'Request Status',
            macro: statusMacro,
            summaryMacro: statusSummaryMacro,
            order: 100,
        }),
    },
})
```

### Custom Variable with sys_id Reference

Reference an existing platform macro by sys_id string when the macro is not defined in the current project. Look up the real sys_id with the `now-sdk query` command (see the `query-guide` topic) — don't guess or reuse a sys_id from an example.

```
import { CatalogItem, CustomVariable } from '@servicenow/sdk/core'

export const changeTemplate = CatalogItem({
    $id: Now.ID['change-template'],
    name: 'Modify a Standard Change Template',
    shortDescription: 'Modify an existing standard change template',
    variables: {
        change_task_annotation: CustomVariable({
            question: 'Change Task annotation',
            macro: '<sys_id of an existing platform sys_ui_macro>',
            order: 100,
        }),
    },
})
```

## See

- `ui-macro-guide` — Jelly authoring, parameter passing, and form formatter patterns

- `uimacro-api` — full `UiMacro` property reference

- `service-catalog-variables-guide` — all variable types and catalog examples

- `customwithlabelvariable-api` — same variable with a displayed label

- https://docs.servicenow.com/csh?topicname=variable-types.html&version=latest

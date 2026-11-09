Version: 4.14.0

# CatalogUiPolicy

API reference and patterns for Catalog UI Policies (`catalog_ui_policy`) for catalog items and record producers and variable sets.

## Signature

```
CatalogUiPolicy(config)
```

## Parameters

### config

`CatalogUiPolicyProps`

Catalog UI Policy configuration — condition, actions, target item or variable set.

## Properties

- 
$id (required): `string | number | ExplicitKey<string>`

- 
shortDescription (required): `string`
Description of what the policy does.

- 
$meta (optional): `object`

- installMethod: `'first install' | 'demo' | 'once'`
Map a record to an output folder that loads only in specific circumstances.
'first install' -> 'unload',
'demo' -> 'unload.demo'

- useEsLatest: `boolean`
Whether scripts on this record run with the latest ECMAScript (ES12+) support.

- 
actions (optional): `CatalogUiPolicyAction[]`
Actions to take when the policy is triggered.

- 
active (optional): `boolean`
Whether the policy is active. Default: `true`.

- 
appliesOnCatalogItemView (optional): `boolean`
Whether the policy applies when viewing the catalog item. Default: `true`.

- 
appliesOnCatalogTasks (optional): `boolean`
Whether the policy applies on catalog tasks. Default: `false`.

- 
appliesOnRequestedItems (optional): `boolean`
Whether the policy applies on requested items. Default: `false`.

- 
appliesOnTargetRecord (optional): `boolean`
Whether the policy applies on the target record. Default: `false`.

- 
appliesTo (optional): `'item' | 'set'`
Required if using `variableSet`. Default: `'item'`.

- 
catalogCondition (optional): `string`
Condition to determine when the policy applies to the catalog.

- 
catalogItem (optional): `string | CatalogItem`
Required if not using `variableSet`. Mutually exclusive with `variableSet`.

- 
description (optional): `string`
Detailed description of the UI policy.

- 
executeIfFalse (optional): `string`
Script to execute when the policy condition is false.

- 
executeIfTrue (optional): `string`
Script to execute when the policy condition is true.

- 
global (optional): `boolean`
Whether the policy applies globally. Default: `true`.

- 
isolateScript (optional): `boolean`
Whether to isolate the script execution context. Default: `true`.

- 
onLoad (optional): `boolean`
Whether the UI policy runs on page load. Default: `true`.

- 
order (optional): `number`
Order in which the policy should be evaluated. Default: `100`.

- 
reverseIfFalse (optional): `boolean`
Whether to reverse the policy condition logic. Default: `true`.

- 
runScripts (optional): `boolean`
Whether the UI policy runs scripts. Default: `false`.

- 
runScriptsInUiType (optional): `'desktop' | 'mobileOrServicePortal' | 'all'`
Default: `'all'`.

- 
vaSupported (optional): `boolean`
Whether the policy is supported for virtual agents. Default: `true`.

- 
variableSet (optional): `string | VariableSet`
Required if not using `catalogItem`. Mutually exclusive with `catalogItem`.

## Action Properties

| Property | Type | Description |
| variableName | `string | VariableReference` | Required. Variable reference. |
| variable | string | Human-readable variable name. |
| visible | boolean | Show/hide the variable. |
| mandatory | boolean | Make variable required. |
| readOnly | boolean | Make variable read-only. |
| cleared | boolean | Whether the field should be cleared when the policy is triggered. Default: `false` . |
| value | string | Value to set. |
| valueAction | string | `'clearValue'` or `'setValue'` . |
| order | number | Execution order. Default: `100` . |
| variableMessage | string | Message to display on the field. |
| variableMessageType | string | `'info'` , `'warning'` , `'error'` . |

## Condition Syntax

```
// Simple condition
catalogCondition: `${catalogItem.variables.priority}=high^EQ`;

// Multiple conditions with AND
catalogCondition: `${catalogItem.variables.env}=prod^${catalogItem.variables.critical}=true^EQ`;

// Multiple conditions with OR
catalogCondition: `${catalogItem.variables.env}=prod^OR${catalogItem.variables.critical}=true^EQ`;

// Not empty check
catalogCondition: `${catalogItem.variables.reference}ISNOTEMPTY^EQ`;
```

## Priority Rules

- Mandatory has highest priority

- If a variable is mandatory and has no value, readonly/hide actions do not work

- If a variable set/container has a mandatory variable without value, the entire set cannot be hidden

- "Clear value" action does not work on variable sets and containers

## Variable Type Limitations

| Policy Type | Not Applicable To |
| Mandatory | Fraction, Container Split, Container End, UI Macro, Label, UI Page |
| Read-only | Fraction, Container Split, Container End, UI Macro, Label, UI Page |
| Visibility | Fraction, Container Split, Container End |

## When to Use UI Policy vs Client Script

| Use Case | UI Policy | Client Script |
| Show/hide variables | Preferred | Supported |
| Make variables mandatory | Preferred | Supported |
| Make variables read-only | Preferred | Supported |
| Set variable values | Supported | Supported |
| Complex validation | Limited | Preferred |
| Dynamic calculations | Limited | Preferred |
| API calls / async | Not supported | Supported |
| Form submission control | Not supported | Supported |

## Common User Requests Mapping

| User Request | Agent Implementation |
| "Show field when priority is high" | UI Policy with condition and visible action |
| "Make field read-only conditionally" | UI Policy with readOnly and setValue actions |
| "Run script when condition matches" | UI Policy with runScripts and executeIfTrue/False |
| "Apply policy to variable set" | UI Policy with variableSet and appliesTo: "set" |

## Quick Reference

### ALWAYS

- Use UI Policies for simple show/hide/mandatory/read-only logic

- Use object references in properties (e.g., `catalogItem.variables.urgency`)

- End conditions with `^EQ`

- Use `reverseIfFalse: true` to auto-reverse when condition no longer matches

### NEVER

- Use UI Policies for complex validation (use Client Scripts)

- Use UI Policies for async/API calls (use Client Scripts)

- Hide mandatory variables that have no value (action will not work)

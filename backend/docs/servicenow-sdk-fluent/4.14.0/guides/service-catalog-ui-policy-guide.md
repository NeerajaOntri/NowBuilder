Version: 4.14.0

# Catalog UI Policies

Guide for building ServiceNow Catalog UI Policies (`catalog_ui_policy`) — conditionally shows, hides, or sets variables on a catalog item, record producer or variable set based on a condition.

## Catalog UI Policy Reference

### Properties

For the complete property reference including all properties, types, and detailed descriptions, see the `cataloguipolicy-api` documentation.

### Condition Syntax

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

### Priority Rules

- Mandatory has highest priority

- If a variable is mandatory and has no value, readonly/hide actions do not work

- If a variable set/container has a mandatory variable without value, the entire set cannot be hidden

- "Clear value" action does not work on variable sets and containers

### Variable Type Limitations

| Policy Type | Not Applicable To |
| Mandatory | Fraction, Container Split, Container End, UI Macro, Label, UI Page |
| Read-only | Fraction, Container Split, Container End, UI Macro, Label, UI Page |
| Visibility | Fraction, Container Split, Container End |

### Policy with Client Scripts

Set `runScripts: true` and provide `executeIfTrue` / `executeIfFalse` scripts via `Now.include(...)`. These scripts run client-side in the browser where modules are not available, so `Now.include()` is the correct approach. Scripts must be wrapped in `function onCondition() {}`.

## Examples

### Catalog UI Policy -- Show/Hide Based on Condition

```
import { CatalogUiPolicy } from "@servicenow/sdk/core";
import { hardwareRequestItem } from "./catalog-items/HardwareRequest.now";

export const managerApprovalPolicy = CatalogUiPolicy({
  $id: Now.ID["manager_approval_policy"],
  shortDescription: "Show manager approval when high priority selected",
  catalogItem: hardwareRequestItem,
  catalogCondition: `${hardwareRequestItem.variables.priority}=high^EQ`,
  actions: [
    {
      variableName: hardwareRequestItem.variables.manager_approval,
      visible: true,
      mandatory: true
    }
  ]
});
```

### Catalog UI Policy -- Read-Only with Value

```
import { CatalogUiPolicy } from "@servicenow/sdk/core"
import { softwareRequestItem } from './catalog-items/software-request'

export const readOnlyPolicy = CatalogUiPolicy({
  $id: Now.ID["readonly_license_policy"],
  shortDescription: "Make license type read-only for standard software",
  catalogItem: softwareRequestItem,
  catalogCondition: `${softwareRequestItem.variables.software_type}=standard^EQ`,
  actions: [
    {
      variableName: softwareRequestItem.variables.license_type,
      readOnly: true,
      value: "standard_license",
      valueAction: "setValue"
    }
  ]
});
```

### Catalog UI Policy -- With Client Scripts

```
import { CatalogUiPolicy } from "@servicenow/sdk/core"
import { cloudVmRequest } from './catalog-items/cloud-vm-request'

CatalogUiPolicy({
  $id: Now.ID["vm_prod_controls_policy"],
  shortDescription: "VM: Prod/BizCritical Controls",
  catalogItem: cloudVmRequest,
  catalogCondition: `${cloudVmRequest.variables.environment}=prod^OR${cloudVmRequest.variables.business_critical}=true^EQ`,
  active: true,
  onLoad: true,
  reverseIfFalse: true,
  runScripts: true,

  actions: [
    {
      variableName: cloudVmRequest.variables.backup_required,
      value: "true",
      valueAction: "setValue",
      readOnly: true,
      order: 100
    },
    {
      variableName: cloudVmRequest.variables.cost_center,
      mandatory: true,
      order: 200
    }
  ],

  executeIfTrue: Now.include("../../scripts/vm-production-controls.js"),
  executeIfFalse: Now.include("../../scripts/vm-development-controls.js")
});
```

vm-production-controls.js:

```
function onCondition() {
  var PROD_REGIONS = [
    ["AP-South-1", "AP-South-1 (Mumbai)"],
    ["EU-West-1", "EU-West-1 (Ireland)"]
  ];

  g_form.clearOptions("region");
  PROD_REGIONS.forEach(function (pair) {
    g_form.addOption("region", pair[0], pair[1]);
  });

  g_form.showFieldMsg(
    "environment",
    "Production VMs enforce backup and require cost center.",
    "info"
  );
}
```

### Catalog UI Policy -- Applied to Variable Set

```
import { CatalogUiPolicy } from "@servicenow/sdk/core"
import { shippingVariableSet } from './variable-sets/shipping'

export const internationalShippingPolicy = CatalogUiPolicy({
  $id: Now.ID["international_shipping_policy"],
  shortDescription: "Show customs fields for international shipping",
  variableSet: shippingVariableSet,
  appliesTo: "set",
  catalogCondition: `${shippingVariableSet.variables.shipping_country}!=US^EQ`,
  appliesOnCatalogItemView: true,
  appliesOnRequestedItems: true,
  actions: [
    {
      variableName: shippingVariableSet.variables.customs_declaration,
      visible: true,
      mandatory: true,
      variableMessage: "Required for international shipping",
      variableMessageType: "warning"
    }
  ]
});
```

## Multiple Actions on Multiple Variables

```
export const urgentRequestPolicy = CatalogUiPolicy({
  $id: Now.ID["urgent_request_policy"],
  shortDescription: "Show additional fields for urgent requests",
  catalogItem: laptopRequest,
  catalogCondition: `${laptopRequest.variables.urgency}=1^EQ`,
  onLoad: true,
  reverseIfFalse: true,
  actions: [
    {
      variableName: laptopRequest.variables.justification,
      mandatory: true,
      variableMessage: "Justification required for urgent requests",
      variableMessageType: "info",
      order: 100
    },
    {
      variableName: laptopRequest.variables.manager_approval,
      visible: true,
      mandatory: true,
      order: 200
    },
    {
      variableName: laptopRequest.variables.delivery_date,
      visible: true,
      order: 300
    }
  ]
});
```

## Related Topics

- For service catalog items and record producers: service-catalog-guide.md

- For variable sets: service-catalog-variables-guide.md

- For catalog client scripts: service-catalog-client-script-guide.md

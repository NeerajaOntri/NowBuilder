Version: 4.14.0

# Catalog Client Scripts

Guide for building ServiceNow Catalog Client Scripts (`catalog_script_client`) for service catalog items, record producers, and variable sets. These client-side scripts run in response to catalog form events such as `onLoad`, `onChange`, or `onSubmit`, enabling dynamic form behavior like field validation, visibility toggling, auto-populating fields from the current user, and user feedback messages.

## Properties

For the complete property reference including all properties, types, and detailed descriptions, see the `catalogclientscript-api` documentation.

## Script Types

### onLoad

Runs when the form loads. Use for initial setup (field states, defaults, visibility).

### onChange

Runs when a specific variable changes. Always guard with `if (isLoading) return;` to prevent execution during form load.

### onSubmit

Runs on form submission. Return `false` to block submission. Avoid GlideAjax here — async calls won't complete before the form submits.

## g_form API Reference

| Method | Description |
| `getValue(fieldName)` | Get variable value |
| `setValue(fieldName, value)` | Set variable value |
| `setDisplay(fieldName, display)` | Show/hide variable |
| `setMandatory(fieldName, mandatory)` | Set mandatory state |
| `setReadOnly(fieldName, readOnly)` | Set read-only state |
| `clearValue(fieldName)` | Clear variable value |
| `hasField(fieldName)` | Check if field exists |
| `showFieldMsg(fieldName, message, type, scrollForm)` | Show field message |
| `hideFieldMsg(fieldName, clearAll)` | Hide field message |
| `addErrorMessage(message)` | Add banner error message |
| `clearOptions(fieldName)` | Clear all select options |
| `addOption(fieldName, value, label)` | Add a select option |
| `getReference(fieldName, callback)` | Get referenced record (legacy) |

Note on `getReference`: Legacy convenience method. Works for simple lookups but `GlideAjax` is preferred for complex server-side logic. May make synchronous calls in some versions, which can freeze the UI.

## GlideAjax

Use `GlideAjax` to call server-side Script Includes from client scripts. The client sends a request, the Script Include processes it, and returns a result via a callback.

### GlideAjax Types — Quick Decision Guide

| Method | Execution | Use When | Avoid When |
| `getXMLAnswer()` | Async | Simple lookups, returning a single value/string | You need the full XML response object |
| `getXML()` | Async | Need full XML response, complex response parsing | Simple value returns (use getXMLAnswer) |
| `getXMLWait()` | Sync | Almost never — legacy/global scope only | Scoped apps, any production code |

### GlideAjax Parameter Rules

All custom parameters must start with `sysparm_`. The first `addParam` call must always be `sysparm_name` with the method name.

```
ga.addParam("sysparm_name", "methodName"); // REQUIRED: always first
ga.addParam("sysparm_user_id", userSysId); // Custom param: prefix with sysparm_
ga.addParam("sysparm_category", selectedCat); // Custom param: prefix with sysparm_
```

## Script Include (Server-Side Companion)

Every `GlideAjax` call requires a corresponding Script Include on the server. The Script Include must extend `AbstractAjaxProcessor` and be marked Client Callable.

### Script Include Setup Checklist

| Property | Value |
| Name | Must match the string in `new GlideAjax('ClassName')` |
| Client callable | Checked (required for GlideAjax access) |
| Extends | `global.AbstractAjaxProcessor` |
| Retrieve params | Use `this.getParameter('sysparm_param_name')` |
| Return data | Use `return` (simple string) or `return JSON.stringify(obj)` for objects |

### Script Include Security

- Client callable = true: Only check this when the method is explicitly needed from the client.

- Access controls: Runs in the logged-in user's session context. ACLs still apply to GlideRecord queries.

- Input validation: Always validate parameters from `this.getParameter()`. Never trust client-side input.

## Scripts on Variable Sets

Scope scripts to a variable set using `variableSet` and `appliesTo: 'set'` so they apply to all catalog items using that set. Always use `hasField()` checks since the variable may not exist on every item that includes the set.

### Execution Order Note

When multiple variable sets are attached to a catalog item, scripts execute in the order the variable sets are listed on the item. If both a variable set script and an item-level script target the same variable, the item-level script runs last and takes precedence.

## Catalog Client Script vs Standard Client Script

| Aspect | Catalog Client Script | Standard Client Script |
| Scope | Catalog item or variable set | Table (e.g., Incident) |
| onChange target | Links to a variable | Links to a field |
| Context | Catalog ordering, RITM, Catalog Task forms | Table forms |
| Variable access | Direct by variable name | Use `variables.variable_name` prefix |
| Applies to | `item` or `set` | Specific table |

## Best Practices

- Guard onChange: Always start with `if (isLoading) return;` to prevent execution on form load.

- Use `hasField()` in variable set scripts: The variable may not exist on every catalog item using the set.

- Avoid GlideAjax in onSubmit: Async calls won't complete before submission. Use onSubmit only for synchronous client-side validation.

- Use `g_form` APIs, not DOM: Never use `document.getElementById()` or jQuery — it breaks across UI versions (UI16, Workspace, Portal).

- Prefix for conflicts: If a variable name conflicts with a table field name, use `variables.variable_name` to reference the catalog variable.

- Return JSON from Script Includes: Use `JSON.stringify()` on the server and `JSON.parse()` on the client for structured data.

- Validate inputs in Script Includes: Never trust client-side parameters. Check for empty values, validate sys_id formats, and handle edge cases.

- Use `Now.include()` for shared code: Extract reusable client logic into UI Scripts and load with `Now.include('script_name')` for maintainability.

- Prefer `getXMLAnswer` over `getXML`: Simpler callback, less parsing code. Use `getXML` only when you need the full XML response.

- Never use `getXMLWait()`: Synchronous, freezes the UI, not available in scoped apps. Always use async patterns.

## Examples

### Catalog Client Script -- onLoad

```
import { CatalogClientScript } from "@servicenow/sdk/core";
import { laptopRequest } from "../catalog-items/laptop-request.now";

CatalogClientScript({
  $id: Now.ID["laptop_onload"],
  name: "Laptop Request - OnLoad",
  script: Now.include("../../client/laptop-onload.js"),
  type: "onLoad",
  catalogItem: laptopRequest,
  active: true,
  appliesOnCatalogItemView: true
});
```

laptop-onload.js:

```
function onLoad() {
  g_form.setReadOnly("estimated_cost", true);
  g_form.setValue("estimated_cost", "$0");
  g_form.setMandatory("justification", true);
}
```

### Catalog Client Script -- onChange

```
import { CatalogClientScript } from "@servicenow/sdk/core"
import { laptopRequest } from '../catalog-items/laptop-request.now'

CatalogClientScript({
  $id: Now.ID["laptop_type_change"],
  name: "Laptop Type - onChange",
  script: Now.include("../../client/laptop-type-change.js"),
  type: "onChange",
  catalogItem: laptopRequest,
  variableName: laptopRequest.variables.laptopType,
  active: true
});
```

laptop-type-change.js:

```
function onChange(control, oldValue, newValue, isLoading) {
  if (isLoading) return; // Always guard against initial load

  if (newValue === "developer") {
    g_form.setDisplay("accessories", true);
  } else {
    g_form.setDisplay("accessories", false);
    g_form.clearValue("accessories");
  }
}
```

### Catalog Client Script -- onSubmit Validation

```
import { CatalogClientScript } from "@servicenow/sdk/core"
import { laptopRequest } from '../catalog-items/laptop-request.now'

CatalogClientScript({
  $id: Now.ID["laptop_validation"],
  name: "Laptop Request - Validation",
  script: Now.include("../../client/laptop-validation.js"),
  type: "onSubmit",
  catalogItem: laptopRequest,
  active: true
});
```

laptop-validation.js:

```
function onSubmit() {
  var justification = (g_form.getValue("justification") || "").trim();

  if (justification.length < 20) {
    g_form.showFieldMsg("justification", "Please provide at least 20 characters.", "error", true);
    g_form.addErrorMessage("Justification is too short.");
    return false;
  }

  return true;
}
```

### Catalog Client Script -- onChange with GlideAjax

```
import { CatalogClientScript } from "@servicenow/sdk/core"
import { equipmentRepairItem } from '../catalog-items/equipment-repair'

CatalogClientScript({
  $id: Now.ID["asset_tag_lookup"],
  name: "Asset Tag - Warranty Lookup",
  script: Now.include("../../client/asset-tag-lookup.js"),
  type: "onChange",
  catalogItem: equipmentRepairItem,
  variableName: equipmentRepairItem.variables.asset_tag,
  active: true
});
```

asset-tag-lookup.js:

```
function onChange(control, oldValue, newValue, isLoading) {
  if (isLoading) return;

  if (!newValue) {
    g_form.clearValue("warranty_status");
    return;
  }

  var ga = new GlideAjax("global.AssetLookupUtil");
  ga.addParam("sysparm_name", "getWarrantyStatus");
  ga.addParam("sysparm_asset_tag", newValue);
  ga.getXMLAnswer(function (response) {
    if (!response) return;
    var info = JSON.parse(response);
    g_form.setValue("warranty_status", info.status);
  });
}
```

### Catalog Client Script -- Scoped to Variable Set

```
import { CatalogClientScript } from "@servicenow/sdk/core";
import { requesterInfoSet } from "./variable-sets/requester-info-set.now";

CatalogClientScript({
  $id: Now.ID["department_change_script"],
  name: "Department Change - Clear Manager",
  type: "onChange",
  variableSet: requesterInfoSet,
  appliesTo: "set",
  variableName: requesterInfoSet.variables.department,
  script: Now.include("../../client/department-change.js"),
  active: true
});
```

department-change.js:

```
function onChange(control, oldValue, newValue, isLoading) {
  if (isLoading) return;
  g_form.clearValue("manager");
  if (!newValue) return;
  g_form.showFieldMsg("manager", "Please select a manager from the new department", "info", false);
}
```

### GlideAjax -- Dynamic Options Based on Selection

Client script (onChange on 'department' variable):

```
function onChange(control, oldValue, newValue, isLoading) {
  if (isLoading) return;

  g_form.clearOptions("category");
  g_form.addOption("category", "", "-- Select --");

  if (!newValue) return;

  var ga = new GlideAjax("CatalogOptionLoader");
  ga.addParam("sysparm_name", "getCategoriesByDept");
  ga.addParam("sysparm_department", newValue);

  ga.getXMLAnswer(function (answer) {
    if (!answer) return;
    var categories = JSON.parse(answer);
    categories.forEach(function (cat) {
      g_form.addOption("category", cat.value, cat.label);
    });
  });
}
```

Script Include (CatalogOptionLoader, Client callable = true):

```
var CatalogOptionLoader = Class.create();
CatalogOptionLoader.prototype = Object.extendsObject(global.AbstractAjaxProcessor, {
  getCategoriesByDept: function () {
    var deptId = this.getParameter("sysparm_department");
    var categories = [];

    var gr = new GlideRecord("sc_category");
    gr.addQuery("department", deptId);
    gr.addQuery("active", true);
    gr.orderBy("title");
    gr.query();

    while (gr.next()) {
      categories.push({ value: gr.getUniqueValue(), label: gr.getValue("title") });
    }
    return JSON.stringify(categories);
  },

  type: "CatalogOptionLoader"
});
```

### GlideAjax -- Server-Side Validation (getXML)

Client script (onChange on 'asset_tag' variable):

```
function onChange(control, oldValue, newValue, isLoading) {
  if (isLoading) return;
  g_form.hideFieldMsg("asset_tag", true);

  if (!newValue) {
    g_form.clearValue("configuration_item");
    return;
  }

  var ga = new GlideAjax("AssetValidator");
  ga.addParam("sysparm_name", "validateAssetTag");
  ga.addParam("sysparm_asset_tag", newValue);

  ga.getXML(function (response) {
    var answer = response.responseXML.documentElement.getAttribute("answer");
    if (!answer) {
      g_form.showFieldMsg("asset_tag", "Unable to validate. Try again.", "error");
      return;
    }

    var result = JSON.parse(answer);
    if (result.found) {
      g_form.setValue("configuration_item", result.ci_sys_id);
      g_form.showFieldMsg("asset_tag", "Found: " + result.ci_name, "info");
    } else {
      g_form.clearValue("configuration_item");
      g_form.showFieldMsg("asset_tag", "Asset tag not found in CMDB.", "error");
    }
  });
}
```

Script Include (AssetValidator, Client callable = true):

```
var AssetValidator = Class.create();
AssetValidator.prototype = Object.extendsObject(global.AbstractAjaxProcessor, {
  validateAssetTag: function () {
    var assetTag = this.getParameter("sysparm_asset_tag");

    if (!assetTag) {
      return JSON.stringify({ found: false, error: "No asset tag provided" });
    }

    var gr = new GlideRecord("cmdb_ci");
    gr.addQuery("asset_tag", assetTag);
    gr.setLimit(1);
    gr.query();

    if (gr.next()) {
      return JSON.stringify({
        found: true,
        ci_sys_id: gr.getUniqueValue(),
        ci_name: gr.getDisplayValue("name"),
        ci_class: gr.getDisplayValue("sys_class_name")
      });
    }
    return JSON.stringify({ found: false });
  },

  type: "AssetValidator"
});
```

### Script Include -- Multi-Method Pattern

```
var CatalogUtils = Class.create();
CatalogUtils.prototype = Object.extendsObject(global.AbstractAjaxProcessor, {
  getItemPrice: function () {
    var itemId = this.getParameter("sysparm_item_id");
    var gr = new GlideRecord("sc_cat_item");
    if (gr.get(itemId)) {
      return gr.getValue("price");
    }
    return "0";
  },

  getManagerName: function () {
    var userId = this.getParameter("sysparm_user_id");
    var gr = new GlideRecord("sys_user");
    if (gr.get(userId)) {
      return JSON.stringify({
        manager_sys_id: gr.getValue("manager"),
        manager_name: gr.getDisplayValue("manager"),
        department: gr.getDisplayValue("department")
      });
    }
    return JSON.stringify({ error: "User not found" });
  },

  type: "CatalogUtils"
});
```

### Script Include -- Input Validation

```
getUserInfo: function() {
    var userId = this.getParameter('sysparm_user_id');

    // Validate: check it looks like a sys_id
    if (!userId || userId.length !== 32) {
        return JSON.stringify({ error: 'Invalid user ID' });
    }

    var gr = new GlideRecord('sys_user');
    if (gr.get(userId)) {
        return JSON.stringify({ name: gr.getDisplayValue('name') });
    }
    return JSON.stringify({ error: 'User not found' });
}
```

## Related Topics

- For service catalog items and record producers: service-catalog-guide.md

- For variable sets: service-catalog-variables-guide.md

- For UI policies: service-catalog-ui-policy-guide.md

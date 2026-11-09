Version: 4.14.0

# Service Catalog

Guide for building ServiceNow Service Catalog components using the Fluent API — catalog items [sc_cat_item], record producers [sc_cat_item_producer], variables [item_option_new], variable sets [item_option_new_set], UI policies [catalog_ui_policy], and client scripts [catalog_script_client]. Whenever the requirement is a form that captures user input and creates a record in a table — e.g., `problem`, `incident`, `change_request`, or a custom table, including mapping mandatory fields, applying validation, and confirming submission — the correct metadata is a Record Producer (`CatalogItemRecordProducer`), NOT a UI Page or a Scripted REST API. A Record Producer provides the form, field mapping (`mapToField`), validation (catalog UI policies + client scripts), and built-in submit/confirm behavior with no custom page or endpoint. Use a catalog item instead when ordering goods/services with approvals and fulfillment. Also use this guide when the user mentions service catalog, catalog items, record producers, variables, variable sets, UI policies, client scripts, form validation, dynamic fields, onChange, onLoad, onSubmit, ordering, or self-service. Includes property references, code examples, field mapping, scripting patterns, and best practices for end-to-end Service Catalog configuration. Only supported in SDK 4.3.0 or higher

## When to Use

- When creating catalog items for ordering goods/services, see Catalog Item Reference section

- When creating record producers to capture user input and create a record in a table (e.g., `incident`, `change_request`, `problem`) — this is the correct choice over a UI Page, see Catalog Item Record Producer Reference section.

- When defining catalog variables (form fields) for user input, see service-catalog-variables-guide.md

- When creating variable sets for reusable variable groups, see service-catalog-variables-guide.md

- When implementing catalog UI policies for show/hide, mandatory, read-only, simple value setting, see service-catalog-ui-policy-guide.md

- When adding catalog client scripts for complex validation, dynamic calculations, auto-populating a field from the current/requesting user (onLoad + GlideAjax), API/async calls (GlideAjax), form submission control (onSubmit), see service-catalog-client-script-guide.md

- When user mentions "service catalog", "catalog item", "record producer", "variables", "UI policy", "client script", "onChange", "onLoad", "onSubmit", or "form validation"

## Instructions

⚠️ Planning Rule: If the user's requirement mentions restricting who can "see", "view", "access", "order", or "submit" a catalog item — the plan should include a User Criteria step, NOT an ACL step. ACLs are never needed for catalog item visibility. Do not add a "security/ACL" step to the plan for this use case.
⚠️ Planning Rule: Every ordering/request use case **must create at least one `CatalogItem` (or `RecordProducer`) ** as the root, in your application's own scope. Variables, variable sets, UI policies, and client scripts are children of that item.

- Catalog, Category & Taxonomy: Items must be assigned to at least one catalog and category, and optionally a taxonomy topic. Use queries to find existing sys_ids.

- Variable Naming: Use `snake_case` for variable names. Use `order` increments of 100.

- Record Producer Tables: Only use for task-based tables (incident, change_request, problem). Never for sc_req_item, sc_request, sc_task.

- Field Mapping: Use `mapToField: true` for simple mappings, scripts for complex logic.

- UI Policy vs Client Script: Use UI policies for simple show/hide/mandatory. Use client scripts for validation, calculations, async calls.

- onChange Guard: Always start onChange scripts with `if (isLoading) return;`.

- onSubmit: Avoid GlideAjax in onSubmit (async issues). Return `false` to block submission.

- Variable References: Use object references in properties (e.g., `catalogItem.variables.urgency`), strings inside script code (e.g., `g_form.getValue('urgency')`).

- Variable Sets: Use for reusable variable groups. UI policies and client scripts can be scoped to a variable set with `appliesTo: 'set'`.

- DOM Manipulation: Never manipulate DOM directly -- always use `g_form` API.

- Variable Name Conflicts: Do not use the same variable name as a target table field name.

- Record Producer Scripts: Never call `current.update()` or `current.insert()` in pre-insert script.

- Circular Dependency (Flow + CatalogItem): When a flow uses `getCatalogVariables` with a catalog item's variables, the flow file imports the CatalogItem, and the CatalogItem references the flow using `Now.ref()` (NO import) to break the cycle.

- Visibility is controlled via User Criteria (`availableFor`/`notAvailableFor`), never use ACLs or the `roles` property. For controlling who can see and order a catalog item, always use `availableFor`/`notAvailableFor` with User Criteria records (see `user-criteria-guide`). Never use ACLs or the `roles` property -- User Criteria is the only supported mechanism for catalog item visibility. This is self-contained — do not add a separate security/ACL plan step for catalog item visibility.

## Key Concepts

### Catalog Item vs Record Producer

| Aspect | Catalog Item | Record Producer |
| Creates | REQ + RITM + Fulfillment Tasks | Record in target table (incident, change_request, etc.) |
| Fulfillment | Flow Designer / Workflow / Delivery Plan | Server-side scripts |
| Use when | Ordering goods/services with approvals | Creating task records directly |
| Examples | "Request Laptop", "Software License" | "Report Incident", "Submit HR Case" |

Key Rule: Ordering/requesting something --> Catalog Item. Creating a task record --> Record Producer.

### Taxonomy & Access (Catalog Items & Record Producers)

Taxonomy (`taxonomy_topic`): Hierarchical classification on catalog items. Organizes items from broad categories to specific subcategories, improving searchability and navigation -- particularly in Employee Center, where it maps items to topics and appears above the item name in search results. Assign topics to a catalog item using the `assignedTopics` property.

Catalog & Category Assignment: Items must belong to at least one Catalog (`sc_catalog`) and Category (`sc_category`). Categories can be nested into subcategories. Items can appear in multiple catalogs and categories simultaneously.

Visibility: Visibility is controlled via User Criteria (`availableFor`/`notAvailableFor`), never ACLs or the `roles` property. This is self-contained — do not add a separate security/ACL plan step for catalog item visibility.

### Querying Catalog, Category, and Taxonomy sys_ids

Use `now-sdk query` to resolve names to sys_ids before coding. Hard-code the resulting sys_id strings in your Fluent source — never query at build time.

Scope of this step: Query for existing catalogs, categories, and taxonomy topics only. Do not query for or reuse an existing catalog item if not asked explicitly or if the requirement does not specify a particular item — the catalog item is always authored fresh in your application scope (see the Root Artifact Rule above).

```
# Find a catalog by name
now-sdk query sc_catalog -q 'title=Service Catalog' -f 'sys_id,title' -o json

# Find a category by name
now-sdk query sc_category -q 'title=Hardware' -f 'sys_id,title' -o json

# Find a taxonomy topic by label (use -q 'label=...' for the topic table)
now-sdk query topic_m2m_task -q 'labelLIKEIT Services' -f 'sys_id,label' -o json
```

See the `query-guide` topic for full `now-sdk query` syntax and options.

Visibility (REQUIRED): Always use user criteria (`availableFor`/`notAvailableFor`) to control who can see and order catalog items -- even for simple single-role restrictions. Do not use the `roles` property for this purpose. `notAvailableFor` always overrides `availableFor` when both are present. See the `user-criteria-guide` for creating criteria records.

### User Criteria vs roles Property

| Aspect | User Criteria ( `availableFor` ) | `roles` Property |
| Use for | Catalog item visibility (who can see/order) | Legacy compatibility only |
| Hides in browsing | ✅ Yes - fully hides items | ❌ Partial - items may still appear |
| Supports | Roles, groups, departments, locations, companies, scripts | Roles only |
| Reusable | ✅ Yes - across multiple items | ❌ No - per item only |
| Exclusion lists | ✅ Yes ( `notAvailableFor` ) | ❌ No |
| Recommended | ✅ Always use for new implementations | ❌ Avoid - legacy only |

When to use each:

- User Criteria (`availableFor`): Always use for controlling who can see and order catalog items. This is the platform-standard mechanism.

- `roles` property: Do not use for new implementations. Retained only for backward compatibility with existing items.

### UI Policy vs Client Script

| Use Case | UI Policy | Client Script |
| Show/hide variables | Preferred | Supported |
| Make variables mandatory | Preferred | Supported |
| Make variables read-only | Preferred | Supported |
| Set variable values | Supported | Supported |
| Complex validation | Limited | Preferred |
| Dynamic calculations | Limited | Preferred |
| API calls / async | Not supported | Supported |
| Form submission control | Not supported | Supported |

### Common Validation Scenarios

| Validation | Implementation | Script Type |
| No past dates | Client Script | onChange |
| Date range (start < end) | Client Script | onChange |
| Min/max numeric values | Client Script | onChange |
| Text min/max length | Client Script | onSubmit |
| Format validation (regex) | Client Script | onChange or onSubmit |
| Required based on another field | UI Policy (preferred) or Client Script | onChange |
| Lookup / async validation | Client Script with GlideAjax | onChange |

### Decision Tree

- Ordering goods/services --> Catalog Item with variables and Flow Designer

- Creating task records (incident, change, problem) --> Record Producer with field mapping

- Reusable form fields across items --> Variable Set (singleRow or multiRow)

- Simple show/hide/mandatory logic --> Catalog UI Policy

- Complex validation, calculations, async calls --> Catalog Client Script

- Grid/table data entry --> Multi-Row Variable Set (MRVS)

- Restricting who can see/order an item --> User Criteria (`availableFor`/`notAvailableFor`) via `user-criteria-guide`

- Auto-populating a field from another reference variable on the form (e.g., manager from a "Requested for" variable) --> `dependentQuestion` with `dotWalkPath` (see `service-catalog-variables-guide`)

- Auto-populating a field from the current/requesting user when there is no on-form source variable (e.g., cost center from the requester's department) --> `onLoad` Catalog Client Script with GlideAjax (see `service-catalog-client-script-guide`). A bare reference variable does not populate itself.

## Avoidance

- Never use catalog items for creating task records directly (use Record Producers)

- Never create record producers for `sc_request`, `sc_req_item`, `sc_task`

- Never call `current.update()` or `current.insert()` in pre-insert scripts

- Never call `current.setAbortAction()` in Record Producer scripts

- Never use GlideAjax in onSubmit scripts (async issues)

- Never manipulate DOM directly -- always use `g_form` API

- Never use the same variable name as a target table field name

- Never skip the `order` property on variables

- Never skip catalogs or categories assignment

- Never hard-code sys_ids without documenting their source

- Never use the `roles` property on catalog items for visibility control -- always use `availableFor` with a User Criteria record instead. The `roles` property does not fully hide items in catalog browsing; User Criteria is the platform-standard mechanism for catalog visibility.

- Never create a new variable alongside an existing one with the same name — query `item_option_new` first to confirm existence, then update the same key in the `variables` object in-place (same key = same record, type changes are applied in-place); never remove choice keys from SelectBox/MultipleChoice variables — use `inactive: true` instead to preserve historical data (see `service-catalog-variables-guide` → Modifying Existing Variables)

- Variables without names cannot be accessed by client scripts

- Mandatory variables without values cannot be hidden by UI policies

- Multi-row variable sets have restrictions on certain variable types (no attachments, containers, HTML, macros)

- Container variables must follow the triplet order: ContainerStartVariable → variables → ContainerSplitVariable → variables → ContainerEndVariable. They cannot be used inside multiRow variable sets.

## Catalog Item Reference

For the complete property reference including all properties, types, and detailed descriptions, see the `catalogitem-api` documentation.

Key properties:

- `$id`, `name`, `shortDescription`, `description` — Basic identification

- `catalogs`, `categories`, `assignedTopics` — Taxonomy and organization

- `availableFor`, `notAvailableFor` — User Criteria for visibility control (see `user-criteria-guide`)

- `flow`, `workflow`, `executionPlan` — Fulfillment configuration (mutually exclusive)

- `variables`, `variableSets` — Form fields

- `active`, `availability`, `requestMethod` — Activation and display settings

### Fulfillment Configuration

Flow Designer (`flow`) — Automates request fulfillment using Flow Designer. Triggered on submission, it handles approvals, notifications, and task creation — retrieving catalog variables for dynamic processing and tracking progress through defined stages.

Reference a flow defined in the project using `Now.ref()`. This avoids importing the flow file directly, which prevents circular dependencies when the flow also imports the catalog item (e.g., for `getCatalogVariables`):

```
flow: Now.ref("sys_hub_flow", "my_fulfillment_flow");
```

Or reference an existing flow by sys_id:

```
flow: "e0d08b13c3330100c8b837659bba8fb4";
```

Refer to the wfa flow guide for more information on how to use the `wfa` namespace.

### Pricing Configuration

Use `pricingDetails` array with `{ amount, currencyType, field }` objects. Supported `field` values: `price`, `recurring_price`. When using `recurring_price`, `recurringFrequency` is required (`monthly`, `yearly`, etc.).

### Access Control

Use User Criteria as the preferred method:

- `availableFor`: Users/groups who can see the item

- `notAvailableFor`: Users/groups restricted (overrides availableFor)

- `accessType`: `'restricted'` or `'delegated'`

- `roles`: Role-based restrictions

- `assignedTopics`: For Employee Center visibility

Standard user criteria updates take effect immediately; scripted user criteria requires session relaunch.

### Circular Dependency Resolution (Flow + CatalogItem)

When a flow needs to use `getCatalogVariables` with the catalog item's variables:

- Flow --> imports CatalogItem (can use `getCatalogVariables` with variables)

- CatalogItem --> uses `Now.ref()` to reference Flow (NO import)

```
// catalog-item.now.ts - Uses Now.ref(), does NOT import flow
export const myCatalogItem = CatalogItem({
  $id: Now.ID["my_catalog_item"],
  flow: Now.ref("sys_hub_flow", "my_flow"), // No import needed
  variables: { ... }
});

// flow.now.ts - Imports catalog item for getCatalogVariables
import { myCatalogItem } from "../catalog-item.now";

export const myFlow = Flow(
  { $id: Now.ID["my_flow"] },
  wfa.trigger(trigger.application.serviceCatalog, ...),
  _params => {
    const vars = wfa.action(action.core.getCatalogVariables, {
      template_catalog_item: `${myCatalogItem}`,
      catalog_variables: [myCatalogItem.variables.field1, ...]
    });
  }
);
```

Refer to the wfa flow guide for more information.

### UI Display Options

| Property | Description |
| hideAddToCart | Hides "Add to Cart" button |
| hideAttachment | Hides attachment section |
| hideDeliveryTime | Hides delivery time |
| hideQuantitySelector | Hides quantity selection |
| hideSaveAsDraft | Hides "Save as Draft" |
| hideSP | Hides from Service Portal |
| hideAddToWishList | Hides "Add to Wishlist" |
| ignorePrice | Ignores price display |
| omitPrice | Omits price entirely |
| mandatoryAttachment | Requires attachment |
| makeItemNonConversational | Prevents virtual agent ordering |
| showVariableHelpOnLoad | Shows help text by default |

### Best Practices

- Create separate catalogs for different business units

- Use logical category hierarchy (max 3 levels deep)

- Each item should represent one orderable good or service

- Use Flow Designer as the preferred fulfillment method

- Set `active: false` for items under development

- Use `meta` tags for improved search discovery

- Always use queries to find existing catalog/category/topic sys_ids

- Use Service Catalog trigger for flow fulfillment

## Catalog Item Record Producer Reference

For the complete property reference including all properties, types, and detailed descriptions, see the `catalogitemrecordproducer-api` documentation.

Key properties: `$id`, `table`, `name` (required); `script`, `postInsertScript`, `saveScript` for scripting; `redirectUrl`, `allowEdit`, `canCancel` for submission behavior; `variables`, `variableSets` for the form.

All catalog item properties (catalogs, categories, accessType, etc.) also apply to record producers.

### Field Mapping Methods

| Scenario | Recommended Method |
| Simple text/choice mapping | `mapToField: true` |
| System values (gs.getUserID()) | Script |
| Conditional logic | Script |
| Calculated values | Script |
| Variables in Variable Sets | Script |

- mapToField (Recommended): Set `mapToField: true` and `field` on the variable to map directly to the target table field.

- Script-Based: Use `script` (pre-insert) or `postInsertScript` (post-insert) with `Now.include(...)` for external files.

- Variable Name Matching: Variable name matches target field name for automatic mapping. Less explicit than mapToField.

### Script Types

| Script | Timing | Can call update()? |
| `script` | Before insert | No |
| `postInsertScript` | After insert | Yes |
| `saveScript` | On step save | No |

#### Available Script Objects

| Object | Description |
| `current` | GlideRecord of the record being created |
| `producer.var_name` | Form variable values |
| `cat_item` | Record Producer definition (postInsertScript only) |
| `gs` | GlideSystem |

#### Script Rules

- Never call `current.update()` or `current.insert()` in pre-insert script

- Never call `current.setAbortAction()`

- Never set `current.sys_class_name`

- Use `postInsertScript` for post-creation updates, related records, notifications

### Unsupported Tables

Do not create record producers for:

- `sc_request`, `sc_req_item`, `sc_task` — Use Catalog Items instead.

### Redirect Options

- generatedRecord (default): Redirects to the created record

- catalogHomePage: Redirects to catalog home page

## Examples

### Catalog Item

#### Basic Catalog Item with Variables

```
import { CatalogItem, SelectBoxVariable, MultiLineTextVariable } from "@servicenow/sdk/core";

const serviceCatalog = "e0d08b13c3330100c8b837659bba8fb4";
const hardwareCategory = "d258b953c611227a0146101fb1be7c31";
const hardwareTopic = "782413a7c3053010069aec4b7d40ddf1";
const itilUsers = "2f137fb2eb303010e0ef83c45e52287c";
const guestUsers = "76f09af6cb1200108ad442fcf7076dbf";

export const laptopRequest = CatalogItem({
  $id: Now.ID["laptop_request"],
  name: "Laptop Request",
  shortDescription: "Request a new laptop for work",
  description: "Submit a request for a new laptop with configuration options.",

  catalogs: [serviceCatalog],
  categories: [hardwareCategory],
  assignedTopics: [hardwareTopic],
  availableFor: [itilUsers],
  notAvailableFor: [guestUsers],

  // Pricing
  pricingDetails: [{ amount: 1299, currencyType: "USD", field: "price" }],

  // Variables for user input
  variables: {
    laptopType: SelectBoxVariable({
      question: "Laptop Type",
      choices: {
        standard: { label: "Standard Laptop", sequence: 1 },
        developer: { label: "Developer Workstation", sequence: 2 }
      },
      mandatory: true,
      order: 100
    }),
    justification: MultiLineTextVariable({
      question: "Business Justification",
      mandatory: true,
      order: 200
    })
  },

  // Fulfillment
  flow: "523da512c611228900811a37c97c2014",
  fulfillmentAutomationLevel: "semiAutomated",
  deliveryTime: { days: 7, hours: 0 },

  // UI settings
  availability: "both",
  requestMethod: "order"
});
```

#### Catalog Item with Variable Sets

```
import { CatalogItem, VariableSet, SingleLineTextVariable, SelectBoxVariable, MultiLineTextVariable, ReferenceVariable, DateVariable } from "@servicenow/sdk/core";

// Query existing catalogs and categories using now-sdk query
// Example: now-sdk query sc_catalog -q 'title=Service Catalog' -f 'sys_id,title' -o json
// Example: now-sdk query sc_category -q 'title=Software' -f 'sys_id,title' -o json
const serviceCatalog = "e0d08b13c3330100c8b837659bba8fb4";
const softwareCategory = "d258b953c611227a0146101fb1be7c31";

// Define variable sets for example
export const contactInfoSet = VariableSet({
  $id: Now.ID["contact_info_set"],
  title: "Contact Information",
  description: "Standard contact information fields",
  type: "singleRow",
  layout: "2across",
  displayTitle: true,
  variables: {
    requesterName: SingleLineTextVariable({
      question: "Requester Name",
      mandatory: true,
      order: 100
    }),
    contactNumber: SingleLineTextVariable({
      question: "Contact Number",
      mandatory: true,
      order: 200
    })
  }
});

export const approvalInfoSet = VariableSet({
  $id: Now.ID["approval_info_set"],
  title: "Approval Information",
  description: "Approval workflow details",
  type: "singleRow",
  layout: "2across",
  displayTitle: true,
  variables: {
    approver: ReferenceVariable({
      question: "Approver",
      referenceTable: "sys_user",
      referenceQualCondition: "active=true",
      mandatory: true,
      order: 100
    }),
    approvalDeadline: DateVariable({
      question: "Approval Deadline",
      mandatory: true,
      order: 200
    })
  }
});

export const softwareLicenseRequest = CatalogItem({
  $id: Now.ID["software_license_request"],
  name: "Software License Request",
  shortDescription: "Request a software license",

  catalogs: [serviceCatalog],
  categories: [softwareCategory],

  // Attach reusable variable sets
  variableSets: [
    { variableSet: contactInfoSet, order: 100 },
    { variableSet: approvalInfoSet, order: 200 }
  ],

  // Item-specific variables
  variables: {
    software_name: SingleLineTextVariable({
      question: "Software Name",
      mandatory: true,
      order: 100
    }),
    license_type: SelectBoxVariable({
      question: "License Type",
      choices: {
        individual: { label: "Individual", sequence: 1 },
        team: { label: "Team (5 seats)", sequence: 2 },
        enterprise: { label: "Enterprise (unlimited)", sequence: 3 }
      },
      mandatory: true,
      order: 200
    }),
    number_of_licenses: SingleLineTextVariable({
      question: "Number of Licenses",
      defaultValue: "1",
      order: 300
    }),
    justification: MultiLineTextVariable({
      question: "Business Justification",
      mandatory: true,
      order: 400
    })
  },

  // Pricing with recurring charges
  pricingDetails: [
    { amount: 0, currencyType: "USD", field: "price" },
    { amount: 99, currencyType: "USD", field: "recurring_price" }
  ],
  recurringFrequency: "monthly",

  flow: "523da512c611228900811a37c97c2014",
  deliveryTime: { days: 3, hours: 0 }
});
```

#### Circular Dependency Resolution

When a flow needs to use `getCatalogVariables` with the catalog item's variables,
there's a circular dependency:

- Flow needs to import CatalogItem (for template_catalog_item and catalog_variables)

- CatalogItem needs to reference Flow (for fulfillment)

Solution Pattern:

- Flow → imports CatalogItem (can use getCatalogVariables with variables)

- CatalogItem → uses `Now.ref()` to reference Flow (NO import)

```
import { CatalogItem } from "@servicenow/sdk/core";

// catalog-item.now.ts - Uses Now.ref(), does NOT import flow
export const myCatalogItem = CatalogItem({
  $id: Now.ID["my_catalog_item"],
  name: "My Catalog Item",
  flow: Now.ref("sys_hub_flow", "my_flow"), // No import needed
  variables: { /* ... */ }
});
```

```
import { Flow } from "@servicenow/sdk/flow";
import * as wfa from "@servicenow/sdk/wfa";
import * as trigger from "@servicenow/sdk/wfa/trigger";
import * as action from "@servicenow/sdk/wfa/action";
import { myCatalogItem } from "./catalog-item.now";
// flow.now.ts - Imports catalog item for getCatalogVariables
export const myFlow = Flow(
  { $id: Now.ID["my_flow"] },
  wfa.trigger(trigger.application.serviceCatalog, {}),
  _params => {
    // Note: In practice, this would import from the catalog item file
    const catalogItemRef = "my_catalog_item"; // Reference to catalog item
    const vars = wfa.action(action.core.getCatalogVariables, {
      template_catalog_item: `${myCatalogItem}`,
      catalog_variables: [myCatalogItem.variables.field1]
    });
  }
);
```

### Catalog Item Record Producer

#### Comprehensive Record Producer with Field Mapping

```
import { CatalogItemRecordProducer, SingleLineTextVariable, SelectBoxVariable, ReferenceVariable } from "@servicenow/sdk/core";

const serviceCatalog = "e0d08b13c3330100c8b837659bba8fb4";
const itServicesCategory = "d258b953c611227a0146101fb1be7c31";

export const comprehensiveIncidentProducer = CatalogItemRecordProducer({
  $id: Now.ID["comprehensive_incident_producer"],
  name: "Report Incident with Full Configuration",
  shortDescription: "Complete incident producer with variables and scripts",
  table: "incident",

  catalogs: [serviceCatalog],
  categories: [itServicesCategory],

  variables: {
    short_description: SingleLineTextVariable({
      question: "Brief Summary",
      mandatory: true,
      mapToField: true,
      field: "short_description",
      order: 100
    }),
    urgency: SelectBoxVariable({
      question: "Urgency",
      mandatory: true,
      mapToField: true,
      field: "urgency",
      choices: {
        "1": { label: "High", sequence: 1 },
        "2": { label: "Medium", sequence: 2 },
        "3": { label: "Low", sequence: 3 }
      },
      order: 200
    }),
    assignment_group: ReferenceVariable({
      question: "Assignment Group",
      mapToField: true,
      field: "assignment_group",
      referenceTable: "sys_user_group",
      order: 300
    })
  },

  script: Now.include("../scripts/rp-pre-insert.js"),
  postInsertScript: Now.include("../scripts/rp-post-insert.js"),

  redirectUrl: "generatedRecord",
  view: "ess",
  allowEdit: true
});
```

rp-pre-insert.js:

```
(function executeProducerScript(current, producer) {
  // Set defaults and auto-populate fields
  current.impact = 3;
  current.contact_type = "self-service";
  current.caller_id = gs.getUserID();

  // Complex conditional logic
  if (producer.urgency === "1") {
    current.priority = 1;
    current.assignment_group = "Hardware Team";
  }
  // Do NOT use current.update() or current.insert() here
})(current, producer);
```

rp-post-insert.js:

```
(function executeProducerScript(current, producer) {
  // Post-creation updates are safe here
  current.work_notes = "Created via Service Catalog at " + gs.nowDateTime();
  current.update();

  // Create related records if needed
  var task = new GlideRecord("sc_task");
  task.initialize();
  task.request = current.sys_id;
  task.short_description =
    "Follow up on incident: " + current.short_description;
  task.insert();
})(current, producer);
```

#### Different Table Examples

```
import { CatalogItemRecordProducer } from "@servicenow/sdk/core";

const serviceCatalog = "e0d08b13c3330100c8b837659bba8fb4";
const itServicesCategory = "d258b953c611227a0146101fb1be7c31";

// Problem Record Producer
export const problemProducer = CatalogItemRecordProducer({
  $id: Now.ID["problem_producer"],
  name: "Report a Problem",
  shortDescription: "Create a problem record",
  table: "problem",
  catalogs: [serviceCatalog],
  categories: [itServicesCategory],
  script: Now.include("../scripts/rp-problem-pre-insert.js"),
  redirectUrl: "generatedRecord"
});

// Change Request Producer
export const changeRequestProducer = CatalogItemRecordProducer({
  $id: Now.ID["change_request_producer"],
  name: "Submit Change Request",
  shortDescription: "Create a change request",
  table: "change_request",
  catalogs: [serviceCatalog],
  categories: [itServicesCategory],
  script: Now.include("../scripts/rp-change-pre-insert.js"),
  redirectUrl: "generatedRecord"
});
```

rp-problem-pre-insert.js:

```
(function executeProducerScript(current, producer) {
  current.short_description = producer.problem_summary;
  current.description = producer.problem_details;
  current.impact = producer.impact_level;
  current.priority = producer.priority_level;
  current.caller_id = gs.getUserID();
})(current, producer);
```

rp-change-pre-insert.js:

```
(function executeProducerScript(current, producer) {
  current.short_description = producer.change_summary;
  current.description = producer.change_details;
  current.type = producer.change_type;
  current.requested_by = gs.getUserID();
  current.risk = producer.risk_level;
})(current, producer);
```

## Related Topics

- wfa flow guide

- service-catalog-variables-guide.md

- service-catalog-ui-policy-guide.md

- service-catalog-client-script-guide.md

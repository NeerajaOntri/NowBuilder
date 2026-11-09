Version: 4.14.0

# CatalogItem

Creates a Service Catalog Item (`sc_cat_item`) — a requestable item in the ServiceNow Service Catalog.

## Signature

```
CatalogItem(config)
```

## Usage

Use `CatalogItem` for ordering goods and services. Assign `catalogs` and `categories` to place the item in the catalog. Control visibility with `availableFor`/`notAvailableFor` using User Criteria sys_ids — never use the `roles` property for this. Wire fulfillment via `flow`, `workflow`, or `executionPlan` (mutually exclusive). Define user input with `variables` (inline) or `variableSets` (reusable groups). For conditional show/hide and mandatory logic, attach `CatalogUiPolicy` records; for validation and dynamic calculations, attach `CatalogClientScript` records.

## Properties

- 
$id (required): `string | number | ExplicitKey<string>`

- 
name (required): `string`
Name to appear in the catalog.

- 
accessType (optional): `'restricted' | 'delegated'`
Controls who can request the item. Default: `'restricted'`.

- 
active (optional): `boolean`
Whether the item is active. Default: `true`.

- 
assignedTopics (optional): `(string | Record<'topic'>)[]`
sys_id of existing topics. Controls ESC portal visibility.

- 
availability (optional): `'desktopOnly' | 'both' | 'mobileOnly'`
Platform availability. Default: `'desktopOnly'`.

- 
availableFor (optional): `(string | Record<'user_criteria'>)[]`
sys_id of user criteria for availability.

- 
billable (optional): `boolean`
Billable status. Default: `false`.

- 
catalogs (optional): `(string | Record<'sc_catalog'>)[]`
sys_id of existing catalogs. Use queries to find.

- 
categories (optional): `(string | Record<'sc_category'>)[]`
sys_id of existing categories. Use queries to find. Can only be selected after `catalogs` is populated.

- 
checkedOut (optional): `boolean`
Whether the item is checked out.

- 
cost (optional): `number`
Cost of the catalog item. Default: `0`.

- 
customCart (optional): `string | Record<'sys_ui_macro'> | UiMacro`
Reference to a `sys_ui_macro` record that replaces the default cart/checkout experience for this catalog item. When set, the platform renders this macro instead of the standard Add to Cart / Order Now buttons and cart summary. Use this for items that need a custom checkout flow — such as a license acceptance step, a payment form, a multi-step confirmation, or a bundle breakdown preview. Pass a `UiMacro` object from the same project, a `Now.ref()` reference, or a sys_id string. See `uimacro-api` for macro authoring and the `ui-macro-guide` for the custom cart pattern.

- 
deliveryPlanScript (optional): `string`
Delivery plan script for the catalog item.

- 
deliveryTime (optional): `Duration`
Estimated delivery time `{ days, hours }`. Default: `{}`.

- 
description (optional): `string`
Detailed description shown on the item page.

- 
displayPriceProperty (optional): `string`
Display price property. Default: `'non_zero'`.

- 
entitlementScript (optional): `string`
Entitlement script for the catalog item.

- 
executionPlan (optional): `string | Record<'sc_cat_item_delivery_plan'>`
Delivery plan sys_id for fulfillment. Mutually exclusive with `flow` and `workflow`.

- 
flow (optional): `string | Record<'sys_hub_flow'> | Flow`
Flow Designer flow sys_id or `Flow()` instance for fulfillment. Mutually exclusive with `executionPlan` and `workflow`.

- 
fulfillmentAutomationLevel (optional): `'unspecified' | 'manual' | 'semiAutomated' | 'fullyAutomated'`
Default: `'unspecified'`.

- 
fulfillmentGroup (optional): `string | Record<'sys_user_group'>`
Group sys_id responsible for delivery.

- 
hideAddToCart (optional): `boolean`
Hides "Add to Cart" button. Default: `false`.

- 
hideAddToWishList (optional): `boolean`
Hides "Add to Wishlist". Default: `false`.

- 
hideAttachment (optional): `boolean`
Hides attachment section. Cannot be `true` when `mandatoryAttachment` is `true`. Default: `false`.

- 
hideDeliveryTime (optional): `boolean`
Hides delivery time. Default: `false`.

- 
hideQuantitySelector (optional): `boolean`
Hides quantity selection. Default: `false`.

- 
hideSaveAsDraft (optional): `boolean`
Hides "Save as Draft". Default: `false`.

- 
hideSP (optional): `boolean`
Hides from Service Portal. Default: `false`.

- 
icon (optional): `string`
Icon for the catalog item.

- 
ignorePrice (optional): `boolean`
Ignores price display. Default: `true`.

- 
image (optional): `string`
Image for the catalog item.

- 
location (optional): `string | Record<'cmn_location'>`
Location for access configuration.

- 
makeItemNonConversational (optional): `boolean`
Prevents virtual agent ordering. Default: `false`.

- 
mandatoryAttachment (optional): `boolean`
Requires an attachment. Forces `hideAttachment` to `false` when set. Default: `false`.

- 
meta (optional): `string[]`
Search tags for the catalog item.

- 
mobileHidePrice (optional): `boolean`
Hides price on mobile. Default: `false`.

- 
mobilePicture (optional): `string`
Mobile picture for the catalog item.

- 
mobilePictureType (optional): `'desktopPicture' | 'mobilePicture' | 'noPicture'`
Mobile picture type. Default: `'desktopPicture'`.

- 
model (optional): `string | Record<'cmdb_model'>`
Model of the catalog item.

- 
noCart (optional): `boolean`
Hide cart (legacy). Default: `false`.

- 
noOrder (optional): `boolean`
Hide order (legacy). Default: `false`.

- 
noOrderNow (optional): `boolean`
Hide order now (legacy). Default: `false`.

- 
noProceedCheckout (optional): `boolean`
Hide proceed checkout (legacy). Default: `false`.

- 
noQuantity (optional): `boolean`
Hide quantity (legacy). Default: `false`.

- 
noSearch (optional): `boolean`
Exclude from portal search. Default: `false`.

- 
notAvailableFor (optional): `(string | Record<'user_criteria'>)[]`
sys_id of user criteria for restrictions (overrides `availableFor`).

- 
omitPrice (optional): `boolean`
Omits price entirely. Default: `false`.

- 
order (optional): `number`
Order of the catalog item. Default: `0`.

- 
owner (optional): `string | Record<'sys_user'>`
Owner for the catalog item.

- 
picture (optional): `string`
Picture for the catalog item.

- 
pricingDetails (optional): `PricingDetail[]`
Pricing breakdown: `{ amount, currencyType, field }`.

- 
recurringFrequency (optional): `'weekly' | 'quarterly' | 'weekly2' | 'semiannual' | 'monthly' | 'yearly' | 'daily' | 'monthly2'`
Required when `pricingDetails` contains `'recurring_price'`.

- 
requestMethod (optional): `'order' | 'request' | 'submit'`
Submission button label. Default: `'order'`.

- 
roles (optional): `(string | Role)[]`
Roles for catalog item access.

- 
shortDescription (optional): `string`
Brief summary shown in catalog listings.

- 
showVariableHelpOnLoad (optional): `boolean`
Shows help text by default. Default: `false`.

- 
startClosed (optional): `boolean`
Start closed. Default: `false`.

- 
state (optional): `'published' | 'draft' | 'publishing' | 'in_review' | 'reviewed'`
State of the catalog item.

- 
useScLayout (optional): `boolean`
Use service catalog layout. Default: `true`.

- 
variables (optional): `object`
Variable definitions for the form.

- 
variableSets (optional): `{ variableSet: string | VariableSet; order: number }[]`
Variable set references.

- 
vendor (optional): `string | Record<'core_company'>`
Vendor for access configuration.

- 
version (optional): `number`
Version of the catalog item. Default: `1`.

- 
view (optional): `string | Record<'sys_ui_view'>`
View for the catalog item.

- 
visibleBundle (optional): `boolean`
Bundle visibility. Default: `true`.

- 
visibleGuide (optional): `boolean`
Guide visibility. Default: `true`.

- 
visibleStandalone (optional): `boolean`
Standalone visibility. Default: `true`.

- 
workflow (optional): `string | Record<'wf_workflow'>`
Legacy workflow sys_id for fulfillment. Mutually exclusive with `executionPlan` and `flow`.

## Fulfillment Configuration

Flow Designer (`flow`) — Recommended fulfillment method for catalog items. Use `Now.ref()` to reference a project-defined flow or provide a sys_id string for an existing platform flow.

## Pricing Configuration

Use `pricingDetails` array with `{ amount, currencyType, field }` objects. Supported `field` values: `price`, `recurring_price`. When using `recurring_price`, `recurringFrequency` is required (`monthly`, `yearly`, etc.).

## Access Control

Use User Criteria as the preferred method:

- `availableFor`: Users/groups who can see the item

- `notAvailableFor`: Users/groups restricted (overrides availableFor)

- `accessType`: `'restricted'` or `'delegated'`

- `roles`: Role-based restrictions

- `assignedTopics`: For Employee Center visibility

Standard user criteria updates take effect immediately; scripted user criteria requires session relaunch.

## UI Display Options

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

## Common User Requests Mapping

| User Request | Agent Implementation |
| "Order a laptop" | Catalog Item with variables and Flow Designer |
| "Request software license" | Catalog Item with variable sets and recurring pricing |
| "Service with approvals" | Catalog Item with flow fulfillment |
| "Reusable fields across items" | Catalog Item with variable sets |

## Quick Reference

### ALWAYS

- Assign items to at least one catalog and category

- Use queries to find existing catalog/category/topic sys_ids

- Use Flow Designer as the preferred fulfillment method

- Use `snake_case` for variable names

- Use `order` increments of 100

### NEVER

- Use catalog items for creating task records directly (use Record Producers)

- Skip catalogs or categories assignment

- Hard-code sys_ids without documenting their source

## See

- https://docs.servicenow.com/csh?topicname=service-catalog-api-now-ts.html&version=latest

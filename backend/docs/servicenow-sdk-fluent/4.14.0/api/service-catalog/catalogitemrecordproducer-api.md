Version: 4.14.0

# CatalogItemRecordProducer

Creates a Record Producer (`sc_cat_item_producer`) — a catalog item that creates a record in a
specified table when submitted. Extends CatalogItem with record creation and script capabilities.

## Signature

```
CatalogItemRecordProducer(config)
```

## Properties

- 
$id (required): `string | number | ExplicitKey<string>`

- 
name (required): `string`
Name to appear in the catalog.

- 
active (optional): `boolean`
Whether the item is active. Default: `true`.

- 
allowEdit (optional): `boolean`
Whether to allow editing of the generated record after creation. Default: `false`.

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
canCancel (optional): `boolean`
Whether the user can cancel the record producer submission. Default: `false`.

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
description (optional): `string`
Detailed description shown on the item page.

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
image (optional): `string`
Image for the catalog item.

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
mobilePicture (optional): `string`
Mobile picture for the catalog item.

- 
mobilePictureType (optional): `'desktopPicture' | 'mobilePicture' | 'noPicture'`
Mobile picture type. Default: `'desktopPicture'`.

- 
model (optional): `string | Record<'cmdb_model'>`
Model of the catalog item.

- 
noSearch (optional): `boolean`
Excludes item from portal search results. Default: `false`.

- 
notAvailableFor (optional): `(string | Record<'user_criteria'>)[]`
sys_id of user criteria for restrictions (overrides `availableFor`).

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
postInsertScript (optional): `((producer: RecordProducerContext, current: GlideRecord, cat_item: RecordProducerDefinition) => void) | string`
Script executed AFTER the record is generated. Safe to call `current.update()`. Use `producer.var_name` to access variables and `cat_item` to access the Record Producer definition.

- 
redirectUrl (optional): `'generatedRecord' | 'catalogHomePage'`
Where to redirect after record creation. Default: `'generatedRecord'`.

- 
roles (optional): `(string | Role)[]`
Roles for catalog item access.

- 
saveOptions (optional): `string`
Options for saving the record producer (advanced configuration).

- 
saveScript (optional): `((producer: RecordProducerContext, current: GlideRecord, cat_item: RecordProducerDefinition) => void) | string`
Script executed at every step save in Catalog Builder. Executed BEFORE the main script. Use `current` to access the GlideRecord.

- 
script (optional): `((producer: RecordProducerContext, current: GlideRecord) => void) | string`
Server-side script executed BEFORE the record is generated. Use `producer.var_name` to access variables and `current` to access the GlideRecord being produced. Do NOT use `current.update()` or `current.insert()`.

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
table (required): `TableName | Table`
Target table where the record will be created. Accepts a table name string or a `Table()` definition. Example: `'incident'`, `'change_request'`, `'problem'`.

- 
variables (optional): `object`
Variable definitions for the form.

- 
variableSets (optional): `{ variableSet: string | VariableSet; order: number }[]`
Variable set references.

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

## Field Mapping Methods

| Scenario | Recommended Method |
| Simple text/choice mapping | `mapToField: true` |
| System values (gs.getUserID()) | Script |
| Conditional logic | Script |
| Calculated values | Script |
| Variables in Variable Sets | Script |

## Script Types

| Script | Timing | Can call update()? |
| `script` | Before insert | No |
| `postInsertScript` | After insert | Yes |
| `saveScript` | On step save | No |

### Available Script Objects

| Object | Description |
| `current` | GlideRecord of the record being created |
| `producer.var_name` | Form variable values |
| `cat_item` | Record Producer definition (postInsertScript only) |
| `gs` | GlideSystem |

### Script Rules

- 
Never call `current.update()` or `current.insert()` in pre-insert script

- 
Never call `current.setAbortAction()`

- 
Never set `current.sys_class_name`

- 
Use `postInsertScript` for post-creation updates, related records, notifications

## Unsupported Tables

Do not create record producers for:

- `sc_request`, `sc_req_item`, `sc_task` — Use Catalog Items instead.

## Common User Requests Mapping

| User Request | Agent Implementation |
| "Report an incident from catalog" | Record Producer targeting incident table |
| "Submit a change request" | Record Producer targeting change_request table |
| "Report a problem" | Record Producer targeting problem table |
| "Create record with auto-fill" | Record Producer with pre-insert script |

## Quick Reference

### ALWAYS

- Use `mapToField: true` for simple field mappings

- Use `Now.include(...)` for external script files

- Use `postInsertScript` for post-creation updates and related records

- Set `redirectUrl: "generatedRecord"` to redirect to the created record

### NEVER

- Call `current.update()` or `current.insert()` in pre-insert script

- Call `current.setAbortAction()` in Record Producer scripts

- Set `current.sys_class_name` in scripts

- Create Record Producers for `sc_request`, `sc_req_item`, `sc_task`

## Usage

### When to Use Record Producer vs Catalog Item

Use `CatalogItemRecordProducer` when the catalog submission should create a record in a specific table — incident, change request, task, or a custom table. Use `CatalogItem` for items that fulfill via order tasks and fulfillment workflows.

### Mapping Variables to Record Fields

The `mapToField` and `field` properties on variables automatically populate fields on the created record from user-entered variable values. This is the primary way to transfer form input to the target record — no script required.

See the Service Catalog Variables Guide for the full list of variable properties including `mapToField` and `field`.

### Script Execution Order

When a record producer is submitted, scripts run in this order:

| Order | Script | When | `cat_item` available? |
| 1 | `saveScript` | On each step save in Catalog Builder | Yes |
| 2 | `script` | Before the record is inserted | No |
| — | (mapToField applied automatically) | After `script` , before `postInsertScript` | — |
| 3 | `postInsertScript` | After the record is inserted | Yes |

### Available Script Objects

| Object | Type | Available in |
| `producer` | `RecordProducerContext` | All scripts |
| `current` | `GlideRecord` | All scripts |
| `cat_item` | `RecordProducerDefinition` | `saveScript` , `postInsertScript` only |

`cat_item` is not injected into `script`. If you need the Record Producer definition after insert, use `postInsertScript`.

See the Service Catalog Guide — Record Producer section for a full walkthrough of script patterns.

## See

- Service Catalog Guide — Record Producer patterns, `mapToField` and script interaction

- Service Catalog Variables Guide — All variable types and variable properties (`mapToField`, `field`, etc.)

- https://docs.servicenow.com/csh?topicname=c_CreatingARecordProducer.html&version=latest

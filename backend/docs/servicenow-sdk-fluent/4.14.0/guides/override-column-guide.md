Version: 4.14.0

# Overriding Inherited Columns

Guide for using `OverrideColumn` to modify properties of columns inherited from a parent table. When you extend a table using `extends`, you inherit all columns from the parent. Use `OverrideColumn` to change how these inherited fields behave on the child table without modifying the parent table's definition.

## When to Use

Use OverrideColumn for static/unconditional inherited field behavior:

- Making an inherited field mandatory on a child table while leaving it optional on the parent (unconditional — applies to ALL records)

- Changing the read-only behavior of an inherited field (e.g., making state always read-only in a specific child table)

- Setting static default values for inherited fields

- Filtering reference fields with static encoded queries (e.g., "active=true^roles=itil")

- Overriding calculation scripts for inherited calculated fields

- Changing dependent field settings on inherited fields

- Controlling whether an inherited field is displayed in the UI

- Modifying field attributes (edge encryption, sort behavior, display options)

Use Business Rules/UI Policies/Data Policies instead for conditional/dynamic behavior:

- Conditional enforcement: "mandatory if severity is Critical", "read-only if state is Closed"

- Dynamic filtering: "filter references based on current user's department" (use `javascript:` in `referenceQualifier`)

- Complex validation logic beyond mandatory/read-only

- Field value manipulation or calculations based on other fields

Do NOT use OverrideColumn when:

- Creating a new column (use the appropriate column type like `StringColumn`, `ReferenceColumn`, etc.)

- Adding fields to a table you don't extend (use regular column definitions or see the `table-augments-guide` topic)

- Modifying a field on the parent table itself (edit the parent table's definition directly)

- The field doesn't exist in any parent table (validate field existence first — see Field Validation section)

## Instructions

- Use `OverrideColumn` inside the table's `schema`: Dictionary overrides are defined directly in the `Table` object's `schema` property, using the inherited field name as the key. This requires the table to have `extends` set.

- `baseTable` is optional: Omit `baseTable` when the field belongs to the table referenced in `extends`. Specify it explicitly when the field is defined further up the inheritance chain (e.g., `task` rather than `incident`).

- Override selectively: Only set the properties you need to change. Unset properties inherit from the base table.

- Table must extend a base table: `OverrideColumn` only works in tables that have `extends`. For non-extended tables, modify the field definition directly.

- Import `OverrideColumn`: Import it from `@servicenow/sdk/core` alongside `Table`.

## Key Concepts

`OverrideColumn` creates a `sys_dictionary_override` record in ServiceNow. This record modifies how an inherited column behaves on a child table without changing the parent table's column definition. The parent table and other child tables are unaffected.

Table inheritance requirements:

- The `baseTable` must be a parent table in the inheritance hierarchy

- The schema key (e.g., `priority`) must be a field defined in the base table

- The `Table` must have `extends` pointing to a table that is extensible

### Available Override Properties

| Property | Applies To | Description |
| `mandatory` | All fields | Make the field required or optional |
| `default` | All fields | Change the default value (use `default` , not `defaultValue` ) |
| `display` | One field per table (display value) | Set this inherited field as the table's display value (primary identifier). Controls which column serves as the record's primary identifier, not UI visibility. |
| `readOnlyOption` | All fields | Control read-only access (see options below) |
| `attributes` | All fields | Change field attributes as a key-value object (e.g., `{ edge_encryption_enabled: true }` ) |
| `referenceQualifier` | Reference fields | Filter reference field options using encoded queries or dynamic JavaScript qualifiers |
| `dependent` | Choice fields | Set dependent field for cascading selects |
| `calculation` | Calculated fields | Change the calculation script for calculated fields |

#### Read-only options

The `readOnlyOption` property accepts the following values:

| Use Case | Option | Behavior |
| Backwards compatibility (default) | `'instance_configured'` | System property controls behavior |
| UI read-only, allow all programmatic updates | `'display_read_only'` | Modified by Client scripts or server-side operations |
| UI read-only, only client scripts can update | `'client_script_modifiable'` | Client scripts allowed, server-side APIs blocked |
| Completely locked, no updates allowed | `'strict_read_only'` | All modifications prevented |

#### Reference qualifier examples

When using `referenceQualifier`, you can:

- Use simple encoded queries: `"active=true^roles=itil"`

- Use dynamic qualifiers with `javascript:` prefix when filtering depends on:

- Current record values: `"javascript:'active=true^location=' + current.getValue('location')"`

- User context: `"javascript:'active=true^department=' + gs.getUser().getDepartmentID()"`

- Complex business logic that cannot be expressed as a static query

#### 🔍 Attribute Selection Guide

When using the `attributes` property in `OverrideColumn`, common available attributes can be found in the tables below organized by field type. Match attribute names exactly (case-sensitive) and use the correct value types.

##### Reference field attributes

| Attribute | Value | Description |
| `ref_ac_columns` | semicolon-separated field names | Additional columns shown in the autocomplete dropdown (e.g., `"name;email"` ). Requires `ref_auto_completer: "AJAXTableCompleter"` . |
| `ref_ac_columns_search` | `true` / `false` | Enables autocomplete to search across all `ref_ac_columns` , not just the display value column. |
| `ref_ac_display_value` | `true` / `false` | Hides the display value column in autocomplete, showing only `ref_ac_columns` matches. Requires `AJAXTableCompleter` . |
| `ref_ac_order_by` | field name | Column used to sort the autocomplete list. |
| `ref_auto_completer` | JS class name | Custom autocomplete class. Options: `AJAXReferenceCompleter` (list, display value only), `AJAXTableCompleter` (table with extra columns), `AJAXReferenceChoice` (list, max 25 results). |
| `ref_contributions` | semicolon-separated UI macro names | Invokes the named UI macros when the reference field renders on a form. |
| `ref_decoration_disabled` | `true` / `false` | Disables the reference icon displayed next to a populated reference field. |
| `ref_qual_elements` | semicolon-separated field names | Fields sent back to the server to recalculate the reference qualifier dynamically. |
| `ref_sequence` | caret-separated field names ( `^` ) | Fields in the referenced table used to order the reference list (equivalent to `ORDER BY` ). |
| `tree_picker` | `true` / `false` | Displays the reference field as a hierarchical tree (e.g., for location or category fields). |
| `short_label` | `true` / `false` | Shows the short label for a reference field (e.g., `Email` instead of `Caller Email` ). Overrides the global `glide.short.labels` property. |
| `long_label` | `true` / `false` | Shows the long label for a reference field (e.g., `Caller Email` ). Overrides the global `glide.short.labels` property. |
| `slushbucket_ref_no_expand` | `true` / `false` | Prevents users from expanding the reference in a form or list slush bucket. |
| `allow_references` | `true` / `false` | Displays a tree with reference fields so users can dot-walk when selecting a value. |

##### List field attributes (`glide_list`)

| Attribute | Value | Description |
| `maintain_order` | `true` / `false` | Shows up/down arrow buttons to reorder items in the list. Requires using the Add Multiple button. |
| `no_multiple` | `true` / `false` | Hides the select-multiple icons on a list field. |
| `no_view` | `true` / `false` | Hides the view-selected-item icon on a list field. |
| `no_email` | `true` / `false` | Removes the email box from a `glide_list` field referencing `sys_user` (e.g., Watch List). |
| `start_locked` | `true` / `false` | Sets the list field as locked by default. Set to `false` to unlock by default. |
| `field_list_selector` | `true` / `false` | Enables the user to select a field from the dependent table (or current table if no dependent is set). |

#### String and text field attributes

| Attribute | Value | Description |
| `no_truncate` | `true` / `false` | Shows the full text value in list views without truncation (default truncation is 40 characters). |
| `html_sanitize` | `true` / `false` | Enables or disables HTML sanitization on HTML/Translated HTML fields. Sanitization is on by default; set to `false` to disable. |
| `strip_html_in_pdf` | `true` / `false` | Strips HTML tags from the field value when exporting to PDF. |
| `ro_collapsible` | `true` / `false` | Adds an expand/collapse toggle icon next to a multiline field label. |
| `allow_null` | `true` / `false` | Allows the user to set the field value to `None` . |
| `barcode` | `true` / `false` | Enables a string field to use a mobile camera to scan and populate a barcode value. |
| `knowledge_search` | `true` / `false` | Shows a knowledge base search icon next to the field. Clicking it opens a knowledge search popup. |
| `i18n_session_language_sortable` | `true` / `false` | Enables sorting the column by the user's session language. When `false` , sorting follows the English alphabet. |

##### Numeric and decimal field attributes

| Attribute | Value | Description |
| `scale` | integer | Number of decimal places for a `Decimal` field. Default is `2` . Requires `maxLength` to be increased accordingly (e.g., 4 decimal places needs `maxLength` > 15). |
| `omit_sys_original` | `true` / `false` | Skips retrieving the original value during calculations on price/currency fields, improving performance on high-volume tables. |

#### General field attributes

| Attribute | Value | Description |
| `no_audit` | `true` / `false` | Excludes this field from auditing even when the table is audited. |
| `no_text_index` | `true` / `false` | Prevents this field from being included in the table's text index. |
| `isOrder` | `true` / `false` | Sets this field as the default sort column in list views. Can be overridden by the `ORDERBY` URL parameter or user sort preferences. |
| `user_preference` | `true` / `false` | Uses the user's saved preferences for this field's default value instead of the system default. |
| `ts_weight` | integer | Controls the relative importance of text search matches in this field. Higher values rank this field's matches higher in search results. |
| `ignore_filter_on_new` | `true` / `false` | Prevents the field from auto-populating with values from a filtered list when creating a new record. |
| `field_decorations` | semicolon-separated UI macro names | Invokes the named UI macros when the field renders on a form. Similar to `ref_contributions` but for non-reference fields. |
| `table` | table name | For `FieldListColumn` — specifies which table's fields to populate the list from (e.g., `"task"` ). |
| `vertical_layout` | `true` / `false` | Displays radio button choices vertically instead of horizontally. |
| `edge_encryption_enabled` | `true` / `false` | Enables Edge Encryption for this field. Requires Edge Encryption to be configured on the instance. |

### ⚠️ CRITICAL: Field validation and baseTable selection

You MUST confirm the field exists in the base table or an ancestor before using `OverrideColumn`:

- Start with the table specified in `extends` as the initial base table to check.

- Use your knowledge of the ServiceNow table hierarchy to determine which table defines the field. Common fields and their defining tables for frequently-extended tables:

- Fields on `task`: `priority`, `state`, `assigned_to`, `assignment_group`, `short_description`, `description`, `number`, `active`, `opened_by`, `closed_at`, `work_notes`, `comments`

- Fields on `incident` (extends `task`): `caller_id`, `category`, `subcategory`, `impact`, `urgency`, `severity`, `business_impact`, `resolve_time`

- Fields on `sys_user`: `user_name`, `first_name`, `last_name`, `email`, `department`, `manager`, `roles`

- If the field's origin is unclear from the task description or platform documentation, check the System Dictionary (`sys_dictionary` table) in your ServiceNow instance, filtering by the base table name and field name.

- Continue up the inheritance chain (e.g., `incident` → `task`) until the field is found or no more parent tables exist.

- When the field is found, set `baseTable` in `OverrideColumn` to the table where the field was found (only if different from `extends`).

- If the field is not found in any table in the inheritance chain, do NOT use `OverrideColumn` for that field. Instead, create a new field with the appropriate type in the table's `schema`.

## Examples

### Example 1: Making an Inherited Field Mandatory

```
import { Table, OverrideColumn } from "@servicenow/sdk/core";

export const x_myapp_custom_incident = Table({
  name: "x_myapp_custom_incident",
  extends: "incident",
  schema: {
    short_description: OverrideColumn({
      mandatory: true
    })
  }
});
```

### Example 2: Changing Default Value

```
import { Table, OverrideColumn } from "@servicenow/sdk/core";

export const x_myapp_vip_task = Table({
  name: "x_myapp_vip_task",
  extends: "task",
  schema: {
    priority: OverrideColumn({
      default: "1"
    })
  }
});
```

### Example 3: Overriding Reference Qualifier

```
import { Table, OverrideColumn } from "@servicenow/sdk/core";

export const x_myapp_special_incident = Table({
  name: "x_myapp_special_incident",
  extends: "incident",
  schema: {
    assignment_group: OverrideColumn({
      referenceQualifier: "roles=itil^active=true^type=support"
    })
  }
});
```

### Example 3a: Advanced Reference Qualifier with Current Record Context

```
import { Table, OverrideColumn } from "@servicenow/sdk/core";

export const x_myapp_department_incident = Table({
  name: "x_myapp_department_incident",
  extends: "incident",
  schema: {
    assigned_to: OverrideColumn({
      baseTable: "task",
      referenceQualifier:
        "javascript:'active=true^department=' + current.getValue('u_department')"
    })
  }
});
```

### Example 3b: Advanced Reference Qualifier with Dynamic Field Reference

```
import { Table, OverrideColumn } from "@servicenow/sdk/core";

// Note: location field is inherited from task table
export const x_myapp_location_incident = Table({
  name: "x_myapp_location_incident",
  extends: "incident",
  schema: {
    assigned_to: OverrideColumn({
      baseTable: "task",
      referenceQualifier:
        "javascript:'active=true^location=' + current.getValue('location')"
    }),
    assignment_group: OverrideColumn({
      referenceQualifier:
        "javascript:'active=true^u_location=' + current.getValue('location') + '^u_support_type=' + current.getValue('category')"
    })
  }
});
```

### Example 4: Overriding Read-Only Option

```
import { Table, OverrideColumn } from "@servicenow/sdk/core";

export const x_myapp_approved_change = Table({
  name: "x_myapp_approved_change",
  extends: "change_request",
  schema: {
    state: OverrideColumn({
      readOnlyOption: "display_read_only" // appears read only, but can be modified by business rules and client script
    })
  }
});
```

### Example 5: Changing Calculation

```
import { Table, OverrideColumn } from "@servicenow/sdk/core";

export const x_myapp_custom_user = Table({
  name: "x_myapp_custom_user",
  extends: "sys_user",
  schema: {
    name: OverrideColumn({
      calculation:
        "current.last_name + ', ' + current.first_name + ' (' + current.employee_number + ')'"
    })
  }
});
```

### Example 6: Multiple Property Overrides

```
import { Table, OverrideColumn } from "@servicenow/sdk/core";

export const x_myapp_locked_task = Table({
  name: "x_myapp_locked_task",
  extends: "task",
  schema: {
    state: OverrideColumn({
      readOnlyOption: "strict_read_only", // strict read only, cannot be modified.
      mandatory: true,
      default: "1"
    })
  }
});
```

### Example 7: Overriding Dependent Field

```
import { Table, OverrideColumn } from "@servicenow/sdk/core";

export const x_myapp_custom_incident = Table({
  name: "x_myapp_custom_incident",
  extends: "incident",
  schema: {
    subcategory: OverrideColumn({
      dependent: "u_custom_category"
    })
  }
});
```

### Example 8: Changing Field Attributes (field on direct extends table)

```
import { Table, OverrideColumn } from "@servicenow/sdk/core";

// caller_id is defined on incident — no baseTable needed.
export const x_myapp_secure_incident = Table({
  name: "x_myapp_secure_incident",
  extends: "incident",
  schema: {
    caller_id: OverrideColumn({
      referenceQualifier: "active=true^department=IT",
      attributes: { ref_auto_completer: "AJAXTableCompleter" }
    })
  }
});
```

### Example 9: baseTable Different from extends

When a table extends an intermediate table (e.g., `incident` extends `task`), and the field is defined on the grandparent, `baseTable` must point to the table where the field is actually defined — not the direct parent in `extends`.

```
import { Table, OverrideColumn } from "@servicenow/sdk/core";

// x_myapp_secure_incident extends incident, but description is defined on task.
// baseTable must be "task", not "incident".
export const x_myapp_secure_incident = Table({
  name: "x_myapp_secure_incident",
  extends: "incident",
  schema: {
    description: OverrideColumn({
      baseTable: "task",
      attributes: { edge_encryption_enabled: true }
    })
  }
});
```

### Example 10: Complete Override with baseTable

```
import { Table, OverrideColumn, StringColumn } from "@servicenow/sdk/core";

export const x_myapp_custom_task = Table({
  name: "x_myapp_custom_task",
  extends: "task",
  schema: {
    assigned_to: OverrideColumn({
      baseTable: "task",
      mandatory: true,
      default: "javascript:gs.getUserID()",
      referenceQualifier: "active=true",
      attributes: { ref_auto_completer: "AJAXTableCompleter" }
    }),
    custom_field: StringColumn({ label: "Custom Field" })
  }
});
```

## Avoidance

- ⚠️ CRITICAL: Never create business rules, client scripts, or UI policies for static inherited field behavior that OverrideColumn supports — always prefer declarative overrides (`mandatory`, `default`, `readOnlyOption`, `referenceQualifier`, `attributes`) over imperative workarounds for unconditional requirements

- Never use OverrideColumn for new columns — use the appropriate column type (`StringColumn`, `ReferenceColumn`, etc.) instead

- Never omit baseTable on multi-level inheritance — when extending a table that itself extends another table, always specify which table defines the column

- Never override a column that doesn't exist on the parent — the field must be validated to exist in the base table or any ancestor table before using OverrideColumn

- Never use OverrideColumn without `extends` — if the table doesn't extend another table, there are no inherited columns to override

- Never use attributes that don't exist in `sys_schema_attribute` table — the attribute must be defined in ServiceNow's attribute catalog

## Related Topics

- `overridecolumn-api` — OverrideColumn API reference and property details

- `table-guide` — Creating and extending tables

- `table-api` — Full Table API reference

- `referencecolumn-api` — Creating new reference columns

- `data-policy-guide` — Conditional mandatory/read-only enforcement

- `ui-policy-guide` — Client-side field behavior

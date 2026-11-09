Version: 4.14.0

# Field Styles

Guide for creating ServiceNow Field Styles using the Record API. Field styles apply CSS styling to fields in list and form views based on field values or scripted conditions.

## When to Use

- Highlighting list cells with background colors based on field values (e.g., red for critical priority)

- Styling the field's text — bold, italic, color, font size, strikethrough, underline — based on field values, independent of background color

- Setting column widths or text alignment in list views

- Adding visual indicators like icons to fields based on conditions

- Applying themed CSS styles with design token variables for Polaris compatibility

The `style`/`themed_style` fields are not limited to `background-color`. Any standard CSS property is valid — `font-weight`, `font-style`, `color`, `font-size`, `text-decoration`, `text-align`, `width`, `border`, etc. See the "Column Width," "Text Alignment," "Text Styling Without Background Color," and "Strikethrough and Underline" examples below.

## Instructions

- Each field style must have a unique `$id` using `Now.ID['value']` format.

- Set `table: 'sys_ui_style'` for all field style records.

- Provide a valid `name` — the table name this style applies to.

- Set `element` — the field name on the table to style.

- The `value` field controls where the style applies:

- Static value (e.g., `'1'`) — style applies in list view only when the field equals this value.

- JavaScript condition (e.g., `'javascript:current.priority == 1'`) — style applies in list view only when the script returns true.

- Empty — style applies to form view unconditionally; in list view, only applied when the field value itself is null/empty. Use `value: 'javascript:1==1;'` if you need unconditional list-view application.

- The `style` field contains standard CSS (e.g., `'background-color:tomato'`).

- The `themed_style` field is optional — use it for Polaris-themed CSS with `--now-color_*` design tokens.

## Property Reference

Field styles are created using the `Record()` API with `table: 'sys_ui_style'`. For complete property information:

- Record API: See the record-api topic for implementing records with the `Record()` function

- Build-time validation: The compiler provides type checking and property validation based on the table schema

- Instance metadata: Query your ServiceNow instance dictionary for `sys_ui_style` to see all available fields

## Key Properties

| Property | Type | Max Length | Description |
| `name` | `table_name` | 80 | Table name this style applies to (e.g., `'incident'` , `'change_task'` ) |
| `element` | `field_name` | 80 | Field name to style (e.g., `'state'` , `'priority'` ) |
| `value` | `string` | 250 | Trigger condition: a static value, `javascript:` expression, or empty (applies to form unconditionally and to list when field is null/empty) |
| `style` | `string` | 1000 | CSS style to apply (e.g., `'background-color:tomato'` ) |
| `themed_style` | `string` | 1000 | Polaris-themed CSS override using `--now-color_*` design tokens |
| `alt` | `translated_text` | 100 | Alternative text describing the style, shown to screen readers (e.g., for icons set via `background-image` ) |

## Value Field Behavior

| `value` content | List View | Form View |
| Static value (e.g., `'1'` ) | Applied when field matches | Not applied (unless field is read-only) |
| `javascript:` condition | Applied when script returns true | Not applied |
| Empty | Applied when field value is null/empty | Applied unconditionally |

Note: `value: ''` serializes to `<value/>` and imports as `null`. For layout styles (`width`, `text-align`) that must apply unconditionally in list view, use `value: 'javascript:1==1;'` — it always evaluates `true`, applying the style to every row. Empty values only apply to list cells where the field value itself is null/empty.

Polaris Note: On Polaris-themed instances, `background-color` styles render as a colored dot indicator next to the field value in list views, rather than filling the entire cell. Other CSS properties such as `font-weight`, `text-align`, and `width` are not affected.

## Examples

### Conditional List Styling (Background Color by State)

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['style_change_task_state_open'],
    table: 'sys_ui_style',
    data: {
        name: 'change_task',
        element: 'state',
        value: '1',
        style: 'background-color:LimeGreen',
    },
})

Record({
    $id: Now.ID['style_change_task_state_closed'],
    table: 'sys_ui_style',
    data: {
        name: 'change_task',
        element: 'state',
        value: '7',
        style: 'background-color:SkyBlue',
    },
})
```

### Column Width in List View

Column width styles set the width of a column in list views. Use `value: 'javascript:1==1;'` to apply the width unconditionally to all rows.

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['style_dictionary_dynamic_ref_qual_width'],
    table: 'sys_ui_style',
    data: {
        name: 'sys_dictionary',
        element: 'dynamic_ref_qual',
        value: 'javascript:1==1;',
        style: 'width:240px;',
    },
})
```

Narrow columns work the same way — set a smaller pixel width:

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['style_checkout_status_width'],
    table: 'sys_ui_style',
    data: {
        name: 'x_acme_checkout',
        element: 'status',
        value: 'javascript:1==1;',
        style: 'width:80px;',
    },
})
```

### Text Alignment in List View

Text alignment styles apply to columns in list views. Use `value: 'javascript:1==1;'` to apply unconditionally to all rows:

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['style_sales_report_amount_align'],
    table: 'sys_ui_style',
    data: {
        name: 'x_acme_sales_report',
        element: 'amount',
        value: 'javascript:1==1;',
        style: 'text-align:right;',
    },
})
```

### Text Styling Without Background Color (Bold, Italic, Color, Size)

Style the text itself by combining font CSS properties — no `background-color` required:

```
import { Record } from '@servicenow/sdk/core'

// Overdue items: bold red text
Record({
    $id: Now.ID['style_task_overdue_text'],
    table: 'sys_ui_style',
    data: {
        name: 'x_acme_task',
        element: 'due_date',
        value: 'javascript:current.due_date < gs.nowDateTime() && current.state != "Complete"',
        style: 'color:red;font-weight:bold;',
    },
})

// Completed items: italic green text
Record({
    $id: Now.ID['style_task_completed_text'],
    table: 'sys_ui_style',
    data: {
        name: 'x_acme_task',
        element: 'state',
        value: 'Complete',
        style: 'color:green;font-style:italic;',
    },
})
```

### Strikethrough and Underline (text-decoration)

```
import { Record } from '@servicenow/sdk/core'

// Cancelled orders: strikethrough
Record({
    $id: Now.ID['style_order_cancelled_strikethrough'],
    table: 'sys_ui_style',
    data: {
        name: 'x_acme_order',
        element: 'state',
        value: 'Cancelled',
        style: 'text-decoration:line-through;',
    },
})

// Flagged orders: underline
Record({
    $id: Now.ID['style_order_flagged_underline'],
    table: 'sys_ui_style',
    data: {
        name: 'x_acme_order',
        element: 'flagged_for_review',
        value: 'true',
        style: 'text-decoration:underline;',
    },
})
```

### Themed Style with Polaris Design Tokens

This technique applies to regular fields only. It does not work for the reserved `work_notes`/`comments` fields — see "Activity and Work Notes Styling" below.

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['style_incident_priority_critical'],
    table: 'sys_ui_style',
    data: {
        name: 'incident',
        element: 'priority',
        value: '1',
        style: 'background-color:tomato;',
        themed_style: 'background-color: RGB(var(--now-color_alert--critical-0, 226,63,74))',
    },
})
```

### JavaScript Condition

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['style_incident_vip_caller'],
    table: 'sys_ui_style',
    data: {
        name: 'incident',
        element: 'caller_id',
        value: 'javascript:current.caller_id.vip == true',
        style: 'background-image: url(images/icons/vip.gif); background-position: right; background-repeat: no-repeat;',
        alt: 'VIP caller',
    },
})
```

## Important Notes

### Styling Limitations

- Polaris/Next Experience: `background-color` styles render as dot indicators in Polaris rather than filling cells.

- Choice/select fields on forms: `sys_ui_style` does not apply background colors to choice-type fields (like State) on forms. Styles on these fields only render in list views.

- Read-only fields: When a field is read-only, the `value` condition affects both list and form views (not just the list).

- Scope restrictions: Field styles can only be defined for tables and database views in the same scope as the field style, or for tables that have at least one field in the same scope. Field styles defined for a table do not apply to database views that include the table — create separate field styles for database views.

- Single JavaScript condition: The `value` field supports only one `javascript:` entry. To combine multiple conditions, consolidate them into a single expression (e.g., `'javascript:current.state == "Completed" && current.error_tables > 0'`).

### Activity and Work Notes Styling

The two reserved, out-of-box `task` fields — `work_notes` and `comments` (Additional Comments) — are a special case. Their activity stream entries are not styled with `sys_ui_style`. Instead, only the entry's background color can be changed, and only by setting a system property in global scope:

| Property | Description |
| `glide.ui.activity_stream.style.work_notes` | Background color for work notes entries in the activity stream |
| `glide.ui.activity_stream.style.comments` | Background color for additional comments entries in the activity stream |

Set these with the `Property()` API or `Record()` with `table: 'sys_properties'`, in global scope — see the `property-guide` topic.

This restriction applies only to these two reserved fields. Any custom journal field you create (e.g. `internal_notes`) is not affected — style its row/list cell with a normal `sys_ui_style` record like any other field (see examples above). See the `table-guide` topic for creating journal fields.

## See Also

- `record-api` — Generic `Record()` API reference

- `table-guide` — Creating journal fields (comments, work notes, discussion threads) and other column types

- `property-guide` — System properties configuration

- `form-layout-guide` — Form layout and section configuration

- https://www.servicenow.com/docs/r/platform-administration/t_DefineFieldStyles.html

Version: 4.14.0

# Form Layout

Guide for creating ServiceNow form layouts using the Form API. Forms define which fields, annotations, formatters, and embedded lists appear on a record's form view and how they are arranged.

## When to Use

- Defining what fields appear on a record form and in what order

- Organizing fields into sections with one-column or two-column layouts

- Adding informational annotations (banners, warnings, instructions)

- Embedding related record lists directly within a form section

- Adding formatters (activity streams, attached knowledge) to a form

- Creating role-restricted or user-specific form layouts

## Instructions

- Choose the view first: Use `default_view` for the default layout, or create a `Record<'sys_ui_view'>` for a custom view. The same view const works with both `Form()` and `List()`.

- Organize sections logically: Header/details first, notes/activity in the middle, related lists at the bottom. Use descriptive captions (e.g., `'Assignment'`, not `'Section 1'`).

- Pick the right layout block: Use `two-column` for 4+ short fields (dropdowns, references). Use `one-column` for text areas, formatters, annotations, and embedded lists.

- Set the element type: Every element needs a `type` discriminator: `'table_field'`, `'annotation'`, `'formatter'`, or `'list'`.

- Import only what you use: Import `AnnotationType`, `Formatter`, `default_view`, or `Record` only if actually used — unused imports cause build issues.

- Avoid duplicates: Each field should appear only once per section.

- Dedicate sections to special elements: Formatters and embedded lists work best in their own sections, never mixed with regular fields.

## API Reference

See the `form-api` topic for the full property reference, including `FormSection`, `LayoutBlock`, and `FormElement` types.

## Key Concepts

### Record Hierarchy

The Form API creates a hierarchy of ServiceNow records automatically:

| Record | Table | Description |
| Form | `sys_ui_form` | Main form record linking a table to a view |
| Form Section Link | `sys_ui_form_section` | Join table linking form to sections (with position) |
| Section | `sys_ui_section` | Section records with caption, header, and view |
| Element | `sys_ui_element` | Individual field elements within sections |
| Annotation | `sys_ui_annotation` | Annotation records (when `type: 'annotation'` ) |

You only define sections in the `sections` array — the Form API creates the link records for you.

### Layout Blocks

Each section's `content` array contains one or more layout blocks:

One-column — elements stacked vertically:

```
{ layout: 'one-column', elements: [/* elements */] }
```

Two-column — elements split left/right (maps to `.begin_split`/`.split`/`.end_split` in ServiceNow):

```
{ layout: 'two-column', leftElements: [/* left */], rightElements: [/* right */] }
```

A section can contain multiple layout blocks to create mixed layouts (e.g., a two-column block followed by a one-column block for a text area).

### Layout Decision Guide

| Condition | Layout |
| 1–3 fields in a section | `one-column` |
| 4+ short fields of similar length | `two-column` |
| Text areas, descriptions, notes | `one-column` always |
| Formatters and embedded lists | `one-column` in a dedicated section |
| Fields are logically paired (start/end date) | `two-column` |

### Element Types

| Type | Key Properties | Description |
| `table_field` | `field` , `type` | Table column field |
| `annotation` | `annotationId` , `text` , `isPlainText?` , `annotationType?` | Informational text banner |
| `formatter` | `formatterRef` , `formatterName?` | UI formatter (activity stream, knowledge, etc.) |
| `list` | `listType` , `listRef` | Embedded related list (12M, M2M, or custom) |

### Annotations

Annotations display informational text not tied to any table field. The Form API creates both a `sys_ui_annotation` record and a `sys_ui_element` linking it to the section.

| Property | Required | Description |
| `annotationId` | Yes | `Now.ID['<unique_key>']` — becomes the annotation record's sys_id |
| `text` | Yes | Content (plain text or HTML) |
| `isPlainText` | No | `true` (default) for plain text, `false` for HTML |
| `annotationType` | No | `AnnotationType` constant or `Record<'sys_ui_annotation_type'>` . Default: `AnnotationType.Info_Box_Blue` |

Available AnnotationType constants (import from `@servicenow/sdk/core`):

| Constant | Description |
| `AnnotationType.Info_Box_Blue` | Blue info box (default) |
| `AnnotationType.Info_Box_Red` | Red info box |
| `AnnotationType.Line_Separator` | Horizontal line |
| `AnnotationType.Plain_Text` | Plain text (left-padded) |
| `AnnotationType.Section_Details` | Section details |
| `AnnotationType.Section_Plain_Text` | Plain text in section |
| `AnnotationType.Section_Separator` | Section separator |
| `AnnotationType.Text` | Basic text |

### Embedded Lists

Embedded lists display child or associated records directly in a form section. All three types require `type: 'list'`.

| List Type | `listRef` Format | When to Use |
| `12M` | `'<child_table>.<ref_column>'` | Child table has a reference field pointing to parent |
| `M2M` | `'<join_table>.<ref_column>'` | Join table connects two tables via reference fields |
| `custom` | `Record<'sys_relationship'>` or GUID string | No reference field, platform tables, or OOB relationships |

Always search for existing relationships before creating new `sys_relationship` records. Platform tables like `sys_attachment`, `sys_audit`, and `sys_journal_field` use polymorphic string fields and always require `custom` type.

### Platform Tables

Platform tables use polymorphic string fields (not reference fields) and always require `custom` list type:

- `sys_attachment` — file attachments

- `sys_audit` — audit history

- `sys_journal_field` — journal entries (comments, work notes)

- `sys_history_line` — history records

- `approval_approver` — approval records

- `sys_email` — email records

- `wf_activity` — workflow activities

Always use `listType: 'custom'` with a `Record<'sys_relationship'>` reference for these tables.

### Verification Before Adding Embedded Lists

Before adding an embedded list, verify the relationship and target table exist:

- 
Search existing relationships: Query `sys_relationship` where `basic_apply_to=<parent>^basic_query_from=<child>`, retrieving `sys_id` and `name` (see the `query` topic).

- 
Verify target table exists: Query `sys_db_object` where `name=<child_table>`, retrieving `sys_id`, `name`, and `label` (see the `query` topic).

- 
Check field structure: Query `sys_dictionary` where `name=<child_table>^element=<ref_field>^internal_type=reference`, retrieving `element` and `reference` (see the `query` topic).

This workflow prevents build errors from missing relationships or tables.

### Common OOB Relationships

Query `sys_relationship` for out-of-box relationships using these encoded query filters (see the `query` topic):

| Purpose | Encoded Query |
| Audit History | `basic_query_from=sys_audit` |
| Attachments | `basic_query_from=sys_attachment` |
| Comments/Work Notes | `basic_query_fromLIKEjournal` |
| Approvals | `basic_query_from=approval_approver` |
| Workflows | `basic_query_from=wf_activity` |

Use the returned `sys_id` values in `listRef` for `custom` type embedded lists.

### Migrating from Record API to Form API

When to convert: When the codebase has `Record()` calls for `sys_ui_section` + `sys_ui_element` and the user wants to add new sections, elements, annotations, or formatters.

5-Step Conversion Algorithm:

- 
Extract section metadata from `sys_ui_section` Record → `caption`, `header`, `title`; map `data.view` to a view Record const (not string)

- 
Sort `sys_ui_element` Records by `data.position` (ascending)

- 
Group elements into layout blocks by processing split markers:

- `.begin_split` → flush buffer, collect left until `.split`, right until `.end_split` → two-column block

- Lone `.split` (no `.begin_split`) → buffer becomes left, collect right until next split marker → two-column block (stopping marker NOT consumed)

- `.end_split` at top level → silently ignored

- No markers → one-column block

- 
Map element types:

- `sys_ui_element` with `data.type='field'` → `{ field: data.element, type: 'table_field' }`

- `sys_ui_annotation` → `{ type: 'annotation', annotationId, text, isPlainText, annotationType }`

- `sys_ui_formatter` → `{ type: 'formatter', formatterRef }`

- Embedded list → `{ type: 'list', listType, listRef }`

- 
Convert formatter GUIDs to constants:

- `444ea5c6bf310100e628555b3f0739d6` → `Formatter.Activities_Filtered`

- `cfa76e850a0a0b1f01446f67c8538d00` → `Formatter.Attached_Knowledge`

Formatter GUID → Name lookup (globally available):

- `444ea5c6bf310100e628555b3f0739d6` → `Formatter.Activities_Filtered`

- `cfa76e850a0a0b1f01446f67c8538d00` → `Formatter.Attached_Knowledge`

Example conversion:

Before (Record API):

```
Record({ table: 'sys_ui_section', data: { name: 'details', caption: 'Details', position: 0 } })
Record({ table: 'sys_ui_element', data: { element: 'name', position: 0, type: 'field' } })
Record({ table: 'sys_ui_element', data: { element: '.begin_split', position: 1 } })
Record({ table: 'sys_ui_element', data: { element: 'state', position: 2, type: 'field' } })
Record({ table: 'sys_ui_element', data: { element: '.split', position: 3 } })
Record({ table: 'sys_ui_element', data: { element: 'priority', position: 4, type: 'field' } })
Record({ table: 'sys_ui_element', data: { element: '.end_split', position: 5 } })
```

After (Form API):

```
Form({
    sections: [{
        caption: 'Details',
        content: [
            { layout: 'one-column', elements: [{ field: 'name', type: 'table_field' }] },
            { layout: 'two-column', leftElements: [{ field: 'state', type: 'table_field' }], rightElements: [{ field: 'priority', type: 'table_field' }] }
        ]
    }]
})
```

### View Handling

Default view:

```
import { Form, default_view } from '@servicenow/sdk/core'
Form({ table: 'x_myapp_task', view: default_view, sections: [...] })
```

Custom view (canonical pattern):

```
import { Record, Form } from '@servicenow/sdk/core'

const myView = Record({
    $id: Now.ID['my_view'],
    table: 'sys_ui_view',
    data: { name: 'my_custom_view', title: 'My Custom View' },
})

Form({ table: 'x_myapp_task', view: myView, sections: [...] })
```

The same view const can be passed to `List({ view: myView })` — both APIs accept a `sys_ui_view` Record reference.

### Standard Section Layout

Common section organization pattern for task-based forms:

| Section | Position | Layout | Content |
| Header / Details | 0 | Two-column | Short fields: name, state, priority |
| Extended Details | 1 | One-column | Text areas: description, comments |
| Activity / Notes | 2 | One-column | Formatters: activity stream |
| Related Lists | 3 | One-column | Dedicated — never mix with fields |

This pattern provides a consistent user experience across applications.

### Default Form Design Heuristic

When the user specifies no explicit layout, follow this heuristic:

- Single merged section: Combine all fields into one section unless the user explicitly requests multiple sections

- Two-column for short fields: Use `two-column` layout when there are 4+ short fields (dropdowns, references, dates)

- One-column for text areas: Always use `one-column` for long text fields, HTML fields, and journal fields

- Dedicated blocks for formatters: Place formatters (activity, knowledge) in their own `one-column` blocks

- Dedicated blocks for embedded lists: Never mix embedded lists with regular fields

- Exclude extended/parent table fields: Only include fields from the target table unless explicitly requested

This heuristic ensures forms are readable and follow ServiceNow best practices.

### Section Behavior

How sections render on the form:

- Tabs: If tabs are enabled on the instance, each section appears as a separate tab

- Ordering: Sections are ordered by their position in the `sections` array (0-indexed)

- Empty sections: Sections with an empty `content` array create a section header with no elements

## Examples

### Simple Form with Default View

```
import { Form, default_view } from '@servicenow/sdk/core'

Form({
    table: 'x_myapp_task',
    view: default_view,
    sections: [
        {
            caption: 'General',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { field: 'name', type: 'table_field' },
                        { field: 'short_description', type: 'table_field' },
                        { field: 'active', type: 'table_field' },
                    ],
                },
            ],
        },
        {
            caption: 'Details',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { field: 'description', type: 'table_field' },
                        { field: 'priority', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})
```

### Two-Column Layout with Annotations and Activity Formatter

```
import '@servicenow/sdk/global'
import { Form, Record, AnnotationType, Formatter } from '@servicenow/sdk/core'

const detailedView = Record({
    $id: Now.ID['detailed-view'],
    table: 'sys_ui_view',
    data: { name: 'x_myapp_detailed', title: 'Detailed View' },
})

Form({
    table: 'x_myapp_task',
    view: detailedView,
    roles: ['admin', 'itil'],
    sections: [
        {
            caption: 'Overview',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'annotation',
                            annotationId: Now.ID['overview-banner'],
                            text: 'Complete all required fields before submitting.',
                            isPlainText: true,
                            annotationType: AnnotationType.Info_Box_Blue,
                        },
                    ],
                },
                {
                    layout: 'two-column',
                    leftElements: [
                        { field: 'name', type: 'table_field' },
                        { field: 'category', type: 'table_field' },
                    ],
                    rightElements: [
                        { field: 'priority', type: 'table_field' },
                        { field: 'assigned_to', type: 'table_field' },
                    ],
                },
                {
                    layout: 'one-column',
                    elements: [{ field: 'description', type: 'table_field' }],
                },
            ],
        },
        {
            caption: 'Activity',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { type: 'formatter', formatterRef: Formatter.Activities_Filtered },
                    ],
                },
            ],
        },
    ],
})
```

### Complete Form with Embedded Lists

```
import '@servicenow/sdk/global'
import { Form, Record, Formatter } from '@servicenow/sdk/core'

const taskToAuditRel = Record({
    $id: Now.ID['task-audit-rel'],
    table: 'sys_relationship',
    data: {
        name: 'Task Audit History',
        basic_apply_to: 'x_myapp_task',
        basic_query_from: 'sys_audit',
        advanced: false,
    },
})

const completeView = Record({
    $id: Now.ID['complete-view'],
    table: 'sys_ui_view',
    data: { name: 'x_myapp_complete', title: 'Complete View' },
})

Form({
    table: 'x_myapp_task',
    view: completeView,
    sections: [
        {
            caption: 'Details',
            content: [
                {
                    layout: 'two-column',
                    leftElements: [
                        { field: 'name', type: 'table_field' },
                        { field: 'category', type: 'table_field' },
                    ],
                    rightElements: [
                        { field: 'priority', type: 'table_field' },
                        { field: 'assigned_to', type: 'table_field' },
                    ],
                },
                {
                    layout: 'one-column',
                    elements: [{ field: 'description', type: 'table_field' }],
                },
            ],
        },
        {
            caption: 'Activity',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { type: 'formatter', formatterRef: Formatter.Activities_Filtered },
                    ],
                },
            ],
        },
        {
            caption: 'Subtasks',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { type: 'list', listType: '12M', listRef: 'x_myapp_subtask.parent_task' },
                    ],
                },
            ],
        },
        {
            caption: 'Audit History',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { type: 'list', listType: 'custom', listRef: taskToAuditRel },
                    ],
                },
            ],
        },
    ],
})
```

### HTML Annotation

Add an annotation with HTML formatting (`isPlainText: false`) to display rich text with bold, italic, and links.

```
import '@servicenow/sdk/global'
import { Form, AnnotationType, default_view } from '@servicenow/sdk/core'

Form({
    table: 'x_myapp_task',
    view: default_view,
    sections: [
        {
            caption: 'Instructions',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'annotation',
                            annotationId: Now.ID['html-annotation'],
                            text: '<b>Important:</b> Review the <a href="/kb_view.do">knowledge base</a> before proceeding.',
                            isPlainText: false,
                            annotationType: AnnotationType.Info_Box_Blue,
                        },
                        { field: 'short_description', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})
```

Result: Annotation displays with bold text and clickable link.

### Custom Annotation Type

Create a custom annotation type with custom CSS and reference it in the form.

```
import '@servicenow/sdk/global'
import { Record, Form, default_view } from '@servicenow/sdk/core'

const customAnnotationType = Record({
    $id: Now.ID['custom-warning-type'],
    table: 'sys_ui_annotation_type',
    data: {
        name: 'Custom Warning',
        style: `
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 12px;
            margin: 8px 0;
            color: #856404;
        `,
    },
})

Form({
    table: 'x_myapp_task',
    view: default_view,
    sections: [
        {
            caption: 'Task Details',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'annotation',
                            annotationId: Now.ID['custom-warning-annotation'],
                            text: 'This task requires manager approval before proceeding.',
                            isPlainText: true,
                            annotationType: customAnnotationType,
                        },
                        { field: 'short_description', type: 'table_field' },
                        { field: 'assigned_to', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})
```

Result: Annotation displays with custom yellow warning styling.

### Multiple AnnotationType

Use different annotation types across multiple sections to demonstrate Plain_Text, Line_Separator, and Section_Details.

```
import '@servicenow/sdk/global'
import { Form, AnnotationType, default_view } from '@servicenow/sdk/core'

Form({
    table: 'x_myapp_task',
    view: default_view,
    sections: [
        {
            caption: 'Text Annotations',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'annotation',
                            annotationId: Now.ID['plain-text-annotation'],
                            text: 'Plain text annotation — no HTML formatting applied.',
                            isPlainText: true,
                            annotationType: AnnotationType.Plain_Text,
                        },
                        { field: 'description', type: 'table_field' },
                    ],
                },
            ],
        },
        {
            caption: 'Separators and Section Details',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'annotation',
                            annotationId: Now.ID['line-separator'],
                            text: '',
                            isPlainText: true,
                            annotationType: AnnotationType.Line_Separator,
                        },
                        { field: 'state', type: 'table_field' },
                        {
                            type: 'annotation',
                            annotationId: Now.ID['section-details'],
                            text: 'Provide additional context about the task below.',
                            isPlainText: true,
                            annotationType: AnnotationType.Section_Details,
                        },
                        { field: 'notes', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})
```

Result: Demonstrates three different annotation styles in one form.

### M2M Embedded List

Many-to-Many relationship using a join table pattern with `listType: "M2M"` and `listRef: "join_table.parent_field"` format.

```
import { Form, default_view } from '@servicenow/sdk/core'

Form({
    table: 'sn_form_example_task',
    view: default_view,
    sections: [
        {
            caption: 'Details',
            content: [
                {
                    layout: 'one-column',
                    elements: [{ field: 'name', type: 'table_field' }],
                },
            ],
        },
        {
            caption: 'Tags',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'list',
                            listType: 'M2M',
                            listRef: 'sn_form_example_task_tag.task',
                        },
                    ],
                },
            ],
        },
    ],
})
```

How it works: The join table (`sn_form_example_task_tag`) has a reference field (`task`) pointing back to the parent. The `listRef` format is `join_table.parent_field`.

## Choosing Embedded List vs Related List

When showing related records on a form, choose between embedding lists within form sections (Form API) and end-of-form related lists (Record API).

Core principle: Embedded List = "Edit in context" | Related List = "Navigate & manage"

| Embedded List (Form API) | Related List (Record API) |
| User needs to edit/act immediately in context | User needs to view/manage/navigate data |
| Small dataset (< 20 records) | Large or unbounded dataset ("all", "history") |
| Core workflow action | Secondary/supporting data |

Keyword signals:

| Signals → Embedded List | Signals → Related List |
| "quickly", "inline", "while filling", "within section", "immediate", "direct edit" | "all", "history", "at the bottom", "end of form", "related to", "display on record" |
| Action verbs: "create", "edit", "modify", "select", "assign" | View verbs: "show", "display", "list", "view" |

Default: When ambiguous, use Related List (standard ServiceNow behavior). See the `relationship-guide` topic for end-of-form related list patterns.

## Avoidance

- Never put text areas in two-column blocks — text areas (`description`, `work_notes`) need full width. Always use `one-column`.

- Never mix embedded lists with regular fields — embedded lists must be in their own dedicated section with a descriptive caption.

- Never use empty captions — empty `caption` strings cause build errors. Always provide a meaningful section name.

- Never hardcode formatter or relationship GUIDs — use `Formatter.*` constants for Activity and Attached Knowledge. For relationships, use a `Record<'sys_relationship'>` reference or query the instance for the sys_id.

- Never use raw GUID strings for `annotationType` — use `AnnotationType.*` constants when a built-in type matches. For custom styles, create a `Record<'sys_ui_annotation_type'>`.

- Never import unused symbols — importing `Record`, `default_view`, `AnnotationType`, or `Formatter` when not used causes build issues.

- Never duplicate fields in the same section — each field should appear only once per section to avoid rendering issues.

- Never create `sys_ui_formatter` records for globally available formatters — Activity (`Formatter.Activities_Filtered`) and Attached Knowledge (`Formatter.Attached_Knowledge`) already exist on all instances.

- Never exceed 1000 characters in annotation text — keep annotations concise. For lengthy content, consider using a UI Page or knowledge article link instead.

- Never use JavaScript or complex HTML in annotations — use plain text (`isPlainText: true`) by default. Only use HTML for simple formatting (`<b>`, `<br>`) when strictly necessary.

## See Also

- `field-styles-guide` — Apply CSS styling (background colors, text alignment, column widths) to form and list fields based on field values

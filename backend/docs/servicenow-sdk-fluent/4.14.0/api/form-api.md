Version: 4.14.0

# Form

Creates a form definition (`sys_ui_form`) for a ServiceNow table with sections and layout blocks.

The Form API creates the following ServiceNow records:

- `sys_ui_form` — Main form record linking table and view

- `sys_ui_form_section` — Join table linking form to sections

- `sys_ui_section` — Section records with caption and layout

- `sys_ui_element` — Individual field elements within sections

- `sys_ui_annotation` — Annotation records (when `type: 'annotation'`)

## Signature

```
Form(config)
```

## Parameters

### config

`Form<T extends TableName = TableName>`

Form configuration object:

- table — The ServiceNow table this form is associated with.

- view — View name string or `Record<'sys_ui_view'>` reference. Use `default_view` for the default view.

- user — Optional. Personalize for a specific user (`string` or `Record<'sys_user'>`).

- roles — Optional. Array of role names or `Role` objects that have access to this form.

- sections — Array of form sections. Each section has:

- caption — Section header text (required, non-empty).

- header — Optional. Whether the section renders as a header.

- title — Optional. Whether the section renders as a title/header row.

- content — Array of layout blocks:

- `{ layout: 'one-column', elements: [...] }` — Single-column layout

- `{ layout: 'two-column', leftElements: [...], rightElements: [...] }` — Two-column layout

- $meta (optional): `object`

- installMethod: `'first install' | 'demo' | 'once'`
Map a record to an output folder that loads only in specific circumstances.
'first install' -> 'unload',
'demo' -> 'unload.demo',
'once' -> 'apply_once'

### Element Types

Each element in a layout block requires a `type` discriminator:

- 
table_field — A standard table column field.

- `field` (required): Column name from the table schema.

- `type`: `'table_field'`

- 
annotation — Informational text displayed on the form.

- `type`: `'annotation'`

- `annotationId` (required): `Now.ID['...']` reference for the `sys_ui_annotation` record.

- `text` (required): Display text (plain or HTML).

- `isPlainText` (optional): `true` for plain text (default), `false` for HTML.

- `annotationType` (optional): A predefined key  (e.g., `AnnotationType.Info_Box_Blue`), `Record<'sys_ui_annotation_type'>`, or GUID string. Defaults to `'AnnotationType.Info_Box_Blue'`.

- 
formatter — Special UI component (e.g., activity stream).

- `type`: `'formatter'`

- `formatterRef` (required): A predefined key (e.g., `'Activities_Filtered'`), `Record<'sys_ui_formatter'>`, or GUID string.

- `formatterName` (optional): Formatter file name. Auto-derived for predefined keys and Record references.

- 
list — Related list element. Discriminated by `listType`:

- `'12M'` / `'M2M'`: `listRef` is dot-notation `'<table>.<column>'`.

- `'custom'`: `listRef` is a `Record<'sys_relationship'>` or GUID string.

### Predefined Constants

AnnotationType constants: `AnnotationType.Info_Box_Blue`, `AnnotationType.Info_Box_Red`, `AnnotationType.Line_Separator`, `AnnotationType.Plain_Text`, `AnnotationType.Section_Details`, `AnnotationType.Section_Plain_Text`, `AnnotationType.Section_Separator`, `AnnotationType.Text`.

Formatter keys: `'Activities_Filtered'` (activity.xml), `'Attached_Knowledge'` (attached_knowledge).

### Coalesce Keys

| Table | Coalesce Keys |
| `sys_ui_form` | `name` , `view` , `sys_domain` |
| `sys_ui_section` | `name` , `caption` , `view` , `sys_domain` |
| `sys_ui_form_section` | `sys_ui_form` , `sys_ui_section` |
| `sys_ui_element` | `sys_ui_section` , `element` , `position` |

### Field Mapping (Fluent → ServiceNow)

sys_ui_form:

| Fluent Property | ServiceNow Field | Notes |
| `table` | `name` | Table name the form belongs to |
| `view` | `view` | Resolved to `sys_ui_view` sys_id |
| `user` | `sys_user` | Username or record reference |
| `roles` | `roles` | Array → comma-separated string |

sys_ui_section:

| Fluent Property | ServiceNow Field | Notes |
| `table` (inherited) | `name` | Inherited from parent form |
| `caption` | `caption` | Section header text |
| `title` | `title` | Whether section renders as title row |
| `header` | `header` | Whether section renders as header |
| `view` (inherited) | `view` | Inherited from parent form's view |

sys_ui_element:

| Fluent Property | ServiceNow Field | Notes |
| `field` | `element` | For `table_field` |
| `formatterName` | `element` | For `formatter` |
| `annotationId` | `element` | For `annotation` (stores annotation sys_id) |
| `listRef` | `element` | For embedded lists (encoded format) |
| `formatterRef` | `sys_ui_formatter` | GUID for formatter elements |
| `type` | `type` | Set from element discriminant ( `'annotation'` , `'formatter'` , or empty) |
| (auto) | `position` | Sequential, 0-indexed |

sys_ui_annotation:

| Fluent Property | ServiceNow Field | Notes |
| `annotationId` | `sys_id` | Annotation record ID |
| `text` | `text` | Content string |
| `isPlainText` | `is_plain_text` | Direct mapping (default `true` ) |
| `annotationType` | `type` | Reference to `sys_ui_annotation_type` |

### Default Values

| Property | Default | Notes |
| `view` | (required) | Use `default_view` for the default ServiceNow view |
| `user` | `''` | Omitted from generated Fluent code when empty |
| `roles` | `[]` | Omitted from generated Fluent code when empty |
| `sections[].header` | `false` | Omitted when `false` |
| `sections[].title` | `false` | Omitted when `false` |
| `isPlainText` | `true` | Defaults to plain text for annotations |
| `annotationType` | `'AnnotationType.Info_Box_Blue'` | Default annotation styling |

## See

- https://docs.servicenow.com/csh?topicname=form-administration.html&version=latest

## Examples

### Basic Form with Default View

Create a simple form with two sections on the default view using one-column layout.

```
/**
 * @title Basic Form with Default View
 * @description Create a simple form with two sections on the default view using one-column layout.
 */

import { Form, default_view } from '@servicenow/sdk/core'

export const basicForm = Form({
    table: 'sn_my_app_task',
    view: default_view,
    sections: [
        {
            caption: 'Details',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { field: 'name', type: 'table_field' },
                        { field: 'description', type: 'table_field' },
                    ],
                },
            ],
        },
        {
            caption: 'Assignment',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { field: 'assigned_to', type: 'table_field' },
                        { field: 'state', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})
```

### Comprehensive Form — All Element Types

Create a form with two-column layout, annotation, formatter, related list, custom view, and role-based access.

```
/**
 * @title Comprehensive Form — All Element Types
 * @description Create a form with two-column layout, annotation, formatter, related list, custom view, and role-based access.
 */

import { AnnotationType, Form, Record } from '@servicenow/sdk/core'

export const opsView = Record({
    $id: Now.ID['ops_view'],
    table: 'sys_ui_view',
    data: { name: 'operations', title: 'Operations' },
})

export const comprehensiveForm = Form({
    table: 'sn_my_app_task',
    view: opsView,
    roles: ['admin', 'itil'],
    sections: [
        {
            caption: 'Overview',
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
                    elements: [
                        {
                            type: 'annotation',
                            annotationId: Now.ID['task_notice'],
                            text: 'Review all fields before saving.',
                            isPlainText: true,
                            annotationType: AnnotationType.Info_Box_Blue,
                        },
                        { field: 'description', type: 'table_field' },
                    ],
                },
            ],
        },
        {
            caption: 'Activity',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'formatter',
                            formatterRef: 'Activities_Filtered',
                        },
                    ],
                },
            ],
        },
        {
            caption: 'Related Tasks',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'list',
                            listType: '12M',
                            listRef: 'task_sla.task',
                        },
                    ],
                },
            ],
        },
    ],
})
```

### Custom Formatter and Annotation Type via Record API

Create a form that references custom formatter and annotation type records instead of built-in constants.

```
/**
 * @title Custom Formatter and Annotation Type via Record API
 * @description Create a form that references custom formatter and annotation type records instead of built-in constants.
 */

import { Form, Record } from '@servicenow/sdk/core'

// Custom formatter — `formatterName` is derived from the record's `formatter` field
export const myFormatter = Record({
    $id: Now.ID['parent_breadcrumb_formatter'],
    table: 'sys_ui_formatter',
    data: {
        name: 'parent_breadcrumb',
        type: 'formatter',
        formatter: 'parent_crumbs.xml',
        table: 'sn_my_app_task',
        active: true,
    },
})

export const myAnnotationType = Record({
    $id: Now.ID['custom_warning_banner'],
    table: 'sys_ui_annotation_type',
    data: {
        name: 'Custom Warning Banner',
        active: true,
        style: 'background-color: #fff3cd; border: 1px solid #ffc107; padding: 12px; border-radius: 4px; color: #856404;',
    },
})

export const customRecordsForm = Form({
    table: 'sn_my_app_task',
    view: 'custom_refs_view',
    sections: [
        {
            caption: 'Custom Elements',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'annotation',
                            annotationId: Now.ID['custom_notice'],
                            text: '<b>Warning:</b> Custom styled annotation.',
                            isPlainText: false,
                            annotationType: myAnnotationType,
                        },
                        {
                            type: 'formatter',
                            formatterRef: myFormatter,
                        },
                    ],
                },
            ],
        },
    ],
})
```

### Formatter Variants

Shows all formatterName resolution paths: predefined key, custom Record, and raw GUID.

```
/**
 * @title Formatter Variants
 * @description Shows all formatterName resolution paths: predefined key, custom Record, and raw GUID.
 */

import { Form, Record } from '@servicenow/sdk/core'

// Custom formatter record — formatterName derived from the `formatter` field
export const appFormatter = Record({
    $id: Now.ID['parent_breadcrumb_formatter_1'],
    table: 'sys_ui_formatter',
    data: {
        name: 'parent_breadcrumb',
        type: 'formatter',
        formatter: 'parent_crumbs.xml',
        table: 'sn_my_app_task',
        active: true,
    },
})

export const formatterVariantsForm = Form({
    table: 'sn_my_app_task',
    view: 'formatter_demo',
    sections: [
        {
            caption: 'Formatter Variants',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        // 1. Predefined key — formatterName auto-derived (activity.xml)
                        {
                            type: 'formatter',
                            formatterRef: 'Activities_Filtered',
                        },
                        // 2. Custom Record — formatterName derived from record's `formatter` field
                        {
                            type: 'formatter',
                            formatterRef: appFormatter,
                        },
                        // 3. Raw GUID — formatterName must be provided (not derivable)
                        {
                            type: 'formatter',
                            formatterName: 'custom_formatter.xml',
                            formatterRef: 'aabbccdd11223344aabbccdd11223344',
                        },
                    ],
                },
            ],
        },
    ],
})
```

### M2M Related List and Custom Relationship

Create a form with many-to-many and custom relationship related lists.

```
/**
 * @title M2M Related List and Custom Relationship
 * @description Create a form with many-to-many and custom relationship related lists.
 */

import { Form, Record } from '@servicenow/sdk/core'

export const incidentToProblem = Record({
    $id: Now.ID['inc_to_problem'],
    table: 'sys_relationship',
    data: {
        name: 'Incident to Problem',
        basic_apply_to: 'sn_my_app_task',
        basic_query_from: 'problem',
        reference_field: 'problem_id',
    },
})

export const relatedListsForm = Form({
    table: 'sn_my_app_task',
    view: 'relationships_view',
    sections: [
        {
            caption: 'Many-to-Many',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'list',
                            listType: 'M2M',
                            listRef: 'm2m_task_project.task_ref',
                        },
                    ],
                },
            ],
        },
        {
            caption: 'Custom Relationship',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'list',
                            listType: 'custom',
                            listRef: incidentToProblem,
                        },
                    ],
                },
            ],
        },
    ],
})
```

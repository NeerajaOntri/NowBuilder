Version: 4.14.0

# Form Formatters

Guide for adding formatters to ServiceNow forms using the Form API. Formatters display special UI components (activity streams, process flows, knowledge panels, checklist, parent breadcrumb, custom macro renderers) that are not regular table fields.

## When to Use

Use formatters to enhance existing forms with these capabilities:

- Adding an activity stream (comments, work notes, journal) to an existing form

- Displaying attached knowledge articles on existing task records

- Showing a process flow (lifecycle stages) at the top of an existing form

- Adding a checklist for tracking sub-tasks on an existing form

- Displaying CI relationship maps on existing CMDB record forms

- Showing parent breadcrumb navigation on existing hierarchical task records

- Surfacing contextual search results (knowledge articles, catalog items) on an existing form based on field values

- Displaying variable/question values from record producers on existing service catalog forms

- Rendering a custom macro-backed component when no built-in formatter fits the use case

## Critical Instructions

When adding formatter elements to forms, follow these guidelines to ensure proper functionality. Failure to follow these requirements may result in build or runtime errors.

- Always set `type: 'formatter'` — this is required for the element to be treated as a formatter

- `formatterRef` is required — use a predefined key string (e.g., `'Activities_Filtered'`), a `Formatter.*` constant, or a `Record<'sys_ui_formatter'>` reference

- Set the formatter Record's `formatter` field to the exact filename the platform will resolve; `formatterName` is optional — when omitted it is derived from the `Formatter.*` constant or the project `Record<'sys_ui_formatter'>`'s `formatter` field, and if you set it, it must be that same filename. Neither value is ever scope-adjusted. See "Macro Formatter Filenames" below for which value to use.

- Import `Formatter` from `@servicenow/sdk/core` when using formatter constants

- Prefer built-in formatters for standard needs (activity stream, attached knowledge, process flow, checklist, etc.)

- Custom formatter macros are supported through the `UiMacro` API and the `sys_ui_formatter` table — see the `ui-macro-guide` topic for how to create a macro and wire it to a formatter

- Never create new `sys_ui_formatter` records for globally available formatters (Activity, Attached Knowledge) — they already exist

- Formatter properties are formatter-only — never use `formatterRef` or `formatterName` on other element types

- Always include `angular_module` when required — Checklist and CI Relations formatters require this property

## Instructions

- Identify the formatter: Determine whether a built-in formatter matches your use case from the Built-in Formatters table below, or whether you need a custom macro-backed formatter.

- Check availability: Activity and Attached Knowledge exist globally — skip to step 4. For all others, query `sys_ui_formatter` using the 3-level cascade (target table → global → parent table).

- Create if missing: If the `sys_ui_formatter` record does not exist, create one using `Record()` before the `Form()` call. For custom macros, create the `UiMacro` first, then create the `sys_ui_formatter` record with its `formatter` field set to the macro's effective invocation key (see "Macro Formatter Filenames" below).

- Add the element: Add `{ type: 'formatter', formatterRef: ... }` to the appropriate section in your `Form()` call.

- Position correctly: Follow the placement rules — visual formatters go at the top, historical formatters go in dedicated sections at the bottom.

- Handle prerequisites: Some formatters require additional setup (stage records, CXS config, `parent` field). See per-formatter details below.

## API Reference

See the `form-api` topic for the full `FormElement` type reference, including `formatterRef` and `formatterName` properties.

### Table Schema

The `sys_ui_formatter` table schema for creating formatter records using `Record()`:

| Field | Type | Required | Description |
| `name` | `String` | Yes | Display name of the formatter (shown in form designer and admin lists). |
| `type` | `String` | Yes | Must be `'formatter'` — identifies this as a formatter record. |
| `formatter` | `String` | Yes | Macro filename. FormPlugin writes this value straight to `sys_ui_element.element` with no scope-prefixing of its own — see "Macro Formatter Filenames" below for which value to use. |
| `table` | `String` | Yes | Target table name. Use `'global'` for all tables, specific table name (e.g., `'incident'` ), or parent table (e.g., `'task'` , `'cmdb_ci'` ) for inheritance. |
| `active` | `Boolean` | Yes | Whether the formatter is active and available for use. Set to `true` to enable. |
| `angular_module` | `String` | Conditional | AngularJS module name. Required for Checklist ( `'inlineChecklist'` ) and CI Relations ( `'sn.ciRelationFormatter'` ). Optional for Contextual Search ( `'sn.cxs.table_search'` ). Omit for all other formatters. |

## Key Concepts

### Form API Structure

Understanding the Form API hierarchy is essential for correct formatter placement:

Form Structure:

- A form has multiple sections (array of section objects)

- Each section has a content array containing layout blocks

- Layout blocks can be `one-column` (with `elements` array) or `two-column` (with `leftElements` and `rightElements` arrays)

- Element position is determined by array order within the layout block

Example structure:

```
Form({
    table: 'x_myapp_task',
    view: default_view,
    sections: [                    // Array of sections
        {
            caption: 'Overview',
            content: [             // Array of layout blocks
                {
                    layout: 'one-column',
                    elements: [    // Array of elements - order matters!
                        // First element (index 0)
                        { type: 'formatter', formatterRef: processFlowFormatter },
                        // Second element (index 1)
                        { field: 'name', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})
```

When we say "first element in section", this means index 0 in the elements array of the first layout block.

### Formatter Properties

| Property | Required | Type | Description |
| `type` | Yes | `'formatter'` | Must be `'formatter'` |
| `formatterRef` | Yes | `Formatter.*` constant, `Record<'sys_ui_formatter'>` , or key string | Identifies which formatter to display |
| `formatterName` | Conditional | `string` | Macro filename (e.g., `'activity.xml'` ). Optional for `Formatter.*` constants and project `Record<'sys_ui_formatter'>` references — derived from the constant or the Record's `formatter` field, never scope-adjusted. Required only when `formatterRef` is the sys_id of a formatter not predefined in `Formatter.*` . See "Macro Formatter Filenames" below for which value to use. |

### Macro Formatter Filenames

The platform resolves a formatter macro by an exact match on the macro's effective invocation key — its `scoped_name`, or its unprefixed `name` when `scoped_name` is empty. Get this value wrong and the formatter silently fails to render, with no build error.

Global-scope macros (all OOB macros such as `process_flow` and `activity`) have an empty `scoped_name`, so use the unprefixed `name` in every scope. A `UiMacro()` created in an app scope gets `scoped_name` = `<scope>_<name>` (e.g. `x_myapp_status_badge`); that scoped value, not the local `name`, is the key.

FormPlugin does not compute this value for you — there is no scope-prefixing step. Set the formatter Record's `formatter` field to the macro's effective invocation key exactly. `formatterName` is optional — when omitted it is derived from that field; if you set it, it overrides the field (no diagnostic is reported if they differ), so keep them identical. FormPlugin copies the value to `sys_ui_element.element` exactly as given, with no prefixing.

```
import { Form, Record, default_view } from '@servicenow/sdk/core'

const statusBadgeFormatter = Record({
    $id: Now.ID['status-badge-formatter-example'],
    table: 'sys_ui_formatter',
    data: { name: 'Status Badge', type: 'formatter', formatter: 'x_myapp_status_badge.xml', table: 'incident', active: true },
})

Form({
    table: 'incident',
    view: default_view,
    sections: [
        {
            caption: 'Status',
            content: [{ layout: 'one-column', elements: [
                // CORRECT — custom macro in a scoped app: the macro's real scoped filename
                { type: 'formatter', formatterRef: statusBadgeFormatter, formatterName: 'x_myapp_status_badge.xml' },
                // WRONG — unprefixed local name: builds fine, but no 'status_badge.xml' macro exists, so it silently fails to render
                // { type: 'formatter', formatterRef: statusBadgeFormatter, formatterName: 'status_badge.xml' },
            ] }],
        },
    ],
})
```

### Formatter Constants

Only two formatters have predefined constants (import from `@servicenow/sdk/core`):

```
import { Formatter } from '@servicenow/sdk/core'
```

| Constant | Macro | Description |
| `Formatter.Activities_Filtered` | `activity.xml` | Activity stream with filtering (comments, work notes, journal) |
| `Formatter.Attached_Knowledge` | `attached_knowledge` | Related knowledge articles panel |

All other formatters require a `Record<'sys_ui_formatter'>` reference as `formatterRef`.

### Built-in Formatters

| Formatter | Macro | Angular Module | Position | Prerequisites |
| Activity | `activity.xml` | N/A | Dedicated section at bottom | None — globally available |
| Attached Knowledge | `attached_knowledge` | N/A | Dedicated section at bottom | Knowledge Management plugin; table extends `task` |
| Process Flow | `process_flow.xml` | N/A | First element in first section | `sys_process_flow` stage records for the table |
| Checklist | `inline_checklist_macro.xml` | `inlineChecklist` | Dedicated section near bottom | Checklist plugin; task-derived table |
| CI Relations | `ui_ng_relation_formatter.xml` | `sn.ciRelationFormatter` | First element in section | CMDB plugin; table extends `cmdb_ci` ; relationship records in `cmdb_rel_ci` |
| Parent Breadcrumb | `parent_crumbs.xml` | N/A | First element in section | Table must have a field named exactly `parent` (reference type) |
| Contextual Search | `cxs_table_search.xml` | `sn.cxs.table_search` | After the search context field | CXS enabled; `cxs_table_config` and `cxs_table_field_config` records |
| Variables Editor | `com_glideapp_questionset_default_question_editor` | N/A | No fixed position | Table extends task; record created from record producer. Note: this OOB macro name has no `.xml` suffix, unlike the others — use the name exactly as shown. |

Angular Module Requirement:

- Checklist: MUST include `angular_module: 'inlineChecklist'` in the `sys_ui_formatter` Record() data

- CI Relations: MUST include `angular_module: 'sn.ciRelationFormatter'` in the `sys_ui_formatter` Record() data

- Contextual Search: The table lists `sn.cxs.table_search` but this may be optional — verify on your instance

- All others: No angular_module required

### Placement Rules

| Category | Formatters | Where to Place | Additional Guidance |
| Visual/Overview | Process Flow, Parent Breadcrumb, CI Relations | First element in the main section | These are visual headers that belong with record details — place in a section that also contains fields |
| Contextual | Contextual Search, Variables Editor | Same section as related fields, after them | Place immediately after the field they relate to (e.g., CXS after `short_description` ) |
| Historical/Reference | Activity, Checklist, Attached Knowledge | Dedicated section at bottom of form | Formatter-only sections (no other fields) — these become separate tabs in the UI |

General rules:

- Use one-column layout for formatters — formatters typically span the full width; avoid placing them in `leftElements` or `rightElements` of two-column layouts

- One formatter per dedicated section — Activity, Attached Knowledge, and Checklist each get their own section

- Visual formatters can share sections — Process Flow, Parent Breadcrumb can be in the same section as form fields (as the first element)

### sys_ui_formatter Records

Before adding any formatter (except Activity and Attached Knowledge), verify the `sys_ui_formatter` record exists using a 3-level cascade query:

- Target table: `table=<table_name>^formatter=<macro_filename>`

- Global scope: `table=global^formatter=<macro_filename>`

- Parent table: `table=<parent_table>^formatter=<macro_filename>` (if table extends another)

If found, use the existing record. If not found, create one. For a custom macro in a scoped app, the `formatter` field must be the macro's scoped filename:

```
import { Record } from '@servicenow/sdk/core'

const myFormatter = Record({
    $id: Now.ID['my-formatter'],
    table: 'sys_ui_formatter',
    data: {
        name: 'Formatter Display Name',
        type: 'formatter',
        formatter: '<scope>_<macro_name>.xml', // scoped filename for custom macros; unprefixed for OOB macros
        table: '<target_table>',
        active: true,
        // Include angular_module if required (Checklist, CI Relations)
        // angular_module: 'module.name',
    },
})
```

## Examples

### Activity Stream (Global Formatter)

No `sys_ui_formatter` record needed — use the `Formatter` constant directly.

```
import { Form, Formatter, default_view } from '@servicenow/sdk/core'

Form({
    table: 'x_myapp_task',
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

Prerequisites: Available by default for every table. No additional setup required.

### Custom Macro Formatter

When no built-in formatter fits, create a `UiMacro` and wire it to a form as a formatter. See the `ui-macro-guide` topic's "Form Formatter Using a Macro" example for the full walkthrough (macro definition, `sys_ui_formatter` record, and `Form()` wiring) and "Using a Macro as a Form Formatter" for the scoped-filename rule, and its "Client-Rendered Formatter Values" section for client-rendered patterns. For writing the macro's Jelly itself (phases and caching, XML-safe JavaScript), see the `jelly-guide` topic.

### Process Flow with Stage Records

Requires a `sys_ui_formatter` record and `sys_process_flow` stage records as prerequisites. Process Flow is an OOB macro — the project does NOT define a `UiMacro` for it. Set the Record's `formatter` field to `'process_flow.xml'` (`formatterName` is optional; if set, it overrides that field, so keep them identical) — FormPlugin writes it through as-is; the unprefixed filename is correct precisely because this macro has no scope (see "Macro Formatter Filenames" above).

```
import { Form, Record, default_view } from '@servicenow/sdk/core'

const processFlowFormatter = Record({
    $id: Now.ID['process-flow-formatter'],
    table: 'sys_ui_formatter',
    data: {
        name: 'Process Flow',
        type: 'formatter',
        formatter: 'process_flow.xml',
        table: 'x_myapp_task',
        active: true,
    },
})

Record({
    $id: Now.ID['stage-new'],
    table: 'sys_process_flow',
    data: {
        active: true,
        condition: 'state=new^EQ',
        label: 'New',
        name: 'Task Flow - New',
        order: '100',
        table: 'x_myapp_task',
    },
})

Record({
    $id: Now.ID['stage-active'],
    table: 'sys_process_flow',
    data: {
        active: true,
        condition: 'state=active^EQ',
        label: 'Active',
        name: 'Task Flow - Active',
        order: '200',
        table: 'x_myapp_task',
    },
})

Record({
    $id: Now.ID['stage-closed'],
    table: 'sys_process_flow',
    data: {
        active: true,
        condition: 'state=closed^EQ',
        label: 'Closed',
        name: 'Task Flow - Closed',
        order: '300',
        table: 'x_myapp_task',
    },
})

Form({
    table: 'x_myapp_task',
    view: default_view,
    sections: [
        {
            caption: 'Overview',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        // formatterName is explicit for clarity — FormPlugin would derive the same unprefixed value from the Record's formatter field if omitted
                        { type: 'formatter', formatterRef: processFlowFormatter, formatterName: 'process_flow.xml' },
                    ],
                },
                {
                    layout: 'two-column',
                    leftElements: [
                        { field: 'name', type: 'table_field' },
                        { field: 'state', type: 'table_field' },
                    ],
                    rightElements: [
                        { field: 'priority', type: 'table_field' },
                        { field: 'assigned_to', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})
```

Prerequisites: Stage Model must be configured in `sys_process_flow` for the target table.

### Checklist Formatter

Requires the Checklist plugin and a task-derived table. Checklist is an OOB macro — set the Record's `formatter` field to its unprefixed filename; `formatterName` is optional.

```
import { Form, Record, default_view } from '@servicenow/sdk/core'

const checklistFormatter = Record({
    $id: Now.ID['checklist-formatter'],
    table: 'sys_ui_formatter',
    data: {
        name: 'Checklist Formatter',
        type: 'formatter',
        formatter: 'inline_checklist_macro.xml',
        angular_module: 'inlineChecklist', // REQUIRED for Checklist
        table: 'x_myapp_task',
        active: true,
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
                        { field: 'name', type: 'table_field' },
                        { field: 'state', type: 'table_field' },
                    ],
                },
            ],
        },
        {
            caption: 'Checklist',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { type: 'formatter', formatterRef: checklistFormatter, formatterName: 'inline_checklist_macro.xml' },
                    ],
                },
            ],
        },
    ],
})
```

Prerequisites:

- Checklist plugin enabled

- Target table supports checklists (typically task-derived)

- Checklist definitions/items exist or can be added

- User has rights to view/edit checklist items

### Attached Knowledge Formatter

Display knowledge articles linked to a task record. Uses the global `Formatter.Attached_Knowledge` constant — no `sys_ui_formatter` record needed.

```
import { Form, Formatter, default_view } from '@servicenow/sdk/core'

Form({
    table: 'incident',
    view: default_view,
    sections: [
        {
            caption: 'Incident Details',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { field: 'short_description', type: 'table_field' },
                        { field: 'description', type: 'table_field' },
                    ],
                },
            ],
        },
        {
            caption: 'Knowledge',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'formatter',
                            formatterRef: Formatter.Attached_Knowledge,
                        },
                    ],
                },
            ],
        },
    ],
})
```

Prerequisites:

- Knowledge Management plugin installed

- At least one knowledge article is attached to the record

- Target table is `task` or extends from `task`

### CI Relations Formatter

Display CI relationship maps on CMDB records. Requires creating a `sys_ui_formatter` record first. CI Relations is an OOB macro — set the Record's `formatter` field to its unprefixed filename; `formatterName` is optional.

```
import { Record, Form, default_view } from '@servicenow/sdk/core'

const ciRelationsFormatter = Record({
    $id: Now.ID['ci-relations-formatter'],
    table: 'sys_ui_formatter',
    data: {
        formatter: 'ui_ng_relation_formatter.xml',
        angular_module: 'sn.ciRelationFormatter', // REQUIRED for CI Relations
        name: 'CI Relations',
        table: 'cmdb_ci',
        type: 'formatter',
        active: true,
    },
})

Form({
    table: 'cmdb_ci_server',
    view: default_view,
    sections: [
        {
            caption: 'Server Details',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'formatter',
                            formatterRef: ciRelationsFormatter,
                            formatterName: 'ui_ng_relation_formatter.xml',
                        },
                        { field: 'name', type: 'table_field' },
                        { field: 'ip_address', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})
```

Prerequisites:

- CMDB plugin installed

- Target table extends `cmdb_ci`

- Relationship records exist in `cmdb_rel_ci` with appropriate relationship types

### Contextual Search Formatter

Adds a search results panel to an EXISTING form that displays contextual knowledge articles or catalog items based on field values as the user types. This formatter enhances platform forms (incident, task, custom tables) — it does NOT create a new search page or interface. Requires CXS configuration records.

#### How CXS Works (Architecture)

```
Form record (e.g. incident)
  └─ field value (e.g. short_description = "VPN not connecting")
        └─ used as search term
              └─ searches Knowledge Base (kb_knowledge), Catalog, or Communities
                    └─ matching articles displayed in the formatter panel on the form
```

Key architectural concepts:

- `cxs_table_config.table` — the form table (e.g., `incident`). This is the table whose field values drive the search.

- `cxs_table_field_config.field` — the field on the form table whose value is sent as the search term.

- `cxs_context_config` — defines the search sources (KB, Catalog, Communities). These are platform system records — never create them. Query to find available ones.

- CXS searches `kb_knowledge` (Knowledge Base), catalog items, and communities. It does NOT search custom tables.

#### Critical CXS Limitations

- CXS cannot search custom tables — it only searches Knowledge Base (`kb_knowledge`), Catalog items, and Communities. Never create a custom knowledge table and attempt to wire it to CXS.

- Knowledge articles must exist as `kb_knowledge` records inside an active Knowledge Base. If the user asks for a "contextual panel showing knowledge articles", those articles must be in the platform KB, not a custom table.

- Query existing search contexts first — `cxs_context_config` records are platform system records. Query the instance for active records in table `cxs_context_config` with fields `sys_id`, `name` before configuring (see `query` topic).

#### CXS Setup Process

Step 1: Get available search contexts

Query the instance for table `cxs_context_config` for all records with fields `sys_id`, `name`, `description` (see `query` topic for how to perform queries in your environment).

Common context: Knowledge Base Search. Ask the user to select a search context if multiple are available.

Step 2: Create `cxs_table_config` record

The `table` field here is the form table (e.g., `incident`, `sn_si_incident`) — not the KB table. The `match_condition` is an encoded query on this same form table to control when the formatter is active.

CRITICAL: `match_condition` field validation

The `match_condition` field must only use fields that exist on the form table. Before using a field in `match_condition`:

- Query the instance for table `sys_dictionary` where `name=<form_table>` and `element=<field_name>`, retrieving field `element` to verify the field exists (see `query` topic)

- Use `sys_created_on!=NULL^EQ` as a safe fallback if unsure (always true for saved records)

Step 3: Verify string fields on form table

For `cxs_table_field_config`, you need to identify string fields available on the form table.

First, query the instance for table `sys_glide_object` where `name=string` to get the String type `sys_id` (see `query` topic).

Then query the instance table `sys_dictionary` where `name=<form_table>` and `internal_type=<string_type_id>`, retrieving field `element` to find available string fields (see `query` topic).

Prefer `short_description` or `description`. If neither exists, ask the user to select an appropriate string field.

#### Full Example

```
import { Record, Form, default_view } from '@servicenow/sdk/core'

// Create CXS table config
const cxsTableConfig = Record({
    $id: Now.ID['incident-cxs-config'],
    table: 'cxs_table_config',
    data: {
        table: 'incident', // The form table - drives the search
        name: 'Incident[incident]', // Format: "Label[table_name]"
        active: true,
        cxs_context_config: '<sys_id_from_query>', // From step 1
        ui_type: 'platform',
        results_header_text: 'Related Search Results',
        limit: 10,
        results_per_page: 10,
        match_condition: 'short_descriptionISNOTEMPTY^category=software', // Encoded query on form table
        related_search_active: true,
        enable_source_selector: true,
    },
})

// Create CXS field config
const cxsFieldConfig = Record({
    $id: Now.ID['incident-cxs-field-config'],
    table: 'cxs_table_field_config',
    data: {
        active: true,
        cxs_table_config: cxsTableConfig,
        field: 'short_description', // Field on form table used as search term
        name: 'Short Description[short_description]', // Format: "Field Label[field_name]"
        sys_name: 'Short Description[short_description]',
        default_config: true,
        weight: 100,
    },
})

// Create formatter
const cxsFormatter = Record({
    $id: Now.ID['incident-cxs-formatter'],
    table: 'sys_ui_formatter',
    data: {
        formatter: 'cxs_table_search.xml',
        name: 'Contextual Search',
        table: 'incident',
        type: 'formatter',
        active: true,
        // angular_module: 'sn.cxs.table_search', // May be optional - verify on your instance
    },
})

Form({
    table: 'incident',
    view: default_view,
    sections: [
        {
            caption: 'Details',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { field: 'short_description', type: 'table_field' },
                        {
                            type: 'formatter',
                            formatterRef: cxsFormatter,
                            formatterName: 'cxs_table_search.xml',
                        },
                        { field: 'category', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})
```

Prerequisites:

- Contextual Search enabled and configured on the instance

- Knowledge articles exist as `kb_knowledge` records in an active Knowledge Base

- `cxs_table_config` must be configured for the form table

- `match_condition` uses fields that exist on the table

### Parent Breadcrumb Formatter

Show parent breadcrumb navigation on hierarchical task records. Requires a field named exactly `parent`.

#### Critical Field Requirement

The table MUST have a reference field named exactly `parent`.

| Field Name | Acceptable |
| `parent` | ✅ Yes |
| `parent_task` | ❌ No |
| `parent_ticket` | ❌ No |
| `parent_record` | ❌ No |

The field must:

- Be named exactly `parent` (case-sensitive)

- Be a reference field type

- Reference the same table the record is on, or a table it extends from (e.g., the base `task` table)

If this field does not exist, create it before adding the formatter.

```
import { Record, Form, default_view } from '@servicenow/sdk/core'

const parentBreadcrumbFormatter = Record({
    $id: Now.ID['parent-breadcrumb-formatter'],
    table: 'sys_ui_formatter',
    data: {
        formatter: 'parent_crumbs.xml',
        name: 'Parent Breadcrumb',
        table: 'incident',
        type: 'formatter',
        active: true,
    },
})

Form({
    table: 'incident',
    view: default_view,
    sections: [
        {
            caption: 'Incident',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'formatter',
                            formatterRef: parentBreadcrumbFormatter,
                            formatterName: 'parent_crumbs.xml',
                        },
                        { field: 'number', type: 'table_field' },
                        { field: 'parent', type: 'table_field' },
                    ],
                },
            ],
        },
    ],
})
```

Prerequisites: Table must have a field named exactly `parent` (reference type, not `parent_task` or `parent_record`).

### Variables Editor Formatter

Display variable/question values from record producers on task-derived tables.

```
import { Record, Form, default_view } from '@servicenow/sdk/core'

const variablesFormatter = Record({
    $id: Now.ID['variables-formatter'],
    table: 'sys_ui_formatter',
    data: {
        formatter: 'com_glideapp_questionset_default_question_editor',
        name: 'Variables',
        table: 'sc_req_item',
        type: 'formatter',
        active: true,
    },
})

Form({
    table: 'sc_req_item',
    view: default_view,
    sections: [
        {
            caption: 'Request Details',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { field: 'number', type: 'table_field' },
                        { field: 'short_description', type: 'table_field' },
                    ],
                },
            ],
        },
        {
            caption: 'Variables',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        {
                            type: 'formatter',
                            formatterRef: variablesFormatter,
                            formatterName: 'com_glideapp_questionset_default_question_editor',
                        },
                    ],
                },
            ],
        },
    ],
})
```

Prerequisites:

- Target table extends `task`

- Record created from a record producer

- Questions/variables are defined for the table

Position: No fixed position requirement — place where variable questions logically fit in the form flow.

## Best Practices

- Use `Formatter` constants: Always prefer `Formatter.Activities_Filtered` over raw GUID strings for readability and maintainability

- Place activity streams in dedicated sections: Activity formatters are best at the bottom of the form in their own section — this matches ServiceNow's standard layout convention and creates a separate tab in the UI

- Don't duplicate formatters: Each formatter should appear only once per form — adding the same formatter twice causes rendering issues

- Check formatter availability: Before using a formatter, verify the `sys_ui_formatter` record exists on the target instance using the 3-level cascade query (target table → global → parent table)

- Use one-column layouts: Formatters span the full width — always use `layout: 'one-column'` for formatter elements

- Validate prerequisites before adding: Process Flow needs stage records, CXS needs config records, Parent Breadcrumb needs a `parent` field — verify these exist before adding the formatter element

## Avoidance

- Never write a custom macro's unprefixed local name into `formatter`/`formatterName` in a scoped app — the formatter silently fails to render with no build error. See "Macro Formatter Filenames" above for the exact filename to use.

- Never create `sys_ui_formatter` records for Activity or Attached Knowledge — they exist globally on all instances.

- Never place formatters in two-column layout blocks — formatters need full width. Always use `one-column`.

- Never duplicate formatters on the same form — adding the same formatter twice causes rendering issues.

- Never use the Parent Breadcrumb formatter without a field named exactly `parent` — must be a reference type (not `parent_task`, `parent_record`).

- Never create `cxs_table_config` without verifying the `match_condition` uses fields that exist on the form table — query the instance for table `sys_dictionary` where `name=<form_table>` and `element=<field_name>`, retrieving field `element` to verify the field exists (see `query` topic).

- Never hardcode formatter GUIDs — use `Formatter.*` constants for Activity and Attached Knowledge, or a `Record<'sys_ui_formatter'>` reference for all others.

- Never skip the sys_ui_formatter query — always check if the record exists before creating a new one using the 3-level cascade (target table → global → parent table). This applies to formatters that may already exist on the instance; a formatter you define in the same project has no existing record to find.

- Never create a custom knowledge table for CXS — CXS only searches `kb_knowledge`, catalog items, and communities. Custom tables are not supported as search sources.

- Never omit `angular_module` for Checklist or CI Relations — these formatters require the angular_module property in the sys_ui_formatter record or they will fail at runtime.

## Related Topics

- `ui-macro-guide` — creating custom UI Macros to back form formatters

- `jelly-guide` — writing the Jelly content of a custom formatter macro

- `form-api` — full `FormElement` type reference

- table-guide.md — table creation and field management

- service-catalog-guide.md — service catalog and record producer configuration

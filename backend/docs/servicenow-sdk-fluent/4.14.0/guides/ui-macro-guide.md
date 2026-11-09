Version: 4.14.0

# UI Macros

Guide for creating ServiceNow UI Macros (`sys_ui_macro`) with the Fluent `UiMacro` API. UI Macros are reusable Jelly components that render HTML and can run server-side script; in Fluent they are used to back custom form formatters (via a `sys_ui_formatter` `Record()` and a `Form()` formatter element referencing it) and to power custom Service Catalog variable types via `CustomVariable` and `CustomWithLabelVariable`.

## When to Use

- Supplying the display logic behind a custom form formatter

- Rendering a custom control that no standard field type provides (pickers, formatted displays, status cards) inside a formatter area

- Embedding a custom UI component in a Service Catalog form via `CustomVariable` or `CustomWithLabelVariable` (the `macro` property references a `sys_ui_macro`)

- Providing a custom cart checkout experience on a catalog item (the `customCart` property on `CatalogItem` references a `sys_ui_macro`)

- Building a reusable Jelly fragment that appears on more than one form

- Wrapping a repeated Jelly pattern behind a single callable tag

## Instructions

- Set `$id`: Every `UiMacro` needs a unique `$id` using `Now.ID` notation.

- Use the unprefixed `name`: The build derives `scoped_name` by adding the application scope prefix. Write the local name only, e.g. `name: 'alert_banner'` in the `x_myapp` scope. Including the prefix yourself produces a build warning in any non-global scope — the build still derives the correct `scoped_name`, since it leaves an already-prefixed name unchanged.

- Extract the Jelly to a `.jelly.xml` file and reference it with `Now.include()`. This avoids `${...}` escaping and gives you XML syntax highlighting.

- Write a `description` that names the parameters the macro accepts. It is the only parameter documentation a consumer of the macro sees.

- Read parameters as `jvar_` variables: an attribute passed as `<g:x_myapp_my_macro message="Hi" />` (the scoped invocation tag) is available inside the macro as `${jvar_message}` in phase one, or as `jelly.jvar_message` inside a `jelly="true"` evaluate block.

- Fluent warns on malformed XML. The build checks the `xml` field for mismatched tags, unclosed elements, and invalid XML characters in element text (bare `<` and `&`) — the same characters inside an attribute value are not checked by the build, but are still invalid XML and must be escaped, e.g. a Jelly condition must be written `test="${a &amp;&amp; b}"`, not `test="${a && b}"`, or the platform's own parser rejects it at render time. These are warnings only — the content is written as-is and the build is not blocked. Runtime Jelly errors (unknown tags, expression failures) still surface only when the form renders.

## Key Concepts

### UiMacro API

```
import { UiMacro } from '@servicenow/sdk/core'

UiMacro({
    $id: Now.ID['my-macro'],
    name: 'my_macro',
    description: 'Describes what the macro does and the parameters it accepts.',
    xml: Now.include('./my-macro.jelly.xml'),
})
```

See "Alert Banner Macro" under Examples below for a complete, working macro.

### Properties

See the `uimacro-api` topic for the full property list, types and defaults.

`UiMacro` also accepts `protectionPolicy`, `$override`, and `$meta` — see the `uimacro-api` topic for what each controls.

### Scope Prefix Validation

The build emits a warning when `name` starts with the application scope followed by `_`:

```
UI Macro name 'x_myapp_alert_banner' already includes the application scope prefix 'x_myapp_'. Consider omitting it — the build derives the scope prefix for scoped_name automatically for names that don't already carry it.
```

Two things to know about this check:

- It is a warning, not an error. The build still succeeds — real legacy macros exist with this shape and resolve fine at runtime, and the build derives the correct `scoped_name` either way (it leaves an already-prefixed name unchanged rather than doubling the prefix).

- It runs in every non-global scope, including `sn_`-prefixed scopes. Global scope has no prefix, so it is not checked.

### Project Structure

```
src/
  fluent/
    example.now.ts             # UiMacro and sys_ui_formatter Record definitions
    alert-banner.jelly.xml     # Jelly for the alert banner macro
    info-card.jelly.xml        # Jelly for the info card macro
    incident-form.now.ts       # Form() that references the formatter
```

### Why `Now.include()` for Jelly

Jelly relies on `${...}` expressions. Inlined in a TypeScript template literal, every one of them has to be escaped as `\${...}` or JavaScript interpolates it first:

```
// BAD -- every Jelly expression needs escaping, and the editor sees no XML
UiMacro({
    $id: Now.ID['my-macro'],
    name: 'my_macro',
    xml: `<?xml version="1.0" encoding="utf-8" ?>
<j:jelly trim="false" xmlns:j="jelly:core" xmlns:g="glide">
    <div>\${jvar_message}</div>
</j:jelly>`,
})
```

```
// GOOD -- no escaping, XML tooling works, the Fluent file stays readable
UiMacro({
    $id: Now.ID['my-macro'],
    name: 'my_macro',
    xml: Now.include('./my-macro.jelly.xml'),
})
```

Both forms produce the same `xml` column. Inline strings are supported, but reserve them for one-liners.

## Jelly in UI Macros

A macro's `xml` is a Jelly template. See the `jelly-guide` topic for the template preamble, the two-phase (`j:`/`g:` vs `j2:`/`g2:`) evaluation model and caching, XML-safe JavaScript inside `<script>` blocks, server-side `g2:evaluate` script, and conditional rendering. The sections below cover what is specific to UI Macros.

### Parameters and `jvar_` Variables

Each attribute on an invoking tag becomes a `jvar_`-prefixed Jelly variable. Read it in phase one as `${jvar_name}`, or inside a `jelly="true"` evaluate block as `jelly.jvar_name` (coerce with `+ ''` before using it as a string).

When one macro invokes another, attributes become parameters:

```
<!-- caller -->
<g:x_myapp_alert_banner type="info" message="Hello" />

<!-- inside the macro: ${jvar_type} is "info", ${jvar_message} is "Hello" -->
<div class="alert alert-${jvar_type}">${jvar_message}</div>
```

Parameters are not request parameters — `RP.getParameterValue()` does not read them.

### Client-Rendered Formatter Values

For values already loaded on the form, do not render them server-side at all — phase-one output is cached and cannot reflect unsaved edits anyway. Render a static shell, then initialize and update it from `g_form` in client script inside the macro:

- Render a static shell (`<tr><td colspan="2">` containing the panel markup) and hydrate it client-side after form load — defer setup with `addLateLoadEvent`.

- Read initial values from `g_form` (`g_form.getValue('field')`, or the control's selected option for display labels) — no server query or record-ID lookup is needed.

- Observe each dependent control with `addEventListener('change', ...)` and re-apply the display on every change so the panel tracks unsaved edits.

- Use `textContent` for scalar values and set styles/attributes explicitly (`setAttribute`, `style` properties); never inject values with `innerHTML`.

- Use GlideAjax only for live server-only data — fields and values absent from `g_form`. The Script Include must be client callable and invoked by its installed scoped API name; schedule the next refresh inside the `getXMLAnswer` callback so requests never overlap.

A phase-one server payload is not a reliable initial render — even when it happens to be fresh, it goes stale the moment the user edits the form. The `g_form` + change-listener pattern above is the primary pattern; GlideAjax is an optional enhancement:

```
function refresh() {
    var ajax = new GlideAjax('x_myapp.IncidentStatusAjax');
    ajax.addParam('sysparm_name', 'getStatus');
    ajax.addParam('sysparm_sys_id', g_form.getUniqueValue());
    ajax.getXMLAnswer(function (answer) {
        apply(JSON.parse(answer));
        window.setTimeout(refresh, 30000);
    });
}
window.setTimeout(refresh, 30000);
```

## Using a Macro as a Form Formatter

Fluent has no dedicated formatter constructor. To put a custom macro on a form:

- Define the `UiMacro`.

- Create the `sys_ui_formatter` row with the generic `Record()` API, setting its `formatter` field to the macro's real element filename. FormPlugin never scope-prefixes this value, so you must supply it directly — see the `form-formatters-guide` topic's scoped-filename rule for exactly which filename to use in a scoped vs. global app.

- Reference that record from a `Form()` formatter element — `formatterRef` accepts a `Record<'sys_ui_formatter'>`. `formatterName` is optional (FormPlugin derives it from the record's `formatter` field when omitted) — but either way, whatever filename ends up in play is written to `sys_ui_element.element` exactly as given, with no prefixing or stripping.

Prefer a built-in formatter where one exists; see the `form-formatters-guide` topic for the predefined `Formatter.*` constants and the per-formatter prerequisites.

### Formatter Data

Formatter data has different sources depending on when it must refresh. Server-rendered Jelly cannot see unsaved form edits, so choose the source by lifecycle:

- Values already loaded on the form — read them client-side from `g_form` and re-read them on every dependent field `change` event. This is the common case; see "Client-Rendered Formatter Values" above and the full example below.

- Request-dependent server values for the initial render — compute them in phase two (`g2:evaluate` / `$[...]`), never in cached phase one; see the `jelly-guide` topic's "Server-Side Script".

- Live server-only data — use a client-callable scoped GlideAjax Script Include. Do not call GlideAjax for values already present in `g_form`.

## Examples

The first two show macro definitions with common Jelly patterns; the rest cover wiring a macro into a form formatter, Service Catalog variable, and cart, plus deactivating one.

### Alert Banner Macro

Accepts `type` and `message`, and renders nothing when `message` is empty.

`example.now.ts`:

```
import { UiMacro } from '@servicenow/sdk/core'

UiMacro({
    $id: Now.ID['alert-banner'],
    name: 'alert_banner', // In scope x_myapp, the build derives scoped_name: x_myapp_alert_banner
    description: 'Displays a styled alert banner. Parameters: type (info|success|warning|danger), message.',
    xml: Now.include('./alert-banner.jelly.xml'),
})
```

`alert-banner.jelly.xml`:

```
<?xml version="1.0" encoding="utf-8" ?>
<j:jelly trim="false" xmlns:j="jelly:core" xmlns:g="glide" xmlns:j2="null" xmlns:g2="null">

    <j:if test="${!gs.nil(jvar_message)}">
        <div class="alert alert-${jvar_type}" role="alert" style="margin: 10px 0; padding: 12px 16px; border-radius: 4px;">
            <strong>
                <j:if test="${jvar_type == 'danger'}">Error: </j:if>
                <j:if test="${jvar_type == 'warning'}">Warning: </j:if>
                <j:if test="${jvar_type == 'success'}">Success: </j:if>
                <j:if test="${jvar_type == 'info'}">Info: </j:if>
            </strong>
            ${jvar_message}
        </div>
    </j:if>

</j:jelly>
```

### Record Count Card Macro

Accepts `title` and `table`, and aggregates a count server-side.

```
import { UiMacro } from '@servicenow/sdk/core'

UiMacro({
    $id: Now.ID['info-card'],
    name: 'info_card', // In scope x_myapp, the build derives scoped_name: x_myapp_info_card
    description: 'Shows a record count card. Parameters: title, table.',
    xml: Now.include('./info-card.jelly.xml'),
})
```

If wiring this macro to a form formatter in a scoped app, the `sys_ui_formatter` Record's `formatter` field must use the scoped filename (`x_myapp_info_card.xml`), not the unprefixed local name — see "Using a Macro as a Form Formatter" above.

`info-card.jelly.xml`:

```
<?xml version="1.0" encoding="utf-8" ?>
<j:jelly trim="false" xmlns:j="jelly:core" xmlns:g="glide" xmlns:j2="null" xmlns:g2="null">

    <g2:evaluate var="jvar_count" jelly="true">
        var gr = new GlideAggregate(jelly.jvar_table + '');
        gr.addAggregate('COUNT');
        gr.query();
        var count = 0;
        if (gr.next()) {
            count = parseInt(gr.getAggregate('COUNT'), 10) || 0;
        }
        count;
    </g2:evaluate>

    <div style="display: inline-block; width: 200px; margin: 8px; padding: 16px; border: 1px solid #ddd; border-radius: 8px; text-align: center; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <div style="font-size: 32px; font-weight: bold; color: #485fc7;">$[jvar_count]</div>
        <div style="font-size: 14px; color: #666; margin-top: 4px;">${jvar_title}</div>
    </div>

</j:jelly>
```

### Form Formatter Using a Macro

This example wires a status panel UI macro to an incident form as a custom formatter. The formatter displays a styled panel showing the incident's current state and priority.

```
import { UiMacro, Record, Form, default_view } from '@servicenow/sdk/core'

UiMacro({
    $id: Now.ID['incident-status-panel'],
    name: 'incident_status_panel', // In scope x_myapp, the build derives scoped_name: x_myapp_incident_status_panel
    description: 'Displays a styled status panel for the requested incident record.',
    xml: Now.include('./incident-status-panel.jelly.xml'),
})

const incidentStatusFormatter = Record({
    $id: Now.ID['incident-status-formatter'],
    table: 'sys_ui_formatter',
    data: {
        name: 'Incident Status Panel',
        type: 'formatter',
        // The scoped filename, matching this UiMacro's real scoped_name in an x_myapp-scoped app —
        // see "Using a Macro as a Form Formatter" above. FormPlugin does not compute this for you.
        formatter: 'x_myapp_incident_status_panel.xml',
        table: 'incident',
        active: true,
    },
})

Form({
    table: 'incident',
    view: default_view,
    sections: [
        {
            caption: 'Status Overview',
            content: [
                {
                    layout: 'one-column',
                    elements: [
                        { type: 'formatter', formatterRef: incidentStatusFormatter, formatterName: 'x_myapp_incident_status_panel.xml' },
                        { type: 'table_field', field: 'state' },
                        { type: 'table_field', field: 'priority' },
                    ],
                },
            ],
        },
    ],
})
```

The `formatter` field and `formatterName` here both use the macro's real scoped filename (`x_myapp_incident_status_panel.xml`, assuming an `x_myapp`-scoped app) — FormPlugin does not compute this for you; whatever filename you give it is written straight to `sys_ui_element.element`. Using the unprefixed local name (`incident_status_panel.xml`) here would build without error but wouldn't resolve to any real macro in a non-global scope, since this `UiMacro`'s own `scoped_name` is `x_myapp_incident_status_panel`, not `incident_status_panel`. The `state` and `priority` `table_field` elements ensure those controls are loaded on the form so `g_form` can read and observe them.

`incident-status-panel.jelly.xml` renders a static shell and lets client script hydrate it from `g_form` — no server query and no record-ID lookup:

```
<?xml version="1.0" encoding="utf-8" ?>
<j:jelly trim="false" xmlns:j="jelly:core" xmlns:g="glide" xmlns:j2="null" xmlns:g2="null">
    <tr>
        <td colspan="2" width="100%">
            <div id="incident_status_panel" style="padding: 12px 16px; border: 1px solid #ddd; border-radius: 4px; margin: 10px 0;">
                <span id="incident_status_badge" style="display: inline-block; padding: 2px 8px; border-radius: 3px; background: #485fc7; color: #fff;">--</span>
                <div><strong>State:</strong> <span id="incident_status_state">--</span></div>
                <div><strong>Priority:</strong> <span id="incident_status_priority">--</span></div>
            </div>
            <script type="text/javascript">
                (function () {
                    function labelFor(fieldName) {
                        var control = g_form.getControl(fieldName);
                        if (control) {
                            if (control.options) {
                                if (control.selectedIndex > -1) {
                                    return control.options[control.selectedIndex].text;
                                }
                            }
                        }
                        return g_form.getValue(fieldName) || '--';
                    }
                    function update() {
                        var stateLabel = labelFor('state');
                        var priorityLabel = labelFor('priority');
                        var stateEl = document.getElementById('incident_status_state');
                        var priorityEl = document.getElementById('incident_status_priority');
                        var badge = document.getElementById('incident_status_badge');
                        if (stateEl) {
                            stateEl.textContent = stateLabel;
                        }
                        if (priorityEl) {
                            priorityEl.textContent = priorityLabel;
                        }
                        if (badge) {
                            badge.textContent = stateLabel;
                            badge.setAttribute('data-state', g_form.getValue('state') || '');
                        }
                    }
                    function observeField(fieldName) {
                        var control = g_form.getControl(fieldName);
                        if (!control) {
                            return;
                        }
                        if (control.addEventListener) {
                            control.addEventListener('change', update, false);
                        } else if (control.attachEvent) {
                            control.attachEvent('onchange', update);
                        }
                    }
                    function init() {
                        if (typeof g_form === 'undefined') {
                            return;
                        }
                        update();
                        observeField('state');
                        observeField('priority');
                    }
                    if (typeof addLateLoadEvent === 'function') {
                        addLateLoadEvent(init);
                    } else if (window.addEventListener) {
                        window.addEventListener('load', init);
                    } else if (window.attachEvent) {
                        window.attachEvent('onload', init);
                    }
                })();
            </script>
        </td>
    </tr>
</j:jelly>
```

The script writes only through `textContent` and `setAttribute`, derives display labels from each select control's selected option, and re-applies on every `change` event, so the panel tracks unsaved edits. The field observers use `addEventListener` with an `attachEvent` fallback; initialization uses `addLateLoadEvent`, then `window.addEventListener('load', ...)`, then `attachEvent`.

Formatter output is inserted inside a platform `<table>` — wrap visual content in `<tr><td colspan="2">...</td></tr>` rather than emitting a top-level `<div>`.

Every element opened in a Jelly template must be closed. An unclosed `<div>` produces a build warning — Fluent validates the `xml` field for mismatched tags, unclosed tags, and invalid XML characters in element text, such as bare `<` and `&`. The same characters inside an attribute value are not checked by the build, but are still invalid XML — escape a Jelly condition as `test="${a &amp;&amp; b}"`, not `test="${a && b}"`, or the platform's own parser rejects it at render time.

### Catalog Variable Using a Macro

UI Macros can be embedded directly into Service Catalog forms through `CustomVariable` and `CustomWithLabelVariable`. The `macro` property on these variables accepts a `UiMacro` reference, which the platform renders inline on the catalog request form.

`CustomVariable` renders the macro without a label; `CustomWithLabelVariable` displays the `question` text as a visible label above the macro. Neither type supports `mandatory`, `hidden`, or `readOnly`.

```
import { CatalogItem, CustomVariable, CustomWithLabelVariable, UiMacro, SingleLineTextVariable } from '@servicenow/sdk/core'

const searchPanelMacro = UiMacro({
    $id: Now.ID['catalog-search-panel'],
    name: 'catalog_search_panel',
    description: 'Renders an inline contextual search panel on a catalog form.',
    category: 'catalog',
    xml: Now.include('./catalog-search-panel.jelly.xml'),
})

const dateRangeMacro = UiMacro({
    $id: Now.ID['date-range-picker'],
    name: 'date_range_picker',
    description: 'Renders a custom date range picker on a catalog form.',
    category: 'catalog',
    xml: Now.include('./date-range-picker.jelly.xml'),
})

export const serviceRequest = CatalogItem({
    $id: Now.ID['service-request'],
    name: 'Service Request',
    shortDescription: 'Submit a service request',
    variables: {
        // No label — macro renders directly on the form
        search_results: CustomVariable({
            question: 'Contextual Search Results',
            macro: searchPanelMacro,
            order: 100,
        }),
        // Label shown above the macro
        travel_dates: CustomWithLabelVariable({
            question: 'Select Travel Dates',
            macro: dateRangeMacro,
            order: 200,
        }),
        description: SingleLineTextVariable({
            question: 'Description',
            order: 300,
            mandatory: true,
        }),
    },
})
```

Catalog variables also support `widget` (Service Portal), `macroponent` (Next Experience), and `topicBlock` (Virtual Agent) for cross-context rendering. A single variable can set both `macro` and `widget` so the correct component renders in each context. The `summaryMacro` property provides a separate read-only rendering on confirmation pages.

### Catalog Client Script Isolation

ServiceNow runs catalog client scripts in scoped applications in isolated mode by default. Isolated scripts execute in strict mode with `window`, `document`, `jQuery`, and `prototype` set to `null`. A catalog client script that references `window` to call a function registered by the macro fails at runtime:

```
TypeError: Cannot read properties of null (reading 'x_myapp_refreshMyComponent')
```

The platform warns on the script record: "This catalog client script is not VA supported due to the presence of the following variables in the script: window.x_myapp_…, window.setTimeout"

Do not create catalog client scripts (`onChange`, `onLoad`, `onSubmit`) that bridge to the macro through `window`. Instead, let the macro's inline `<script>` self-initialize and bind its own `g_form` listeners directly — the inline script runs in the global scope where `g_form`, `document`, and DOM APIs are available:

```
<script type="text/javascript">
    (function () {
        function refresh() {
            var level = g_form.getValue('access_level') || '';
            var badge = document.getElementById('my_badge');
            if (badge) {
                badge.textContent = level || 'Not assessed';
            }
        }
        function listen(fieldName) {
            var control = g_form.getControl(fieldName);
            if (control) {
                control.addEventListener('change', refresh, false);
            }
        }
        function init() {
            if (typeof g_form === 'undefined') { return; }
            refresh();
            listen('access_level');
            listen('business_justification');
        }
        if (typeof addAfterPageLoadedEvent === 'function') {
            addAfterPageLoadedEvent(init);
        }
    })();
</script>
```

This pattern avoids catalog client scripts entirely. The macro reads initial values from `g_form`, observes each dependent field's control, and refreshes itself on every change — all without crossing the isolation boundary. It uses `addAfterPageLoadedEvent` rather than the form-formatter example's `addLateLoadEvent` because a catalog variable's macro renders as part of the catalog item page itself, not a platform form section — `addAfterPageLoadedEvent` is the catalog/Service Portal page's own post-load hook.

For the full property reference, see `customvariable-api` and `customwithlabelvariable-api`.

### Summary Macro for Custom Variables

When a user submits a catalog request, the confirmation and request-summary pages show each variable's value. For standard variables the platform renders the raw value, but a custom variable backed by a rich interactive macro (risk badge, cost calculator, readiness checklist) has no meaningful raw value — the user sees blank or a sys_id.

The `summaryMacro` property on `CustomVariable` / `CustomWithLabelVariable` provides a separate read-only UI Macro that renders a human-readable version on those pages. It receives the same variable context but should not include edit controls, change listeners, or `g_form` calls — the summary page has no live form.

```
import { CatalogItem, CustomWithLabelVariable, UiMacro, SelectBoxVariable, SingleLineTextVariable } from '@servicenow/sdk/core'

const budgetPreviewMacro = UiMacro({
    $id: Now.ID['budget-preview-macro'],
    name: 'budget_preview',
    description: 'Interactive budget preview with live cost estimate.',
    category: 'catalog',
    xml: Now.include('./budget-preview.jelly.xml'),
})

const budgetSummaryMacro = UiMacro({
    $id: Now.ID['budget-summary-macro'],
    name: 'budget_summary',
    description: 'Read-only budget summary for confirmation and request pages.',
    category: 'catalog',
    xml: Now.include('./budget-summary.jelly.xml'),
})

export const eventRequest = CatalogItem({
    $id: Now.ID['event-request'],
    name: 'Plan a Corporate Event',
    shortDescription: 'Request a corporate event',
    variables: {
        venue_type: SelectBoxVariable({
            question: 'Venue Type',
            order: 100,
            mandatory: true,
            choices: {
                internal: { label: 'Internal', sequence: 1 },
                hotel: { label: 'Hotel', sequence: 2 },
                convention: { label: 'Convention Center', sequence: 3 },
            },
        }),
        attendees: SingleLineTextVariable({
            question: 'Expected Attendees',
            order: 200,
            mandatory: true,
        }),
        budget_preview: CustomWithLabelVariable({
            question: 'Budget Preview',
            macro: budgetPreviewMacro,
            summaryMacro: budgetSummaryMacro,
            order: 300,
        }),
    },
})
```

The interactive macro (`budget-preview.jelly.xml`) reads `g_form` values and updates live. The summary macro (`budget-summary.jelly.xml`) renders a static read-only display — typically reading submitted variable values from the request item context rather than `g_form`.

### Custom Cart Macro

The `customCart` property on `CatalogItem` replaces the entire default cart/checkout section (Add to Cart, Order Now, Proceed to Checkout buttons) with a custom UI Macro. Use this when the standard checkout flow is insufficient — for example:

- License agreement: Show terms the user must accept before submitting

- Payment form: Collect billing information before the request is created

- Bundle confirmation: Show a breakdown of everything that will be provisioned

- Approval preview: Show the approval chain this request will trigger based on the variable values

```
import { CatalogItem, UiMacro, SelectBoxVariable, CheckboxVariable } from '@servicenow/sdk/core'

const licenseCartMacro = UiMacro({
    $id: Now.ID['license-cart-macro'],
    name: 'license_agreement_cart',
    description: 'Custom cart with license agreement acceptance before checkout.',
    category: 'catalog',
    xml: Now.include('./license-agreement-cart.jelly.xml'),
})

export const softwareRequest = CatalogItem({
    $id: Now.ID['software-request'],
    name: 'Request Software License',
    shortDescription: 'Request a new software license',
    customCart: licenseCartMacro,
    variables: {
        software_title: SelectBoxVariable({
            question: 'Software',
            order: 100,
            mandatory: true,
            choices: {
                ide: { label: 'IDE Pro', sequence: 1 },
                design: { label: 'Design Suite', sequence: 2 },
                analytics: { label: 'Analytics Platform', sequence: 3 },
            },
        }),
        accept_terms: CheckboxVariable({
            question: 'I accept the license terms',
            order: 200,
        }),
    },
})
```

The custom cart macro renders inside the standard catalog item page layout, replacing only the cart/checkout buttons and summary area. It must provide its own submit mechanism (typically a button that calls the catalog order API). The macro's inline `<script>` can read variable values from `g_form` to customize the checkout display.

### Deactivating a Macro

Set `active: false` to disable a macro without deleting the record. See the `uimacro-api` topic's "Deactivated UI Macro" example.

## Avoidance

- Never inline Jelly in a TypeScript template literal for anything beyond a one-liner — use `Now.include()` for a `.jelly.xml` file.

- Never include the scope prefix in `name` — the build derives `scoped_name` from the unprefixed name; a prefixed name produces a build warning in any non-global scope.

- Never set `mediaType` to a MIME type — it is a device type/variant lookup key, not a content type; values like `'text/html'` produce a build warning, because the platform looks macros up by device type and never matches a MIME-style value, so the macro silently fails to resolve at render time. Omit it for standard macros and form formatters.

- Update every `<g:...>` invocation when renaming a macro — the record is identified by `$id`, so a rename updates it in place, but callers still invoke the old tag name.

- Never set `sys_name` or `scoped_name` — the build derives both from `name`.

- Never create catalog client scripts that reference `window` to call macro functions — scoped catalog client scripts run in isolated mode where `window` is `null`. Let the macro's inline `<script>` self-initialize with `g_form` listeners instead.

- Never expect server-rendered Jelly to react to unsaved field changes — use `g_form` and field `change` handlers instead.

- Never call GlideAjax for values already present in `g_form` — reserve it for server-only data.

- Never emit a top-level `<div>` from a formatter macro — formatter output is inserted inside a platform `<table>`; wrap visual content in `<tr><td colspan="2">...</td></tr>`.

- Never use `innerHTML` for server-derived scalar values — use `textContent` and explicit styles/attributes.

- Never read macro parameters with `RP.getParameterValue()` — attributes passed between macros arrive as `${jvar_*}` variables; only request parameters such as `sys_id` come from `RP`.

- Never ship malformed XML — the build validates the `xml` field and warns on mismatched tags, unclosed elements, and bare `<` or `&` characters in element text (not inside attribute values). Unknown tags and runtime Jelly errors still surface only when the form renders.

- Never create a macro to hold a React component — React interfaces belong in a UI Page built from `@servicenow/react-components`, not in a form formatter.

- For Jelly phase, caching, and XML-safe script pitfalls, see the `jelly-guide` topic's Avoidance section.

## Related Topics

- `uimacro-api` — full `UiMacro` property reference

- `jelly-guide` — Jelly template structure, phases and caching, XML-safe script, and server-side evaluate

- `form-formatters-guide` — predefined formatters and form placement

- `customvariable-api` — Custom variable that embeds a macro in a catalog form (no label)

- `customwithlabelvariable-api` — Custom variable with a displayed label

- `service-catalog-variables-guide` — all variable types and catalog examples

- `catalogitem-api` — Catalog Item configuration reference

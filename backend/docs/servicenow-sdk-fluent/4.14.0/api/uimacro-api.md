Version: 4.14.0

# UiMacro

Creates a UI Macro — a reusable Jelly component that accepts parameters, renders HTML, and can run server-side script (`sys_ui_macro`). UI Macros are invoked by name from Jelly UI Pages, form formatters, Service Catalog variable types, and other UI Macros.

## Signature

```
UiMacro(config)
```

## Parameters

### config

`UiMacro`

Properties:

- 
$id (required): `string | number | ExplicitKey<string>`

- 
$meta (optional): `object`

- installMethod: `'first install' | 'demo' | 'once'`
Map a record to an output folder that loads only in specific circumstances.
'first install' -> 'unload' (only loaded when the plugin is first registered),
'demo' -> 'unload.demo' (only loaded when demo data is loaded),
'once' -> 'apply_once' (scripts that are only applied once)

- useEsLatest: `boolean`
Controls whether the macro's server-side script runs with the latest supported ECMAScript version rather than the application's default. Omit to leave the sys_app/now.config default in place.

- 
name (required): `string`
Local name of the UI Macro, without the scope prefix. Choose a distinctive name: the platform rejects saving an active macro whose `name` and `mediaType` match another active macro anywhere on the instance, in any scope. Two macros in the same project with the same `name` and `mediaType` are a build error; collisions with macros outside the project only surface at install time. In scoped applications, invoke the macro with the scope-qualified tag, e.g. `<g:x_myapp_alert_banner />` for a macro named `alert_banner` in scope `x_myapp`. Including the scope prefix in `name` yourself produces a build warning, and `<scope>_<name>` longer than 100 characters is a build error. Renaming a macro updates the existing record in place (it is identified by `$id`), but update every `<g:...>` invocation that uses the old name.

- 
active (optional): `boolean`
Set to `false` to disable the macro without deleting it. Defaults to `true`.

- 
category (optional): `'general' | 'catalog' | 'layout' | 'cms' | '' | (string & {})`
Category used to group and filter macros in the UI Macro list, e.g. `'catalog'` for Service Catalog variable and cart macros. Use `''` to explicitly clear the category on a record that previously had one set. Defaults to `'general'`. This is a choice field on the platform, not free text — the listed values are the known choices, but the SDK still accepts any other string for forward compatibility with choices added later.

- 
description (optional): `string`
Free-text notes for other developers, shown on the macro's record form (not rendered at runtime). UI Macros have no typed parameter list, so document the Jelly variables the macro accepts here — it's the only parameter documentation other developers see. Empty by default.

- 
mediaType (optional): `string`
Optional device type/variant lookup key — not an HTTP MIME type. Omit it for standard UI Macros and form formatters: MIME-style values such as `'text/html'` are never matched by the platform's device-type macro lookup, so the macro silently fails to resolve at render time; the build produces a warning. Empty by default.

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit/view access for other developers after the application is installed.

- read: Others can see the Jelly but not change it.

- protected: Others cannot change this record.

- Omit to allow other developers to customize this record.

- 
xml (optional): `string`
Jelly XML content defining the macro behavior. Prefer `Now.include()` to keep the Jelly in a separate `.jelly.xml` file, which avoids escaping every `${...}` expression. The build reports malformed XML (mismatched or unclosed tags, bare `<` or `&` in element text) as a warning (the content is still written as-is). Attribute values and runtime Jelly errors are not checked at build time. See the `jelly-guide` topic for Jelly phases, caching, and XML-safe script content. Empty by default.

`name` populates the record's `name` and `sys_name` columns; the build sets the read-only `scoped_name` ("API Name") to `<scope>_<name>` in scoped applications, and leaves it empty for global-scope macros. Do not set `sys_name` or `scoped_name` directly. See the `name` property above for the platform's cross-scope uniqueness check.

## Examples

### UI Macro with External Jelly File

Create a reusable alert banner macro whose Jelly lives in a separate file. This is the recommended form.

```
/**
 * @title UI Macro with External Jelly File
 * @description Create a reusable alert banner macro whose Jelly lives in a separate file
 */
import { UiMacro } from '@servicenow/sdk/core'

UiMacro({
    $id: Now.ID['alert-banner'],
    name: 'alert_banner',
    description: 'Displays a styled alert banner. Parameters: type (info|success|warning|danger), message.',
    xml: Now.include('./alert-banner.jelly.xml'),
})
```

See the `ui-macro-guide` topic's "Alert Banner Macro" example for the full `alert-banner.jelly.xml` content. Each attribute on the invoking tag arrives as a `jvar_`-prefixed Jelly variable. Invoke it using the scoped tag name (e.g., in scope `x_myapp`):

```
<g:x_myapp_alert_banner type="info" message="Welcome" />
```

### UI Macro with Server-Side Script

Use `<g2:evaluate jelly="true">` to run server-side JavaScript per request. Phase-two `g2:`/`j2:` tags avoid the phase-one macro compilation cache, phase-two values are emitted with `$[...]`, and invocation parameters are read inside the script as `jelly.jvar_*`. Stable invocation parameters and other phase-one values still use `${...}`. The `var` attribute receives the value of the block's last expression.

```
/**
 * @title UI Macro with Server-Side Script
 * @description Create a card macro that aggregates a record count server-side
 */
import { UiMacro } from '@servicenow/sdk/core'

UiMacro({
    $id: Now.ID['info-card'],
    name: 'info_card',
    description: 'Shows a record count card. Parameters: title, table.',
    xml: Now.include('./info-card.jelly.xml'),
})
```

See the `ui-macro-guide` topic's "Record Count Card Macro" example for the full `info-card.jelly.xml` content. `g2:evaluate` avoids the phase-one macro compilation cache so the count is computed on every request, and `$[jvar_count]` emits the phase-two value. `${jvar_title}` still resolves in phase one because the parameter is stable for the compiled macro. Pass only table and field names as parameters this way — never raw user input that could alter the query.

### UI Macro with Inline Jelly

Inline Jelly is supported. Every `${...}` expression must be escaped as `\${...}` so JavaScript does not interpolate it first, so reserve this form for short content.

```
/**
 * @title UI Macro with Inline Jelly
 * @description Create a macro with its Jelly defined inline
 */
import { UiMacro } from '@servicenow/sdk/core'

UiMacro({
    $id: Now.ID['sample-macro'],
    name: 'alert',
    description: 'Displays an alert message',
    active: true,
    category: 'general',
    xml: `<?xml version="1.0" encoding="utf-8" ?>
<j:jelly trim="false" xmlns:j="jelly:core" xmlns:g="glide" xmlns:j2="null" xmlns:g2="null">
    <div class="alert" role="alert">Hello</div>
</j:jelly>`,
})
```

### Catalog Macro with Protection

Classify a macro for Service Catalog use and ship it read-only so installing developers can inspect but not modify the Jelly.

```
/**
 * @title Catalog Macro with Protection
 * @description Create a protected catalog-category macro
 */
import { UiMacro } from '@servicenow/sdk/core'

UiMacro({
    $id: Now.ID['catalog-widget'],
    name: 'catalog_widget',
    description: 'Renders a custom catalog variable. Parameters: message.',
    category: 'catalog',
    protectionPolicy: 'read',
    xml: Now.include('./catalog-widget.jelly.xml'),
})
```

### Deactivated UI Macro

Disable a macro without deleting the record.

```
/**
 * @title Deactivated UI Macro
 * @description Disable a macro without deleting the record
 */
import { UiMacro } from '@servicenow/sdk/core'

UiMacro({
    $id: Now.ID['deprecated-macro'],
    name: 'old_widget',
    active: false,
    description: 'Deprecated. Use new_widget instead.',
    xml: Now.include('./old-widget.jelly.xml'),
})
```

For Jelly syntax, parameter passing, and formatter usage, see the `ui-macro-guide` topic.

## See

- `ui-macro-guide` — parameter passing, formatter usage, and client-rendered patterns.

- `jelly-guide` — Jelly phases, caching, XML-safe script content, and server-side evaluate.

- `override-guide` — setting record columns not directly supported by the API.

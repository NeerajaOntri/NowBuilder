Version: 4.14.0

# SPPage

Creates a Service Portal page — a layout of widget instances organized into containers, rows, and columns (`sp_page`). Pages are the top-level navigation targets in a portal and define the visual structure users interact with.

## Signature

```
SPPage(config)
```

## Parameters

### config

`SPPage`

Properties:

- 
pageId (required): `string`
URL-level identifier for the page, used in routing (`?id=<pageId>`).
Maps to `sp_page.id`. Must be unique within the portal (required).

- 
$meta (optional): `object`

- installMethod: `'first install' | 'demo' | 'once'`
Map a record to an output folder that loads only in specific circumstances.
'first install' - > 'unload',
'demo' -> 'unload.demo'

- 
category (optional, default: 'custom'): `PageCategory`
Groups the page in the portal designer for organisational purposes.
Valid values: `'custom'`, `'standard'`, `'sample'`, `'sp_platform'`,
`'kb'`, `'other'`, `'sc'`, `'sn_ex_sp_taxonomy'`.

- 
containers (optional): `SPContainer[]`
Top-level layout sections of the page. Each container holds rows of columns
which hold widget instances. Renders in ascending `order` value.

SPContainer properties:

- $id (required): `string | number | ExplicitKey<string>`

- name (optional): `string` — Admin label for the container. Auto-generated as `"<pageTitle> - Container <order>"` if omitted.

- title (optional): `string` — Visible heading rendered above the container content.

- width (optional, default: `'container'`): `'container' | 'container-fluid'` — Bootstrap layout width. `'container'` = fixed max-width centered; `'container-fluid'` = full viewport width.

- backgroundColor (optional): `string` — CSS color value for the container background (e.g. `'#f5f5f5'`).

- backgroundImage (optional): `string` — URL or attachment reference for a container background image.

- backgroundStyle (optional, default: `'default'`): `'default' | 'contain' | 'repeat' | 'cover'` — Controls how the background image is rendered: `'default'` — no special background behavior; `'contain'` — scales image to fit within the container; `'repeat'` — tiles the image; `'cover'` — scales image to cover the full container area.

- cssClass (optional): `string` — CSS class added to the inner container element.

- parentClass (optional): `string` — CSS class added to the outer wrapper element (above the Bootstrap container).

- subheader (optional, default: false): `boolean` — Renders the container in the subheader position (below the main header).

- bootstrapAlt (optional, default: false): `boolean` — Applies alternate Bootstrap column rendering for the container.

- semanticTag (optional): `'main'` — Renders the container as an HTML5 `<main>` element for accessibility. Only one `<main>` element should exist per page.

- order (optional): `number` — Sort order of this container on the page. Lower renders first.

- rows (optional): `SPRow[]` — Rows inside this container.

SPRow properties:

- $id (required): `string | number | ExplicitKey<string>`

- cssClass (optional): `string` — CSS class added to the `sp_row` wrapper element.

- semanticTag (optional): `'main'` — Renders the row as an HTML5 `<main>` element instead of `<div>` for improved page accessibility and landmark navigation.

- order (optional): `number` — Sort order of this row within the container.

- columns (optional): `SPColumn[]` — Columns inside this row.

SPColumn properties:

- $id (required): `string | number | ExplicitKey<string>`

- size (optional, default: 12): `number` — Bootstrap `md` column width (1–12). Columns in a row should sum to 12.

- sizeSm (optional): `number` — Bootstrap `sm` breakpoint column width (1–12).

- sizeLg (optional): `number` — Bootstrap `lg` breakpoint column width (1–12).

- sizeXs (optional): `number` — Bootstrap `xs` breakpoint column width (1–12). Set to 12 to stack on mobile.

- cssClass (optional): `string` — CSS class added to the column element.

- semanticTag (optional): `'main'` — Renders the column as an HTML5 `<main>` element instead of `<div>` for improved page accessibility and landmark navigation.

- order (optional): `number` — Sort order of this column within the row.

- instances (optional): `SPInstance[]` — Widget instances placed in this column.

- nestedRows (optional): `SPRow[]` — Rows nested inside this column (for advanced two-dimensional layouts).

SPInstance properties:

- $id (required): `string | number | ExplicitKey<string>`

- widget (optional): `string | Record<'sp_widget'> | SPWidget` — The widget to render. Pass an SPWidget object for owned widgets, or a sys_id string for OOTB widgets.

- widgetParameters (optional): `JsonSerializable` — Key-value pairs passed to the widget's server and client scripts as `options`. Accepts a JSON string, a plain object (auto-serialized by the build plugin), or `Now.include('./params.json')`. Keys must match `optionSchema` `name` values. See `spwidget-api`.

- title (optional): `string` — Heading text displayed above the widget instance in the portal UI.

- id (optional): `string` — Unique string identifier for the `sp_instance` record.

- shortDescription (optional): `string` — Admin-facing description. Not shown to end users.

- column (optional): `string | Record<'sp_column'>` — Reference to the `sp_column` record this instance belongs to (used internally).

- css (optional): `string` — SCSS or CSS scoped to this instance only, applied in addition to the widget's own CSS.

- url (optional): `string` — URL override for the instance link or title.

- glyph (optional): `string` — FontAwesome icon class (without `fa-` prefix) shown alongside the instance title.

- size (optional, default: `'md'`): `'sm' | 'md' | 'lg' | 'xl'` — Visual card size in the portal designer UI only. Does not affect the rendered page layout.

- color (optional, default: `'default'`): `'default' | 'primary' | 'success' | 'info' | 'warning' | 'danger'` — Bootstrap contextual color for the instance panel header.

- cssClass (optional): `string` — Additional CSS class applied to the instance wrapper element.

- active (optional, default: true): `boolean` — Set to `false` to hide the instance without deleting it.

- order (optional): `number` — Sort order within the column. Defaults to position index + 1.

- roles (optional): `(string | Role | Record<'sys_user_role'>)[]` — Hides this instance for users without any of the listed roles. Does not return a 403 — other instances on the page remain visible.

- asyncLoad (optional, default: false): `boolean` — Defers widget server-side rendering until the async trigger fires. Use with `asyncLoadTrigger`.

- asyncLoadTrigger (optional, default: `'viewport'`): `'viewport' | 'parallel'` — `'viewport'` loads when scrolled into view; `'parallel'` loads immediately in parallel with other page content.

- asyncLoadDeviceType (optional): `string` — Comma-separated device types to apply async loading to (e.g. `'desktop,tablet,mobile'`). Empty = all devices.

- preservePlaceholderSize (optional, default: false): `boolean` — Keeps the placeholder element's height while async content loads, preventing layout shift. Only relevant when `asyncLoad` is `true`.

- placeholderTemplate (optional): `string` — AngularJS HTML shown while the widget loads asynchronously.

- advancedPlaceholderDimensions (optional, default: false): `boolean` — Enables explicit width/height control via `placeholderDimensions`.

- placeholderDimensions (optional): `JsonSerializable` — Explicit dimensions for the async placeholder per device type (e.g. `{ mobile: { height: '250px', width: '100%' } }`). Only used when `advancedPlaceholderDimensions` is `true`.

- placeholderConfigurationScript (optional): `string` — Server-side script that returns placeholder dimension config dynamically. Evaluated on page load before the widget is asynchronously loaded.

- 
css (optional): `string`
Page-scoped SCSS or CSS applied only when this page is rendered.

- 
draft (optional, default: false): `boolean`
Marks the page as a draft. Draft pages are visible only to portal designers
and admins, not to regular users.

- 
dynamicTitleStructure (optional): `string`
Template string used to build a dynamic page `<title>` tag.
Supports portal variable substitution.

- 
humanReadableUrlStructure (optional): `string`
Friendly URL path pattern for the page, enabling human-readable URLs.
Use `{variable}` placeholders to capture path segments as URL parameters.
Must contain exactly one `/` separator.

- 
internal (optional, default: false): `boolean`
Marks the page as an internal platform page (not user-created).
Internal pages are hidden from the page picker in the portal designer.

- 
omitWatcher (optional, default: false): `boolean`
Disables the AngularJS `$watch` listener for this page, improving
performance for static or data-light pages.

- 
public (optional, default: false): `boolean`
Makes the page accessible to unauthenticated users without login.

- 
roles (optional): `(string | Role | Record<'sys_user_role'>)[]`
Restricts access to users with at least one of the specified roles.
If empty, the page is accessible to all authenticated users (or all users if `public` is true).

- 
seoScript (optional): `string | ScriptIncludeOptions | Record<'sys_script_include'>`
Server-side script (`sys_script_include`) that returns a dynamic page title
and meta description for SEO purposes. Only used when `useSeoScript` is `true`.

- 
shortDescription (optional): `string`
Brief admin-visible description of the page's purpose. Not displayed to end users.

- 
title (optional): `string`
Page title displayed in the browser tab.

- 
useSeoScript (optional, default: false): `boolean`
Enables dynamic `<title>` and meta tag generation via `seoScript`.

## Examples

### sp-page-basic

```
// Source: packages/api/tests/service-portal/page-plugin.test.ts

import { SPPage } from '@servicenow/sdk/core'

export const BasicPageExample = SPPage({
    title: 'My Simple Page',
    pageId: 'simple_page',
})
```

### sp-page-draft

```
// Source: packages/api/tests/service-portal/page-plugin.test.ts

import { SPPage } from '@servicenow/sdk/core'

export const PageWithDraftExample = SPPage({
    title: 'My Complete Page',
    pageId: 'complete_page',
    category: 'custom',
    draft: true,
    dynamicTitleStructure: 'Dynamic Title',
    shortDescription: 'This is a test page',
})
```

### sp-page-with-containers

```
// Source: packages/api/tests/service-portal/page-plugin.test.ts

import { SPPage } from '@servicenow/sdk/core'

export const PageWithContainersExample = SPPage({
    title: 'Hierarchical Page',
    pageId: 'hierarchical_page',
    containers: [
        {
            $id: Now.ID['main-container'],
            name: 'Main Container',
            title: 'Main Container Title',
            backgroundColor: '#ffffff',
            backgroundImage: 'bg-image.jpg',
            cssClass: 'main-container',
            parentClass: 'sp-hero-section',
            subheader: true,
            bootstrapAlt: true,
            semanticTag: 'main',
            order: 1,
            rows: [
                {
                    $id: Now.ID['main-row'],
                    cssClass: 'main-row',
                    semanticTag: 'main',
                    order: 1,
                    columns: [
                        {
                            $id: Now.ID['main-column'],
                            size: 8,
                            sizeSm: 6,
                            sizeLg: 10,
                            sizeXs: 12,
                            cssClass: 'main-column',
                            semanticTag: 'main',
                            order: 1,
                            instances: [
                                {
                                    $id: Now.ID['widget-instance'],
                                    title: 'Widget Instance',
                                    id: 'widget-instance-1',
                                    widget: '7690d6d2ff5d3610166dffffffffff5d',
                                    widgetParameters: { param1: 'value1' },
                                    css: '.widget { margin: 10px; }',
                                    url: '/widget-url',
                                    glyph: 'home',
                                    size: 'lg',
                                    color: 'primary',
                                    cssClass: 'widget-class',
                                    active: true,
                                    order: 1,
                                    roles: ['admin'],
                                    shortDescription: 'Widget description',
                                },
                            ],
                        },
                        {
                            $id: Now.ID['secondary-column'],
                            size: 4,
                            order: 2,
                            cssClass: '',
                            instances: [],
                        },
                    ],
                },
            ],
        },
    ],
})
```

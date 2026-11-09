Version: 4.14.0

# Service Portal Fluent Components Guide

Reference for SPTheme, SPHeaderFooter, SPMenu, SPAngularProvider, and SPWidgetDependency. These are the supporting components that surround a widget — they control visual identity, navigation, shared AngularJS logic, and external library loading. All five map to distinct ServiceNow tables. You MUST check for reusable OOTB records before creating custom ones.

Sys_id note (applies to the whole document): Every sys_id referenced anywhere in this guide (themes, headers/footers, menu widgets, etc.) is from a baseline ServiceNow instance and may differ by release or per-instance customization. Always verify against your target instance before use.

## SPTheme — Visual Identity (sp_theme)

`SPTheme` controls the look of the entire portal. It compiles SCSS variables once for the portal and makes them available to every widget, header, and footer via Bootstrap 3's variable system.

### OOTB Themes — Use First

Look up the sys_id using `now-sdk query` — do not hardcode sys_ids. They differ by release and instance customization.

For full query syntax and options, see query-guide.md.

```
# Look up an OOTB theme by name
now-sdk query sp_theme -q 'name=Coral' -f 'sys_id,name' -o json

# Common OOTB themes to query:
now-sdk query sp_theme -q 'name=Coral' -f 'sys_id,name' -o json              # Default recommended theme
now-sdk query sp_theme -q 'name=La Jolla' -f 'sys_id,name' -o json           # Modern flat design
now-sdk query sp_theme -q 'name=Stock' -f 'sys_id,name' -o json              # Baseline plain theme
now-sdk query sp_theme -q 'name=Stock High Contrast' -f 'sys_id,name' -o json # Accessibility-compliant
now-sdk query sp_theme -q 'name=EC Theme' -f 'sys_id,name' -o json           # Employee Center default
```

To use an OOTB theme, pass the sys_id string directly to `ServicePortal.theme`. MUST NOT create an `SPTheme` wrapper around an OOTB record.

```
// Using an OOTB theme — pass sys_id string
export const myPortal = ServicePortal({
    theme: '281507c44317d210ca4c1f425db8f2fd', // Coral
    ...
});
```

### Custom SPTheme

Create a custom `SPTheme` only when OOTB cannot satisfy branding requirements.

```
import '@servicenow/sdk/global';
import { SPTheme, JsInclude, CssInclude } from '@servicenow/sdk/core';
import { portalHeader } from '../../sp-header-footer/portal-header/portal-header.now';
import { portalFooter } from '../../sp-header-footer/portal-footer/portal-footer.now';

// App scope: x_myco_itsm (example — use YOUR app scope from now.config.json)
export const customTheme = SPTheme({
    $id: Now.ID['x_myco_itsm_theme'],
    name: 'My Portal Theme',

    // header / footer — pass SPHeaderFooter object or OOTB sys_id string
    // OOTB Stock Header: 'bf5ec2f2cb10120000f8d856634c9c0c'
    // OOTB Sample Footer: 'feb4f763df121200ba13a4836bf26320'
    header: portalHeader,
    footer: portalFooter,

    fixedHeader: true,   // sticky navbar
    fixedFooter: true,   // sticky footer

    logo: '',            // sys_id of user_image OR Now.attach('./logo.png')
    logoAltText: 'My Portal',
    icon: '',            // browser favicon — sys_id of user_image

    turnOffScssCompilation: false,  // must be false when using $variables or sp-rgb()
    matchingNextExperienceTheme: '', // sys_id of sys_ux_theme for NX bridge (optional)

    // jsIncludes: JS loaded on EVERY page of this portal, before widget clientScripts
    jsIncludes: [
        {
            order: 100,
            include: JsInclude({
                $id: Now.ID['x_myco_itsm_theme_global_js'],
                name: 'Portal global script',
                url: 'https://cdn.example.com/analytics.min.js',
                // Alternative: sysUiScript: 'sys_id_of_sys_ui_script'
            })
        }
    ],

    // cssIncludes: CSS loaded on EVERY page of this portal, before widget CSS
    cssIncludes: [
        {
            order: 100,
            include: CssInclude({
                $id: Now.ID['x_myco_itsm_theme_global_css'],
                name: 'Portal global CSS',
                url: 'https://cdn.example.com/custom-icons.css',
                lazyLoad: false,    // false → injected at page load (avoids FOUC)
                // rtlCssUrl: 'https://cdn.example.com/custom-icons-rtl.css'
            })
        }
    ],

    customCss: `
$brand-primary: #0A2947 !default;
$body-bg:       #FDF6ED !default;
$text-color:    #0A2947 !default;
$link-color:    #4382DF !default;

$navbar-inverse-bg:               $brand-primary !default;
$navbar-inverse-link-color:       rgba(255,255,255,0.90) !default;
$navbar-inverse-link-hover-color: #FFFFFF !default;
$navbar-inverse-border:           darken($brand-primary, 5%) !default;
`,
});
```

### SPTheme Field Reference

| Field | Type | Notes |
| `header` | SPHeaderFooter | string | Required for menu display. OOTB: `'bf5ec2f2cb10120000f8d856634c9c0c'` . |
| `footer` | SPHeaderFooter | string | Optional. OOTB: `'feb4f763df121200ba13a4836bf26320'` . |
| `fixedHeader` | boolean | `true` → sticky navbar. Recommended default. |
| `fixedFooter` | boolean | `true` → sticky footer. |
| `logo` | string | sys_id of `user_image` record OR `Now.attach('./logo.png')` . |
| `icon` | string | Browser favicon. sys_id of `user_image` record. |
| `turnOffScssCompilation` | boolean | Must be `false` when `customCss` uses `$variables` . |
| `matchingNextExperienceTheme` | string | sys_id of `sys_ux_theme` for NX color bridge. Optional. |
| `jsIncludes` | array | `[{ order, include: JsInclude({...}) }]` — global JS per page. |
| `cssIncludes` | array | `[{ order, include: CssInclude({...}) }]` — global CSS per page. |
| `customCss` | string | SCSS variables compiled once for the entire portal. |

### customCss SCSS Variable Groups

All variables MUST end with `!default` to allow override.

DO NOT include in customCss:

| Pattern | Why |
| `body { padding-top: ... }` | Framework handles via `body.fixed-header` class |
| `.navbar-fixed-top { ... }` | Framework handles positioning |
| `position: fixed` on navbar | Conflicts with framework positioning |
| Raw selectors like `nav { ... }` | Use scoped classes instead |
| Raw hex colors without `sp-rgb()` | Breaks dark mode and UXF consistency |

### CRITICAL: Use `sp-rgb()` UXF Tokens

MANDATORY: All color variables MUST use `sp-rgb()` with UXF token and fallback.

```
// CORRECT — sp-rgb() with UXF token and fallback
$brand-primary: sp-rgb(--now-color--primary-1, #0080A3) !default;

// WRONG — raw hex values (breaks dark mode, UXF consistency)
$brand-primary: #1D4ED8 !default;  // ❌ MUST NOT use raw hex
```

For complete Coral theme SCSS variables, see service-portal-ootb-reference.md.

When user requests custom colors — map to UXF token with user's color as fallback:

```
// User requested: primary #1D4ED8 (blue)
$brand-primary: sp-rgb(--now-color--primary-1, #1D4ED8) !default;
```

### Spacing Scale

Use only these variables for margin/padding. MUST NOT use arbitrary pixel values.

| Variable | Value | Use Case |
| `$sp-space-1` | 4px | Icon gaps, badge padding |
| `$sp-space-2` | 8px | Input padding, label gaps |
| `$sp-space-3` | 12px | Button padding Y, tight sections |
| `$sp-space-4` | 16px | Base unit — form group gap |
| `$sp-space-5` | 24px | Card padding, section gap |
| `$sp-space-6` | 32px | Between major sections |
| `$sp-space-7` | 48px | Page top padding, empty states |
| `$sp-space-8` | 64px | Full-bleed sections |

### Typography Scale

Every `font-size` MUST use a theme variable — MUST NOT use raw pixel values.

This scale applies everywhere in the app — theme `customCss`, header/footer CSS, and every widget's `styles.css`. It is not a theme-only convention.

| Variable | Value | Use Case |
| `$sp-text-xs` | 12px | Badges, timestamps, captions |
| `$sp-text-sm` | 14px | Helper text, table metadata |
| `$sp-text-base` | 16px | Body, labels, table cells |
| `$sp-text-md` | 18px | Card titles, sub-headings |
| `$sp-text-lg` | 22px | Section headings |
| `$sp-text-xl` | 26px | Page title |
| `$sp-text-2xl` | 32px | Hero / banner headings |

MUST NOT set any `font-size` below `$sp-text-xs` (12px) anywhere, including badges, pills, status labels, and stat/counter captions. These small UI elements are the most common violators — it's tempting to shrink a badge or label below the scale's smallest tier "to make it fit," but text below 12px is not reliably readable. If a badge or label doesn't fit at 12px, resize the container instead of shrinking the text.

### Icon Size Scale

| Variable | Value | Use Case |
| `$sp-icon-xs` | 12px | Badge / chevron icons |
| `$sp-icon-sm` | 16px | Button / inline / alert icons |
| `$sp-icon-md` | 20px | Card / stat tile icons |
| `$sp-icon-lg` | 32px | Section / feature icons |
| `$sp-icon-xl` | 48px | Empty state / hero icons |

### Bootstrap 3 Grid Patterns

Service Portal uses Bootstrap 3's 12-column grid. Every column MUST include `col-xs-12` so it stacks correctly on mobile.

| Layout | Bootstrap Classes |
| Full width | `col-md-12` |
| Main + sidebar | `col-md-8` + `col-md-4` |
| Equal 2-column | `col-md-6 col-xs-12` × 2 |
| 3-column cards | `col-md-4 col-sm-6 col-xs-12` × 3 |
| 4-column stat tiles | `col-md-3 col-sm-6 col-xs-12` × 4 |

These map to the `size`, `sizeSm`, `sizeLg`, `sizeXs` fields on `SPColumn` in the page layout.

## SPHeaderFooter — Header and Footer (sp_header_footer)

`SPHeaderFooter` creates an `sp_header_footer` record, which extends `sp_widget`. It has all `SPWidget` fields plus one extra: `static`.

Headers and footers are wired to the portal via `SPTheme.header` and `SPTheme.footer`. The platform injects them at the top/bottom of every page that uses the theme.

OOTB Reference Records (Gold Standard):

Look up the sys_id using `now-sdk query` — do not hardcode sys_ids. They differ by release and instance customization.

```
# Look up OOTB header/footer by name
now-sdk query sp_header_footer -q 'name=Stock Header' -f 'sys_id,name' -o json   # Header — canonical reference
now-sdk query sp_header_footer -q 'name=Sample Footer' -f 'sys_id,name' -o json  # Footer
```

```
import '@servicenow/sdk/global';
import { SPHeaderFooter } from '@servicenow/sdk/core';

// App scope: x_myco_itsm (example — use YOUR app scope from now.config.json)
export const portalHeader = SPHeaderFooter({
    $id: Now.ID['x_myco_itsm_header'],
    name: 'My Portal Header',
    id: 'x_myco_itsm_header',

    // CRITICAL: static must be false when header is wired via theme
    // static: false → rendered because it is referenced by the theme (normal use case)
    // static: true  → rendered unconditionally on every page (rarely needed)
    static: false,  // MUST be false for theme-wired headers

    htmlTemplate: Now.include('./template.html'),
    clientScript: Now.include('./client_script.js'),
    serverScript: Now.include('./server_script.js'),
    customCss: Now.include('./styles.scss'),

    category: 'custom',
    description: 'Main portal header with navigation.',
});
```

### Header Template, Server Script, and CSS Patterns

CRITICAL: For exact OOTB Stock Header patterns and all mandatory rules, see service-portal-ootb-reference.md. That guide contains:

- Exact template, server script, and CSS to copy

- Critical Rules Summary table

- Prevention Checklist (MUST complete before creating any header/footer)

How fixed positioning works:

- `theme.fixedHeader = true` (maps to `navbar_fixed` field)

- Body gets class `fixed-header`

- CSS selector `body.fixed-header div.sp-page-root > header` applies sticky positioning

- MUST NOT add `navbar-fixed-top` class — it conflicts with framework positioning

### How SPMenu connects to the header

The menu is NOT directly injected into the header template. The platform wires them at runtime:

- `ServicePortal({ mainMenu: portalNavMenu })` stores the menu instance sys_id in `sp_portal.sp_rectangle_menu`.

- The header server script reads `$sp.getValue('sp_rectangle_menu')` to get the menu instance.

- `$sp.getWidgetFromInstance(menuId)` loads the menu widget and its items.

- The header template renders `<sp-widget widget="::data.menu">`.

If the header does not call `$sp.getValue('sp_rectangle_menu')`, the menu will not display even if `mainMenu` is set on the portal.

### Three requirements for menu display

All three MUST be set, or the menu will not appear:

- `ServicePortal.theme` → theme is set

- `SPTheme.header` → header is set on the theme

- `ServicePortal.mainMenu` → menu is set on the portal

### MANDATORY: Pre-Creation Checklist

BEFORE creating ANY custom header/footer, complete the Header/Footer Prevention Checklist in the OOTB Reference guide. Skipping any item causes silent failures.

## SPMenu — Navigation Menu (sp_instance_menu)

`SPMenu` creates an `sp_instance_menu` record and its `sp_instance_menu_item` children.

```
import '@servicenow/sdk/global';
import { SPMenu } from '@servicenow/sdk/core';
import { homePage } from '../../sp-page/home/home.now';

// App scope: x_myco_itsm (example — use YOUR app scope from now.config.json)
export const portalNavMenu = SPMenu({
    $id: Now.ID['x_myco_itsm_menu'],
    title: 'Main Menu',

    // widget: sys_id of the menu rendering widget (OOTB Header Menu widget)
    // MUST use an OOTB menu widget — MUST NOT recreate menu rendering logic.
    // OOTB Header Menu: '5ef595c1cb12020000f8d856634c9c6e'
    widget: '5ef595c1cb12020000f8d856634c9c6e',

    items: [
        {
            $id: Now.ID['x_myco_itsm_menu_item_home'],
            type: 'page',
            label: 'Home',
            page: homePage,           // app-owned page — pass imported SPPage object
            glyph: 'home',
            order: 100,
            active: true,
        },
        {
            $id: Now.ID['x_myco_itsm_menu_item_kb'],
            type: 'kb',          // Knowledge Base home
            label: 'Knowledge',
            glyph: 'book',
            order: 200,
        },
        {
            $id: Now.ID['x_myco_itsm_menu_item_services'],
            type: 'sc',          // Service Catalog home
            label: 'Services',
            glyph: 'briefcase',
            order: 300,
            childItems: [
                {
                    $id: Now.ID['x_myco_itsm_menu_item_it'],
                    type: 'sc_category',
                    label: 'IT Services',
                    scCategory: '<sc_category_sys_id>',
                    page: '9f12251147132100ba13a5554ee490f4', // OOTB Catalog Item page sys_id
                    order: 100,
                }
            ]
        },
        {
            $id: Now.ID['x_myco_itsm_menu_item_external'],
            type: 'url',
            label: 'Docs',
            url: 'https://docs.servicenow.com',
            urlTarget: '_blank',
            glyph: 'new-window',
            order: 400,
        }
    ]
});
```

### Menu Item Types

Critical: For `type: 'page'` items, `page` MUST be set. If `page` is omitted or null, the menu link will silently render with no destination and clicking it will fall back to the portal's default home page — which is usually the OOTB home, not the page you built. You MUST pass either the imported SPPage object (for pages you own) or a 32-char sys_id string (for OOTB pages). A page `id` string like `'my-portal-home'` is NOT valid — it will be ignored.

| Type | Required extra fields | Description |
| `page` | `page` — mandatory : SPPage object for app-owned pages; 32-char sys_id string for OOTB pages | Links to a Service Portal page. Omitting `page` causes the link to silently fail. |
| `url` | `url` , optionally `urlTarget` | External or internal URL |
| `sc` | none | Service Catalog home |
| `sc_category` | `scCategory` , `page` | Service Catalog category page |
| `sc_cat_item` | `catItem` , `page` | Specific catalog item |
| `kb` | none | Knowledge Base home |
| `kb_topic` | `kbTopic` , `page` | Knowledge topic |
| `kb_article` | `kbArticle` , `page` | Specific knowledge article |
| `kb_category` | `kbCategory` , `page` | Knowledge category |
| `filtered` | `table` , `filter` | Dynamic content based on filter |
| `scripted` | `script` | Server-side generated items |

There is no `divider`/separator item type. `sp_instance_menu_item` has no native visual-separator concept. If the user asks for a "visual separator between sections" in the menu, achieve it one of two ways:

- Grouping (preferred): use `childItems` to nest related items under a parent (e.g., a "Resources" dropdown) — the dropdown boundary itself reads as a visual break between groups, with no extra CSS needed.

- CSS border: add a rule to the theme's `customCss` targeting the specific item's position, e.g. `.navbar-nav > li:nth-child(3) { border-left: 1px solid $sp-navbar-divider-color; }` — fragile, since it depends on item order staying fixed; prefer grouping via `childItems` when the choice is available.

### OOTB Menu Widgets

You MUST use one of these OOTB menu widgets. MUST NOT recreate menu rendering logic.

Look up the sys_id using `now-sdk query` — do not hardcode sys_ids. They differ by release and instance customization.

For full query syntax and options, see query-guide.md.

```
# Look up OOTB menu widgets by name
now-sdk query sp_widget -q 'name=Header Menu' -f 'sys_id,name,id' -o json       # Standard top navigation
now-sdk query sp_widget -q 'name=Icon Menu List' -f 'sys_id,name,id' -o json    # Menu with icons per item
now-sdk query sp_widget -q 'name=Single Icon Menu' -f 'sys_id,name,id' -o json  # Compact icon dropdown
```

Use the `sys_id` from the query result in your `SPMenu.widget` field.

## SPAngularProvider — Shared AngularJS Logic (sp_angular_provider)

`SPAngularProvider` creates an `sp_angular_provider` record. It registers a factory, service, or directive that widget client scripts can inject as a dependency.

Providers are linked to a widget via `SPWidget.angularProviders: [provider1, provider2]`. The platform loads them before the widget controller runs.

### Provider Types

| Type | Script returns | When to use |
| `directive` | Directive Definition Object (DDO) | Custom HTML attributes or elements |
| `service` | Object with methods (plain object) | Shared logic, utilities, state |
| `factory` | Object or primitive | Configurable objects, API wrappers |

### Provider Script Rules — Critical

The script file MUST contain a plain named function matching the `name` field exactly. MUST NOT use `api.value = ...`, `api.controller = ...`, or any `api.*` pattern inside a provider script. Those patterns are only for widget client scripts.

```
// CORRECT — plain named function
function myService() {
    var svc = {};
    svc.doSomething = function (value) {
        return value.trim();
    };
    return svc;
}

// WRONG — api.* pattern in a provider script causes ReferenceError
api.value = function myService() { ... };  // ← MUST NOT do this in a provider
```

### Directive Example

```
// sn-focus-input.now.ts
export const snFocusInputDirective = SPAngularProvider({
    $id: Now.ID['sn-focus-input-directive'],
    name: 'snFocusInput',    // camelCase name → kebab-case attribute: sn-focus-input
    type: 'directive',
    script: Now.include('./sn-focus-input.js'),
});
```

```
// sn-focus-input.js — plain named function, no api.*
function snFocusInput($timeout) {
    return {
        restrict: 'A',
        link: function (scope, element, attrs) {
            scope.$watch(attrs.snFocusInput, function (val) {
                if (val) {
                    $timeout(function () { element[0].focus(); }, 50);
                }
            });
        },
    };
}
```

Usage in template:

```
<input type="text" sn-focus-input="c.shouldFocus" ng-model="c.form.field" />
```

### Service Example

```
// form-utils-service.now.ts
export const formUtilsServiceProvider = SPAngularProvider({
    $id: Now.ID['form-utils-service'],
    name: 'formUtilsService',   // inject in client script as: formUtilsService
    type: 'service',
    script: Now.include('./form-utils-service.js'),
    // requires: load order dependency — platform ensures listed providers are
    // registered before this one. Pass SPAngularProvider objects.
    requires: [snFocusInputDirective],
});
```

```
// form-utils-service.js — plain named function, returns object
function formUtilsService() {
    var svc = {};
    svc.isValidEmail = function (email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email || '');
    };
    svc.trimAll = function (obj) {
        var result = {};
        Object.keys(obj).forEach(function (k) {
            result[k] = typeof obj[k] === 'string' ? obj[k].trim() : obj[k];
        });
        return result;
    };
    return svc;
}
```

Inject in the widget client script by adding the provider name as a function parameter:

```
// client_script.js — inject formUtilsService by name
api.controller = function (formUtilsService) {
    var c = this;
    c.submit = function () {
        var cleaned = formUtilsService.trimAll(c.form);
        if (!formUtilsService.isValidEmail(cleaned.email)) {
            c.serverErrors = ['Invalid email address.'];
            return;
        }
        // ...
    };
};
```

### Factory Example

```
export const userContextFactory = SPAngularProvider({
    $id: Now.ID['user-context-factory'],
    name: 'userContextFactory',
    type: 'factory',
    script: Now.include('./user-context-factory.js'),
});
```

```
// user-context-factory.js
function userContextFactory($http) {
    return {
        getCurrentUser: function () {
            return $http.get('/api/now/table/sys_user', {
                params: {
                    sysparm_query: 'user_name=javascript:gs.getUserName()',
                    sysparm_limit: 1
                }
            });
        }
    };
}
```

### `requires` — Load Order

`requires` ensures that listed providers are registered before this provider. Pass the imported SPAngularProvider objects (not name strings).

```
export const myService = SPAngularProvider({
    name: 'myService',
    type: 'service',
    script: Now.include('./my-service.js'),
    requires: [snFocusInputDirective, userContextFactory],
});
```

### Linking Providers to a Widget

```
export const myWidget = SPWidget({
    $id: Now.ID['my-widget'],
    name: 'My Widget',
    angularProviders: [snFocusInputDirective, formUtilsServiceProvider],
    clientScript: Now.include('./client_script.js'),
    // ...
});
```

## SPWidgetDependency — External Libraries (sp_dependency)

`SPWidgetDependency` creates an `sp_dependency` record that bundles one or more JS and CSS files. Widgets declare dependencies via `SPWidget.dependencies: [dep1, dep2]`.

MUST NOT re-add these globally bundled libraries — they are already in Service Portal and adding them again causes version conflicts:

- jQuery

- AngularJS

- Bootstrap 3 CSS and JS

- Bootstrap 3 Glyphicons

A `JsInclude` needs exactly one source: `url` for an external file, or `sysUiScript` for a `sys_ui_script` record. Same for `CssInclude`: `url` or `spCss`. Do not set both, and do not set neither.

```
import '@servicenow/sdk/global';
import { SPWidgetDependency, JsInclude, CssInclude } from '@servicenow/sdk/core';

export const chartJsDependency = SPWidgetDependency({
    $id: Now.ID['chartjs-dependency'],
    name: 'Chart.js 4.4.0',

    // jsIncludes: ordered JS files for this dependency
    jsIncludes: [
        {
            order: 100,
            include: JsInclude({
                $id: Now.ID['chartjs-js'],
                name: 'chart.js 4.4.0',
                url: 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js',
                // Alternative: sysUiScript: 'sys_id_of_sys_ui_script'
            })
        }
    ],

    // cssIncludes: ordered CSS files for this dependency
    cssIncludes: [
        {
            order: 100,
            include: CssInclude({
                $id: Now.ID['chartjs-css'],
                name: 'Chart.js CSS overrides',
                url: 'https://cdn.example.com/chart-overrides.css',
                lazyLoad: false,     // false → injected at page load (avoids FOUC)
                // rtlCssUrl: 'https://cdn.example.com/chart-rtl.css'
            })
        }
    ],

    // angularModuleName: if this library ships its own Angular module,
    // declare it here so widgets can list it in their ng-dependencies.
    // Leave empty for global libraries like Chart.js.
    // angularModuleName: 'myChartModule',

    // includeOnPageLoad: true → loaded on every page in portalsForPageLoad
    // without any widget needing to declare it. Use only for truly global dependencies.
    // false (default) → loaded only when a widget with this dependency is on the page.
    includeOnPageLoad: false,

    // portalsForPageLoad: restrict auto-loading to these portals.
    // Empty array = all portals. Pass sp_portal sys_id strings or portal objects.
    portalsForPageLoad: [],
});
```

Linking to a widget:

```
export const myChartWidget = SPWidget({
    $id: Now.ID['my-chart-widget'],
    name: 'My Chart Widget',
    dependencies: [chartJsDependency],
    // ...
});
```

### SPWidgetDependency Field Reference

| Field | Type | Notes |
| `jsIncludes` | array | `[{ order, include: JsInclude({...}) }]` . Lower order loads first. |
| `cssIncludes` | array | `[{ order, include: CssInclude({...}) }]` . Lower order loads first. |
| `angularModuleName` | string | Angular module name if the library exposes one. Leave empty for globals. |
| `includeOnPageLoad` | boolean | `true` → auto-load on every page without widget declaration. Default: `false` . |
| `portalsForPageLoad` | array | Restrict auto-load to these portals. Empty = all portals. |

### JsInclude and CssInclude

`JsInclude` creates an `sp_js_include` record:

```
JsInclude({
    $id: Now.ID['my-js'],
    name: 'My JS',
    url: 'https://cdn.example.com/lib.min.js',
    // Alternative: sysUiScript: 'sys_id_of_sys_ui_script'
})
```

`CssInclude` creates an `sp_css_include` record:

```
CssInclude({
    $id: Now.ID['my-css'],
    name: 'My CSS',
    url: 'https://cdn.example.com/lib.min.css',
    lazyLoad: false,          // true → inject only when widget renders
    // rtlCssUrl: 'https://cdn.example.com/lib-rtl.min.css'
    // Alternative: spCss: 'sys_id_of_sp_css_record'
})
```

### Dependency Loading Order

Lower `order` values load first. You MUST ensure base libraries load before plugins:

```
jsIncludes: [
    { order: 100, include: JsInclude({ name: 'Moment.js', url: '...' }) },    // base
    { order: 200, include: JsInclude({ name: 'Moment Timezone', url: '...' }) }, // plugin
]
```

## API to Table Mapping

| Fluent API | ServiceNow Table | Notes |
| `ServicePortal()` | `sp_portal` | One entry point per portal |
| `SPPage()` | `sp_page` | Contains containers → rows → columns → instances |
| `SPWidget()` | `sp_widget` | Widget definition; scripts via `Now.include()` |
| `SPTheme()` | `sp_theme` | SCSS variables, header, footer, global JS/CSS |
| `SPHeaderFooter()` | `sp_header_footer` | Extends `sp_widget` ; has extra `static` field |
| `SPMenu()` | `sp_instance_menu` | Navigation menu + items |
| `SPAngularProvider()` | `sp_angular_provider` | AngularJS factory / service / directive |
| `SPWidgetDependency()` | `sp_dependency` | External JS/CSS library bundle |
| `JsInclude()` | `sp_js_include` | Single JS file reference |
| `CssInclude()` | `sp_css_include` | Single CSS file reference |
| `SPPageRouteMap()` | `sp_page_route_map` | Page-level navigation redirects |

## Related Guides

This guide covers themes, headers/footers, menus, Angular providers, and widget dependencies. Load the guides below when the task also involves these areas:

| When you need to… | Load this guide |
| Create the portal entry point, pages, and widgets | `service-portal-guide` |
| Write server scripts, client scripts, or HTML templates | `service-portal-guide` |
| Set up page redirects or understand admin role bypass | `service-portal-advanced-guide` |
| Debug widgetParameters or theme issues | `service-portal-advanced-guide` |
| Find OOTB widget or page sys_ids | `service-portal-advanced-guide` |
| Copy exact OOTB Stock Header template/script/CSS | `service-portal-ootb-reference` |
| Copy exact Coral theme SCSS variables | `service-portal-ootb-reference` |

For a complete portal build, load these guides:

- `service-portal-guide` — portal, pages, widgets, scripts

- `service-portal-components-guide` — theme, header/footer, menu, providers, dependencies (this file)

- `service-portal-advanced-guide` — route maps, constraints, troubleshooting

- `service-portal-ootb-reference` — exact OOTB patterns (Stock Header, Coral theme) — load when creating custom headers/themes

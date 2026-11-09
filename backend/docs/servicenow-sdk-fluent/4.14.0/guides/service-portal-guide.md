Version: 4.14.0

# Service Portal

Guide for building ServiceNow Service Portal experiences using the Fluent API. Service Portal is a portal framework for building user-facing self-service experiences using AngularJS and Bootstrap 3. This guide covers core portal concepts: portals, pages, widgets, and themes.

Sys_id note (applies to the whole document): Every sys_id referenced anywhere in this guide (themes, pages, catalog/KB records, etc.) is from a baseline ServiceNow instance and may differ by release or per-instance customization. Always verify against your target instance before use.

Example code is illustrative, not literal (applies to the whole document). Table names (`incident`), field names (`short_description`, `state`), identifiers (`x_myco_itsm_widget`), and CSS classes shown in code examples are placeholders demonstrating a pattern — not requirements to reuse those exact names. This guide is used to build portals for many different use cases (HR requests, asset tracking, approvals, facilities, custom business objects, etc.), not just incident-based ones. Before copying an example, substitute every table/field/identifier for whatever the actual portal requirement calls for — do not carry over `incident`, `state`, or any other example-specific name unless that is genuinely what the portal needs. All unique identifiers MUST be prefixed with your app scope (e.g., `x_myco_itsm_`) — see Naming Convention.

## When to Use

- Portal for external users (employees, customers, members, partners, vendors)

- Self-service experiences where users submit requests, view status, access knowledge

- Branded portal with custom themes, logos, headers, footers

- Portal with multiple pages and navigation menus

- Interactive widgets with client-server communication

## When NOT to Use

- Internal admin tools — use `ui-page-guide` (React-based UI Pages)

- Next Experience / UI Builder — different framework (no AngularJS)

- Backend scripts — business rules, script includes, scheduled jobs

- Flow Designer — no portal component needed

Key differentiator: Service Portal = external self-service users. UI Page = internal platform users.

## Critical Implementation Notes — Uniqueness Constraints

The following fields have enforced unique constraints at the database level. If you attempt to create a record with a duplicate value, the deploy will fail.

MANDATORY:

You MUST query the instance to verify uniqueness BEFORE generating any Fluent code. Failure to do so will cause deploy failures.

### Required Pre-flight Checks

| Component | Field | Table | Query | Scope |
| ServicePortal | `urlSuffix` | `sp_portal` | `url_suffix=<value>` | Instance-wide |
| SPPage | `pageId` | `sp_page` | `id=<value>` | Instance-wide (all portals) |
| SPWidget | `id` | `sp_widget` | `id=<value>` | Instance-wide |
| SPWidgetDependency | `name` | `sp_dependency` | `name=<value>` | Instance-wide |
| SPWidgetDependency | `module` | `sp_dependency` | `module=<value>` | Instance-wide |
| SPInstance | `$id` | `sp_instance` | `id=<value>` | Instance-wide |
| SPNgTemplate | `id` | `sp_ng_template` | `id=<value>` | Instance-wide |

### Pre-flight Check Procedure

CRITICAL: Before writing ANY Fluent code, run these queries. If a collision is found, auto-generate a unique alternative — do NOT ask the user or stop.

Use `now-sdk query` (see query-guide.md) to run read-only queries against the authenticated instance.

```
# App scope: x_myco_itsm (example — use YOUR app scope from now.config.json)

# 1. Check urlSuffix is unique (REQUIRED for ServicePortal)
now-sdk query sp_portal -q 'url_suffix=x_myco_itsm' -f 'sys_id' --limit 1 -o json
# If a record is returned → AUTO-MODIFY: append timestamp or counter (e.g., x_myco_itsm_v2, x_myco_itsm_1719849600)

# 2. Check pageId is unique (REQUIRED for each SPPage)
now-sdk query sp_page -q 'id=x_myco_itsm_home' -f 'sys_id' --limit 1 -o json
# If a record is returned → AUTO-MODIFY: append suffix (e.g., x_myco_itsm_home_v2)

# 3. Check widget id is unique (REQUIRED for each SPWidget)
now-sdk query sp_widget -q 'id=x_myco_itsm_hero_widget' -f 'sys_id' --limit 1 -o json
# If a record is returned → AUTO-MODIFY: append suffix (e.g., x_myco_itsm_hero_widget_v2)

# 4. Check dependency name is unique (REQUIRED for each SPWidgetDependency)
now-sdk query sp_dependency -q 'name=x_myco_itsm_utils' -f 'sys_id' --limit 1 -o json
# If a record is returned → AUTO-MODIFY: append suffix (e.g., x_myco_itsm_utils_v2)
```

Auto-Modification Rules:

- First attempt: append `_v2` to the identifier

- If `_v2` exists: increment to `_v3`, `_v4`, etc.

- Alternative: append Unix timestamp (e.g., `_1719849600`)

- MUST inform the user what modification was made in the response

- Update ALL references to the modified identifier throughout the code

### Naming Convention — App Scope Prefix (MANDATORY)

CRITICAL: You MUST prefix ALL unique identifiers with the application scope name. This is not optional — it is a mandatory requirement to prevent collisions and ensure traceability.

Rule: Every `urlSuffix`, `pageId`, `widget.id`, `SPInstance.$id`, `SPWidgetDependency.name`, `SPWidgetDependency.module`, and `SPNgTemplate.id` MUST start with the app scope (e.g., `x_myco_myapp_`).

| Bad | Good (with app scope `x_myco_myapp` ) |
| `home` | `x_myco_myapp_home` |
| `hero-widget` | `x_myco_myapp_hero_widget` |
| `esc` | `x_myco_myapp_esc` |
| `utils` | `x_myco_myapp_utils` |
| `support_portal` | `x_myco_myapp_support_portal` |

How to find your app scope: The app scope is defined in your scoped application record (`sys_scope`). It typically follows the pattern `x_<vendor>_<app>` (e.g., `x_abc_hr`, `x_myco_itsm`). You can also find it in your `now.config.json` under the `scope` field.

Why this matters:

- Prevents collisions with OOTB components and other scoped apps

- Makes it immediately clear which app owns each component

- Simplifies debugging and maintenance

- Required for enterprise deployments with multiple teams

### Fields WITHOUT Unique Constraints (duplicates allowed)

These fields do NOT require pre-flight checks — duplicates are allowed:

- `sp_theme.name`

- `sp_instance_menu.title`

- `sp_header_footer.name`

- `sp_angular_provider.name`

- `sp_css_include.name`

- `sp_js_include.name`

### Query Help

For `now-sdk query` syntax, output format, and error handling, see query-guide.md.

## Implementation Workflow

Follow this order for every portal build. Dependencies MUST exist before consumers:

- Understand requirements — identify which components are needed and their relationships

- Check OOTB reusability — check OOTB widgets, themes, and pages before creating any custom component

- Verify uniqueness — run pre-flight checks (see Critical Implementation Notes above). If any query returns a record, choose a different value BEFORE proceeding.

- Create bottom-up:

- SPWidgetDependency (external libraries)

- SPAngularProvider (shared AngularJS logic)

- SPWidget (widget definitions)

- SPHeaderFooter (custom header/footer, if needed)

- SPTheme (links header + footer + CSS)

- SPMenu (navigation items)

- SPPage (layout + widget instances)

- ServicePortal (ties everything together)

- SPPageRouteMap (redirect rules, standalone)

- Generate code — use dedicated Fluent API constructors, include all required fields, no placeholders

- Verify — confirm portal loads at `https://<instance>.service-now.com/<urlSuffix>?id=<homePage.pageId>`. If the home page looks wrong (plain search box with no branding), it means `homePage` was not wired correctly — check that `homePage` is set to your imported SPPage object, not a page id string.

- Preview — This step is MANDATORY. After every successful deploy, you MUST preview the portal in the studio/ide and provide the user with the exact clickable preview URL constructed from the values you used (`<instance>` is the deploy target origin, which `now-sdk deploy` prints on success):

- Portal home (open this immediately): `<instance>/<urlSuffix>?id=<homePage.pageId>`
Example: for instance `https://abc.service-now.com`, `urlSuffix: 'x_abc_hr'`, and `pageId: 'x_abc_hr_home'`, the preview URL is `https://abc.service-now.com/x_abc_hr?id=x_abc_hr_home`.
MUST NOT omit this step. The user cannot find the portal without these URLs.

## Decision Trees

### Portal

```
"Create or update a portal"
├── Existing portal?
│   ├── YES → Query sp_portal, update only changed fields
│   └── NO  → Use ServicePortal() to create new
├── Theme?
│   ├── No custom branding needed → Pass OOTB theme sys_id (Coral first)
│   └── Custom branding required → Create SPTheme()
└── Navigation menu?
    ├── YES → Create SPMenu() + ensure theme.header is set
    └── NO  → Skip
```

### Widget

```
"Create or update a widget"
├── Existing OOTB widget satisfies the need?
│   ├── YES → Reference by sys_id, MUST NOT recreate
│   └── NO  → Create new SPWidget() with Now.include() files
├── Needs external libraries (Chart.js, Select2, etc.)?
│   ├── YES → SPWidgetDependency() + link via widget.dependencies
│   └── NO  → Skip
└── Needs shared AngularJS services or directives?
    ├── YES → SPAngularProvider() + link via widget.angularProviders
    └── NO  → Skip
```

### Theme

```
"Create or update a theme"
├── Portal already has a theme set?
│   ├── YES → Use existing theme. Only update customCss if branding change is explicit
│   └── NO  → Check OOTB themes (Coral first, La Jolla second)
└── OOTB theme satisfies branding?
    ├── YES → Pass OOTB theme sys_id to ServicePortal.theme
    └── NO  → Create SPTheme() with customCss SCSS variables
```

## OOTB First — Critical Rule

MANDATORY: Before creating ANY portal component, check if an OOTB equivalent exists. Only create custom components when explicitly requested or when OOTB cannot satisfy the requirement.

### Decision Matrix

| Component | Default Action | Create Custom Only When |
| Theme | Use OOTB Coral | User explicitly requests custom branding/colors |
| Header | Use OOTB Stock Header | User explicitly requests custom header layout |
| Footer | Use OOTB Sample Footer or none | User explicitly requests custom footer |
| Widget | Search OOTB widgets first | No OOTB widget matches the functionality |
| Page | Search OOTB pages first | Custom layout or widget arrangement needed |

### OOTB Reference Records (Global Scope — Cross-Scope Accessible)

| Component | Reference Location |
| Themes | service-portal-components-guide.md — Coral (default), La Jolla, Stock, High Contrast, EC Theme |
| Headers/Footers | service-portal-components-guide.md — Stock Header, Sample Footer |
| Widgets | service-portal-advanced-guide.md — Data Table, Form, Simple List, etc. |
| Pages | service-portal-advanced-guide.md — form, list, ticket, login, 404, etc. |

Quick reference (default choices):

- Theme: Coral `281507c44317d210ca4c1f425db8f2fd`

- Header: Stock Header `bf5ec2f2cb10120000f8d856634c9c0c`

### MANDATORY: Verify OOTB sys_ids Against Target Instance

CRITICAL: Before using ANY OOTB sys_id in Fluent code, you MUST query the target instance to verify the sys_id exists and maps to the expected component. sys_ids can differ across ServiceNow releases, instance configurations, or plugin activations.

Verification procedure:

```
# REQUIRED: Query the instance to verify each OOTB sys_id before use
now-sdk query sp_theme -q 'sys_id=281507c44317d210ca4c1f425db8f2fd' -f 'sys_id,name' --limit 1 -o json
now-sdk query sp_header_footer -q 'sys_id=bf5ec2f2cb10120000f8d856634c9c0c' -f 'sys_id,name' --limit 1 -o json
now-sdk query sp_widget -q 'sys_id=<widget_sys_id>' -f 'sys_id,id,name' --limit 1 -o json
now-sdk query sp_page -q 'sys_id=<page_sys_id>' -f 'sys_id,id,title' --limit 1 -o json
```

If verification fails (0 records returned):

- Query by name instead: `now-sdk query sp_theme -q 'nameLIKECoral' -f 'sys_id,name' --limit 5 -o json`

- Use the sys_id from the query result

- Inform the user: "The documented sys_id `<old_id>` was not found. Using `<new_id>` from your instance."

MUST NOT skip this step. Using an invalid sys_id causes silent failures — the portal deploys but references point to non-existent records.

### Pre-Build OOTB Check Procedure

REQUIRED: Before writing any Fluent code, run these queries to find reusable OOTB components:

```
# 1. Check for OOTB widgets that match the requirement
now-sdk query sp_widget -q 'nameLIKE<keyword>^sys_scope=global' -f 'sys_id,id,name' --limit 10 -o json

# 2. Check for OOTB pages that match the requirement
now-sdk query sp_page -q 'titleLIKE<keyword>^sys_scope=global' -f 'sys_id,id,title' --limit 10 -o json

# 3. List available OOTB themes
now-sdk query sp_theme -q 'sys_scope=global' -f 'sys_id,name' --limit 10 -o json
```

### Cross-Scope Access Rules

OOTB components in global scope can be referenced by any scoped application:

```
// CORRECT — Reference OOTB by sys_id string (cross-scope safe)
export const myPortal = ServicePortal({
    theme: '281507c44317d210ca4c1f425db8f2fd',  // OOTB Coral theme
    // ...
});

export const myPage = SPPage({
    containers: [{
        instances: [{
            widget: '5b255672cb03020000f8d856634c9c28',  // OOTB Simple List widget
        }]
    }]
});
```

```
// WRONG — MUST NOT create Fluent wrappers around OOTB records
export const coralTheme = SPTheme({
    $id: '281507c44317d210ca4c1f425db8f2fd',  // ❌ MUST NOT wrap OOTB
    // ...
});
```

### When User Says "Create a Portal"

- Theme → Use OOTB Coral unless user says "custom theme", "custom branding", or "specific colors"

- Header → Use OOTB Stock Header unless user says "custom header"

- Footer → Skip unless user explicitly requests one

- Widgets → Search OOTB first; create custom only for unique functionality

- Pages → Create custom pages for layout, but use OOTB widgets on them where possible

## Component Hierarchy

```
ServicePortal  (sp_portal)
  └── SPTheme  (sp_theme)
        ├── SPHeaderFooter  header  (sp_header_footer)
        └── SPHeaderFooter  footer  (sp_header_footer)
  ├── SPMenu   (sp_instance_menu)
  └── SPPage[] (sp_page)
        └── containers → rows → columns → instances (sp_instance)
              └── SPWidget  (sp_widget)
                    ├── SPAngularProvider[]  (sp_angular_provider)
                    └── SPWidgetDependency[] (sp_dependency)
```

## File Structure

The Fluent root defaults to `src/fluent` (configurable via `fluentDir` in `now.config.json`); the subfolder names below are an organizational convention — the SDK discovers `.now.ts` files anywhere under `fluentDir`.

```
src/fluent/   # or your configured fluentDir
  service-portal/
    portal.now.ts                        ← ServicePortal() definition
  sp-page/<page-name>/
    <page-name>.now.ts                   ← SPPage()
  sp-widget/<widget-name>/
    widget.now.ts                        ← SPWidget()
    server_script.js                     ← server script (IIFE)
    client_script.js                     ← client script (api.controller)
    template.html                        ← AngularJS HTML template
    styles.css                           ← widget CSS/SCSS
  sp-theme/<name>/<name>.now.ts          ← SPTheme()
  sp-menu/<name>/<name>.now.ts           ← SPMenu()
  sp-instance-menu/
    menu.now.ts                          ← SPMenu() (alternative location)
  sp-angular-provider/<name>/
    <name>.now.ts                        ← SPAngularProvider()
    <name>.js                            ← provider function script
  sp-widget-dependency/<name>.now.ts     ← SPWidgetDependency()
  sp-header-footer/<name>/
    <name>.now.ts                        ← SPHeaderFooter()
    template.html / client_script.js / server_script.js
  sp-page-route-map/<name>.now.ts        ← SPPageRouteMap()
```

## portal.now.ts — Portal Definition

The portal definition file creates the `ServicePortal` record. Place it under `service-portal/portal.now.ts`.

```
// service-portal/portal.now.ts
import "@servicenow/sdk/global";
import { ServicePortal } from "@servicenow/sdk/core";
import { homePage } from "../sp-page/home/home-page.now";
import { mainMenu } from "../sp-instance-menu/menu.now";

// App scope: x_myco_itsm (example — use YOUR app scope from now.config.json)
export const itsmPortal = ServicePortal({
    $id: Now.ID["x_myco_itsm_portal"],
    title: 'IT Support Portal',
    urlSuffix: 'x_myco_itsm',       // UNIQUE — MUST be prefixed with app scope; query sp_portal with url_suffix=<value> before creating
    homePage: homePage,             // MUST be an imported SPPage object (for pages you own) OR a 32-char sys_id string (for OOTB pages). A page 'id' string like 'my-portal-home' is NOT valid here — it will silently fall back to the OOTB default home page.
    loginPage: '6995a144cb11120000f8d856634c9c25',   // OOTB login page sys_id
    notFoundPage: '3c2c9063cb11020000f8d856634c9c1f', // OOTB 404 page sys_id
    theme: '281507c44317d210ca4c1f425db8f2fd',       // OOTB Coral theme sys_id (or SPTheme object)
    mainMenu: mainMenu,             // SPMenu object — requires theme.header to be set
    defaultPortal: false,
    enableFavorites: false,
    inactive: false,
    hidePortalName: false,          // true → suppress portal title text in header

    // ITSM Integration Fields (optional)
    catalogHomePage: '53261e3487100300e0ef0cf888cb0b7c',   // OOTB catalog home page sys_id
    categoryHomePage: '07261a2147132100ba13a5554ee49092',  // OOTB category browsing page sys_id
    knowledgeHomePage: '26c2e030d7201200a9addd173e24d437', // OOTB KB home page sys_id
    catalogs: [
        { catalog: 'e0d08b13c3330100c8b837659bba8fb4', order: 100, active: true }  // Service Catalog sys_id
    ],
    knowledgeBases: [
        { knowledgeBase: 'a7e8a78bff0221009b20ffffffffff17', order: 100, active: true }  // KB sys_id
    ],
    searchSources: [
        { searchSource: 'c96eb1686721220023c82e08f585efff', order: 100 },  // Catalog search source
        { searchSource: 'c6170ae86721220023c82e08f585efe6', order: 200 }   // KB search source
    ],

    // darkTheme: darkTheme,        // SPTheme for prefers-color-scheme: dark
    // alternatePortal: '<sys_id>', // portal to redirect to when inactive: true
    // cssVariables: '--sp-accent: #4382DF;', // per-portal CSS token overrides
    // taxonomies: [],              // structured navigation taxonomy sys_ids
});
```

### ITSM Integration Fields

These fields integrate Service Catalog and Knowledge Base into your portal:

| Field | Type | Notes |
| `catalogHomePage` | string | sys_id of the catalog home page (OOTB: `53261e3487100300e0ef0cf888cb0b7c` ) |
| `categoryHomePage` | string | sys_id of the category browsing page (OOTB: `07261a2147132100ba13a5554ee49092` ) |
| `knowledgeHomePage` | string | sys_id of the KB home page (OOTB: `26c2e030d7201200a9addd173e24d437` ) |
| `catalogs` | `{catalog: string, order: number, active: boolean}[]` | Service Catalog sys_ids to include in portal |
| `knowledgeBases` | `{knowledgeBase: string, order: number, active: boolean}[]` | Knowledge Base sys_ids to include in portal |
| `searchSources` | `{searchSource: string, order: number}[]` | Zing search source sys_ids for portal search |

Note: These are portal configuration fields that set which OOTB pages and data sources the portal uses. They are NOT `SPPageRouteMap` redirect rules.

Important: The sys_ids shown above are from a standard ServiceNow instance. You MUST query your target instance to get the correct sys_ids — they may differ across instances or versions.

Rules:

- CRITICAL: `urlSuffix` MUST be unique across the instance. Query `sp_portal` with `url_suffix=<value>` before creating. If count > 0, choose a different value.

- `mainMenu` only renders if `theme.header` is set. All three MUST be present: `portal.theme` + `theme.header` + `portal.mainMenu`.

- Pass imported Fluent objects for owned components (menu, pages). Pass sys_id strings for OOTB records.

- `defaultPortal: true` SHOULD exist on at most one portal per instance.

### Logo Fallback (REQUIRED)

If no logo image is provided, you MUST generate a default logo. A portal without a logo displays broken/empty header branding.

Fallback approach:

- Generate an SVG with portal initials or abbreviated name

- Create a `sys_attachment` record with the SVG content

- Set `sp_portal.logo` to the attachment sys_id

```
// Server-side script to generate logo fallback
if (!portal.logo) {
    var title = portal.title || 'Portal';
    var initials = title.split(' ').map(function(w) { return w[0]; }).join('').substring(0, 2).toUpperCase();
    
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40">' +
        '<rect width="120" height="40" rx="6" fill="#1E1B4B"/>' +
        '<text x="60" y="26" text-anchor="middle" fill="white" font-size="16" font-weight="bold">' + initials + '</text>' +
        '</svg>';
    
    // Create attachment and set portal.logo = attachment_sys_id
}
```

## SPPage — Page Definition

Each page is a `.now.ts` file under `sp-page/<name>/`.

```
import '@servicenow/sdk/global';
import { SPPage } from '@servicenow/sdk/core';
import { myWidget } from '../../sp-widget/my-widget/my-widget.now';

// App scope: x_myco_itsm (example — use YOUR app scope from now.config.json)
export const homePage = SPPage({
    pageId: 'x_myco_itsm_home',   // UNIQUE — MUST be prefixed with app scope; query sp_page with id=<value> before creating
    title: 'Home',
    public: true,               // false → requires authentication
    draft: false,
    // roles: ['itil', 'admin'], // page-level access — server returns 403 without the role
    // css: '.hero { padding: 24px; }',  // page-level CSS
    dynamicTitleStructure: 'Home - ${portal.title}',  // browser tab title pattern
    // humanReadableUrlStructure: 'section/{name}', // friendly URL — one '/' required
    containers: [
        {
            $id: Now.ID['x_myco_itsm_home_container_1'],
            name: 'Main Content',
            width: 'container',      // 'container' (fixed width) | 'container-fluid' (full width)
            order: 100,
            rows: [
                {
                    $id: Now.ID['x_myco_itsm_home_row_1'],
                    order: 100,
                    columns: [
                        {
                            $id: Now.ID['x_myco_itsm_home_col_1'],
                            size: 12,        // Bootstrap md column — MUST sum to 12 across row
                            sizeSm: 12,      // sm breakpoint
                            sizeXs: 12,      // xs breakpoint — MUST set to stack on mobile
                            order: 100,
                            instances: [
                                {
                                    $id: Now.ID['x_myco_itsm_home_instance_1'],
                                    widget: myWidget,  // SPWidget object
                                    order: 100,
                                    active: true,
                                    // widgetParameters: '{"key":"value"}', // JSON string — see below
                                    // roles: ['itil'],  // instance-level visibility filter
                                    // asyncLoad: false, // true → defer widget render
                                    // size: 'md',       // designer UI size: 'sm'|'md'|'lg'|'xl'
                                    // css: '.panel-heading { font-size: 15px; }',
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
});
```

### SPPage Field Reference

| Field | Type | Notes |
| `pageId` | string | UNIQUE — query `sp_page` with `id=<value>` before creating. MUST prefix with app scope (e.g., `x_myco_itsm_home` ). |
| `public` | boolean | `false` → platform requires login before serving the page. |
| `roles` | string[] | Server-side 403 for users without any listed role. Admin always has access. |
| `draft` | boolean | `true` → page hidden from nav but accessible by URL. |
| `dynamicTitleStructure` | string | Browser tab title. `${portal.title}` is replaced at runtime. |
| `humanReadableUrlStructure` | string | Friendly URL e.g. `section/{name}` . MUST contain exactly one `/` . |
| `css` | string | Page-level CSS applied to every widget on this page. |

### SPInstance Field Reference

| Field | Type | Notes |
| `widget` | SPWidget | string | SPWidget object or sys_id of existing sp_widget record. |
| `widgetParameters` | string | object | JSON string, plain object (auto-serialized), or `Now.include()` . Keys must match `optionSchema` names. See note below. |
| `roles` | string[] | Hides this instance for users without the role. Does not return 403 — other instances remain visible. |
| `asyncLoad` | boolean | `true` → defer widget server call until trigger fires. |
| `asyncLoadTrigger` | string | `'viewport'` (scroll into view) | `'parallel'` (immediate async). |
| `asyncLoadDeviceType` | string | Comma-separated device types to apply async to. Empty = all. |
| `preservePlaceholderSize` | boolean | `true` → placeholder keeps widget height, prevents layout shift. Only when `asyncLoad:true` . |
| `placeholderTemplate` | string | AngularJS HTML shown while widget loads async. |
| `advancedPlaceholderDimensions` | boolean | `true` → use `placeholderDimensions` for explicit size. |
| `placeholderDimensions` | object | `{ width: '100%', height: '400px' }` . Only when `advancedPlaceholderDimensions:true` . |
| `size` | string | Designer UI card size: `'sm'` | `'md'` | `'lg'` | `'xl'` . Does NOT affect rendered layout. |
| `css` | string | Instance-level SCSS, scoped to this instance only. |
| `color` | string | Bootstrap context color for panel header: `'primary'` , `'info'` , `'success'` , etc. |

### widgetParameters — Accepted Forms

The build plugin handles all three forms correctly:

```
// Form 1 — JSON string (preferred)
widgetParameters: '{"form_title":"Register User","show_phone":"true","max_records":10}',

// Form 2 — plain object (plugin auto-serializes via JSON.stringify)
widgetParameters: { form_title: 'Register User', show_phone: true, max_records: 10 },

// Form 3 — external JSON file
widgetParameters: Now.include('./widget-params.json'),
```

Prefer Form 1 (JSON string) — boolean values stored as objects arrive as `true`/`false`, but stored as JSON strings they arrive as `'true'`/`'false'`. Keep this consistent with how the server script reads them.

In the widget server script, read parameters via `options.*`:

```
data.formTitle = options.form_title || 'Default Title';
data.showPhone = options.show_phone !== false && options.show_phone !== 'false';
```

Boolean options stored in `widgetParameters` arrive as strings `'true'` / `'false'`, not booleans. You MUST compare against both:

```
data.flag = options.my_boolean !== false && options.my_boolean !== 'false';
```

## SPWidget — Widget Definition

Each widget is a folder under `sp-widget/<widget-name>/` containing `widget.now.ts` and its asset files.

```
// sp-widget/my_widget/widget.now.ts
import "@servicenow/sdk/global";
import { SPWidget } from "@servicenow/sdk/core";
import { myProvider } from "../../sp-angular-provider/my-provider/my-provider.now";
import { chartJsDep } from "../../sp-widget-dependency/chartjs.now";

// App scope: x_myco_itsm (example — use YOUR app scope from now.config.json)
export const myWidget = SPWidget({
    $id: Now.ID["x_myco_itsm_my_widget"],
    id: "x_myco_itsm_my_widget",         // UNIQUE — MUST be prefixed with app scope; query sp_widget with id=<value> before creating
    name: 'My Widget',              // display name (duplicates allowed)
    htmlTemplate: Now.include("./template.html"),
    clientScript: Now.include("./client_script.js"),
    serverScript: Now.include("./server_script.js"),
    customCss: Now.include("./styles.css"),

    // Shared AngularJS logic — factories, services, directives
    angularProviders: [myProvider],

    // External JS/CSS libraries (Chart.js, Select2, etc.)
    dependencies: [chartJsDep],

    // Widget options configurable in Portal Designer
    // NOTE: `section` is REQUIRED on every optionSchema entry — omitting it is a type error at build time.
    optionSchema: [
        { name: 'title', label: 'Title', type: 'string', section: 'Presentation', defaultValue: 'My Title' },
        { name: 'max_records', label: 'Max Records', type: 'integer', section: 'Data', defaultValue: 10 },
        { name: 'show_footer', label: 'Show Footer', type: 'boolean', section: 'Behavior', defaultValue: 'false' },
    ],
});
```

### optionSchema — All Supported Types

| Type | Designer UI | Notes |
| `string` | Text input | Free text. |
| `boolean` | Toggle | `defaultValue` must be string `'true'` or `'false'` , not a boolean. |
| `integer` | Number input | `defaultValue` is a number, not a string. |
| `choice` | Dropdown | Requires `choices: [{label, value}]` . `defaultValue` is a `choices[].value` . |
| `reference` | Reference picker | Requires `ed: { reference: 'table_name' }` . Stores sys_id. |
| `field_list` | Multi-field picker | Requires `table: 'table_name'` . Stores comma-separated field names. |
| `field_name` | Single-field picker | Single field from a table's schema. |
| `glide_list` | List picker | Requires `ed: { reference: 'table_name' }` . Multi-value reference list. |
| `glyphicon` | Icon picker | Bootstrap glyphicon / FontAwesome picker. Stores icon name (without prefix). |

```
optionSchema: [
    { name: 'title',        label: 'Title',           type: 'string',    section: 'Presentation', defaultValue: 'My Title' },
    { name: 'show_footer',  label: 'Show Footer',     type: 'boolean',   section: 'Behavior',     defaultValue: 'false' },
    { name: 'max_records',  label: 'Max Records',     type: 'integer',   section: 'Data',         defaultValue: 10 },
    { name: 'mode',         label: 'Display Mode',    type: 'choice',    section: 'Presentation',
        defaultValue: 'card',
        choices: [{ label: 'Card', value: 'card' }, { label: 'List', value: 'list' }] },
    { name: 'ref_group',    label: 'Group',           type: 'reference', section: 'Data',
        ed: { reference: 'sys_user_group' } },
    { name: 'visible_fields', label: 'Visible Fields', type: 'field_list', section: 'Data',
        table: 'sys_user' },
    { name: 'sort_field',   label: 'Sort Field',      type: 'field_name', section: 'Data' },
    { name: 'notify_groups', label: 'Notify Groups',  type: 'glide_list', section: 'Data',
        ed: { reference: 'sys_user_group' } },
    { name: 'icon',         label: 'Icon',            type: 'glyphicon', section: 'Presentation', defaultValue: 'user' },
],
```

## Server Script Pattern

The server script runs on the server before the widget HTML is rendered. Widget server scripts use an IIFE pattern.

Note: Header and footer server scripts do NOT use IIFE — see `service-portal-ootb-reference` for the correct pattern.

```
// server_script.js (widget)
(function () {
    // MUST initialize all data.* properties — prevents undefined errors in template
    data.records = [];
    data.message = '';
    data.submitResult = null;

    // Read options (from widgetParameters on sp_instance)
    data.title = options.title || 'My Widget';
    // Boolean options arrive as strings — compare against both
    data.showFooter = options.show_footer !== false && options.show_footer !== 'false';

    // Handle client-submitted actions
    // input is populated when client calls c.server.update() after setting c.data.action
    if (input && input.action === 'create_record') {
        var result = handleCreate(input);
        data.submitResult = result;
        return;  // skip initial load
    }

    // Initial load — query data
    var gr = new GlideRecord('incident');
    gr.addQuery('active', true);
    gr.orderByDesc('sys_created_on');
    gr.setLimit(options.max_records || 10);  // MUST setLimit() — MUST NOT omit
    gr.query();
    while (gr.next()) {
        data.records.push({
            sys_id: gr.getUniqueValue(),
            number: gr.getValue('number'),
            short_description: gr.getValue('short_description'),
            state: gr.getDisplayValue('state')
        });
    }

    function handleCreate(input) {
        var errors = [];
        if (!input.short_description || (input.short_description + '').trim() === '') {
            errors.push('Short description is required.');
        }
        if (errors.length > 0) {
            return { success: false, errors: errors };
        }
        var gr = new GlideRecord('incident');
        gr.initialize();
        gr.setValue('short_description', (input.short_description + '').trim());
        var sysId = gr.insert();
        if (!sysId) {
            return { success: false, errors: ['Insert failed. Check permissions.'] };
        }
        return { success: true, sys_id: sysId + '', number: gr.getValue('number') };
    }
})();
```

Server script context variables:

| Variable | Description |
| `data` | Object passed to the client. Anything set on `data` is available as `c.data.*` . |
| `input` | Object sent from the client via `c.server.update()` . Contains everything that was on `c.data` at the time of the call. |
| `options` | Widget option values from `widgetParameters` / `optionSchema` . |

## Client Script Pattern

The client script runs in the browser as AngularJS controller logic.

```
// client_script.js
api.controller = function () {
    var c = this;

    // Initialize state
    c.view = 'list';       // use named views to switch between form/list/success
    c.submitting = false;
    c.serverErrors = [];

    c.form = {
        short_description: '',
    };

    // Submit handler — assigns form data to c.data before calling update()
    c.submit = function () {
        c.serverErrors = [];
        if (!c.form.short_description) { return; }

        c.submitting = true;

        // IMPORTANT: assign fields to c.data BEFORE calling c.server.update()
        // c.server.update() sends the current c.data object as input to the server.
        // Passing an argument to update() does NOT work — the argument is not sent.
        c.data.action = 'create_record';
        c.data.short_description = c.form.short_description;

        c.server.update().then(function () {
            c.submitting = false;
            var result = c.data.submitResult;
            if (result && result.success) {
                c.view = 'success';
                c.data.action = null;
            } else if (result && result.errors) {
                c.serverErrors = result.errors;
                c.data.action = null;
            }
        });
    };

    c.reset = function () {
        c.form = { short_description: '' };
        c.serverErrors = [];
        c.view = 'list';
    };
};
```

### c.server Methods

| Method | When to use |
| `c.server.update()` | POST — sends current `c.data` as `input` to server. Merges server response back into `c.data` . |
| `c.server.get(payload)` | GET — sends `payload` as `input` . Use for read-only fetches that don't modify state. |
| `c.server.refresh()` | Full widget reload — re-runs server script from scratch and re-renders. |

Critical constraint: `c.server.update()` sends the full `c.data` object. You MUST assign action and payload fields onto `c.data` before calling `update()`. MUST NOT pass them as arguments to `update()`.

### Paginated List Pattern

MUST NOT implement pagination as a client-side-only page indicator. A common failure mode: the page-number links change their visual "active" state, but clicking them never triggers a new data fetch — the widget silently displays the same records regardless of which page is "selected." Pagination MUST re-query the server for the requested page.

```
// client_script.js
api.controller = function () {
    var c = this;
    c.currentPage = 1;
    c.pageSize = 10;

    c.goToPage = function (page) {
        if (page < 1 || page > c.data.totalPages) { return; }
        c.currentPage = page;
        // c.server.get() sends this payload as `input` on the server —
        // the server MUST use it to compute an offset, not just re-run the same query.
        c.server.get({ page: page }).then(function () {
            // c.data is updated in place with the new page's records + totalPages
        });
    };
};
```

```
// server_script.js — reads input.page to compute the correct window
(function () {
    var pageSize = options.page_size || 10;
    var page = (input && input.page) || 1;

    var gr = new GlideRecord('incident');
    gr.addQuery('active', true);
    gr.orderByDesc('sys_created_on');

    var countGr = new GlideAggregate('incident');
    countGr.addQuery('active', true);
    countGr.addAggregate('COUNT');
    countGr.query();
    var total = countGr.next() ? parseInt(countGr.getAggregate('COUNT'), 10) : 0;

    gr.chooseWindow((page - 1) * pageSize, page * pageSize);  // MUST use chooseWindow for the page offset — setLimit() alone always returns page 1
    gr.query();

    data.records = [];
    while (gr.next()) {
        data.records.push({ sys_id: gr.getUniqueValue(), number: gr.getValue('number') });
    }
    data.currentPage = page;
    data.totalPages = Math.max(1, Math.ceil(total / pageSize));
})();
```

Rule: if a widget has a paginated list, verify by actually clicking a page-2 link after deploy and confirming the displayed records change and a new network request fires — do not assume pagination works just because the UI renders page-number links.

Note: `'incident'` above is a placeholder — the pagination mechanics (`chooseWindow`, page/pageSize tracking) are table-agnostic and apply identically whether the widget paginates incidents, requests, assets, or any other table.

### AngularJS Binding Reference

| Pattern | Usage |
| `{{c.data.field}}` | Display a value |
| `ng-model="c.form.fieldName"` | Two-way bind an input |
| `ng-if="c.data.showSection"` | Remove element from DOM |
| `ng-show="c.loading"` | Hide/show (keeps element in DOM) |
| `ng-repeat="item in c.data.records track by item.sys_id"` | List iteration — MUST use `track by` |
| `ng-click="c.methodName()"` | Click handler |
| `ng-class="{'has-error': c.errors.field}"` | Dynamic CSS class |
| `ng-disabled="c.submitting"` | Disable button during submit |

## HTML Template Pattern

```
<!-- template.html — uses Bootstrap 3 and controller alias c -->
<div class="panel panel-default">
  <div class="panel-heading">
    <h3 class="panel-title">{{c.data.title}}</h3>
  </div>
  <div class="panel-body">

    <!-- Error list -->
    <div class="alert alert-danger" ng-if="c.serverErrors.length">
      <ul class="list-unstyled m-b-none">
        <li ng-repeat="err in c.serverErrors track by $index">{{err}}</li>
      </ul>
    </div>

    <!-- Form view -->
    <div ng-if="c.view === 'form'">
      <form name="myForm" ng-submit="c.submit()" novalidate>
        <div class="form-group" ng-class="{'has-error': myForm.desc.$touched && myForm.desc.$invalid}">
          <label for="desc">Description <span class="text-danger">*</span></label>
          <input type="text" id="desc" name="desc" class="form-control"
                 ng-model="c.form.short_description" required />
          <span class="help-block" ng-if="myForm.desc.$touched && myForm.desc.$error.required">
            Required.
          </span>
        </div>
        <button type="submit" class="btn btn-primary"
                ng-disabled="c.submitting || myForm.$invalid">
          <span ng-if="c.submitting"><i class="fa fa-spinner fa-spin"></i> Saving…</span>
          <span ng-if="!c.submitting">Submit</span>
        </button>
      </form>
    </div>

    <!-- Success view -->
    <div ng-if="c.view === 'success'" class="text-center">
      <i class="fa fa-check-circle fa-3x text-success"></i>
      <p class="m-t-sm">Record created: <strong>{{c.data.submitResult.number}}</strong></p>
      <button type="button" class="btn btn-default m-t-sm" ng-click="c.reset()">Back</button>
    </div>

    <!-- Record list view -->
    <div ng-if="c.view === 'list'">
      <ul class="list-group">
        <li ng-repeat="rec in c.data.records track by rec.sys_id" class="list-group-item">
          <strong>{{rec.number}}</strong> — {{rec.short_description}}
          <!-- MUST NOT hardcode a flat class like label-default for a field with semantic
               weight (state, priority, severity, risk, etc.) — map the value to a class.
               See "Mapping Data Values to Visual Indicators" below. rec.stateClass is
               computed server-side per record, not hardcoded in the template. -->
          <span class="label pull-right" ng-class="rec.stateClass" ng-bind="rec.state"></span>
        </li>
      </ul>
      <div class="text-center text-muted" ng-if="!c.data.records.length">
        <i class="fa fa-inbox fa-2x"></i>
        <p>No records found.</p>
      </div>
    </div>

  </div>
</div>
```

Template rules:

- MUST use `c.data.*`, `c.options.*`, `c.form.*` — MUST NOT use `data.*` or `options.*` directly.

- MUST use Bootstrap 3 classes: `.panel`, `.btn-default`, `.col-xs-*` through `.col-lg-*`.

- Every `ng-repeat` MUST have `track by item.sys_id` (or `track by $index` for non-record arrays).

- Every `<button>` MUST have `type="button"` or `type="submit"` — MUST NOT omit `type`.

- Every `<input>` must have a paired `<label for="id">`.

### Mapping Data Values to Visual Indicators

This applies to any field with semantic weight, on any table, in any portal — priority, severity, approval status, risk level, SLA state, health, sentiment, stock level, or anything else where different values mean different things. It is not specific to incidents, priorities, or this example.

MUST NOT render such a field with a single flat class for every value (e.g., `label-default` regardless of what the value is). A flat class produces uniform, low-contrast output that fails to communicate the field's meaning — and combined with custom theme colors, can render as barely-visible text (light-colored text on a light background).

Pattern: compute the class per record in the server script — keeps the template dumb and the mapping in one place — and bind it with `ng-class`:

```
// server_script.js — VALUE_CLASS_MAP keys are whatever raw values YOUR field stores
// (a choice list value, a priority number, a status string) — adapt to the actual field.
var VALUE_CLASS_MAP = {
    '1': 'label-danger',   // highest severity/urgency
    '2': 'label-warning',
    '3': 'label-info',
    '4': 'label-success',  // lowest severity/urgency, or "healthy"/"approved"/etc.
};
data.records.push({
    // ...other fields...
    state: gr.getDisplayValue('state'),
    stateClass: VALUE_CLASS_MAP[gr.getValue('state')] || 'label-default',  // fallback ONLY for genuinely unmapped values
});
```

```
<span class="label" ng-class="rec.stateClass" ng-bind="rec.state"></span>
```

This pattern is table- and field-agnostic: the same `computed-class-per-record` approach applies whether the widget displays incidents, requests, assets, approvals, or a custom business object — only the map's keys and CSS classes change to fit the field's actual values.

## Page Completeness Checklist

A page is only complete when it meets ALL of these criteria:

| Requirement | Why |
| Has at least one container | Empty `containers: []` renders a blank page |
| Each container has at least one row | Containers without rows have no layout |
| Each row has at least one column | Rows without columns cannot hold widgets |
| Each column has at least one instance | Columns without instances show nothing |
| Each instance references a complete widget | Widget must have `htmlTemplate` at minimum |
| Page is linked in menu OR assigned to `homePage` | Unreachable pages are useless |

Do NOT create a page with `containers: []` — this is a scaffolding error. Every page must have at least one widget instance to be considered complete.

## Requirement Coverage Checklist

MANDATORY before declaring any build complete. A build can pass every other checklist in this guide (Page Completeness, Wiring) and still silently drop capabilities the user explicitly asked for — those checklists only verify structural completeness, not "did I build everything requested."

Before writing the Post-Installation Summary, re-read the user's original request and list every distinct capability named in it (e.g., a specific theme/color scheme, a logo, a reusable service/directive, an external library, animations, per-instance configurable options, a specific data source, a form with client-server submission, role-based access, redirect rules). For each capability, identify the exact Fluent component/file that implements it:

| Requested capability (example) | Must map to |
| Custom colors / branding | `SPTheme.customCss` with `sp-rgb()` tokens |
| Company logo | `sp_portal.logo` set — see Logo Fallback (REQUIRED) below if no real asset is provided |
| Reusable logic/service shared across widgets | `SPAngularProvider` (type: `service` / `factory` / `directive` ), linked via `widget.angularProviders` |
| External library (charting, date-picking, etc.) | `SPWidgetDependency` , linked via `widget.dependencies` — not a hand-rolled CSS/SVG substitute |
| Per-instance configurable widget options | `optionSchema` entries + distinct `widgetParameters` per `sp_instance` |
| Data from a table | `GlideRecord` in the widget server script |
| Form submission | `c.server.update()` pattern (see Client Script Pattern) |
| Role-restricted page | `SPPage.roles` |
| Navigation redirect | `SPPageRouteMap` |

Rule: if a requested capability has no corresponding component in your file list, that is a defect — either build it, or explicitly tell the user it was skipped and why. Silence is not an acceptable outcome. Do NOT substitute a fake/approximate implementation (e.g., plain CSS bars standing in for a real charting library) without disclosing the substitution to the user.

## Wiring Checklist — Common Silent Failures

These mistakes produce no build error but cause the portal to silently show wrong content at runtime:

| Mistake | Symptom | Fix |
| `homePage` set to a page `id` string (e.g. `'my-portal-home'` ) | Portal loads OOTB default home page (plain search box, no branding) | Set `homePage` to the imported SPPage object or a 32-char sys_id |
| `type: 'page'` menu item with no `page` field | Menu link renders but navigates nowhere or falls back to default home | MUST set `page` to the imported SPPage object or a 32-char sys_id |
| `mainMenu` set but `theme` or `theme.header` not set | Menu never appears in the portal | All three required: `portal.theme` , `theme.header` , `portal.mainMenu` |
| Page created but not assigned as `homePage` | The well-designed page is unreachable; portal shows OOTB home | Import the page and pass it to `ServicePortal.homePage` |
| Page created but not linked in any menu item | Users cannot navigate to the page from the menu | Add a `type: 'page'` menu item with `page: yourPage` |
| `portal.logo` left unset when the user requested a logo | Header silently falls back to plain text via the OOTB header's built-in `ng-if="::!portal.logo"` branch — no error, no visual indication anything is missing | Generate a fallback SVG logo per Logo Fallback (REQUIRED) above, or ask the user for a real logo asset |

## Do NOT

- Use `Record()` / `Now.table()` for Service Portal components — every component has a dedicated API.

- Use GlideAjax in widgets — use `c.server.get()` or `c.server.update()`.

- Omit `setLimit()` on any `GlideRecord` query.

- Use Bootstrap 4/5 classes — SP uses Bootstrap 3 only.

- Use `$scope` directly — MUST use controller alias `c` (`var c = this`).

- Re-add jQuery, AngularJS, or Bootstrap — they are globally bundled in Service Portal.

- Use `c.server.update(payload)` expecting `payload` to become `input` on the server — assign fields to `c.data` first.

- Use inline `style=""` attributes — use SCSS classes.

- Use raw hex or rgb values in widget CSS — use theme SCSS variables.

- Use `!important` in widget CSS — increase selector specificity instead.

- Omit `track by` on `ng-repeat` — MUST use `track by item.sys_id` or `track by $index`.

- Use a single flat badge/label class (e.g., `label-default`) for every value of a field that carries semantic weight (priority, state, severity, risk, approval status, etc.), on any table — map each distinct value to a distinct class per the Mapping Data Values to Visual Indicators pattern.

## Related Guides

This guide covers the portal entry point, pages, widgets, and server/client scripts. Load the guides below when the task also involves these areas:

| When you need to… | Load this guide |
| Add a theme, SCSS variables, header, footer, nav menu | `service-portal-components-guide` |
| Add an Angular provider (directive / service / factory) | `service-portal-components-guide` |
| Add an external JS/CSS library to a widget | `service-portal-components-guide` |
| Add page redirect rules | `service-portal-advanced-guide` |
| Debug widgetParameters or admin bypass | `service-portal-advanced-guide` |
| Find OOTB widget or page sys_ids to reuse | `service-portal-advanced-guide` |
| Verify deployment succeeded (post-deploy checks) | `service-portal-advanced-guide` |
| Copy exact OOTB Stock Header template/script/CSS | `service-portal-ootb-reference` |
| Copy exact Coral theme SCSS variables | `service-portal-ootb-reference` |

For a complete portal build, load these guides:

- `service-portal-guide` — portal, pages, widgets, scripts (this file)

- `service-portal-components-guide` — theme, header/footer, menu, providers, dependencies

- `service-portal-advanced-guide` — route maps, constraints, troubleshooting

- `service-portal-ootb-reference` — exact OOTB patterns (Stock Header, Coral theme) — load when creating custom headers/themes

## Post-Installation Summary Template

After a successful build and deploy, you MUST provide the user with a summary of what was built and a clickable link to the portal. Use this template:

```
### Portal Installation Complete

**Portal:** {portal.title}
**URL Suffix:** {portal.urlSuffix}

#### Components Built

| Type | Count | Details |
|------|-------|---------|
| Portal | 1 | {portal.title} |
| Pages | {n} | {page1.title}, {page2.title}, ... |
| Widgets | {n} | {widget1.name}, {widget2.name}, ... |
| Menu Items | {n} | {item1.label}, {item2.label}, ... |
| Theme | {custom/OOTB} | {theme.name or "OOTB Coral"} |
| Header | {custom/OOTB} | {header.name or "OOTB Stock Header"} |
| Footer | {custom/OOTB/None} | {footer.name or "None"} |
| Route Maps | {n} | {routeMap.shortDescription}, ... |

#### Integrations (if configured)

| Integration | Status |
|-------------|--------|
| Service Catalog | {configured/not configured} |
| Knowledge Base | {configured/not configured} |
| Search Sources | {n} sources configured |

#### Access Your Portal

**Portal Home:** `{instanceUrl}/{urlSuffix}?id={homePage.pageId}`
**Portal Designer:** `{instanceUrl}/sp_config?id=designer&page={homePage.pageId}`
```

Rules for the summary:

- Before filling this out, complete the Requirement Coverage Checklist — every capability the user requested must map to a row in "Components Built" or be explicitly disclosed as skipped.

- List ONLY artifacts that were actually created — do not list OOTB references as "built".

- If a component uses OOTB (e.g., theme: Coral), state "OOTB Coral" not the sys_id.

- The portal URL MUST be clickable so the user can navigate directly.

- Include integrations section only if `catalogs`, `knowledgeBases`, or `searchSources` were configured.

- Count only custom widgets, not OOTB widget references.

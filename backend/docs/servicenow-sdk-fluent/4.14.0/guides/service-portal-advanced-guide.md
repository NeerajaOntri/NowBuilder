Version: 4.14.0

# Service Portal Fluent Advanced Guide

Advanced topics for Service Portal Fluent SDK: page route maps, widgetParameters serialization, platform constraints, OOTB widget and page references, scoped app restrictions, and troubleshooting. Every statement here is verified against the actual running example application.

Sys_id note (applies to the whole document): Every sys_id referenced anywhere in this guide (OOTB widgets, OOTB pages, etc.) is from a baseline ServiceNow instance and may differ by release or per-instance customization. Always verify against your target instance before use.

## SPPageRouteMap — Page Navigation Redirects (sp_page_route_map)

`SPPageRouteMap` intercepts a user navigating to `routeFromPage` and issues an HTTP 302 redirect to `routeToPage` before the page renders. It is evaluated server-side.

Route maps are not ACLs. They redirect — they do not block. A user who bypasses the redirect (e.g. by direct URL) can still access the page unless the page also has `roles` set or ACLs in place.

```
import '@servicenow/sdk/global';
import { SPPageRouteMap } from '@servicenow/sdk/core';
import { homePage } from '../sp-page/home/home-page.now';
import { dashboardPage } from '../sp-page/dashboard/dashboard-page.now';

export const redirectAdminToDashboard = SPPageRouteMap({
    $id: Now.ID['route-home-to-dashboard'],

    // routeFromPage and routeToPage accept:
    // - SPPage objects (for pages created by this app)
    // - sys_id strings (for OOTB pages)
    routeFromPage: homePage,      // SPPage object — build resolves the reference
    routeToPage: dashboardPage,   // SPPage object — build resolves the reference

    // portals: array of sp_portal sys_ids — build serializes as CSV string
    // Empty / omitted → rule fires in ALL portals
    portals: ['678796e6be6445c6880a413ebbbc3115'],

    // roles: array of role names — build serializes as CSV string
    // roles: ['admin'] → fires FOR users WHO HAVE the admin role
    // Empty / omitted → fires for ALL users
    roles: ['admin'],

    order: 5,       // lower order = evaluated first; first match wins
    active: true,
    shortDescription: 'Forward admin from home page to dashboard',
});
```

### SPPageRouteMap Field Reference

For the full `SPPageRouteMap` field reference (types, defaults, accepted reference forms), see `sppageroutemap-api`.

### Route Map Rules — What To Do

| Rule | Action | Why |
| SHOULD use `active: false` to disable | Set `active: false` instead of deleting rules during testing. | Preserves rule for re-enabling without recreating. |
| MUST warn user about admin bypass | If `roles` is set, inform user: "Admin users bypass role filters — route fires for admin regardless of roles specified." | `gs.hasRole()` always returns `true` for admin. |

Platform Behavior (Reference): When user navigates to `?id=<pageId>`, platform queries `sp_page_route_map` matching `route_from_page`, `portals`, and `roles`, sorted by `order` ASC. First match triggers HTTP 302 redirect.

### Admin Role Bypass — Agent Action Required

When creating a route map with `roles` field set, you MUST include this warning in your response to the user:

Platform Constraint: Admin users bypass all role filters. This route map will fire for admin users regardless of the roles specified. To truly restrict admin access, use ACLs on the `sp_page` record.

### Redirect Loop Prevention — Agent Action Required

Before creating a route map, query existing route maps to detect potential loops:

```
# Check if target page already has a route map pointing back
now-sdk query sp_page_route_map -q 'route_from_page=<toPage_sys_id>' -f 'sys_id,short_description' --limit 10 -o json
```

If a conflicting map exists:

- Warn user: "Creating this route map would cause a redirect loop with existing map `<shortDescription>`."

- Suggest: scope to different portals, use different roles, or set `active: false` on one map.

## widgetParameters — Serialization Details

For `widgetParameters` accepted forms (JSON string, plain object, `Now.include()`), boolean handling, and `optionSchema` rules, see service-portal-guide.md.

Platform serialization note: Both JSON string and plain object forms are normalized to `{value, displayValue}` format, but the `value` field is always a string for `sp_instance` (page widgets) to match platform behavior.

## Scoped App Restrictions

Fluent SDK supports both scoped and global applications; API availability depends on which scope your app runs in. If your app is scoped (the common case), global-scope-only functions are not available and must be replaced:

| Not allowed (global-only) | Scoped alternative |
| `nowDateTime()` | `new GlideDateTime()` |
| `getXMLWait()` | `c.server.get()` or REST API |
| `gs.print()` | `gs.info()` , `gs.error()` |
| `current` (implicit) | Use `var gr = new GlideRecord(...)` explicitly |
| `pm.isActive('com.glide.i18n')` | Not available in scoped apps — throws `"pm" is not defined"` . Omit the language-selector block entirely when adapting the OOTB Stock Header server script for a scoped app (see `service-portal-ootb-reference.md` ). |

If your app is global, these functions remain available and this table does not apply.

Widget server scripts and Angular providers run in the scope of the owning app. For scoped apps, any `GlideRecord`, `GlideSystem`, or utility call must be scoped-safe.

## OOTB Widget Reference

Before creating a custom widget, you MUST verify whether one of these OOTB widgets satisfies the need. MUST NOT recreate.

Look up the sys_id using `now-sdk query` — do not hardcode sys_ids. They differ by release and instance customization (see the sys_id note at the top of this document). Query by the stable `Widget ID` to get the authoritative sys_id for your target instance.

For full query syntax and options, see query-guide.md.

```
# Look up an OOTB widget by its stable Widget ID
now-sdk query sp_widget -q 'id=widget-data-table' -f 'sys_id,id,name' -o json

# Common OOTB widgets to query:
now-sdk query sp_widget -q 'id=widget-form' -f 'sys_id,id,name' -o json          # Full ServiceNow form
now-sdk query sp_widget -q 'id=typeahead-search' -f 'sys_id,id,name' -o json     # Search with autocomplete
now-sdk query sp_widget -q 'id=widget-login' -f 'sys_id,id,name' -o json         # Portal login form
now-sdk query sp_widget -q 'id=user-profile' -f 'sys_id,id,name' -o json         # User profile card
now-sdk query sp_widget -q 'id=widget-simple-list' -f 'sys_id,id,name' -o json   # Minimal record list
now-sdk query sp_widget -q 'id=breadcrumbs' -f 'sys_id,id,name' -o json          # Navigation breadcrumb trail
now-sdk query sp_widget -q 'id=sp-user-menu' -f 'sys_id,id,name' -o json         # User dropdown in header
```

Use the `sys_id` from the query result in your Fluent definition.

## OOTB Page Reference

Before creating a custom page, verify whether an OOTB page covers the need.

Look up the sys_id using `now-sdk query` — do not hardcode sys_ids. They differ by release and instance customization. Query by the stable `Page ID` to get the authoritative sys_id for your target instance.

For full query syntax and options, see query-guide.md.

```
# Look up an OOTB page by its stable Page ID
now-sdk query sp_page -q 'id=form' -f 'sys_id,id,title' -o json

# Common OOTB pages to query:
now-sdk query sp_page -q 'id=list' -f 'sys_id,id,title' -o json           # Generic record list
now-sdk query sp_page -q 'id=ticket' -f 'sys_id,id,title' -o json         # Ticket/case detail
now-sdk query sp_page -q 'id=login' -f 'sys_id,id,title' -o json          # Portal login
now-sdk query sp_page -q 'id=404' -f 'sys_id,id,title' -o json            # 404 error page
now-sdk query sp_page -q 'id=search' -f 'sys_id,id,title' -o json         # Search results
now-sdk query sp_page -q 'id=approvals' -f 'sys_id,id,title' -o json      # Approval list
now-sdk query sp_page -q 'id=requests' -f 'sys_id,id,title' -o json       # User's requests
now-sdk query sp_page -q 'id=user_profile' -f 'sys_id,id,title' -o json   # User profile page
now-sdk query sp_page -q 'id=sc_landing' -f 'sys_id,id,title' -o json     # Service Catalog landing
now-sdk query sp_page -q 'id=sc_cat_item' -f 'sys_id,id,title' -o json    # Catalog item order form
now-sdk query sp_page -q 'id=kb_view' -f 'sys_id,id,title' -o json        # Knowledge base home
now-sdk query sp_page -q 'id=kb_article' -f 'sys_id,id,title' -o json     # Knowledge article reader
```

Use the `sys_id` from the query result in your Fluent definition.

You MUST reference OOTB pages by sys_id (e.g. `loginPage`, `notFoundPage` on `ServicePortal`). MUST NOT create SPPage wrappers for OOTB pages.

## Troubleshooting

### Menu not showing

See service-portal-components-guide.md for the three requirements and service-portal-ootb-reference.md for the full prevention checklist.

### Widget options arrive as undefined

`sp_instance.widget_parameters` is empty or malformed. Possible causes:

- `widgetParameters` was omitted entirely on the `sp_instance` — add it.

- A `Now.include()` path in `widgetParameters` points to a file that does not exist — fix the path.

- The option name in `widgetParameters` does not match the `name` in `optionSchema` — names are case-sensitive.

### Server script not receiving submitted data

See service-portal-guide.md for `c.server.update()` usage. Key rule: assign fields to `c.data` before calling `update()` — arguments passed to `update()` are ignored.

### Theme SCSS not compiling

`SPTheme.turnOffScssCompilation` is set to `true`. Set it to `false` when `customCss` uses `$variables`, `sp-rgb()`, `darken()`, `lighten()`, or any SCSS function.

### Route map fires for admin even with role restriction

This is a platform constraint. `gs.hasRole()` always returns `true` for the admin role regardless of the role name checked. Route maps cannot exclude admin via role filtering. Use ACLs on `sp_page` for true admin exclusion.

### pageId conflict

`pageId` must be globally unique across ALL portals on the instance. Using a generic name like `home` or `dashboard` will conflict with existing pages. Always prefix with your app scope: `x_myco_itsm_home`, `x_myco_itsm_dashboard`.

### Angular provider ReferenceError in browser console

The provider script used `api.value = ...` or `api.controller = ...`. Provider scripts must use a plain named function. The `api.*` pattern is only for widget client scripts.

### Header shows no logo / broken branding

`portal.logo` (or `theme.logo`) was left unset. This produces no build error — the OOTB Stock Header template has a built-in `ng-if="::!portal.logo"` branch that silently falls back to plain text, with no visual indication anything is missing.

Agent Action Required — MUST NOT leave the header logo unset. If the user did not supply a real logo asset, you MUST generate a fallback SVG logo (portal initials or abbreviated name), create a `sys_attachment` record from it, and set the logo field to that attachment's sys_id. Do not silently ship a portal with a blank/broken logo, and do not skip this step even if the user did not explicitly ask for a logo. See service-portal-guide.md — Logo Fallback (REQUIRED) for the exact SVG generation script and attachment steps.

## Previewing the Portal After Deploy

Once the app is installed on the instance, the portal and all its pages are live. Use any of the following methods to preview or inspect it.

### Browser Preview

Open the portal home page directly in a studio/ide after installation:

```
<instance>/<urlSuffix>?id=<homePage.pageId>
```

- `urlSuffix` — the value set in `ServicePortal.urlSuffix` (e.g. `now_support`)

- `homePage.pageId` — the value set in `SPPage.pageId` (e.g. `now-support-portal-home`)

Example: `https://abc.service-now.com/now_support?id=now-support-portal-home`

To preview any specific page (not just the home page):

```
<instance>/<urlSuffix>?id=<page.pageId>
```

### Service Portal Designer (In-Browser Visual Editor)

The portal designer lets you inspect the page layout, container/row/column/instance hierarchy, and widget configuration visually.

Navigate to:

```
<instance>/sp_config?id=designer&page=<page.pageId>
```

Or from ServiceNow: Service Portal → Service Portal Configuration → Designer, then select the portal and page.

The designer shows:

- All containers, rows, columns, and widget instances on the page

- Widget option values (widgetParameters) per instance

- Live preview of the rendered page

## Post-Deploy Verification Checklist

After deploy succeeds, verify each component you created by querying the instance. Do NOT report success until all checks pass.

Verify only the components you actually created:

| Component Created | Verification Query | Expected |
| `ServicePortal` | `now-sdk query sp_portal -q 'url_suffix=<urlSuffix>' -f 'sys_id' --limit 1 -o json` | 1 record |
| `SPPage` | `now-sdk query sp_page -q 'id=<pageId>' -f 'sys_id' --limit 1 -o json` | 1 record per page |
| `SPWidget` | `now-sdk query sp_widget -q 'id=<widget.id>' -f 'sys_id' --limit 1 -o json` | 1 record per widget |
| `SPTheme` (custom) | `now-sdk query sp_theme -q 'sys_id=<theme.$id>' -f 'sys_id' --limit 1 -o json` | 1 record |
| `SPMenu` | `now-sdk query sp_instance_menu -q 'sys_id=<menu.$id>' -f 'sys_id' --limit 1 -o json` | 1 record |
| `SPHeaderFooter` | `now-sdk query sp_header_footer -q 'sys_id=<header.$id>' -f 'sys_id' --limit 1 -o json` | 1 record |
| `SPAngularProvider` | `now-sdk query sp_angular_provider -q 'sys_id=<provider.$id>' -f 'sys_id' --limit 1 -o json` | 1 record |
| `SPWidgetDependency` | `now-sdk query sp_dependency -q 'name=<dependency.name>' -f 'sys_id' --limit 1 -o json` | 1 record |
| `SPPageRouteMap` | `now-sdk query sp_page_route_map -q 'sys_id=<routeMap.$id>' -f 'sys_id' --limit 1 -o json` | 1 record |
| `SPInstance` | `now-sdk query sp_instance -q 'sys_id=<instance.$id>' -f 'sys_id' --limit 1 -o json` | 1 record per widget instance |

Note: Use `id` for components with a unique identifier field (`SPPage`, `SPWidget`). Use `sys_id` for all others.

Skip verification for:

- OOTB components referenced by sys_id (e.g., `theme: '281507c44317d210ca4c1f425db8f2fd'`)

- Components not created in this deployment

After verification:

- All checks pass → Report success with list of deployed components

- Any check fails → Report which component is missing and its expected identifier

## Related Guides

This guide covers route maps, platform constraints, OOTB references, and troubleshooting. Load the guides below when the task also involves these areas:

| When you need to… | Load this guide |
| Create the portal entry point, pages, or widgets | `service-portal-guide` |
| Write server scripts, client scripts, or widget templates | `service-portal-guide` |
| Configure the theme, SCSS variables, header, footer, or nav menu | `service-portal-components-guide` |
| Add Angular providers or external JS/CSS libraries to a widget | `service-portal-components-guide` |
| Copy exact OOTB Stock Header template/script/CSS | `service-portal-ootb-reference` |
| Copy exact Coral theme SCSS variables | `service-portal-ootb-reference` |

For a complete portal build, load these guides:

- `service-portal-guide` — portal, pages, widgets, scripts

- `service-portal-components-guide` — theme, header/footer, menu, providers, dependencies

- `service-portal-advanced-guide` — route maps, constraints, troubleshooting (this file)

- `service-portal-ootb-reference` — exact OOTB patterns (Stock Header, Coral theme) — load when creating custom headers/themes

Quick tag lookup for AI agents:

- Prompt contains “create portal” / “build portal” / “new portal” → load all four guides

- Prompt contains “create widget” / “write server script” / “widget template” → start with `service-portal-guide`

- Prompt contains “theme” / “menu” / “header” / “footer” / “angular provider” / “dependency” → load `service-portal-components-guide`

- Prompt contains “redirect” / “route map” / “widget not showing” / “options undefined” / “troubleshoot” / “OOTB” / “no logo” / “missing logo” / “blank header” → load `service-portal-advanced-guide`

- Prompt contains "custom header" / "custom theme" / "OOTB pattern" / "Stock Header" / "Coral" → load `service-portal-ootb-reference`

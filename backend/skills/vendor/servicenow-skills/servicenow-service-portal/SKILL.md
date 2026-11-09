---
name: servicenow-service-portal
description: ServiceNow Service Portal and Employee Center - portals, pages, widgets (HTML template, CSS, client controller, server script, options), the data object, c.server.update / c.server.get, spUtil, $sp server API, theming and security. Use for portal pages, custom widgets or questions about how the portal works.
license: Apache-2.0
metadata:
  category: ui
  version: "1.1"
---

# Service Portal

## Building blocks
| Record | Table | Holds |
|---|---|---|
| Portal | `sp_portal` | URL suffix (`/sp`, `/esc`), homepage, theme, menus, Knowledge bases and catalogs |
| Page | `sp_page` | Layout of containers → rows → columns → widget instances |
| Widget | `sp_widget` | HTML template, CSS (SCSS), client controller (AngularJS), server script, option schema |
| Widget instance | `sp_instance` | A widget placed on a page, with its options |
| Theme | `sp_theme` | Header/footer, CSS variables |

## Widget pattern
```javascript
// Server script: runs on load and on c.server.update(); fills `data`
(function () {
    data.items = [];
    if (input && input.action === 'refresh') { /* react to the client */ }
    var gr = new GlideRecordSecure('incident');
    gr.addQuery('caller_id', gs.getUserID());
    gr.addActiveQuery();
    gr.setLimit(10);
    gr.query();
    while (gr.next()) {
        data.items.push({ sys_id: gr.getUniqueValue(), number: gr.getValue('number'),
                          short_description: gr.getValue('short_description') });
    }
})();
```
```javascript
// Client controller
api.controller = function () {
    var c = this;
    c.refresh = function () { c.server.get({ action: 'refresh' }).then(function (r) { c.data.items = r.data.items; }); };
};
```
HTML template: `<div ng-repeat="i in c.data.items">{{i.number}} - {{i.short_description}}</div>`.

## Rules
1. Clone OOB widgets before changing them; never edit the originals.
2. Use `GlideRecordSecure` (or `$sp` helpers) in server scripts: the portal serves end users.
3. Pass only the fields the widget needs into `data`; never whole records or secrets.
4. Client→server: `c.server.update()` (sends `c.data` as `input`) or `c.server.get({...})`.
5. Use `spUtil.addInfoMessage`, `spUtil.recordWatch` for live updates, `$sp.getParameter` for URL params.
6. Catalog items and record producers render in the portal through `sc_cat_item` pages; behaviour
   comes from catalog UI policies and catalog client scripts (UI Type: All / Mobile / Service Portal).
7. Employee Center is a portal (`/esc`) built on the same records; prefer configuring it over new portals.

## What nowBuilder does
nowBuilder doesn't write portal widgets or pages; it describes the widget (template, client and
server scripts) for the user to create in Service Portal → Widgets, and builds supporting script
includes, business rules and notifications as plan rows.

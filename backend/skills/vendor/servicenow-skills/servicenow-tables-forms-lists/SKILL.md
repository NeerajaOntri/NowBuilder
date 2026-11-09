---
name: servicenow-tables-forms-lists
description: Designing and changing ServiceNow tables, fields (dictionary), reference qualifiers, forms, lists and records, including table extension (task, cmdb_ci), field types, views and dot-walking. Use when creating a table or field, changing a form or list layout, choosing a field type, or writing reference qualifiers.
license: Apache-2.0
metadata:
  category: foundations
  version: "1.1"
---

# Tables, forms, lists and records

## When to use
- Creating or extending a table, adding a field, choosing a field type.
- Configuring form sections, views, related lists, list columns.
- Writing reference qualifiers or dot-walked conditions.

## Key facts
- Table definitions live in `sys_db_object`; fields in `sys_dictionary`; labels in `sys_documentation`; choice values in `sys_choice`.
- Every record has system fields: `sys_id`, `sys_created_on`, `sys_created_by`, `sys_updated_on`, `sys_updated_by`, `sys_mod_count`, `sys_class_name` (on extended tables).
- **Extension:** child tables inherit parent fields. `task` is the parent of incident, problem, change_request, sc_req_item, sc_task, sn_customerservice_case, HR cases. `cmdb_ci` is the root of the CI class hierarchy.
- **Naming:** global custom tables/fields get `u_`; scoped ones get the scope prefix, e.g. `x_acme_ai_suggestion`, field `x_acme_ai_confidence` only when added to a table outside the scope.
- **Dot-walking:** follow references in conditions and layouts, e.g. `caller_id.department.name`.

## Rules
1. **Extend before you create.** If the record is a unit of work with assignment, state and SLAs, extend `task`. If it is a configuration item, extend the right `cmdb_ci` class. Otherwise create a standalone table.
2. Check licensing before creating custom tables - many subscriptions limit custom tables. Prefer extending a licensed table where it fits.
3. Choose the **narrowest correct field type:** Reference (not String) for links to records, Choice for closed sets, Date/Time types (not String) for dates, Integer/Decimal/Currency for numbers, Journal for comment streams.
4. Choice fields: store stable **values**, display **labels**. Code and integrations compare values, never labels.
5. Add fields to the child table that needs them, not to `task` or `cmdb_ci`, unless every child genuinely needs it.
6. Use **reference qualifiers** so users can only pick valid records:
   - Simple: built with the condition builder.
   - Dynamic: reuse a *Dynamic Filter Option*.
   - Advanced: `javascript:new MyRefQuals().activeGroupsFor(current)` - keep the script in a Script Include, never inline logic.
7. Set **mandatory/read-only at the dictionary level** only when it must hold everywhere (including imports and APIs); otherwise use UI/Data Policies.
8. Index fields that appear in frequent queries on large tables (raise with platform owners; indexes are requested, not always self-service).
9. Never reuse a field for a different meaning. Create a new field and migrate.

## The records behind tables and fields
| What | Table | Key columns |
|---|---|---|
| Table | `sys_db_object` | `name` (global: `u_…`, scoped: `x_<vendor>_<app>_…`; lowercase, digits, underscores), `label`, `super_class` (the parent table's record - a sys_id), `is_extendable` |
| Field (column) | `sys_dictionary` | `name` (the table), `element` (column, global `u_…`), `column_label`, `internal_type`, `max_length`, `reference` (referenced table), `choice` (1 = dropdown with --None--, 3 = without), `mandatory`, `read_only`, `default_value`, `active` |
| Choice values | `sys_choice` | `name` (table), `element` (field), `value`, `label`, `sequence`, `language`, `inactive` |
| Field labels | `sys_documentation` | maintained by the platform from the column label |

- Creating a table record creates the database table, its system fields (`sys_id`, `sys_created_on`,
  `sys_created_by`, `sys_updated_on`, `sys_updated_by`, `sys_mod_count`) and, when it extends a table,
  all of the parent's fields. Creating a dictionary record adds the column.
- **Field types** (`internal_type`, the names in `sys_glide_object`): `string`, `integer`, `decimal`,
  `float`, `boolean`, `glide_date`, `glide_date_time`, `glide_duration`, `reference`, `glide_list`
  (List), `choice`, `journal_input` (comments / work notes style), `html`, `email`, `url`, `currency`,
  `price`, `script`, and more - the instance's own list is the authority.
- String sizes: 40 (default), 100, 255; over 255 becomes a long text column, 4000 for descriptions.
- A table without ACLs relies on the default rules; add read / write / create / delete ACLs for the
  table's role (requires security_admin).
- Check custom table entitlements before creating tables; don't extend `sys_choice` (not supported).

## What nowBuilder does
Tables (`table` rows) and fields (`field` rows, with their choice values) are plan rows and deploy
into the update set: table first, then its fields, then the business rules, policies and flows that
use them. It doesn't change out-of-box fields, form or list layouts, views, dictionary overrides or
ACLs - it says what to configure.

## Forms and lists
- Keep forms short: most-used fields in the first section, rarely used ones in tabs/sections.
- Use **views** for different audiences instead of hiding fields with scripts.
- Related lists for child records; *Defined Related Lists* (`sys_relationship`) for relationships that are not a direct reference.
- List layouts: 6-8 columns; include number, short description, state, assignment group, updated.
- Form annotations explain fields; don't add explanation text with client scripts.

## Anti-patterns
- String fields holding sys_ids or comma-separated lists of sys_ids (use Reference or List type).
- Copying a field's value onto another table to avoid a dot-walk (data goes stale).
- Huge single-section forms with 60+ fields.
- Deleting a field that integrations or reports still use - deactivate and hide first, delete after a release.

## Example: advanced reference qualifier
```javascript
// Dictionary attribute on incident.assignment_group:
// javascript:new RefQuals().groupsForCategory(current.category)
var RefQuals = Class.create();
RefQuals.prototype = {
    initialize: function () {},
    groupsForCategory: function (category) {
        var q = 'active=true^type=itil';   // adjust to your group types
        if (category) q += '^u_categoriesLIKE' + category;
        return q;
    },
    type: 'RefQuals'
};
```

## Review checklist
- [ ] Extends the right parent (task / cmdb_ci / none)
- [ ] Field types are specific; references not strings
- [ ] Reference qualifiers restrict choices
- [ ] Choice values (not labels) used in code
- [ ] Form and list layouts are short and audience-specific

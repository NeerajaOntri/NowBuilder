---
name: servicenow-platform-basics
description: Core concepts of the ServiceNow platform - instances, scopes, the sys_id/table/record model, release families, navigation, and how configuration differs from customization. Use when explaining how ServiceNow works, orienting a new developer or admin, or deciding where a change belongs before writing anything.
license: Apache-2.0
metadata:
  category: foundations
  version: "1.1"
---

# ServiceNow platform basics

## When to use
- Someone asks "how does ServiceNow work", "what is a scope", "what is a sys_id".
- Before designing any change: decide whether it is configuration, customization, or a new app.
- Before touching an instance: confirm which instance (dev/test/prod) and which scope you are in.

## Mental model
- **Instance:** a single-tenant ServiceNow environment (`https://<name>.service-now.com`). Typical landscape: dev → test → prod. Only dev is for building.
- **Everything is a record in a table.** Forms, lists, scripts, ACLs, menus and even table definitions are records (`sys_script`, `sys_security_acl`, `sys_db_object`, `sys_dictionary`).
- **sys_id:** 32-character GUID that uniquely identifies every record. Reference fields store sys_ids.
- **Scope:** every artifact belongs to an application scope - `global` or a scoped app such as `x_acme_ai`. Scope controls naming, cross-scope access, and how the work is packaged.
- **Release families** are named alphabetically (…, Xanadu, Yokohama, Zurich, Australia, Brazil). Two families per year. Check the instance version under *System Diagnostics > Stats* or `glide.buildtag`.
- **Platform vs products:** the Now Platform provides tables, security, automation, UI and integrations. ITSM, CSM, HRSD, ITOM etc. are applications built on it and licensed separately.

## Rules
1. Build in a sub-production instance. Never develop directly in production.
2. Before any change, confirm the **application scope** in the scope picker. Work done in the wrong scope is hard to move.
3. Prefer **configuration** (no-code: dictionary, form/list layout, UI policies, flows, properties) over **customization** (scripts, changes to out-of-box records). Configuration survives upgrades; customization creates skipped records.
4. Do not modify out-of-box (OOB) records when an extension point exists (a new Business Rule, a new UI Action, a Script Include override). Modified OOB records are skipped on upgrade.
5. Reference records by **sys_id** in code only through properties or lookups by a stable key (name, number). Never hard-code sys_ids that differ between instances (users, groups, data records).
6. Every change you want to promote must be captured: an Update Set (global) or the scoped app's source control / application repository.

## Navigation essentials
- `<table>.list` and `<table>.do` in the filter navigator open a list or a new form (e.g. `incident.list`).
- `<table>.config` opens the table's configuration (dictionary, layouts, business rules).
- `sys.scripts.do` (Scripts - Background) runs server JavaScript - admin only, dev only, and it is not captured in update sets.
- Right-click a form header → *Configure* / *Show XML* / *Copy sys_id*.

## Configuration vs customization decision
| Need | First choice | Only if that can't do it |
|---|---|---|
| Show/hide/mandatory field | UI Policy | Client Script |
| Enforce a rule on save regardless of UI | Data Policy | Before Business Rule |
| Automate multi-step process | Flow (Workflow Studio) | Business Rule + Script Include |
| Reusable server logic | Script Include | - |
| Store a setting | System property | Hard-coded constant (never) |

## Anti-patterns
- Running fixes in *Scripts - Background* on production without a captured, reviewed script.
- Adding a field to `task` (the parent of incident/problem/change/etc.) when only one child table needs it.
- Treating "admin" as a role to hand out for convenience.

## Review checklist
- [ ] Correct instance and scope confirmed
- [ ] Configuration preferred over code where possible
- [ ] No OOB record modified without a written reason
- [ ] Change is captured for promotion

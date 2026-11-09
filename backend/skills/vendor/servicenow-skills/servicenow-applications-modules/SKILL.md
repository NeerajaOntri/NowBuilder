---
name: servicenow-applications-modules
description: Building ServiceNow applications - scoped vs global apps, App Engine Studio / ServiceNow Studio, application menus and modules, cross-scope access, application repository and source control. Use when starting a new app, adding navigation (application menus/modules), deciding between scoped and global, or packaging an app for other instances.
license: Apache-2.0
metadata:
  category: foundations
  version: "1.1"
---

# Applications and modules

## When to use
- Starting a new application or feature set.
- Adding left-nav entries (application menus and modules).
- Deciding scoped vs global, or troubleshooting cross-scope errors.
- Moving an app between instances.

## Key facts
- **Scoped application:** has a namespace (`x_<vendor prefix>_<app>`), its own tables, scripts, roles and properties, and protection from other scopes. Default for new work.
- **Global scope:** shared namespace; customizations of OOB apps live here. No isolation.
- **Application menu** (`sys_app_application`) = a section in the left navigator. **Module** (`sys_app_module`) = a link under it (list, form, URL, separator, report, etc.).
- Build tools: **ServiceNow Studio** / **App Engine Studio** (low-code, guided) for developers and citizen devs.
- **Cross-scope access:** calling another scope's Script Include or table needs that scope to allow it (*Accessible from: All application scopes*) and, depending on settings, a *Cross-scope privilege* record. Runtime restrictions appear as "Access to ... from scope ... has been refused".
- **Promotion:** scoped apps move via the application repository (*Publish to app repo* / install on target) or **source control** (Git integration in Studio). Update sets also work but are the weaker option for apps.

## Rules
1. **New functionality = new scoped app.** Use global only when you must modify a global OOB artifact.
2. One app per business capability. Don't make a "misc utilities" app that everything depends on.
3. Create app roles at the start (`x_acme_ai.user`, `x_acme_ai.admin`) and put every module behind a role.
4. Modules:
   - Link to lists with a filter and a sensible default sort (`active=true^ORDERBYDESCsys_updated_on`).
   - Name them as tasks users do ("My open suggestions"), not tables.
   - Use separators to group; keep each menu under ~12 modules.
5. Keep **cross-scope** surface small: expose a few Script Include APIs marked accessible from all scopes; keep everything else *This application scope only*.
6. Put configurable values in **system properties** inside the app's scope (`x_acme_ai.endpoint`), with a category so admins can find them.
7. Connect the app to **source control** from day one; commit with meaningful messages; branch for features.
8. Version the app (semantic versioning) and keep release notes in the app's description or repo.

## Example module definitions
| Title | Link type | Table | Filter | Roles |
|---|---|---|---|---|
| AI Assistant (menu) | - | - | - | x_acme_ai.user |
| My suggestions | List of Records | x_acme_ai_suggestion | assigned_to=javascript:gs.getUserID()^active=true | x_acme_ai.user |
| All suggestions | List of Records | x_acme_ai_suggestion | (none) | x_acme_ai.admin |
| Properties | URL | - | `system_properties_ui.do?sysparm_title=AI&sysparm_category=x_acme_ai` | x_acme_ai.admin |

## Anti-patterns
- Building an app in global "because it is easier", then fighting update-set collisions forever.
- Modules with no role (visible to everyone, including self-service users).
- Turning off scope protection or granting all cross-scope privileges to silence errors.
- Copying an OOB app into a scope instead of extending it.

## Review checklist
- [ ] Scoped app with clear prefix and roles
- [ ] Every module role-restricted, filtered and named for the user's task
- [ ] Minimal cross-scope API surface
- [ ] Properties for configuration
- [ ] Source control connected

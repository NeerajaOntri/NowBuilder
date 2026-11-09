---
name: servicenow-development-standards
description: Cross-cutting ServiceNow development standards and code review - naming, upgrade safety, performance, security, logging, Automated Test Framework (ATF), Instance Scan, documentation and a full review checklist. Use when reviewing any ServiceNow change before promotion, setting team coding standards, or when unsure which specific ServiceNow skill applies.
license: Apache-2.0
metadata:
  category: standards
  version: "1.1"
---

# ServiceNow development standards

## Which skill to load
| Task | Skill |
|---|---|
| Table/field/form/list work | servicenow-tables-forms-lists |
| Access, roles, ACLs | servicenow-users-roles-acls |
| New app, menus, scopes | servicenow-applications-modules |
| No-code settings, notifications, properties | servicenow-configuration |
| Promoting changes | servicenow-update-sets |
| Any script | servicenow-javascript + servicenow-glide-apis |
| Server record logic | servicenow-business-rules |
| Browser form logic | servicenow-client-scripts, servicenow-ui-policies-ui-actions |
| Reusable logic / GlideAjax | servicenow-script-includes |
| Automation | servicenow-flow-designer, servicenow-workflow-studio |
| APIs and data loads | servicenow-integrations-rest |
| Process apps | incident, problem, change, request, service-catalog, knowledge, cmdb, sla, csm, hrsd skills |
| Events, scheduled jobs, system properties | servicenow-events-scheduled-jobs |
| Portal pages and widgets | servicenow-service-portal |
| Testing | servicenow-atf |
| Loading data | servicenow-import-sets |
| Reports, dashboards, KPIs | servicenow-reporting |
| Chatbot topics, generative AI | servicenow-virtual-agent-now-assist |

## Scope of the examples in these skills
Examples are written for the **global** scope in ES5 (what a Table API deployment into an update set creates). In a scoped app, prefix tables, properties, events and roles with the scope (`x_<vendor>_<app>`), and call another scope's include as `new x_vendor_app.ClassName()`.

## Naming
- Scoped artifacts carry the scope prefix automatically; give records human names: `AI - Triage on insert` (BR), `AIClient` (Script Include, PascalCase), `acme.ai.auto_apply_threshold` (property, lowercase dot.notation; scoped apps prefix it with the scope, e.g. `x_acme_ai.auto_apply_threshold`).
- One purpose per artifact; description field says *what* and *why*.

## Upgrade safety
1. Don't edit OOB records; copy/extend/override.
2. Check **skipped records** after each upgrade and decide: keep yours, revert, or merge.
3. Avoid DOM manipulation, undocumented APIs and global-scope monkey patching.

## Performance
- Filters and limits in queries; GlideAggregate for counts; no queries in loops.
- Async for external calls and heavy work.
- Few client scripts; scratchpad for load data.
- Index frequent query fields on large tables.
- Watch the **slow transaction log** and **slow query log** after releases.

## Security
- ACLs on every new table and sensitive field; roles via groups.
- GlideRecordSecure in user-facing server code; validate all inputs.
- No secrets in scripts; credentials in aliases/auth profiles.
- No PII in logs; mask PII before external AI or integrations.

## Testing
- **ATF** tests for critical forms, catalog items, Business Rules and Script Includes; run the suite before every promotion.
- **Instance Scan** checks (best-practice and custom) run in CI or before release; fix findings or document exceptions.
- Test as real personas via impersonation, in Workspace and portal as well as UI16.

## Anti-patterns
- "It works in dev" promoted without ATF, preview or a second reviewer.
- Each developer following personal conventions; no shared checklist.
- Suppressing Instance Scan findings without a documented exception.

## Review checklist
- [ ] Correct scope; captured for promotion
- [ ] Configuration preferred; OOB untouched
- [ ] Scripts: getValue, no GlideElement leaks, IIFE, try/catch
- [ ] Business Rules: right timing, condition field, no current.update()
- [ ] Client: UI Policy first, async GlideAjax, no DOM
- [ ] Script Includes: name/type match, input validation, role checks
- [ ] Flows: narrow triggers, error handling, run-as chosen
- [ ] Integrations: async, OAuth/aliases, retries, idempotent
- [ ] ACLs and roles least-privilege, tested by impersonation
- [ ] ATF + Instance Scan pass
- [ ] Description/documentation updated

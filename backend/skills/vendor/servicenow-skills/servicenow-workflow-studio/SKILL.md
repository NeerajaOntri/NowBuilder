---
name: servicenow-workflow-studio
description: Using ServiceNow Workflow Studio, the single home for process automation - flows, subflows, actions, playbooks (Process Automation Designer / Playbook Experience), decision tables (Decision Builder), and migrating legacy Workflow Editor workflows. Use when choosing the right automation tool, designing cross-team processes or playbooks, externalizing decision rules, or retiring classic workflows.
license: Apache-2.0
metadata:
  category: automation
  version: "1.1"
---

# Workflow Studio

## When to use
- Deciding which automation tool fits a requirement.
- Designing playbooks that guide agents through multi-stage work.
- Moving rules out of code into decision tables.
- Replacing classic workflows (Workflow Editor).

## What lives in Workflow Studio
| Tool | Best for |
|---|---|
| **Flows / subflows** | Automated multi-step processes triggered by records, schedules or apps |
| **Actions** | Reusable single steps with inputs/outputs |
| **Playbooks** (Process Automation Designer) | Process owners designing stage-based, cross-department processes that agents work through in Workspace (Playbook Experience) |
| **Decision tables** (Decision Builder) | Business rules as rows - inputs → result - editable without code |
| **Service Creator** | Departments publishing simple services into the catalog |
| **Classic workflow** (legacy) | Maintain only; plan migration |

## Choosing a tool
1. Fully automated, no human guidance → **flow**.
2. Humans complete activities across stages with visibility of progress (onboarding, major incident, complex case) → **playbook**, with flows doing the automated parts.
3. "If X and Y then Z" rules that business owners change often (routing, approval level, risk tier) → **decision table**, called from a flow or script.
4. Field-level, fast, technical logic on save → Business Rule (outside Workflow Studio).

## Rules
1. **No new classic workflows.** Build new automation in flows or playbooks; migrate existing workflows when you next change them.
2. Design playbooks **stage first**: name the stages and their exit criteria before adding activities.
3. Keep each playbook activity small and owned (one role or group).
4. Decision tables: inputs must be record fields or explicit inputs; include a **default row**; order rows from specific to general; document each row's intent.
5. Call decision tables from flows (*Make a decision* / decision action) or script (`sn_dt.DecisionTableAPI`), not by copying the logic into code.
6. Reuse: shared logic in subflows and actions, published in a scoped app.
7. Name with the business process: "Employee onboarding - IT provisioning", not "Flow 7".
8. Review automation inventory periodically: inactive, failing or duplicate flows.

## Migration from classic workflow
1. Inventory active workflows and their triggers (catalog items, tables).
2. Map each activity: approvals → *Ask for Approval*; tasks → *Create Task*; timers → *Wait*; scripts → actions calling Script Includes.
3. Build and test the flow in parallel; switch the catalog item's process engine or trigger; keep the workflow inactive for one release, then retire.
4. In-flight contexts finish on the old workflow; new requests use the flow.

## Anti-patterns
- Encoding approval matrices as nested If blocks instead of a decision table.
- Playbooks with 40 activities in one stage.
- Starting new classic workflows "because the team knows it".

## Review checklist
- [ ] Right tool for the requirement
- [ ] No new classic workflow
- [ ] Decision tables have defaults and documented rows
- [ ] Playbooks stage-first with owners
- [ ] Migration plan for touched legacy workflows

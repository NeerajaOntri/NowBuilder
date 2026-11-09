---
name: servicenow-problem-management
description: ServiceNow Problem Management - problem table and state model, root cause analysis, workarounds, known errors and the known error knowledge base, linking incidents and changes, proactive problem detection and KPIs. Use when configuring problem workflows, automating problem creation from incident trends, writing RCA, or publishing known errors.
license: Apache-2.0
metadata:
  category: itsm
  version: "1.1"
---

# Problem Management

## Purpose
Find and remove the underlying causes of incidents, and reduce the impact of incidents that can't be prevented, through workarounds and known errors.

## Data model
- Table `problem` extends `task`. Key fields: problem_statement / short_description, cmdb_ci, service, category, impact, urgency, priority, assignment_group, cause_notes (root cause), fix_notes, workaround, known_error, first_reported_by_task, related incidents (via `incident.problem_id`).
- **State values** (OOB, newer model): 101 New, 102 Assess, 103 Root Cause Analysis, 104 Fix in Progress, 106 Resolved, 107 Closed.
- Problem tasks (`problem_task`) for RCA or fix activities.

## Rules
1. Create problems for: major incidents (always), recurring incidents on the same CI/service, incidents resolved without a known cause, and trends from reporting.
2. **Link incidents** with `incident.problem_id`; don't copy incident details into the problem.
3. Document a **workaround** as soon as one exists and mark the problem as a **known error** - publish it to the known error KB so the service desk can use it.
4. Record **root cause** in cause notes using a method (5 Whys, Fishbone/Ishikawa, Kepner-Tregoe); separate *symptom*, *trigger* and *root cause*.
5. Permanent fixes go through **Change Management** - link the change to the problem.
6. Close a problem only after the fix is verified (no recurrence over an agreed period) or the business accepts the risk.
7. Problem ownership: one problem manager or coordinator per problem; RCA tasks assigned to technical groups.
8. Review open problems regularly; age and recurrence count drive priority.

## RCA write-up template
- **Problem statement:** what, where, since when, how many incidents.
- **Impact:** services, users, duration.
- **Timeline:** key events.
- **Root cause:** the condition that, if removed, prevents recurrence.
- **Contributing factors.**
- **Workaround.**
- **Permanent fix and change number.**
- **Preventive actions** with owners and dates.

## Automation ideas (safe)
- Cluster recent incidents by CI and description to propose candidate problems.
- Draft RCA hypotheses from linked incident notes - presented as hypotheses for engineers to confirm.
- Draft known error articles from the workaround.

## Anti-patterns
- Problems created and left in New forever.
- RCA that names a person ("human error") instead of the process/condition.
- Resolving incidents with "see problem" and no workaround.

## Review checklist
- [ ] Incidents linked via problem_id
- [ ] Workaround + known error published early
- [ ] Root cause method used and documented
- [ ] Fix linked to a change; verification before closure

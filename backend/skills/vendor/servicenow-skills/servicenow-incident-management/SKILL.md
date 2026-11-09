---
name: servicenow-incident-management
description: ServiceNow Incident Management process and configuration - incident table, state model, priority from impact and urgency, assignment, major incidents, resolution and closure, linking to problems and changes, and KPIs. Use when configuring or customizing incident behaviour, writing incident automation, triaging or routing incidents, or reviewing incident data quality.
license: Apache-2.0
metadata:
  category: itsm
  version: "1.1"
---

# Incident Management

## Purpose
Restore normal service as quickly as possible with minimum business impact. An incident is an unplanned interruption or degradation.

## Data model
- Table `incident` extends `task`. Key fields: number, caller_id, opened_by, contact_type, category/subcategory, cmdb_ci, business_service, impact, urgency, priority, assignment_group, assigned_to, state, hold_reason, close_code, close_notes, problem_id, rfc (change), caused_by (change), parent_incident.
- **State values** (OOB): 1 New, 2 In Progress, 3 On Hold, 6 Resolved, 7 Closed, 8 Canceled.
- **Priority** is calculated from impact × urgency through the priority data lookup (`dl_u_priority`); 1 = Critical … 5 = Planning.

## Rules
1. **Never set priority directly**; set impact and urgency and let the lookup calculate it. Change the matrix, not scripts.
2. Categorisation: keep categories few and stable (the OOB set, extended carefully). Use the CI and service fields for "what is broken", category for "what kind of issue".
3. Routing: use **assignment rules / data lookups** or a decision table by category, CI support group, or location - not hard-coded group sys_ids in scripts.
4. **Resolve requires** close code and close notes (enforce with a Data Policy or before Business Rule). Resolved incidents auto-close after a configured number of days.
5. On Hold requires a hold reason; *Awaiting caller* should pause the SLA (see SLA skill).
6. Link: recurring or unknown cause → **problem_id**; fix needs a change → **rfc**; caused by a change → **caused_by**.
7. **Major incidents:** use the Major Incident Management process (candidate → proposed → accepted), a communication plan and child incidents linked via parent_incident; don't escalate by raising priority alone.
8. Keep the caller informed via **additional comments** (customer-visible); internal detail in **work notes**.
9. Don't reopen closed incidents - raise a new one linked to the old.
10. Duplicates: link to the parent incident and resolve the child as duplicate.

## KPIs to report
- Mean time to resolve by priority, first-contact resolution, reassignment count, reopen rate, % with CI populated, SLA attainment, backlog age.

## Automation ideas (safe)
- Suggest category/group from description (suggest-only first, then auto-apply above a confidence threshold).
- Detect duplicates among recent open incidents on the same CI.
- Summarise long activity streams for handover.
- Recommend KB articles to the agent and caller.

## Anti-patterns
- Scripts setting `priority` directly.
- Reassignment ping-pong because groups are chosen by category alone.
- Closing incidents without close notes.
- Using incidents for service requests ("I need a laptop") - that's Request Management.

## Review checklist
- [ ] Impact/urgency drive priority
- [ ] Routing via rules/lookups
- [ ] Resolution fields enforced server-side
- [ ] Problem/change links used
- [ ] Customer vs internal comments separated

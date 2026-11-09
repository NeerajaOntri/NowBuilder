---
name: servicenow-change-management
description: ServiceNow Change Management - normal, standard and emergency changes, state model, risk assessment and conflict detection, approvals and CAB, change schedules, blackout and maintenance windows, standard change catalog, implementation, backout and test plans, and post-implementation review. Use when configuring change processes, automating risk or approvals, reviewing a change request, or reducing change-related incidents.
license: Apache-2.0
metadata:
  category: itsm
  version: "1.1"
---

# Change Management

## Purpose
Maximise successful changes by assessing risk, authorizing appropriately and scheduling to avoid conflicts.

## Data model
- Table `change_request` extends `task`; `change_task` for implementation steps; approvals in `sysapproval_approver`.
- **Types:** Normal (full assessment and approval), Standard (pre-approved, low risk, from templates), Emergency (expedited, retrospective review).
- **State values** (OOB): -5 New, -4 Assess, -3 Authorize, -2 Scheduled, -1 Implement, 0 Review, 3 Closed, 4 Canceled.
- Key fields: type, category, cmdb_ci, risk, impact, start_date, end_date, implementation_plan, backout_plan, test_plan, justification, risk_impact_analysis, conflict_status, close_code.

## Rules
1. **Choose the type honestly.** Repeatable low-risk work → Standard change templates (managed in the Standard Change Catalog, reviewed periodically). Emergency only for restoring service or urgent security fixes.
2. Every Normal change needs: CI, planned window, implementation plan, **backout plan**, **test plan**, justification and risk/impact analysis. Enforce before moving to Assess.
3. **Risk** comes from the risk assessment (questionnaire) and/or risk conditions/risk intelligence - not a free choice. Higher risk → more approval levels.
4. **Conflict detection:** run it on the CI and window; respect **blackout** and **maintenance schedules**; resolve conflicts before Authorize.
5. Approvals: use approval policies / decision tables by risk and type; CAB reviews only high-risk or high-impact normals, using CAB Workbench agendas.
6. Implement only inside the approved window; extending the window needs re-approval.
7. Close with an accurate close code (successful / successful with issues / unsuccessful) and run a **PIR** (post-implementation review) for unsuccessful and emergency changes.
8. Link incidents caused by a change via `incident.caused_by`; track change success rate per group and CI.
9. Automate standard changes from pipelines (DevOps Change Velocity) where available, but keep the evidence (tests, approvals) attached.

## Risk review checklist for a change
- [ ] Backout plan concrete (steps, time to back out, decision point)
- [ ] Test plan with pre- and post-checks
- [ ] Window avoids blackout; no overlapping changes on same CI or dependent services
- [ ] CI has had recent incidents? Higher risk
- [ ] Implementer and approver are different people
- [ ] Communication to affected users planned

## Automation ideas (safe)
- AI risk advisory: score and list plan gaps, conflicts, recent incidents on the CI - posted as a work note; humans approve.
- Suggest standard change templates for repeated normal changes.

## Anti-patterns
- "N/A" backout plans.
- Everything raised as Emergency to skip CAB.
- AI or scripts moving changes to Authorized or Scheduled without human approval.

## Review checklist
- [ ] Correct type
- [ ] Plans complete, risk assessed
- [ ] Conflicts and blackout checked
- [ ] Approvals proportional to risk
- [ ] PIR for unsuccessful/emergency

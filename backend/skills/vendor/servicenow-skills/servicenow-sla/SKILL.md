---
name: servicenow-sla
description: ServiceNow Service Level Management - SLA, OLA and underpinning contract definitions (contract_sla), task SLA records (task_sla), start, pause, stop, cancel and reset conditions, schedules and time zones, retroactive start, breach and warning notifications via SLA flows, repair, and reporting. Use when defining or debugging SLAs, explaining why an SLA breached or paused, or building breach-risk automation.
license: Apache-2.0
metadata:
  category: itsm
  version: "1.1"
---

# SLA (Service Level Management)

## Data model
- **SLA Definition** `contract_sla`: type (SLA / OLA / Underpinning contract), table (incident, sc_req_item, sc_task, case...), duration or relative duration, **schedule**, timezone source, start/pause/stop/reset/cancel conditions, flow (SLA workflow/flow for notifications).
- **Task SLA** `task_sla`: one per definition attached to a task. Key fields: stage (in_progress, paused, completed, cancelled, breached), has_breached, planned_end_time, business_percentage, percentage, business_time_left, time_left.
- Engine re-evaluates SLAs whenever the task is updated.

## Rules
1. Define **what is measured**: response (assigned or first touch) and resolution are separate definitions.
2. **Conditions:**
   - Start: when the clock should start (e.g. priority = 1 and active).
   - Pause: waiting on the customer / vendor (state = On Hold and hold_reason = Awaiting caller).
   - Stop: goal achieved (state = Resolved).
   - Cancel / Reset: what happens when priority changes - decide explicitly (commonly cancel and start the new priority's SLA, with *retroactive start* so the clock counts from the original creation).
3. Use **schedules** (business hours, holidays) and the correct **timezone source** (caller, location, SLA definition).
4. Keep conditions simple and on fields that change via the normal process; avoid scripted conditions.
5. Notifications at 50/75/100% via the SLA **flow** (or legacy workflow); notify the assignee at warning, manager at breach.
6. After changing definitions, use **Repair SLAs** on affected tasks (in a controlled window) instead of hand-editing task_sla.
7. OLAs for internal group targets; underpinning contracts for vendors - separate definitions, separate reporting.
8. Report attainment from task_sla (has_breached = false / total completed) by definition, priority, group, month.

## Debugging "why did the SLA breach / not pause"
1. Open the task's SLA related list → timeline/history.
2. Compare the task's field values over time (audit history) with the definition's conditions.
3. Check the schedule and timezone; check whether retroactive start or reset applied.
4. Check whether the condition fields were set by an import/API that skips the expected state.

## Automation ideas (safe)
- Breach-risk list: active task_sla with business_percentage above a threshold → summarise the task and suggest next action as a work note.
- Predict breach from queue age and group throughput.

## Anti-patterns
- One SLA for all priorities with scripted durations.
- Pausing SLAs on generic "On Hold" without a reason.
- Editing task_sla records manually.

## Review checklist
- [ ] Response and resolution defined separately
- [ ] Pause/stop/reset rules explicit; retroactive start decided
- [ ] Schedule and timezone correct
- [ ] Warning and breach notifications
- [ ] Repair used after definition changes

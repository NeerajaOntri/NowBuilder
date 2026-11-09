---
name: servicenow-events-scheduled-jobs
description: ServiceNow events (event registry, gs.eventQueue, script actions, event-driven notifications), scheduled jobs (Scheduled Script Execution, sysauto_script, run types, batching) and system properties for settings. Use when something should happen on a schedule, when work should be decoupled from a save with an event, or when a value should be configurable.
license: Apache-2.0
metadata:
  category: scripting
  version: "1.1"
---

# Events, scheduled jobs and system properties

## Events
- Register an event in **Event Registry** (`sysevent_register`: `event_name`, `table`, `fired_by`,
  `description`, `queue`). Unregistered events are still queued but can't be picked in notifications.
- Fire it from server script: `gs.eventQueue(name, record, parm1, parm2[, queue])`, e.g.
  `gs.eventQueue('incident.p1.escalated', current, current.getValue('assignment_group'), '');`.
  `gs.eventQueueScheduled(name, record, parm1, parm2, expiration)` fires it at a GlideDateTime.
- Events are processed asynchronously from `sysevent` by the event processor.
- React with:
  - a **notification** whose *Send when* is *Event is fired* (`generation_type` event, `event_name`);
    recipients can be `parm1` / `parm2` ("Event parm 1 contains recipient");
  - a **script action** (`sysevent_script_action`: `name`, `event_name`, `order`, `condition_script`,
    `script`, `active`). In it, `current` is the event record and `event.parm1` / `event.parm2` hold
    the parameters. It runs in the background, so a slow call doesn't hold the user's save.
- Naming: lowercase dot.notation `<table>.<what happened>` (`incident.p1.escalated`); scoped apps prefix
  the scope.

## Scheduled jobs
- *Scheduled Script Execution* records live in `sysauto_script`: `name`, `active`, `run_type` (daily,
  weekly, monthly, periodically, once, on_demand), `run_time` (time of day, stored as
  1970-01-01 HH:MM:SS), `run_dayofweek` (weekly, 1 = Monday … 7 = Sunday), `run_dayofmonth` (monthly),
  `run_period` (periodically, a duration), `conditional` + `condition`, `run_as`, `script`.
- Run outside business hours; process in batches (`setLimit`) so a backlog is worked off over several
  runs; make the job safe to run twice (re-check the condition per record); log one summary line.
- Logic longer than a few lines goes in a script include the job calls.
- `gs.executeNow(job)` runs a job immediately (used by *Execute Now*); test on sub-production first.
- A flow with a *Daily / Weekly / Repeat* trigger is the no-code alternative for record work.

## System properties
- `sys_properties`: `name`, `value`, `type` (string, integer, boolean, choicelist, …), `description`.
- Read with a default: `gs.getProperty('incident.autoclose.days', '7')`; parse numbers with `parseInt`.
- Put thresholds, switches, URLs and lists in properties, not in scripts. Secrets belong in
  credential records / Connection & Credential aliases, never in a plain property.

## Anti-patterns
- Doing slow or external work in a before/after business rule instead of firing an event.
- A scheduled job that loops over every incident with no limit.
- Hard-coded day counts, group names or email addresses in scripts.

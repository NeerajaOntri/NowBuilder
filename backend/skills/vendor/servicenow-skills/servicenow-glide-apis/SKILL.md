---
name: servicenow-glide-apis
description: Correct and efficient use of ServiceNow Glide APIs - GlideRecord, GlideRecordSecure, GlideAggregate, GlideQuery, GlideSystem (gs), GlideDateTime, GlideDuration, GlideSysAttachment and client-side GlideForm, GlideUser and GlideAjax. Use when querying or updating records in script, counting, working with dates, attachments, or choosing between Glide APIs.
license: Apache-2.0
metadata:
  category: scripting
  version: "1.1"
---

# Glide APIs

## When to use
- Any script that reads, counts, inserts, updates or deletes records.
- Date/time maths, attachments, system info.
- Choosing GlideRecord vs GlideQuery vs GlideAggregate.

## Choosing the API
| Need | Use |
|---|---|
| Read/update records, all platforms | `GlideRecord` |
| Same, but enforce the user's ACLs | `GlideRecordSecure` |
| Count / sum / group | `GlideAggregate` (never loop to count) |
| Modern, fluent, fails loudly on bad fields | `GlideQuery` (scoped and global, newer releases) |
| Logging, properties, user, events | `gs` (GlideSystem) |
| Dates and durations in a timezone | `GlideDateTime`, `GlideDuration`, `GlideSchedule` |
| Attachments | `GlideSysAttachment` |
| Client form | `g_form`, `g_user`, `GlideAjax` |

## Rules - GlideRecord
1. Filter in the database: `addQuery`, `addEncodedQuery`, `addActiveQuery`. Never query everything and filter in JS.
2. **Limit:** `setLimit(n)` when you need n rows; `get()` for one record by sys_id or unique field.
3. Only `query()` once; check `if (gr.next())` / `while (gr.next())`.
4. Read with `getValue()` / `getDisplayValue()`; write with `setValue()`.
5. `update()` inside a Business Rule on the same record causes recursion - see business rules skill.
6. `updateMultiple()` / `deleteMultiple()` skip some per-record logic and are irreversible at scale: test on a small encoded query first and log the count.
7. `setWorkflow(false)` suppresses Business Rules, notifications and audit-driving engines - only for controlled data fixes, documented. `autoSysFields(false)` likewise.
8. Prefer `GlideRecordSecure` (or `canRead()` checks) in code that serves a user (portal, REST, client-callable).
9. Build encoded queries with the list filter, then *Copy query*, instead of hand-typing.

## Examples
```javascript
// Count open P1 incidents per group - GlideAggregate, not a loop
var ga = new GlideAggregate('incident');
ga.addEncodedQuery('active=true^priority=1');
ga.addAggregate('COUNT');
ga.groupBy('assignment_group');
ga.query();
while (ga.next()) {
    gs.info('{0}: {1}', ga.assignment_group.getDisplayValue(), ga.getAggregate('COUNT'));
}

// GlideQuery: fetch fields as plain objects
var openP1 = new GlideQuery('incident')
    .where('active', true)
    .where('priority', 1)
    .select('number', 'short_description', 'assignment_group$DISPLAY')
    .limit(50)
    .toArray(50);

// Dates: add 3 business days using a schedule
var gdt = new GlideDateTime();
var sched = new GlideSchedule('<schedule sys_id from a property>');
var due = sched.add(gdt, new GlideDuration(3 * 9 * 60 * 60 * 1000)); // 3 x 9h days
```

## Rules - GlideSystem and dates
- `gs.getProperty(name, default)`, `gs.getUserID()`, `gs.hasRole()`, `gs.getUser().isMemberOf(groupId)`.
- `gs.eventQueue('acme.ai.suggested', current, parm1, parm2)   // the event must be registered in sysevent_register` to decouple notifications and async work.
- Store and compare dates as `GlideDateTime` (UTC internally); use `getDisplayValue()` for the user's timezone. Never parse date strings by hand.
- Use `GlideSchedule` for business-hours maths (SLAs, due dates).

## Client-side
- `g_form.getValue/setValue/setMandatory/setDisplay/addInfoMessage/showFieldMsg`.
- `g_user.hasRole()`, `g_user.userID`.
- Server data: **async** `GlideAjax` with `getXMLAnswer(callback)`; never `getXMLWait()`; never client GlideRecord.

## Anti-patterns
- Counting with `while (gr.next()) count++`.
- `gr.query()` with no conditions on task/incident.
- `new GlideRecord('sys_user')` in a loop over incidents.
- String-built date maths: `'2026-10-' + day`.

## Review checklist
- [ ] Right API for the job; aggregates for counts
- [ ] Database-side filters and limits
- [ ] Secure variant where users are served
- [ ] setWorkflow(false)/bulk ops justified and tested
- [ ] Dates via GlideDateTime/GlideSchedule

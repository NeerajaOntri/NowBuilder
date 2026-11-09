---
name: servicenow-business-rules
description: Writing ServiceNow Business Rules correctly - choosing before, after, async, display or query timing, conditions, current and previous, aborting saves, avoiding current.update() recursion, g_scratchpad, and performance. Use when adding server-side logic that runs on insert, update, delete, query or form display, or reviewing an existing Business Rule.
license: Apache-2.0
metadata:
  category: scripting
  version: "1.1"
---

# Business Rules

## When to use
- Server logic that must run when a record is displayed, queried, inserted, updated or deleted - whatever the source (form, list edit, import, API, flow).

## Choosing *When*
| When | Runs | Use for | Don't |
|---|---|---|---|
| **before** | Before the DB write, same transaction | Set/validate fields on `current`; abort the save | Call `current.update()`; update other records (prefer after) |
| **after** | After the write, same transaction | Update related records; create child records | Change `current` fields (needs another update) |
| **async** | Later, in a scheduler worker | Integrations, REST calls, heavy work, notifications needing the committed record | Need `previous` (it is not available) |
| **display** | When a form loads | Fill `g_scratchpad` for client scripts | Write data |
| **before query** (`before` + *Query* ticked) | Before a query on the table | Row-level restriction (e.g. users see only their company's records) | Heavy logic - it runs on every query |

## Rules
1. **Put the filter in the Condition field** (or the condition builder) - not an `if` at the top of the script. The engine skips the script entirely when the condition is false.
2. Use the narrowest triggers: tick only the operations needed (insert/update/delete/query) and set a precise condition such as `current.state.changesTo(6)`.
3. **Never `current.update()` in a before or after rule on the same table.** In *before*, just set fields; in *after*, if truly necessary, use a separate mechanism (async rule, event, flow) rather than re-updating.
4. Use `previous` to detect change in before/after: `current.priority.changes()`, `changesTo()`, `changesFrom()`.
5. **Abort** invalid saves in *before* (it has no effect after the write): `gs.addErrorMessage('Resolution notes are required'); current.setAbortAction(true);`.
6. Long-running or external work (REST, heavy queries) → **async**. Never make a synchronous outbound call from a before/after rule.
7. Display rules pass data to the client: `g_scratchpad.isVip = current.caller_id.vip == true;` - avoids GlideAjax round-trips on load.
8. Keep the script a few lines: delegate to a **Script Include**.
9. Use **Order** deliberately (default 100). Document dependencies between rules.
10. Avoid global Business Rules (table = Global) - they load on every transaction.
11. Prefer **Flows** for multi-step, business-owned processes; Business Rules for fast, technical, record-level logic.

## The record (sys_script)
| Field | Holds |
|---|---|
| `name` | What it does, in words |
| `collection` | The table (incident, change_request…) - never Global |
| `when` | `before`, `after`, `async` or `display`. A *query* rule is `before` with `action_query=true` |
| `order` | Number, default 100 |
| `action_insert` / `action_update` / `action_delete` / `action_query` | Which operations run it |
| `filter_condition` | Condition builder (encoded query), e.g. `priority=1^active=true` |
| `condition` | Script condition, e.g. `current.state.changesTo(6)` |
| `advanced` | `true` for any rule with a script (the script only runs on advanced rules) |
| `script` | The IIFE below |
| `active` | true |

## Examples
```javascript
// BEFORE update on incident. Condition: current.state.changesTo(6)  (Resolved)
(function executeRule(current, previous) {
    if (!current.close_notes.nil()) return;
    gs.addErrorMessage(gs.getMessage('Add resolution notes before resolving.'));
    current.setAbortAction(true);
})(current, previous);

// ASYNC insert on incident. Condition: current.assignment_group.nil()
(function executeRule(current, previous) {
    new AIClient().triageIncident(current.getUniqueValue());
})(current, previous);

// DISPLAY on incident
(function executeRule(current, previous) {
    g_scratchpad.callerIsVip = current.caller_id.vip == true;
})(current, previous);
```

## Anti-patterns
- `if (current.state == 6) { ... }` inside the script with an empty Condition field.
- `current.update()` in a before rule (double save, recursion, duplicate audit).
- RESTMessageV2 `execute()` in an after rule blocking the agent's save.
- GlideRecord queries in a query Business Rule.
- Several rules on the same table doing overlapping things with default order 100.

## Review checklist
- [ ] Correct *When*; operations ticked narrowly
- [ ] Condition field used
- [ ] No current.update() recursion
- [ ] External calls async; errors caught
- [ ] Logic delegated to Script Include
- [ ] Order and interactions documented

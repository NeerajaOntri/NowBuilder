---
name: servicenow-javascript
description: Writing JavaScript that runs correctly on ServiceNow - server-side Rhino engine, ES5 in global vs newer ECMAScript in scoped apps, GlideElement pitfalls, IIFE wrapping, logging, error handling and performance basics. Use whenever writing or reviewing any ServiceNow server or client script, background script, or fixing a bug where values look wrong or all the same.
license: Apache-2.0
metadata:
  category: scripting
  version: "1.1"
---

# JavaScript on ServiceNow

## When to use
- Writing any server script (Business Rule, Script Include, Scheduled Job, Fix Script, Flow script step, Scripted REST) or client script.
- Debugging values that are `[object GlideRecord]`, all identical in an array, or comparisons that fail.

## Key facts
- Server-side code runs on Mozilla **Rhino** inside the platform (Java-backed). Client-side code runs in the user's browser.
- **Global scope:** write ES5-compatible code (`var`, `function`, no arrow functions, no template literals) unless you have confirmed the instance's engine mode.
- **Scoped apps:** since Tokyo, an application can run in **ECMAScript 2021 (ES12)** mode (the *JavaScript Mode* field on the application record), allowing `let`, `const`, arrow functions, template literals, classes and destructuring. Confirm the app's mode before using them; client scripts run in the browser and are not affected by it.
- Field access on a GlideRecord returns a **GlideElement**, not a string: `gr.short_description` is an object.
- Client and server are different worlds: no GlideRecord in modern client code, no `g_form` on the server.

## Rules
1. **Get values explicitly:** `gr.getValue('state')` (string or null) or `gr.state.toString()`. Use `getDisplayValue('assigned_to')` for labels.
2. Never push a GlideElement into an array or object - you'll store a reference that changes as the loop moves:
   ```javascript
   ids.push(gr.getUniqueValue());     // correct
   ids.push(gr.sys_id);               // BUG: every entry ends up the same
   ```
3. Compare as strings: `if (gr.getValue('state') == '6')`; `===` against a GlideElement is always false.
4. **Wrap Business Rule / background code in an IIFE** (the BR template already does) so variables don't leak into the global namespace.
5. Use `var` + `function` in global scope. Never rely on hoisting tricks.
6. **Logging:** `gs.info('[AI] triage {0} -> {1}', number, group)`; use `gs.debug` for noisy output. `gs.log` is not available in scoped apps. Don't log PII or secrets.
7. **Errors:** wrap integration and parsing code in `try/catch`; log with context; fail safely (don't block the user's save for a non-critical failure).
8. Parse JSON defensively: `var data; try { data = JSON.parse(body); } catch (e) { gs.error(...); return; }`.
9. Don't use `eval`, `new Function`, or `GlideEvaluator` on untrusted input.
10. Avoid nested GlideRecord queries inside loops (N+1). Query once with `IN` or use GlideAggregate.
11. Keep scripts short; move logic into a **Script Include** with a name and unit-testable methods.

## Example: safe server function
```javascript
(function executeRule(current, previous) {
    try {
        var groupId = current.getValue('assignment_group');
        if (!groupId) return;
        var helper = new TriageHelper();
        var count = helper.openCountForGroup(groupId);
        gs.debug('[AI] {0} open for group {1}', count, groupId);
    } catch (e) {
        gs.error('[AI] triage BR failed for {0}: {1}', current.getValue('number'), e.message);
    }
})(current, previous);
```

## Anti-patterns
- `gr.sys_id` pushed into arrays; `gr.state == 6` compared to a number without converting.
- Arrow functions in global Business Rules.
- `gs.log` in a scoped app; logging full records or user emails.
- 200-line Business Rule scripts with no functions.

## Review checklist
- [ ] Values read with getValue/toString/getDisplayValue
- [ ] Syntax matches the scope's JavaScript mode
- [ ] IIFE wrapping, no globals
- [ ] try/catch around integrations and parsing
- [ ] No PII in logs; no eval
- [ ] Logic in Script Includes

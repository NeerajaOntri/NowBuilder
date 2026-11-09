---
name: servicenow-client-scripts
description: Writing ServiceNow Client Scripts (onLoad, onChange, onSubmit, onCellEdit) and catalog client scripts with g_form, g_user, g_scratchpad and asynchronous GlideAjax, including UI Type for Workspace and Service Portal compatibility. Use when adding browser-side form behaviour, field validation, or dynamic form changes, or reviewing a slow or broken form.
license: Apache-2.0
metadata:
  category: scripting
  version: "1.1"
---

# Client Scripts

## When to use
- Form behaviour that a UI Policy cannot express: computed values, dependent defaults, confirmation prompts, async lookups.
- Validation feedback before submit (server must still enforce).

## Types
| Type | Signature | Use |
|---|---|---|
| onLoad | `function onLoad()` | One-time form setup |
| onChange | `function onChange(control, oldValue, newValue, isLoading, isTemplate)` | React to a field change |
| onSubmit | `function onSubmit()` | Last check; `return false` cancels |
| onCellEdit | `function onCellEdit(sysIDs, table, oldValues, newValue, callback)` | List editing; call `callback(true/false)` |

## The record (sys_script_client)
`name`, `table`, `type` (onLoad / onChange / onSubmit / onCellEdit), `field_name` (onChange and onCellEdit only), `ui_type` (`0` Desktop, `1` Mobile / Service Portal, `10` All), `isolate_script` (keep `true`), `active`, `script`, `description`. The function in the script must match `type`.

## Rules
1. **Try a UI Policy first** for mandatory/visible/read-only. Use a Client Script only for logic.
2. In onChange, **exit early on load and empty values**:
   ```javascript
   if (isLoading || newValue === '') return;
   ```
3. Server data: **asynchronous GlideAjax** with `getXMLAnswer(cb)`. Never `getXMLWait()`, never client-side `GlideRecord`, never `g_form.getReference()` without a callback.
4. Data known at load time → **Display Business Rule + g_scratchpad**, not a GlideAjax call in onLoad.
5. Use `g_form` APIs only - **no DOM manipulation** (`document.getElementById`, jQuery). DOM code breaks in Workspace, Service Portal, and upgrades. Leave *Isolate script* checked.
6. Set **UI Type** to *All* when the script must work in Service Portal / Workspace / mobile, and test there.
7. Never rely on a client script for security or data integrity; enforce with ACLs and Data Policies / Business Rules.
8. onSubmit: keep it synchronous and quick; it cannot wait for GlideAjax. Validate with data already on the form or pre-loaded in g_scratchpad.
9. Use `g_form.showFieldMsg` / `addInfoMessage` for feedback; `getMessage()` for translatable text.
10. Minimize the count of scripts per table; each adds load time.

## Example: async lookup with GlideAjax
```javascript
// onChange of short_description on incident (UI Type: All)
function onChange(control, oldValue, newValue, isLoading) {
    if (isLoading || newValue === '' || newValue.length < 15) return;
    var ga = new GlideAjax('AIAjax')   // global include: its name; scoped: 'x_vendor_app.AIAjax';
    ga.addParam('sysparm_name', 'suggestCategory');
    ga.addParam('sysparm_text', newValue);
    ga.getXMLAnswer(function (answer) {
        if (!answer) return;
        var s = JSON.parse(answer);
        g_form.hideFieldMsg('category', true);
        g_form.showFieldMsg('category', 'AI suggests: ' + s.category + ' (' + Math.round(s.confidence * 100) + '%)', 'info');
    });
}
```

## Anti-patterns
- `var gr = new GlideRecord('sys_user'); gr.get(id);` in a client script (synchronous, slow, blocked in portals).
- `getXMLWait()` freezing the browser.
- onChange scripts that run on load and overwrite values the user saved.
- Hiding fields as a security measure.

## Review checklist
- [ ] UI Policy considered first
- [ ] isLoading/empty guard
- [ ] Only async GlideAjax; scratchpad for load-time data
- [ ] No DOM, isolate script on, UI Type set and tested
- [ ] Server-side enforcement exists

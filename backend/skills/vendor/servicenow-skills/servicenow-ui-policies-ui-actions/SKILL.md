---
name: servicenow-ui-policies-ui-actions
description: Configuring ServiceNow UI Policies, Data Policies and UI Actions - making fields mandatory, visible or read-only without code, enforcing rules server-side, and adding form buttons, links, context menu items and list actions with client, server or combined client-plus-server scripts. Use when changing field behaviour on forms or adding a button or action to a form or list.
license: Apache-2.0
metadata:
  category: scripting
  version: "1.1"
---

# UI Policies, Data Policies and UI Actions

## UI Policies
**Use for:** mandatory, visible, read-only, and clearing values based on conditions - no script needed.

Rules:
1. Build the condition with the condition builder; tick **On load** if it must apply when the form opens; keep **Reverse if false** on so the policy undoes itself.
2. Use UI Policy Actions (field + mandatory/visible/read only) rather than the advanced script.
3. Set **Order** when two policies touch the same field; higher order runs later and wins.
4. Remember UI Policies run only in the browser. Pair them with a **Data Policy** when the rule must hold for imports, APIs and list edits.
5. Don't make a field read-only and mandatory at the same time with an empty value - users can't save.
6. Catalog UI Policies apply to variables; set *Applies on* (catalog item view, RITM, catalog task) explicitly.

Records: `sys_ui_policy` (`short_description`, `table`, `conditions` encoded query, `on_load`, `reverse_if_false`, `run_scripts`, `order`, `global` = all views, `active`) and one `sys_ui_policy_action` per field (`ui_policy`, `table`, `field`, and `mandatory` / `visible` / `disabled` each `true`, `false` or `ignore`; `disabled` = read only).

## Data Policies
- Server-side mandatory/read-only that applies to every channel. Can be converted from a UI Policy (*Convert this to Data Policy*).
- Use for data integrity rules ("close code required when resolved").

## UI Actions
**Use for:** buttons, links, context-menu items and list choices that perform an action.

| Field | Guidance |
|---|---|
| Action name | Unique per table; needed for client+server pattern |
| Show insert / Show update | Tick only where it makes sense |
| Condition | Server-side, evaluated per record: `current.active == true && gs.hasRole('itil')` |
| Roles | Restrict visibility (in addition to the condition) |
| Client | Tick only if `onclick` client code is needed |
| Form button / link / context menu / List choice | Choose the narrowest surface |

Rules:
1. Always set a **condition** and **roles**; a button the user can't use shouldn't render.
2. Server-side UI Actions run as the user - ACLs still apply when using GlideRecordSecure.
3. End server actions with `action.setRedirectURL(current)` and a message so the user sees the outcome.
4. Long work (REST, AI calls) → queue an event or async job; don't block the click for many seconds.
5. Copy OOB UI Actions to change them; don't edit the originals.
6. Workspace/Next Experience needs the *Workspace* settings (form button / menu) ticked.

Record: `sys_ui_action` - `name` (label), `table`, `action_name`, `condition`, `form_button`, `form_link`, `form_context_menu`, `list_button`, `list_choice`, `show_insert`, `show_update`, `client`, `onclick`, `order`, `active`, `script`, `comments`.

## Example: client + server UI Action (confirm, then run on server)
```javascript
// Action name: x_ai_summarize ; Client: true ; Onclick: confirmSummarize()
function confirmSummarize() {
    if (!confirm(getMessage('Generate an AI summary into work notes?'))) return false;
    gsftSubmit(null, g_form.getFormElement(), 'x_ai_summarize'); // re-submit to run server part
}
if (typeof window == 'undefined') runServer();   // server side
function runServer() {
    gs.eventQueue('acme.ai.summarize_requested', current, current.getTableName());
    gs.addInfoMessage(gs.getMessage('AI summary requested; it will appear in Work notes shortly.'));
    action.setRedirectURL(current);
}
```

## Anti-patterns
- UI Policies with scripts that do what policy actions could.
- Mandatory-only-in-UI rules that imports bypass.
- UI Actions with no condition or roles.
- Synchronous REST calls in a UI Action's server script.

## Review checklist
- [ ] UI Policy before Client Script
- [ ] Data Policy where server enforcement needed
- [ ] UI Action condition + roles + narrow surface
- [ ] Redirect and user message
- [ ] Heavy work async

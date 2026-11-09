---
name: servicenow-configuration
description: No-code and low-code ServiceNow configuration - dictionary attributes and overrides, choice lists, system properties, form and list layouts, data lookups, data policies, notifications, scheduled jobs and the configure-versus-customize trade-off. Use when changing how the platform behaves without (or before) writing scripts, setting up notifications or properties, or reviewing a change for upgrade safety.
license: Apache-2.0
metadata:
  category: foundations
  version: "1.1"
---

# Configuration

## When to use
- A requirement can likely be met without scripting.
- Adding settings, choices, notifications, data lookups, scheduled jobs.
- Reviewing changes for upgrade impact.

## Tools and when to use each
| Tool | Table | Use for |
|---|---|---|
| Dictionary entry / attributes | sys_dictionary | Field type, max length, default value, mandatory/read-only everywhere, attributes like `ref_auto_completer`, `tree_picker` |
| Dictionary override | sys_dictionary_override | Different default/mandatory/reference qualifier on a child table (e.g. incident vs task) |
| Choice list | sys_choice | Closed value sets; values stable, labels translatable |
| System property | sys_properties | Settings, thresholds, endpoints, feature flags |
| Data lookup rules | dl_definition (e.g. dl_u_priority) | Set field values from a matrix (priority from impact × urgency) |
| Assignment rules / Assignment data lookups | sysrule_assignment | Route tasks to groups by condition |
| Data Policy | sys_data_policy2 | Mandatory/read-only enforced server-side, including imports and web services |
| Notification | sysevent_email_action | Email on record change or event; use templates and *Notification email scripts* for logic |
| Scheduled job | sysauto_script | Periodic server work; prefer a scheduled Flow if no script is needed |
| Template | sys_template | Prefill common records |

## Rules
1. **Try configuration first, script last.** Every script is code you must test, secure and upgrade.
2. Use **dictionary overrides** to change behaviour on one child table; don't change the parent `task` definition.
3. Put thresholds, endpoints, toggles and lists in **system properties**, read with `gs.getProperty('acme.ai.threshold', '0.85')` (always pass a default). Secrets use a property of type `password2` or, better, Connection & Credential aliases.
4. Use **data lookup rules** for matrices (priority, routing) instead of if/else scripts.
5. **Notifications:** trigger on an event (`gs.eventQueue`) or a clear condition; send to groups or fields (assigned_to, caller) not hard-coded emails; one notification per audience; include a link to the record; test with *Preview Notification*.
   Record fields (`sysevent_email_action`): `collection` (table; not `task` itself), `generation_type` (*Send when*: `engine` = record inserted or updated, `event` = event is fired, `triggered` = by a flow or script), `action_insert` / `action_update` (for `engine`), `event_name` (for `event`; register the event in `sysevent_register`), `condition`, `recipient_fields` (e.g. `caller_id,opened_by`), `recipient_users`, `recipient_groups`, `send_self`, `exclude_delegates`, `weight`, `subject`, `message_html` (`${number}`, `${URI_REF}` for the link), `content_type`, `active`.
6. **Scheduled jobs:** run outside peak hours, process in batches (`setLimit`), make them safe to re-run, and log a summary.
7. Changing an OOB configuration record (a notification, an assignment rule) creates a customization - copy it (*Insert and Stay*), deactivate the original, and change the copy when practical.
8. Document *why* in the record's description field.

## Example: property-driven threshold
```javascript
// System property acme.ai.auto_apply_threshold (type: decimal, default 0.85)
var threshold = parseFloat(gs.getProperty('acme.ai.auto_apply_threshold', '0.85'));
if (suggestion.confidence >= threshold) { /* apply */ }
```

## Anti-patterns
- Thresholds, emails or URLs hard-coded in scripts.
- Client scripts enforcing mandatory fields that imports and APIs bypass (use a Data Policy).
- Editing OOB notifications in place.
- A scheduled job that queries the whole incident table every minute.

## Review checklist
- [ ] Could this be done without a script?
- [ ] Settings in properties with defaults
- [ ] Server-side enforcement via Data Policy where required
- [ ] Notifications target roles/fields, are event-driven, previewed
- [ ] OOB records copied rather than edited

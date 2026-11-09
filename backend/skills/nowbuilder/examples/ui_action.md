# Example: UI action

**Request:** "Add an Escalate button on incident for itil users that makes it P1 and adds a work note."

```json
{"record": {"name": "Escalate", "table": "incident", "action_name": "escalate_incident",
            "condition": "current.active == true && current.priority != 1 && gs.hasRole('itil')",
            "form_button": "true", "form_link": "false", "list_button": "false", "client": "false",
            "onclick": "", "order": "100", "active": "true",
            "comments": "Raises impact and urgency to 1 (priority 1) and notes who escalated."},
 "script": "current.impact = 1;\ncurrent.urgency = 1;\ncurrent.work_notes = gs.getMessage('Escalated to priority 1 by {0}', gs.getUserDisplayName());\ncurrent.update();\ngs.addInfoMessage(gs.getMessage('Incident escalated to priority 1.'));\naction.setRedirectURL(current);"}
```

A server-side UI action script may call `current.update()` (it isn't a business rule). Priority comes
from impact and urgency, so set those rather than `priority`.

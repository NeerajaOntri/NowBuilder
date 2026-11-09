# Example: notification

**Request:** "Email the assignment group when a P1 incident is created."

```json
{"record": {"name": "P1 incident created - assignment group", "collection": "incident", "active": "true",
            "action_insert": "true", "action_update": "false", "event_name": "", "triggered_by_flow": "false",
            "condition": "priority=1", "recipient_fields": "assignment_group", "recipient_users": "",
            "recipient_groups": "", "subject": "P1 incident ${number}: ${short_description}",
            "message_html": "<p>A priority 1 incident was opened.</p><p>${number} - ${short_description}</p><p>Caller: ${caller_id}</p><p>${URI_REF}</p>",
            "weight": "0", "send_self": "false", "exclude_delegates": "false", "content_type": "text/html"}}
```

**Request:** "Tell the caller when their incident is resolved."

```json
{"record": {"name": "Incident resolved - caller", "collection": "incident", "active": "true",
            "action_insert": "false", "action_update": "true", "event_name": "", "triggered_by_flow": "false",
            "condition": "stateCHANGESTO6", "recipient_fields": "caller_id", "recipient_users": "",
            "recipient_groups": "", "subject": "Your incident ${number} has been resolved",
            "message_html": "<p>${number} - ${short_description} was resolved.</p><p>Resolution: ${close_notes}</p><p>${URI_REF}</p>",
            "weight": "0", "send_self": "false", "exclude_delegates": "false", "content_type": "text/html"}}
```

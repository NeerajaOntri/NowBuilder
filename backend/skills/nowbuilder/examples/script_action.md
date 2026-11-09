# Example: script action

**Request:** (reacting to `incident.p1.escalated`) "Add a work note on the incident when it fires."

```json
{"record": {"name": "Note P1 escalation", "event_name": "incident.p1.escalated", "order": "100",
            "condition_script": "", "active": "true"},
 "script": "(function () {\n    if (!current || !current.isValidRecord()) {\n        return;\n    }\n    current.work_notes = gs.getMessage('P1 escalation processed.');\n    current.update();\n})();"}
```

In a script action `current` is the event's record and `event.parm1` / `event.parm2` are the event
parameters. It runs asynchronously, so `current.update()` here is fine (it isn't a business rule).

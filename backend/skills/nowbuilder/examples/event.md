# Example: event registration

**Request:** "When a P1 incident is escalated, fire an event so other things can react."

```json
{"record": {"event_name": "incident.p1.escalated", "table": "incident",
            "fired_by": "Business rule: Fire P1 escalation event",
            "description": "Fired when an incident becomes priority 1. parm1 = assignment group sys_id."}}
```

Fire it from a business rule or UI action: `gs.eventQueue('incident.p1.escalated', current,
current.getValue('assignment_group'), '');`. React with a script action or a notification whose
`event_name` is this event.

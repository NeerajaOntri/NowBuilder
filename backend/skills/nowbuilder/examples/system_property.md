# Example: system property

**Request:** "Make the auto-close period configurable, default 7 days."

```json
{"record": {"name": "incident.autoclose.days", "value": "7", "type": "integer",
            "description": "Days an incident stays Resolved before the nightly job closes it. Whole number."}}
```

Read it with `gs.getProperty('incident.autoclose.days', '7')` - always with a default. Names are
lowercase dot.notation; never store secrets in a plain property.

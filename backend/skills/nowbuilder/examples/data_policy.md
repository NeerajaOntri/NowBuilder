# Example: data policy

**Request:** "Close notes must be filled in when an incident is resolved - also for imports and the API."

```json
{"record": {"short_description": "Close notes required on resolved incidents", "model_table": "incident",
            "conditions": "state=6", "apply_import_set": "true", "apply_soap": "true", "enforce_ui": "true",
            "inherit": "false", "active": "true"},
 "actions": [{"field": "close_notes", "mandatory": "true", "disabled": "ignore"},
             {"field": "close_code", "mandatory": "true", "disabled": "ignore"}]}
```

A data policy is enforced on the server (imports, web services, list edits); `enforce_ui` "true" also
applies it on forms, so a separate UI policy isn't needed for the same rule.

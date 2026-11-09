# Example: business rule

**Request:** "Don't let anyone resolve an incident without resolution notes."

```json
{"record": {"name": "Require resolution notes on resolve", "collection": "incident", "when": "before",
            "order": "100", "active": "true", "action_insert": "false", "action_update": "true",
            "action_delete": "false", "action_query": "false",
            "condition": "", "filter_condition": "stateCHANGESTO6",
            "description": "Stops an incident being resolved without close notes."},
 "script": "(function executeRule(current, previous /*null when async*/) {\n    if (!current.close_notes.nil()) {\n        return;\n    }\n    gs.addErrorMessage(gs.getMessage('Add resolution notes before resolving the incident.'));\n    current.setAbortAction(true);\n})(current, previous);"}
```

**Request:** "When a P1 incident is created, add a work note." (before rule: it sets a field on the record being saved)

```json
{"record": {"name": "Note new P1 incidents", "collection": "incident", "when": "before", "order": "100",
            "active": "true", "action_insert": "true", "action_update": "false", "action_delete": "false",
            "action_query": "false", "condition": "", "filter_condition": "priority=1",
            "description": "Adds a work note to new priority 1 incidents."},
 "script": "(function executeRule(current, previous /*null when async*/) {\n    current.work_notes = gs.getMessage('Priority 1 incident: the major incident checklist applies.');\n})(current, previous);"}
```

Patterns: setting a field on the record being saved → `before`, no `current.update()`; changing other
records → `after`; external calls → `async`; the filter goes in `filter_condition` (encoded query:
`priority=1`, `stateCHANGESTO6`, `assignment_groupISEMPTY`) or `condition` (script:
`current.priority.changesTo(1)`), never an `if` that wraps the whole script.

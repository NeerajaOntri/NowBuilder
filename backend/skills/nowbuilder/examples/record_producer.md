# Example: record producer

**Request:** "Let employees report a facilities problem from the portal; it should become an incident."

```json
{"record": {"name": "Report a facilities issue", "short_description": "Broken lights, heating, doors and more",
            "table_name": "incident", "sc_catalogs": "Service Catalog", "category": "", "active": "true"},
 "script": "current.short_description = 'Facilities: ' + producer.issue_summary;\ncurrent.description = producer.details;\ncurrent.category = 'facilities';\ncurrent.caller_id = gs.getUserID();",
 "variables": [
   {"name": "issue_summary", "question_text": "What's the problem?", "type": "single_line_text",
    "mandatory": "true", "order": "100", "reference": "", "help_text": ""},
   {"name": "details", "question_text": "Where is it, and anything else we should know?", "type": "multi_line_text",
    "mandatory": "false", "order": "200", "reference": "", "help_text": ""}]}
```

The producer inserts the record itself: set `current.<field>` from `producer.<variable>` and never call
`current.insert()`. Use field values that exist on the table (check the category choices).

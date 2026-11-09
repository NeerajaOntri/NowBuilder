# Example: UI policy

**Request:** "Make subcategory mandatory and show it when category is hardware."

```json
{"record": {"short_description": "Hardware incidents need a subcategory", "table": "incident",
            "conditions": "category=hardware", "on_load": "true", "reverse_if_false": "true",
            "run_scripts": "false", "active": "true"},
 "actions": [{"field": "subcategory", "mandatory": "true", "visible": "true", "disabled": "false"}]}
```

**Request:** "Make the description read-only once an incident is resolved."

```json
{"record": {"short_description": "Description read-only after resolve", "table": "incident",
            "conditions": "state=6^ORstate=7", "on_load": "true", "reverse_if_false": "true",
            "run_scripts": "false", "active": "true"},
 "actions": [{"field": "description", "mandatory": "ignore", "visible": "ignore", "disabled": "true"}]}
```

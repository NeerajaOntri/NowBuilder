# Example: catalog item

**Request:** "Add a catalog item so people can request a new laptop, with a justification and who it's for."

```json
{"record": {"name": "Request a new laptop", "short_description": "Order a standard laptop for yourself or a colleague",
            "description": "<p>Standard laptops ship within 5 working days.</p>",
            "sc_catalogs": "Service Catalog", "category": "Hardware", "active": "true"},
 "variables": [
   {"name": "requested_for", "question_text": "Who is the laptop for?", "type": "reference", "mandatory": "true",
    "order": "100", "reference": "sys_user", "help_text": ""},
   {"name": "business_justification", "question_text": "Why is it needed?", "type": "multi_line_text",
    "mandatory": "true", "order": "200", "reference": "", "help_text": "One or two sentences."},
   {"name": "needs_docking_station", "question_text": "Also need a docking station?", "type": "yes_no",
    "mandatory": "false", "order": "300", "reference": "", "help_text": ""}]}
```

Check the catalog and category titles exist (`query_instance_records` on `sc_catalog` / `sc_category`)
before using them. Fulfilment is a separate flow row (Service Catalog trigger) or the item's process engine.

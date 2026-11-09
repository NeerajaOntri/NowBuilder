# Example: field

**Reference field** (the vendor on a contract):
```json
{"record": {"name": "u_vendor_contract", "element": "u_vendor", "column_label": "Vendor",
            "internal_type": "reference", "max_length": "", "reference": "core_company", "choice": "",
            "mandatory": "true", "read_only": "false", "default_value": "", "active": "true"}}
```

**Currency field:**
```json
{"record": {"name": "u_vendor_contract", "element": "u_contract_value", "column_label": "Contract value",
            "internal_type": "currency", "max_length": "", "reference": "", "choice": "",
            "mandatory": "false", "read_only": "false", "default_value": "", "active": "true"}}
```

**Date field:**
```json
{"record": {"name": "u_vendor_contract", "element": "u_end_date", "column_label": "End date",
            "internal_type": "glide_date", "max_length": "", "reference": "", "choice": "",
            "mandatory": "false", "read_only": "false", "default_value": "", "active": "true"}}
```

**Choice field** (a string field with a choice list):
```json
{"record": {"name": "u_vendor_contract", "element": "u_contract_status", "column_label": "Contract status",
            "internal_type": "string", "max_length": "40", "reference": "", "choice": "1",
            "mandatory": "false", "read_only": "false", "default_value": "draft", "active": "true"},
 "choices": [{"value": "draft", "label": "Draft", "sequence": "100"},
             {"value": "active", "label": "Active", "sequence": "200"},
             {"value": "expired", "label": "Expired", "sequence": "300"}]}
```

**A field on an existing table** (incident):
```json
{"record": {"name": "incident", "element": "u_vip_caller", "column_label": "VIP caller",
            "internal_type": "boolean", "max_length": "", "reference": "", "choice": "",
            "mandatory": "false", "read_only": "false", "default_value": "false", "active": "true"}}
```

Rules: global field names start `u_`. Pick the narrowest type: reference (not string) for links to
records, glide_date / glide_date_time for dates, integer / decimal / currency for numbers, boolean for
yes/no, a string with a choice list for closed sets (stable lowercase values, readable labels),
journal_input for comment streams. Add a field to the child table that needs it (incident), never to
`task` itself. Don't add fields the parent table already has (task gives state, number, assignment).

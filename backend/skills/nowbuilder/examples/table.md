# Example: table (+ its fields)

**Request:** "Create a table to track vendor contracts: vendor, contract value, start and end dates,
and a status of draft, active or expired. Work on it gets assigned to people."

Plan rows: `c1` table, then one `field` row per column, each `"dependsOn": ["c1"]`. Work that is
assigned and has a state extends `task`, so the table gets number, assignment group, assigned to,
state, short description, work notes and SLAs for free - don't add those as fields.

```json
{"record": {"name": "u_vendor_contract", "label": "Vendor Contract", "super_class": "task",
            "is_extendable": "false"}}
```

A standalone reference table (no assignment, no state), e.g. a list of vendors:

```json
{"record": {"name": "u_vendor", "label": "Vendor", "super_class": "", "is_extendable": "false"}}
```

Rules: global names start `u_`; lowercase letters, digits, underscores. Extend `task` for work items,
a `cmdb_ci` class for configuration items, otherwise nothing. Never create a table that already
exists - add fields to it. Add an assumption that read/write ACLs for the right role are needed.

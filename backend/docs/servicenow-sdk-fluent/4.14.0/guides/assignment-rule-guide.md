Version: 4.14.0

# Assignment Rules

Guide for creating ServiceNow Assignment Rules using the Fluent API. Assignment rules automatically populate empty `assignment_group` or `assigned_to` fields on task or task-inherited tables after a record is saved to the database. Assignment rules do not run if these fields already have values. They execute after the insert or update operation completes.

## When to Use

### Table Eligibility (Required)

Assignment rules only work on tables that extend `task`. Any custom table whose parent or ancestor is `task` (directly or through inheritance) qualifies for assignment rules.

✅ Table extends task → Use Assignment Rules
❌ Table does NOT extend task → Use Business Rules instead

### Common Use Cases

Use assignment rules when you need to:

Automatic Team/User Assignment:

- Automatically assign tasks, incidents, changes, or problems to specific users or groups after save

- Populate assignment fields after records are saved to the database

- Route records based on field values (category, priority, location, VIP status, geography, department)

- Escalate critical/urgent items to senior staff or specialized teams

- Ensure records don't remain unassigned after creation

Workload Distribution:

- Implement round-robin assignment across team members

- Balance workload based on current assignments or availability

- Route to different teams based on time of day or business hours

Dynamic Assignment Logic:

- Use scripts to implement complex assignment rules

- Query related records to determine assignment

- Calculate assignment based on custom business logic

### OOB Task-Extended Tables

The following are examples of out-of-box tables that extend `task`. Any custom table that extends `task` or any of these tables can use assignment rules:

| OOB table | Label |
| `task` | Task (base) |
| `incident` | Incident |
| `change_request` | Change Request |
| `change_task` | Change Task |
| `problem` | Problem |
| `problem_task` | Problem Task |
| `sc_request` | Request |
| `sc_req_item` | Requested Item |
| `sc_task` | Catalog Task |
| `sn_si_incident` | Security Incident |
| `hr_case` | HR Case |
| `hr_task` | HR Task |
| `csm_order` | Consumer Order |

Example: If you create a custom table `u_security_task` that extends `sn_si_incident`, it can use assignment rules because `sn_si_incident` extends `task`.

### Critical Limitations

⚠️ Assignment rules run AFTER a record is saved to the database:

- They do NOT run during form interaction or while editing

- They do NOT run when a form first opens

- They execute only after the insert or update operation completes

- Alternative: If you need assignment on form load or during form interaction, use Client Script (onChange or onLoad) instead

⚠️ Assignment rules only populate EMPTY fields:

- If `assignment_group` or `assigned_to` already has a value, the rule will NOT execute

- They cannot override or reassign existing assignments

- Alternative: If you need to reassign or override existing values, use a Business Rule instead

## Assignment Rules vs Business Rules

Use Assignment Rules when:

- Primary goal is to assign records to users or groups after a record is saved (post-insert or post-update)

- Working with task or task-extended tables (incident, change, problem, etc.)

- Assignment logic is condition-based and relatively straightforward

- Assignment fields are empty (no existing assignment to override)

- You want to use the platform's built-in assignment engine

Use Business Rules when:

- You need complex logic beyond assignment (field updates, validations, integrations)

- You need precise control over timing (before/after/async/display)

- You need to work with tables that don't inherit from task

- You need to reassign or override existing assignments

- Assignment logic requires multiple GlideRecord queries to related tables

## Key Concepts

Assignment rules run after a record is saved (inserted or updated in the database) and automatically set `assigned_to` or `assignment_group` fields. They do not execute during form interaction, while creating a record, or when opening an existing record for editing — only after the save operation completes.

Important limitations:

- Assignment rules are only applicable to task or task-extended tables (incident, change_request, problem, sc_req_item, etc.)

- Assignment rules only fire when assignment fields are empty. If `assignment_group` or `assigned_to` already has a value, the rule will not execute. If you need to reassign or override existing assignments, use a Business Rule instead.

### Static assignment vs Script-based assignment

Static Assignment (Recommended for Simple Cases):

- Set `group` field to a specific group sys_id

- Set `user` field to a specific user sys_id

- No script needed

- Fast and simple

- Example: "All hardware incidents go to Hardware group"

Script-Based Assignment (For Complex Logic):

- Use `script` field to write JavaScript assignment logic

- Access current record via `current` variable

- Use `setDisplayValue()` for setting groups/users by name

- Example: Round-robin assignment, load balancing, conditional logic

Static vs Script-Based:

- Static: Set `group` or `user` field to a sys_id (simple, fast)

- Script-Based: Use `script` field for conditional logic, round-robin, etc.

## Instructions

Follow these steps to implement assignment rules:

- 
Verify table eligibility (CRITICAL): Confirm the table extends task (incident, change_request, problem, sc_req_item, change_task, sc_task, or custom task-inherited table). Assignment rules do NOT work on non-task tables. Always confirm the correct table name before writing the rule.

- 
Query existing assignment rules (if table exists): If the target table already exists on the instance, query for existing assignment rules to understand what order values are already in use and avoid conflicts or duplication. Use the query pattern: `table=<target_table>^active=true^ORDERBYorder`

- 
Define conditions: Specify when the rule should fire (category, priority, status, custom fields). Use the `condition` field with ServiceNow's encoded query syntax. Assignment rules evaluate conditions before executing scripts.

- 
Set match conditions: Set `match_conditions` to `'ALL'` (default) to require all conditions to match, or `'ANY'` to match if any condition is true.

- 
Determine assignment target: Decide on group vs user assignment or both. Groups are preferred for scalability and flexibility. If the group or user name is not explicitly provided, query the `sys_user_group` table (for groups) or `sys_user` table (for users) to get the correct name or label before proceeding.

- 
Validate group/user existence (CRITICAL): Query `sys_user_group` (for groups) or `sys_user` (for users) to confirm the target exists.

- If the query returns a match, use the sys_id from the result in the `group` or `user` field for static assignment.

- If the query returns NO match, STOP and inform the user that the group/user was not found on the instance. Query for similar names (e.g., partial match, case-insensitive) to help identify the correct record. If still not found, this is a blocker. Do NOT silently use setDisplayValue() as a workaround. Ask whether they want to: (a) create the group/user, (b) use a different existing group/user, or (c) proceed with a script-based setDisplayValue() approach (with the caveat that it will only work once the group/user is created).

- 
Write script if needed: For simple assignments (static group/user), set the group or user field directly using the sys_id obtained in the previous step. For moderately complex logic (round-robin, load balancing, conditional routing by category), use the `script` field with server-side JavaScript. If the logic is very complex (requires external API calls, multiple GlideRecord queries, aggregated data, or exceeds 8000 characters), use a business rule instead — assignment rules are designed for straightforward post-save routing.

- 
Choose between single vs. multiple assignment rules:

- Use a single script-based assignment rule when multiple assignment scenarios for the same table are closely related and differ only by one routing logic (for example, assigning incidents to different groups based on category or service offering).

- Use separate assignment rules with clear conditions when business requirements are independent and unrelated. Separate rules are often more maintainable and align better with ServiceNow's declarative configuration approach.

- See the Decision Guide below for detailed guidance on making this choice.

- 
Set execution order: Based on the existing assignment rules queried in step 2 (if applicable), set an appropriate `order` value to avoid conflicts. Lower numbers run first (e.g., order 10 runs before order 50, which runs before order 100). Default is 100. Use this to implement tiered assignment strategies:

- High priority rules (order 1-30): VIP callers, critical incidents, emergency changes

- Medium priority rules (order 40-70): Specialized routing based on specific conditions

- Default/catch-all rules (order 80-100): General assignment for unassigned records

- 
Configure metadata: Set `active: true` to enable the rule. Use clear, descriptive names that explain what the rule does (e.g., "Assign Hardware Incidents to Hardware Team"). Use `Now.ID["identifier"]` where the identifier is in kebab-case (lowercase with hyphens) and descriptively matches the rule's purpose. Examples: `Now.ID["hardware-incident-assignment"]`, `Now.ID["vip-caller-assignment"]`.

### Decision Guide: Single or Multiple Rules

Example User Prompts and Correct Interpretation:

PROMPT 1:

```
"Assign incidents based on issue type: hardware issues go to Hardware Team,
software issues go to Software Team, network issues go to Network Team."
```

ANALYSIS:

- Same decision field: issue type (category)

- Multiple branches of ONE routing logic

- Single rule avoids order-dependent fragility of multiple rules at the same order that all match the same record

- ACTION: Create ONE script-based assignment rule

PROMPT 2:

```
"Hardware incidents should go to Hardware Team.
Also, VIP callers should always go to VIP Support Team.
After hours, everything should go to 24/7 Support."
```

ANALYSIS:

- Different decision fields: category, caller_id.vip, time

- Three independent business requirements

- ACTION: Create THREE separate assignment rules with different order values

Validation Checklist:

Before generating assignment rules, check:

-  Count how many distinct decision fields are referenced

-  If only ONE field → likely ONE script-based rule

-  If multiple unrelated fields → likely multiple separate rules

-  Verify all targets are variations of the same routing strategy

## API Reference

Assignment rules use the generic `Record()` API with `table: "sysrule_assignment"`. There is no dedicated `AssignmentRule()` Fluent API.

### Table Schema

| Field | Type | Required | Description |
| `name` | `String` | Yes | Descriptive name for the rule (max 40 characters). |
| `table` | `TableName` | Yes | Target table (must extend task — restricted choice list). Default: `'incident'` . |
| `active` | `Boolean` | No | Whether the rule is active. Default: `true` . |
| `condition` | `String` | No | Encoded query against the table chosen in `table` (max 1000 characters). The trailing `^EQ` end-of-query marker is optional — see encoded-query-guide . |
| `match_conditions` | `String` | No | How multiple conditions are evaluated: `'ALL'` (all must match) or `'ANY'` (any matches). Default: `'ALL'` . |
| `group` | `string | Record<'sys_user_group'>` | No | sys_id of the assignment group or `Record` reference. Prefer over `user` for scalability. |
| `user` | `string | Record<'sys_user'>` | No | sys_id of the assigned user or `Record` reference. Use for individual assignment. |
| `script` | `String` | No | Server-side JavaScript (max 8000 characters). `current` is the saved record. Overrides `group` / `user` . |
| `order` | `Integer` | No | Execution order. Lower numbers run first. Default: `100` . |
| `description` | `String` | No | Description of the rule's purpose (max 4000 characters). |

### Condition Syntax

Encoded query syntax: `=` (equals), `!=` (not equal), `^` (AND), `^OR` (OR), `IN` (list), `ISEMPTY`, `ISNOTEMPTY`

```
category=hardware                        // Single condition (^EQ optional)
category=hardware^priority=1^EQ          // AND condition, with optional end-marker
stateIN1,2                               // IN list
```

### Script Patterns

The `script` field can reference external JavaScript files using `Now.include("path/to/file.js")` (recommended for maintainability) or contain inline JavaScript code using backticks. For complex scripts, use the two-file pattern: create a Fluent definition file (`.now.ts`) with `script: Now.include()` and a separate script file (`.js`) containing the JavaScript logic.

Common script patterns:

Setting assignment group by name:

```
current.assignment_group.setDisplayValue("Hardware Team");
```

Setting assignment user by sys_id:

```
current.setValue("assigned_to", "<sys_id_of_user>");
```

Conditional assignment by name:

```
if (current.priority == "1") {
  current.assignment_group.setDisplayValue("Critical Response Team");
} else {
  current.assignment_group.setDisplayValue("Standard Support");
}
```

## Examples

### Static Group Assignment

```
import { Record } from "@servicenow/sdk/core";

export const hardwareIncidentAssignment = Record({
  $id: Now.ID["hardware-incident-assignment"],
  table: "sysrule_assignment",
  data: {
    name: "Assign Hardware Incidents to Hardware Team",
    table: "incident",
    active: true,
    condition: "category=hardware^EQ",
    group: "<sys_id_of_hardware_group>",
    order: 100
  }
});
```

### Script-Based with Now.include

Fluent Definition:

```
import { Record } from "@servicenow/sdk/core";

export const categoryBasedAssignment = Record({
  $id: Now.ID["category-based-assignment"],
  table: "sysrule_assignment",
  data: {
    name: "Assign by Category",
    table: "incident",
    active: true,
    order: 100,
    script: Now.include("./category-based.js")
  }
});
```

Script File:

```
if (current.category == "Hardware")
  current.assignment_group.setDisplayValue("Hardware");
else if (current.category == "Software")
  current.assignment_group.setDisplayValue("Software");
else
  current.assignment_group.setDisplayValue("Service Desk");
```

### Execution Order Priority

```
// High priority (order 10) - runs first
import { Record } from "@servicenow/sdk/core";

export const vipAssignment = Record({
  $id: Now.ID["vip-assignment"],
  table: "sysrule_assignment",
  data: {
    name: "VIP Caller Assignment",
    table: "incident",
    condition: "caller_id.vip=true^EQ",
    group: "<vip_support_group_sys_id>",
    order: 10
  }
});

// Default (order 100) - runs last as catch-all
export const defaultAssignment = Record({
  $id: Now.ID["default-assignment"],
  table: "sysrule_assignment",
  data: {
    name: "Default Assignment",
    table: "incident",
    group: "<service_desk_sys_id>",
    order: 100
  }
});
```

### Round-Robin Assignment

```
import { Record } from "@servicenow/sdk/core";

export const roundRobinAssignment = Record({
  $id: Now.ID["round-robin-assignment"],
  table: "sysrule_assignment",
  data: {
    name: "Round-Robin Assignment",
    table: "incident",
    order: 100,
    script: Now.include("./round-robin.js")
  }
});
```

Script:

```
var gr = new GlideRecord("sys_user_grmember");
gr.addQuery("group.name", "Service Desk");
gr.addQuery("user.active", true);
gr.query();

var users = [];
var groupSysId = "";
while (gr.next()) {
  users.push(gr.user.sys_id.toString());
  if (!groupSysId) groupSysId = gr.group.sys_id.toString();
}

if (users.length > 0) {
  var incidentNum = parseInt(current.number.toString().replace(/[^0-9]/g, ""));
  current.setValue("assigned_to", users[incidentNum % users.length]);
  current.setValue("assignment_group", groupSysId);
}
```

### Script-Based Assignment Using sys_id (when group/user sys_id is available)

When you have the sys_id of the group or user, assign directly instead of using `setDisplayValue()`:

Fluent Definition (`src/fluent/assignment-rules/priority-based.now.ts`):

```
import { Record } from "@servicenow/sdk/core";

export const priorityBasedAssignment = Record({
  $id: Now.ID["priority-based-assignment"],
  table: "sysrule_assignment",
  data: {
    name: "Assign Incidents by Priority",
    table: "incident",
    active: true,
    match_conditions: "ALL",
    order: 100,
    script: Now.include("./priority-based.js")
  }
});
```

Script File (`priority-based.js`):

```
// Using setValue() with sys_id (faster and more reliable than setDisplayValue)
if (current.priority == "1") {
  current.setValue("assignment_group", "<sys_id_of_critical_response_team>");
  current.setValue("assigned_to", "<sys_id_of_john_doe>");
} else if (current.priority == "2") {
  current.setValue("assignment_group", "<sys_id_of_high_priority_team>");
} else {
  current.setValue("assignment_group", "<sys_id_of_standard_support>");
}
```

### Single Script vs Multiple Rules Pattern

Single script-based assignment (use when scenarios are related):

```
import { Record } from "@servicenow/sdk/core";

// All category-based routing in ONE rule with script
export const categoryRoutingRule = Record({
  $id: Now.ID["incident-category-routing"],
  table: "sysrule_assignment",
  data: {
    name: "Route Incidents by Category",
    table: "incident",
    active: true,
    order: 100,
    script: `
      if (current.category == "Hardware") {
        current.assignment_group.setDisplayValue("Hardware Team");
      } else if (current.category == "Software") {
        current.assignment_group.setDisplayValue("Software Team");
      } else if (current.category == "Network") {
        current.assignment_group.setDisplayValue("Network Team");
      } else {
        current.assignment_group.setDisplayValue("Service Desk");
      }
    `
  }
});
```

Multiple separate assignment rules (use when requirements are independent):

```
import { Record } from "@servicenow/sdk/core";

// Rule 1: VIP caller priority (independent business requirement)
export const vipAssignment = Record({
  $id: Now.ID["vip-caller-assignment"],
  table: "sysrule_assignment",
  data: {
    name: "VIP Caller Priority Assignment",
    table: "incident",
    active: true,
    condition: "caller_id.vip=true^EQ",
    group: "<vip_support_group_sys_id>",
    order: 10  // Runs first
  }
});

// Rule 2: Critical incidents (independent business requirement)
export const criticalIncidentAssignment = Record({
  $id: Now.ID["critical-incident-assignment"],
  table: "sysrule_assignment",
  data: {
    name: "Critical Incident Assignment",
    table: "incident",
    active: true,
    condition: "priority=1^state=1^EQ",
    group: "<critical_response_team_sys_id>",
    order: 20  // Runs after VIP rule
  }
});

// Rule 3: After-hours assignment (independent business requirement)
export const afterHoursAssignment = Record({
  $id: Now.ID["after-hours-assignment"],
  table: "sysrule_assignment",
  data: {
    name: "After Hours Assignment",
    table: "change_request",
    active: true,
    order: 30,
    script: `
      var now = new GlideDateTime();
      var hour = now.getHourLocalTime();
      if (hour < 8 || hour >= 18) {
        current.assignment_group.setDisplayValue("24/7 Support Team");
      }
    `
  }
});
```

When to use which approach:

- Single script: Category routing (all related to categorization), service offering routing (all related to services), location-based routing (all related to geography)

- Multiple rules: VIP handling + critical incidents + after-hours support (each is a distinct business requirement with different triggers and priorities)

## Avoidance

- Never use on non-task tables — Use business rules instead

- Never expect to run on unsaved changes on a form — Runs after form is saved

- When using `script`, avoid setting `group`/`user` — `script` silently overrides static assignments; setting both is confusing and the static values are ignored

- Never skip the instance query (step 6) — Always query `sys_user_group` or `sys_user` on the instance before writing the rule. Do NOT create the group/user or fall back to `setDisplayValue()` until a query has been attempted and returned no match. A queried sys_id used in the `group`/`user` field is the preferred outcome — this is NOT hardcoding. Exception: If the sys_id has been explicitly provided, skip the query and use it directly.

- Never silently fall back to `setDisplayValue()` — `setDisplayValue()` is only acceptable when explicitly chosen after the group/user is confirmed not found on the instance (see step 6 options). It must never be used as a default or convenience shortcut.

- Avoid complex logic — If script exceeds 8000 chars, needs external APIs, or multiple GlideRecord queries, use business rule instead

## Related Topics

See `business-rule-guide`, `client-script-guide`, `table-guide` topics.

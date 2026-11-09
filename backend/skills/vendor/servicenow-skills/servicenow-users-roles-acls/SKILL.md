---
name: servicenow-users-roles-acls
description: ServiceNow identity and access - users (sys_user), groups (sys_user_group), roles, role inheritance, and Access Control Lists (ACLs) including evaluation order, record/field ACLs, deny-unless ACLs and security_admin elevation. Use when granting access, designing roles for an app or integration user, writing or debugging ACLs, or reviewing security.
license: Apache-2.0
metadata:
  category: foundations
  version: "1.1"
---

# Users, roles, groups and ACLs

## When to use
- Designing roles for a new app, team or integration user.
- Writing, reviewing or debugging an ACL ("why can't this user see the field?").
- Security reviews and least-privilege checks.

## Key facts
- Users: `sys_user`. Groups: `sys_user_group`. Membership: `sys_user_grmember`. Roles: `sys_user_role`. Role grants: `sys_user_has_role` (users) and `sys_group_has_role` (groups).
- Roles can **contain** other roles (inheritance). `admin` passes almost every ACL.
- ACLs live in `sys_security_acl`. Operations: read, write, create, delete (plus execute and others for special types).
- ACL names: `incident` (table-level, same as `incident.None`), `incident.*` (any field), `incident.short_description` (one field).
- An ACL passes only if **all three** of its parts pass: required roles, condition, and script.
- To access a field, the user needs a passing **table-level** ACL and a passing **field-level** ACL for that operation.
- Most specific match wins: the field-specific ACL (`incident.short_description`) is evaluated before the wildcard (`incident.*`), and table ACLs walk up the hierarchy (`incident` then `task` then `*`).
- If several ACLs match at the same level, **any one passing** grants access (OR).
- Newer releases add **Deny-Unless** ACLs, evaluated before Allow-If ACLs: the user must satisfy every applicable deny-unless ACL first. Use them for blanket restrictions (e.g. "only HR roles, ever").
- Editing ACLs requires elevating to `security_admin` for the session.

## Rules
1. **Assign roles to groups, never directly to users.** Access then follows group membership and is auditable.
2. Least privilege: create app roles (`x_acme_ai.user`, `x_acme_ai.admin`) and grant only what each persona needs. Never give `admin` to integrations or service accounts.
3. Integration users: mark *Web service access only*, use OAuth where possible, grant a minimal role set (e.g. `itil` + specific app roles).
4. Prefer **role + condition** in ACLs. Use the script field only when the rule cannot be expressed as a condition; keep it short and return a boolean via `answer`.
5. Never put security in client scripts or UI policies - they only hide things in the browser. Enforce on the server with ACLs (and Data Policies / Business Rules for data rules).
6. In scripts that run on behalf of users (Scripted REST, client-callable Script Includes, portal widgets) use `GlideRecordSecure` or check `canRead()`/`canWrite()` so ACLs apply.
7. Test ACLs with **impersonation** of a real persona and the *Debug Security Rules* / Access Analyzer tools, not as admin.
8. Don't create overlapping ACLs that grant what another denies by condition - with OR semantics the broadest one wins.

## Example ACL script (field-level read)
```javascript
// ACL: x_acme_ai_suggestion.rationale, operation: read
// Requires role: x_acme_ai.user ; Condition: (empty)
answer = (function () {
    if (gs.hasRole('x_acme_ai.admin')) return true;
    // Agents can read rationale only for tasks assigned to their groups
    return gs.getUser().isMemberOf(current.task.assignment_group.toString());
})();
```

## Debugging "user can't see X"
1. Impersonate the user; reproduce.
2. Enable *Debug Security Rules* (or use Access Analyzer) and reload.
3. Check: table ACL for the operation → field ACL → role on user via group → condition → script.
4. Check Query Business Rules and Before Query restrictions, which hide rows before ACLs run.
5. For scoped tables, check *Application Access* settings (can read/create/update from other scopes).

## Anti-patterns
- Roles granted to individual users "temporarily" and never removed.
- `answer = true;` ACL scripts used to "fix" access issues.
- Hiding sensitive fields with `g_form.setDisplay(false)` as the security control.
- One giant role that contains every other role.

## Review checklist
- [ ] Roles granted via groups
- [ ] App-specific roles; no admin for service accounts
- [ ] Every sensitive table/field has server-side ACLs
- [ ] ACLs tested by impersonation
- [ ] GlideRecordSecure in user-context server code

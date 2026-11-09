---
name: servicenow-script-includes
description: Designing ServiceNow Script Includes - class-based (Class.create) and function-style includes, client-callable GlideAjax processors extending AbstractAjaxProcessor, accessibility across scopes, extending OOB utilities, and testing. Use when creating reusable server-side logic, an API for client scripts, or refactoring logic out of Business Rules, UI Actions or flows.
license: Apache-2.0
metadata:
  category: scripting
  version: "1.1"
---

# Script Includes

## When to use
- Logic used in more than one place, or longer than a few lines.
- A server endpoint for client scripts (GlideAjax).
- A scoped app's public API for other scopes.

## Patterns
**Class-based (default):**
```javascript
var TriageHelper = Class.create();
TriageHelper.prototype = {
    initialize: function () {
        this.threshold = parseFloat(gs.getProperty('acme.ai.auto_apply_threshold', '0.85'));
    },
    /** @returns {number} open incidents for an assignment group */
    openCountForGroup: function (groupId) {
        var ga = new GlideAggregate('incident');
        ga.addQuery('assignment_group', groupId);
        ga.addActiveQuery();
        ga.addAggregate('COUNT');
        ga.query();
        return ga.next() ? parseInt(ga.getAggregate('COUNT'), 10) : 0;
    },
    type: 'TriageHelper'
};
```

**Client-callable (GlideAjax):**
```javascript
var AIAjax = Class.create();
AIAjax.prototype = Object.extendsObject(global.AbstractAjaxProcessor, {
    suggestCategory: function () {
        var text = this.getParameter('sysparm_text');
        if (!text || text.length > 4000) return '';
        if (!gs.hasRole('itil')) return '';               // authorize every call
        var result = new AIClient().suggestCategory(text);
        return JSON.stringify(result);
    },
    type: 'AIAjax'
});
```

## The record (sys_script_include)
| Field | Holds |
|---|---|
| `name` | The class name, exactly as in `Class.create()` and `type:` |
| `api_name` | Set by the instance: `<scope>.<name>` (`global.TriageHelper`). Don't write it |
| `client_callable` | `true` only for GlideAjax processors |
| `access` | `package_private` (this application scope only) or `public` (all application scopes) |
| `active` | true |
| `script`, `description` | The class, and one line on what it is for |

## Rules
1. **Name = class name = `type`.** The record name must match exactly or the include won't resolve.
2. Keep `initialize` light; no queries in the constructor.
3. One responsibility per include; small public methods with JSDoc.
4. **Client callable:** tick *Client callable*, extend `AbstractAjaxProcessor`, read inputs with `getParameter('sysparm_...')`, validate them, **check roles/ACLs inside every method** (client-callable methods are reachable by any logged-in user who can call GlideAjax), return strings (JSON.stringify for objects). Since the Australia release (Glide AJAX enabled = the old *Client callable*), users must satisfy an ACL associated with the include: add it from the include's **Access Controls** related link (type *client_callable_script_include*, the roles that may call it; needs security_admin). Admins pass without it, so test as a normal user. Add `isPublic: function () { return false; },` so it never runs for unauthenticated users (`glide.script.ccsi.ispublic` sets the instance default).
5. Accessibility: *This application scope only* by default; *All application scopes* only for deliberate public APIs.
6. To change an OOB include, **extend it** (`Object.extendsObject(OOBInclude, {...})`) and point callers at your subclass, rather than editing the original.
7. Use `GlideRecordSecure` in methods that act for a user.
8. Return values, don't set globals or `current` from inside includes (pass records in as parameters).
9. Write ATF server-side script tests for public methods.

## Anti-patterns
- Client-callable methods that trust input and skip role checks.
- Name/type mismatch ("Script Include not found").
- Business logic duplicated across Business Rules instead of a shared include.
- Editing OOB includes like `TaskUtils` directly.

## Review checklist
- [ ] Name, class and type match
- [ ] Inputs validated; roles checked in client-callable methods
- [ ] Narrowest accessibility
- [ ] OOB includes extended not edited
- [ ] ATF tests for public methods

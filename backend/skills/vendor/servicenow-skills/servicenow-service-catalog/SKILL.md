---
name: servicenow-service-catalog
description: Building the ServiceNow Service Catalog - catalog items, record producers, order guides, variables and variable sets (including multi-row), catalog client scripts and UI policies, user criteria, categories, pricing and fulfilment flows. Use when creating or reviewing a catalog item, designing variables, restricting who can order, or choosing between item, record producer and order guide.
license: Apache-2.0
metadata:
  category: itsm
  version: "1.1"
---

# Service Catalog

## Choosing the object
| Object | Creates | Use for |
|---|---|---|
| **Catalog item** | REQ + RITM (+ tasks via flow) | Orderable goods/services with fulfilment |
| **Record producer** | A record in any table (incident, HR case, case) | Friendly form that creates a non-request record ("Report an issue") |
| **Order guide** | Several RITMs from one questionnaire | Bundles (new hire: laptop + accounts + phone) |
| **Content item** | Nothing | Links to KB or external info in the catalog |

## Variables
- Types: Single line text, Multi-line, Select box, Reference, Lookup select box, Checkbox, Date, Yes/No, Attachment, Label, Container start/end, **Multi-row variable set (MRVS)** for repeating rows.
- **Variable sets** share variables across items (requested for, location, business justification).
- Variable **names** are API names: lowercase, underscores, stable (`requested_for`, `business_justification`).

## Rules
1. Each item has: clear name, short description written as an outcome, category, icon/picture, **user criteria**, **fulfilment flow**, and an owner.
2. Ask the minimum: every variable must be used by fulfilment, approval or reporting. Default and auto-fill what you can (requested_for = current user).
3. Prefer **Reference / Select** variables over free text. Use reference qualifiers.
4. Reuse **variable sets** for common questions; one place to change.
5. Behaviour: **Catalog UI Policies** first, **Catalog Client Scripts** only for logic; set *Applies on* (item, RITM, task) deliberately. Use `g_form` with variable names. Scripts that work across items belong on the variable set.
6. **User criteria** (*Available for* / *Not available for*) control who sees and orders; don't hide items with roles or scripts.
7. Record producers: map variables to fields in the producer script (`current.short_description = producer.short_description;`) and keep extra answers as variables.
8. Pricing only if you charge back; recurring price for subscriptions.
9. Test as a requester persona in the Service Portal / Employee Center, on mobile too.
10. Review the catalog quarterly: unused items, items with high rejection, items ordered then cancelled.

## Example: catalog client script (onChange)
```javascript
// Applies to: variable set "Hardware common" ; Variable: laptop_model ; UI Type: All
function onChange(control, oldValue, newValue, isLoading) {
    if (isLoading || !newValue) return;
    var needsJustification = newValue == 'performance';
    g_form.setDisplay('business_justification', needsJustification);
    g_form.setMandatory('business_justification', needsJustification);
}
```

## Anti-patterns
- 40-question items; free-text "describe what you want" as the only variable.
- Items visible to everyone because user criteria were skipped.
- Separate near-identical items per department instead of one item with variables.
- Workflow logic inside catalog client scripts.

## Review checklist
- [ ] Right object type
- [ ] Minimal, typed, stable-named variables; sets reused
- [ ] UI policies before scripts; *Applies on* set
- [ ] User criteria configured
- [ ] Flow attached; tested as requester

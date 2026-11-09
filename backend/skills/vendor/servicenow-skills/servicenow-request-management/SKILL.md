---
name: servicenow-request-management
description: ServiceNow Request Management - the request (sc_request), requested item (sc_req_item / RITM) and catalog task (sc_task) hierarchy, approvals, stages, fulfilment flows, requested_for, variables on RITMs and closure. Use when designing request fulfilment, automating RITM processing, debugging a stuck request, or reporting on request performance.
license: Apache-2.0
metadata:
  category: itsm
  version: "1.1"
---

# Request Management

## Purpose
Fulfil standard service requests (access, hardware, software, information) efficiently through the Service Catalog.

## Data model
| Record | Table | Holds |
|---|---|---|
| Request (REQ) | `sc_request` | The order / cart: requested_for, opened_by, overall approval and state |
| Requested Item (RITM) | `sc_req_item` | One catalog item ordered: cat_item, quantity, variables, stage, approval |
| Catalog Task (SCTASK) | `sc_task` | Work for a fulfilment group, linked by `request_item` |
| Approvals | `sysapproval_approver` | Approver, state, linked by `sysapproval` |
| Variables | `sc_item_option_mtom` / `sc_item_option` | Answers to the item's questions |

## Rules
1. **Requests are not incidents.** If nothing is broken, it's a request. Configure the portal to route "I need..." to the catalog.
2. Fulfilment is driven by the **item's flow** (Flow Designer) - approvals, tasks, provisioning. Keep one flow per item or a shared subflow per fulfilment pattern.
3. Use **stages** on the RITM so requesters see progress (Waiting for approval, Fulfilment, Delivery, Completed).
4. **Approvals:** by manager, cost, or group via approval rules/decision tables; handle rejection (close RITM as rejected and inform requester).
5. Read variables in script via `current.variables.<name>`; in flows with *Get Catalog Variables*. Never parse them from descriptions.
6. Always populate **requested_for** correctly (may differ from opened_by).
7. Close the RITM when all its tasks are closed; the REQ closes when all RITMs close. Don't close REQs manually while RITMs are open.
8. Provide SLAs on RITMs (delivery) and SCTASKs (group performance).
9. Automate fulfilment (account creation, licence assignment) through IntegrationHub spokes, with a manual task fallback on failure.

## Debugging a stuck RITM
1. Check the flow execution for the RITM (Flow execution details) - error or waiting?
2. Approvals: any approver record still *Requested*? Is the approver inactive?
3. Catalog tasks: open tasks blocking closure?
4. Stage and state consistent?

## Automation ideas (safe)
- Summarise a RITM's history for a fulfiller.
- Recommend the right catalog item from a free-text need.
- Predict delivery date from historical RITM durations.

## Anti-patterns
- Fulfilment logic in Business Rules on sc_req_item instead of the item's flow.
- Variables copied into the description and parsed later.
- Generic "Other request" item used for 40% of requests.

## Review checklist
- [ ] Item has a flow with approvals, tasks, stages
- [ ] requested_for set; variables read properly
- [ ] Rejection and failure paths handled
- [ ] SLAs on RITM and SCTASK

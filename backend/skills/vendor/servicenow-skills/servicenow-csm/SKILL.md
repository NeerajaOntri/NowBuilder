---
name: servicenow-csm
description: ServiceNow Customer Service Management (CSM) - cases (sn_customerservice_case), accounts, contacts, consumers, entitlements, assets and install base, channels, CSM Configurable Workspace, customer portal, account-based security, and escalations. Use when configuring customer service processes, routing or triaging cases, securing customer data between accounts, or drafting customer communications.
license: Apache-2.0
metadata:
  category: crm
  version: "1.1"
---

# Customer Service Management (CSM)

## Data model
- **Case** `sn_customerservice_case` (extends task): account, contact or consumer, product/asset, category, priority, state, assignment, entitlement, channel (web, email, phone, chat).
- **Accounts** `customer_account` (B2B, with hierarchy and partners); **contacts** `customer_contact`; **consumers** `csm_consumer` (B2C).
- **Install base / assets** - what the customer owns; **entitlements** and **contracts** - what support they're owed (and SLA).
- Agents work in **CSM Configurable Workspace**; customers in the customer service portal.

## Rules
1. **Account-based data separation is the top security requirement.** Customers and partner contacts must only see their own account's cases, assets and contacts. Use the OOB CSM roles (`sn_customerservice.customer`, `.customer_admin`, `.partner`) and their contextual security; test by impersonating contacts from two different accounts.
2. Every case links to an **account/contact (or consumer)** and, where possible, a **product or install base item** - this drives routing, entitlement and SLA.
3. **Entitlement check** on case creation: valid contract → apply its SLA; no entitlement → route per policy (not silently dropped).
4. Route with **Advanced Work Assignment** (skills, capacity, channels) or assignment rules; avoid manual dispatch queues.
5. Customer-visible communication only via **additional comments** / outbound email - never put internal notes where customers can read them.
6. Use **case types** / templates for common issues; capture resolution codes for reporting.
7. **Escalations** follow a defined process (escalation request → approval → management attention), not just priority bumps.
8. Link cases to **incidents/problems/changes** when the cause is internal (ITSM integration) - customers see case status, not internal detail.
9. Knowledge for customers lives in a separate, customer-facing knowledge base with user criteria per account type.
10. Measure: first response time, resolution time, CSAT, reopen rate, cases per account/product.

## AI guidance for CSM
- Draft customer replies for agent review - never send automatically.
- Keep tone professional, specific, and free of internal system names or other customers' data.
- Summaries for handover may include internal notes; customer drafts must not.

## Anti-patterns
- Customer portal users granted ITIL-like roles.
- Cases with no account or contact.
- Internal investigation notes in customer-visible fields.

## Review checklist
- [ ] Account separation tested with two accounts
- [ ] Account/contact/product on every case
- [ ] Entitlements → SLAs
- [ ] AWA or rules for routing
- [ ] Customer vs internal communication separated

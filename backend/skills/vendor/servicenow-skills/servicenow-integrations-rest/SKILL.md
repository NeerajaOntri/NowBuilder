---
name: servicenow-integrations-rest
description: Integrating ServiceNow with other systems over REST - inbound Table API, Scripted REST APIs, Import Set API with transform maps, outbound RESTMessageV2, OAuth and Connection & Credential aliases, MID Server, async calls, pagination, retries, idempotency and error handling. Use when exposing or consuming an API, building an integration, loading external data, or debugging integration failures.
license: Apache-2.0
metadata:
  category: integrations
  version: "1.1"
---

# Integrations and REST APIs

## When to use
- Any system-to-system data exchange with ServiceNow.
- Choosing Table API vs Scripted REST vs Import Set API.
- Making outbound calls from Business Rules, flows or Script Includes.

## Inbound: choose the entry point
| Need | Use | Why |
|---|---|---|
| Simple CRUD on a table, trusted caller | **Table API** `/api/now/table/{table}` | No code; ACLs apply |
| Bulk or messy external data | **Import Set API** `/api/now/import/{staging_table}` + **Transform Map** | Staging, coalescing, transform scripts, errors visible per row |
| Custom contract, validation, composite operations | **Scripted REST API** (`sys_ws_definition`) | You define the resource, version and response |
| CIs | **IRE** (Identification and Reconciliation) via import/transform or `IdentificationEngine` | Prevents duplicate CIs (see CMDB skill) |

Table API essentials: `sysparm_query` (encoded query), `sysparm_fields`, `sysparm_limit` + `sysparm_offset` for paging, `sysparm_display_value=true|false|all`, `sysparm_exclude_reference_link=true`.

## Outbound
```javascript
// In an async Business Rule, Script Include or flow script step
var r = new sn_ws.RESTMessageV2('x_acme_ai AI Service', 'triage'); // REST Message record + method
r.setStringParameterNoEscape('sys_id', current.getUniqueValue());
r.setHttpTimeout(10000);
try {
    var resp = r.execute();
    var code = resp.getStatusCode();
    if (code >= 200 && code < 300) {
        var body = JSON.parse(resp.getBody());
    } else {
        gs.warn('[AI] triage HTTP {0}: {1}', code, resp.getErrorMessage());
    }
} catch (e) {
    gs.error('[AI] triage call failed: {0}', e.message);
}
```

## Rules
1. **Inbound data goes through staging** (Import Set + Transform Map) unless it is simple, validated CRUD. Set **coalesce** fields so re-sends update instead of duplicating.
2. **Least-privilege integration user**: *Web service access only*, minimal roles, no admin. Prefer **OAuth 2.0** (client credentials or JWT) over basic auth.
3. **Outbound credentials** live in REST Message auth profiles or **Connection & Credential aliases** - never in scripts or properties as plain text.
4. **Never call out synchronously from before/after Business Rules** - use async rules, events, flows, or `executeAsync()` with a callback/ECC handling.
5. On-premise targets → route through a **MID Server**.
6. Set **timeouts**, handle non-2xx, log status + correlation id (never the full payload if it holds PII).
7. **Retries with backoff** for 429/5xx; respect `Retry-After`. Make operations **idempotent** (store external ids in a `correlation_id` field and check before insert).
8. **Page** large reads (`sysparm_limit` 100-1000 + `sysparm_offset`), request only needed fields.
9. Scripted REST: version the API (`/api/x_acme/ai/v1/...`), validate input, return clear status codes (400, 404, 409), and use `GlideRecordSecure` or explicit checks.
10. Configure **REST API rate limits** for heavy callers; monitor the transaction and outbound HTTP logs.
11. Document each integration: owner, direction, frequency, volume, auth, error handling, contacts.

## Anti-patterns
- Admin credentials in a third-party tool "to make it work".
- Direct Table API inserts into `cmdb_ci_*` from discovery tools (duplicates).
- Synchronous outbound calls holding the user's transaction.
- Swallowing errors with an empty catch.

## Review checklist
- [ ] Right inbound pattern; coalesce set
- [ ] OAuth/aliases; no secrets in code
- [ ] Async outbound, timeouts, retries, idempotency
- [ ] Paging and field selection
- [ ] Logging without PII; integration documented

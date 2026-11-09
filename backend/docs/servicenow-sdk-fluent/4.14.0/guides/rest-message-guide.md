Version: 4.14.0

# REST Message Guide

Guide for creating ServiceNow Outbound REST Messages (`sys_rest_message`) to call external HTTP services using the Fluent SDK. REST Messages define reusable, authenticated integrations with one base URL, shared headers, and multiple named HTTP operations callable from server-side scripts via `sn_ws.RESTMessageV2`.

## When to Use

- Integrating with an external HTTP/REST API from ServiceNow (outbound direction)

- Grouping multiple HTTP methods (GET, POST, PUT, PATCH, DELETE, HEAD) against the same base endpoint

- When the integration requires Basic auth, OAuth 2.0, API Key, or no authentication

- When requests must be routed through a MID server to reach an internal or on-premise system

- When you need parameterized URLs, headers, or bodies resolved at runtime via `${varName}` substitution

- Creating a reusable, auditable integration definition instead of ad-hoc scripted HTTP calls

## Do NOT Use For

- Exposing your own endpoints to external callers — use the `scripted-rest-api` skill instead

- One-off ephemeral HTTP calls with absolutely no reuse — prefer RestMessage even then; use dynamic `new sn_ws.RESTMessageV2()` only for truly throwaway cases

## Core Principles

- One `RestMessage` per external service: Define the base `endpoint` once at the message level. Every function inherits it unless it overrides `endpoint` for a specific operation.

- One function per HTTP method + path: Each entry in `functions` represents a single callable operation. Set `httpMethod` to `'GET'`, `'POST'`, `'PUT'`, `'PATCH'`, `'DELETE'`, or `'HEAD'` (uppercase — the platform stores it lowercase internally).

- Parameterize with `${varName}`: Place `${something}` in `endpoint`, `content`, header `value`, or query param `value`. Declare each placeholder in the function's `variables` array or the call fails.

- Message-level vs function-level headers: Use top-level `headers` for headers shared by every function (e.g., `Content-Type`, `Accept`). Use function-level `headers` for headers unique to a single call (e.g., `X-Idempotency-Key`).

- Authentication — reuse credential profiles, never inline secrets:

- `authenticationType: 'noAuthentication'` — public APIs (default)

- `authenticationType: 'basic'` + `basicAuthProfile: '<sys_id>'` — Basic auth

- `authenticationType: 'oauth2'` + `oauthProfile: '<sys_id>'` — OAuth 2.0

- API Key: use `'noAuthentication'` + custom header `X-API-Key: ${apiKey}`. Store the actual key in a `password2` system property, never hardcoded.

- Request body for POST/PUT/PATCH: Set `content` on the function with `${varName}` placeholders. Use `escapeType: 'noEscaping'` (default) for JSON. Use `escapeType: 'escapeXml'` for XML.

- Query params vs path variables: Put filters and pagination in `queryParams` (appended as `?key=value`). Put resource identifiers directly in the `endpoint` path as `${id}` substitution.

- MID server for internal targets: Set `midServer` to the sys_id of the `ecc_agent` record when the target host is not reachable from the ServiceNow instance.

- Scope visibility: Default `access: 'packagePrivate'`. Set `access: 'public'` only when other scoped apps must call this message.

- `$id` required on all records: Every `RestMessage`, `RestMessageHeader`, `RestMessageFnHeader`, `RestMessageParamSubstitution`, and `RestMessageQueryParam` must have `$id: Now.ID['some-key']`. Only `RestMessageFn` (functions) is identified by `name` via coalesce. All other child records use explicit `$id` for identity — no name-based coalesce.

- Always provide `description` at the message level for discoverability.

- Always set explicit timeout in runtime scripts: `rm.setHttpTimeout(30000)`.

## Quick Decision Guide

| Scenario | Approach |
| Multiple methods against the same API | One `RestMessage` , multiple `functions` |
| Same service, different auth per endpoint | One `RestMessage` , override `authenticationType` on individual functions |
| On-premise / internal host unreachable from instance | Set `midServer` on each function |
| Public API, no credentials | `authenticationType: 'noAuthentication'` (default) |
| Service account credentials | `authenticationType: 'basic'` + `basicAuthProfile` |
| Token-based / modern OAuth | `authenticationType: 'oauth2'` + `oauthProfile` |
| API Key in header | `'noAuthentication'` + function-level header `X-API-Key: ${apiKey}` |
| API Key in query string | `'noAuthentication'` + queryParam `api_key: ${apiKey}` (less secure — visible in logs) |
| JSON body | `content` with `${vars}` ; runtime `setStringParameterNoEscape()` |
| XML body | `content` with `${vars}` ; `escapeType: 'escapeXml'` ; runtime `setStringParameter()` |

## Key Concepts

### Record Hierarchy

```
RestMessage                        → sys_rest_message
├── headers[]                      → sys_rest_message_headers       (shared, applied to every function)
└── functions[]                    → sys_rest_message_fn            (one per HTTP method/path)
    ├── headers[]                  → sys_rest_message_fn_headers    (function-specific)
    ├── variables[]                → sys_rest_message_fn_parameters (${varName} declarations)
    └── queryParams[]              → sys_rest_message_fn_param_defs (?key=value pairs)
```

### Variable Substitution

Placeholders (`${name}`) may appear in `endpoint`, header `value`, query param `value`, and `content`. Each must be declared in the function's `variables` array.

- `escapeType: 'noEscaping'` (default) — inserts value as-is. Use for JSON.

- `escapeType: 'escapeXml'` — XML-escapes `<>&'"`. Use for XML only.

Critical runtime distinction: `setStringParameter()` applies XML escaping regardless of `escapeType`. `setStringParameterNoEscape()` inserts as-is. For JSON payloads, always use `setStringParameterNoEscape()` — the escaped variant corrupts JSON with `&amp;`, `&lt;`, etc.

### Authentication Patterns

| Pattern | Fluent Config | Runtime Behavior |
| None | `authenticationType: 'noAuthentication'` | No auth header sent |
| Basic | `authenticationType: 'basic'` + `basicAuthProfile` | Auto-sends `Authorization: Basic <base64>` |
| OAuth 2.0 | `authenticationType: 'oauth2'` + `oauthProfile` | Auto-manages tokens; sends `Authorization: Bearer <token>` |
| API Key (header) | `'noAuthentication'` + header `X-API-Key: ${apiKey}` | Set at runtime via `setStringParameterNoEscape('apiKey', gs.getProperty('x.api.key'))` |
| API Key (query) | `'noAuthentication'` + queryParam `api_key: ${apiKey}` | Same pattern. Less secure — visible in server logs |

Credential profiles: When using `authenticationType: 'basic'`, set `basicAuthProfile` to the sys_id of a `sys_auth_profile_basic` record. For OAuth 2.0, set `oauthProfile` to the sys_id of an `oauth_entity_profile` record. The plugin writes both `authentication_type` and the profile reference correctly.

### Runtime Invocation

```
var rm = new sn_ws.RESTMessageV2('CRM Integration', 'createContact');
rm.setStringParameterNoEscape('firstName', firstName); // NoEscape for JSON
rm.setStringParameterNoEscape('lastName', lastName);
rm.setHttpTimeout(30000); // Always set timeout

try {
  var response = rm.execute();
  var status = response.getStatusCode();
  var body = response.getBody();

  if (status >= 200 && status < 300) {
    return JSON.parse(body);
  }
  gs.error('API error ' + status + ': ' + body);
  return null;
} catch (ex) {
  gs.error('API exception: ' + ex.getMessage());
  return null;
}
```

The first argument to `RESTMessageV2` is the RestMessage `name`; the second is the function `name`. Both are case-sensitive.

Key runtime methods:

| Method | Use |
| `setStringParameterNoEscape(name, value)` | Set variable — use for JSON |
| `setStringParameter(name, value)` | Set variable (XML-escaped) — use for XML |
| `setHttpTimeout(ms)` | Timeout in milliseconds — always set explicitly |
| `setRequestHeader(name, value)` | Add or override a header at runtime |
| `setEndpoint(url)` | Override the endpoint URL at runtime |
| `setMIDServer(name)` | Route through MID server — takes MID server name , not sys_id |
| `execute()` | Synchronous execution |
| `executeAsync()` | Async via ECC Queue (MID server scenarios); call `response.waitForResponse(secs)` before reading body |

#### Script Include wrapper (`src/server/`)

For reusable integrations, wrap the `RESTMessageV2` calls in a Script Include class under `src/server/`. Script Include files run in the ServiceNow server-side context where Glide globals — including `sn_ws` — are available without imports.

`src/server/integrations/crm-client.js`

```
var CrmClient = Class.create();
CrmClient.prototype = {
    createContact: function(firstName, lastName, email) {
        var rm = new sn_ws.RESTMessageV2('CRM Integration', 'createContact');
        rm.setStringParameterNoEscape('firstName', firstName);
        rm.setStringParameterNoEscape('lastName', lastName);
        rm.setStringParameterNoEscape('email', email);
        rm.setHttpTimeout(30000);

        try {
            var response = rm.execute();
            var status = response.getStatusCode();
            var body = response.getBody();

            if (status >= 200 && status < 300) {
                return JSON.parse(body);
            }
            gs.error('CRM createContact error ' + status + ': ' + body);
            return null;
        } catch (ex) {
            gs.error('CRM createContact exception: ' + ex.getMessage());
            return null;
        }
    },

    getContact: function(contactId) {
        var rm = new sn_ws.RESTMessageV2('CRM Integration', 'getContact');
        rm.setStringParameterNoEscape('contactId', contactId);
        rm.setHttpTimeout(30000);

        try {
            var response = rm.execute();
            var status = response.getStatusCode();
            var body = response.getBody();

            if (status >= 200 && status < 300) {
                return JSON.parse(body);
            }
            gs.error('CRM getContact error ' + status + ': ' + body);
            return null;
        } catch (ex) {
            gs.error('CRM getContact exception: ' + ex.getMessage());
            return null;
        }
    },

    type: 'CrmClient'
};
```

Wire it up as a Script Include in your Fluent definition:

`src/fluent/script-includes/crm-client.now.ts`

```
import '@servicenow/sdk/global';
import { ScriptInclude } from '@servicenow/sdk/core';

export const CrmClientSI = ScriptInclude({
    $id: Now.ID['crm-client-si'],
    name: 'CrmClient',
    script: Now.include('../../server/integrations/crm-client.js'),
    clientCallable: false,
});
```

Call the Script Include from any server-side script using `new CrmClient()`:

```
var client = new CrmClient();
var contact = client.createContact(firstName, lastName, email);
if (contact) {
    gs.info('Created contact: ' + contact.id);
}
```

### Project Structure

```
src/
  fluent/
    rest-messages/
      crm-integration.now.ts      ← RestMessage definition
      geocoding-api.now.ts
  server/
    integrations/
      crm-client.js               ← Script Include wrapper with error handling
```

## Avoidance

- Never hardcode credentials in `endpoint`, `content`, or headers — always reference `basicAuthProfile`/`oauthProfile` sys_ids, or use system properties at runtime

- Never use `${varName}` without declaring it in the function's `variables` array — the placeholder is sent literally and the call fails silently

- Never lowercase `httpMethod` — use `'GET'`, `'POST'`, etc.; the plugin handles DB casing

- Never use `setStringParameter()` for JSON payloads — it XML-escapes and corrupts JSON; always use `setStringParameterNoEscape()`

- Never use `escapeType: 'escapeXml'` on variables injected into JSON — only use it for XML payloads

- Never omit `setHttpTimeout()` in runtime scripts — default timeout may be too short for external services

- Avoid separate RestMessages for the same API when functions differ only by method/path — consolidate under one RestMessage

- Avoid `access: 'public'` unless another scoped app genuinely needs to call this message

- Don't put resource identifiers in `queryParams` — use path-style `${id}` substitution in `endpoint`

- Don't store API keys in `endpoint` or `content` — pass as variables set at runtime from `gs.getProperty()`

- Avoid duplicate `name` values across RestMessages — `RESTMessageV2('name', 'fn')` picks one arbitrarily when duplicates exist

- Only use valid `authenticationType` values: `'noAuthentication'`, `'basic'`, `'oauth2'` at message level; additionally `'inheritFromParent'` at function level — any other value is rejected at compile time

## Security Best Practices

| Concern | Rule |
| Credentials | Never hardcode. Use `basicAuthProfile` / `oauthProfile` pointing to credential records |
| API Keys | Store in `password2` system properties. Set at runtime via `gs.getProperty()` |
| HTTPS only | Always use `https://` endpoints in production |
| Minimal scope | Default `access: 'packagePrivate'` . Use `'public'` only when cross-scope is required |
| Least privilege | Configure OAuth scopes and API key permissions to the minimum needed |
| Logging | Never log full response bodies (PII/token risk). Log status codes and correlation IDs only |
| Token handling | Use OAuth profiles for auto-lifecycle management. Never pass tokens in query strings |

## Troubleshooting

| Symptom | Likely Cause | Fix |
| `${varName}` sent literally in request | Variable not in `variables[]` | Add matching entry to function's `variables` array |
| 401 Unauthorized | Wrong or missing auth profile | Verify sys_id; confirm credential record exists and is valid |
| JSON body corrupted ( `&amp;` , `&lt;` ) | `escapeType: 'escapeXml'` on a JSON variable, or using `setStringParameter()` | Remove `escapeType` or switch to `setStringParameterNoEscape()` |
| Wrong endpoint called | Function inheriting parent endpoint unintentionally | Set explicit `endpoint` on the function |
| Header applied to all functions unexpectedly | Header placed at message level | Move to function-level `headers[]` |
| Duplicate `$id` build error | Two records share the same `Now.ID` key | Ensure every `Now.ID` key is unique across the codebase |
| MID server call hangs | Wrong sys_id or MID server offline | Verify `ecc_agent` record; check MID server status |
| Query params missing from request | No `queryParams[]` or wrong `value` | Confirm `value` uses `${varName}` and the var is declared |
| Timeout errors | Default timeout too short | Set `rm.setHttpTimeout(30000)` or higher |

## API Reference

For the full property reference (`RestMessage`, `RestMessageFn`, `RestMessageHeader`, `RestMessageFnHeader`, `RestMessageParamSubstitution`, `RestMessageQueryParam`, and table mappings), see the `restmessage-api` topic.

## Examples

### Minimal GET with Query Parameters

```
import '@servicenow/sdk/global';
import { RestMessage } from '@servicenow/sdk/core';

RestMessage({
  $id: Now.ID['geocoding-msg'],
  name: 'Geocoding API',
  endpoint: 'https://geocoding-api.open-meteo.com/v1/search',
  description: 'Search for a city by name using Open-Meteo geocoding',
  functions: [
    {
      name: 'searchCity',
      httpMethod: 'GET',
      variables: [{ $id: Now.ID['geocoding-search-var-city'], name: 'city' }],
      queryParams: [
        { $id: Now.ID['geocoding-search-param-name'], name: 'name', value: '${city}', order: 1 },
      ],
    },
  ],
});
```

### OAuth 2.0 with Shared Headers and Multiple Functions

```
import '@servicenow/sdk/global';
import { RestMessage } from '@servicenow/sdk/core';

RestMessage({
  $id: Now.ID['crm-integration'],
  name: 'CRM Integration',
  endpoint: 'https://crm.example.com/api',
  description: 'Outbound integration with CRM for contact management',
  authenticationType: 'oauth2',
  oauthProfile: '00000000000000000000000000000002', // sys_id of oauth_entity_profile
  headers: [
    { $id: Now.ID['crm-header-content-type'], name: 'Content-Type', value: 'application/json' },
    { $id: Now.ID['crm-header-accept'],       name: 'Accept',       value: 'application/json' },
  ],
  functions: [
    {
      name: 'createContact',
      httpMethod: 'POST',
      endpoint: 'https://crm.example.com/api/contacts',
      content: '{"firstName":"${firstName}","lastName":"${lastName}","email":"${email}"}',
      variables: [
        { $id: Now.ID['crm-create-var-first-name'], name: 'firstName' },
        { $id: Now.ID['crm-create-var-last-name'],  name: 'lastName' },
        { $id: Now.ID['crm-create-var-email'],      name: 'email' },
      ],
    },
    {
      name: 'getContact',
      httpMethod: 'GET',
      endpoint: 'https://crm.example.com/api/contacts/${contactId}',
      variables: [{ $id: Now.ID['crm-get-var-contact-id'], name: 'contactId' }],
    },
  ],
});
```

### API Key via Custom Header

```
import '@servicenow/sdk/global';
import { RestMessage } from '@servicenow/sdk/core';

RestMessage({
  $id: Now.ID['notification-api'],
  name: 'Notification Service',
  endpoint: 'https://api.notify.example.com/v1',
  description: 'Push notifications with API key auth via header',
  headers: [
    { $id: Now.ID['notify-header-content-type'], name: 'Content-Type', value: 'application/json' },
  ],
  functions: [
    {
      name: 'sendNotification',
      httpMethod: 'POST',
      endpoint: 'https://api.notify.example.com/v1/messages',
      content: '{"to":"${recipient}","body":"${messageBody}"}',
      headers: [
        { $id: Now.ID['notify-fn-header-api-key'], name: 'X-API-Key', value: '${apiKey}' },
      ],
      variables: [
        { $id: Now.ID['notify-var-api-key'],      name: 'apiKey' },
        { $id: Now.ID['notify-var-recipient'],    name: 'recipient' },
        { $id: Now.ID['notify-var-message-body'], name: 'messageBody' },
      ],
    },
  ],
});
```

Runtime invocation:

```
var rm = new sn_ws.RESTMessageV2('Notification Service', 'sendNotification');
rm.setStringParameterNoEscape('apiKey', gs.getProperty('x_myapp.notify.api_key'));
rm.setStringParameterNoEscape('recipient', userEmail);
rm.setStringParameterNoEscape('messageBody', message);
rm.setHttpTimeout(30000);
var response = rm.execute();
```

### Basic Auth Through MID Server (On-Premise)

```
import '@servicenow/sdk/global';
import { RestMessage } from '@servicenow/sdk/core';

RestMessage({
  $id: Now.ID['on-prem-service'],
  name: 'On-Premise ERP Service',
  endpoint: 'https://internal.corp.example.com/erp/api',
  description: 'ERP integration routed through MID server with basic auth',
  authenticationType: 'basic',
  basicAuthProfile: '00000000000000000000000000000001', // sys_id of sys_auth_profile_basic
  functions: [
    {
      name: 'getEmployee',
      httpMethod: 'GET',
      endpoint: 'https://internal.corp.example.com/erp/api/employees/${employeeId}',
      midServer: 'd1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6', // sys_id of ecc_agent
      variables: [{ $id: Now.ID['erp-get-var-employee-id'], name: 'employeeId' }],
    },
    {
      name: 'updateEmployee',
      httpMethod: 'PUT',
      endpoint: 'https://internal.corp.example.com/erp/api/employees/${employeeId}',
      midServer: 'd1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6',
      content: '{"department":"${department}","title":"${title}"}',
      headers: [
        { $id: Now.ID['erp-update-header-content-type'], name: 'Content-Type', value: 'application/json' },
      ],
      variables: [
        { $id: Now.ID['erp-update-var-employee-id'], name: 'employeeId' },
        { $id: Now.ID['erp-update-var-department'],  name: 'department' },
        { $id: Now.ID['erp-update-var-title'],       name: 'title' },
      ],
    },
  ],
});
```

### Full CRUD — Five Operations Under One Service

```
import '@servicenow/sdk/global';
import { RestMessage } from '@servicenow/sdk/core';

RestMessage({
  $id: Now.ID['project-api'],
  name: 'Project Management API',
  endpoint: 'https://pm.example.com/api/v2',
  description: 'Full CRUD integration with project management system',
  authenticationType: 'oauth2',
  oauthProfile: '00000000000000000000000000000003',
  headers: [
    { $id: Now.ID['pm-header-content-type'], name: 'Content-Type', value: 'application/json' },
    { $id: Now.ID['pm-header-accept'],       name: 'Accept',       value: 'application/json' },
  ],
  functions: [
    {
      name: 'listProjects',
      httpMethod: 'GET',
      endpoint: 'https://pm.example.com/api/v2/projects',
      variables: [
        { $id: Now.ID['pm-list-var-limit'],  name: 'limit' },
        { $id: Now.ID['pm-list-var-offset'], name: 'offset' },
      ],
      queryParams: [
        { $id: Now.ID['pm-list-param-limit'],  name: 'limit',  value: '${limit}',  order: 1 },
        { $id: Now.ID['pm-list-param-offset'], name: 'offset', value: '${offset}', order: 2 },
      ],
    },
    {
      name: 'getProject',
      httpMethod: 'GET',
      endpoint: 'https://pm.example.com/api/v2/projects/${projectId}',
      variables: [{ $id: Now.ID['pm-get-var-project-id'], name: 'projectId' }],
    },
    {
      name: 'createProject',
      httpMethod: 'POST',
      endpoint: 'https://pm.example.com/api/v2/projects',
      content: '{"name":"${projectName}","description":"${projectDesc}"}',
      variables: [
        { $id: Now.ID['pm-create-var-name'], name: 'projectName' },
        { $id: Now.ID['pm-create-var-desc'], name: 'projectDesc' },
      ],
    },
    {
      name: 'updateProject',
      httpMethod: 'PUT',
      endpoint: 'https://pm.example.com/api/v2/projects/${projectId}',
      content: '{"name":"${projectName}","description":"${projectDesc}"}',
      variables: [
        { $id: Now.ID['pm-update-var-project-id'], name: 'projectId' },
        { $id: Now.ID['pm-update-var-name'],       name: 'projectName' },
        { $id: Now.ID['pm-update-var-desc'],       name: 'projectDesc' },
      ],
    },
    {
      name: 'deleteProject',
      httpMethod: 'DELETE',
      endpoint: 'https://pm.example.com/api/v2/projects/${projectId}',
      variables: [{ $id: Now.ID['pm-delete-var-project-id'], name: 'projectId' }],
    },
  ],
});
```

### XML Payload with escapeXml

```
import '@servicenow/sdk/global';
import { RestMessage } from '@servicenow/sdk/core';

RestMessage({
  $id: Now.ID['soap-bridge'],
  name: 'Legacy SOAP Bridge',
  endpoint: 'https://legacy.example.com/ws',
  description: 'Bridge to legacy SOAP service via REST wrapper',
  headers: [
    { $id: Now.ID['soap-header-content-type'], name: 'Content-Type', value: 'application/xml' },
  ],
  functions: [
    {
      name: 'createOrder',
      httpMethod: 'POST',
      content: '<Order><CustomerName>${customerName}</CustomerName><Amount>${amount}</Amount></Order>',
      variables: [
        { $id: Now.ID['soap-create-var-customer-name'], name: 'customerName', escapeType: 'escapeXml' },
        { $id: Now.ID['soap-create-var-amount'],        name: 'amount',        escapeType: 'escapeXml' },
      ],
    },
  ],
});
```

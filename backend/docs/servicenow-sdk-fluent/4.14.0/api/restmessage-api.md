Version: 4.14.0

# RestMessage

Creates outbound HTTP integrations (`sys_rest_message`) with a base URL, shared authentication, shared headers, and one or more callable HTTP method functions (`sys_rest_message_fn`) invokable from server-side scripts via `sn_ws.RESTMessageV2`.

## Parameters

### RestMessage

| Property | Type | Required | Default | Description |
| `$id` | `Now.ID` | Yes | — | Unique stable identifier. Format: `Now.ID['key']` . Hashed to sys_id at build time. |
| `name` | `string` | Yes | — | Display name. First arg in `RESTMessageV2('name', 'fn')` . Case-sensitive. Max 40 chars. Maps to `sys_rest_message.name` . |
| `endpoint` | `string` | Yes | — | Base URL. Supports `${varName}` substitution. Max 200 chars. Maps to `sys_rest_message.rest_endpoint` . |
| `description` | `string` | No | `''` | Human-readable purpose. Max 1000 chars. Maps to `sys_rest_message.description` . |
| `authenticationType` | `string` | No | `'noAuthentication'` | `'noAuthentication'` | `'basic'` | `'oauth2'` . Maps to `sys_rest_message.authentication_type` . |
| `basicAuthProfile` | `string` | No | — | sys_id of `sys_auth_profile_basic` . Required when `authenticationType` is `'basic'` . Maps to `sys_rest_message.basic_auth_profile` . |
| `oauthProfile` | `string` | No | — | sys_id of `oauth_entity_profile` . Required when `authenticationType` is `'oauth2'` . Maps to `sys_rest_message.oauth2_profile` . |
| `access` | `string` | No | `'packagePrivate'` | `'packagePrivate'` | `'public'` . Maps to `sys_rest_message.access` . |
| `headers` | `RestMessageHeader[]` | No | `[]` | Message-level headers sent with every function. See RestMessageHeader . |
| `functions` | `RestMessageFn[]` | No | `[]` | HTTP operations. Include at least one for a useful definition. See RestMessageFn . |

### RestMessageFn

Used within `RestMessage.functions[]`. Maps to `sys_rest_message_fn`.

| Property | Type | Required | Default | Description |
| `name` | `string` | Yes | — | Operation name. Second arg in `RESTMessageV2('msg', 'name')` . Case-sensitive. Max 100 chars. Must be unique within the parent message. Maps to `sys_rest_message_fn.function_name` . |
| `httpMethod` | `string` | Yes | — | `'GET'` | `'POST'` | `'PUT'` | `'PATCH'` | `'DELETE'` | `'HEAD'` (uppercase). Platform stores lowercase. Maps to `sys_rest_message_fn.http_method` . |
| `endpoint` | `string` | No | Inherited | Full URL override for this function. Supports `${varName}` . Max 200 chars. Maps to `sys_rest_message_fn.rest_endpoint` . |
| `content` | `string` | No | `''` | Request body template with `${varName}` placeholders. Use for POST, PUT, PATCH. Max 4000 chars. Maps to `sys_rest_message_fn.content` . |
| `authenticationType` | `string` | No | `'inheritFromParent'` | `'inheritFromParent'` | `'noAuthentication'` | `'basic'` | `'oauth2'` . Maps to `sys_rest_message_fn.authentication_type` . |
| `basicAuthProfile` | `string` | No | Inherited | Overrides parent Basic auth profile for this function only. Maps to `sys_rest_message_fn.basic_auth_profile` . |
| `oauthProfile` | `string` | No | Inherited | Overrides parent OAuth profile for this function only. Maps to `sys_rest_message_fn.oauth2_profile` . |
| `midServer` | `string` | No | — | sys_id of `ecc_agent` . Routes this function's requests through a MID server. Maps to `sys_rest_message_fn.use_mid_server` . |
| `lock` | `boolean` | No | `false` | Prevents editing this function on the instance. Maps to `sys_rest_message_fn.lock` . |
| `headers` | `RestMessageFnHeader[]` | No | `[]` | Function-specific headers, added alongside (not replacing) message-level headers. See RestMessageFnHeader . |
| `variables` | `RestMessageParamSubstitution[]` | No | `[]` | Declared `${varName}` placeholders used in this function. See RestMessageParamSubstitution . |
| `queryParams` | `RestMessageQueryParam[]` | No | `[]` | URL query parameters appended as `?key=value` . See RestMessageQueryParam . |

### RestMessageHeader

Used within `RestMessage.headers[]`. Maps to `sys_rest_message_headers`.

| Property | Type | Required | Description |
| `$id` | `Now.ID` | Yes | Unique stable identifier. Format: `Now.ID['key']` . Hashed to sys_id at build time. |
| `name` | `string` | Yes | Header name (e.g., `'Content-Type'` ). Max 80 chars. Maps to `sys_rest_message_headers.name` . |
| `value` | `string` | Yes | Header value. Supports `${varName}` . Max 1000 chars. Maps to `sys_rest_message_headers.value` . |

### RestMessageFnHeader

Used within `RestMessageFn.headers[]`. Maps to `sys_rest_message_fn_headers`.

| Property | Type | Required | Description |
| `$id` | `Now.ID` | Yes | Unique stable identifier. Format: `Now.ID['key']` . Hashed to sys_id at build time. |
| `name` | `string` | Yes | Header name. Max 80 chars. Maps to `sys_rest_message_fn_headers.name` . |
| `value` | `string` | Yes | Header value. Supports `${varName}` . Max 1000 chars. Maps to `sys_rest_message_fn_headers.value` . |

### RestMessageParamSubstitution

Used within `RestMessageFn.variables[]`. Maps to `sys_rest_message_fn_parameters`. Declares the `${varName}` placeholders used in the function's `endpoint`, `content`, `headers`, and `queryParams`.

| Property | Type | Required | Default | Description |
| `$id` | `Now.ID` | Yes | — | Unique stable identifier. Format: `Now.ID['key']` . Hashed to sys_id at build time. |
| `name` | `string` | Yes | — | Matches the `${name}` placeholder. Max 80 chars. Maps to `sys_rest_message_fn_parameters.name` . |
| `escapeType` | `string` | No | `'noEscaping'` | `'noEscaping'` — inserts value as-is (use for JSON). `'escapeXml'` — XML-escapes `<>&'"` before insertion (use for XML only). Maps to `sys_rest_message_fn_parameters.type` . |

At runtime, `setStringParameter(name, value)` applies XML escaping regardless of `escapeType`. For JSON payloads always use `setStringParameterNoEscape(name, value)`.

### RestMessageQueryParam

Used within `RestMessageFn.queryParams[]`. Maps to `sys_rest_message_fn_param_defs`.

| Property | Type | Required | Default | Description |
| `$id` | `Now.ID` | Yes | — | Unique stable identifier. Format: `Now.ID['key']` . Hashed to sys_id at build time. |
| `name` | `string` | Yes | — | Query parameter key (e.g., `'limit'` produces `?limit=...` ). Max 80 chars. Maps to `sys_rest_message_fn_param_defs.name` . |
| `value` | `string` | No | — | Static string or `${varName}` reference. Max 1000 chars. Maps to `sys_rest_message_fn_param_defs.value` . |
| `order` | `number` | No | `0` | Sort order when multiple query params exist. Maps to `sys_rest_message_fn_param_defs.order` . |

## Table Mappings

### RestMessage → `sys_rest_message`

| Fluent Property | Instance Column | Notes |
| `$id` | `sys_id` | Hashed at build time |
| `name` | `name` | Max 40 chars |
| `endpoint` | `rest_endpoint` | Max 200 chars |
| `description` | `description` | Max 1000 chars |
| `authenticationType` | `authentication_type` | `'noAuthentication'` | `'basic'` | `'oauth2'` |
| `basicAuthProfile` | `basic_auth_profile → sys_auth_profile_basic` | Required when `authenticationType` is `'basic'` |
| `oauthProfile` | `oauth2_profile → oauth_entity_profile` |  |
| `access` | `access` |  |
| `headers` | `sys_rest_message_headers` | Related list |
| `functions` | `sys_rest_message_fn` | Related list |

### RestMessageFn → `sys_rest_message_fn`

| Fluent Property | Instance Column | Notes |
| `name` | `function_name` | Max 100 chars. Identified by `(rest_message, function_name)` coalesce — must be unique within the parent message. |
| `httpMethod` | `http_method` | Stored lowercase on instance |
| `endpoint` | `rest_endpoint` | Max 200 chars |
| `content` | `content` | Max 4000 chars |
| `authenticationType` | `authentication_type` | `'inheritFromParent'` | `'noAuthentication'` | `'basic'` | `'oauth2'` |
| `basicAuthProfile` | `basic_auth_profile → sys_auth_profile_basic` | Required when `authenticationType` is `'basic'` |
| `oauthProfile` | `oauth2_profile → oauth_entity_profile` |  |
| `midServer` | `use_mid_server → ecc_agent` | sys_id of `ecc_agent` record |
| `lock` | `lock` |  |
| `headers` | `sys_rest_message_fn_headers` | Related list |
| `variables` | `sys_rest_message_fn_parameters` | Related list |
| `queryParams` | `sys_rest_message_fn_param_defs` | Related list |

### Supporting Objects

| Object | Instance Table | Key Column Mappings |
| `RestMessageHeader` | `sys_rest_message_headers` | `name` , `value` |
| `RestMessageFnHeader` | `sys_rest_message_fn_headers` | `name` , `value` |
| `RestMessageParamSubstitution` | `sys_rest_message_fn_parameters` | `name` , `type` (escapeType) |
| `RestMessageQueryParam` | `sys_rest_message_fn_param_defs` | `name` , `value` , `order` |

## Platform Field Mapping

All fields write to and read from their correct platform columns:

| Fluent Property | Instance Column | Notes |
| `authenticationType: 'basic'` | `authentication_type = 'basic'` | Stored as `'basic'` choice value. No Business Rule triggered. |
| `basicAuthProfile: '<sys_id>'` | `basic_auth_profile` | Stored correctly as sys_id reference to `sys_auth_profile_basic` . |
| `midServer: '<sys_id>'` | `use_mid_server` | Stored correctly as sys_id reference to `ecc_agent` . |
| Function `authenticationType` default | `authentication_type = 'inherit_from_parent'` | Written explicitly to prevent UI blank value. |

## Legacy Instance Import

Records created via the ServiceNow UI may have `authentication_type = 'basic_simple'` (legacy). The plugin imports these as `authenticationType: 'basic'`. On next deploy the value is stored as `'basic'`.

## Instance Fields Not Exposed in Fluent

| Instance Field | Table | Reason |
| `basic_auth_user` | Both | Legacy — superseded by `basicAuthProfile` |
| `basic_auth_password` | Both | Legacy — superseded by `basicAuthProfile` |
| `use_basic_auth` | Both | Legacy flag — not written by the plugin; set by older UI-created records |
| `protocol_name` | Both | Mutual auth (mTLS) not yet supported in Fluent |
| `use_mutual_auth` | Both | Mutual auth not yet supported in Fluent |
| `use_auth_mid_server` | `sys_rest_message_fn` | OAuth via MID not surfaced in Fluent |
| `qualified_name` | `sys_rest_message_fn` | Auto-generated by platform |
| `rest_message` | `sys_rest_message_fn` | Auto-set parent reference |

## See

- https://docs.servicenow.com/csh?topicname=outbound-rest-message-api-now-ts.html&version=latest

## Examples

### GET with Query Parameters

```
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

### POST with OAuth 2.0 and JSON Body

```
import { RestMessage } from '@servicenow/sdk/core';

RestMessage({
  $id: Now.ID['crm-integration'],
  name: 'CRM Integration',
  endpoint: 'https://crm.example.com/api',
  description: 'Outbound integration with CRM for contact management',
  authenticationType: 'oauth2',
  oauthProfile: '00000000000000000000000000000002',
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

### Full Example — Basic Auth, MID Server, All Methods, QueryParams

```
import { RestMessage } from '@servicenow/sdk/core';

RestMessage({
  $id: Now.ID['erp-service'],
  name: 'On-Premise ERP Service',
  endpoint: 'https://internal.corp.example.com/erp/api',
  description: 'ERP integration routed through MID server with basic auth',
  authenticationType: 'basic',
  basicAuthProfile: '00000000000000000000000000000001',
  access: 'packagePrivate',
  headers: [
    { $id: Now.ID['erp-header-content-type'], name: 'Content-Type', value: 'application/json' },
    { $id: Now.ID['erp-header-accept'],       name: 'Accept',       value: 'application/json' },
  ],
  functions: [
    {
      name: 'getEmployee',
      httpMethod: 'GET',
      endpoint: 'https://internal.corp.example.com/erp/api/employees/${employeeId}',
      midServer: 'd1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6',
      variables: [{ $id: Now.ID['erp-get-var-employee-id'], name: 'employeeId' }],
    },
    {
      name: 'listEmployees',
      httpMethod: 'GET',
      endpoint: 'https://internal.corp.example.com/erp/api/employees',
      midServer: 'd1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6',
      variables: [
        { $id: Now.ID['erp-list-var-limit'],  name: 'limit' },
        { $id: Now.ID['erp-list-var-offset'], name: 'offset' },
      ],
      queryParams: [
        { $id: Now.ID['erp-list-param-limit'],  name: 'limit',  value: '${limit}',  order: 1 },
        { $id: Now.ID['erp-list-param-offset'], name: 'offset', value: '${offset}', order: 2 },
      ],
    },
    {
      name: 'createEmployee',
      httpMethod: 'POST',
      endpoint: 'https://internal.corp.example.com/erp/api/employees',
      midServer: 'd1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6',
      content: '{"name":"${empName}","department":"${dept}","title":"${title}"}',
      lock: true,
      variables: [
        { $id: Now.ID['erp-create-var-emp-name'], name: 'empName' },
        { $id: Now.ID['erp-create-var-dept'],     name: 'dept' },
        { $id: Now.ID['erp-create-var-title'],    name: 'title' },
      ],
    },
    {
      name: 'updateEmployee',
      httpMethod: 'PUT',
      endpoint: 'https://internal.corp.example.com/erp/api/employees/${employeeId}',
      midServer: 'd1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6',
      content: '{"department":"${dept}","title":"${title}"}',
      variables: [
        { $id: Now.ID['erp-update-var-employee-id'], name: 'employeeId' },
        { $id: Now.ID['erp-update-var-dept'],        name: 'dept' },
        { $id: Now.ID['erp-update-var-title'],       name: 'title' },
      ],
    },
    {
      name: 'deleteEmployee',
      httpMethod: 'DELETE',
      endpoint: 'https://internal.corp.example.com/erp/api/employees/${employeeId}',
      midServer: 'd1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6',
      authenticationType: 'noAuthentication',
      variables: [{ $id: Now.ID['erp-delete-var-employee-id'], name: 'employeeId' }],
    },
  ],
});
```

### XML Payload with escapeXml

```
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

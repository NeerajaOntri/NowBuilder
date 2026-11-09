Version: 4.14.0

# Connection & Credential Aliases

Guide for creating ServiceNow Connection & Credential Aliases (`sys_alias`) using the Fluent API. Use when the user mentions connecting to external systems, storing or managing credentials, integrating with external databases, managing connections across multiple environments, authentication configuration, or shared integration settings with parent-child inheritance. Do NOT use system properties or custom tables to store connection details or credentials — use aliases instead.

## When to Use

- Integrating with external REST APIs where connection details differ per environment

- Connecting to external databases via JDBC with environment-specific credentials

- Building reusable integrations that work across multiple ServiceNow instances

- Managing OAuth tokens or API keys separately from connection configuration

- Implementing load balancing or failover with multiple active connections

## Instructions

- Choose alias type: Use `type: 'connection'` for routing to connection records (HTTP, JDBC, etc.), or `type: 'credential'` for credential-only lookups.

- Set connectionType: For connection aliases, specify which connection table backs it (`'httpConnection'`, `'jdbcConnection'`, etc.).

- Use descriptive names: Make alias names clear and purposeful — they're referenced by name in integration code.

- Add descriptions: Document the alias purpose for other developers and administrators.

- Add retry policies when needed: Create retry policies if you want automatic retries on transient failures. Omit if you want immediate failure.

- Add templates when needed: Attach configuration templates for wizard UIs when connections require complex setup.

- Leverage parent-child: Group related aliases with common configuration using parent references.

## API Reference

See the `alias-api` topic for the full property reference.

## Key Concepts

### Alias Types

Connection Alias (`type: 'connection'`) — Use this for most cases

Routes to both a connection record (HTTP endpoint, JDBC data source, etc.) AND its associated credential record. A single connection alias manages both the connection and credential together.

```
import { Alias } from '@servicenow/sdk/core'

Alias({
    $id: Now.ID['my-api'],
    name: 'My API Connection',
    type: 'connection',
    connectionType: 'httpConnection',
    // This single alias handles both connection AND credential records
})
```

Credential Alias (`type: 'credential'`) — Rarely needed

Routes to a credential record only, without an associated connection. Only use this when you need to manage credentials independently without any connection.

```
import { Alias } from '@servicenow/sdk/core'

Alias({
    $id: Now.ID['standalone-creds'],
    name: 'Standalone Credentials',
    type: 'credential',
    description: 'Credential-only alias (rare use case)',
})
```

Important: Don't create separate aliases for connection and credential — use a single `type: 'connection'` alias that manages both.

### Connection Types

When creating a connection alias, specify which connection table backs it:

| Value | Use for |
| `'httpConnection'` | HTTP/REST APIs (default) |
| `'jdbcConnection'` | Database connections |
| `'basicConnection'` | Basic (generic) connections |
| `'jmsConnection'` | JMS message queues |

### Parent-Child Hierarchies

Create a hierarchy where child aliases share configuration with a parent. This is useful for managing multiple endpoints with similar configuration.

Shared properties to populate on the child:

- `type`

- `connectionType`

- `multipleConnections`

- `configurationTemplate`

- `retryPolicy`

Important — populate shared fields on the child: In the platform UI, when you set a parent, the above fields are disabled on the child and a business rule copies them from the parent on insert. Fluent installs the record via XML import, so that business rule does not fire and the fields are left empty on the child. To ensure the child behaves correctly (and to remain consistent with how the UI would have stored the record), explicitly populate each of these fields on the child with the same values as its parent.

```
import { Alias } from '@servicenow/sdk/core'

// Parent alias with common configuration
const baseApi = Alias({
    $id: Now.ID['base-api'],
    name: 'Base API',
    type: 'connection',
    connectionType: 'httpConnection',
    multipleConnections: true,
})

// Child must repeat the parent's shared values — the platform's inheritance BR
// does not fire during Fluent install, so empty fields stay empty.
const productApi = Alias({
    $id: Now.ID['product-api'],
    name: 'Product API',
    parent: baseApi,
    type: 'connection',
    connectionType: 'httpConnection',
    multipleConnections: true,
})
```

Important: Parent reference is immutable after creation — you cannot change it later.

Cross-scope parents: If the parent is an OOB or cross-scope alias whose values you don't know at build time, set the shared fields to the values you want the child to use. Fluent does not read the parent's values at build time, so the child only ever has the values you write explicitly.

### Configuration Templates

Link an alias to a configuration template (`AliasTemplate`) to provide a guided wizard UI for administrators creating connections.

- Use a configuration template when:

- You need a guided wizard UI with custom fields for administrators

- The connection requires specific configuration beyond standard connection fields

- You want to provide default values or validation for connection setup

- The user explicitly requests or specifies a template

If using a template:

- Use existing templates if one already matches your connection requirements (check platform OOB templates or application-provided templates first)

- Always confirm with the user before using an existing template — show them the template name and fields to verify it meets their needs

- Reference user-specified template if the user explicitly provides or requests a specific template

- Create a new template only when:

- No existing template fits your connection type and field requirements

- You need custom validation, pre-edit scripts, or specialized wizard UI

- You're building a reusable integration that requires specific configuration fields

```
import { Alias, AliasTemplate } from '@servicenow/sdk/core'

const template = AliasTemplate({
    $id: Now.ID['api-template'],
    name: 'API Template',
    dynamicDataSchema: {
        connectionFields: [
            { name: 'connection.connection_url', label: 'Base URL', type: 'text', mandatory: true },
        ],
        credentialFields: [
            { name: 'credential.api_key', label: 'API Key', type: 'text', mandatory: true },
        ],
    },
    defaultDataTemplate: {
        connection: { table: 'http_connection', name: 'API Connection' },
        credential: { table: 'api_key_credentials', name: 'API Key' },
    },
})

const alias = Alias({
    $id: Now.ID['my-api'],
    name: 'My API',
    type: 'connection',
    connectionType: 'httpConnection',
    configurationTemplate: template,
})
```

See the `alias-template-guide` topic for detailed template configuration.

### Retry Policies

Retry policies control how ServiceNow handles transient failures when connecting to external systems. If you omit the `retryPolicy` field, the platform will use its default retry policies. Set `retryPolicy: ''` (empty string) if you want connections to fail immediately without retrying.

For Platform provides OOB default retry policies - Omit this field to use platform defaults.

For any other existing retry policies you can query in the instance for the `sys_retry_policy` table.

```
import { Alias, Record } from '@servicenow/sdk/core'

// Reference the platform's default HTTP retry policy
const alias = Alias({
    $id: Now.ID['my-api'],
    name: 'My API',
    type: 'connection',
    connectionType: 'httpConnection',
    retryPolicy: '<ef751ff07301330025d71afe2ff6a7f9>', // Replace with actual retry policy sys_id
})
```

When to create a custom retry policy: see `retry-policy-guide` for detailed configuration options.

- You need specific retry counts or intervals different from platform defaults

- You want exponential backoff instead of fixed intervals

- You need to honor `Retry-After` headers (HTTP only)

- You want to retry only on specific HTTP status codes or error conditions

```
import { Alias, RetryPolicy } from '@servicenow/sdk/core'

// Create a custom retry policy for specific requirements
const apiRetryPolicy = RetryPolicy({
    $id: Now.ID['api-retry'],
    name: 'API Retry',
    retryStrategy: 'exponential_backoff',
    count: 5,
    interval: 5,
    condition: 'status_codeIN429,500,502,503,504',
    restrictTo: ['http_method', 'status_code', 'error', 'response_body', 'response_headers'],
})

const alias = Alias({
    $id: Now.ID['my-api'],
    name: 'My API',
    type: 'connection',
    retryPolicy: apiRetryPolicy,
})
```

Note: Omit `retryPolicy` to use platform default retry policies, or set `retryPolicy: ''` to fail immediately without retrying.

See the `retry-policy-guide` topic for retry strategy patterns and detailed configuration options.

### Multiple Connections

Allow multiple active connection records per domain for load balancing or failover:

```
import { Alias } from '@servicenow/sdk/core'

Alias({
    $id: Now.ID['load-balanced'],
    name: 'Load Balanced API',
    type: 'connection',
    multipleConnections: true,
})
```

## Validation and Constraints

### Name Character Restrictions

Alias names must match the pattern: `[A-Za-z0-9_ @./()#&+\-=!*]`

```
// ✅ Valid
Alias({
    $id: Now.ID['valid'],
    name: 'My API (v2) @prod ./env',
    type: 'connection',
})

// ✗ Invalid: < and > not allowed
Alias({
    $id: Now.ID['invalid'],
    name: 'My API <v2>',  // Build error
    type: 'connection',
})
```

### Immutable Parent Field

Once an alias is created with a parent, the parent reference cannot be changed:

```
// Initial creation - OK
const child = Alias({
    $id: Now.ID['child'],
    name: 'Child Alias',
    type: 'connection',
    parent: Now.ID['parent-1'],
})

// Later update attempting to change parent - ERROR
const child = Alias({
    $id: Now.ID['child'],
    name: 'Child Alias',
    type: 'connection',
    parent: Now.ID['parent-2'],  // Runtime error
})
```

## Examples

### Basic HTTP API integration

```
import { Alias } from '@servicenow/sdk/core'

export const salesforceApi = Alias({
    $id: Now.ID['salesforce-api'],
    name: 'Salesforce REST API',
    type: 'connection',
    connectionType: 'httpConnection',
    description: 'Salesforce integration for customer data sync',
})
```

### Database connection

```
import { Alias } from '@servicenow/sdk/core'

export const dataWarehouse = Alias({
    $id: Now.ID['data-warehouse'],
    name: 'Data Warehouse',
    type: 'connection',
    connectionType: 'jdbcConnection',
    description: 'JDBC connection to analytics database',
})
```

### Credential-only alias

```
import { Alias } from '@servicenow/sdk/core'

export const oauthToken = Alias({
    $id: Now.ID['oauth-token'],
    name: 'OAuth Token',
    type: 'credential',
    description: 'Shared OAuth token for multiple API endpoints',
})
```

### Multi-endpoint integration with parent-child

```
import { Alias } from '@servicenow/sdk/core'

// Parent with common configuration
const baseErp = Alias({
    $id: Now.ID['base-erp'],
    name: 'Base ERP Connection',
    type: 'connection',
    connectionType: 'httpConnection',
    multipleConnections: false,
    description: 'Base configuration for ERP integrations',
})

// Child aliases for specific modules — repeat the parent's shared fields
// (`type`, `connectionType`, `multipleConnections`) so they are populated on
// install; the platform's inheritance BR does not fire during Fluent import.
export const erpInventory = Alias({
    $id: Now.ID['erp-inventory'],
    name: 'ERP Inventory API',
    type: 'connection',
    connectionType: 'httpConnection',
    multipleConnections: false,
    parent: baseErp,
    description: 'Inventory management endpoint',
})

export const erpOrders = Alias({
    $id: Now.ID['erp-orders'],
    name: 'ERP Orders API',
    type: 'connection',
    connectionType: 'httpConnection',
    multipleConnections: false,
    parent: baseErp,
    description: 'Order processing endpoint',
})

export const erpShipping = Alias({
    $id: Now.ID['erp-shipping'],
    name: 'ERP Shipping API',
    type: 'connection',
    connectionType: 'httpConnection',
    multipleConnections: false,
    parent: baseErp,
    description: 'Shipping and logistics endpoint',
})
```

### Complete integration with template and retry

```
import { Alias, AliasTemplate, RetryPolicy } from '@servicenow/sdk/core'

// 1. Retry policy
const apiRetry = RetryPolicy({
    $id: Now.ID['external-api-retry'],
    name: 'External API Retry',
    connectionType: 'http_retry_conditions',
    retryStrategy: 'exponential_backoff',
    count: 3,
    interval: 5,
    condition: 'status_codeIN429,500,502,503,504',
    restrictTo: ['status_code'],
})

// 2. Configuration template
const apiTemplate = AliasTemplate({
    $id: Now.ID['external-api-template'],
    name: 'External API Template',
    dynamicDataSchema: {
        connectionFields: [
            { 
                name: 'connection.connection_url', 
                label: 'API Base URL', 
                type: 'text', 
                mandatory: true,
                hint: 'Enter the base URL for the API endpoint'
            },
            {
                name: 'connection.timeout',
                label: 'Timeout (seconds)',
                type: 'number',
                defaultValue: 30,
            },
        ],
        credentialFields: [
            { 
                name: 'credential.api_key', 
                label: 'API Key', 
                type: 'text', 
                mandatory: true 
            },
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: 'External API Connection',
            connectionUrl: 'https://api.example.com',
        },
        credential: {
            table: 'api_key_credentials',
            name: 'External API Key',
        },
    },
})

// 3. Complete alias with references to retry policy and alias template
export const externalApi = Alias({
    $id: Now.ID['external-api'],
    name: 'External API',
    type: 'connection',
    connectionType: 'httpConnection',
    configurationTemplate: apiTemplate,
    retryPolicy: apiRetry,
    description: 'Primary external API integration with wizard UI and retry logic',
})
```

## Configuring the alias after deployment

Fluent defines the alias record (`sys_alias`), but the underlying connection and credential values are environment-specific runtime data and are not part of the Fluent source — they are configured on each ServiceNow instance by an administrator after the app is deployed.

After running `now-sdk install`, the CLI summary lists every record that was created or updated, including each `sys_alias` you defined. Each alias entry includes a direct link to the alias record on the target instance, for example:

```
✓ sys_alias  Salesforce REST API
   → https://<instance>.service-now.com/sys_alias.do?sys_id=<alias-sys-id>
```

Open the link and configure the alias from the instance UI:

- Connection — set the connection URL, MID server, and any transport-specific options. For HTTP connections you can also create or pick the connection record on the Connection related list.

- Credentials — pick or create the matching credential record (Basic Auth, OAuth, API Key, JWT Bearer, etc.) on the Credentials related list. These records hold the secrets and must not be stored in the Fluent source.

- Configuration Template — if the alias references a `configurationTemplate`, the template's dynamic-data form opens automatically; fill in the wizard fields and the platform creates the connection and credential records for you.

- Multiple connections — if `multipleConnections: true`, you can add more than one connection on the related list and the platform will route traffic across them per domain.

The alias `sys_id` is deterministic across builds (it is derived from `Now.ID['<name>']`), so the link is stable: re-deploying does not change the URL, and any connection/credential records you attach on the instance stick to the same alias record across releases.

## Best Practices

- Use descriptive names: Make alias names clear and purposeful — `'Salesforce REST API'` not `'API 1'`

- Add descriptions: Document the alias purpose for other developers

- Leverage parent-child: Group related aliases with common configuration

- Add retry policies for resilience: Include `retryPolicy` if you want automatic retries on transient failures

- Use templates when needed: Provide wizard UIs for complex connection setups, not for simple HTTP connections

- Plan hierarchy: Design parent-child relationships upfront — parent references are immutable

- Never commit secrets: Connection URLs that change per environment, usernames, passwords, OAuth tokens, and API keys belong on the instance — not in the Fluent source. The alias is the contract; the values are configured post-deployment.

## Related Topics

- `alias-api` — Full API reference for Alias

- `alias-template-guide` — Creating configuration templates with wizard UIs

- `retry-policy-guide` — Configuring retry behavior for connections

- `external-services-guide` — Patterns for external system integrations

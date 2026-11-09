Version: 4.14.0

# Alias

Creates a Connection & Credential Alias (`sys_alias`) — a named handle that integrations, Flow Designer actions, and scripts use to reference a connection and credential pair without hard-coding instance-specific values. Reference fields like `configurationTemplate`, `retryPolicy`, and `parent` accept a sys_id string, a `Record` reference, or the corresponding Fluent call (`AliasTemplate()`, `RetryPolicy()`, `Alias()`) directly.

## Signature

```
Alias(config)
```

## Parameters

### config

`Alias & Meta`

An object containing the properties of the Connection Alias.

Properties:

- 
$id (required): `string | number | ExplicitKey<string>`

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit/view access for other developers after the application is installed. `'read'` lets others see the script logic but not change it. `'protected'` prevents others from changing the record. Omit to allow other developers to customize this record.

- 
name (required): `string`
Display name for the Connection & Credential Alias.

- 
type (optional): `'connection' | 'credential'`
`'connection'` (default) creates a Connection and Credential alias. `'credential'` creates a credential-only alias.

- 
connectionType (optional): `'httpConnection' | 'jdbcConnection' | 'basicConnection' | 'jmsConnection'`
The underlying connection type. Defaults to `'httpConnection'`. Only applies when `type` is `'connection'`.

- 
description (optional): `string`
A description of the alias.

- 
parent (optional): `string | Record<'sys_alias'> | Alias`
Parent alias reference. Used for child aliases that inherit configuration from a parent. Pass a sys_id string, a `Record<'sys_alias'>` reference, or an `Alias()` call directly. Not supported for credential-only aliases.

- 
configurationTemplate (optional): `string | Record<'sys_alias_templates'> | AliasTemplate`
Reference to a configuration template. Pass the template's sys_id string, a `Record<'sys_alias_templates'>` reference, or an `AliasTemplate()` call directly.

- 
retryPolicy (optional): `string | Record<'sys_retry_policy'> | RetryPolicy`
Default retry policy reference. Only applies when `type` is `'connection'`. Pass a sys_id string, a `Record<'sys_retry_policy'>` reference, or a `RetryPolicy()` call directly. When omitted, the plugin fills in the OOB default for the resolved `connectionType`.

- 
multipleConnections (optional): `boolean`
Whether the alias supports multiple active connections. Defaults to `false`. Only applies when `type` is `'connection'`.

- 
$meta (optional): `object`

- installMethod: `'first install' | 'demo' | 'once'`
Map a record to an output folder that loads only in specific circumstances.
'first install' -> 'unload',
'demo' -> 'unload.demo'

## See

- The `alias-guide` topic

## Examples

### Basic HTTP Connection Alias

Create a basic HTTP connection alias that integrations can reference

```
/**
 * @title Basic HTTP Connection Alias
 * @description Create a basic HTTP connection alias that integrations can reference
 */
import { Alias } from '@servicenow/sdk/core'

Alias({
    $id: Now.ID['my_http_alias'],
    name: 'My HTTP Connection',
    description: 'HTTP connection for external API',
})
```

### Alias referencing a configuration template by sys_id

Pass the configuration template's sys_id directly

```
/**
 * @title Alias referencing a configuration template by sys_id
 * @description Pass the configuration template's sys_id directly
 */
import { Alias } from '@servicenow/sdk/core'

Alias({
    $id: Now.ID['my_oauth_alias'],
    name: 'My OAuth Connection',
    configurationTemplate: 'ddfc6a34873233008f64bd6ec7cb0b33',
    description: 'OAuth-protected external service',
})
```

### Credential-Only Alias

Create a credential-only alias (no connection record)

```
/**
 * @title Credential-Only Alias
 * @description Create a credential-only alias (no connection record)
 */
import { Alias } from '@servicenow/sdk/core'

Alias({
    $id: Now.ID['my_credential_alias'],
    name: 'My Credential',
    type: 'credential',
    description: 'Reusable credential reference',
})
```

### JDBC Connection with Multiple Connections

Configure a JDBC alias that supports multiple active connections

```
/**
 * @title JDBC Connection with Multiple Connections
 * @description Configure a JDBC alias that supports multiple active connections
 */
import { Alias } from '@servicenow/sdk/core'

Alias({
    $id: Now.ID['my_jdbc_alias'],
    name: 'My JDBC Connection',
    connectionType: 'jdbcConnection',
    multipleConnections: true,
    description: 'JDBC data source for reporting',
})
```

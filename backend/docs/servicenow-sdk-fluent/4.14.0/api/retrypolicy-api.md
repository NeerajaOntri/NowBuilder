Version: 4.14.0

# RetryPolicy

Creates a Retry Policy record (`sys_retry_policy`) that controls how outbound integration connections handle transient failures. A retry policy defines the strategy, attempt count, wait interval, maximum elapsed time, and the conditions under which retries apply.

## Signature

```
RetryPolicy(config)
```

## Parameters

### config

`RetryPolicy`

Configuration for the retry policy.

Properties:

- 
$id (required): `string | number | ExplicitKey<string>`

- 
name (optional, default: `''`): `string`
Display name shown in the retry policy list.

- 
connectionType (optional, default: `'http_retry_conditions'`): `'http_retry_conditions' | 'jdbc_retry_conditions' | 'basic_retry_conditions'`
Connection type this policy applies to.

- 'http_retry_conditions': Outbound HTTP/REST connections.

- 'jdbc_retry_conditions': JDBC database connections.

- 'basic_retry_conditions': SFTP connections.

- 
retryStrategy (optional, default: `'fixed_time_interval'`): `'fixed_time_interval' | 'exponential_backoff' | 'retry_after'`
Strategy for calculating wait time between retry attempts.

- 'fixed_time_interval': Waits a constant `interval` seconds between attempts.

- 'exponential_backoff': Doubles the wait time after each failure.

- 'retry_after': Honors the HTTP `Retry-After` response header. Only valid when `connectionType` is `'http_retry_conditions'`.

- 
count (optional): `number`
Maximum number of retry attempts. Not valid when `retryStrategy` is `'retry_after'`.

- 
interval (optional): `number`
Wait interval between retries in seconds. Used with `'fixed_time_interval'` and `'exponential_backoff'` strategies. Not valid when `retryStrategy` is `'retry_after'`.

- 
maxElapsedTime (optional): `number`
Maximum total time budget for all retry attempts in seconds. Required when `retryStrategy` is `'retry_after'`; not valid for other strategies. Must not exceed `86400` (24 hours).

- 
condition (optional, default: `''`): `string`
Encoded query condition that determines when to retry after a failed attempt. Only valid when `connectionType` is `'http_retry_conditions'`.

- Example: `'status_codeIN429,500,502,503,504'` - Retry on specific status codes

- Example: `'status_code=429^ORstatus_codeBETWEEN500@599'` - Retry on 429 or 5xx errors

- 
restrictTo (optional, default: `['http_method', 'status_code', 'error', 'response_body', 'response_headers']`): `string[]`
Fields evaluated in the condition.

- Omit this field to use the platform default set of fields.

- Provide an empty array `[]` to explicitly clear all fields (no field evaluation).

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls whether other developers can view or edit this record after the application is installed.

- 'read': Allows viewing the configuration but prevents edits.

- 'protected': Hides and locks the record entirely.

- undefined: Allows full customization by other developers.

## Type Safety

The `RetryPolicy` type uses a discriminated union with three variants (`RetryAfter`, `HttpRetry`, `NonHttpRetry`) to enforce field constraints at compile-time. Most invalid configurations are TypeScript errors:

- `retry_after` with `count` or `interval` → TypeScript error

- `retry_after` without `maxElapsedTime` → TypeScript error

- `retry_after` with non-HTTP connection type → TypeScript error

- `maxElapsedTime` with non-`retry_after` strategies → TypeScript error

- `condition` with JDBC/SFTP connections → TypeScript error

Runtime validation (build-time):

| Rule | Error |
| `maxElapsedTime` exceeds 86400 seconds | Error on `maxElapsedTime` |

## Examples

### HTTP policy with exponential backoff

```
import { RetryPolicy } from '@servicenow/sdk/core'

export const httpRetryPolicy = RetryPolicy({
    $id: Now.ID['rest-exponential-retry'],
    name: 'REST API Exponential Backoff',
    connectionType: 'http_retry_conditions',
    retryStrategy: 'exponential_backoff',
    count: 5,
    interval: 5,
    condition: 'status_codeIN429,500,502,503,504',
    restrictTo: ['status_code', 'error'],
})
```

### HTTP policy honoring Retry-After header

```
import { RetryPolicy } from '@servicenow/sdk/core'

export const retryAfterPolicy = RetryPolicy({
    $id: Now.ID['retry-after-policy'],
    name: 'Honour Retry-After Header',
    connectionType: 'http_retry_conditions',
    retryStrategy: 'retry_after',
    maxElapsedTime: 120,
    condition: 'status_codeIN429,503',
    restrictTo: ['status_code'],
})
```

### JDBC policy with fixed interval

```
import { RetryPolicy } from '@servicenow/sdk/core'

export const jdbcRetryPolicy = RetryPolicy({
    $id: Now.ID['jdbc-retry-policy'],
    name: 'JDBC Database Retry',
    connectionType: 'jdbc_retry_conditions',
    retryStrategy: 'fixed_time_interval',
    count: 3,
    interval: 10,
})
```

For patterns on choosing the right retry strategy and handling different connection types, see the `retry-policy-guide` topic.

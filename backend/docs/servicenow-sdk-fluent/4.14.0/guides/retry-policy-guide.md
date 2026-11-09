Version: 4.14.0

# Retry Policies

Guide for creating ServiceNow Retry Policies using the Fluent API. Retry policies control how outbound integration connections recover from transient failures by defining when to retry, how many times, and how long to wait between attempts.

## When to Use

- Automatically retry failed requests when a step encounters an intermittent issue such as a network failure or request rate limit, to prevent having to manually trigger the step again

- Outbound HTTP/REST calls that may encounter rate limits (`429`) or temporary server errors (`500`, `502`, `503`, `504`)

- JDBC connections that may fail transiently on database restarts or network hiccups

- SFTP connections that require retry logic for reliability

## Instructions

- Choose `connectionType` first: The connection type determines which retry conditions and strategies are available. Most use cases are HTTP (`'http_retry_conditions'`).

- Pick the right strategy: `'fixed_time_interval'` and `'exponential_backoff'` use `count` and `interval`; `'retry_after'` uses only `maxElapsedTime` and honors the HTTP `Retry-After` header.

- Scope with `condition`: Use an encoded query on `restrictTo` fields to limit retries to the right error types. This prevents retrying on non-recoverable errors (e.g., `400 Bad Request`).

- Set `restrictTo` narrowly: Only include the fields your condition actually uses to avoid evaluating irrelevant conditions.

## API Reference

See the `retrypolicy-api` topic for the full property reference.

## Key Concepts

### Retry Strategies

`fixed_time_interval` (default)

Waits exactly `interval` seconds after each failed attempt before retrying. Use when the downstream service needs a predictable recovery window.

```
RetryPolicy({
    $id: Now.ID['fixed-retry'],
    retryStrategy: 'fixed_time_interval',
    count: 3,
    interval: 10,
})
```

`exponential_backoff`

Exponentially increases the time interval for subsequent retry attempts. The multiplier is 2 — each wait is double the previous. Start with a short `interval` (e.g., 5 seconds) and let backoff handle growth.

```
RetryPolicy({
    $id: Now.ID['exponential-retry'],
    retryStrategy: 'exponential_backoff',
    count: 5,
    interval: 5,
})
```

`retry_after`

Retries based on the date and time value returned in the `Retry-After` header of the HTTP response. The header value can be either an HTTP-date or a delay in seconds. Requires `maxElapsedTime` and is only valid with `connectionType: 'http_retry_conditions'` (REST steps).

```
RetryPolicy({
    $id: Now.ID['retry-after'],
    connectionType: 'http_retry_conditions',
    retryStrategy: 'retry_after',
    maxElapsedTime: 300,
})
```

`count` and `interval` are not valid with `retry_after` — the wait time comes from the response header, not a fixed value.

### Condition and restrictTo

Use `condition` (an encoded query) to limit retries to specific failure scenarios. The `restrictTo` array declares which fields your condition references — only include fields actually used in the condition.

Encoded query operators:

- `IN` - Match any value in a list: `status_codeIN429,500,502`

- `^OR` - Logical OR: `status_code=429^ORstatus_code=503`

- `BETWEEN` - Range: `status_codeBETWEEN500@599`

- `ISNOTEMPTY` - Field has a value: `endpoint_errorISNOTEMPTY`

```
// Example 1: Retry on specific status codes or any error message
RetryPolicy({
    $id: Now.ID['selective-retry'],
    connectionType: 'http_retry_conditions',
    retryStrategy: 'exponential_backoff',
    count: 5,
    interval: 5,
    condition: 'status_codeIN429,500,502,503,504^ORendpoint_errorISNOTEMPTY',
    restrictTo: ['status_code', 'error'],
})

// Example 2: Retry on 429 or any 5xx error
RetryPolicy({
    $id: Now.ID['rate-limit-or-5xx'],
    connectionType: 'http_retry_conditions',
    retryStrategy: 'retry_after',
    maxElapsedTime: 300,
    condition: 'status_code=429^ORstatus_codeBETWEEN500@599',
    restrictTo: ['status_code'],
})
```

`condition` is only valid for HTTP connections — it is not supported for JDBC or SFTP (`basic_retry_conditions`).

### maxElapsedTime

Sets a ceiling on the total retry window in seconds. Required for `retry_after`; an error for all other strategies. Must not exceed `86400` (24 hours).

```
// ✅ Valid: retry_after requires maxElapsedTime
RetryPolicy({
    $id: Now.ID['bounded-retry'],
    retryStrategy: 'retry_after',
    maxElapsedTime: 120,
})

// ✗ Invalid: maxElapsedTime not allowed with fixed_time_interval
RetryPolicy({
    $id: Now.ID['bad-retry'],
    retryStrategy: 'fixed_time_interval',
    count: 3,
    interval: 10,
    maxElapsedTime: 60, // build error
})
```

### Connection Types

| Value | Use for |
| `'http_retry_conditions'` | REST / outbound HTTP integrations |
| `'jdbc_retry_conditions'` | JDBC database connections |
| `'basic_retry_conditions'` | SFTP connections |

`condition` and `retry_after` strategy are only supported for `'http_retry_conditions'`.

## Examples

### Rate-limited API (retry_after)

For APIs like Salesforce or external SaaS that return `429 Too Many Requests` with a `Retry-After` header:

```
import { RetryPolicy } from '@servicenow/sdk/core'

export const salesforceRetry = RetryPolicy({
    $id: Now.ID['salesforce-retry'],
    name: 'Salesforce Rate Limit Retry',
    connectionType: 'http_retry_conditions',
    retryStrategy: 'retry_after',
    maxElapsedTime: 300,
    condition: 'status_codeIN429',
    restrictTo: ['status_code'],
})
```

### Resilient REST integration (exponential backoff)

For outbound REST calls that may encounter transient server errors:

```
import { RetryPolicy } from '@servicenow/sdk/core'

export const restRetry = RetryPolicy({
    $id: Now.ID['rest-retry'],
    name: 'REST API Retry',
    connectionType: 'http_retry_conditions',
    retryStrategy: 'exponential_backoff',
    count: 5,
    interval: 5,
    condition: 'status_codeIN500,502,503,504',
    restrictTo: ['http_method', 'status_code', 'error', 'response_body', 'response_headers'],
})
```

### JDBC connection retry

For database connections that may fail during short outages:

```
import { RetryPolicy } from '@servicenow/sdk/core'

export const dbRetry = RetryPolicy({
    $id: Now.ID['db-retry'],
    name: 'Database Connection Retry',
    connectionType: 'jdbc_retry_conditions',
    retryStrategy: 'fixed_time_interval',
    count: 3,
    interval: 10,
})
```

## Related Topics

- `retrypolicy-api` — Full property reference for `RetryPolicy`

- `alias-guide` — Creating Connection & Credential Aliases that use retry policies

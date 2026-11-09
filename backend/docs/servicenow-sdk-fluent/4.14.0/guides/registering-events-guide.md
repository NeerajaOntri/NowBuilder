Version: 4.14.0

# Registering Events Guide

Guide for registering custom ServiceNow events in the Event Registry (`sysevent_register`) using the Record API, including custom queue configuration for high-volume event processing. Use when a custom event name is referenced, when building event-driven applications, or when the user mentions event registry, custom events, `gs.eventQueue()`, or custom queues.

## When to Use

- Use proactively as a prerequisite step whenever a custom event name is referenced. The event must be registered before it can be fired or consumed.

- When building event-driven applications that need to fire or consume custom events.

- When the user mentions "event registry", "register event", "custom event", `gs.eventQueue()`, or `sysevent_register`.

- When the user mentions "custom queue", "event queue", or high-volume event processing.

### When to Use Event-Based Approach

| Scenario | Use Event-Based? |
| Single reaction to a record change | No -- direct action is simpler |
| One trigger, multiple independent reactions | Yes |
| Passing contextual data to downstream consumers | Yes |
| Asynchronous processing that shouldn't block the user | Yes |

## Instructions

- Use the Record API: There is no dedicated Fluent plugin for `sysevent_register`. Always use `Record()` with `table: 'sysevent_register'`.

- Scope-aware field usage:

- Global apps: Set `event_name` directly. Leave `suffix` blank.

- Scoped apps: Set both `suffix` AND `event_name: '<scope>.<suffix>'` explicitly. The platform does not auto-generate `event_name` on initial Record API creation.

- CRITICAL -- 40-character limit on `event_name`: Values longer than 40 characters are silently truncated. Always verify `<scope>.<suffix>` fits within 40 characters.

- Derive `$id` from the event name: Use a stable `$id` that maps 1-to-1 with the event name to prevent duplicate records on rebuild.

- Never set `derived_priority`: It is read-only and auto-computed.

- Register before firing: The event must exist before any code calls `gs.eventQueue()` or fires from Flow Designer.

- Always populate `fired_by`: Document what fires the event for maintainability.

- Always export the Record when used with flows: So flows can import and reference `myEvent.$id`.

- Use custom queues for high-volume events: Prevents flooding the default processor and allows serial processing to avoid race conditions.

## Avoidance

- Never omit `event_name` in scoped apps -- always set it explicitly as `<scope>.<suffix>` alongside `suffix`.

- Never omit `suffix` in scoped apps -- it is mandatory alongside `event_name`.

- Never modify `suffix` on existing scoped events -- changing it regenerates `event_name` and breaks all listeners.

- Never exceed 40 characters for `event_name` -- silently truncated with no warning.

- Never use two different `$id` values for the same `event_name` -- creates duplicate registrations causing listeners to fire twice.

- Never fire an event before registering it -- fails silently in scoped apps.

- Never leave `fired_by` blank.

- Never pass priority as a String -- the field expects an integer.

- Never forget to export the event Record when referenced by a flow.

## Event Registry API Reference

Register events using `Record()` with `table: 'sysevent_register'`.

### Data Fields

| Name | Type | Mandatory | Description |
| `event_name` | String (max 40) | -- | Primary identifier. Scoped: set as `<scope>.<suffix>` . Global: set directly. |
| `suffix` | String (max 40) | Yes (scoped) | Mandatory in scoped apps alongside `event_name` . Not used in global apps. |
| `description` | String (max 100) | -- | When and why the event fires. |
| `table` | String (max 80) | -- | Associated ServiceNow table. |
| `fired_by` | String (max 100) | -- | What code fires the event (required for traceability). |
| `priority` | integer | -- | Processing order (lower = higher priority). Default: `100` . |
| `queue` | String | -- | Custom queue name. Must match an existing `sysevent_queue` record. |
| `caller_access` | String (choice) | -- | Cross-scope access: `''` (none), `'1'` (tracking), `'2'` (restriction). |
| `derived_priority` | Float | -- | READ-ONLY. Never set this field. |

### Caller Access Values

| Value | UI Label | Behavior |
| `''` (default) | None | No restriction. Any caller can fire the event. |
| `'1'` | Caller Tracking | Cross-scope allowed but logged. |
| `'2'` | Caller Restriction | Cross-scope blocked by default; admin approval required. |

### Priority and queues

- `priority` defaults to `100`. Lower value = higher priority when multiple registrations or listeners compete.

- `queue` Omit this field to use the system default queue for event processing.

- Decision criteria for custom queues:

| Scenario | Recommendation |
| Low/moderate frequency (tens per hour) | ❌ Default queue is sufficient |
| High volume (hundreds/thousands per batch) | ✅ Custom queue to isolate traffic |
| Events that must not race each other | ✅ Custom queue with sequential mode |
| Isolation from other apps' event traffic | ✅ Custom queue |

The default queue processes events in parallel across multiple workers. A custom queue lets you control processing mode (parallel or sequential), scale factor, and poll interval independently.

→ See Custom Queue Registration below for detailed setup instructions, queue naming conventions, configuration options, and examples.

## Examples

### Scoped App Event Registration

```
import { Record } from '@servicenow/sdk/core';

Record({
  $id: Now.ID['x-myapp-incident-approved-event'],
  table: 'sysevent_register',
  data: {
    suffix: 'incident.approved',
    event_name: 'x_myapp.incident.approved',
    description: 'Fired when an incident is approved in My App',
    table: 'incident',
    fired_by: 'Business Rule: My App Incident Approvals',
    priority: 200,
  },
});
```

### Global App Event Registration

```
import { Record } from '@servicenow/sdk/core';

Record({
  $id: Now.ID['incident-approved-event'],
  table: 'sysevent_register',
  data: {
    event_name: 'incident.approved',
    description: 'Fired when an incident is approved',
    table: 'incident',
    fired_by: 'Business Rule: Incident Approvals',
    priority: 100,
  },
});
```

### Event with Caller Tracking

```
import { Record } from '@servicenow/sdk/core';

Record({
  $id: Now.ID['x-myapp-contract-expiring-event'],
  table: 'sysevent_register',
  data: {
    suffix: 'contract.expiring',
    event_name: 'x_myapp.contract.expiring',
    description: 'Fired when a contract is within 30 days of expiry',
    table: 'x_myapp_contract',
    fired_by: 'Business Rule: Contract Expiry Check',
    priority: 100,
    caller_access: '1',
  },
});
```

### Event-Driven Flow with Email Notification

Three-file pattern: Event Registration, Flow (`fireEvent`), Email Notification.

File 1: Register and export the event:

```
import { Record } from '@servicenow/sdk/core';

export const employeeTerminatedEvent = Record({
  $id: Now.ID['sn-myapp-employee-terminated-event'],
  table: 'sysevent_register',
  data: {
    suffix: 'employee.terminated',
    event_name: 'sn_myapp.employee.terminated',
    description: 'Fired when employee status changes to Terminated',
    table: 'sn_myapp_employee_record',
    fired_by: 'Flow: Notify manager on termination',
    priority: 100,
  },
});
```

File 2: Flow fires the event using `employeeTerminatedEvent.$id` (resolves to sys_id).

File 3: Notification references event by name string `'sn_myapp.employee.terminated'`.

Critical difference: The Flow uses `.$id` (sys_id reference). The Notification uses the event name string. Mixing them up causes errors.

### Event-Driven Business Rule with Script Action

Four-file pattern: Event Registration, Business Rule (`gs.eventQueue`), ScriptAction, Email Notification.

The business rule fires via `gs.eventQueue('sn_myapp.new.employee.added', current, parm1, parm2)`. The ScriptAction and EmailNotification both reference the full event name string in their `eventName` fields.

## Custom Queue Registration

Use a custom queue when your app generates high volumes of events or when events must be processed serially.

### Queue Naming Convention

Scoped apps: `<scope_name>.<suffix>` (suffix is mandatory).
Global apps: Plain unique name (no suffix field).

### ⛔ CRITICAL: Pre-Installation Uniqueness Check

Before creating any queue record, you MUST query the `sysevent_queue` table to verify your intended queue name does not already exist. Queue names must be unique across the entire table. Duplicate queue names cause conflicts in event routing and processing.

Always query in the instance before building/installing:

Query `sysevent_queue` with encodedQuery: `queue=<your_intended_queue_name>`

If a conflict is found:

| Application Type | Resolution |
| Scoped app | Change both the `suffix` and the `queue` value to `<scope>.<new_suffix>` |
| Global app | Change the `queue` name directly |

Example conflicts:

- Intended: `sn_my_app.email_queue` → already exists → Change to: `sn_my_app.email_notification_queue`

- Intended: `batch_processor` → already exists → Change to: `async_batch_processor`

### Choosing the Right Configuration

Use this decision matrix to select appropriate queue settings based on your use case:

| Use Case | Poll Interval | Processing Order | Jobs | Provider |
| General event handling | 30s | `parallel` | 1 | Event Provider |
| High-volume processing | 2–5s | `parallel` | 2-3 | NowMQ Provider |
| Ordered task execution | 10–30s | `sequential` | 1 | Event Provider |
| Background batch jobs | 1–10 min | `parallel` | 1 | Event Provider |
| Low-latency interactive flows | 1–2s | `parallel` | 2 | NowMQ Provider |

### Pre-Installation Checklist

Before building and installing your custom queue:

- ⛔ Query `sysevent_queue` for your intended queue name — ensure it doesn't already exist

- ✅ Include `sys_class_name: "sysevent_queue"` in the record data (required for installation)

- ✅ Set `suffix` if scoped app; omit `suffix` if global app

- ✅ Use `<scope>.<suffix>` format for `queue` in scoped apps; plain name for global

- ✅ Verify the provider sys_id exists on the target instance

- ✅ Build and install

- ✅ Post-install verification — query `sysevent_queue` to confirm the record was created

### Custom Queue Properties

| Field | Type | Mandatory | Description |
| `sys_class_name` | string | Yes | Must be `"sysevent_queue"` for correct installation. |
| `queue` | string | Yes | Full queue name. |
| `suffix` | string | Scoped: Yes | Portion after scope prefix. |
| `poll_interval` | glide_duration | Yes | Format: `"1970-01-01 HH:mm:ss"` . |
| `job_config` | string | No | `"jobs_per_node"` or `"job_count"` . |
| `job_config_value` | integer | Yes | Number of concurrent jobs. |
| `provider` | reference | Yes | sys_id of `sysevent_queue_provider` record. |
| `processing_order` | string | No | `"parallel"` or `"sequential"` . |

### Available Providers

| Provider | sys_id | Description |
| Event Provider | `44af4464431212108da9a574a9b8f2f5` | Default; uses Processing Framework |
| NowMQ Provider | `3ccf4464431212108da9a574a9b8f2fb` | In-memory queue for high throughput |

Tip: Use Event Provider for standard use cases. Use NowMQ Provider for high-throughput, low-latency scenarios.

### Poll Interval Format

The `poll_interval` field uses the `glide_duration` type with the format `"1970-01-01 HH:mm:ss"`.

Common values:

| Duration | Value |
| 1 second | `"1970-01-01 00:00:01"` |
| 5 seconds | `"1970-01-01 00:00:05"` |
| 30 seconds | `"1970-01-01 00:00:30"` |
| 1 minute | `"1970-01-01 00:01:00"` |
| 10 minutes | `"1970-01-01 00:10:00"` |

### Configuration Reference

#### `job_config` Options

| Value | Behavior |
| `jobs_per_node` | `job_config_value` specifies the number of jobs per application node |
| `job_count` | `job_config_value` specifies the total number of jobs across all nodes |

#### `processing_order` Options

| Value | Behavior |
| `parallel` | Events are processed concurrently (faster, no ordering guarantee) |
| `sequential` | Events are processed one at a time in order (slower, order preserved) |

### Examples

#### Example 1: Scoped App — Basic Parallel Processing

A standard scoped event queue with 30-second polling and parallel processing.

```
import { Record } from '@servicenow/sdk/core';

// Step 1: Create the queue
Record({
  $id: Now.ID['my_app_custom_queue'],
  table: 'sysevent_queue',
  data: {
    sys_class_name: 'sysevent_queue',
    queue: 'sn_my_app.custom_queue',
    suffix: 'custom_queue',
    description: 'General-purpose event queue for my application.',
    poll_interval: '1970-01-01 00:00:30',
    job_config: 'jobs_per_node',
    job_config_value: 1,
    provider: '44af4464431212108da9a574a9b8f2f5',
    automatic_processing: true,
    processing_order: 'parallel',
  },
});

// Step 2: Register the event with the queue name
Record({
  $id: Now.ID['sn_my_app-contract-expiring-event'],
  table: 'sysevent_register',
  data: {
    suffix: 'contract.expiring',
    event_name: 'sn_my_app.contract.expiring',
    description: 'Fired when a contract is within 30 days of expiry',
    table: 'sn_my_app_contract',
    fired_by: 'Business Rule: Contract Expiry Check',
    priority: 100,
    queue: 'sn_my_app.custom_queue',
  },
});
```

#### Example 2: Scoped App — Sequential Batch Processing

A scoped queue for ordered batch jobs that must be processed one at a time to avoid race conditions.

```
import { Record } from '@servicenow/sdk/core';

export const batchQueue = Record({
  $id: Now.ID['my_app_batch_queue'],
  table: 'sysevent_queue',
  data: {
    sys_class_name: 'sysevent_queue',
    queue: 'sn_my_app.batch_processing',
    suffix: 'batch_processing',
    description: 'Sequential batch processing queue — events processed one at a time in order.',
    poll_interval: '1970-01-01 00:01:00',
    job_config: 'jobs_per_node',
    job_config_value: 1,
    provider: '44af4464431212108da9a574a9b8f2f5',
    automatic_processing: true,
    processing_order: 'sequential',
  },
});
```

#### Example 3: Scoped App — High-Throughput Queue with NowMQ Provider

A fast scoped queue using the in-memory NowMQ provider for high-volume event processing.

```
import { Record } from '@servicenow/sdk/core';

export const highThroughputQueue = Record({
  $id: Now.ID['my_app_fast_queue'],
  table: 'sysevent_queue',
  data: {
    sys_class_name: 'sysevent_queue',
    queue: 'sn_my_app.fast_processing',
    suffix: 'fast_processing',
    description: 'High-throughput queue using NowMQ for low-latency event processing.',
    poll_interval: '1970-01-01 00:00:02',
    job_config: 'jobs_per_node',
    job_config_value: 3,
    provider: '3ccf4464431212108da9a574a9b8f2fb',
    automatic_processing: true,
    processing_order: 'parallel',
  },
});
```

#### Example 4: Global App — Simple Event Queue

A global application queue — no suffix, plain queue name.

```
import { Record } from '@servicenow/sdk/core';

export const globalEventQueue = Record({
  $id: Now.ID['global_email_queue'],
  table: 'sysevent_queue',
  data: {
    sys_class_name: 'sysevent_queue',
    queue: 'custom_email_notifications',
    description: 'Global queue for processing email notification events.',
    poll_interval: '1970-01-01 00:00:05',
    job_config: 'job_count',
    job_config_value: 2,
    provider: '44af4464431212108da9a574a9b8f2f5',
    automatic_processing: true,
    processing_order: 'parallel',
  },
});
```

Note: Global queues do not have a `suffix` field.

### Troubleshooting

| Symptom | Cause | Fix |
| Install succeeds but queue record missing | Missing `sys_class_name` in record data | Add `sys_class_name: 'sysevent_queue'` |
| Build error on `poll_interval` | Wrong format for glide_duration | Use `"1970-01-01 HH:mm:ss"` format |
| Queue name doesn't appear correctly | Missing scope prefix in queue name | Use `<scope>.<suffix>` naming convention for scoped apps |
| Record not found after first install | Rare install timing issue | Reinstall — the record should appear on retry |
| Events not routing to custom queue | Queue name mismatch between event and queue | Verify exact queue name matches in both records |
| Duplicate queue name conflict | Queue name already exists on instance | Query `sysevent_queue` first; change suffix (scoped) or queue name (global) |
| "Event is not defined" errors | `event_name` exceeded 40 chars | Shorten `<scope>.<suffix>` to fit within 40 characters |

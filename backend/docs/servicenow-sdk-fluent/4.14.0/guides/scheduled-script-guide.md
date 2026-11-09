Version: 4.14.0

# Scheduled Script Guide

Create ServiceNow Scheduled Script Executions (`sysauto_script`) to run server-side logic on a time-based schedule. This guide covers all 11 frequency types, script file patterns, timezone handling, conditional execution, business calendar integration, and best practices.

## When to Use

- Running server-side logic at a fixed time every day, week, month, or year

- Recurring background maintenance tasks (data cleanup, archiving, cache refresh)

- Periodic data synchronization with external systems

- Generating scheduled reports or summary notifications

- Executing a script exactly once at a future date/time

- Running a script manually on-demand (no automated trigger)

- Scheduling jobs that align with business calendar entries

- Repeating at a custom interval (e.g., every 4 hours, every 30 minutes)

Proactive Usage: Consider suggesting scheduled scripts when a use case requires logic to run automatically at a set time or interval without a record trigger (e.g., "send a report every Monday" or "clean up old data nightly").

## Do NOT Use For

- Structured bulk data imports (CSV, LDAP, REST sources with transform maps)

- Multi-step orchestrations with branching conditions and discrete actions on a timer

## Instructions

- Choose `frequency` first: This determines which companion fields are required and which are ignored.

- Use `Now.include` for scripts: The ScheduledScript API only accepts strings, so reference an external `.js` file with `Now.include('./path-to-file.js')`. The script must use an IIFE: `(function() { ... })();`.

- `timeZone`: All times in `executionStart`, `executionEnd`, and `executionTime` are interpreted in the `timeZone` you set. Use `'floating'` to always match the platform's current system timezone. Avoid setting unless explicitly specified by the user.

- `executionInterval` is exclusive to `periodically`: Setting it on any other frequency is a build error.

- `daysOfWeek` is required for `weekly`: Omitting it is a build error.

- `businessCalendar` is required for calendar types: Both `business_calendar_start` and `business_calendar_end` require it.

- `executionEnd` must allow at least one execution: For recurring jobs, must be at least one full interval after `executionStart`.

## Quick Decision Guide

| User says | Use `frequency` | Required extra fields |
| "every day at X", "nightly", "daily" | `daily` | `executionTime` |
| "every Monday", "on Tuesdays and Fridays" | `weekly` | `daysOfWeek` (mandatory; array of lowercase names) |
| "first of the month", "every month on day X" | `monthly` | `dayOfMonth` (1-31; 31 = month-end) |
| "every N hours/minutes", "periodically" | `periodically` | `executionInterval` (mandatory), `executionStart` recommended |
| "once", "one-time", "migration" | `once` | `executionStart` |
| "manually", "on demand" | `on_demand` | (none) |
| "every year on [month] [day]" | `day_and_month_in_year` | `month` (1-12), `dayOfMonth` (1-31) |
| "second Monday of every month" | `week_in_month` | `weekInMonth` (1-6), `dayOfWeek` |
| "third Tuesday of March every year" | `day_week_month_year` | `dayOfWeek` , `weekInMonth` , `month` |
| "when business period starts" | `business_calendar_start` | `businessCalendar` |
| "when business period ends" | `business_calendar_end` | `businessCalendar` |

### Do I need `executionTime`?

- Recommended for: `daily`, `weekly`, `monthly`, `day_and_month_in_year`, `week_in_month`, `day_week_month_year`

- Not applicable: `periodically` (uses `executionInterval`), `once` (uses `executionStart`), `on_demand`

### Do I need `executionStart`?

- Recommended: `periodically`, `once`

- Optional: all other types (use to define when the first execution is eligible)

- If you do not have date/time context from the user, omit it -- Fluent will auto-populate with the current date/time during build.

## API Reference

For the full property reference, see the `scheduledscript-api` topic.

### Valid Frequency Values

`'daily'`, `'weekly'`, `'monthly'`, `'periodically'`, `'once'`, `'on_demand'`, `'day_and_month_in_year'`, `'day_week_month_year'`, `'week_in_month'`, `'business_calendar_start'`, `'business_calendar_end'`

## Run Type Details

- `daily` -- Runs once per day at `executionTime`.

- `weekly` -- Runs on specific weekdays. Requires `daysOfWeek` (array).

- `monthly` -- Runs on a fixed day. Requires `dayOfMonth` (1-31). Platform behavior for short months: If `dayOfMonth` is set to a day that does not exist in a given month (e.g., 29, 30, or 31 in February; 31 in April, June, September, or November), the platform runs the job on the last day of that month instead (e.g., Feb 28 or Feb 29 in a leap year). This means `dayOfMonth: 31` effectively becomes a month-end job that runs every month without skipping.

- `periodically` -- Repeats at a fixed interval. Requires `executionInterval`. Avoid seconds or single-digit minutes for performance. If a run is still executing when the next fires, the platform skips that trigger silently.

- `once` -- Runs once at `executionStart`, then stops.

- `on_demand` -- Never runs automatically; triggered manually.

- `day_and_month_in_year` -- Runs annually on a fixed date. Requires `month` + `dayOfMonth`.

- `week_in_month` -- Runs on a specific week ordinal. Requires `weekInMonth` (1-6) + `dayOfWeek`.

- `day_week_month_year` -- Runs on a specific weekday in a specific week in a specific month each year.

- `business_calendar_start` / `business_calendar_end` -- Fires when calendar entries begin/end. Requires `businessCalendar`.

## Script File Pattern

The ScheduledScript API accepts strings for its `script` property and should use `Now.include` to import the javascript code, see the `now-include-guide` topic for more information

The script file must use an IIFE (Immediately Invoked Function Expression):

```
(function () {
  // your logic here
})();
```

Reference it from the `script` field:

```
import { ScheduledScript } from '@servicenow/sdk/core'

ScheduledScript({
    $id: Now.ID['my-job'],
    name: 'My Job',
    script: Now.include('./my-job.js'),
    frequency: 'daily',
    executionTime: Time({ hours: 2, minutes: 0 }),
})
```

Note: Unlike BusinessRule and ScriptAction, the ScheduledScript API does not accept function types. Module imports will produce a TypeScript error. Use `Now.include()` or inline strings.

### Script Best Practices

- Always use an IIFE wrapper

- Add try-catch blocks for error handling

- Use `gs.info()` for success, `gs.error()` for failures, `gs.debug()` for tracing

- Keep scripts focused -- one task per scheduled script

- Use `setLimit()` when processing large datasets

- Return early on failed preconditions

- Add JSDoc comments explaining the script's purpose

## Timezone Handling

- `timeZone` -- Controls how `executionStart`, `executionEnd`, and `executionTime` are interpreted. Platform stores UTC internally.

- `'floating'` -- Always uses the platform's currently configured system timezone.

- `userTimeZone` -- Controls timezone for `GlideDateTime` calculations inside the script. Defaults to the `runAs` user's profile timezone.

## executionTime Format Options

The `executionTime` field accepts two formats:

### Raw Object Format (Recommended for Simple Cases)

Use a plain object when you want the time to automatically use the ScheduledScript's `timeZone`:

```
import { ScheduledScript } from '@servicenow/sdk/core'

ScheduledScript({
    $id: Now.ID['daily-job'],
    name: 'Daily Job',
    script: Now.include('./daily-job.js'),
    frequency: 'daily',
    executionTime: { hours: 9, minutes: 30, seconds: 0 },
    timeZone: 'America/New_York',  // Raw object uses this timezone
})
```

The raw object format:

- Automatically uses the ScheduledScript's `timeZone` for conversion

- Is simpler when you don't need explicit timezone per time value

- Works with `'floating'` timezone (no conversion, raw time is stored)

### Time() Helper Format (Explicit Timezone)

Use the `Time()` helper when you need to specify a different timezone than the ScheduledScript's `timeZone`, or when you want to be explicit about timezone handling:

```
import { ScheduledScript } from '@servicenow/sdk/core'

ScheduledScript({
    $id: Now.ID['india-job'],
    name: 'India Time Job',
    script: Now.include('./india-job.js'),
    frequency: 'daily',
    executionTime: Time({ hours: 14, minutes: 30 }, 'Asia/Kolkata'),
    timeZone: 'Asia/Kolkata',
})
```

The `Time()` helper format:

- Requires explicit timezone as the second parameter

- Must match the ScheduledScript's `timeZone` (build error if they differ)

- Provides clarity about timezone handling in the source code

Note: Both formats produce identical output. The choice is based on code clarity and personal preference.

## Conditional Execution

Set `conditional: true` and provide a `condition` expression for dynamic per-cycle skipping. This allows the job to remain active but skip execution based on runtime checks.

Important — Condition field restrictions: The `condition` field is evaluated in the server-side script sandbox, which only allows single expressions. The following are not allowed in conditions:

- Variable declarations (`var`, `let`, `const`)

- Control flow (`if`, `for`, `while`, `switch`, `return`)

- Assignment operators (`=`)

- Function declarations or IIFEs

- Multiple statements (semicolons)

- Object literals

If your condition requires complex logic (multiple checks, GlideRecord queries, aggregates), create a `sandboxCallable` script include and call it from the condition as a single expression. See the `script-include-guide` topic for the sandbox callable pattern.

### Common Use Cases

- Weekend/Holiday Checks: Preventing a job from running on weekends or specific company holidays

- Data-Driven Execution: Only running when a system property flag is enabled or specific records exist

- Time-Specific Logic: Ensuring a job only acts during specific, granular times (e.g., business hours only)

- Threshold-Based Execution: Running cleanup only when record count exceeds a threshold

### Simple Single-Expression Condition

```
ScheduledScript({
  $id: Now.ID["conditional-job"],
  name: "Weekday-Only Sync",
  script: Now.include("./conditional-job.server.js"),
  frequency: "daily",
  executionTime: Time({ hours: 6, minutes: 30 }),
  conditional: true,
  condition:
    "gs.getDayOfWeekLocalTime() >= 2 && gs.getDayOfWeekLocalTime() <= 6"
});
```

### Property-Gated Execution

```
import { ScheduledScript } from '@servicenow/sdk/core'

ScheduledScript({
  $id: Now.ID["property-gated-sync"],
  name: "Property-Gated Data Sync",
  script: Now.include("./property-sync.server.js"),
  frequency: "daily",
  executionTime: Time({ hours: 1, minutes: 0 }),
  conditional: true,
  condition: "gs.getProperty('x_myapp.sync.enabled') === 'true'",
});
```

### Complex condition using a `sandboxCallable` script include

```
ScheduledScript({
  $id: Now.ID["conditional-sync"],
  name: "Conditional Data Sync",
  script: Now.include("./conditional-sync.server.js"),
  frequency: "daily",
  executionTime: { hours: 9, minutes: 0 },
  conditional: true,
  condition: "new global.SyncConditionChecker().shouldRun()",
});
```

The companion script include handles the complex logic (property check + weekday check + GlideRecord query) in normal server-side context where `var`, `if`, loops, and GlideRecord are fully supported. See the `script-include-guide` topic for how to create `sandboxCallable` script includes.

### Holiday-Aware Execution

Skip execution on company holidays stored in a custom table:

```
import { ScheduledScript } from '@servicenow/sdk/core'

ScheduledScript({
  $id: Now.ID["holiday-skip-sync"],
  name: "Daily Sync - Skip Holidays",
  script: Now.include("./daily-sync.server.js"),
  frequency: "daily",
  executionTime: Time({ hours: 8, minutes: 0 }),
  conditional: true,
  condition: "!new GlideRecord('x_myapp_holiday').get('date', new GlideDate().getValue())",
});
```

### Business Hours Only

Run every hour but only during business hours (9 AM - 5 PM):

```
import { ScheduledScript } from '@servicenow/sdk/core'

ScheduledScript({
  $id: Now.ID["business-hours-only"],
  name: "Business Hours Processing",
  script: Now.include("./business-hours-processing.server.js"),
  frequency: "periodically",
  executionInterval: Duration({ hours: 1 }),
  conditional: true,
  condition:
    "new GlideDateTime().getLocalTime().getHourLocalTime() >= 9 && new GlideDateTime().getLocalTime().getHourLocalTime() < 17",
  advanced: true,
});
```

## Advanced Features

### offset and offsetType

Shift the scheduled execution time forward or backward:

- `offset` -- A `Duration` value specifying how much to shift

- `offsetType: 'future'` -- Runs after the scheduled time (forward shift)

- `offsetType: 'past'` -- Runs before the scheduled time (backward shift)

Example: Run 30 minutes after the scheduled time:

```
import { ScheduledScript } from '@servicenow/sdk/core'

ScheduledScript({
  $id: Now.ID["offset-job"],
  name: "Delayed Execution Job",
  script: Now.include("./delayed-job.server.js"),
  frequency: "daily",
  executionTime: Time({ hours: 8, minutes: 0 }),
  offset: { minutes: 30 },
  offsetType: "future", // Runs at 8:30 AM instead of 8:00 AM
});
```

### maxDrift

Sets a tolerance window for time-sensitive jobs. If the job cannot start within `maxDrift` of its scheduled time (e.g., due to system load), the execution is skipped entirely. This is useful when a late run is worse than no run.

Example: Skip execution if it can't start within 10 minutes:

```
import { ScheduledScript } from '@servicenow/sdk/core'

ScheduledScript({
  $id: Now.ID["time-sensitive-sync"],
  name: "Time-Sensitive Hourly Sync",
  script: Now.include("./time-sensitive-sync.server.js"),
  frequency: "periodically",
  executionInterval: Duration({ hours: 1 }),
  maxDrift: { minutes: 10 },
  advanced: true,
});
```

Note: All Duration fields (`executionInterval`, `maxDrift`, `offset`) accept either:

- Duration helper: `Duration({days: 1, hours: 1, minutes: 30 })` (explicit)

- Raw object: `{days: 1, hours: 1, minutes: 30 }` (all duration fields optional: days, hours, minutes, seconds)

Raw objects are convenient for simple durations, while the `Duration()` helper provides validation and consistency.

### repeatEvery

For recurring frequency types, `repeatEvery: N` makes the script execute only on every Nth scheduled occurrence. The scheduler still tracks each occurrence internally, but the script only runs on the Nth one.

Example: Run on every 3rd daily occurrence (effectively every 3 days):

```
import { ScheduledScript } from '@servicenow/sdk/core'

ScheduledScript({
  $id: Now.ID["every-third-day"],
  name: "Every Third Day Report",
  script: Now.include("./every-third-day.server.js"),
  frequency: "daily",
  executionTime: Time({ hours: 9, minutes: 0 }),
  repeatEvery: 3, // Runs every 3rd day
});
```

### runAs and userTimeZone Usage

Important: Only set `runAs` and `userTimeZone` when explicitly requested by the user.

- 
`runAs`: Only set if the user specifically mentions running the script as a particular user or with specific permissions. Query `sys_user` to find the target user's sys_id. Do not create a new user record unless explicitly asked.

- 
`userTimeZone`: Only set if the user specifically mentions timezone handling for date/time calculations within the script logic (e.g., `GlideDateTime` operations). This controls the timezone context for script execution, not the scheduled time.

## Protection

- `protectionPolicy: 'read'` -- Others can view but not modify

- `protectionPolicy: 'protected'` -- Others cannot view or modify

- Omit to allow full customization

## Business Calendar Integration

### Query Pattern

To use business calendar frequencies, you need to reference a business calendar entry by its sys_id. Use GlideRecord to query the `business_calendar` table:

```
// Query for a specific calendar by name
var gr = new GlideRecord('business_calendar');
gr.addQuery('calendar_name', 'fiscal_quarters');
gr.query();
if (gr.next()) {
  var calendarSysId = gr.sys_id.toString();
  // Use this sys_id in your ScheduledScript
}
```

### Standard Calendar Entries

The platform provides standard business calendar entries:

- Week entries: Weekly calendar periods

- Month entries: Monthly calendar periods

- Quarter entries: Quarterly calendar periods

- Year entries: Annual calendar periods

### Best Practices

- Always reference business calendar entries by sys_id from the `business_calendar` table

- Examples use descriptive placeholders (e.g., `"<business_calendar-sys-id>"`) with comments indicating they must be replaced with actual sys_ids

- Query the appropriate calendar entry before creating the scheduled script

- If the user provides a specific calendar name or sys_id, use that instead of standard entries

## Examples

Note: All examples use `x_myapp` as a placeholder scope prefix in table names and event names. Replace it with your application's actual scope prefix.

### Basic Daily Job

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["close-resolved-incidents"],
  name: "Close Resolved Incidents",
  script: Now.include("./close-resolved-incidents.server.js"),
  frequency: "daily",
  executionTime: Time({ hours: 2, minutes: 0 }),
});
```

Script file (`close-resolved-incidents.server.js`):

```
(function () {
  var gr = new GlideRecord("incident");
  gr.addEncodedQuery("state=6^sys_updated_onRELATIVELT@dayofweek@ago@30");
  gr.query();

  var count = 0;
  while (gr.next()) {
    gr.state = 7;
    gr.update();
    count++;
  }
  gs.info("Closed " + count + " resolved incidents older than 30 days");
})();
```

### Weekly Job

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["weekly-sla-report"],
  name: "Weekly SLA Report",
  script: Now.include("./weekly-sla-report.server.js"),
  frequency: "weekly",
  daysOfWeek: ["monday", "friday"],
  executionTime: Time({ hours: 7, minutes: 0 }),
});
```

### Periodically (Every 4 Hours)

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["periodic-sync"],
  name: "Periodic Data Sync",
  script: Now.include("./periodic-sync.server.js"),
  frequency: "periodically",
  executionInterval: Duration({ hours: 4 }),
  advanced: true,
});
```

### One-Time Migration

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["one-time-migration"],
  name: "Data Migration Script",
  script: Now.include("./one-time-migration.server.js"),
  frequency: "once",
  executionStart: "2026-06-15 02:00:00",
});
```

### On-Demand

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["manual-cache-refresh"],
  name: "Manual Cache Refresh",
  script: Now.include("./manual-cache-refresh.server.js"),
  frequency: "on_demand",
});
```

### Monthly (Last Day)

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["monthly-report"],
  name: "Monthly Report Generator",
  script: Now.include("./monthly-report.server.js"),
  frequency: "monthly",
  dayOfMonth: 31,
  executionTime: { hours: 23, minutes: 0, seconds: 0 },
});
```

### Annual Job

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["annual-license-review"],
  name: "Annual License Review",
  script: Now.include("./annual-license-review.server.js"),
  frequency: "day_and_month_in_year",
  month: 1,
  dayOfMonth: 15,
  executionTime: Time({ hours: 9, minutes: 0 }),
});
```

### Week-in-Month Job

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["second-monday-report"],
  name: "Second Monday Report",
  script: Now.include("./second-monday-report.server.js"),
  frequency: "week_in_month",
  weekInMonth: 2,
  dayOfWeek: "monday",
  executionTime: Time({ hours: 8, minutes: 0 }),
});
```

### Daily with Inline Script

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["daily-notification"],
  name: "Daily Morning Notification",
  script: `(function() {
    gs.eventQueue('x_myapp.daily.notification', null, gs.nowDateTime(), gs.getUserID());
    gs.info('Daily notification sent at ' + gs.nowDateTime());
  })()`,
  frequency: "daily",
  executionTime: Time({ hours: 9, minutes: 0 }),
});
```

### Daily with Bounded Execution Period

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["q1-daily-report"],
  name: "Q1 Daily Status Report",
  script: Now.include("./q1-daily-report.server.js"),
  frequency: "daily",
  executionTime: Time({ hours: 8, minutes: 0 }),
  executionStart: "2026-01-01 08:00:00",
  executionEnd: "2026-03-31 23:59:59",
});
```

### Day-Week-Month-Year Job

Run on a specific weekday in a specific week in a specific month each year (e.g., third Tuesday of March):

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["annual-board-meeting"],
  name: "Annual Board Meeting Preparation",
  script: Now.include("./board-meeting-prep.server.js"),
  frequency: "day_week_month_year",
  dayOfWeek: "tuesday",
  weekInMonth: 3,
  month: 3,
  executionTime: Time({ hours: 9, minutes: 0 }),
});
```

### Service Account Creation

Create a dedicated service account user for scheduled jobs:

```
import { ScheduledScript, Record } from "@servicenow/sdk/core";

// Create a dedicated service account user
const dataServiceAccount = Record({
  $id: Now.ID["data.sync.service.account"],
  table: "sys_user",
  data: {
    user_name: "data.sync.service",
    first_name: "Data Sync",
    last_name: "Service Account",
    email: "data.sync@company.com",
    active: true,
    web_service_access_only: true,
  },
});

// Use the service account in the scheduled script
ScheduledScript({
  $id: Now.ID["data-sync-service-job"],
  name: "Data Sync with Service Account",
  script: Now.include("./data-sync-service.server.js"),
  frequency: "periodically",
  executionInterval: { hours: 4 },
  timeZone: "UTC",
  advanced: true,
  runAs: dataServiceAccount,
  userTimeZone: "UTC",
});
```

Script file (`data-sync-service.server.js`):

```
(function () {
  try {
    gs.info("Starting data sync as service account");

    var currentUser = gs.getUserName();
    gs.info("Running as user: " + currentUser);

    var endpoint = gs.getProperty("x_myapp.sync.endpoint");
    var request = new sn_ws.RESTMessageV2();
    request.setEndpoint(endpoint);
    request.setHttpMethod("GET");

    var response = request.execute();
    var data = JSON.parse(response.getBody());

    var synced = 0;
    for (var i = 0; i < data.length; i++) {
      var item = data[i];
      var gr = new GlideRecord("x_myapp_external_data");
      gr.addQuery("external_id", item.id);
      gr.query();

      if (gr.next()) {
        gr.setValue("data", JSON.stringify(item));
        gr.update();
      } else {
        gr.initialize();
        gr.setValue("external_id", item.id);
        gr.setValue("data", JSON.stringify(item));
        gr.insert();
      }
      synced++;
    }

    gs.info("Data sync completed. Synced " + synced + " records.");
  } catch (e) {
    gs.error("Data sync failed: " + e.message);
  }
})();
```

### Business Calendar Start

Run when a business calendar period starts:

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["fiscal-period-open"],
  name: "Fiscal Period Open Notification",
  script: Now.include("./fiscal-period-open.server.js"),
  frequency: "business_calendar_start",
  businessCalendar: "<business_calendar-sys-id>", // Replace with actual sys_id
});
```

### Business Calendar End

Run when a business calendar period ends:

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["fiscal-period-close"],
  name: "Fiscal Period Close Archive",
  script: Now.include("./fiscal-period-close.server.js"),
  frequency: "business_calendar_end",
  businessCalendar: "<business_calendar-sys-id>", // Replace with actual sys_id
});
```

Script file (`fiscal-period-close.server.js`):

```
(function () {
  try {
    gs.info("Starting fiscal period close notification");

    var closeDate = new GlideDateTime();
    var message = "Fiscal period has closed\n";
    message += "Close Date: " + closeDate.getDisplayValue() + "\n";
    message += "Please complete period-end activities.";

    var gr = new GlideRecord("sys_user_group");
    gr.addQuery("name", "Finance Team");
    gr.query();

    if (gr.next()) {
      gs.eventQueue("x_myapp.fiscal_period_close", gr, message, gs.getUserID());
    }

    gs.setProperty("x_myapp.fiscal_period_last_closed", closeDate.getValue());
    gs.info("Fiscal period close notification sent");
  } catch (e) {
    gs.error("Error in fiscal period close notification: " + e.message);
  }
})();
```

### Threshold-Based Conditional

Only run cleanup when record count exceeds a threshold. This example uses a `sandboxCallable` script include to perform the complex GlideAggregate check:

```
import { ScheduledScript } from "@servicenow/sdk/core";

ScheduledScript({
  $id: Now.ID["threshold-cleanup"],
  name: "Cleanup - Only When Threshold Met",
  script: Now.include("./threshold-cleanup.server.js"),
  frequency: "daily",
  executionTime: Time({ hours: 2, minutes: 0 }),
  conditional: true,
  condition: "new global.ThresholdChecker().exceedsLimit('x_myapp_temp_data', 'stale', true, 1000)",
});
```

The `ThresholdChecker` script include implements the `exceedsLimit()` method to perform the GlideAggregate count check. See the `script-include-guide` topic for how to create `sandboxCallable` script includes with full implementation examples.

Script file (`threshold-cleanup.server.js`):

```
(function () {
  gs.info("Starting cleanup of stale records (threshold exceeded)");

  var gr = new GlideRecord("x_myapp_temp_data");
  gr.addQuery("stale", true);
  gr.query();

  var deleted = 0;
  while (gr.next()) {
    gr.deleteRecord();
    deleted++;
  }

  gs.info("Cleanup complete: deleted " + deleted + " stale records");
})();
```

## Related Topics

- `scheduledscript-api` — For complete API reference of all ScheduledScript properties and types

- `script-include-guide` — For reusable utility logic called from scheduled scripts, including `sandboxCallable` pattern for complex conditions

- `business-rule-guide` — For server-side logic triggered by record events (insert/update/delete) instead of time-based schedules

- `now-include-guide` — For understanding how to reference external JavaScript files in scheduled scripts

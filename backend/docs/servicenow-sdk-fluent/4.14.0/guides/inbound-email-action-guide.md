Version: 4.14.0

# Inbound Email Actions

Guide for creating ServiceNow Inbound Email Actions using the Fluent API. Inbound email actions define how ServiceNow processes incoming emails — creating records, updating existing records, sending auto-replies, or running custom logic when emails are received.

## When to Use

- Creating or modifying inbound email actions for automated email processing

- Implementing email-to-record conversion (e.g., email to incident, case, or request)

- Setting up auto-reply functionality for incoming emails

- Configuring email routing based on sender, content, or criteria

- Implementing role-based email processing restrictions

- Classifying and categorizing incoming emails automatically

## Instructions

- Choose the correct action type: Use `record_action` for creating/updating records, or `reply_email` for auto-replies. Most use cases require `record_action`.

- Respect field restrictions: `record_action` uses `table` (required), `script`, `fieldAction`, `assignmentOperator`. `reply_email` uses `replyEmail` and optionally `table`. Never mix incompatible fields.

- Use correct $id syntax: Always use `$id: Now.ID['value']` format, never plain strings.

- Validate table fields: When using `fieldAction`, always verify field names exist on the target table before adding them.

- Multi-table operations: While `table` specifies the primary target, scripts can perform actions on multiple tables by instantiating additional GlideRecordSecure objects.

- Script organization: Use inline scripts for simple logic. For complex logic, use `Now.include()` to move the script to a separate `.js` file or use a function exported from your `src/server` modules.

- GUID validation: The `from` field must contain a valid 32-character hexadecimal GUID or a `Record<'sys_user'>` reference.

## API Reference

See the `inboundemailaction-api` topic for the full property reference, including field restrictions by action type and `fieldAction` format.

## Key Concepts

### Action Types

record_action (Default)

- Creates or updates records in a target table

- Supports custom scripts and field value assignments

- Most common for email-to-record conversion

- Multi-table support: While the `table` property specifies the primary target table, the `script` can perform actions on multiple tables using GlideRecordSecure or other APIs

reply_email

- Sends automatic reply email to sender

- Uses `replyEmail` field for HTML content

- Cannot create or update records

### Email Types

| Type | Description |
| `new` | New incoming emails (default) |
| `reply` | Email replies to previous emails |
| `forward` | Forwarded emails |

### Common Configuration Properties

| Property | Type | Default | Description |
| `active` | `boolean` | `false` | Whether the action is enabled |
| `order` | `number` | `100` | Execution order when multiple actions match. Lower numbers execute first |
| `eventName` | `string` | `'email.read'` | Event name that triggers this action |
| `stopProcessing` | `boolean` | `false` | When true, stops processing subsequent actions after this one executes |
| `filterCondition` | `string` | - | Encoded query string to filter which emails trigger this action |
| `conditionScript` | `string` | - | Condition that must evaluate to true for the action to execute |

See the `inboundemailaction-api` topic for the full property reference.

### Script Context

When using `record_action` with a script, five objects are available:

| Object | Type | Description |
| `current` | `GlideRecord` | The target record being created or updated |
| `event` | `GlideRecord` | The sysevent record |
| `email` | `EmailWrapper` | The inbound email (subject, body_text, from, from_sys_id, etc.) |
| `logger` | `ScopedEmailLogger` | For logging email processing activity |
| `classifier` | `EmailClassifier` | For classifying the email (getCategory, getSubcategory) |

Scripts can perform operations on multiple tables by instantiating additional GlideRecordSecure objects. Note that `classifier` may not be available on all instances — always guard with a null check (e.g., `if (classifier) { ... }`).

### Filtering and Security

- Filter Conditions: Use `filterCondition` with encoded query format to target specific emails (e.g., `'subjectCONTAINSsupport^EQ'`)

- Role Restrictions: Use `requiredRoles` array to restrict processing to users with specific roles

- User Restrictions: Use `from` field to restrict to emails from a specific user (GUID or `Record<'sys_user'>`)

### Field Action Format

The `fieldAction` property sets field values on the target record using encoded query format:

| Value Type | Format | Example |
| Static value | `field=value` | `priority=1` |
| Static reference | `field=<sys_id>` | `assigned_to=62826bf03710200044e0bfc8bcbe5df1` |
| Datetime | `field=YYYY-MM-DD HH:MM:SS` | `activity_due=2026-03-17 00:00:00` |
| Dynamic from email | `fieldDYNAMIC<sys_id>` | `short_descriptionDYNAMICb637bd21ef3221002841f7f775c0fbb6` |
| Comma-separated list | `fieldDYNAMIC<id1>,<id2>` | `additional_assignee_listDYNAMIC0a82...,be82...` |
| Text query | `123TEXTQUERY321=value` | `123TEXTQUERY321=Issue` |

Separate multiple assignments with `^` and always end with `^EQ`.

OOB sys_filter_option_dynamic sys_ids:

| Email Property | sys_id | Compatible Field Types | Use For |
| Subject | `b637bd21ef3221002841f7f775c0fbb6` | String, Text | short_description, subject fields |
| Body (text) | `367bf121ef3221002841f7f775c0fbe2` | String, Text | description, comments fields |
| Recipients | `e009a97bef3221002841f7f775c0fb16` | String, Text | recipient fields |
| Sender | `2fd8e97bef3221002841f7f775c0fbc1` | Reference (sys_user) | caller_id, user reference fields |
| Sender->Company | `d27bf240ef0321002841f7f775c0fbeb` | Reference (core_company) | company reference fields |
| Sender->Location | `6d418b40ef0321002841f7f775c0fb46` | Reference (cmn_location) | location reference fields |
| Sender->Language | `fa128b40ef0321002841f7f775c0fbe6` | String | language fields |

Important: These are standard ServiceNow OOB records. Match the "Compatible Field Types" to your target field's type — for example, use `Sender` only for `Reference (sys_user)` fields like `caller_id`, not for string fields.

### Property Mapping (Fluent → ServiceNow)

The plugin automatically converts between camelCase (Fluent) and snake_case (ServiceNow). Properties not listed map 1:1 (e.g., `name` → `name`, `table` → `table`):

| Fluent (camelCase) | ServiceNow (snake_case) |
| `eventName` | `event_name` |
| `stopProcessing` | `stop_processing` |
| `conditionScript` | `condition_script` |
| `filterCondition` | `filter_condition` |
| `fieldAction` | `template` |
| `replyEmail` | `reply_email` |
| `requiredRoles` | `required_roles` |
| `assignmentOperator` | `assignment_operator` |

Notable: `fieldAction` maps to `template` in ServiceNow (not `field_action`).

Notable: `assignmentOperator` is the assignment operator for field actions. Only available for 'record_action' action type.

## Examples

### Email to Incident Conversion

Automatically create incident records from support emails.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

InboundEmailAction({
    $id: Now.ID['email-to-incident'],
    name: 'Email To Incident',
    description: 'Create incident from support emails',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    active: true,
    filterCondition: 'subjectCONTAINSsupport^EQ',
    script: `(function runAction(current, event, email, logger, classifier) {
    current.short_description = email.subject;
    current.description = email.body_text;
    current.caller_id = email.from_sys_id;
    current.priority = 3;
    current.state = 1;
    current.contact_type = 'email';

    if (current.canCreate()) {
        current.insert();
    }

    logger.log('Created incident from email: ' + email.subject, 'InboundEmailAction');
})(current, event, email, logger, classifier)`,
})
```

### Update Record on Reply

Update an existing record when a reply email is received.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

InboundEmailAction({
    $id: Now.ID['update-on-reply'],
    name: 'Update Incident on Reply',
    description: 'Updates an existing incident when a reply email is received',
    action: 'record_action',
    table: 'incident',
    type: 'reply',
    active: true,
    order: 200,
    script: `(function runAction(current, event, email, logger, classifier) {
    current.comments = email.body_text;
    current.update();

    logger.log('Incident updated from reply: ' + current.number, 'InboundEmailAction');
})(current, event, email, logger, classifier)`,
})
```

### Auto-Reply to Customers

Send automatic acknowledgment emails to incoming email senders.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

InboundEmailAction({
    $id: Now.ID['auto-reply'],
    name: 'Auto Reply Action',
    description: 'Send automatic reply to incoming emails',
    action: 'reply_email',
    type: 'new',
    active: true,
    order: 50,
    filterCondition: 'subjectCONTAINSsupport^EQ',
    replyEmail: `<div style="font-family: Arial, sans-serif;">
    <p>Dear Customer,</p>
    <p>Thank you for contacting us. We have received your email and will respond within 24 hours.</p>
    <p>If this is urgent, please call our support line at 1-800-SUPPORT.</p>
    <p>Best regards,<br/>Support Team</p>
</div>`,
})
```

### Role-Based Email Processing

Restrict email processing to users with specific roles for enhanced security.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

InboundEmailAction({
    $id: Now.ID['role-restricted'],
    name: 'Role Restricted Action',
    description: 'Only process emails from ITIL or admin users',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    active: true,
    requiredRoles: ['itil', 'admin'],
    script: `(function runAction(current, event, email, logger, classifier) {
    current.short_description = email.subject;
    current.description = email.body_text;
    current.caller_id = email.from_sys_id;
    current.insert();

    logger.log('Incident created by authorized user: ' + email.from, 'InboundEmailAction');
})(current, event, email, logger, classifier)`,
})
```

### Email Routing

Route emails to different tables based on content. Create multiple inbound email actions with different `filterCondition` values and use `order` to control execution sequence.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

// Route 1: High priority incidents (executes first)
InboundEmailAction({
    $id: Now.ID['urgent-incident-route'],
    name: 'Urgent Incident Route',
    description: 'Route urgent emails to incidents with high priority',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    order: 100,
    stopProcessing: true,
    active: true,
    filterCondition: 'subjectCONTAINSurgent^ORsubjectCONTAINSemergency^EQ',
    script: `(function runAction(current, event, email, logger, classifier) {
    current.short_description = email.subject;
    current.priority = 1;
    current.state = 1;
    current.insert();

    logger.log('Urgent incident created', 'InboundEmailAction');
})(current, event, email, logger, classifier)`,
})

// Route 2: Service requests (executes second)
InboundEmailAction({
    $id: Now.ID['service-request-route'],
    name: 'Service Request Route',
    description: 'Route service request emails to request table',
    action: 'record_action',
    table: 'sc_request',
    type: 'new',
    order: 200,
    stopProcessing: true,
    active: true,
    filterCondition: 'subjectCONTAINSrequest^ORsubjectCONTAINSservice^EQ',
    script: `(function runAction(current, event, email, logger, classifier) {
    current.short_description = email.subject;
    current.description = email.body_text;
    current.insert();

    logger.log('Service request created', 'InboundEmailAction');
})(current, event, email, logger, classifier)`,
})

// Route 3: Default fallback (executes last)
InboundEmailAction({
    $id: Now.ID['default-incident-route'],
    name: 'Default Incident Route',
    description: 'Default route for all other emails',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    order: 999,
    active: true,
    script: `(function runAction(current, event, email, logger, classifier) {
    current.short_description = email.subject;
    current.priority = 3;
    current.insert();

    logger.log('Default incident created', 'InboundEmailAction');
})(current, event, email, logger, classifier)`,
})
```

### Email Classification

Automatically classify and categorize incoming emails using the `classifier` object.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

InboundEmailAction({
    $id: Now.ID['classify-incident'],
    name: 'Classify Incident from Email',
    description: 'Automatically classify incidents based on email content',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    active: true,
    script: `(function runAction(current, event, email, logger, classifier) {
    current.short_description = email.subject;
    current.description = email.body_text;
    current.caller_id = email.from_sys_id;

    // Use classifier to categorize
    if (classifier) {
        var category = classifier.getCategory();
        var subcategory = classifier.getSubcategory();

        if (category) {
            current.category = category;
            logger.log('Category set to: ' + category, 'InboundEmailAction');
        }

        if (subcategory) {
            current.subcategory = subcategory;
            logger.log('Subcategory set to: ' + subcategory, 'InboundEmailAction');
        }
    }

    // Set priority based on keywords
    var subject = email.subject.toLowerCase();
    if (subject.indexOf('urgent') >= 0 || subject.indexOf('critical') >= 0) {
        current.priority = 1;
    } else if (subject.indexOf('high') >= 0) {
        current.priority = 2;
    } else {
        current.priority = 3;
    }

    current.insert();
    logger.log('Classified incident created', 'InboundEmailAction');
})(current, event, email, logger, classifier)`,
})
```

### Field Action — Static Values

Set fields to literal values without extracting from email.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

InboundEmailAction({
    $id: Now.ID['static-field-action'],
    name: 'Static Field Action',
    description: 'Set incident fields to static values',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    active: true,
    fieldAction: 'priority=1^active=true^state=1^EQ',
    script: `(function runAction(current, event, email, logger, classifier) {
    current.short_description = email.subject;
    current.description = email.body_text;
    current.insert();
})(current, event, email, logger, classifier)`,
})
```

### Field Action — Dynamic Values from Email

Extract values from email properties using OOB `sys_filter_option_dynamic` records.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

InboundEmailAction({
    $id: Now.ID['dynamic-field-action'],
    name: 'Dynamic Field Action',
    description: 'Extract field values from email',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    active: true,
    // short_description from email subject, description from body, caller from sender
    fieldAction:
        'short_descriptionDYNAMICb637bd21ef3221002841f7f775c0fbb6^descriptionDYNAMIC367bf121ef3221002841f7f775c0fbe2^caller_idDYNAMIC2fd8e97bef3221002841f7f775c0fbc1^priority=2^EQ',
})
```

### Field Action — Mixed Static and Dynamic

Combine dynamic field extraction with static values and classification.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

InboundEmailAction({
    $id: Now.ID['classify-with-field-action'],
    name: 'Classify with Field Action',
    description: 'Use fieldAction for consistent classification with dynamic email data',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    active: true,
    filterCondition: 'subjectCONTAINSemail^ORsubjectCONTAINSoutlook^EQ',
    // Dynamic from email subject + static category and priority
    fieldAction:
        'short_descriptionDYNAMICb637bd21ef3221002841f7f775c0fbb6^category=software^subcategory=email^priority=3^state=1^EQ',
    script: `(function runAction(current, event, email, logger, classifier) {
    current.description = email.body_text;
    current.caller_id = email.from_sys_id;
    current.insert();
})(current, event, email, logger, classifier)`,
})
```

### Multi-Table Operations

Perform actions on multiple tables from a single inbound email action. The `table` property specifies the primary target, while the script uses GlideRecordSecure for additional tables.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

InboundEmailAction({
    $id: Now.ID['multi-table-action'],
    name: 'Multi Table Action',
    description: 'Creates incident and related task records from email',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    active: true,
    script: `(function runAction(current, event, email, logger, classifier) {
    // Create the primary incident record
    current.short_description = email.subject;
    current.description = email.body_text;
    current.caller_id = email.from_sys_id;
    current.priority = 2;
    current.state = 1;
    current.insert();

    logger.log('Created incident: ' + current.number, 'InboundEmailAction');

    // Create related task in another table
    var task = new GlideRecordSecure('task');
    task.initialize();
    task.short_description = 'Follow up: ' + email.subject;
    task.description = 'Follow up on incident ' + current.number;
    task.parent = current.sys_id;
    task.assigned_to = current.assigned_to;
    task.insert();

    logger.log('Created follow-up task: ' + task.number, 'InboundEmailAction');

    // Update configuration item in a third table
    var ci = new GlideRecordSecure('cmdb_ci');
    if (ci.get('name', 'EmailServer')) {
        ci.comments = 'Incident ' + current.number + ' created from email';
        ci.update();
        logger.log('Updated CI: EmailServer', 'InboundEmailAction');
    }

    // Add work note to incident
    current.work_notes = 'Incident created from email. Follow-up task ' + task.number + ' assigned.';
    current.update();
})(current, event, email, logger, classifier)`,
})
```

### Condition Script — Conditional Execution

Use `conditionScript` to dynamically control whether the action executes.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

InboundEmailAction({
    $id: Now.ID['conditional-action'],
    name: 'Conditional Incident Action',
    description: 'Only create incident during business hours',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    active: true,
    conditionScript: `var now = new GlideDateTime();
var hour = now.getLocalTime().getHourOfDayLocalTime();
answer = (hour >= 8 && hour < 18);`,
    script: `(function runAction(current, event, email, logger, classifier) {
    current.short_description = email.subject;
    current.description = email.body_text;
    current.caller_id = email.from_sys_id;
    current.insert();

    logger.log('Business hours incident created', 'InboundEmailAction');
})(current, event, email, logger, classifier)`,
})
```

### Using Now.include() for External Scripts

Move complex script logic to a separate `.js` file for maintainability.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

InboundEmailAction({
    $id: Now.ID['external-script-action'],
    name: 'External Script Action',
    description: 'Process email using external script file',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    active: true,
    script: Now.include('../scripts/processInboundEmail.js'),
})
```

### Using Server Module Functions

Use a function exported from your `src/server` modules. The plugin automatically wraps it with the correct parameters (`current`, `event`, `email`, `logger`, `classifier`).

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'
import { processEmail } from './server/emailProcessor'

InboundEmailAction({
    $id: Now.ID['module-function-action'],
    name: 'Module Function Action',
    description: 'Process email using exported server module function',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    active: true,
    script: processEmail,
})
```

### User-Restricted Action

Restrict email processing to a specific sender using the `from` field.

```
import '@servicenow/sdk/global'
import { InboundEmailAction } from '@servicenow/sdk/core'

InboundEmailAction({
    $id: Now.ID['user-restricted-action'],
    name: 'VIP Email Processing',
    description: 'Only process emails from a specific VIP user',
    action: 'record_action',
    table: 'incident',
    type: 'new',
    active: true,
    from: '6816f79cc0a8016401c5a33be04be441', // GUID string; a Record<'sys_user'> reference is also accepted (preferred for cross-instance portability)
    script: `(function runAction(current, event, email, logger, classifier) {
    current.short_description = '[VIP] ' + email.subject;
    current.description = email.body_text;
    current.priority = 1;
    current.insert();

    logger.log('VIP incident created', 'InboundEmailAction');
})(current, event, email, logger, classifier)`,
})
```

## Best Practices

- Use `stopProcessing: true` when you don't want any later action (higher `order`) to also fire — when multiple actions might match the same email, use `stopProcessing` on higher-priority actions to stop the chain.

- Order actions by specificity — assign lower `order` values to more specific actions and higher values to catch-all defaults.

- Wrap scripts in IIFE format — use `(function runAction(current, event, email, logger, classifier) { ... })(current, event, email, logger, classifier)` for proper scoping and parameter documentation.

- Use `fieldAction` for simple field assignments — prefer `fieldAction` over scripts when setting static or dynamic values without complex logic.

- Use `Now.include()` or server module functions for complex scripts — keep inline scripts minimal and move complex logic to separate files for maintainability.

- Always set `active: true` explicitly — the default is `false`, so actions are inactive unless explicitly enabled.

- Use `filterCondition` to narrow email matching — reduces unnecessary script execution and improves performance.

- Log processing activity — use `logger.log()` to track email processing for debugging and auditing.

- Use GlideRecordSecure for multi-table operations — always use `GlideRecordSecure` (not `GlideRecord`) when accessing additional tables in scripts for proper access control.

- Validate field names before using `fieldAction` — verify field names exist on the target table to avoid silent failures.

- Only use OOB sys_filter_option_dynamic sys_ids — never create or use custom sys_ids for dynamic field values in `fieldAction`.

## Avoidance

- Never use incorrect $id syntax — always use `$id: Now.ID['value']`, never plain strings like `$id: 'value'`.

- Never mix incompatible fields — `record_action` cannot use `replyEmail`; `reply_email` cannot use `script`, `fieldAction`, or `assignmentOperator`.

- Never use `fieldAction` without `table` — field actions require a target table to be specified. The build plugin validates this and will emit an error.

- Never assume field names exist — always verify field names exist on the target table before using them in `fieldAction`.

- Never use invalid GUIDs for `from` — when using a GUID string, it must be valid 32-character hex. The `Record<'sys_user'>` form is also accepted and survives sys_id changes across instances. The build plugin validates GUID format.

- Never use custom sys_filter_option_dynamic sys_ids — only use the out-of-the-box sys_ids provided for dynamic field values in `fieldAction`.

- Use `insert()` for new records and `update()` for existing records — for `type: 'new'` and `'forward'`, use `current.insert()`. For `type: 'reply'`, the record already exists — use `current.update()`. For additional GlideRecordSecure objects, call `insert()` or `update()` as appropriate.

- Never omit `active: true` for production actions — the default is `false`, so actions will not execute unless explicitly activated.

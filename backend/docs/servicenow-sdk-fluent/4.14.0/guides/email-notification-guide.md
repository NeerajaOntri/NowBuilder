Version: 4.14.0

# Email Notification Guide

Create ServiceNow Email Notifications (`sysevent_email_action`) to send automated emails based on database operations, custom events, or manual triggers. This guide covers trigger types, content formats, recipients, digest emails (batched notifications), templates, styles, scripts, access restrictions, and notification categories. Supported in SDK 4.3.0 or higher.

## When to Use

- Creating or modifying email notifications for database operations (insert/update)

- Implementing event-based email notifications triggered by custom events

- Setting up manual/on-demand notifications triggered by scripts

- Configuring recipient lists based on users, groups, or record fields

- Implementing calendar invitations (vCalendar notifications)

- Implementing digest notifications or email templates (advanced features)

## Instructions

- 
ONE Notification Rule: Create one notification per request unless explicitly asked for multiple. Use both `onRecordInsert: true` AND `onRecordUpdate: true` in one notification instead of separate notifications for create/insert and update.

- 
Simplicity First: Default to inline content with minimal HTML (`<p>` and `<div>` tags only). No templates, no digest, no styles unless explicitly requested.

- 
Template Order: If templates are requested, create the template first, then reference it. Never create inline content then retrofit.

- 
Field Validation: Only use actual table fields (e.g., `${field_name}`). Email fields (`replyTo`, `from`) must be plain strings, never template variables.

- 
Business Rules Are Not Needed: For engine-based notifications (`generationType: 'engine'`), do not create business rules -- the notification engine handles triggering automatically.

- 
Instance URLs: Never Use `\${URI_REF}` for instance URLs link. Always use a mail script with `gs.getProperty('glide.servlet.uri')` to generate the instance URL dynamically.

## Quick Decision Guide

How Many Notifications?

- "send email on insert/update" -- ONE notification with both flags

- "when created or updated" / "when created and updated" -- ONE notification with both flags

- "multiple notifications" -- Ask: "How many and for what purposes?"

Should I Use Templates?

- Default: NO (use inline content)

- Only if explicitly requested: "template", "reusable content"

Should I Add Digest?

- Default: NO

- Only if explicitly requested: "daily digest", "group emails"

Should I Add Styles?

- Default: NO (minimal HTML only)

- Only if explicitly requested: "styled", "branded", "formatted"

## Request Classification

- SIMPLE ("send email when...") -- ONE notification, inline content, no advanced features

- COMPREHENSIVE ("email system", "multiple notifications") -- Ask clarifying questions first

- UNCLEAR -- Ask: "How many notifications?", "Need templates?", "Group into digests?"

## Table Selection

The `table` property must match the table where the triggering event occurs. If you target the wrong table, the notification silently never fires.

- Use the table where the record change happens. For example, if an incident is updated, `table: 'incident'`; if a change task is closed, `table: 'change_task'`.

- Do not assume all related workflows share a table. Service Catalog requests, requested items, and approvals each live on different tables.

### Service Catalog Notifications

Service Catalog workflows span multiple tables. Choose the correct one based on what triggers the notification:

| Scenario | Table | Why |
| Request opened, approved, completed, or rejected | `sc_request` | Lifecycle events fire on the request record. Add `universal_requestISEMPTY` to exclude Universal Requests |
| Item fulfilled, rejected, delivery, or comments | `sc_req_item` | Item-level events fire on the requested item (not `sc_request` , even though requests contain items). Dot-walk recipients through `request.requested_for` to reach the requester |
| Catalog task assigned or work-noted | `sc_task` | Fulfillment tasks created from requested items have their own assignment and work note notifications |
| Approval requested, approved, or rejected | `sysapproval_approver` | Approval records live here; use `sysapproval.sys_class_name` (e.g., `sysapproval.sys_class_name=sc_req_item^EQ` ) to scope to catalog approvals. OOB has separate notifications for RITM vs Request approvals |

### KB Approval Notifications

When targeting `sysapproval_approver` for KB approvals, field tokens like `\${short_description}` or `\${author.name}` resolve against `sysapproval_approver`, not `kb_knowledge`, and will be empty. Use an Email Script (`sys_script_email`) with `KBKnowledge().getNotificationObject(current)` — the platform Script Include that resolves article fields, links, and approver details from the approval record. Reference it inline: `\${mail_script:Script Name}`. See the KB Approval Email Script example.

## Trigger Types

### Engine-Based (`generationType: 'engine'`)

Auto-triggers on insert/update. Do not create business rules to trigger the notification. Most common type for standard CRUD operations.

Choose when:

- Notification should fire on record insert/update

- No custom business logic needed

- Standard CRUD operation monitoring

### Event-Based (`generationType: 'event'`)

Triggers on custom ServiceNow events. Requires the Event Registry to register the event first. Requires a Business Rule (or equivalent) to fire the event via `gs.eventQueue()`.

Choose when:

- Custom workflow events trigger notification

- Complex business logic determines when to send

- Event parameters contain recipient information

Important: Always query the instance for the event name (`sysevent_register` table) before using it in a notification. Do not assume an event name exists. If the event does not exist, create it first using the Event Registry (see `registering-events-guide`), then create a Business Rule to trigger it via `gs.eventQueue()`.

### Triggered (`generationType: 'triggered'`)

Manual/script-triggered. Requires explicit triggering logic via scripts or business rules.

Choose when:

- Manual/on-demand sending required

- Script-controlled timing needed

- Maximum control over when notification sends

## Content Types

### HTML (`'text/html'`, default)

Rich emails with minimal HTML (`<p>`, `<div>`). Only create `messageHtml` field.

### Plain Text (`'text/plain'`)

Simple text-only for maximum compatibility or SMS. Only create `messageText` field.

### Multipart (`'multipart/mixed'`)

Both HTML and plain text versions for best compatibility. Must create both `messageHtml` AND `messageText` fields.

### Variable Syntax

When writing TypeScript code, use a single backslash to escape variables in template literals:

```
// CORRECT - Single backslash in TypeScript code
messageHtml: `<p>Hello \${assigned_to.name}</p><p>Incident \${number}</p>`;

// WRONG - Double backslash
messageHtml: `<p>Hello \\${assigned_to.name}</p>`;

// WRONG - No backslash (JavaScript interpolates it)
messageHtml: `<p>Hello ${assigned_to.name}</p>`;
```

In TypeScript template literals (backticks), write `\${field_name}` with one backslash. This escapes the dollar sign so JavaScript does not try to interpolate it, producing the runtime string `${field_name}` which ServiceNow then substitutes.

## Recipients

Field Recipients (`recipientFields`): Dynamic recipients from record fields (e.g., `assigned_to`, `caller`). Most common and flexible pattern.

Group Recipients (`recipientGroups`): Array of group sys_ids for teams/departments. Preferred over individual users for scalability.

User Recipients (`recipientUsers`): Array of user sys_ids for fixed lists of specific individuals.

Special Recipients:

- `sendToCreator: true` -- Send to record creator

- `eventParm1WithRecipient` / `eventParm2WithRecipient` -- Event-based only

- `excludeDelegates: true` -- Exclude out-of-office delegates

- `isSubscribableByAllUsers: true` -- Allow user subscriptions

## API Reference

For the full property reference (EmailNotification, trigger conditions, email content, digest), see the `emailnotification-api` topic.

## Supporting Record Types

These are created using the `Record` API, not dedicated Fluent constructors.

### Email Template (`sysevent_email_template`)

| Field | Type | Required | Description |
| `name` | `String` | Yes | Template name. |
| `subject` | `String` | No | Email subject (max 100). |
| `message_html` | `HTMLScript` | No | HTML message (max 4000). |
| `message_text` | `EmailScript` | No | Plain text message (max 4000). |
| `message` | `EmailScript` | No | Message content, legacy field (max 4000). |
| `sms_alternate` | `EmailScript` | No | SMS alternate message (max 8000). |
| `collection` | `TableName` | No | Target table. Default: `'incident'` . |
| `sys_version` | `String` | No | Version. Default: `'2'` . |
| `email_layout` | `Reference` | No | Reference to `sys_email_layout` (overall structure: header, footer, container). |
| `message_list` | `List` | No | Push messages, reference to `sys_push_notif_msg` . |

On the template record use the snake_case field names (`message_html`, `message_text`), not the camelCase `messageHtml`/`messageText` names used in `emailContent`.

Choosing the content field: Put the body in the field that matches the content type:

- `message_html` — any content with HTML tags, links (`<a>`), or inline styling. This is the field the platform renders as HTML (`html_script`).

- `message_text` — plain-text content.

- `message` — legacy combined field. Prefer `message_html`/`message_text`.

Important: Always query the instance for existing email templates before creating new ones. Only create a new template if none of the existing templates satisfy your requirement or it is specifically asked to create one. Reusing existing templates promotes consistency and reduces maintenance overhead.

### Email Layout (`sys_email_layout`)

An Email Layout is the reusable outer shell (header, footer, branding, container) that wraps a template's content. A layout is attached to a template through the template's `email_layout` field, and the template is attached to the notification. Create a layout only when you need consistent branding across multiple notifications.

| Field | Type | Required | Description |
| `name` | `String` | Yes | Layout name (max 100). |
| `layout` | `HTML` | No | The layout HTML. Must include the `${notification:body}` token where the template/notification content is injected (see below). |
| `advanced` | `Boolean` | No | Enables advanced (XML) layout mode. Default: `false` . Leave `false` for standard HTML layouts. |
| `advanced_layout` | `XML` | No | Advanced layout definition (XML). Only used when `advanced` is `true` . |
| `description` | `String` | No | Description (max 1000). |

The `${notification:body}` token (required for the body to appear): Because a layout is a shared shell, it cannot contain any one notification's content. Instead, put the literal token `${notification:body}` in the `layout` HTML at the spot where the content should appear. At send time the platform replaces that token with the body rendered by the template/notification using this layout.

See the Notification with Email Layout example.

Important: Always query the instance for existing email layouts before creating a new one. Reuse an existing layout when it satisfies the branding requirement.

### Email Style (`sysevent_email_style`)

| Field | Type | Required | Description |
| `name` | `String` | Yes | Style name. |
| `style` | `HTML` | No | CSS/HTML style content (max 65000). |

Email Client Compatibility: Most clients support colors, fonts, spacing, borders, and text-align. Limited support for flexbox, grid, and pseudo-classes. Use inline styles for critical styling and tables for layout.

### Email Script (`sys_script_email`)

| Field | Type | Required | Description |
| `name` | `String` | Yes | Script name (max 100, unique). |
| `script` | `String` | No | Script contents (max 4000). |
| `new_lines_to_html` | `Boolean` | No | Convert newlines to HTML. Default: `false` . |

The script must maintain the structure `(function runMailScript(current, template, email, email_action, event) {...})(current, template, email, email_action, event);` and use `template.print()` to output content. Available variables: `current` (the target record), `template` (TemplatePrinter), and the optional `email`, `email_action`, and `event`.

To run a mail script, create the `sys_script_email` record and reference it by name inline in the message content using `\${mail_script:Script Name}`. See the Notification with Email Script example.

### Email Access Restriction (`email_access_restriction`)

| Field | Type | Required | Description |
| `notification` | `Reference` , `EmailNotification` | Yes | Reference to `sysevent_email_action` . |
| `conditions` | `Conditions` | Yes | Access conditions (max 8000). |
| `description` | `String` | No | Description (max 1000). |

Important: Only one restriction per notification. Query first to check if a restriction already exists before creating. Combine multiple conditions using `^` (AND) or `^OR` (OR). Do not use `Now.ID` for the notification field -- use `notificationVariable.$id` or a queried sys_id.

Condition Format: Conditions must match the notification's table fields using format `field_name=value^EQ` or `field_name!=value`. Example: `priority=1^ORpriority=2^state!=6^EQ` for P1/P2 incidents that aren't resolved.

Behavior: When access is denied, recipients receive the email but content is replaced with a generic message. Subject lines remain visible.

### Email Digest Interval (`sys_email_digest_interval`)

| Field | Type | Required | Description |
| `name` | `TranslatedText` | Yes | Interval name. |
| `interval` | `GlideDuration` | Yes | Duration (max 40) in format `YYYY-MM-DD HH:MM:SS` . |

Common intervals: Hourly `1970-01-01 01:00:00`, Daily `1970-01-02 00:00:00`, Weekly `1970-01-08 00:00:00`. Range: one hour to one week.

Choosing an Interval: Use hourly for high-volume operational monitoring, daily for moderate-volume end-of-day summaries, weekly for low-volume status reports.

Important: Always query the instance for existing digest intervals before creating new ones. Only create a new interval if none of the existing intervals satisfy your requirement. Reusing existing intervals helps maintain consistency across notifications.

### Notification Category (`sys_notification_category`)

| Field | Type | Required | Description |
| `name` | `TranslatedText` | Yes | Category name (max 32, unique). |
| `short_description` | `String` | No | Short description (max 1000). |

Default category sys_id: `c97d83137f4432005f58108c3ffa917a`.

Organization Patterns: Organize by application (Incident Management, Change Management), by priority (Critical Alerts, Standard Updates), or by event type (Assignments, Approvals, Status Changes).

## GUID Validation

All reference fields must contain valid 32-character hexadecimal sys_ids:

- `category` -- `sys_notification_category`

- `emailContent.template` -- `sysevent_email_template`

- `emailContent.style` -- `sysevent_email_style`

- `recipientDetails.recipientUsers` -- `sys_user`

- `recipientDetails.recipientGroups` -- `sys_user_group`

- `digest.defaultInterval` -- `sys_email_digest_interval`

## Handling Existing OOB Notifications

Before creating a custom notification, query `sysevent_email_action` for existing OOB notifications on the same table and event (e.g., `collection=incident^active=true^nameLIKEAssign`). Failing to check can cause duplicate emails in production.

If a match exists:

- Reuse — If the OOB notification already satisfies the requirement, skip creation.

- Deactivate and replace — If content or recipients need to change, deactivate the OOB notification (`active: false`) and create a new custom one. Never modify OOB notifications in-place — upgrades overwrite customizations silently.

- Keep both — If the custom notification serves a different audience/purpose, both can coexist.

To deactivate, check out the OOB record and set `active: false`. Do not delete OOB notifications — only deactivate them for upgrade safety.

## Common Mistakes to Avoid

- Do not use incorrect `$id` syntax -- always use `$id: Now.ID["value"]`

- Do not use double backslash in TypeScript template literals

- Do not hallucinate fields -- only use actual table fields in message content

- Do not assume or auto-populate `replyTo` and `from` fields

- Do not create business rules for engine-based notifications

- Do not create templates, digest, or styles unless explicitly requested

- Do not put HTML, links, or styling in a template's `message` field -- use `message_html`, which the platform renders as HTML (`message` is treated as plain text and strips tags/links)

- Do not use `\${URI_REF}` for record links  -- use a mail script with `gs.getProperty('glide.servlet.uri')` to generate the URL dynamically

- Do not skip checking for existing OOB notifications before creating custom ones -- query `sysevent_email_action` first to avoid duplicate emails

## Examples

### Simple Insert/Update Notification

```
import { EmailNotification } from "@servicenow/sdk/core";

EmailNotification({
  $id: Now.ID["incident-update-notification"],
  table: "incident",
  name: "Incident Notification",
  triggerConditions: {
    generationType: "engine",
    onRecordUpdate: true,
    onRecordInsert: true
  },
  recipientDetails: {
    recipientFields: ["assigned_to"]
  },
  emailContent: {
    subject: "Incident \${number} Update",
    messageHtml: `<p>Hello \${assigned_to.name}</p><p>Incident \${number} has been updated.</p><p>Priority: \${priority}</p>`
  }
});
```

### Notification with Link to Record

Include a clickable link to the record by dynamically generating the instance URL using a mail script.

```
import { EmailNotification, Record } from "@servicenow/sdk/core";

// Create email script to generate the record link dynamically
Record({
  $id: Now.ID["generate_record_link_script"],
  table: "sys_script_email",
  data: {
    name: "Generate Record Link",
    new_lines_to_html: false,
    script: `(function runMailScript(/* GlideRecord */ current, /* TemplatePrinter */ template,
      /* Optional EmailOutbound */ email, /* Optional GlideRecord */ email_action,
      /* Optional GlideRecord */ event) {
      var instanceUrl = gs.getProperty('glide.servlet.uri');
      var recordUrl = instanceUrl + '/' + current.getTableName() + '.do?sys_id=' + current.sys_id;
      template.print(recordUrl);
})(current, template, email, email_action, event);`
  }
});

EmailNotification({
  $id: Now.ID["incident-with-link"],
  table: "incident",
  name: "Incident Notification with Link",
  triggerConditions: {
    generationType: "engine",
    onRecordUpdate: true,
    onRecordInsert: true
  },
  recipientDetails: {
    recipientFields: ["assigned_to"]
  },
  emailContent: {
    subject: "Incident \${number} Update",
    messageHtml: `<p>Hello \${assigned_to.name},</p>
      <p>Incident <strong>\${number}</strong> has been updated.</p>
      <p><strong>Priority:</strong> \${priority}</p>
      <p><strong>Short Description:</strong> \${short_description}</p>
      <p>
        <a href="\${mail_script:Generate Record Link}"
           style="display: inline-block; padding: 10px 20px; background-color: #0066cc; color: white; text-decoration: none; border-radius: 4px;">
          View Incident
        </a>
      </p>`
  }
});
```

Dynamic URL Generation: The mail script uses `gs.getProperty('glide.servlet.uri')` to get the instance URL at runtime, then constructs the full record URL: `<instance-url>/<table>.do?sys_id=<sys_id>`. This ensures the link works across different instances (dev, test, prod) without hardcoding.

### Notification with Template

```
import { EmailNotification, Record } from "@servicenow/sdk/core";

const incidentTemplate = Record({
  $id: Now.ID["incident_update_template"],
  table: "sysevent_email_template",
  data: {
    name: "Incident Update Template",
    subject: "Incident \${number} has been updated",
    message_html: `<h1>Incident Update</h1>
      <p>Incident \${number} has been updated:</p>
      <ul>
        <li>State: \${state}</li>
        <li>Priority: \${priority}</li>
        <li>Assigned To: \${assigned_to}</li>
      </ul>`,
    collection: "incident",
    sys_version: "2"
  }
});

EmailNotification({
  $id: Now.ID["incident-with-template"],
  table: "incident",
  name: "Incident Notification With Template",
  active: true,
  triggerConditions: {
    generationType: "engine",
    onRecordUpdate: true
  },
  recipientDetails: {
    recipientFields: ["assigned_to"]
  },
  emailContent: {
    template: incidentTemplate
  }
});
```

### Notification with Email Layout

The layout `layout` and the template `message_html` use escaped template literals (`\${...}`) so the `${...}` tokens survive to runtime.

```
import { EmailNotification, Record } from "@servicenow/sdk/core";

// 1. Layout — ${notification:body} marks where content is injected
const brandedLayout = Record({
  $id: Now.ID["branded_email_layout"],
  table: "sys_email_layout",
  data: {
    name: "Branded Customer Layout",
    layout: `<div style="font-family: Arial, sans-serif;">
      <div style="background: #0066cc; padding: 16px; color: #fff;">Acme Support</div>
      <div style="padding: 24px;">\${notification:body}</div>
      <div style="padding: 16px; color: #888;">Need help? support@example.com</div>
    </div>`
  }
});

// 2. Template — attach the layout via email_layout
const acknowledgementTemplate = Record({
  $id: Now.ID["case_acknowledgement_template"],
  table: "sysevent_email_template",
  data: {
    name: "Case Acknowledgement",
    subject: "Your case \${number} has been received",
    email_layout: brandedLayout,
    message_html: `<p>Hello \${caller_id.name},</p>
      <p>We have received your case <strong>\${number}</strong>.</p>`,
    collection: "incident"
  }
});

// 3. Notification — reference the template
EmailNotification({
  $id: Now.ID["case-acknowledgement-notification"],
  table: "incident",
  name: "Case Acknowledgement",
  active: true,
  triggerConditions: {
    generationType: "engine",
    onRecordInsert: true
  },
  recipientDetails: {
    recipientFields: ["caller_id"]
  },
  emailContent: {
    template: acknowledgementTemplate
  }
});
```

### Digest Notification

Digest batches multiple notifications into fewer emails. `type` controls how:

- `'multiple'` (Multiple Digest) -- Sends separate emails per record, but batched by interval. Each record becomes a separate entry rendered with `emailContent.messageHtml` and joined by `digest.separatorHtml`. Use for record-specific tracking where individual emails per record are needed.

- `'single'` (Single Digest) -- Sends one consolidated email per interval containing all records. Built from `digest.html` (or `digest.template`); the per-record `emailContent.messageHtml` is ignored. Use for high-volume notifications where maximum email reduction is desired.

Digest has built-in scheduling -- do not create business rules or schedulers to drive it. Digest is not available for `vcalendar` notifications.

```
import { EmailNotification } from "@servicenow/sdk/core";

EmailNotification({
  $id: Now.ID["daily-incident-digest"],
  table: "incident",
  name: "Daily Incident Digest",
  active: true,
  triggerConditions: {
    generationType: "engine",
    onRecordInsert: true
  },
  recipientDetails: {
    recipientFields: ["assignment_group"]
  },
  emailContent: {
    subject: "Incident \${number} Created",
    messageHtml: `<div style="border-bottom: 1px solid #ddd; padding: 10px;">
      <h4>\${number}: \${short_description}</h4>
      <p><strong>Priority:</strong> \${priority} | <strong>State:</strong> \${state}</p>
    </div>`
  },
  digest: {
    allow: true,
    type: "multiple",
    defaultInterval: "daily_digest_sys_id",
    subject: "Daily New Incidents - \${digest_count} incidents",
    html: "<h2>New Incidents (\${digest_count} total)</h2>",
    separatorHtml: '<hr style="margin: 15px 0;">'
  }
});
```

### Event-Based Notification

```
import { EmailNotification } from "@servicenow/sdk/core";

EmailNotification({
  $id: Now.ID["contract-expiring-notification"],
  table: "sn_contract_e_2_contract",
  name: "Contract Expiring - Account Owner Notification",
  active: true,
  triggerConditions: {
    generationType: "event",
    eventName: "sn_contract_e_2.contract.expiring"
  },
  recipientDetails: {
    eventParm1WithRecipient: true
  },
  emailContent: {
    subject: `Contract Expiring Soon: \${name}`,
    messageHtml: `<p>Dear \${account_owner.name},</p>
      <p>The following contract is approaching its expiration date:</p>`
  }
});
```

### Plain Text Notification

```
import { EmailNotification } from "@servicenow/sdk/core";

EmailNotification({
  $id: Now.ID["system-alert-plain-text"],
  table: "incident",
  name: "System Alert Plain Text",
  triggerConditions: {
    generationType: "engine",
    onRecordInsert: true,
    condition: "priority=1^EQ"
  },
  recipientDetails: {
    recipientFields: ["assigned_to"]
  },
  emailContent: {
    contentType: "text/plain",
    subject: "ALERT: Incident \${number}",
    messageText: `Hello \${assigned_to.name},\n\nIncident \${number} requires attention.\nPriority: \${priority}\nDescription: \${short_description}`
  }
});
```

### VCalendar Meeting Invitation

```
import { EmailNotification } from "@servicenow/sdk/core";

EmailNotification({
  $id: Now.ID["incident-review-meeting"],
  table: "incident",
  name: "Incident Review Meeting",
  notificationType: "vcalendar",
  triggerConditions: {
    generationType: "event",
    eventName: "incident.severity.1",
    condition: "active=true^EQ"
  },
  recipientDetails: {
    recipientFields: ["assignment_group", "assigned_to"]
  },
  emailContent: {
    subject: "Incident \${number} Review Meeting",
    messageHtml: `<div>You are invited to review incident \${number}</div>`
  }
});
```

### Triggered (Manual) Notification

Manually invoked notifications -- they are not fired automatically. You must trigger them from a script or business rule.

```
import { EmailNotification } from "@servicenow/sdk/core";

EmailNotification({
  $id: Now.ID["manual-incident-notification"],
  table: "incident",
  name: "Manual Incident Notification",
  triggerConditions: {
    generationType: "triggered"
  },
  recipientDetails: {
    recipientFields: ["assigned_to"],
    sendToCreator: true
  },
  emailContent: {
    subject: "Manual Notification - Incident \${number}",
    messageHtml: `<p>This is a manually triggered notification.</p><p>Incident: \${number}</p><p>Status: \${state}</p>`
  }
});
```

### Multipart Notification (HTML + Text)

Set `contentType: 'multipart/mixed'` and provide BOTH `messageHtml` and `messageText`. Clients display HTML when supported and fall back to text otherwise.

```
import { EmailNotification } from "@servicenow/sdk/core";

EmailNotification({
  $id: Now.ID["multipart-incident-notification"],
  table: "incident",
  name: "Multipart Incident Notification",
  triggerConditions: {
    generationType: "engine",
    onRecordUpdate: true
  },
  recipientDetails: {
    recipientFields: ["assigned_to"]
  },
  emailContent: {
    contentType: "multipart/mixed",
    subject: "Incident \${number} Update",
    messageHtml: `<p>Hello \${assigned_to.name}</p><p>Incident \${number} has been updated.</p><p><strong>Priority:</strong> \${priority}</p>`,
    messageText: `Hello \${assigned_to.name},\n\nIncident \${number} has been updated.\nPriority: \${priority}\n\nThank you.`
  }
});
```

### Notification with Email Script

Create the `sys_script_email` record with `Record`, then reference it inline in the message content with `\${mail_script:Script Name}`. There is no `emailScript` field on `emailContent`.

```
import { EmailNotification, Record } from "@servicenow/sdk/core";

Record({
  $id: Now.ID["format_incident_details_script"],
  table: "sys_script_email",
  data: {
    name: "Format Incident Details",
    new_lines_to_html: false,
    script: `(function runMailScript(/* GlideRecord */ current, /* TemplatePrinter */ template,
      /* Optional EmailOutbound */ email, /* Optional GlideRecord */ email_action,
      /* Optional GlideRecord */ event) {
      template.print("Incident: " + current.number);
      template.print("\\nPriority: " + current.getDisplayValue('priority'));
      template.print("\\nStatus: " + current.getDisplayValue('state'));
})(current, template, email, email_action, event);`
  }
});

EmailNotification({
  $id: Now.ID["incident-with-script"],
  table: "incident",
  name: "Incident With Script",
  triggerConditions: {
    generationType: "engine",
    onRecordUpdate: true
  },
  recipientDetails: {
    recipientFields: ["assigned_to"]
  },
  emailContent: {
    subject: "Incident \${number} Update",
    messageHtml: `<p>Hello \${assigned_to.name}</p><p>Incident details:</p>\${mail_script:Format Incident Details}`
  }
});
```

### KB Approval Email Script

KB approval notifications target `sysapproval_approver`, where field tokens cannot access `kb_knowledge` fields. Use the OOB `KBKnowledge` Script Include via `getNotificationObject(current)` to resolve article details, links, and approver info from the approval record.

Fluent Definition:

```
import { Record } from "@servicenow/sdk/core";

Record({
  $id: Now.ID["kb_approval_details_script"],
  table: "sys_script_email",
  data: {
    name: "KB Approval Article Details",
    new_lines_to_html: false,
    script: Now.include("./kb-approval-details.js")
  }
});
```

Script File (`kb-approval-details.js`):

```
(function runMailScript(current, template, email, email_action, event) {
    var obj = new KBKnowledge().getNotificationObject(current);
    var content =
        'Hi ' + obj.approver + ',<br/><br/>' +
        '<a href="' + obj.article_link + '">' + obj.number + '</a> is awaiting approval.<br/><br/>' +
        '<b>Article Title</b>: ' + obj.short_desc + '<br/><br/>' +
        'Please review the article and <a href="' + obj.approval_link + '">Approve/Reject</a> it<br/><br/>';
    email.setSubject(obj.number + ' is awaiting approval.');
    template.print(content);
})(current, template, email, email_action, event);
```

Reference inline in the notification body: `\${mail_script:KB Approval Article Details}`.

Note: The `KBKnowledge` Script Include is specific to KB approval workflows. For other use cases where no OOB Script Include exists, use a generic `GlideRecord` lookup (e.g., `new GlideRecord('target_table').get(current.document_id)`) to retrieve fields from the related record.

### Styled Notification

Create a `sysevent_email_style` record and pass it to `emailContent.style`. Prefer inline styles in `messageHtml` for maximum email-client compatibility.

```
import { EmailNotification, Record } from "@servicenow/sdk/core";

const corporateStyle = Record({
  $id: Now.ID["corporate_email_style"],
  table: "sysevent_email_style",
  data: {
    name: "Corporate Email Style",
    style: `.priority-high { color: #d32f2f; font-weight: bold; }`
  }
});

EmailNotification({
  $id: Now.ID["styled-incident-notification"],
  table: "incident",
  name: "Styled Incident Notification",
  triggerConditions: {
    generationType: "engine",
    onRecordUpdate: true,
    condition: "priority=1^EQ"
  },
  recipientDetails: {
    recipientFields: ["assigned_to"]
  },
  emailContent: {
    subject: "URGENT: Incident \${number}",
    messageHtml: `<p><span class="priority-high">Priority: \${priority}</span></p><p>Incident: \${number}</p><p>\${short_description}</p>`,
    style: corporateStyle
  }
});
```

### Advanced Email Options

Real `emailContent` fields for delivery control. `from` and `replyTo` must be plain static email strings (never template variables) -- only set them when explicitly provided.

```
import { EmailNotification } from "@servicenow/sdk/core";

EmailNotification({
  $id: Now.ID["critical-incident-alert"],
  table: "incident",
  name: "Critical Incident Alert",
  mandatory: true,
  triggerConditions: {
    generationType: "engine",
    onRecordInsert: true,
    onRecordUpdate: true,
    condition: "priority=1^EQ"
  },
  recipientDetails: {
    recipientFields: ["assigned_to", "caller_id"],
    recipientGroups: ["incident_managers_group_sys_id"]
  },
  emailContent: {
    subject: "CRITICAL: Incident \${number}",
    messageHtml: `<p><strong>Incident:</strong> \${number}</p><p><strong>Description:</strong> \${short_description}</p>`,
    importance: "high",
    includeAttachments: true,
    omitWatermark: true,
    forceDelivery: true,
    smsAlternate: "CRITICAL: Incident \${number} - \${short_description}",
    from: "incident-management@company.com",
    replyTo: "itsupport@company.com"
  }
});
```

### Notification with Access Restriction

Restrict which records' content recipients can see. Create an `email_access_restriction` record that references the notification. Use the notification variable's `$id` for the `notification` field -- not a fresh `Now.ID`. Only one restriction is allowed per notification; combine conditions with `^` (AND) or `^OR` (OR).

```
import { EmailNotification, Record } from "@servicenow/sdk/core";

const restrictedNotification = EmailNotification({
  $id: Now.ID["restricted-incident-notification"],
  table: "incident",
  name: "Restricted Incident Notification",
  triggerConditions: {
    generationType: "engine",
    onRecordUpdate: true
  },
  recipientDetails: {
    recipientFields: ["assigned_to"]
  },
  emailContent: {
    subject: "Incident \${number} Update",
    messageHtml: `<p>Incident \${number} has been updated.</p><p>Priority: \${priority}</p>`
  }
});

Record({
  $id: Now.ID["incident_access_restriction"],
  table: "email_access_restriction",
  data: {
    notification: restrictedNotification,
    conditions: "priority=1^ORpriority=2^state!=6^state!=7^EQ",
    description: "Only show content for P1/P2 incidents that are not resolved or closed"
  }
});
```

### Notification with Category

Create categories to organize notifications by type or department. Query for existing categories first before creating new ones.

```
import { EmailNotification, Record } from "@servicenow/sdk/core";

const securityCategory = Record({
  $id: Now.ID["security_notifications_category"],
  table: "sys_notification_category",
  data: {
    name: "Security Notifications",
    short_description: "All security-related incident notifications"
  }
});

EmailNotification({
  $id: Now.ID["security-incident-notification"],
  table: "incident",
  name: "Security Incident Notification",
  category: securityCategory,
  triggerConditions: {
    generationType: "engine",
    onRecordInsert: true,
    condition: "category.name=Security^EQ"
  },
  recipientDetails: {
    recipientFields: ["assignment_group"],
    recipientGroups: ["security_team_sys_id"]
  },
  emailContent: {
    subject: "Security Incident \${number} Created",
    messageHtml: `<p>A new security incident has been created.</p><p>Incident: \${number}</p><p>Description: \${short_description}</p>`
  }
});
```

### Complete Notification with All Advanced Features

Comprehensive example combining category, style, script, and access restriction. Only create all components when explicitly requested for complex requirements.

```
import { EmailNotification, Record } from "@servicenow/sdk/core";

// 1. Create category
const criticalCategory = Record({
  $id: Now.ID["critical_incidents_category"],
  table: "sys_notification_category",
  data: {
    name: "Critical Incidents",
    short_description: "Critical priority incident notifications"
  }
});

// 2. Create email style
const criticalStyle = Record({
  $id: Now.ID["critical_incident_style"],
  table: "sysevent_email_style",
  data: {
    name: "Critical Incident Style",
    style: `.critical-header { background: #dc3545; color: white; padding: 20px; }
      .urgent-badge { background: #dc3545; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; }`
  }
});

// 3. Create email script
const criticalScript = Record({
  $id: Now.ID["critical_incident_script"],
  table: "sys_script_email",
  data: {
    name: "Critical Incident Details Script",
    new_lines_to_html: true,
    script: `(function runMailScript(/* GlideRecord */ current, /* TemplatePrinter */ template,
      /* Optional EmailOutbound */ email, /* Optional GlideRecord */ email_action,
      /* Optional GlideRecord */ event) {
      var created = new GlideDateTime(current.sys_created_on);
      var now = new GlideDateTime();
      var duration = GlideDateTime.subtract(created, now);
      template.print("Time since creation: " + duration.getDisplayValue());
      template.print("\\nAssigned to: " + current.getDisplayValue('assigned_to'));
      if (current.escalation > 0) {
        template.print("\\n⚠️ ESCALATED " + current.escalation + " times");
      }
})(current, template, email, email_action, event);`
  }
});

// 4. Create notification
const criticalNotification = EmailNotification({
  $id: Now.ID["critical_incident_notification"],
  table: "incident",
  name: "Critical Incident Notification",
  category: criticalCategory,
  mandatory: true,
  triggerConditions: {
    generationType: "engine",
    onRecordInsert: true,
    onRecordUpdate: true,
    condition: "priority=1^EQ"
  },
  recipientDetails: {
    recipientFields: ["assigned_to", "caller_id"],
    recipientGroups: ["incident_managers_sys_id"]
  },
  emailContent: {
    subject: "🚨 CRITICAL: Incident \${number}",
    messageHtml: `<div class="critical-header">
      <h1>🚨 CRITICAL INCIDENT ALERT</h1>
      <span class="urgent-badge">IMMEDIATE ACTION REQUIRED</span>
    </div>
    <p><strong>Incident:</strong> \${number}</p>
    <p><strong>Priority:</strong> \${priority}</p>
    <p><strong>Description:</strong> \${short_description}</p>
    <p><strong>Additional Details:</strong></p>
    \${mail_script:Critical Incident Details Script}`,
    style: criticalStyle,
    importance: "high",
    includeAttachments: true,
    forceDelivery: true
  }
});
```

## Related Topics

- `emailnotification-api` — For complete API reference of all EmailNotification properties and types

- `business-rule-guide` — For understanding when to use business rules vs notification engine triggers

- `registering-events-guide` — For creating custom events that can trigger event-based notifications

- `table-guide` — For understanding table structures when configuring notification triggers

- `script-include-guide` — For reusable logic in notification scripts (advanced conditions or content generation)

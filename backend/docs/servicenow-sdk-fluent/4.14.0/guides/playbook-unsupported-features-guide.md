Version: 4.14.0

# Unsupported Features

This document covers playbook features the Fluent SDK doesn't yet support. For each limitation you'll find what works, what doesn't, and what needs to be handled directly in Workflow Studio. Whenever a limitation applies, see Handling Unsupported Features at the bottom — it covers how to look up the playbook and provide a direct Workflow Studio link.

## Table of Contents

- Activities

- Trigger Limitations

- Custom Process Type

- Legacy Schema Version

- Image Attachments

- Handling Unsupported Features

## Activities

All activity types from `ActivityDefinitions.Core.*` are supported. Questionnaire activities and any definitions outside the Core set are not supported.

If a playbook includes an unsupported activity, the rest of the playbook can still be generated — `ActivityDefinitions.Core.Placeholder` can be used as scaffolding in place of the unsupported activity, which you can then replace in Workflow Studio. When transforming an existing playbook that already contains unsupported activities, the transform falls back to the Record API rather than generating a `PlaybookDefinition`.

Creating a playbook with a Questionnaire activity: Use `ActivityDefinitions.Core.Placeholder` as scaffolding in place of the Questionnaire activity. The Placeholder can be swapped for the Questionnaire activity directly in Workflow Studio. See Handling Unsupported Features for the designer link.

Creating a playbook with a non-Core activity definition: Use `ActivityDefinitions.Core.Placeholder` as scaffolding in place of the unsupported activity. Only built-in `ActivityDefinitions.Core.*` definitions are supported. The Placeholder can be replaced with the correct activity type directly in Workflow Studio. See Handling Unsupported Features for the designer link.

Transforming an existing playbook with Questionnaire or non-Core activity records: The transform falls back to the Record API — a `PlaybookDefinition` cannot be generated. This playbook must be managed directly in Workflow Studio. See Handling Unsupported Features for the designer link.

## Trigger Limitations

### Unsupported Trigger Types

Four trigger types are supported:

| Supported |
| `PlaybookTriggerTypes.RecordCreate` |
| `PlaybookTriggerTypes.RecordUpdate` |
| `PlaybookTriggerTypes.RecordCreateOrUpdate` |
| `PlaybookTriggerTypes.Scheduled` |

Any other trigger type — such as on demand — is not supported. If a use case requires a different trigger type, a Flow Designer flow may be a better fit.

## Custom Process Type

Only the default Standard process type is supported by the Fluent SDK. Process type is a one-time decision — it's set when a playbook is created and cannot be changed afterward, even in Workflow Studio. Playbooks with a non-Standard process type must be created directly in Workflow Studio from the start.

Creating a playbook with a custom process type: The Fluent SDK cannot generate this playbook. Process type is set at creation time and cannot be changed afterward, so it must be created directly in Workflow Studio.

An existing playbook with a custom process type: Only Standard playbooks can be generated or modified by the Fluent SDK. This playbook must be managed directly in Workflow Studio. See Handling Unsupported Features for the designer link.

## Legacy Schema Version

The Fluent SDK was introduced with schema version 3. Playbooks with a `schema_version` below 3 predate the SDK entirely — their format is not understood and cannot be safely read or modified. Opening one of these playbooks in Workflow Studio will automatically migrate it to the current schema version.

Editing a playbook with a legacy schema version: The playbook cannot be read, generated, or modified through the Fluent SDK. Opening it directly in Workflow Studio will automatically migrate it to the current schema version. See Handling Unsupported Features for the designer link.

For the highest schema version a given release accepts, and how to choose one, see schemaVersion in `playbook-api`.

## Image Attachments

When a playbook is generated from an image via Now Assist, the source image is uploaded and kept as an attachment purely for later reference. It isn't editable in the designer, so there's no DSL surface for it either.

Pulling a playbook with an existing attachment preserves it automatically across subsequent pull/build round trips; pulling again picks up any change made on the instance.

## Handling Unsupported Features

Some unsupported features are partial limitations — the playbook can still be generated without the unsupported feature, which can then be configured in Workflow Studio. Others are hard limits where no Fluent file can be produced:

- Custom process type — process type is set at creation time and cannot be changed afterward, even in Workflow Studio.

- Transforming an existing playbook with unsupported features — a playbook that contains unsupported activities falls back to the Record API rather than generating a `PlaybookDefinition`.

- Legacy schema version — the schema predates the Fluent SDK entirely and cannot be safely read or modified.

When a limitation requires completing configuration in Workflow Studio, a direct link can be provided to take the user there.

Opening a playbook in Workflow Studio

Playbooks can be opened directly in Workflow Studio using a link that requires the ServiceNow instance URL and the playbook's `sys_id`. The `sys_id` can be found by querying `sys_pd_process_definition` by display name, or in the generated keys file if the playbook was built from a `.now.ts` file. The link follows this pattern:

```
https://<instance>/now/workflow-studio/builder?table=sys_pd_process_definition&sysId=<sys_id>&
```

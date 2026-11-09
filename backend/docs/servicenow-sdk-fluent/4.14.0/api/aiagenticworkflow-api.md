Version: 4.14.0

# AiAgenticWorkflow

Configure an AI Agentic Workflow record. AI Agentic Workflows orchestrate multiple
AI Agents working together as a team, with shared context, triggers, and version
management in ServiceNow's AI Agent Studio.

Branding note: "Now Assist" has been rebranded to "ServiceNow Otto." These names refer to the same product. All technical identifiers (table names, field names, string literals like `"Now Assist Panel"`, `now_assist_deployment`) remain unchanged — use them exactly as-is in code.

## Signature

```
AiAgenticWorkflow(config)
```

## Usage

```
import '@servicenow/sdk/global'
import { AiAgenticWorkflow } from '@servicenow/sdk/core'

AiAgenticWorkflow({
  $id: Now.ID['my_workflow'],
  name: 'My Workflow',
  description: 'Orchestrates agents to analyze records',
  recordType: 'custom',
  securityAcl: {
    $id: Now.ID['my_workflow_acl'],
    type: 'Any authenticated user',
  },
  team: {
    $id: Now.ID['my_team'],
    name: 'My Team',
    members: ['agent_sys_id_1', 'agent_sys_id_2'],
  },
  versions: [
    {
      name: 'V1',
      number: 1,
      state: 'published',
      instructions: 'Analyze records and generate summaries.',
    },
  ],
})
```

## Parameters

### config

`AiAgenticWorkflowType`

AI Agentic Workflow configuration object.

See the `building-ai-agents-guide` topic for team configuration, instructions authoring, trigger setup, and best practices.

Properties:

- 
$id (required): `string | number | ExplicitKey<string>`
Unique identifier for the workflow

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit/view access for other developers after the application is installed. `'read'` lets others see the configuration but not change it. `'protected'` prevents others from changing the record. Omit to allow customization.

- 
$override (optional): `Record<string, string | boolean | number>`
Set properties not directly supported by this API. Key-value pairs are written as additional fields on the generated record.

- 
name (required): `string`
Display name of the AI Agentic Workflow

- 
description (required): `string`
Brief description of what the workflow does. Also auto-populates `team.description`.

- 
securityAcl (required): `SecurityAclUserAccessConfig`
Controls who can invoke the workflow. Automatically generates `sys_security_acl` and `sys_security_acl_role` records. Uses discriminated union on `type`: `'Any authenticated user'`, `'Specific role'`, or `'Public'`. Requires `$id` and for `'Specific role'`, also requires `roles` array of role sys_ids.

- 
active (optional): `boolean`
Whether the workflow is active. Default: `true`

- 
contextProcessingScript (optional): `function | string`
Script to process context before workflow execution. Supports inline scripts or `Now.include()`.

- 
dataAccess (optional): `DataAccessConfigWorkflowType`
Data access controls — required when `runAs` is not set. Defines which roles the workflow can inherit from the invoking user. Use `roleMap` (role names) or `roleList` (role sys_ids). At least one must be non-empty when `runAs` is not set.

- 
executionMode (optional): `'copilot' | 'autopilot'`
Execution mode for the workflow. Default: `'copilot'`

- 
memoryScope (optional): `string`
Memory scope for team members. Default: `'global'`

- 
recordType (optional): `'custom' | 'template' | 'aia_internal'`
Record type. Default: `'template'`. Must set `'custom'` for user-created workflows.

- 
runAs (optional): `string`
Field name for run-as user (dynamic resolution). When set, `dataAccess` is optional. When omitted, the workflow uses dynamic user identity and `dataAccess` becomes mandatory.

- 
sysDomain (optional): `string`
Domain ID. Default: `'global'`

- 
team (optional): `TeamType`
Team configuration with nested `members` array. Key fields:

- `$id` (required) — unique identifier for the team

- `name` — team name

- `sysDomain` — domain ID (default: `'global'`)

- `members` — array of agent sys_ids or `Record<'sn_aia_agent'>` references

Team `description` is auto-populated from the workflow's `description`. Do not set it manually.

- 
triggerConfig (optional): `TriggerConfigType[]`
Array of trigger configurations for automatic invocation. Supported types: `'record_create'`, `'record_create_or_update'`, `'record_update'`, `'email'`, `'scheduled'`, `'daily'`, `'weekly'`, `'monthly'`, `'ui_action'`. Key fields: `name`, `channel` (use `'Now Assist Panel'`), `objectiveTemplate`, `targetTable`, `triggerFlowDefinitionType`, `triggerCondition`. For scheduled triggers, use `schedule` nested object.

- 
versions (optional): `AIAVersion[]`
Array of version configurations. Key fields: `name`, `number`, `state` (`'draft'`, `'committed'`, `'published'`, `'withdrawn'`), `instructions`, `condition`.

Note: The following fields are auto-generated and should not be specified:
`internalName` (auto-generated from `domain.scope.name`), trigger `useCase` (auto-populated with parent workflow ID).

## Examples

### Workflow with Data Access and Triggers

```
/**
 * @title Workflow with Data Access and Triggers
 * @description Create a workflow with role-based access and record/scheduled triggers
 */

import '@servicenow/sdk/global'
import { AiAgenticWorkflow } from '@servicenow/sdk/core'

export const exampleAgenticWorkflow = AiAgenticWorkflow({
  $id: Now.ID['employee_record_summarization_workflow'],
  name: 'Employee Record Summarization',
  description: 'Analyzes employee records and generates summaries',
  recordType: 'custom',

  securityAcl: {
    $id: Now.ID['employee_summarization_workflow_acl'],
    type: 'Any authenticated user',
  },

  team: {
    $id: Now.ID['employee_summarization_team'],
    name: 'Employee Summarization Team',
    members: [
      '274b465a7d5f42e581664209557b2b18',  // Record Summary Agent sys_id
      '2dfb22af3351f2101ea99d273e5c7ba3',  // Search Q&A Agent sys_id
    ],
  },

  versions: [
    {
      name: 'V1',
      number: 1,
      state: 'published',
      instructions: 'Fetch employee record, analyze key fields, and generate summary',
    },
    {
      name: 'V2',
      number: 2,
      instructions: 'Enhanced version with validation and department analysis',
    },
  ],

  triggerConfig: [
    {
      name: 'Employee Record Created',
      targetTable: 'x_snc_cust_app_age_employee',
      triggerFlowDefinitionType: 'record_create',
      triggerCondition: 'first_nameISNOTEMPTY',
      objectiveTemplate: 'Summarize employee record ${sys_id}',
      runAsScript: Now.include('./run-as-script.js'),
      showNotifications: true,
      channel: 'Now Assist Panel',
    },
    {
      name: 'Weekly Employee Review',
      active: true,
      targetTable: 'x_snc_cust_app_age_employee',
      triggerCondition: 'first_nameISNOTEMPTY',
      triggerFlowDefinitionType: 'scheduled',
      objectiveTemplate: 'Review all employee records for the week',
      schedule: {
        runDayOfWeek: 2,                         // Monday
        runDayOfMonth: 2,
        starting: '1970-01-01 09:00:00',
        time: '1970-01-01 09:00:00',
      },
      channel: 'Now Assist Panel',
    },
  ],

  dataAccess: {
    roleMap: ['admin'],
    description: 'Restrict workflow access to admin role',
  },
})
```

### Workflow with Fixed User Identity

```
/**
 * @title Workflow with Fixed User Identity
 * @description Create a workflow that runs as a specific user
 */

import '@servicenow/sdk/global'
import { AiAgenticWorkflow } from '@servicenow/sdk/core'

export const dynamicUserWorkflow = AiAgenticWorkflow({
  $id: Now.ID['incident_management_workflow'],
  name: 'Incident Management Workflow',
  description: 'Analyzes incident records, identifies patterns, and provides resolution recommendations',
  recordType: 'custom',
  runAs: '<sys_user_id>',

  securityAcl: {
    $id: Now.ID['incident_management_workflow_acl'],
    type: 'Any authenticated user',
  },

  team: {
    $id: Now.ID['incident_workflow_team'],
    name: 'Incident Management Team',
    members: [],
  },

  versions: [
    {
      name: 'V1',
      number: 1,
      state: 'published',
      instructions: 'Analyze incident ${number} with priority ${priority}. Identify potential root causes and suggest resolution steps.',
    },
  ],
})
```

### Workflow with Record References

```
/**
 * @title Workflow with Record References
 * @description Create a workflow using Record API for agent references
 */

import '@servicenow/sdk/global'
import { AiAgenticWorkflow, Record } from '@servicenow/sdk/core'

const summaryAgent = Record({
  table: 'sn_aia_agent',
  $id: Now.ID['summary_agent'],
  data: { name: 'Record Summary Agent' },
})

const searchAgent = Record({
  table: 'sn_aia_agent',
  $id: Now.ID['search_agent'],
  data: { name: 'Search Q&A Agent' },
})

export const analysisWorkflow = AiAgenticWorkflow({
  $id: Now.ID['analysis_workflow'],
  name: 'Analysis Workflow',
  description: 'Workflow using Record references for agent members',
  recordType: 'custom',

  securityAcl: {
    $id: Now.ID['analysis_workflow_acl'],
    type: 'Any authenticated user',
  },

  dataAccess: {
    roleMap: ['itil', 'user_admin'],
    description: 'Data access for itil and user_admin roles',
  },

  team: {
    $id: Now.ID['analysis_team'],
    name: 'Analysis Team',
    members: [summaryAgent, searchAgent],
  },
})
```

For guidance on team configuration, agent decomposition, trigger setup, instructions authoring, and common patterns, see the `building-ai-agents-guide` topic.

## Supported Record Types

| Record Type | Table | Description |
| AI Agentic Workflow | `sn_aia_usecase` | Primary workflow definition |
| AI Team | `sn_aia_team` | Team configuration for the workflow |
| AI Team Member | `sn_aia_team_member` | Team member associations (agents in the team) |
| AI Version | `sn_aia_version` | Version information for the workflow |
| Use Case Config Override | `sn_aia_usecase_config_override` | Configuration overrides for the workflow |
| Trigger Configuration | `sn_aia_trigger_configuration` | Automated trigger definitions |
| Trigger Agent Usecase M2M | `sn_aia_trigger_agent_usecase_m2m` | Mapping between triggers, workflows, and use cases |
| Agent Access Role Configuration | `sys_agent_access_role_configuration` | Role-based data access controls |

## Coalesce Keys

Coalesce keys determine how the plugin identifies existing records for updates (upsert behavior).

| Table | Coalesce Keys |
| `sn_aia_usecase` | `name` |
| `sn_aia_team` | `name` |
| `sn_aia_team_member` | `agent` , `team` |
| `sn_aia_version` | `target_id` , `version_name` |
| `sn_aia_trigger_configuration` | `name` , `usecase` |
| `sn_aia_trigger_agent_usecase_m2m` | `trigger_configuration` , `related_resource_record` |
| `sn_aia_usecase_config_override` | `usecase_configuration` |
| `sys_agent_access_role_configuration` | `agent` |
| `sys_agent_access_role_mapping` | `agent_access_config` , `role` |
| `sys_security_acl_role` | `sys_security_acl` , `sys_user_role` |

## Field Mapping (Fluent → ServiceNow)

### Workflow (`sn_aia_usecase`)

| Fluent Property | ServiceNow Field | Notes |
| `name` | `name` |  |
| `description` | `description` | Also auto-populates `team.description` |
| `recordType` | `record_type` | Default: `'template'` — set `'custom'` for user-created |
| `executionMode` | `execution_mode` | Default: `'copilot'` |
| `active` | `active` | Default: `true` |
| `sysDomain` | `sys_domain` | Default: `'global'` |
| `contextProcessingScript` | `context_processing_script` | Auto CDATA wrapped |

### Team (`sn_aia_team`)

| Fluent Property | ServiceNow Field | Notes |
| `team.$id` | record ID | Mandatory for teams |
| `team.name` | `name` | Auto-generated from workflow name if omitted |
| `team.sysDomain` | `sys_domain` | Default: `'global'` |
| `team.description` | `description` | Auto-populated from workflow `description` — do not set manually |

### Team Members (`sn_aia_team_member`)

| Fluent Property | ServiceNow Field | Notes |
| `team.members[n]` | `agent` | Agent sys_id or `Record<'sn_aia_agent'>` |
| `memoryScope` | `memory_scope` | Default: `'global'` |

### Use Case Config (`sn_aia_usecase_config_override`)

| Fluent Property | ServiceNow Field | Notes |
| `runAs` | `run_as_user` | Reference to `sys_user` |
| `active` | `active` |  |

### Version (`sn_aia_version`)

| Fluent Property | ServiceNow Field | Notes |
| `versions[n].name` | `version_name` |  |
| `versions[n].number` | `version_number` | Default: `1` |
| `versions[n].state` | `state` | Default: `'draft'` |
| `versions[n].instructions` | `instructions` |  |
| `versions[n].condition` | `condition` |  |

### Trigger Config (`sn_aia_trigger_configuration`)

| Fluent Property | ServiceNow Field | Notes |
| `name` | `name` |  |
| `description` | `description` |  |
| `active` | `active` | Default: `false` |
| `channel` | `channel` | Use `'Now Assist Panel'` — auto-resolved to sys_id |
| `triggerCondition` | `condition` | Encoded query |
| `objectiveTemplate` | `objective_template` |  |
| `targetTable` | `target_table` |  |
| `triggerFlowDefinitionType` | `trigger_flow_definition_type` |  |
| `runAs` | `run_as` |  |
| `runAsScript` | `run_as_script` | Auto CDATA wrapped |
| `runAsUser` | `run_as_user` |  |
| `enableDiscovery` | `enable_discovery` | Default: `false` |
| `showNotifications` | `show_notifications` | Default: `false` |
| `domain` | `sys_domain` | Default: `'global'` |
| `useCase` | `usecase` | Auto-set to parent workflow ID |
| `schedule.runDayOfMonth` | `run_dayofmonth` | Number (1-31) |
| `schedule.runDayOfWeek` | `run_dayofweek` | Number (1=Sunday, 7=Saturday) |
| `schedule.repeatInterval` | `run_period` | Duration format |
| `schedule.starting` | `run_start` | YYYY-MM-DD HH:MM:SS |
| `schedule.time` | `run_time` | 1970-01-01 HH:MM:SS |
| `schedule.triggerStrategy` | `trigger_strategy` |  |
| `notificationScript` | `notification_script` | Client script for handling notifications |
| `profile` | `profile` | ServiceNow Otto deployment profile |
| `portal` | `portal` | ServiceNow Otto deployment channel |
| `businessRule` | `business_rule` | Reference to business rule |
| `sysOverrides` | `sys_overrides` | Override the trigger configuration record |
| `m2mSysOverrides` | `sys_overrides` (on M2M) | Override the trigger-workflow-usecase mapping |
| `triggerFlow` | `trigger_flow` | Reference to Flow Designer flow |

## Related

- query-guide.md — `now-sdk query` syntax for looking up sys_ids, verifying deployments, and resolving references

- building-ai-agents-guide.md — guide for building AI Agents and Agentic Workflows

- aiagent-api.md — AI Agent API reference

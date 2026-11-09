Version: 4.14.0

# AiAgent

Configure an AI Agent record. AI Agents are intelligent agents that execute tools,
process context, control access, trigger automatically, and manage versions in
ServiceNow's AI Agent Studio.

Branding note: "Now Assist" has been rebranded to "ServiceNow Otto." These names refer to the same product. All technical identifiers (table names, field names, string literals like `"Now Assist Panel"`, `now_assist_deployment`) remain unchanged — use them exactly as-is in code.

## Signature

```
AiAgent(config)
```

## Usage

```
import '@servicenow/sdk/global'
import { AiAgent } from '@servicenow/sdk/core'

AiAgent({
  $id: Now.ID['my_agent'],
  name: 'My Agent',
  description: 'An AI agent that assists with tasks',
  agentRole: 'Task assistant',
  recordType: 'custom',
  securityAcl: {
    $id: Now.ID['my_agent_acl'],
    type: 'Any authenticated user',
  },
  versionDetails: [
    {
      name: 'V1',
      number: 1,
      state: 'published',
      instructions: 'Assist users with their tasks.',
    },
  ],
})
```

## Parameters

### config

`AiAgentType`

AI Agent configuration object.

See the `building-ai-agents-guide` topic for tool selection, instructions authoring, trigger configuration, and best practices.

Properties:

- 
$id (required): `string | number | ExplicitKey<string>`
Unique identifier for the agent

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit/view access for other developers after the application is installed. `'read'` lets others see the configuration but not change it. `'protected'` prevents others from changing the record. Omit to allow customization.

- 
$override (optional): `Record<string, string | boolean | number>`
Set properties not directly supported by this API. Key-value pairs are written as additional fields on the generated record.

- 
name (required): `string`
Display name of the AI Agent

- 
description (required): `string`
Brief description of what the agent does

- 
agentRole (required): `string`
Role or purpose of the agent (e.g., "News research specialist")

- 
securityAcl (required): `SecurityAclUserAccessConfig`
Controls who can invoke the agent. Automatically generates `sys_security_acl` and `sys_security_acl_role` records. Uses discriminated union on `type`: `'Any authenticated user'`, `'Specific role'`, or `'Public'`. Requires `$id` and for `'Specific role'`, also requires `roles` array of role sys_ids.

- 
active (optional): `boolean`
Whether the agent is active. Default: `true`

- 
advancedMode (optional): `boolean`
Enables advanced configuration options for power users. Default: `false`

- 
agentConfigSysOverrides (optional): `string | Record<'sn_aia_agent_config'>`
Reference to override another agent config

- 
agentDescriptor (optional): `AiAgentDescriptorType | ''`
Classifies how the agent was created or its access requirement. Values: `'require_caller_id'`, `'created_by_ai_agent_advisor'`, `'created_by_build_agent'`. Default: `''`

- 
agentLearning (optional): `boolean`
Enable agent learning from interactions. Default: `false`

- 
agentType (optional): `'internal' | 'external' | 'voice' | 'aia_internal'`
Type of agent. Default: `'internal'`

- 
channel (optional): `'nap' | 'nap_and_va'`
Channel where the agent operates. `'nap'` = ServiceNow Otto Panel only; `'nap_and_va'` = Panel + Virtual Agent. Default: `'nap_and_va'`

- 
compiledHandbook (optional): `string`
Compiled handbook content for the agent

- 
condition (optional): `string`
Condition table reference

- 
contextProcessingScript (optional): `((context: any, ...dependencies: any[]) => any) | string`
Server-side script that transforms or enriches context before agent execution.
Consider using `Now.include()` to move the script to a separate `.js` file or using a function exported from your `src/server` modules.

- 
dataAccess (optional): `DataAccessConfigType`
Data access controls — required when `runAsUser` is not set. Defines which roles the agent can inherit from the invoking user. Use `roleMap` (role names resolved at build time) or `roleList` (role sys_ids). At least one must be non-empty when `runAsUser` is not set.

- 
docUrl (optional): `string`
Documentation URL for the agent

- 
external (optional): `boolean`
Whether the agent is external

- 
externalAgentConfiguration (optional): `string | Record<'sn_aia_external_agent_configuration'>`
Reference to external agent configuration

- 
iconUrl (optional): `string`
Icon URL for the agent in the UI

- 
memoryCategories (optional): `AiAgentMemoryCategory[]`
Categories of long-term memory the agent may access: `'device_and_software'`, `'meetings_and_events'`, `'projects'`, `'workplace'`

- 
parent (optional): `string | Record<'sn_aia_agent'>`
Reference to the parent AI Agent

- 
postProcessingMessage (optional): `string`
Message displayed after agent completes processing

- 
processingMessage (optional): `string`
Message displayed while agent is processing

- 
public (optional): `boolean`
Whether the agent is publicly accessible. Default: `false`

- 
recordType (optional): `'template' | 'aia_internal' | 'custom' | 'promoted'`
Lifecycle stage of the agent. Default: `'template'`. Must set `'custom'` for user-created agents.

- 
runAsUser (optional): `string | Record<'sys_user'>`
User to run the agent as (sys_user sys_id or Record reference). When set, `dataAccess` is optional.

- 
sourceId (optional): `string | Record<'sn_aia_agent'>`
Reference to source agent (for cloned agents)

- 
sysDomain (optional): `string`
Domain ID

- 
tools (optional): `AiAgentToolDetailsType[]`
Array of tools the agent can use. Each tool uses a discriminated union on `type`:

- `'crud'` — requires `inputs: ToolInputType`

- `'script'` — requires `script`

- `'capability'` — requires `capabilityId`

- `'subflow'` — requires `subflowId`

- `'action'` — requires `flowActionId`

- `'catalog'` — requires `catalogItemId`

- `'topic'` / `'topic_block'` — requires `virtualAgentId`

- `'web_automation'`, `'knowledge_graph'`, `'file_upload'`, `'deep_research'`, `'desktop_automation'`, `'mcp'` — OOB tools, no extra fields

- `'search_retrieval'` — optional `inputs: RagInputType`

For script tools, `inputs` is a simple array of `ToolInputField`. For CRUD tools, `inputs` is a `ToolInputType` object. The SDK auto-generates `input_schema` from `inputs`.

- 
triggerConfig (optional): `AiAgentTriggerConfigType[]`
Array of trigger configurations. Supported types: `'record_create'`, `'record_create_or_update'`, `'record_update'`, `'email'`, `'scheduled'`, `'daily'`, `'weekly'`, `'monthly'`. Key fields: `name`, `channel`, `objectiveTemplate`, `targetTable`, `triggerFlowDefinitionType`, `triggerCondition`. For scheduled triggers, use `schedule` nested object.

- 
versionDetails (optional): `AiAgentVersionDetailsType[]`
Array of version details. Key fields: `name`, `number`, `state` (`'draft'`, `'committed'`, `'published'`, `'withdrawn'`), `instructions`, `condition`.

## Examples

### AI Agent with Multiple Tool Types

Create an AI agent with OOB, RAG, CRUD, and Script tools, plus triggers.

```
/**
 * @title AI Agent with Multiple Tool Types
 * @description Create an AI agent with OOB, RAG, CRUD, and Script tools
 */

import '@servicenow/sdk/global'
import { AiAgent } from '@servicenow/sdk/core'
import { validateTweetData } from '../../server/ai-agent/validate-tweet-data'

export const newsCollectorAgent = AiAgent({
  $id: Now.ID['news_collector_agent'],
  name: 'News Collector Agent',
  description: 'AI agent that searches for and saves news articles',
  agentRole: 'News research specialist',
  agentDescriptor: 'created_by_build_agent',
  recordType: 'custom',
  channel: 'nap_and_va',
  processingMessage: 'Searching for news...',
  postProcessingMessage: 'News collection completed',

  versionDetails: [
    {
      name: 'V1',
      number: 1,
      state: 'published',
      instructions: `You are a news collection specialist. Your job is to:
1. Search the web for the latest news articles using the Web Search tool
2. Save articles to the database using the Save Article tool
3. Provide a comprehensive summary of findings`,
    },
  ],

  securityAcl: {
    $id: Now.ID['news_collector_agent_acl'],
    type: 'Specific role',
    roles: [
      '282bf1fac6112285017366cb5f867469',  // itil
      'b05926fa0a0a0aa7000130023e0bde98',  // user
    ],
  },

  dataAccess: {
    roleMap: ['itil', 'user'],
    description: 'Role-based access for news collection',
  },

  tools: [
    {
      name: 'Web Search',
      description: 'Searches the web for latest news articles',
      type: 'web_automation',
      executionMode: 'autopilot',
      maxAutoExecutions: 5,
      displayOutput: true,
      outputTransformationStrategy: 'paraphrase',
      preMessage: 'Searching the web for news...',
      postMessage: 'Search completed',
    },
    {
      name: 'Knowledge Search',
      description: 'Searches knowledge articles for relevant information',
      type: 'search_retrieval',
      executionMode: 'autopilot',
      preMessage: 'Searching knowledge base...',
      postMessage: 'Search completed',
      inputs: {
        searchType: {
          type: 'semantic',
          semanticIndexes: [{ value: 'kb_knowledge_text_index', label: 'KB Text Index' }],
          documentMatchThreshold: 0.5,
        },
        searchProfile: { value: 'sn_aia_ai_agents_tool_search', label: '[AI Agents] - Tool Search' },
        sources: [{ value: 'kb_knowledge', label: 'Knowledge Base' }],
        fields: [
          { value: 'short_description', label: 'Short Description' },
          { value: 'text', label: 'Article Text' },
        ],
        searchResultsLimit: 5,
      },
    },
    {
      name: 'Save Article',
      description: 'Saves a news article to the database',
      type: 'crud',
      recordType: 'custom',
      executionMode: 'autopilot',
      preMessage: 'Saving article...',
      postMessage: 'Article saved successfully',
      inputs: {
        operationName: 'create',
        table: 'x_my_app_news_articles',
        inputFields: [
          { name: 'title', description: 'Article title', mandatory: true, mappedToColumn: 'title', type: 'string' },
          { name: 'content', description: 'Article content', mandatory: false, mappedToColumn: 'content', type: 'string' },
        ],
        returnFields: [{ name: 'sys_id' }, { name: 'title' }, { name: 'number' }],
      },
    },
    {
      name: 'Validate Tweet Data',
      description: 'Validates tweet content and enriches it with metadata',
      type: 'script',
      executionMode: 'autopilot',
      preMessage: 'Validating tweet data...',
      postMessage: 'Validation completed',
      script: validateTweetData,
      inputs: [
        { name: 'content', description: 'The tweet content to validate', mandatory: true, value: '', invalidMessage: null },
      ],
    },
  ],

  triggerConfig: [
    {
      name: 'News Collection Trigger',
      channel: 'Now Assist Panel',
      objectiveTemplate: 'Collect latest news for topic: ${topic_name}',
      targetTable: 'x_my_app_news_topics',
      triggerFlowDefinitionType: 'record_create_or_update',
      triggerCondition: 'active=true^priority=high',
      showNotifications: true,
    },
    {
      name: 'Daily News Summary Trigger',
      channel: 'Now Assist Panel',
      objectiveTemplate: 'Generate daily news summary report',
      targetTable: 'x_my_app_news_topics',
      triggerCondition: 'active=true',
      triggerFlowDefinitionType: 'daily',
      schedule: {
        time: '1970-01-01 08:00:00',
        triggerStrategy: 'every',
      },
    },
  ],
})
```

### AI Agent with Dynamic User Identity

Create an agent that inherits roles from the invoking user.

```
/**
 * @title AI Agent with Dynamic User Identity
 * @description Create an agent with role-based data access
 */

import '@servicenow/sdk/global'
import { AiAgent } from '@servicenow/sdk/core'

export const dynamicAgent = AiAgent({
  $id: Now.ID['dynamic_agent'],
  name: 'Dynamic Agent',
  description: 'Agent with dynamic user identity',
  agentRole: 'Dynamic assistant',
  recordType: 'custom',
  securityAcl: { $id: Now.ID['dynamic_agent_acl'], type: 'Any authenticated user' },
  versionDetails: [
    { name: 'V1', number: 1, state: 'published', instructions: 'Assist users with their tasks...' },
  ],
  dataAccess: {
    roleMap: ['itil'],
  },
})
```

### AI Agent with Fixed User Identity

Create an agent that always runs as a specific user.

```
/**
 * @title AI Agent with Fixed User Identity
 * @description Create an agent with a fixed run-as user
 */

import '@servicenow/sdk/global'
import { AiAgent } from '@servicenow/sdk/core'

export const fixedAgent = AiAgent({
  $id: Now.ID['fixed_agent'],
  name: 'Fixed Agent',
  description: 'Agent with fixed user identity',
  agentRole: 'System assistant',
  recordType: 'custom',
  securityAcl: { $id: Now.ID['fixed_agent_acl'], type: 'Any authenticated user' },
  runAsUser: '82ef6be43bc7a2103542c11f23e45a61',
  versionDetails: [
    { name: 'V1', number: 1, state: 'published', instructions: 'Perform system tasks...' },
  ],
})
```

For guidance on tool types, security configuration, trigger setup, instructions authoring, and common patterns, see the `building-ai-agents-guide` topic.

## Supported Record Types

| Record Type | Table | Description |
| AI Agent | `sn_aia_agent` | Primary agent definition |
| AI Agent Config | `sn_aia_agent_config` | Agent configuration and settings |
| AI Agent Version | `sn_aia_version` | Version information for the agent |
| AI Agent Tool | `sn_aia_tool` | Tool definitions (script, CRUD, RAG, etc.) |
| AI Agent Tool M2M | `sn_aia_agent_tool_m2m` | Many-to-many relationship between agents and tools |
| Agent Access Role Configuration | `sys_agent_access_role_configuration` | Role-based data access controls |
| Trigger Configuration | `sn_aia_trigger_configuration` | Automated trigger definitions |
| Trigger Agent Usecase M2M | `sn_aia_trigger_agent_usecase_m2m` | Mapping between triggers, agents, and use cases |

## Coalesce Keys

Coalesce keys determine how the plugin identifies existing records for updates (upsert behavior).

| Table | Coalesce Keys |
| `sn_aia_agent` | `name` |
| `sn_aia_agent_config` | `agent` |
| `sn_aia_version` | `target_id` , `version_name` |
| `sn_aia_tool` | `name` |
| `sn_aia_agent_tool_m2m` | `agent` , `tool` , `name` |
| `sys_agent_access_role_configuration` | `agent` |
| `sys_agent_access_role_mapping` | `agent_access_config` , `role` |
| `sys_security_acl_role` | `sys_security_acl` , `sys_user_role` |
| `sn_aia_trigger_configuration` | `name` |
| `sn_aia_trigger_agent_usecase_m2m` | `trigger_configuration` , `related_resource_record` |
| `sn_aia_ltm_category_mapping` | `entity_id` , `category` |

## Field Mapping (Fluent → ServiceNow)

### Agent (`sn_aia_agent`)

| Fluent Property | ServiceNow Field | Notes |
| `name` | `name` |  |
| `description` | `description` |  |
| `agentRole` | `role` |  |
| `agentType` | `agent_type` | Default: `'internal'` |
| `channel` | `channel` | Default: `'nap_and_va'` |
| `compiledHandbook` | `compiled_handbook` |  |
| `condition` | `condition` |  |
| `contextProcessingScript` | `context_processing_script` | Auto CDATA wrapped |
| `parent` | `parent` | Reference to `sn_aia_agent` |
| `recordType` | `record_type` | Default: `'template'` — set `'custom'` for user-created |
| `sourceId` | `source_id` | Reference to `sn_aia_agent` |
| `sysDomain` | `sys_domain` |  |

### Agent Config (`sn_aia_agent_config`)

| Fluent Property | ServiceNow Field | Notes |
| `active` | `active` | Default: `true` |
| `advancedMode` | `advanced_mode` | Default: `false` |
| `agentDescriptor` | `agent_descriptor` | Default: `''` |
| `agentLearning` | `agent_learning` | Default: `false` |
| `docUrl` | `doc_url` |  |
| `iconUrl` | `icon_url` |  |
| `public` | `public` | Default: `false` |
| `runAsUser` | `run_as_user` | Reference to `sys_user` |
| `agentConfigSysOverrides` | `sys_overrides` |  |

### Version Details (`sn_aia_version`)

| Fluent Property | ServiceNow Field | Notes |
| `name` | `version_name` |  |
| `number` | `version_number` |  |
| `state` | `state` | Default: `'draft'` |
| `instructions` | `instructions` |  |
| `condition` | `condition` |  |

### Trigger Config (`sn_aia_trigger_configuration`)

| Fluent Property | ServiceNow Field | Notes |
| `name` | `name` |  |
| `description` | `description` |  |
| `active` | `active` | Default: `false` |
| `channel` | `channel` | `'nap'` / `'nap_and_va'` for agents |
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
| `schedule.runDayOfMonth` | `run_dayofmonth` | Number (1-31) |
| `schedule.runDayOfWeek` | `run_dayofweek` | Number (1=Sunday, 7=Saturday) |
| `schedule.repeatInterval` | `run_period` | Duration format |
| `schedule.starting` | `run_start` | YYYY-MM-DD HH:MM:SS |
| `schedule.time` | `run_time` | 1970-01-01 HH:MM:SS |
| `schedule.triggerStrategy` | `trigger_strategy` |  |
| `usecase` | `usecase` | Optional — link trigger to a workflow |
| `triggerFlow` | `trigger_flow` | Reference to Flow Designer flow |
| `usecaseDiscovery` | `usecase_discovery` | Default: `false` |
| `m2mSysOverrides` | `sys_overrides` (on M2M) | Override the trigger-agent-usecase mapping |
| `notificationScript` | `notification_script` | Client script for handling notifications |
| `profile` | `profile` | ServiceNow Otto deployment profile |
| `portal` | `portal` | ServiceNow Otto deployment channel |
| `businessRule` | `business_rule` | Reference to business rule |
| `sysOverrides` | `sys_overrides` | Override the trigger configuration record |

### Tool Overrides

| Fluent Property | Target Record | Purpose |
| `sysOverrides` | Tool definition ( `sn_aia_tool` ) | Overriding the tool record itself |
| `m2mSysOverrides` | M2M record ( `sn_aia_agent_tool_m2m` ) | Overriding the agent-tool relationship |

## Related

- query-guide.md — `now-sdk query` syntax for looking up sys_ids, verifying deployments, and resolving role references

- building-ai-agents-guide.md — guide for building AI Agents and Agentic Workflows

- aiagenticworkflow-api.md — AI Agentic Workflow API reference

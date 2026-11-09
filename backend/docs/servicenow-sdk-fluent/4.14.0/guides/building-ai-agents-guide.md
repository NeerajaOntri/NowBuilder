Version: 4.14.0

# Building AI Agents Guide

Build and configure ServiceNow AI Agents and AI Agentic Workflows using the Fluent SDK. AI Agents perform tasks with tools (CRUD, script, OOB, reference-based), while AI Agentic Workflows orchestrate multiple agents as a team. This guide covers agent structure, authentication, triggers, ACL deployment, and workflow configuration. Requires SDK 4.4.0 or higher.

Branding note: "Now Assist" has been rebranded to "ServiceNow Otto." These names refer to the same product. All technical identifiers (table names, field names, string literals like `"Now Assist Panel"`, `now_assist_deployment`) remain unchanged — use them exactly as-is in code.

## When to Use

- Creating a new AI Agent in ServiceNow

- Creating AI Agentic Workflows that orchestrate multiple agents

- Modifying existing agents or agentic workflows (adding tools, changing auth, updating instructions)

- Configuring agent authentication and security (Dynamic User vs AI User)

- Selecting and configuring agent tools (CRUD, script, OOB tools)

- Setting up triggers for agents or agentic workflows

- Defining team members for agentic workflows

Related guides:

- See the `building-ai-agents-tools-guide` topic for tool selection, CRUD/script/OOB/RAG tools, execution mode, and tool composition

- See the `building-ai-agents-advanced-guide` topic for instructions authoring, authentication procedures, validation, error recovery, and deployment checklists

- See the `aiagent-api` topic for AI Agent API reference

- See the `aiagenticworkflow-api` topic for AI Agentic Workflow API reference

## Creation Workflow (Mandatory Steps)

Default rule: do not write or generate any agent/workflow code until Q1–Q4 in Phase 2 below have each been either explicitly answered by the user or explicitly confirmed via the Shortcut below. A short natural-language request (e.g. "create an agent to manage travel," "build me an incident bot") is a description of what the agent should do — it is NOT a specification of auth mode, roles, triggers, or ACL access. Do not infer, default, or hallucinate those four answers just because the user described a purpose. Vague requests get MORE questions asked, not fewer.

When creating a new AI Agent or Agentic Workflow, follow these phases in order. Steps marked [STOP] require user input — do NOT proceed until the user responds. Ask questions one at a time; do not batch them.

Shortcut for explicit requests — narrow exception: The Shortcut applies ONLY when the user's request ALREADY states the answer to a given question in the same message (e.g., "...using Dynamic User with admin role, triggered on record create, accessible to itil users" explicitly states auth, roles, trigger, and ACL). For each of Q1–Q4 independently: if that specific answer was explicitly stated, state your inference and confirm in one pass ("Based on your request, I'll use: Auth — Dynamic User, Roles — admin, Trigger — record create on incident, ACL — itil. Is that correct?") and skip its `[STOP]`. If that specific answer was NOT explicitly stated — even if the rest of the request was detailed — you MUST still ask that one via its `[STOP]`. The Shortcut is evaluated per-question, not per-request: a detailed request can still leave one or two questions unanswered, and those still require `[STOP]`.

Anti-pattern (this exact failure has been observed — do not repeat it): User says "create an AI agent to manage travel" → agent immediately writes `.now.ts` code with an inferred `runAsUser`/`dataAccess`, a guessed role list, no trigger, and a guessed ACL type. This is wrong: none of Q1–Q4 were specified, so all four `[STOP]` questions were required before any code was written.

### Phase 1: Discovery

- Prerequisite check: Verify subscription/license (see Prerequisites below). This is a mandatory gate — do NOT proceed to Phase 2 until availability is confirmed.

- Check for existing agents/workflows: Before creating anything, search for similar agents on the instance:

- Query `sn_aia_agent` (encodedQuery: `nameLIKE<name>`) and `sn_aia_usecase` (encodedQuery: `nameLIKE<name>`) to check for duplicates.

- If matches found, present them to the user: "Similar agents/workflows already exist. Would you like to use one of these instead, or proceed to create a new one?"

- Warn about duplicate name risks: similar agents can cause the AI to confuse which agent to invoke.

### Phase 2: Interview

Before creating ANY new agent or workflow, gather the following. No question may be silently skipped.

- 
[STOP] Q1 — Authentication: "Which type of user should this run as: (1) Dynamic User OR (2) AI User?"

- AI User: Query `sys_user` (encodedQuery: `identity_type=ai_agent`) to find available AI Users. Present the list and ask which one. Set `runAsUser` (Agent) or `runAs` (Workflow). Skip Q2, proceed to Q3.

- Dynamic User: Continue to Q2.

- For workflows: After workflow-level auth, ask about each agent individually: "Should each agent use the same auth mode, or do any need different access?"

- 
[STOP] Q2 — Security Roles (Dynamic User only):

- Query `sys_db_object` (encodedQuery: `name=sys_agent_access_role_mapping`) to detect `roleMap` support. Table exists → use `dataAccess.roleMap` with role names. Table missing → use `dataAccess.roleList` with role sys_ids (resolve via `sys_user_role`).

- Auto-discover roles: for each target table, query `sys_security_acl_role` (encodedQuery: `sys_security_acl.nameLIKE<table_name>`).

- Present findings: "These roles are necessary for agent functionality: [roles]. Do you want to add any others?" Wait for response.

- Never use `Now.ID` for roles — always query `sys_user_role` for actual sys_ids. Mismatched `Now.ID` causes silent runtime failures.

- The `maint` role is NOT allowed; reject and ask for a different role. Warn (but allow) if user specifies `security_admin` — it grants broad privileges.

- 
[STOP] Q3 — Trigger configuration: "When should this be triggered? (1) None/manual (2) Record create/update (3) Scheduled (4) Email"

- Trigger condition is MANDATORY for all trigger types. Ask: "Which records should trigger this? Describe the filter conditions." Convert to an encoded query. Validate column names via `sys_dictionary` before writing the condition.

- Scheduled triggers: Ask frequency (daily/weekly/monthly), then schedule details (time, day of week/month).

- Trigger run-as is MANDATORY: For record-based triggers, query `sys_dictionary` (encodedQuery: `name=<table>^internal_type=reference^reference=sys_user`) to find user columns. Present labels and ask: "Which user should this trigger execute as?" For scheduled/email triggers, ask for a username or sys_id.

- 
[STOP] Q4 — ACL Access: Present security implications, then ask: "Who should be able to ACCESS this? (1) Any authenticated user (2) Specific roles (3) Public"

- Authenticated: Use `securityAttribute: "user_is_authenticated"` on the ACL with no roles. Do NOT assign `user` or `snc_internal`.

- Specific roles: MUST follow up with "Which roles should have access?" and wait for response. Use `roles: [...]` on the ACL.

- Public: Use a `condition` on the ACL with no roles or securityAttribute.

### Phase 3: Design & Build

[STOP] Gate — verify before proceeding: Before doing anything below, check: have Q1, Q2 (if applicable), Q3, and Q4 each been either explicitly answered by the user or explicitly confirmed via the Shortcut's one-pass inference message? If any answer is still missing, inferred, or defaulted, STOP now and go back to ask it — do NOT write, generate, or describe any `.now.ts` code first. Writing code before this gate passes is the single most common failure mode; check it explicitly every time, even for requests that sound simple.

- Determine type: Single AI Agent or AI Agentic Workflow — use the decision tree in When to Use Workflows vs Single Agent below.

- Tool discovery & validation — MANDATORY FETCH: Before writing ANY tool code (CRUD, script, RAG, or reference-based), you MUST call `explain_fluent_doc` on `building-ai-agents-tools-guide` and follow it — do NOT rely on this summary guide alone, and do NOT write tool `inputs`/`queryCondition`/`returnFields` from memory. That topic contains the required-fields rules, `mappedToColumn` self-check, and RAG dedup gate — skipping it is a common source of silently-broken tools (e.g. missing `returnFields`, missing `mappedToColumn`). Query the instance for existing subflows, actions, and script includes before creating a new tool. Follow tool selection priority: OOB → reference-based → CRUD → Script.

- Execution mode: Decide `executionMode` based on the use case. Prefer `"copilot"` when the agent creates, updates, or deletes records. Use `"autopilot"` for read-only or fully autonomous workflows. Do not ask the user.

- Write the code — MANDATORY FETCH first: Before creating the `.now.ts` file, you MUST call `explain_fluent_doc` on `building-ai-agents-advanced-guide` and follow its "Required Fields", "Valid Enums", and "Avoidance (Anti-Patterns)" sections — do NOT write mandatory fields, enum values, or `securityAcl`/`dataAccess` shapes from memory. Include `processingMessage` and `postProcessingMessage` on every agent, and `preMessage`/`postMessage` on every tool.

- Build and deploy: Run `now-sdk build && now-sdk install`. This assumes SDK authentication and project setup are already complete — see the `developing-apps-guide` topic for that procedure. If that topic is unavailable and setup has not been done, STOP and tell the user setup is required first — do NOT guess CLI flags, credentials, or environment configuration.

- Provide Deployment Summary with Agent Links (MANDATORY): After deploy, you MUST query for the instance URL and deployed agent/workflow sys_ids, then provide the complete summary with actual clickable Agent Studio URLs — never show placeholders. Do NOT mark the task complete without providing the summary. The summary must include: agent/workflow name, security ACL type, 2-4 sample test prompts, next steps, and all applicable Agent Studio links (Agent Setup, Playground, Agents List; plus Workflow Setup, Workflow Playground, Workflows List if a workflow was created). You MUST call `explain_fluent_doc` on `building-ai-agents-advanced-guide` for the full query workflow, URL patterns, and summary template — do NOT invent URL patterns from memory.

## Prerequisites

Verify that the required subscription and license are available on the instance. This checks whether AppEngine or AI Platform Prime is active — a simple plugin table query cannot validate this.

Create a check script in your project:

```
// scripts/check-product.ts
import { Connector } from '@servicenow/sdk-api'

export default async ({ credential }) => {
    const connector = new Connector(credential)
    const response = await connector.fetch(
        '/api/sn_build_agent/build_agent_api/isProductAvailable',
        { method: 'GET' },
        new URLSearchParams({ productId: 'primeSKU', scopeName: '' })
    )
    const body = await response.json()
    const available = body.result?.isAvailable === true
    console.log(JSON.stringify({ available }))
    if (!available) {
        console.error('ServiceNow Otto for App Engine is not available on this instance.')
    }
}
```

```
now-sdk run check-product
```

If the product is not available, STOP here — do not continue with agent/workflow creation. Inform the user that ServiceNow Otto for App Engine (or AI Platform Prime) is not available on this instance and that their ServiceNow administrator must enable the subscription before proceeding.

Also check for existing agents with similar names:

```
now-sdk query sn_aia_agent -q 'nameLIKE<agent_name>' -f 'sys_id,name,description' -o json
now-sdk query sn_aia_usecase -q 'nameLIKE<workflow_name>' -f 'sys_id,name,description' -o json
```

Warning: Creating an agent with a name similar to an existing one can cause confusion in the ServiceNow Otto Panel and may lead to incorrect agent selection at runtime.

## Workflow vs Single Agent Decision Tree

```
User Request
    |
Does it involve multiple tasks? (AND, THEN, followed by)
    | NO  -> USE SINGLE AI AGENT
    | YES
        |
    Do the tasks require DIFFERENT capability types?
    (e.g., search + summarize, fetch from table A + update table B)
        | NO  -> USE SINGLE AI AGENT (multiple tools, one agent)
        | YES -> USE AI AGENTIC WORKFLOW
```

Pattern Recognition:

| User Says | Type | Why |
| "Fetch X AND do Y" (different capabilities) | Workflow | Different capability types working together |
| "Get data THEN process it" (different agents) | Workflow | Sequential operations needing different specializations |
| "Look up and update an incident" | Single Agent | Same table, same capability type (CRUD), multiple tools |
| "Search for incidents by priority" | Single Agent | Single task |

Key distinction: Multiple tools on the same table or same capability type = single agent with multiple tools. Multiple capability types requiring different specializations = workflow with multiple agents.

## AI Agent vs AI Agentic Workflow

| Feature | AI Agent | AI Agentic Workflow |
| Purpose | Single agent performing tasks | Multiple agents working as a team |
| Import | `AiAgent` from `@servicenow/sdk/core` | `AiAgenticWorkflow` from `@servicenow/sdk/core` |
| Configuration | `tools` array | `team: { $id, name, members: [...] }` |
| Version array | `versionDetails` | `versions` |
| Record identity | `$id` (explicit ID) | `$id` (explicit ID) |
| Security | `securityAcl` (mandatory, auto-generates ACL) | `securityAcl` (mandatory, auto-generates ACL) |
| Run-as user | `runAsUser` | `runAs` |
| Execution mode | `executionMode` on tools | `executionMode` at workflow level (default: `'copilot'` ) |
| Trigger channel | `'nap'` / `'nap_and_va'` (agent-level `channel` ) | `"Now Assist Panel"` (trigger-level, mandatory) |
| Processing messages | `processingMessage` , `postProcessingMessage` | Not available |
| Protection policy | `protectionPolicy` (optional) | `protectionPolicy` (optional) |

## Protection Policy

Both `AiAgent` and `AiAgenticWorkflow` support `protectionPolicy` (inherited from `Now.Internal.WithIdAndMetadata`). This sets the `sys_metadata` protection policy on the generated record, controlling whether other developers can edit the record after the application is installed.

| Value | Effect |
| `'read'` | Others can see the configuration but cannot change it |
| `'protected'` | Others cannot change this record |
| (omitted) | Others can fully customize this record |

You can also use `$override` to set properties not directly supported by the API:

```
AiAgent({
  $id: Now.ID['my_agent'],
  name: 'My Agent',
  protectionPolicy: 'read',
  $override: { custom_field: 'value' },
  // ...
})
```

## Security ACL (`securityAcl`)

`securityAcl` is mandatory on both `AiAgent` and `AiAgenticWorkflow`. It controls who can invoke the agent/workflow and auto-generates the `sys_security_acl` and `sys_security_acl_role` records. It is a discriminated union on the `type` field — each variant also requires a `$id` to identify the generated ACL record.

### Access Types

| `type` | Who can invoke | Extra fields |
| `'Any authenticated user'` | Any logged-in user | None |
| `'Specific role'` | Only users with listed roles | `roles: [...]` (required) |
| `'Public'` | Anyone, no auth required | None |

```
// Any authenticated user
securityAcl: {
    $id: Now.ID['my_agent_acl'],
    type: 'Any authenticated user',
}

// Specific roles only
securityAcl: {
    $id: Now.ID['my_agent_acl'],
    type: 'Specific role',
    roles: [
        '282bf1fac6112285017366cb5f867469',  // itil role sys_id
        'b05926fa0a0a0aa7000130023e0bde98',  // user role sys_id
    ]
}
```

Important distinction: `securityAcl` controls who can invoke the agent. `runAsUser` (agent) / `runAs` (workflow) and `dataAccess` are separate — they control which user identity the agent runs under when executing.

### Execution Identity (`runAsUser` / `dataAccess`)

Set either `runAsUser` (agent) or `dataAccess` — not both:

- `runAsUser` — agent always runs as the specified sys_user sys_id regardless of invoker

- `dataAccess.roleMap` (role names) or `dataAccess.roleList` (role sys_ids) — agent runs as the invoking user, restricted to the listed roles. Required when `runAsUser` is not set. For workflows, use `dataAccess` when `runAs` is not set.

For detailed authentication modes (System-Privilege vs Caller-Privilege, custom table ACLs, AI User discovery), see the `building-ai-agents-advanced-guide` topic.

### Role Discovery

- Identify target tables from the agent's CRUD tools

- Query `sys_security_acl_role` for each table (encodedQuery: `sys_security_acl.nameLIKE<table_name>`)

- Add discovered role names to `dataAccess.roleMap`, or role sys_ids to `dataAccess.roleList` and `securityAcl.roles`

### Common Role sys_ids

| Role | sys_id |
| admin | `2831a114c611228501d4ea6c309d626d` |
| itil | `282bf1fac6112285017366cb5f867469` |
| user | `b05926fa0a0a0aa7000130023e0bde98` |

## Tool Configuration

For complete tool documentation, see the `building-ai-agents-tools-guide` topic. Quick reference:

| Tool Type | Use When |
| CRUD | Create, read, update, or delete records on a table |
| Script | Custom logic via GlideRecordSecure, calculations, aggregations |
| OOB | Pre-built tools (Web Search, Knowledge Graph, RAG, ITSM tools) |
| Reference-Based | Reusing existing Subflows, Flow Actions, Catalog Items |
| RAG | Semantic search across configured AI Search profiles |

### Execution Mode

| Mode | Use When | Behavior |
| `'autopilot'` | Read-only operations (lookup, search) | Tool runs automatically |
| `'copilot'` | Write operations (create, update, delete) | User confirmation required |

## Trigger Configuration

Triggers are optional. Agents/workflows can operate without them via ServiceNow Otto Panel.

### Trigger Types

| Type | Description |
| `record_create` | On new record creation |
| `record_update` | On record update |
| `record_create_or_update` | On both |
| `email` | On email receipt |
| `scheduled` | On a repeating interval |
| `daily` / `weekly` / `monthly` | Scheduled at specific times |
| `ui_action` (workflows only) | From a UI action button |

### Key Differences: Agent vs Workflow Triggers

| Property | Agent trigger | Workflow trigger |
| `channel` | `"nap"` or `"nap_and_va"` (falls back to `""` if omitted — always set explicitly) | `"Now Assist Panel"` (mandatory) |
| `triggerCondition` | Optional (recommended) | Mandatory for record-based |
| `objectiveTemplate` | Required (falls back to `""` if omitted — always set explicitly) | Required |

Note: For agent triggers, `triggerCondition` is optional but strongly recommended. For workflow record-based triggers, it is mandatory — the plugin rejects if missing.

### Scheduled Trigger Fields

The `schedule` object is used when `triggerFlowDefinitionType` is `'scheduled'`, `'daily'`, `'weekly'`, or `'monthly'`.

| Type | Required Fields (inside `schedule` object) |
| `daily` | `schedule.time` |
| `weekly` | `schedule.runDayOfWeek` (1=Sun to 7=Sat), `schedule.time` |
| `monthly` | `schedule.runDayOfMonth` (1-31), `schedule.time` |
| `scheduled` | `schedule.repeatInterval` (e.g., `'1970-01-05 12:00:00'` = every 5 days) |

Time format: `"1970-01-01 HH:MM:SS"`.

The `schedule.triggerStrategy` field controls repeat behavior. Values differ by entity type:

| Entity | Valid `triggerStrategy` values |
| AI Agent | `'every'` , `'once'` , `'unique_changes'` , `'always'` |
| AI Agentic Workflow | `'every'` , `'immediate'` , `'manual'` , `'once'` , `'repeat_every'` , `'unique_changes'` |

### Email Trigger Required Fields

| Field | Required? | Description |
| `targetTable` | Yes | The table where email records are processed |
| `triggerCondition` | Yes | Filter condition for selective email processing |

### Run-As Configuration

Configuring who the trigger executes as is mandatory for all trigger types.

For record-based triggers — discover user-reference columns first:

- Query `sys_dictionary` with: `now-sdk query sys_dictionary -q 'name=<targetTable>^internal_type=reference^reference=sys_user' -f 'column_label,element' -o json`

- Present the discovered columns to the user and ask which user the trigger should run as

- If the user picks a column → set `runAs: "<column_name>"` (do NOT generate `runAsScript`)

- If the user picks "Other user" or for scheduled/email triggers → generate `runAsScript`

Option A — Column-based (`runAs`):

```
{
  runAs: "assigned_to",   // column name, not label
}
```

Option B — Script-based (`runAsScript`):

Resolve the user sys_id first: `now-sdk query sys_user -q 'user_name=<username>' -f 'sys_id,user_name' -o json`

```
{
  runAsScript: `/**
 * Script to be evaluated at runtime when the trigger is executed.
 * @param {GlideRecord} current - Target record that executed this trigger.
 * @returns {string}
 */
(function(current) {
  var result = "<resolved_sys_id>"; // sys_id of the user
  return result;
})(current);`,
}
```

Option C — Fixed user (`runAsUser`):

```
{
  runAsUser: "6816f79cc0a8016401c5a33be04be441",  // specific user sys_id
}
```

Priority: If both `runAs` and `runAsScript` would apply, prefer `runAs` (simpler). Only use `runAsScript` when a specific user is needed that cannot be derived from a record column.

### Trigger Defaults

Agent triggers substitute `""` for `channel` and `objectiveTemplate` if omitted at deploy time — this is a plugin fallback, not a recommended value; always set both explicitly (see Key Differences above for the valid `channel` values). Individually, `runAsScript`, `runAs`, and `runAsUser` are each optional — but at least one of them must be set, since configuring who the trigger executes as is mandatory (see Run-As Configuration above).

### Safety Considerations

- Triggers are deployed inactive — users must manually activate triggers in ServiceNow after testing

- Test thoroughly before activating triggers

- Monitor first executions after activation

- Document trigger conditions for maintainability

- Security Testing: Verify ACLs and role masks are properly configured before activating triggers — query `sys_security_acl` (encodedQuery: `nameLIKE<agent_or_workflow_name>`) to confirm the generated ACL record and roles match what was configured

- Audit Trail: Ensure `runAsScript` returns the appropriate user for audit purposes — verify the resolved sys_id came from a live `sys_user` query (see Run-As Configuration above), never a hardcoded placeholder

### Trigger Activation Workflow

- Create workflow/agent with triggers

- Deploy to ServiceNow instance (`now-sdk build && now-sdk install`)

- Test thoroughly in development/test environment

- Manually activate trigger in ServiceNow after validation

- Monitor first few executions

## ACL Deployment

Both AI Agents and AI Agentic Workflows use `securityAcl`. The plugin automatically generates `sys_security_acl` and `sys_security_acl_role` records — no manual two-step deployment is needed.

The generated ACL name follows the format: `{domain}.{scope}.{name}`

```
// Works the same for both AiAgent and AiAgenticWorkflow
securityAcl: {
    $id: Now.ID['my_agent_acl'],
    type: 'Specific role',
    roles: [
        '282bf1fac6112285017366cb5f867469',  // itil
        'b05926fa0a0a0aa7000130023e0bde98'   // user
    ]
}
```

## Workflow Configuration

### Team Structure

Workflows use `$id` for record identity (just like agents). The `team` object also requires its own `$id`.

```
team: {
    $id: Now.ID["workflow_team"],  // MANDATORY on team
    name: "Workflow Team",
    // description is auto-populated from workflow.description — do not set it
    members: [
        "62826bf03710200044e0bfc8bcbe5df1"  // Agent sys_id from sn_aia_agent table
    ]
}
```

Team members can also be specified using the `Record` API (recommended for portability across instances):

```
import { AiAgenticWorkflow, Record } from '@servicenow/sdk/core'

const lookupAgent = Record({ table: 'sn_aia_agent', $id: Now.ID['lookup_agent'], data: { name: 'Lookup Agent' } })
const analysisAgent = Record({ table: 'sn_aia_agent', $id: Now.ID['analysis_agent'], data: { name: 'Analysis Agent' } })

AiAgenticWorkflow({
    // ...
    team: {
        $id: Now.ID['my_team'],
        name: 'My Team',
        members: [lookupAgent, analysisAgent],
    },
})
```

Agents must be deployed before creating workflows.

Common mistake: Do NOT use `Now.ID["my_agent"]` for cross-file agent references in `members`. You must use the actual sys_id from the deployed agent record.

### Workflow-Level Fields

| Field | Type | Default | Notes |
| `executionMode` | `'copilot' | 'autopilot'` | `'copilot'` | Execution mode for the workflow |
| `memoryScope` | `string` | `'global'` | Memory scope for team members |
| `active` | `boolean` | `true` | Omit if active (default) |
| `sysDomain` | `string` | `'global'` | Omit if global (default) |

Only specify fields that differ from their defaults — the plugin suppresses default values in the transform output.

### Deployment Order

- Create and deploy AI Agents (with `securityAcl`)

- Retrieve the agent sys_ids by querying `sn_aia_agent` (see the `query-guide` topic)

- Create and deploy workflow with `securityAcl` and agent sys_ids

- Query `sn_aia_usecase` to verify the workflow was created

### contextProcessingScript

Supports inline scripts or `Now.include()` for external files. The function receives four parameters:

| Parameter | Description |
| `task` | The task record that triggered the workflow |
| `user_utterance` | The user's input message |
| `workflow_id` | The sys_id of the current workflow |
| `context` | Additional context (pageContext, triggerContext) |

```
(function(task, user_utterance, workflow_id, context) {
    return {
        pageContext: context?.pageContext,
        triggerContext: context?.triggerContext
    };
})(task, user_utterance, workflow_id, context);
```

```
// Preferred: external file
contextProcessingScript: Now.include('./context-processing-script.js')
```

## Complete AI Agent Example

```
import { AiAgent } from "@servicenow/sdk/core";

export const incidentHelperAgent = AiAgent({
    $id: Now.ID["incident_helper_agent"],
    name: "Incident Helper Agent",
    description: "Retrieves incident details and searches for resolution guidance.",
    agentRole: "You are an ITSM incident specialist.",

    // Security — auto-generates ACL records
    securityAcl: {
        $id: Now.ID['incident_helper_agent_acl'],
        type: 'Specific role',
        roles: [
            '282bf1fac6112285017366cb5f867469',  // itil
            'b05926fa0a0a0aa7000130023e0bde98'   // user
        ]
    },

    agentDescriptor: 'created_by_build_agent',
    channel: 'nap_and_va',
    recordType: 'custom',
    processingMessage: "Analyzing your incident request...",
    postProcessingMessage: "Incident analysis complete.",

    versionDetails: [{
        name: "V1",
        number: 1,
        state: "published",
        instructions: `Step 1: Extract the incident number from the user's request.
Step 2: Use the Lookup Incident tool to fetch details.
Step 3: Present details in bullet-point format.
Step 4: Use AIA Web Search for resolution guidance.
Step 5: Recommend next steps. NEVER modify without user approval.`
    }],

    tools: [
        {
            active: true,
            name: "Lookup Incident",
            description: "Searches for incidents by number",
            executionMode: "autopilot",
            type: "crud",
            recordType: "custom",
            preMessage: "Searching for the incident...",
            postMessage: "Incident details retrieved.",
            inputs: {
                operationName: "lookup",
                table: "incident",
                inputFields: [
                    { name: "incident_number", description: "Incident number", mandatory: false }
                ],
                queryCondition: "number={{incident_number}}",
                returnFields: [
                    { name: "number" },
                    { name: "short_description" },
                    { name: "state" },
                    { name: "priority" },
                    { name: "assigned_to", referenceConfig: { table: "sys_user", field: "name" } }
                ]
            }
        },
        {
            type: "web_automation",
            name: "AIA Web Search",
            active: true,
            preMessage: "Searching the web...",
            postMessage: "Web search results retrieved."
        }
    ],

    triggerConfig: []
});
```

## Complete Workflow Example

```
import { AiAgenticWorkflow } from "@servicenow/sdk/core";

export const incidentAnalysisWorkflow = AiAgenticWorkflow({
    $id: Now.ID["incident_analysis_workflow"],
    name: "Incident Analysis Workflow",
    description: "Orchestrates two agents to retrieve and analyze incidents.",
    recordType: "custom",

    // Security — auto-generates ACL records (mandatory)
    securityAcl: {
        $id: Now.ID['incident_analysis_workflow_acl'],
        type: 'Specific role',
        roles: [
            '282bf1fac6112285017366cb5f867469',  // itil
            'b05926fa0a0a0aa7000130023e0bde98'   // user
        ]
    },

    // dataAccess required when runAs is omitted (dynamic user identity)
    // Use roleMap (role names) or roleList (role sys_ids)
    dataAccess: {
        roleMap: ['itil', 'user']
    },

    team: {
        $id: Now.ID["incident_analysis_team"],
        name: "Incident Analysis Team",
        // description is auto-populated from workflow description
        members: [
            "62826bf03710200044e0bfc8bcbe5df1",
            "274b465a7d5f42e581664209557b2b18"
        ]
    },

    versions: [{
        name: "V1",
        number: 1,
        state: "published",
        instructions: `Step 1: Use the Incident Lookup Agent to fetch details.
Step 2: Use the Analysis Agent to examine patterns.
Step 3: Present findings. NEVER modify without user approval.`
    }],

    triggerConfig: [{
        name: "high_priority_incident",
        channel: "Now Assist Panel",
        targetTable: "incident",
        triggerFlowDefinitionType: "record_create",
        triggerCondition: "priority<=2",
        objectiveTemplate: "Analyze high priority incident ${number}",
        runAsScript: `(function(current) {
            return current.assigned_to || "6816f79cc0a8016401c5a33be04be441";
        })(current);`
    }]
});
```

## Related

- See the `building-ai-agents-tools-guide` topic for tool selection, CRUD/script/OOB/RAG tools, execution mode, and tool composition

- See the `building-ai-agents-advanced-guide` topic for instructions authoring, authentication procedures, validation, error recovery, and deployment checklists

- See the `aiagent-api` topic for AI Agent API reference

- See the `aiagenticworkflow-api` topic for AI Agentic Workflow API reference

- See the `developing-apps-guide` topic for project setup, authentication, and build workflow

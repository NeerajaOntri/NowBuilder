Version: 4.14.0

# Building AI Agents — Advanced Guide

Advanced patterns for AI Agent and Agentic Workflow development: instructions authoring, authentication and ACL configuration, validation rules, error recovery, deployment procedures, and anti-patterns to avoid.

## Instructions Authoring

### Three Key Fields

Each field has a distinct purpose — do not duplicate content across them.

| Field | Purpose | Answers |
| `description` | Scope — what it DOES | "What problem does this agent solve?" |
| `agentRole` | Identity — what it IS (agents only) | "Who am I?" |
| `instructions` | Behavior — what it SHOULD DO | "How should I act and use my tools?" |

### Writing Principles

- Clarity: Use specific action verbs (`Fetch`, `Retrieve`, `Filter`, `Analyze`, `Update`). Add explicit conditions: `"If priority = High, then escalate immediately"`

- Actionable steps: Every step MUST bind to a tool action, agent delegation, or concrete output. Avoid vague verbs without tool binding: `"Understand the request"` — prefer `"Use [Tool Name] to retrieve X"`

- Explicit tool references: Name tools explicitly in instructions. Update instructions whenever a tool is renamed

- Contingencies: Handle failures with gates: `"DO NOT PROCEED if details are missing"`

- Coherence: Each step builds on the previous step's results. Use consistent terminology throughout

- Trigger context: Use "from the task" or "from the context" — NOT "from the triggering record"

- Output format is mandatory: Tools return raw data (JSON, integer codes, sys_ids). Every instructions block MUST include a presentation step telling the agent how to format results in plain English

- Never mention underlying tables or column names in instructions — instructions are user-facing. Reference data by business meaning (e.g., "the incident's priority") not by column name (e.g., `priority` on `incident`)

### Discovery Before Writing

Before writing instructions for an agent, discover the target table's columns and types so instructions reference valid fields:

```
now-sdk query sys_dictionary -q 'name=incident' -f 'element,internal_type,column_label' -o json
```

Use the query results to ensure instructions reference real fields and use correct display labels in the presentation step.

### Output Format Guidance

Tools return raw data — JSON objects, integer choice codes (e.g., `state: 1`), and reference sys_ids. The agent surfaces this verbatim unless instructions explicitly tell it to reformat.

Every instructions block that returns data to the user MUST include a presentation step:

```
Step N: Present Results.
- Format the results in plain English as a bulleted list.
- Use readable labels instead of field names (e.g., "Priority" not "priority").
- Replace numeric state/priority codes with their labels (e.g., state 1 = Open, state 6 = Resolved).
- Do NOT display sys_ids, internal field names, or raw JSON to the user.
```

For reference fields, include `referenceConfig` on `returnFields` entries so the tool resolves display values.

| Output type | Minimum instruction required |
| Single record, few fields | `"Present the details in plain English."` |
| Multiple records | `"List each record with a numbered heading and its key fields as sub-bullets."` |
| Records with numeric choice codes | `"Replace state/priority codes with their text labels before presenting."` |
| Records with reference fields | `"Use the display name from reference fields, not the sys_id."` |

### Tool Description Guidance

Write descriptions under two sentences. Include the tool's exact `name` so the agent can match it. Specify inputs, outputs, and scope.

| Quality | Description | Problem |
| Bad | `"Looks up incidents"` | Too vague — agent won't know when to pick this tool over another |
| Good | `"Searches for incidents by number, priority, or assignment group. Returns number, short description, state, priority, and assigned_to."` | Specifies inputs, outputs, and scope |
| Bad | `"Updates stuff"` | No indication of what it updates or when to use it |
| Good | `"Updates an existing incident's state, priority, or assignment group. Requires the incident number to identify the target record."` | Clear target, fields, and precondition |

### Trigger-Initiated Instructions

When an agent or workflow has a trigger, the triggering record's data is available through `task` and `context` — NOT by querying the triggering table directly.

WRONG — agent cannot process "triggering record":

```
Step 1: Gather data from the triggering record.
```

CORRECT — reference task/context:

```
Step 1: Extract Incident Details.
- Extract the incident number, priority, and short description from the task.
- Use the context to identify the assignment group and category.
```

Rules:

- Use "from the task" or "from the context" to reference incoming trigger data

- The first step should extract/parse needed fields from `task`/`context`, not fetch them from a table

- Subsequent steps CAN use tools to fetch additional data not already in the trigger context

- For workflows, use `contextProcessingScript` to shape trigger data before agents use it

### Agent-to-Agent Data Flow (Workflows)

Agents in a workflow share data through the orchestration context. Instructions must explicitly state what data to pass between steps:

- State what to retrieve: `"Use [Agent A] to retrieve the incident's number, priority, state, and assigned_to."`

- Reference previous results: `"Using the incident details from Step 1, use [Agent B] to search for similar resolved incidents."`

- Handle missing data: `"If [Agent A] returns no results, skip [Agent B] and proceed directly to Step N."`

- Aggregate across agents: `"Combine the incident details from Step 1 with the resolution suggestions from Step 2 and present a unified summary."`

Workflow instructions reference agents by name instead of tools. The orchestrator routes each step to the named agent. Define starting conditions, decision points, and end states.

### CRUD Lookup in Instructions

When instructions describe a search/lookup operation, guide the agent to use keyword extraction and the `LIKE` operator for text fields:

```
Step 1: Search for Matching Records.
- Extract 1-2 keywords from the user's request. Do NOT pass full sentences to the search tool.
- Use the LIKE operator for text field searches.
- Prefer the record number as the primary filter, with sys_id as an OR fallback
  (e.g., number={{id}}^ORsys_id={{id}}).
```

### Scaling by Complexity

| Complexity | Tools/Agents | Instructions Length |
| Simple | 1-2 tools | 5-10 lines |
| Moderate | 3-4 tools | 10-20 lines |
| Complex | 5+ tools | 20-30 lines |
| Workflow | 2-10 agents | 15-30 lines |

If instructions exceed ~30 lines, split into multiple agents orchestrated by a workflow.

### Tool Input Echoing Rule

For CRUD tools, instructions must explicitly list the tool's input field names so the agent knows what data to collect from the user. Example: "Step 2: Ask the user for the incident number and priority. Step 3: Use the Lookup Incident tool with the incident_number provided."

### Self-Review Checklist

Before finalizing instructions, verify:

- Every step references a specific tool or agent by its exact `name`

- An output format / presentation step is included

- Contingencies cover tool failures and missing data

- No step uses "from the triggering record" — use "from the task" / "from the context"

- No raw table names or column names appear in user-facing instruction text

- All referenced tool names match the actual `name` property (not renamed or mistyped)

- Instructions stay within the complexity-appropriate line count

## Authentication and ACL Configuration

### System-Privilege vs Caller-Privilege

| Aspect | Caller-Privilege (Dynamic User) | System-Privilege (AI User) |
| Run-as value | Agent: `runAsUser: ""` . Workflow: `runAs: ""` | `runAsUser` / `runAs` : AI User sys_id |
| Data access | Based on logged-in user's roles (filtered by role mask) | Same for all users — uses service account |
| `dataAccess` required? | Yes — `roleMap` (names) or `roleList` (sys_ids) | No |
| Audit trail | Shows actual user | Shows service account |
| Role requirement | Roles in `dataAccess` filter the caller's roles | AI User must hold required roles |
| Best for | Variable permissions, user-level audit | Consistent access, service operations |

### runAs Discovery (AI User Records)

The `runAs` / `runAsUser` value ALWAYS comes from an AI User record — a `sys_user` record where `identity_type=ai_agent`:

```
now-sdk query sys_user -q 'identity_type=ai_agent' -f 'sys_id,name,user_name' -o json
```

For Caller-Privilege mode, the AI User must hold the `itil` role (or the minimum roles needed for the agent's operations).

### Custom Table ACL Procedure

When an agent's CRUD tools target a table that doesn't have ACLs, table-level ACLs must be created. This is separate from the agent execution ACL (`securityAcl` on the agent/workflow record).

Two separate ACL concerns:

| ACL Type | Purpose | Created When |
| Table data ACLs (read/write/create/delete) | Controls who can access the table's data | Before or alongside agent creation |
| Agent execution ACL ( `securityAcl` ) | Controls who can invoke the agent itself | Inline on the agent/workflow — plugin auto-generates |

### CRUD-to-ACL Operation Mapping

| Agent CRUD Operation | Table ACL Operation |
| `lookup` | `read` |
| `create` | `create` |
| `update` | `write` |
| `delete` | `delete` |

Only create ACLs for operations the agent actually uses.

Automated procedure for custom tables:

- Create a custom role for the table (e.g., `x_snc_myapp.table_user`)

- Assign the role to the AI User (if System-Privilege) or add to `dataAccess` (if Caller-Privilege)

- Create table ACLs — one per CRUD operation the agent needs, each requiring the custom role

- Deploy the role and ACLs first — build and install before creating the agent

- Feed the role into agent config:

- `roleMap`: use role name directly — plugin resolves at build time

- `roleList`: query `sys_user_role` for the actual sys_id after deployment. Do NOT use `Now.ID`

After deployment, verify the plugin generated the ACL record:

```
now-sdk query sys_security_acl -q 'nameLIKE<agent_name>' -f 'sys_id,name,operation' -o json
```

## Agent Decomposition for Workflows

When building a workflow, decompose the request into individual agents. Each agent should have a single clear responsibility.

### Decomposition Patterns

| Pattern | When to Use | Example |
| By capability | Agents need different tool types | Lookup Agent (CRUD) + Analysis Agent (Script) + Search Agent (OOB) |
| By table/domain | Work spans multiple tables | Incident Agent + Change Agent + Problem Agent |
| By workflow phase | Clear sequential phases | Gather Agent → Process Agent → Act Agent |

### Rules of Thumb

- One capability per agent — if an agent needs tools that serve fundamentally different purposes, split into separate agents

- Split at >5 tools — an agent with more than 5 tools becomes unfocused

- Each agent gets a clear name — `"Incident Lookup Agent"`, not `"Helper Agent"`

- Non-overlapping responsibilities — no two agents should answer the same question

- Match agent count to complexity — 2-3 agents for most workflows; 4+ only for genuinely complex multi-phase processes

### contextProcessingScript

For workflows with triggers, `contextProcessingScript` processes trigger data before agents use it. Function parameters: `task`, `user_utterance`, `workflow_id`, `context`. The returned object becomes the starting context available to agents during execution.

Important: Agents in `team.members` MUST use deployed sys_ids — never use `Now.ID` references for agents defined in separate files. The plugin requires valid sys_ids from the `sn_aia_agent` table.

## Memory Categories

AI Agents can access long-term memory categories. Set `memoryCategories` to an array of category strings. Only include categories relevant to the agent's purpose — omit the property entirely if the agent doesn't need long-term memory.

| Category | Description |
| `"device_and_software"` | Devices and software used by the user |
| `"meetings_and_events"` | Meetings, events, and calendar items |
| `"projects"` | Projects and initiatives |
| `"workplace"` | Workplace and organizational information |

## Version Management

### State Transitions

Version states progress: `draft` → `committed` → `published`. Only one version can be `state: "published"` at a time. For workflows, the published version's `instructions` are automatically written to `base_plan`.

### Version Operations

| Scenario | Action |
| New agent (first creation) | Create one version with `state: "published"` — this becomes the active version |
| Update instructions on existing agent | Modify the `instructions` in the existing published version — plugin updates in place |
| Rollback needed | Set current version to `state: "withdrawn"` , set previous version to `state: "published"` |

### agentDescriptor Rule

`agentDescriptor` on `AiAgent()` records the agent's creator on `sn_aia_agent_config.agent_descriptor`.

- Create (no existing `sn_aia_agent` record with the same name): set `agentDescriptor: 'created_by_build_agent'`

- Edit (existing agent record): OMIT `agentDescriptor` — overwriting destroys the original creator stamp

## Editing Existing Agents/Workflows

### Auto-Computed Fields

The following fields are auto-generated by the plugin and should not be specified in `.now.ts`:

`internalName`, top-level `instructions`, `base_plan`, `inputSchema`, `targetDocumentTable`, `targetDocument`, CRUD `script`, `team.description`

Trigger `usecase` is NOT in this list — it's user-settable (see "AI Agentic Workflow–Specific" notes below for its default/override behavior).

### Safe Edit Workflow

- Locate the `.now.ts` file

- Read the entire current configuration

- Identify scope of changes (see Change Impact Matrix)

- Apply only the requested changes

- Redeploy and query to verify

### Change Impact Matrix

| Change | Also Update |
| Add CRUD tool | Verify columns, update instructions, check executionMode |
| Remove tool | Remove instruction references, check dependencies |
| Change auth mode | Update `securityAcl.type` , add/remove `roles` as needed |
| Add trigger | Add to `triggerConfig` , verify target table |
| Add team member (workflow) | Deploy agent first, get sys_id, update instructions |
| Update instructions | Ensure all referenced tool/agent names still exist |

## Validation and Enums

### Required Fields

| Entity | Mandatory Fields |
| AI Agent | `$id` , `name` , `description` , `agentRole` , `securityAcl` |
| AI Agentic Workflow | `$id` , `name` , `description` , `securityAcl` , `team.$id` |
| CRUD tool | `name` , `type` , `inputs.operationName` , `inputs.table` , `inputs.inputFields` ( `lookup` operations additionally require `inputs.returnFields` ) |
| Script tool | `name` , `type` , `script` |

### Trigger Validation

| Rule | Description |
| T4 | Workflow record-based triggers require `triggerCondition` — the plugin rejects the trigger if missing. For agents, `triggerCondition` is optional but recommended |
| T6 | Agent triggers: `channel` and `objectiveTemplate` default to `""` if omitted |

### Valid Enums

| Property | Valid Values |
| `recordType` (agent) | `"custom"` , `"template"` , `"aia_internal"` , `"promoted"` (default: `"template"` ) |
| `recordType` (workflow) | `"custom"` , `"template"` , `"aia_internal"` (default: `"template"` ) |
| `executionMode` (tool) | `"autopilot"` , `"copilot"` |
| `executionMode` (workflow) | `"autopilot"` , `"copilot"` (default: `"copilot"` ) |
| `state` (version) | `"draft"` , `"committed"` , `"published"` , `"withdrawn"` (default varies by entity — see Plugin Defaults below) |
| `tool.type` | `"script"` , `"crud"` , `"capability"` , `"subflow"` , `"action"` , `"catalog"` , `"topic"` , `"topic_block"` , `"web_automation"` , `"rag"` |
| `securityAcl.type` | `'Any authenticated user'` , `'Specific role'` , `'Public'` |
| `agentDescriptor` | `"require_caller_id"` , `"created_by_ai_agent_advisor"` , `"created_by_build_agent"` , `""` (default: `""` ) |
| `agentType` | `"internal"` , `"external"` , `"voice"` , `"aia_internal"` |
| `channel` (agent) | `"nap"` , `"nap_and_va"` (default: `"nap_and_va"` ) |
| `schedule.triggerStrategy` (agent) | `"every"` , `"once"` , `"unique_changes"` , `"always"` |
| `schedule.triggerStrategy` (workflow) | `"every"` , `"immediate"` , `"manual"` , `"once"` , `"repeat_every"` , `"unique_changes"` |
| `outputTransformationStrategy` | `"abstract_summary"` , `"custom"` , `"none"` , `"paraphrase"` , `"summary"` , `"summary_for_search_results"` |

### Plugin Defaults

| Property | Applies To | Default | Notes |
| `recordType` | Agent / Workflow / Tool | `"template"` | MUST set `"custom"` for user-created entities |
| `executionMode` | Agent tool | `"autopilot"` | Review for write operations — consider `"copilot"` |
| `state` | Agent version | `"published"` | Workflow versions default to `"draft"` — always set `"published"` explicitly |

RAG naming: Use `"rag"` as the tool type in Fluent (not `"search_retrieval"`).

### Common Hallucinations

| Wrong | Correct |
| `"standard"` | `"custom"` (recordType) |
| `"automatic"` | `"autopilot"` (executionMode) |
| `"active"` | `"published"` (state) |
| `"database"` | `"crud"` (tool.type) |
| `versions` (for agents) | `versionDetails` |
| `versionDetails` (for workflows) | `versions` |
| `runAs` (for agents) | `runAsUser` |
| `"nap"` (for workflow triggers) | `"Now Assist Panel"` |
| `acl: "..."` (for agents or workflows) | `securityAcl: { $id, type, roles? }` (mandatory for both) |
| Missing `securityAcl` on workflows | `securityAcl` is mandatory for workflows too, not just agents |
| `securityAcl: { userAccess: 'dynamic_user' }` | `securityAcl: { $id, type: 'Any authenticated user' | 'Specific role' | 'Public' }` |
| Missing `$id` at workflow top level | Workflows use `$id` just like agents — always include it |
| `processingMessage` on workflows | Agent-only field — not valid on `AiAgenticWorkflow` |
| `team.description` set manually | Auto-populated from workflow `description` — do not set |
| Manual `inputSchema` | Auto-generated from `inputs` — never set manually |
| `inputs: {...}` for script tools | `inputs: [...]` (array, not object) for script tools |
| `dataAccess` omitted when `runAs` absent (workflow) | `dataAccess` is mandatory for workflows when `runAs` is not set |
| `searchProfile: "profile_name"` (RAG) | `searchProfile: { value: "profile_name", label: "Display Name" }` (ValueLabelType required) |
| `sources: ["table1", "table2"]` (RAG) | `sources: [{ value: "table1", label: "Label1" }, ...]` (ValueLabelType array required) |

### Property Naming

Always use camelCase in Fluent config — the plugin converts to snake_case for ServiceNow tables.

| Wrong (snake_case) | Correct (camelCase) |
| `memory_scope` | `memoryScope` |
| `sys_domain` | `sysDomain` |
| `run_as_user` | `runAsUser` |
| `role_list` | `roleList` |
| `target_table` | `targetTable` |
| `objective_template` | `objectiveTemplate` |

## Error Recovery

### Error Patterns Table

| Error Pattern | Category | Resolution |
| `dataAccess must have at least one of roleList or roleMap` | Missing roles | Add `dataAccess.roleMap` (role names) or `dataAccess.roleList` (role sys_ids) — required when `runAsUser` / `runAs` is not set |
| `Table not found` | Bad table name | `now-sdk query sys_db_object -q 'name=<table>' -f 'name,label' -o json` . Try `nameLIKE<partial>` to find similar names |
| `Record not found` / `Invalid reference` | Bad sys_id | Query the appropriate table: `now-sdk query sn_aia_agent -q 'name=<name>' -f 'sys_id,name' -o json` |
| `Duplicate name` | Name collision | `now-sdk query sn_aia_agent -q 'nameLIKE<name>' -f 'sys_id,name' -o json` . Ask user: rename or update existing? |
| ACL / permission error | ACL misconfiguration | Verify `securityAcl` is set correctly. Query `sys_security_acl` to verify ACL was generated |
| Build/compile TypeScript error | Code syntax | Read build output for line number. Common: missing comma, wrong type, unmatched brackets |
| Agent deploys but queries return 0 results | Phantom role | `Now.ID` in `roleList` hashes to non-existent sys_id. Query `sys_user_role` to get actual sys_id |
| `roleMap does not exist in type` | SDK lacks roleMap | Fall back to `roleList` — see roleMap Fallback below |

### Resolution Procedures

ACL misconfiguration recovery:

- Verify `securityAcl` is set on the agent/workflow with a valid `$id` and `type`

- If missing, add it inline and redeploy

- If using `type: 'Specific role'`, verify all role sys_ids via `now-sdk query sys_user_role`

- After redeploy, verify the plugin generated the ACL record:

```
now-sdk query sys_security_acl -q 'nameLIKE<agent_name>' -f 'sys_id,name,operation' -o json
```

### Redeploy-and-Verify Loop

After fixing any error:

- Build and deploy

- Query to verify the record was created/updated on the instance

- If deployment fails again, re-enter step 1 with the new error

Never silently skip a failed deployment. Always notify the user with:

- What failed and which error category was identified

- What fix was applied

- Whether the redeploy succeeded or needs further action

### Rollback

Undo a code change:

- Revert the `.now.ts` file to the previous state

- Redeploy

- Verify the agent/workflow is back to its previous configuration

Roll back via versioning:

- Set current published version's `state` to `"withdrawn"`

- Set previous version's `state` to `"published"`

- Redeploy — agent/workflow uses previous version's instructions

Only one version can be `state: "published"` at a time. For workflows, the published version's `instructions` are automatically written to `base_plan`.

### roleMap Fallback

The SDK may not yet support `roleMap` even if the instance does. Fall back to `roleList` with queried sys_ids:

- For each role name intended for `roleMap`, query `sys_user_role` to get the actual sys_id

- Replace `roleMap: ["role_name"]` with `roleList: ["<queried_sys_id>"]`

- NEVER use `Now.ID["role_name"]` as a fallback — it hashes to a different sys_id than the deployed role

- Redeploy

## Deployment

### Build and Deploy Commands

```
now-sdk build
now-sdk install
```

See the `developing-apps-guide` topic for full setup, authentication, and build workflow details. If that topic is unavailable and SDK authentication/project setup has not been completed, STOP and tell the user setup is required first — do NOT guess CLI flags, credentials, or environment configuration.

### Deployment Order

For workflows, agents must be deployed first:

- Create and deploy AI Agents (with `securityAcl`)

- Retrieve agent sys_ids: `now-sdk query sn_aia_agent -q 'name=<agent_name>' -f 'sys_id,name' -o json`

- Create and deploy workflow with `securityAcl` and agent sys_ids in `team.members`

- Verify: `now-sdk query sn_aia_usecase -q 'name=<workflow_name>' -f 'sys_id,name' -o json`

### ACL Configuration

`securityAcl` is mandatory on both agents and workflows. The plugin automatically generates `sys_security_acl` and `sys_security_acl_role` records — no separate ACL file or deployment step is needed.

Checklist:

- Set `securityAcl` inline on the agent/workflow — do NOT create a separate ACL file

- Do NOT query `sys_security_acl` to get an ACL sys_id for the agent/workflow

- NEVER leave `securityAcl` empty or omit it

- For `'Specific role'`: resolve role names to sys_ids via `sys_user_role` query before adding to `roles` array

### Post-Deployment Verification

After the final deploy, query to verify records were created:

```
# Verify agent was deployed
now-sdk query sn_aia_agent -q 'name=<agent_name>' -f 'sys_id,name' -o json

# Verify agent tools
now-sdk query sn_aia_agent_tool -q 'agentLIKE<agent_sys_id>' -f 'sys_id,name' -o json

# Verify ACL was generated
now-sdk query sys_security_acl -q 'nameLIKE<agent_name>' -f 'sys_id,name,operation' -o json

# Verify workflow (if applicable)
now-sdk query sn_aia_usecase -q 'name=<workflow_name>' -f 'sys_id,name' -o json

# Verify trigger activation status
now-sdk query sn_aia_trigger_configuration -q 'agent=<agent_sys_id>' -f 'sys_id,name,active' -o json
```

Trigger condition validation: Before deploying, validate encoded query syntax using `GlideFilter.checkFilter(encodedQuery)` on the instance. Invalid encoded queries cause silent trigger failures.

### Agent Studio URLs

After querying for sys_ids and instance URL, construct links to Agent Studio:

| View | URL Pattern |
| Agent Setup | `https://<instance>.service-now.com/now/agent-studio/agent-setup/<agent_sys_id>` |
| Agent Playground | `https://<instance>.service-now.com/now/agent-studio/playground/params/agent-id/<agent_sys_id>` |
| Agents List | `https://<instance>.service-now.com/sn_aia_agent_list.do` |
| Workflow Setup | `https://<instance>.service-now.com/now/agent-studio/usecase-guided-setup/<workflow_sys_id>` |
| Workflow Playground | `https://<instance>.service-now.com/now/agent-studio/playground/params/usecase-id/<workflow_sys_id>` |
| Workflows List | `https://<instance>.service-now.com/sn_aia_usecase_list.do` |

Never output placeholder URLs — always query for actual `instance_name` and sys_id values first.

### Deployment Summary Template

```
Created and Deployed: [Agent/Workflow Name]
Security ACL: Generated automatically by plugin (type: [Any authenticated user / Specific role / Public])

Sample Prompts to Test:
- [prompt 1 — targets the primary tool/capability]
- [prompt 2 — targets a secondary tool or edge case]
- [prompt 3 — tests a boundary or error handling path]

Next Steps:
1. Test the sample prompts above in Agent Playground
2. Manually activate triggers in ServiceNow after testing

Access in ServiceNow:
- Agent Setup: <actual URL>
- Playground: <actual URL>
- Agents List: <actual URL>
```

### Sample Prompts

- Generate 2-4 prompts tailored to the agent/workflow's actual tools and instructions

- Each prompt should exercise a different tool or instruction step

- Include at least one prompt that tests error handling (e.g., invalid input, record not found)

- Use realistic placeholder values (e.g., "INC0012345", not `{incident_number}`)

- For workflows, include a prompt that exercises the multi-agent coordination

## Plugin Transformation Notes

These notes describe how the plugin converts Fluent config values to ServiceNow record fields.

### Common to Both Agents and Workflows

- Script fields (`contextProcessingScript`, `runAsScript`, tool `script`): Auto-wrapped in CDATA by the plugin. Never add CDATA tags manually.

- `securityAcl`: Auto-generates `sys_security_acl` and `sys_security_acl_role` records. The ACL name is derived from the internal name: `{domain}.{scope}.{name}`. ACL type is `gen_ai_agent` for agents and `gen_ai_agentic_usecase` for workflows.

- `dataAccess.roleMap`: Role names are resolved to sys_ids via `sys_user_role` table at build time, then written to `sys_agent_access_role_mapping` records.

- `dataAccess.roleList`: Role sys_ids are written directly to `sys_agent_access_role_configuration.role_list` as a comma-separated list.

- `inputSchema`: Auto-generated from `inputs` — never set manually.

- Schedule fields: `runDayOfWeek` and `runDayOfMonth` are numbers in Fluent but stored as strings in ServiceNow. The plugin handles the conversion.

### AI Agent–Specific

- `channel`: String values (`'nap'`, `'nap_and_va'`) are resolved by the plugin to sys_ids during transform.

- CRUD tool `inputs`: Fluent uses `ToolInputType` object (`{ operationName, table, inputFields, queryCondition, returnFields }`). The plugin transforms this into ServiceNow's `crudInputs` JSON format with `operation`, `table.value`, `fieldValues`, and `query`.

- `queryCondition`: Maps to ServiceNow's `query` field on the tool — Fluent uses `queryCondition` to avoid confusion with encoded query syntax.

- `memoryCategories`: Each category creates a record in `sn_aia_ltm_category_mapping` linking the agent to the category.

- `versionDetails`: Published version's `instructions` become the active agent instructions.

- Tool `sysOverrides`: Overrides the tool definition record (`sn_aia_tool`). `m2mSysOverrides`: Overrides the agent-tool M2M record (`sn_aia_agent_tool_m2m`). These are separate properties targeting different tables.

### AI Agentic Workflow–Specific

- `team.description`: Auto-populated from the workflow's `description` field. Never set it manually — it will be overwritten.

- `team.name`: Auto-generated from the workflow name if omitted.

- `internalName`: Auto-generated as `{domain}.{scope}.{name}` — never specify it manually.

- `channel` (triggers): Workflow triggers use `'Now Assist Panel'` (plain string). The plugin resolves this to a sys_id from `messaging_channel`. Do NOT use `Record<'messaging_channel'>` — the workflow plugin rejects Record references for `channel`.

- `usecase` (trigger property): For a workflow's own trigger, automatically set to the parent workflow's record ID — can be overridden to point to a different workflow. For agent triggers, `usecase` has no default and is entirely user-settable to link the trigger to a specific workflow.

- Default value suppression: During `toShape` (ServiceNow → Fluent), fields matching their defaults are omitted to keep generated code clean.

## Avoidance (Anti-Patterns)

- Never use `Now.ID` for roles in `roleList` — always query `sys_user_role` to get the actual sys_id. `Now.ID` can hash to a sys_id that doesn't match the deployed role's actual sys_id ("phantom role" problem)

- Never use agent names in workflow `team.members` — always use agent sys_ids from `now-sdk query sn_aia_agent`

- Never add CDATA tags manually — the plugin handles CDATA wrapping automatically for script fields

- Never omit `securityAcl` — it is mandatory on both agents and workflows

- Never omit `mappedToColumn` on CRUD create/update inputs — without it, the update silently changes nothing

- Never omit `returnFields` on CRUD lookup tools — it is mandatory for lookup operations

- Never use `runAs` for agents or `runAsUser` for workflows — agents use `runAsUser`, workflows use `runAs`

- Never use `versions` for agents or `versionDetails` for workflows — agents use `versionDetails`, workflows use `versions`

- Never use `"nap"` for workflow trigger channel — workflow triggers require `"Now Assist Panel"` (plugin resolves to sys_id)

- Never use `Record<'messaging_channel'>` for workflow trigger channel — workflow plugin rejects Record references for `channel`; use plain strings only

- Never set `team.description` manually on workflows — auto-populated from workflow `description`

- Never set `inputSchema` manually — auto-generated from `inputs`

- Never omit `recordType: "custom"` on user-created agents, workflows, and tools — plugin defaults to `"template"` which is reserved for system-managed records

- Never use CRUD update tools for journal fields (`work_notes`, `comments`) — these are backed by `sys_journal_field`; always use a Script tool

- Never pass full sentences to lookup tool search fields — add keyword extraction guidance in agent instructions

- Never omit the output format step in instructions — tools return raw JSON/codes; without a formatting step, raw data is shown to the user

- Never write "gather from the triggering record" in instructions — use "from the task" or "from the context" instead

- Never create a workflow before deploying its agents — workflow `team.members` requires agent sys_ids which are only available after agent deployment

- Never use `Now.ID` for agents in separate files in `team.members` — must use sys_ids queried from `sn_aia_agent` after deployment

- Never use `GlideRecord` in script tools — always use `GlideRecordSecure` for record access

## Database Tables

| Table | Purpose |
| `sn_aia_agent` | AI Agent records |
| `sn_aia_agent_config` | Agent configuration and settings |
| `sn_aia_usecase` | AI Agentic Workflow records |
| `sn_aia_usecase_config_override` | Configuration overrides for workflows |
| `sn_aia_team` | Team configuration |
| `sn_aia_team_member` | Team member records |
| `sn_aia_version` | Version information |
| `sn_aia_tool` | Tool definitions |
| `sn_aia_agent_tool_m2m` | Agent-to-tool relationships |
| `sn_aia_trigger_configuration` | Trigger configuration |
| `sn_aia_trigger_agent_usecase_m2m` | Trigger-agent-usecase mappings |
| `sys_agent_access_role_configuration` | Role-based data access controls |
| `sys_security_acl` | ACL records (auto-generated by `securityAcl` ) |
| `sys_user_role` | Role records |

## Related

- building-ai-agents-guide.md — Core guide for creating AI Agents and Agentic Workflows

- query-guide.md — `now-sdk query` syntax for looking up sys_ids, verifying deployments, and resolving role references

- aiagent-api.md — AI Agent API reference (coalesce keys, field mappings, defaults)

- See the `developing-apps-guide` topic for project setup, authentication, and build workflow

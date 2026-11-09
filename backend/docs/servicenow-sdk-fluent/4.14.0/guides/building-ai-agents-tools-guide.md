Version: 4.14.0

# Building AI Agents — Tools Guide

Configure and select tools for ServiceNow AI Agents and AI Agentic Workflows using the Fluent SDK. Covers tool types (CRUD, script, OOB, reference-based, RAG), tool discovery, execution mode, output transformation, and multi-tool composition patterns.

## Tool Selection Guide

### Selection Priority

- OOB tools when available (e.g., Web Search, RAG, Knowledge Graph)

- Reference-based tools (action, subflow, capability, catalog, topic)

- CRUD tools for database operations

- Script tools only when no other tool type fits

Never use CRUD tools for journal fields (`work_notes`, `comments`). Always use Script tools with `GlideRecordSecure`.

### Tool Selection Table

| Need | Tool Type | Why |
| Read/search records | CRUD ( `lookup` ) | Direct table query |
| Create new records | CRUD ( `create` ) | Maps inputs to columns |
| Modify records | CRUD ( `update` ) | Query + field update |
| Remove records | CRUD ( `delete` ) | Query-based deletion |
| Custom logic | Script | Full JavaScript control |
| Web information | OOB ( `web_automation` ) | Auto-linked OOB tool |
| Semantic/keyword search | RAG ( `rag` ) | Structured search with ValueLabelType inputs |
| Flow Designer action | Action ( `action` ) | Triggers existing flows |
| Flow Designer subflow | SubFlow ( `subflow` ) | Triggers existing multi-step flows |
| AI skill | Capability ( `capability` ) | Links to GenAI skills |
| Service Catalog request | Catalog ( `catalog` ) | Links to catalog items |
| Virtual Agent conversation | Topic ( `topic` / `topic_block` ) | Links to VA topics |

### CRUD Operation Selection by User Intent

When the user needs database operations, choose the right CRUD operations:

| User Intent | Operations to Create | Example |
| "Look up / search / find / get" | `lookup` only | "Find incidents by priority" |
| "Create / add / insert / submit" | `create` + `lookup` (to verify) | "Create a new incident" |
| "Update / modify / change / assign" | `lookup` + `update` | "Update incident status" |
| "Delete / remove" | `lookup` + `delete` | "Delete a record by ID" |
| "Full CRUD management" | `lookup` + `create` + `update` | "Manage incident records" |

Tip: Most agents need a `lookup` tool even when the primary action is create/update/delete — the agent needs to find records before acting on them.

### `inputs` Format by Tool Type

| Tool type | `inputs` format | Has `script` field? |
| `crud` | Object ( `ToolInputType` ) with `operationName` , `table` , `inputFields` , etc. | No (auto-generated) |
| `rag` | Object ( `RagInputType` ) with `searchType` , `searchProfile` , `sources` , etc. (all using `ValueLabelType` ) | No (auto-generated) |
| `script` | Array of `[{ name, description, mandatory, value? }]` | Yes |
| `web_automation` | Omit (plugin provides defaults) | No |
| Reference types | Omit (platform resolves at runtime) | No |
| Other OOB types | Omit (plugin provides defaults) | No |

Mixing these up is a common error. If `type` is `"crud"`, `inputs` MUST be an object with `operationName`. If `type` is `"script"`, `inputs` MUST be an array.

### Required Tool Properties

Every tool must have `name` and `type`. `preMessage` and `postMessage` are strongly recommended on every tool. Every agent must have `processingMessage` and `postProcessingMessage` (not available on workflows).

### Valid `tool.type` Values

`"script"`, `"crud"`, `"capability"`, `"subflow"`, `"action"`, `"catalog"`, `"topic"`, `"topic_block"`, `"web_automation"`, `"rag"`

## Tool Discovery

Before creating any tool, check existing resources in the current app scope. Run all six checks in order — do not skip any. Only assign `crud` or a new `script` tool if all six checks return no usable match.

Resolve the scope sys_id first:

```
now-sdk query sys_scope -q 'scope=<scope_name>' -f 'sys_id,scope' -o json
```

Then run each check using the scope sys_id:

| Priority | Resource Type | Table to Query | encodedQuery | If match found, use tool type |
| 1 | GenAI Skill | `sn_nowassist_skill_config` | `sys_scope=<scope_sys_id>^active=true` | `capability` + `capabilityId` |
| 2 | SubFlow | `sys_hub_flow` | `type=subflow^sys_scope=<scope_sys_id>` | `subflow` + `subflowId` |
| 3 | Flow Action | `sys_hub_action_type_definition` | `sys_scope=<scope_sys_id>` | `action` + `flowActionId` |
| 4 | Catalog Item | `sc_cat_item` | `sys_scope=<scope_sys_id>^active=true` | `catalog` + `catalogItemId` |
| 5 | Conversational Topic | `sys_cs_topic` | `sys_scope=<scope_sys_id>^active=true` | `topic` + `virtualAgentId` |
| 6 | Script Include method | `sys_script_include` | `sys_scope=<scope_sys_id>^active=true` | `script` calling existing method |

Rule: Only assign `crud` or a new `script` tool if all six checks return no usable match. Always inform the user which existing resource was reused.

Example discovery query:

```
now-sdk query sn_nowassist_skill_config -q 'sys_scope=<scope_sys_id>^active=true' -f 'sys_id,name' -o json
```

## CRUD Tools

For database operations (create, lookup, update, delete). All CRUD tools require `recordType: "custom"` and `type: "crud"`.

### Operations

| Operation | Required Fields |
| `create` | `table` , `inputFields` with `mappedToColumn` |
| `lookup` | `table` , `queryCondition` , `returnFields` (mandatory) |
| `update` | `table` , `queryCondition` , `inputFields` with `mappedToColumn` |
| `delete` | `table` , `queryCondition` |

### queryCondition Syntax

Format: `"column_name=={{input_field_name}}"`. Always verify column names by querying `sys_dictionary` before writing tools.

```
now-sdk query sys_dictionary -q 'name=<target_table>^internal_type!=collection' -f 'element,column_label' -o json
```

| Operator | Syntax | Example |
| Equals | `field=value` | `state=1` |
| Not equals | `field!=value` | `state!=7` |
| Less/greater | `field<=value` | `priority<=2` |
| Contains | `fieldLIKEvalue` | `short_descriptionLIKEnetwork` |
| Starts with | `fieldSTARTSWITHvalue` | `numberSTARTSWITHINC` |
| Is empty | `fieldISEMPTY` | `assigned_toISEMPTY` |
| Is not empty | `fieldISNOTEMPTY` | `resolved_atISNOTEMPTY` |
| OR | `^OR` | `priority=1^ORpriority=2` |

Dot-walking references in query conditions: Use dot notation to traverse reference fields: `assigned_to.department=<value>`. The left side of the operator must always be a valid column path on the target table.

### Common Column Name Mistakes

Before writing any `queryCondition` or `returnFields`, query `sys_dictionary` to get actual column names. Do NOT guess or assume column names.

| Common Mistake | Correct Column | Table |
| `incident_number` | `number` | `incident` |
| `desc` | `short_description` | `incident` |
| `description` (for title) | `short_description` | `incident` |
| Column from a different table | — | Verify table ownership |

Always extract the `element` field from `sys_dictionary` results — these are the valid column names.

### Lookup Best Practices

- Always include `{ name: 'sys_id' }` in `returnFields` — without it, the agent cannot chain operations (e.g., pass the record's sys_id to another tool)

- Use `LIKE` operator for text-based searches (substring match instead of exact match)

- Use multiple keyword inputs with `OR` for broader matching on natural language

- Add keyword extraction guidance in agent instructions: "Extract 1-2 specific keywords from the user's request. Do NOT pass full sentences to the search tool."

- Prefer `number` over `sys_id` as primary filter: `number={{id}}^ORsys_id={{id}}`

- For reference fields in `returnFields`, include `referenceConfig`: `{ table: "sys_user", field: "name" }`

- Also include `number` (or the appropriate identifier) in `returnFields` so downstream tools can reference the record by its display value

Primary filter by table:

| Table | Primary Filter Field | queryCondition Pattern |
| `incident` | `number` | `number={{id}}^ORsys_id={{id}}` |
| `change_request` | `number` | `number={{id}}^ORsys_id={{id}}` |
| `sc_request` | `number` | `number={{id}}^ORsys_id={{id}}` |
| `sys_user` | `user_name` or `name` | `user_name={{id}}^ORsys_id={{id}}` |
| `sys_user_group` | `name` | `name={{id}}^ORsys_id={{id}}` |
| `kb_knowledge` | `number` | `number={{id}}^ORsys_id={{id}}` |

When to use which pattern:

| Search Type | Pattern | Example |
| Known identifier (number, ID) | Exact match with OR fallback: `number={{id}}^ORsys_id={{id}}` | "Find INC0012345" |
| Known value (category, priority) | Exact match: `priority={{priority}}` | "Find P1 incidents" |
| Natural language / description | LIKE + multiple keywords with OR | "email not syncing on Outlook" |

### Create — Mandatory Columns

For `create` operations, query `sys_dictionary` to discover mandatory columns:

```
now-sdk query sys_dictionary -q 'name=<table>^mandatory=true' -f 'column_label,element' -o json
```

Ensure ALL mandatory columns are captured in `inputFields` with `mandatory: true`. Update agent instructions to collect these fields from the user before creating.

### `mappedToColumn` Self-Check

After writing each create or update tool, run this check before proceeding:

- Parse `queryCondition` and list every `{{field_name}}` variable — these are query-only fields

- For each entry in `inputFields`:

- Is the field in the queryCondition variables? → It is a query field. Confirm it does NOT have `mappedToColumn`

- Is the field NOT in queryCondition? → It is a write field. Confirm it HAS `mappedToColumn` set to a valid column name. If missing, add it now

- For `create` tools (no queryCondition): every `inputField` MUST have `mappedToColumn` — no exceptions

- Do NOT proceed to the next tool until this check passes

Without `mappedToColumn`, the plugin silently skips the field — the update finds the record but changes NOTHING, with no error.

```
// WRONG — missing mappedToColumn, update silently changes nothing
{ name: "new_status", mandatory: true }

// CORRECT — mappedToColumn maps input to table column
{ name: "new_status", mandatory: true, mappedToColumn: "state" }
```

```
inputFields: [
  { name: "record_id", mandatory: true },                          // query input — in queryCondition (NO mappedToColumn)
  { name: "new_status", mandatory: true, mappedToColumn: "state" }, // write input
  { name: "priority", mandatory: true, mappedToColumn: "priority" } // write input
]
```

### Delete Operation

For `delete` operations, configure `queryCondition` to identify the target record. No `inputFields` with `mappedToColumn` are needed — the tool only needs to find the record to delete.

```
{
    name: 'Delete Record',
    type: 'crud',
    recordType: 'custom',
    executionMode: 'copilot',
    preMessage: 'Deleting the record...',
    postMessage: 'Record deleted.',
    inputs: {
        operationName: 'delete',
        table: 'incident',
        queryCondition: 'number={{record_number}}',
        inputFields: [
            { name: 'record_number', description: 'The incident number to delete', mandatory: true }
        ]
    }
}
```

## Script Tools

All script inputs are strings at runtime. Parse with `parseInt()`, `JSON.parse()`, etc. The `inputs` field for script tools is a simple array of input field definitions (unlike CRUD tools which use an object).

```
{
    name: 'Calculate Priority',
    type: 'script',
    preMessage: 'Calculating results...',
    postMessage: 'Calculation complete.',
    inputs: [
        { name: 'impact', description: 'Impact level', mandatory: true },
        { name: 'urgency', description: 'Urgency level', mandatory: true }
    ],
    script: `(function(inputs) {
        var impact = parseInt(inputs.impact, 10);
        var urgency = parseInt(inputs.urgency, 10);
        var priority = Math.max(impact, urgency);
        return { priority: priority, status: 'success' };
    })(inputs);`
}
```

Key rules:

- Always use `GlideRecordSecure` (not `GlideRecord`)

- Do NOT add CDATA tags (plugin handles automatically)

- `inputSchema` is auto-generated from `inputs` — do not specify it manually

- Use module imports for server-side script files (or `Now.include()` for legacy scripts)

### Calling Existing Script Includes

If a script include with a matching method exists, call it from within the Script tool instead of re-implementing logic:

```
{
    name: 'Calculate Priority',
    type: 'script',
    preMessage: 'Calculating priority...',
    postMessage: 'Priority calculated.',
    inputs: [
        { name: 'impact', description: 'Impact level', mandatory: true },
        { name: 'urgency', description: 'Urgency level', mandatory: true }
    ],
    script: `(function(inputs) {
        var util = new MyAppUtils();
        var result = util.calculatePriority(inputs.impact, inputs.urgency);
        return { priority: result, status: "success" };
    })(inputs);`
}
```

### Journal Field Updates (`work_notes`, `comments`)

`work_notes` and `comments` are journal fields backed by `sys_journal_field` — they are not columns on the target table. CRUD update tools cannot write to them. Always use a Script tool:

```
{
    name: 'Update Journal Field',
    type: 'script',
    preMessage: 'Updating journal field...',
    postMessage: 'Journal field updated.',
    inputs: [
        { name: 'table_name', description: 'Table name', mandatory: true },
        { name: 'record_sys_id', description: 'Record sys_id', mandatory: true },
        { name: 'field', description: 'Journal field (work_notes or comments)', mandatory: true },
        { name: 'note_text', description: 'Text to add', mandatory: true }
    ],
    script: `(function(inputs) {
        var gr = new GlideRecordSecure(inputs.table_name);
        if (!gr.get(inputs.record_sys_id)) {
            return { status: "error", message: "Record not found: " + inputs.record_sys_id };
        }
        if (inputs.field === "work_notes") {
            gr.work_notes = inputs.note_text;
        } else if (inputs.field === "comments") {
            gr.comments = inputs.note_text;
        } else {
            return { status: "error", message: "Invalid journal field: " + inputs.field };
        }
        gr.update();
        return { status: "success", message: "Journal field updated" };
    })(inputs);`
}
```

### GlideAggregate Pattern

Use `GlideAggregate` in script tools for counting or aggregating records:

```
{
    name: 'Count Records',
    type: 'script',
    preMessage: 'Counting records...',
    postMessage: 'Count complete.',
    inputs: [
        { name: 'table', description: 'Table to count', mandatory: true },
        { name: 'filter', description: 'Encoded query filter', mandatory: true }
    ],
    script: `(function(inputs) {
        var ga = new GlideAggregate(inputs.table);
        ga.addEncodedQuery(inputs.filter);
        ga.addAggregate('COUNT');
        ga.query();
        var count = 0;
        if (ga.next()) {
            count = parseInt(ga.getAggregate('COUNT'), 10);
        }
        return { count: count, status: 'success' };
    })(inputs);`
}
```

## Reference-Based Tools

Each requires a type-specific reference field containing the target record's sys_id. Do NOT add `inputs` — the platform resolves inputs at runtime from the referenced record.

| Tool Type | Required Field | Target Table | Use For |
| `action` | `flowActionId` | `sys_hub_action_type_definition` | Running a Flow Designer action |
| `capability` | `capabilityId` | `sn_nowassist_skill_config` | Using a GenAI skill (summarization, etc.) |
| `subflow` | `subflowId` | `sys_hub_flow` | Running a Flow Designer subflow |
| `catalog` | `catalogItemId` | `sc_cat_item` | Submitting a Service Catalog request |
| `topic` | `virtualAgentId` | `sys_cs_topic` | Invoking a Virtual Agent topic |
| `topic_block` | `virtualAgentId` | `sys_cs_topic` | Invoking a Virtual Agent topic block |

## OOB Tools

OOB tools only require `type` and `name`. The plugin auto-links to the existing OOB tool record.

```
{
    type: 'web_automation',
    name: 'AIA Web Search',
    preMessage: 'Searching the web...',
    postMessage: 'Web search results retrieved.'
}
```

Other supported OOB type: `'rag'` — see the RAG (Search Retrieval) Tools section below.

Shared defaults across OOB tools:

| Property | Default |
| `active` | `true` |
| `executionMode` | `"autopilot"` |
| `displayOutput` | `false` |
| `maxAutoExecutions` | `10` |

### Internal (Platform-Provided) Tools

These are platform-provided tools available to all agents. They do NOT need to be configured in the `tools` array — the platform provides them automatically. Reference them by name in agent `instructions` when the use case requires their behavior.

| Tool | Category | Purpose | Use When |
| `organize_general_knowledge` | Internal | Leverages the agent's general knowledge to answer questions | Agent needs to reason or answer without querying a specific table or tool |
| `math` | Internal | Performs mathematical calculations | Agent needs arithmetic, aggregation, or formula evaluation |
| `finish` | Internal | Signals the agent has completed its task | Agent should explicitly terminate after delivering results |
| `collect_input_from_user` | Communication | Prompts the user for additional input | Agent needs clarification, confirmation, or missing data from the user |
| `show_output_to_user` | Communication | Displays formatted output to the user | Agent needs to present results, summaries, or status updates |

Do NOT add these to the `tools` array — they are automatically available.

Usage in instructions example: `"If the user's request is unclear, use collect_input_from_user to ask for clarification before proceeding."`

## RAG (Search Retrieval) Tools

RAG tools enable semantic search and document retrieval from ServiceNow AI Search indexes. The `type` for RAG tools in Fluent is `'rag'` and requires structured `inputs` configuration with `ValueLabelType` objects.

### Search Types

| Type | Description | Required Fields |
| `'keyword'` | Simple text matching | None |
| `'semantic'` | Semantic search using embeddings | `semanticIndexes` (array of ValueLabelType) |
| `'hybrid'` | Combines keyword and semantic | `semanticIndexes` (array of ValueLabelType) |

Default to `hybrid` when a published profile with active indexes exists. If no active semantic indexes are linked to the picked sources, fall back to `keyword`.

Note: The `query` description is generated using the `searchProfile.label`. `semanticIndexes` and `documentMatchThreshold` are only included in the generated schema for `semantic` and `hybrid` search types. `fields` and `searchResultsLimit` apply to all search types.

### Existing Tool Discovery

Before creating a new RAG tool, check whether an existing one already covers the need — duplicate RAG tools waste search profile setup and can confuse tool selection at runtime.

```
now-sdk query sn_aia_agent_tool_m2m -q 'tool.nameLIKEAIA RAG Retriever^active=true' -f 'sys_id,name,description,inputs' -o json
```

`tool.nameLIKEAIA RAG Retriever` dot-walks to the shared OOB tool definition's name (always "AIA RAG Retriever") — the returned `name` field is each match's own per-instance display name (e.g. "Semantic Knowledge Search"), not "AIA RAG Retriever" itself.

- Matches found: Parse each tool's `inputs` (search profile, sources, fields, search type) and present them to the user. Ask whether to reuse an existing tool or create a new one — do not assume reuse or creation without the user's explicit choice.

- Reusing an existing tool: Re-derive `searchProfile`, `sources`, `fields`, and `semanticIndexes` from a live query (see Profile Cascade below) rather than copying the stored `inputs` verbatim — the profile's state or indexes may have changed since the tool was created. If the live query disagrees with the stored `inputs`, the live result wins.

- No matches, or user wants a new tool: Proceed to the Profile Cascade below.

### Profile Cascade

Before creating a RAG tool, verify a published AI Search profile exists. The SDK does NOT create or publish profiles — profile lifecycle is the user's responsibility.

Query sequence to validate a profile:

- `ais_search_profile` — find active, published profiles (`active=true^state=published`)

- `ais_search_profile_ais_search_source_m2m` — get linked source sys_ids for the picked profile

- `ais_search_source` — get source records and their `datasource` table names

- `ais_semantic_index_configuration` — check for active indexes on those datasources

```
now-sdk query ais_search_profile -q 'active=true^state=published' -f 'sys_id,label,state' -o json
now-sdk query ais_search_profile_ais_search_source_m2m -q 'profile=<profile_sys_id>' -f 'sys_id,search_source' -o json
now-sdk query ais_search_source -q 'sys_idIN<linked_source_sys_ids>^active=true' -f 'sys_id,name,datasource' -o json
now-sdk query ais_semantic_index_configuration -q 'active=true^datasourceIN<table_names>' -f 'sys_id,name' -o json
```

Tier selection (internal logic — not user-facing labels):

| Condition | Search Type | Action |
| Published profile + active semantic indexes | `hybrid` (default) | Proceed |
| Published profile + no active indexes | `keyword` (forced) | Inform user: no active indexes, falling back to keyword |
| No active published profiles | — | [STOP] . Do NOT proceed until the user creates and publishes a profile |

### RAG Tool Inputs Format

All RAG inputs use `ValueLabelType` objects (`{ value: string, label: string }`) — NOT plain strings.

### RAG Tool Example

```
{
    name: 'Semantic Knowledge Search',
    description: 'Searches knowledge articles using semantic search',
    type: 'rag',
    recordType: 'custom',
    executionMode: 'autopilot',
    preMessage: 'Performing semantic search...',
    postMessage: 'Semantic search completed.',
    inputs: {
        searchType: {
            type: 'semantic',
            semanticIndexes: [
                { value: 'kb_knowledge_text_index', label: 'Knowledge Base Text Index' }
            ],
            documentMatchThreshold: 0
        },
        searchProfile: {
            value: 'quick_action_kb_search_profile',
            label: 'Quick Action - KB Search Profile'
        },
        sources: [
            { value: 'kb_knowledge', label: 'Knowledge Articles' }
        ],
        fields: [
            { value: 'kb_knowledge.short_description', label: 'Short description [kb_knowledge]' },
            { value: 'kb_knowledge.text', label: 'Article body [kb_knowledge]' },
            { value: 'kb_knowledge.number', label: 'Number [kb_knowledge]' }
        ],
        searchResultsLimit: 5
    }
}
```

### Search Type Comparison

| Property | `keyword` | `semantic` | `hybrid` |
| `searchType.type` | `'keyword'` | `'semantic'` | `'hybrid'` |
| `semanticIndexes` | Not applicable | Required | Required |
| `documentMatchThreshold` | Not applicable | Always `0` | Always `0` |
| `searchProfile` | Required | Required | Required |
| `sources` | Optional | Optional | Optional |
| `fields` | Optional | Optional | Optional |
| `searchResultsLimit` | Optional | Optional | Optional |

Important: `documentMatchThreshold` must always be set to `0`. The field accepts `[0, 1]` but other values should not be used.

## Execution Mode and Display

### `executionMode` (copilot vs autopilot)

Each tool has its own `executionMode` that overrides the agent-level setting for that specific tool. Default: `"autopilot"`.

| Tool Operation | Suggested `executionMode` | Why |
| CRUD `lookup` | `"autopilot"` | Read-only, no side effects |
| CRUD `create` | `"copilot"` | Creates records — user confirmation recommended |
| CRUD `update` | `"copilot"` | Modifies existing data |
| CRUD `delete` | `"copilot"` | Destructive, hard to reverse |
| Script (read-only) | `"autopilot"` | No side effects |
| Script (writes data) | `"copilot"` | Side effects — user confirmation recommended |
| Web Search | `"autopilot"` | Read-only external search |
| Search Retrieval (RAG) | `"autopilot"` | Read-only retrieval from AI Search indexes |
| Reference-based tools | `"copilot"` | Triggers flows/actions — confirmation recommended |

General rule: Use `"copilot"` for tools that modify data or trigger external processes. Use `"autopilot"` for read-only operations. When unsure, prefer `"copilot"`.

### `displayOutput`

Controls whether tool output is shown to the user.

- `true` — tool output is visible to the user

- `false` — tool output is hidden (agent uses it internally)

### `maxAutoExecutions`

Maximum number of times a tool can auto-execute without user confirmation. Default: `10`. Only applies in copilot mode.

### `outputTransformationStrategy`

Controls how tool output is transformed before the LLM processes it. Default: `"none"`.

| Value | Behavior | Use When |
| `"none"` | No transformation — raw output passed through | Output is already concise, or full data fidelity needed |
| `"summary"` | Summarized into shorter format | Verbose output but key details must be preserved |
| `"abstract_summary"` | Most minimal format | Default for most tools — reduces output while retaining key points |
| `"paraphrase"` | Rephrased in different words | Output needs rewording without significant data loss |
| `"custom"` | Custom transformation using `transformationInstructions` | When custom transform logic is specified |
| `"summary_for_search_results"` | Specialized summary for search results | Web Search or CRUD lookup tools returning many results |

Selection guide by tool type:

| Tool Type | Suggested Strategy | Why |
| CRUD `lookup` (few fields) | `"none"` | Output is already small |
| CRUD `lookup` (many fields/records) | `"none"` | Full data fidelity needed; instructions handle formatting |
| Web Search | `"none"` | Full results needed; agent instructions handle presentation |
| Script (returns structured data) | `"none"` | Preserve data accuracy |
| Tool feeding into another tool | `"abstract_summary"` | Reduce output volume for next tool to consume |
| Tool with user-facing output | `"abstract_summary"` | Concise output for users |

### Processing Messages

Every `AiAgent` MUST include `processingMessage` and `postProcessingMessage` as top-level properties. These are not available on `AiAgenticWorkflow`.

| Property | Required | Description |
| `processingMessage` | Yes (Agent) | Shown to the user while the agent is working |
| `postProcessingMessage` | Yes (Agent) | Shown to the user after the agent finishes |

Generate context-appropriate messages based on the agent's purpose:

| Agent Purpose | `processingMessage` | `postProcessingMessage` |
| Incident management | `"Analyzing your incident request..."` | `"Incident analysis complete."` |
| Knowledge search | `"Searching knowledge base..."` | `"Here are the results I found."` |
| Record creation | `"Processing your request..."` | `"Your request has been completed."` |

Bad examples — do not use generic or uninformative messages:

| Bad `processingMessage` | Why it's bad |
| `"Processing..."` | Too generic, doesn't tell the user what's happening |
| `"Please wait"` | No context about the operation |
| `"Working on it"` | Uninformative |

Every tool also supports `preMessage` and `postMessage` for tool-level status:

| Tool Action | `preMessage` Example | `postMessage` Example |
| CRUD lookup | `"Searching for incidents..."` | `"Incidents retrieved."` |
| CRUD create | `"Creating the incident record..."` | `"Incident created successfully."` |
| CRUD update | `"Updating the record..."` | `"Record updated successfully."` |
| CRUD delete | `"Deleting the record..."` | `"Record deleted."` |
| Script (compute) | `"Calculating results..."` | `"Calculation complete."` |
| Web Search | `"Searching the web..."` | `"Search results retrieved."` |
| Search Retrieval | `"Searching knowledge sources..."` | `"Documents retrieved."` |
| Subflow/Action | `"Running the workflow..."` | `"Workflow completed."` |

## Tool Composition

### Composition Rules

| Scenario | Tools Needed | Why |
| Read/write database records | CRUD only | Direct table operations |
| Read records + calculate/transform | CRUD + Script | Script processes CRUD output |
| Read records + external info | CRUD + OOB | Web Search supplements DB data |
| Read, transform, and enrich | CRUD + Script + OOB | Full pipeline: fetch, process, enrich |

Rules:

- Each tool should do ONE thing — don't combine CRUD and computation in a single tool

- Instructions must define the ORDER tools are used — the agent follows instruction steps

- Name tools clearly so instructions can reference them unambiguously

- Use `outputTransformationStrategy` on tools whose output feeds into other tools

### Multi-Tool Instructions Pattern

When an agent has multiple tools, instructions must chain them explicitly:

```
Step 1: Gather Data.
- Use [CRUD Lookup Tool] to fetch records matching the user's criteria.
- NEVER skip this step — all subsequent steps depend on its output.
- DO NOT PROCEED if no records are found.

Step 2: Process Results.
- Use [Script Tool] to analyze/aggregate the data from Step 1.
- Present computed results to the user.

Step 3: Enrich (if needed).
- Use [OOB Web Search] to find supplementary information.
- Combine with Step 2 results and present the final summary before taking any action.
```

## Troubleshooting

| Problem | Solution |
| LOOKUP returns no data | Add `returnFields` — it's MANDATORY |
| UPDATE runs but doesn't change any fields | Add `mappedToColumn` to all update inputs — without it, the update is a silent failure |
| UPDATE changes wrong fields | Verify `mappedToColumn` values match actual column names from `sys_dictionary` |
| CRUD tool fails | Verify `recordType: "custom"` and correct `inputs` ToolInputType format |
| Script fails | Check input parsing ( `parseInt` , `JSON.parse` ) and error handling |
| Permission issues | Verify user has necessary table/field access |
| OOB tool not working | Verify the tool `type` matches an OOB type (e.g., `web_automation` ) |
| RAG returns no results | Verify profile is `active=true^state=published` and semantic indexes are active |

## Related

- Building AI Agents Guide — full agent/workflow creation, authentication, triggers, ACL deployment

- See the `developing-apps-guide` topic for project setup, authentication, and build workflow

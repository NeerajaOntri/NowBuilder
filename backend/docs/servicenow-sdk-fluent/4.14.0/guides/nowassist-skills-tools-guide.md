Version: 4.14.0

# AI Skills — Tools Guide

Complete reference for configuring tools in NowAssist / GenAI Skills. Tools fetch or manipulate data before prompt processing — use them when a skill needs data beyond user inputs, such as querying records, searching the web, running business logic, or integrating with flows.

## Tool Methods

| Method | Purpose |
| `t.Script()` | Reference an external Script Include |
| `t.InlineScript()` | Inline script function defined directly in the skill |
| `t.WebSearch()` | Web search via AI answers |
| `t.Skill()` | Call another published skill |
| `t.Subflow()` | Execute a Flow Designer subflow |
| `t.FlowAction()` | Execute a Flow Designer action |
| `t.Decision()` | Conditional branching |

## Output Access in Prompts

| Tool Type | Access Pattern |
| `t.Script()` / `t.InlineScript()` | `${p.tool.ToolName.output}` |
| `t.WebSearch()` / `t.Skill()` | `${p.tool.ToolName.response}` |
| `t.Subflow()` | `${p.tool.ToolName.output}` |
| `t.FlowAction()` | `${p.tool.ToolName.outputName}` |

WebSearch / Skill fixed outputs: `provider`, `response`, `error`, `errorcode`, `status`

### ToolHandle Output Access (code-level)

When referencing a tool's output from another tool (not a prompt), the accessor varies:

| Tool Type | Output Access |
| `t.Script()` / `t.InlineScript()` | `toolName.output` only — no nested dot-walk |
| `t.Skill()` / `t.Subflow()` / `t.FlowAction()` | Dot-walk supported if output schema is known |

## Tool Selection Guide

| Need | Tool Method |
| No data operations | None — skip tools entirely |
| Quick database lookup | `t.InlineScript()` |
| Reusable / complex logic | `t.Script()` |
| External web data | `t.WebSearch()` |
| Call another skill | `t.Skill()` |
| Existing subflow | `t.Subflow()` |
| Existing flow action | `t.FlowAction()` |
| Conditional routing | `t.Decision()` |

## Required Identifiers

Every tool needs a `$id`. Some tools need additional identifiers depending on how they integrate with the platform:

| Tool Type | `$id` | `$capabilityId` | `output.$id` | Per-input `$id` | Per-output `$id` |
| `t.InlineScript()` | Yes | No | No | No | No |
| `t.Script()` | Yes | Yes | Yes | Yes | No |
| `t.WebSearch()` | Yes | No | No | No | No |
| `t.Skill()` | Yes | No | No | No | No |
| `t.FlowAction()` | Yes | Yes | No | Yes | Yes |
| `t.Subflow()` | Yes | Yes | No | Yes | Yes |
| `t.Decision()` | Yes | No | No | No | No |

- `$id`: Unique record identifier for the tool itself.

- `$capabilityId`: Identifies the external capability (Script Include, Flow Action, or Subflow) the tool wraps. Required because these tools reference a platform artifact that exists outside the skill definition.

- `output.$id`: Script tools produce a custom output attribute that needs its own identifier. Only applies to `t.Script()`.

- Per-input / per-output `$id`: Each entry in the `inputs` or `outputs` array is a separate mapping record and needs its own unique `$id`.

`$capabilityId` is NOT supported for `t.InlineScript()` and `t.WebSearch()`. Only use `$id` for those tools. The `$capabilityId` property is reserved for datasource tools (`t.Script()`, `t.Subflow()`, `t.FlowAction()`).

## Tool Input Values

Tool inputs (for `t.Script()`, `t.Skill()`, `t.Subflow()`, `t.FlowAction()`) accept these value types:

| Valid Value Type | Example |
| Skill input reference | `t.input.tableName` |
| Literal string | `"hardcoded value"` |
| Tool output reference | `previousTool.output` |

Do NOT use `{ type: 'script', script: '...' }` for input values — this is not a valid type. Handle transformations inside the script itself.

### Tool Name Constraint

Tool names must be alphanumeric only (letters and numbers). Use camelCase. No underscores, spaces, or special characters.

### Referencing Inputs in InlineScript Tools

| Input Name | Correct Syntax | Wrong Syntax |
| `'shift requirement'` | `context.getValue('shift_requirement')` | `context.getValue('shift requirement')` |
| `'incident number'` | `context.getValue('incident_number')` | `context.getValue('incident number')` |
| `'incidentNumber'` | `context.getValue('incidentNumber')` | N/A |

Rule: Convert input name to snake_case for `context.getValue()`. If input name has no spaces (camelCase), use it as-is.

### Referencing Inputs in Script Tool Values

| Input Name | Correct Syntax | Wrong Syntax |
| `'shift requirement'` | `t.input['shift requirement']` | `t.input.shift_requirement` |
| `'incidentNumber'` | `t.input.incidentNumber` | N/A |

Rule: Use bracket notation for input names with spaces.

### Tool Output References

Output accessor varies by tool type:

- Script / InlineScript -> `.output`

- WebSearch / Skill -> `.response`

- FlowAction / Subflow -> `.outputName` (specific named output)

### Valid ToolDataType Values

These types can be used in `type` fields for Subflow and FlowAction inputs/outputs:

- OneExtend types: `'string'`, `'boolean'`, `'numeric'`, `'json_object'`, `'json_array'`, `'simple_array'`, `'glide_record'`, `'table'`, `'object'` (legacy, maps to `json_object`)

- Flow Designer types: `'choice'`, `'date'`, `'datetime'`, `'duration'`, `'html'`, `'conditions'`, `'script'`

### Invalid Input Types (Subflow & FlowAction)

| Invalid Input Type | Description |
| `document_id` | Document ID field type |
| `reference` | Reference field type (use `glide_record` instead) |
| `snapshot_template_value` | Snapshot template value type |

## InlineScript Tool

Lightweight scripts defined directly in the skill — no external Script Include needed. Preferred for most use cases because it is simpler and requires no post-deployment validation.

`$capabilityId` is NOT supported for InlineScript. Only use `$id`.

| Property | Required | Description |
| `$id` | Yes | Unique identifier for the tool record |
| `script` | Yes | Script function body |
| `truncate` | No | Truncate output |
| `depends` | No | Array of tools that must run first |
| `condition` | No | Conditional execution |

```
const getIncident = t.InlineScript("GetIncident", {
  $id: Now.ID["skill_getincident_tool"],
  script: `(function(context) {
        var gr = new GlideRecord('incident');
        gr.addQuery('number', context.getValue('incident_number'));
        gr.query();
        if (gr.next()) {
            return {
                number: gr.getValue('number'),
                short_description: gr.getValue('short_description')
            };
        }
        return { error: 'Incident not found' };
    })(context)`,
});
```

Access inputs via `context.getValue('input_name')` with snake_case conversion (spaces become underscores).

## Script Tool

References an external Script Include. Use when logic is highly complex, needs to be shared across multiple skills, or an existing Script Include already exists.

### Script vs InlineScript — When to Use Which

| Tool Type | When to Use |
| `t.InlineScript()` | Lightweight scripts defined directly in skill, no external Script Include needed |
| `t.Script()` | Complex or reusable logic via external Script Include |

Prefer `t.InlineScript()` for most cases — it is simpler, requires no post-deployment validation, and works for most use cases. Only use `t.Script()` when you have an existing Script Include to reuse OR the logic is highly complex and needs to be shared across multiple skills.

### Script Tool Properties

Requires an external Script Include with `accessibleFrom: 'all'`. Each `inputs[].name` must match a function parameter name exactly.

```
const myTool = t.Script("MyTool", {
  $id: Now.ID["my_skill_script_tool"],
  $capabilityId: Now.ID["my_skill_script_capability"],
  output: { $id: Now.ID["my_skill_script_output"] },
  scriptId: myScriptInclude,
  scriptFunctionName: "processData",
  inputs: [
    { $id: Now.ID["tool_input_id"], name: "param", value: t.input.description },
  ],
});
```

`value` only accepts: `t.input.inputName`, `"hardcoded string"`, or `previousTool.output`.

### scriptId Accepted Values

- ScriptInclude variable (same project — RECOMMENDED)

- Script Include sys_id string (NOT name — must be sys_id)

- DbRecord reference: `Now.Record('sys_script_include', 'sys_id')`

The `scriptId` property does NOT accept the Script Include name. You must use one of the three forms above.

### Script Include Requirements

- `accessible_from` must be set to `'all'` (accessible from all scopes)

- Prefer same app scope as the skill

- Pattern: `Class.create()`

- `clientCallable`: `false`

## WebSearch Tool

For external internet searches only. Do NOT use for internal table queries or KB article lookups.

`$capabilityId` is NOT supported for WebSearch. Only use `$id`.

| Property | Required | Description |
| `$id` | Yes | Unique identifier for the tool record |
| `searchType` | Yes | Must be `'ai_answers'` |
| `query` | Yes | Search query (string or tool output) |
| `aiSearchProviders` | No | `'perplexity'` , `'openai'` , `'gemini'` , `'azure_openAI'` — requires valid API key |
| `depends` | No | Array of tools that must run first |
| `truncate` | No | Per-output truncate config: `{ response?: boolean, provider?: boolean, ... }` |
| `condition` | No | Conditional execution |

```
const searchWeb = t.WebSearch("SearchWeb", {
  $id: Now.ID["my_skill_search_tool"],
  searchType: "ai_answers",
  query: t.input.userQuery,
  aiSearchProviders: "perplexity", // optional
});
```

Always use `searchType: 'ai_answers'`. External providers require API key configuration.

Verify before use: the `aiSearchProviders` values above (`'perplexity'`, `'openai'`, `'gemini'`, `'azure_openAI'`) show inconsistent casing (`azure_openAI` vs. the lowercase others). Confirm the exact enum value accepted by your instance before relying on any one of them verbatim.

API Key Required: External AI search providers require a valid API key configured on the instance. Navigate to Connection & Credential Aliases -> filter by application name `AI Websearch Open API alias` -> update the API credential record with your key. For Perplexity, the API key must be in format: `Bearer <api_key>`.

Outputs: `provider`, `response`, `error`, `errorcode`, `status`

## Skill-as-Tool

Use `t.Skill()` only when an existing published skill should be called as a tool. The target skill must be published first from the Skill Builder UI.

| Property | Required | Description |
| `$id` | Yes | Unique identifier for the tool record |
| `skillId` | Yes | Skill reference or capability sys_id |
| `inputs` | No | Input mappings array (uses `definitionAttributeId` instead of `name` ) |
| `outputs` | Yes | REQUIRED — output mappings with 5 mandatory fields |
| `depends` | No | Array of tools that must run first |
| `condition` | No | Conditional execution |

`skillId` accepts: `NowAssistSkillConfig` variable, `Now.ID['skill_name']`, `string` sys_id, `DbRecord<'sys_one_extend_capability'>`

### Mandatory 5 Output Fields

Every Skill tool must map all 5 outputs, each with a `definitionAttributeId`:

- `provider`

- `response`

- `error`

- `errorcode`

- `status`

Inputs format: Uses `{ definitionAttributeId, value }` only — no `$id` on Skill tool inputs (unlike Script/Subflow tool inputs).

### Response Chaining Between Skills

The `response` output of a Skill tool can be:

- Used in prompts: `${p.tool.CallHelper.response}`

- Passed as input to another tool: set `value: callHelper.response` in the next tool's `inputs`

- Chained with `depends`: ensure the dependent skill runs first

```
tools: (t) => {
  const skillA = t.Skill("SkillA", {
    $id: Now.ID["my_skill_a_tool"],
    skillId: "<skill_a_sys_id>",
    outputs: {
      provider: { definitionAttributeId: "<provider_sys_id>" },
      response: { definitionAttributeId: "<response_sys_id>" },
      error: { definitionAttributeId: "<error_sys_id>" },
      errorcode: { definitionAttributeId: "<errorcode_sys_id>" },
      status: { definitionAttributeId: "<status_sys_id>" },
    },
  });

  const skillB = t.Skill("SkillB", {
    $id: Now.ID["my_skill_b_tool"],
    skillId: "<skill_b_sys_id>",
    depends: [skillA],
    inputs: [
      {
        definitionAttributeId: "<skill_b_input_attr_sys_id>",
        value: skillA.response, // chain SkillA's response as SkillB's input
      },
    ],
    outputs: {
      provider: { definitionAttributeId: "<provider_sys_id>" },
      response: { definitionAttributeId: "<response_sys_id>" },
      error: { definitionAttributeId: "<error_sys_id>" },
      errorcode: { definitionAttributeId: "<errorcode_sys_id>" },
      status: { definitionAttributeId: "<status_sys_id>" },
    },
  });

  return { SkillA: skillA, SkillB: skillB };
};

// In prompt: ${p.tool.SkillB.response}
```

## Subflow and FlowAction Tools

No metadata exists in SDK. The user must provide details from a published and activated Subflow or FlowAction on the instance.

### Subflow Tool

| Property | Required | Description |
| `$id` | Yes | Unique identifier for the tool record |
| `$capabilityId` | Yes | Unique identifier for the tool's capability record |
| `subflowId` | Yes | Subflow sys_id, Subflow definition, or `Now.ID['subflow_name']` |
| `inputs` | No | Input mappings array (each requires `$id` , `name` , `value` , optional `type` ) |
| `outputs` | No | Output definitions array (each requires `$id` , `name` , optional `type` , `truncate` ) |
| `depends` | No | Array of tools that must run first |
| `condition` | No | Conditional execution |

`subflowId` accepts: Subflow definition, `Now.ID['subflow_name']`, or sys_id string

Input/output type (optional): Default is `'string'` for inputs, `'object'` for outputs.

#### Subflow Metadata (User Must Provide)

| Metadata | Table | Key Columns |
| Subflow record | `sys_hub_flow` | `sys_id` , `name` , `active` |
| Input definition | `sys_hub_flow_input` | `flow` (-> sys_hub_flow), `name` , `label` , `type` , `mandatory` |
| Output definition | `sys_hub_flow_output` | `flow` (-> sys_hub_flow), `name` , `label` , `type` , `is_array` |

### FlowAction Tool

| Property | Required | Description |
| `$id` | Yes | Unique identifier for the tool record |
| `$capabilityId` | Yes | Unique identifier for the tool's capability record |
| `actionId` | Yes | Flow action sys_id, Action definition, or `Now.ID['action_name']` |
| `inputs` | No | Input mappings array (each requires `$id` , `name` , `type` , `value` ) |
| `outputs` | No | Output definitions array (each requires `$id` , `name` , `type` , optional `truncate` ) |
| `depends` | No | Array of tools that must run first |
| `condition` | No | Conditional execution |

`actionId` accepts: Action definition, `Now.ID['action_name']`, or sys_id string

Input/output type (REQUIRED): FlowAction inputs and outputs MUST specify `type`.

#### FlowAction Metadata (User Must Provide)

| Metadata | Table | Key Columns |
| Action record | `sys_hub_action_type_definition` | `sys_id` , `name` , `active` |
| Input definition | `sys_hub_action_input` | `action_type` (-> action), `name` , `label` , `type` , `mandatory` |
| Output definition | `sys_hub_action_output` | `action_type` (-> action), `name` , `label` , `type` , `is_array` |

## Decision Node

Use `t.Decision()` for conditional branching based on tool outputs or skill inputs.

| Property | Required | Description |
| `$id` | Yes | Unique identifier for the tool record |
| `targets` | Yes | Array of target tool names (as const) |
| `branches` | Yes | Function returning branch array |
| `default` | Yes | Function returning default target |
| `depends` | No | Array of tools that must run first |
| `condition` | No | Conditional execution |

```
const checkPriority = t.Decision("CheckPriority", {
  $id: Now.ID["skill_decision"],
  depends: [getData],
  targets: ["Escalate", "Standard"] as const,
  branches: (targets) => [
    {
      name: "Critical",
      to: targets.Escalate,
      condition: { field: getData.priority, operator: "is", value: "1" },
    },
  ],
  default: (targets) => targets.Standard,
});
```

### Branch Condition Details

Each branch condition is an object with three fields:

- `field` — A `ToolOutputRef` or `SkillInputRef` (e.g., `getData.isPriority1` or `t.input.flag`)

- `operator` — `'is'` or `'is not'` only

- `value` — A plain string (e.g., `"1"`, `"true"`)

For complex conditions that cannot be expressed with `is` / `is not`, use the tool-level `condition` property with a script instead of a Decision node.

## Tool Chaining

Use the `depends` property to define execution order between tools:

- No `depends` — tool runs first (no prerequisites)

- `depends: [previousTool]` — runs after `previousTool` completes

- `depends: [tool1, tool2]` — runs after both `tool1` and `tool2` complete

```
const searchWeb = t.WebSearch("SearchWeb", {
  $id: Now.ID["search_tool"],
  searchType: "ai_answers",
  query: getIncident.output,
  depends: [getIncident],
});
```

### Tool Return Statement

Always use explicit property assignment — do NOT use shorthand syntax.

```
// CORRECT
return {
  GenerateSchedule: generateSchedule,
  FetchData: fetchData,
};

// WRONG — shorthand syntax breaks tool resolution
// return { GenerateSchedule, FetchData };
```

## Script Guidelines

Rules for writing scripts used in `t.Script()` and `t.InlineScript()` tools.

### Glide APIs Are Global

`gs`, `GlideRecord`, `GlideAggregate`, `GlideDateTime`, `GlideDuration`, `GlideUser` — all globally available. Never import them.

### Input Parsing

All tool inputs arrive as strings. Parse before use:

| Type | Parse Method |
| Number | `parseInt(input, 10)` or `parseFloat()` |
| JSON | `JSON.parse(input)` in try-catch |
| Boolean | `input === 'true'` |

### Scoped App Compatibility

Using Glide methods that are NOT supported in scoped applications will cause skill execution failure.

Before using any Glide API method, verify the method is supported in scoped applications.

| Not Supported (Causes Failure) | Use Instead (Scoped-Compatible) |
| `gs.dateDiff()` | `GlideDateTime.subtract()` |
| `GlideTableDescriptor` | Not available in scoped apps |
| `GlideDuration` | Verify availability — may be missing from global API in scoped contexts |
| `GlideUser` | Verify availability — may be missing from global API in scoped contexts |

### Valid API Methods

| Does Not Exist | Correct Alternative |
| `gr.newQuery()` | `gr.addQuery()` + `.addOrCondition()` for OR conditions |

### Error Handling

Return `{ error: 'message' }` for failures. Log details with `gs.error()`. Always use try-catch:

```
script: `(function(context) {
    try {
        var gr = new GlideRecord('incident');
        gr.addQuery('number', context.getValue('incident_number'));
        gr.query();
        if (gr.next()) {
            return { result: gr.getValue('short_description') };
        }
        return { error: 'Record not found' };
    } catch (e) {
        gs.error('Tool script failed: ' + e.message);
        return { error: 'Script execution failed: ' + e.message };
    }
})(context)`;
```

### Custom Table Validation

GATE: Do NOT write scripts referencing custom tables (`x_*`, `u_*`) until table existence and schema are verified.

Before writing any script that queries a custom table:

- Verify the table exists:

```
now-sdk query sys_db_object -q 'name=<table_name>' -f 'name,sys_id' -o json
```

- If the table does NOT exist — STOP. Do not proceed with script creation

- If the table exists — discover actual field names from the schema:

```
now-sdk query sys_dictionary -q 'name=<table_name>^internal_type!=collection' -f 'element,internal_type,column_label' -o json
```

Use the `element` values as column names in your GlideRecord queries. Never assume or invent column names.

- Query the table for at least one real record for `testValues`

In-script defensive pattern (runtime fallback):

```
script: `(function(context) {
    var tableName = 'x_custom_app_table';
    var gr = new GlideRecord(tableName);
    if (!gr.isValid()) {
        return { error: 'Table ' + tableName + ' does not exist on this instance' };
    }
    // ... rest of query
})(context)`;
```

This runtime check is a fallback only. Always validate tables before generating code — do not rely on runtime errors.

### Custom Table Creation Workflow

When the skill needs a table that doesn't yet exist:

- Create the table using the Table API or `now-sdk init` scaffolding

- Add columns with appropriate types (string, integer, reference, etc.)

- Insert test records — NEVER create a table without also creating test data

- Build and install — deploy the table to the instance

- Only then write the skill that references the table

This workflow ensures that `testValues` can reference real records and the skill can be tested end-to-end immediately.

## Anti-Patterns

Common tool mistakes that cause build or runtime failures:

| User Request | Wrong Approach | Correct Approach |
| "Search my custom table" | `t.WebSearch()` on internal table | `t.InlineScript()` with GlideRecord |
| "Search KB articles" | `t.WebSearch()` | `t.InlineScript()` querying `kb_knowledge` table |
| "Semantic search on records" | Invent `t.SemanticSearch()` | `t.InlineScript()` with LIKE/CONTAINS queries |
| "Vector similarity search" | Fabricate vector API | GlideRecord keyword queries; state limitation to user |
| "Query across multiple tables" | Single tool with JOIN | Chain multiple `t.InlineScript()` tools using `depends` |
| "Single table, no calculations" | `t.Script()` or `t.InlineScript()` | Use `glide_record` input — no tool needed, access fields directly in prompt via `p.input.record.field` |
| "Use record data in tool" | `glide_record` input + tool access | Use `string` input (sys_id/number), query with GlideRecord in tool — `glide_record` inputs are NOT accessible in tools |

## Related

- nowassist-skills-guide — Skill structure, inputs, outputs, prompts, and end-to-end examples

- nowassist-skills-advanced-guide — Multi-step skills, conditional logic, and complex patterns

- See the `developing-apps-guide` topic for project setup, authentication, and build workflow

Version: 4.14.0

# AI Skills Guide

Create and configure AI Skills using the `NowAssistSkillConfig` API in the Fluent SDK. Skills use configured prompts to generate AI responses from an LLM, optionally enriched by inputs and tools (script, inline script, web search, subflows, flow actions, decision branches). This guide covers skill structure, inputs, prompts, deployment, and naming conventions. Requires SDK 4.6.0 or higher.

Branding note: "Now Assist" has been rebranded to "ServiceNow Otto." These names refer to the same product. All technical identifiers (table names, field names, string literals like "Now Assist Panel", `now_assist_deployment`) remain unchanged — use them exactly as-is in code.

[NEVER] ANTI-PATTERN: Do NOT create direct LLM integrations using `sn_generative_ai.LLMClient`, Script Includes, or GlideAjax for AI/summarization features. When a user asks to summarize records, generate text, classify data, or add any AI/LLM capability, ALWAYS create a NowAssist Skill using `NowAssistSkillConfig`. Direct LLM calls bypass skill governance, security controls, prompt management, and the Skill Builder UI.

## When to Use

- Creating or modifying AI Skills using `NowAssistSkillConfig`

- Adding or modifying skill prompts, inputs, or security controls

- Adding or modifying skill tools (script, inline script, web search, subflows, flow actions, skill-as-tool, decision branches)

- Configuring skill deployment to UI Actions, Flow Actions, or ServiceNow Otto Panel

Related guides:

- See the `nowassist-skills-tools-guide` topic for tool configuration, script guidelines, and tool anti-patterns

- See the `nowassist-skills-advanced-guide` topic for provider/model discovery, security controls, URL construction, editing existing skills, validation rules, and troubleshooting

- See the `nowassistskillconfig-api` topic for complete API reference

## Creation Workflow (Mandatory Steps)

When creating a new skill, follow these steps in order. Steps marked [STOP] require user input — do NOT proceed until the user responds. Ask questions one at a time; do not batch them.

Shortcut for explicit requests: If the user's request already specifies answers (e.g., "create a skill that summarizes incidents, deploy as UI Action on incident table, accessible to itil users"), state your inferences and confirm in one pass: "Based on your request, I'll use: Provider — [queried default], Fields — [...], Security — itil roles, Deployment — UI Action on incident. Is that correct?" Then proceed without asking each `[STOP]` separately.

- Prerequisite check: Verify subscription/license (see Prerequisites below).

- Edit detection: Check if a skill already exists in the app scope (query `sn_nowassist_skill_config` where `sys_scope=<scope_sys_id>`). If found, read the existing `.now.ts` file and edit it — do NOT create a duplicate.

- Derive skill name: Analyze the user's request to identify the use case and derive a name (e.g., "summarize incidents" → "Incident Summarizer").

- Duplicate name check: Query `sn_nowassist_skill_config` where `sys_scope=<scope_sys_id>` AND `name=<derived_name>`. If found, inform the user and ask whether to proceed with a different name.

- [STOP] Provider/Model selection: Query the instance's approved providers (see `nowassist-skills-advanced-guide` topic's Provider and Model Configuration section — follow every step in order, including the approval check; skipping it can surface providers the instance steward has not approved). Present the numbered list to the user — never pre-select or recommend one. Wait for the user to choose. If user says "choose for me" or "you decide" — pick the first provider (alphabetical by its resolved display name, e.g. `gen_ai_provider`) from the approved list and confirm the choice before proceeding. Note: this auto-pick shortcut applies to provider selection only — it does NOT extend to the security questions in step 7, which must never be auto-decided.

- [STOP] Table column questions: For EACH table the skill will query, suggest relevant fields and ask the user to confirm or modify. Example: "I suggest these fields from `incident`: `number`, `short_description`, `description`, `priority`, `state`. Would you like to add or remove any?" Never proceed to write code until the user confirms the fields.

- [STOP] Security questions — ask TWO questions, one at a time:

- Q1 (userAccess): "Who should be able to invoke this skill? (1) All authenticated users — any logged-in user (2) Specific roles only — only users with designated roles." If user picks (2), follow up: "Which roles should have access? Please provide the role name(s)." This follow-up is a free-text question — do NOT present numbered options or suggest specific roles. Wait for response. These role names are used as-is in `userAccess.roles` — no sys_id lookup for this field (but see the advanced guide's UserAccess Role Format Verification note — this format has an unresolved inconsistency worth confirming before shipping).

- Q2 (roleRestrictions / roleMap): "What role(s) should the skill execute with? This determines the permissions the skill has when running scripts or querying data. Please provide the role name(s) you want to use." This is a free-text question — do NOT present numbered options or suggest specific roles. Let the user type their own role names. Wait for response. After receiving their answer, determine which field to populate: first run the table-existence check described in the `nowassist-skills-advanced-guide` topic's Determining Which to Use section (query whether `sys_agent_access_role_mapping` exists). If it exists, populate `roleMap` with the role names exactly as given — no sys_id lookup needed. If it does not exist, look up each role's sys_id from `sys_user_role` and populate `roleRestrictions` with those sys_ids.

- Never assume security defaults. If user says "choose for me" or "you decide" — re-ask with numbered options: "I need your input for compliance. Options: (1) All authenticated users, or (2) Specific roles like itil, admin. Which do you prefer?" (This differs deliberately from provider selection in step 5, which allows auto-pick — security decisions carry compliance risk and must always be explicit.)

- The `maint` role is NOT allowed; reject and ask for a different role. Warn (but allow) if user specifies `security_admin` — it grants broad privileges.

- See the `nowassist-skills-advanced-guide` topic for `roleMap` vs `roleRestrictions` selection logic and editing security on existing skills.

- [STOP] Deployment question: "Where should this skill be deployed? (1) UI Action — button on a record form (2) ServiceNow Otto Panel — chat panel (3) Flow Action — callable from Flow Designer (4) None — programmatic use only." Wait for response.

- If UI Action selected: Confirm the target table. Query `sys_db_object` where `name='<table>'` and verify `actions_access = true`. If `false`, inform the user and ask whether to enable it. Only create `deploymentSettings` after the gate passes.

- Query for test data: Query the relevant table(s) to get representative sample data for `testValues`. Auto-select the best record — do not ask the user to pick from a list. Select a record that has populated values for all fields the skill will reference; prefer records with state != closed/cancelled. Briefly inform the user which record was selected and why.

- Write the skill code: Create the `.now.ts` file in `src/fluent/now-assist-skills/`. Use the confirmed provider, fields, security, and deployment settings.

- Build and deploy: Run `now-sdk build && now-sdk install`. See the `developing-apps-guide` topic. This is not the end of the workflow — do not treat a successful build/install as task completion. Steps 13–14 (Skill URL) are still mandatory.

- [STOP] Post-deploy (UI Action only): The auto-generated UI Action shows raw JSON. You MUST update the script to format the response. See the `nowassist-skills-advanced-guide` topic for the post-deploy workflow. Not applicable to other deployments? Do NOT stop here — proceed to step 13, which is unconditional.

- Provide Skill URL (MANDATORY — NEVER SKIP, applies to EVERY deployment type): This step runs regardless of whether step 12 applied. After skill is created/installed, run the exact query chain in the `nowassist-skills-advanced-guide` topic's Post-Creation: Skill URL section (`## Post-Creation: Skill URL`) and provide the constructed URL. Do NOT mark the task complete without it, and do NOT improvise a different query chain here — the canonical, validated one lives in that section only, to avoid two copies drifting out of sync. All sys_ids must be real values from queries — never show placeholders. If any query in the chain returns zero results, follow that section's Handling Empty Results subsection — never silently drop the URL from your response without explanation.

- [GATE] Final self-check — run before your last message: Re-read your draft response. Does it contain EITHER (a) a URL matching `.../now-assist-skillkit/skill/<id>/params/prompt-id/<id>/config-id/<id>`, OR (b) an explicit statement naming which query in the chain failed and why the URL could not be constructed? If neither is present, you have silently skipped step 13 — STOP, go run the query chain (or its retry/disclosure rule) in `nowassist-skills-advanced-guide`'s Post-Creation: Skill URL section now, and only then respond. Never tell the user a skill is ready while omitting both the URL and a stated reason it's missing.

## Prerequisites

Before creating a skill, verify that the required subscription and license are available on the instance. This checks whether AppEngine or AI Platform Prime is active — a simple plugin table query cannot validate this.

Create a check script in your project:

```
// scripts/check-product.ts
import { Connector } from "@servicenow/sdk-api";

export default async ({ credential }) => {
  const connector = new Connector(credential);
  const response = await connector.fetch(
    "/api/sn_build_agent/build_agent_api/isProductAvailable",
    { method: "GET" },
    new URLSearchParams({ productId: "primeSKU", scopeName: "" }),
  );
  const body = await response.json();
  const available = body.result?.isAvailable === true;
  console.log(JSON.stringify({ available }));
  if (!available) {
    console.error(
      "ServiceNow Otto for App Engine is not available on this instance.",
    );
  }
};
```

```
now-sdk run check-product
```

If the product is not available, skill creation will fail. Contact your ServiceNow administrator to verify the subscription.

Also check for existing skills with similar names to avoid conflicts:

```
now-sdk query sn_nowassist_skill_config -q 'nameLIKE<skill_name>' -f 'sys_id,name' -o json
```

Warning: Creating a skill with a name similar to an existing one can cause confusion in the Skill Builder UI and may lead to incorrect skill selection at runtime.

### Resolving `<scope_sys_id>`

Steps 2 and 4 above, and the advanced guide's Post-Creation: Skill URL workflow, all reference `<scope_sys_id>` — the sys_id of the current application's `sys_scope` record. `sys_scope` is a reference field, so the scope name string will not work in these queries. Resolve it once per session and reuse the same value everywhere it's needed:

```
now-sdk query sys_scope -q 'scope=<app_scope_name>' -f 'sys_id,name,scope' -o json
```

Or read it directly from the project's `now.config.json` if already recorded there.

## File Location

ALL skill `.now.ts` files MUST be created inside `src/fluent/now-assist-skills/` folder. Never create skills in any other location.

## Skill Structure

`NowAssistSkillConfig(Arg 1: SkillDefinition, Arg 2: SkillPromptConfig)`

Data flow: Skills send prompts to an LLM to generate responses. Prompts can reference user inputs (`p.input.fieldName`) and tool outputs (`p.tool.ToolName.output`). Tools execute before the prompt, so their outputs are available when the prompt runs.

### API Structure

```
import { NowAssistSkillConfig } from '@servicenow/sdk/core'

NowAssistSkillConfig(
    // Arg 1: SkillDefinition
    {
        $id: Now.ID['skill_name'],
        name: string,
        description?: string,
        shortDescription?: string,
        inputs?: InputAttribute[],
        outputs?: OutputAttribute[],  // optional — 5 standard outputs auto-generated if omitted
        tools?: (t: ToolGraphBuilder) => ToolHandles | void,
        securityControls: SecurityControls,      // MANDATORY
        skillSettings?: SkillSettings,
        deploymentSettings?: DeploymentSettings
    },
    // Arg 2: SkillPromptConfig
    {
        providers: [{
            provider: 'Now LLM Service' | 'Azure OpenAI' | 'Open AI' | string,
            providerAPI?: { type: 'sys_hub_flow', id: string },
            prompts: [{
                name: string,
                versions: [{
                    $id: Now.ID['prompt_v1'],
                    model: string,
                    temperature?: number,
                    maxTokens?: number,
                    promptState: 'draft',
                    prompt: string | ((p: PromptBuilder) => string),
                    filterCondition?: { [inputName: string]: string }
                }]
            }]
        }]
    }
)
```

## Now.ID Key Naming Convention

IMPORTANT: The `Now` object (including `Now.ID`) is globally available when using `@servicenow/sdk/core`. You do NOT need to import it. All `$id` properties MUST use `Now.ID['key']` format, not plain strings.

All `Now.ID` keys MUST be unique and descriptive based on the actual skill/component name, NOT generic terms.

Format: `<skill_name>_<component_type>_<specific_name>`

### Rules

- Include the skill name as prefix for all components

- Add component type (input, tool, prompt, acl)

- Add specific identifier (purpose, version, name)

- Use snake_case for consistency

- Keep keys readable and self-documenting

### Naming Examples

| Component | GOOD | BAD |
| Skill | `Now.ID["incident_summarizer_skill"]` | `Now.ID["my_skill"]` |
| Input | `Now.ID["incident_summarizer_incident_input"]` | `Now.ID["input1"]` |
| Tool | `Now.ID["incident_summarizer_fetch_tool"]` | `Now.ID["tool"]` |
| Prompt | `Now.ID["incident_summarizer_main_prompt"]` | `Now.ID["prompt"]` |
| Security ACL | `Now.ID["incident_summarizer_user_access_acl"]` | `Now.ID["acl"]` |

Why: Generic keys like `Now.ID["my_skill"]` collide across skills in the same workspace. Descriptive keys enable traceability and support the `explicitId` mechanism when editing existing skills.

### Common Mistakes to Avoid

| Mistake | Correct |
| `Now.ID["skill"]` | `Now.ID["incident_summarizer_skill"]` |
| `Now.ID["input1"]` | `Now.ID["incident_summarizer_incident_input"]` |
| `Now.ID["tool"]` | `Now.ID["incident_summarizer_fetch_tool"]` |
| `Now.ID["prompt"]` | `Now.ID["incident_summarizer_main_prompt"]` |
| `Now.ID["acl"]` | `Now.ID["incident_summarizer_user_access_acl"]` |

Best Practices: Derive from skill name, be specific, stay consistent, avoid abbreviations (use `incident` not `inc`), document intent with inline comments.

## Input Attributes

| Property | Required | Description |
| `$id` | Yes | Unique identifier |
| `name` | Yes | Attribute name (use spaces for readability, no underscores or special characters) |
| `description` | No | Description of the input attribute |
| `dataType` | Yes | `'string'` , `'numeric'` , `'boolean'` , `'glide_record'` , `'simple_array'` , `'json_object'` , `'json_array'` |
| `mandatory` | No | Whether input is required (default: `false` ) |
| `truncate` | No | Whether to truncate the value (only valid for: `string` , `numeric` , `boolean` , `glide_record` ; NOT supported for: `simple_array` , `json_object` , `json_array` ) |
| `testValues` | No | Values for testing and validation |
| `tableName` | Conditional | Required when using `glide_record` dataType |
| `tableSysId` | Conditional | Required when `testValues` is provided for `glide_record` type — this is the sys_id of the test record |

Constraint: A skill can have at most one input of type `glide_record`.

### Referencing Inputs in Prompts

Name conversion: Input names with spaces convert to underscores. `"Incident Number"` becomes `{{incident_number}}` in prompts.

| Input Name Format | Correct Syntax | Wrong Syntax |
| With spaces | `${p.input['shift requirement']}` | `${p.input.shift requirement}` |
| Without spaces | `${p.input.incidentNumber}` | N/A |
| Conditional logic | `${p.input['shift requirement'] === 'Morning' ? 'Yes' : 'No'}` | N/A |
| glide_record | `{{incident_record.number}}` | `${p.input['Incident Record'].number}` |

glide_record inputs: For `glide_record` data types, use `{{input_name.field_name}}` format where input name converts to snake_case. Example: If input name is `"Incident Record"`, use `{{incident_record.number}}`, `{{incident_record.short_description}}`.

Input referencing key rules:

- Input definitions — spaces allowed and encouraged for readability

- Prompts with spaces — use bracket notation `${p.input['input name']}`

- Prompts without spaces — use dot notation `${p.input.inputName}`

- InlineScript — convert spaces to underscores `context.getValue('input_name')`

- Script tool — use bracket notation for value `t.input['input name']`

### glide_record vs Tools

Use `glide_record` input (preferred) when:

- Single table query

- No calculations or transformations needed

- No tools need access to the record data

Use tools with `string` input type when:

- Multiple tables or joins needed

- Calculations or transformations required

- Record data needed inside a tool script

Critical: `glide_record` inputs are NOT accessible inside tools. They can only be referenced in prompts via `{{record_name.field_name}}`.

### testValues Selection

Populate `testValues` with real, representative data from the instance. Selection criteria by input type:

| Input Type | Selection Criteria |
| `string` (record identifiers) | Use an actual record number (e.g., `"INC0010001"` ) from a real incident |
| `string` (free text) | Use realistic text matching the use case |
| `glide_record` | Provide `tableSysId` (the sys_id of a real test record). Query the table first to find one |
| `numeric` | Use a realistic value within expected range |
| `boolean` | Use `"true"` or `"false"` |

DO: Use real record numbers, real sys_ids from the instance, realistic descriptions.
DON'T: Use placeholders like `"test"`, `"12345"`, `"xxx"`. These produce low-quality prompt testing.

## Output Attributes

Do NOT define custom outputs. The platform automatically creates five default outputs: `response`, `confidence`, `explanation`, `metadata`, `citations`. Reference them in prompts with `${p.output.response}`.

## Tool Configuration

For complete tool documentation, see the `nowassist-skills-tools-guide` topic. Quick reference:

| Method | Purpose |
| `t.Script()` | Reference Script Include |
| `t.InlineScript()` | Inline script function |
| `t.WebSearch()` | Web search (AI answers) |
| `t.Skill()` | Call another skill |
| `t.Subflow()` | Execute Flow Designer subflow |
| `t.FlowAction()` | Execute Flow Designer action |
| `t.Decision()` | Conditional branching |

## Prompt Configuration

### Mandatory 4-Section Structure

```
## Role
You are a [specialist type]. Your task is to [objective].

## Context
The user's [input]: '{{input_name}}'
Tool output: '${p.tool.ToolName.output}'

## Instructions
1. [First step]
2. [Second step]
3. [Constraints]

## Output
The output should be [format]. It must be [qualities].
```

### Prompt Versions

| Property | Required | Description |
| `$id` | Yes | Unique identifier |
| `model` | Yes | Always `'llm_generic_small_v2'` for Now LLM Service |
| `promptState` | Yes | Always `'draft'` — other values cause validation errors before publishing |
| `prompt` | Yes | Text or builder function `(p) => string` |
| `temperature` | No | 0.0-1.0 (default: `0.2` ) |
| `maxTokens` | No | Required for non-Now LLM providers |
| `filterCondition` | No | Per-version usage conditions |

Static prompt alternative: `prompt: 'Query: {{user_query}}'` — string-based prompts without the builder function.

No array indexing in prompts: `${p.tool.Tool.output.items[0].field}` causes regex timeout. Flatten arrays in tool scripts before referencing in prompts.

### Type-Safe Prompt Builder

```
prompt: (p) => `## Role
You are an incident specialist.

## Context
Incident details: ${p.tool.GetIncident.output}

## Instructions
1. Review the incident data.
2. Provide actionable recommendations.

## Output
Provide a structured analysis with Summary, Root Cause, and Recommendations.`;
```

### maxTokens Guidelines

| Output Type | Recommended `maxTokens` |
| Short answers (yes/no, category) | 100-200 |
| Brief summaries | 300-500 |
| Formatted reports | 1000-2000 |

Warning: Setting `maxTokens` too low for formatted output forces raw JSON responses.

### Model Suggestions Per Provider

| Provider | Model |
| Now LLM Service / Now LLM Generic | `'llm_generic_small_v2'` |
| Azure OpenAI | `'gpt-4'` , `'gpt-4o-mini'` , `'gpt_large'` |
| Open AI | `'gpt-4'` , `'gpt-4o-mini'` |
| Google Gemini | `'gemini-pro'` , `'gemini_large'` |
| AWS Claude | `'claude_large'` |
| IBM Watson | `'ibm/granite-13b-chat-v2'` |

Reference only — do not hardcode. These are illustrative examples of valid model strings, not a guarantee of availability on any given instance. Always confirm the actual model id via the query workflow in the `nowassist-skills-advanced-guide` topic (Step 2: query `sys_generative_ai_model_config`) before writing it into skill code.

### Conditional Prompts (filterCondition)

```
versions: [
  {
    $id: Now.ID["prompt_high"],
    model: "llm_generic_small_v2",
    promptState: "draft",
    prompt: (p) => `High priority analysis: ${p.input.description}`,
    filterCondition: { priority: "1" },
  },
  {
    $id: Now.ID["prompt_default"],
    model: "llm_generic_small_v2",
    promptState: "draft",
    prompt: (p) => `Standard analysis: ${p.input.description}`,
  },
];
```

Keys must exactly match input attribute names (case-sensitive, including spaces).

## Deployment Settings

For advanced deployment configuration (UI Action validation, post-deploy formatting, NAP advanced mode), see the `nowassist-skills-advanced-guide` topic.

| Channel | Configuration | When to Use |
| UI Action | `uiAction: { $id: Now.ID['...'], table: 'incident' }` | Button on record form |
| NAP | `nowAssistPanel: { enabled: true, roles?: ['now_assist_panel_user'] }` | ServiceNow Otto chat panel |
| NAP (advanced) | `nowAssistPanel: { enabled: true, conditionMode: 'advanced', conditionScript?: '...' }` | NAP with custom applicability |
| Flow | `flowAction: true` | Call from Flow Designer |
| Skill Family | `skillFamily: '<sys_id>'` or `Record({ table: 'sn_nowassist_skill_family', data: {...} })` | Associate with skill family |
| None | Omit `deploymentSettings` | Programmatic use only |

```
deploymentSettings: {
    uiAction: { $id: Now.ID['my_skill_uiaction'], table: 'incident' },
    nowAssistPanel: {
        enabled: true,
        roles: ['now_assist_panel_user']
    }
}
```

UI Actions on base tables appear on extended tables.

[CRITICAL] POST-DEPLOY REQUIRED for UI Action: The auto-generated UI Action shows raw JSON. You MUST update the script after first install to format the response. See the `nowassist-skills-advanced-guide` topic for the full post-deploy workflow.

## Skill Settings (Pre/Post Processors)

Naming note: `skillSettings.providers` is unrelated to the top-level `providers` array in Arg 2 (the LLM provider/prompt configuration). Despite the shared field name, this is a separate list of pre/post-processor definitions — do not merge or confuse the two.

CONSTRAINT: Each provider entry must have EITHER `preprocessor` OR `postprocessor` — not both. To use both, create two separate provider entries.

```
skillSettings: {
  providers: [
    {
      $id: Now.ID["skill_preprocessor"],
      name: "TestPreProcessor",
      preprocessor: `(function(payload) {
            payload.timestamp = new Date().toISOString();
            return payload;
        })(payload);`,
    },
    {
      $id: Now.ID["skill_postprocessor"],
      name: "TestPostProcessor",
      postprocessor: `(function(payload) {
            if (payload.response) {
                payload.formatted = payload.response.trim();
            }
            return payload;
        })(payload);`,
    },
  ];
}
```

Format: IIFE — `(function(payload) { return payload; })(payload);`

| Pre-Processor Use Cases | Post-Processor Use Cases |
| Format dates, inject metadata | Extract JSON fields, parse responses |
| Normalize/standardize data | Error handling/detection |
| Validate/sanitize inputs | Format to required output structure |

DO: Keep scripts simple, always return payload, use try-catch, test thoroughly.
DON'T: Database operations (use tools instead), complex logic, modify global state.

| Processor Problem | Solution |
| Processor not executing | Verify IIFE format wrapping |
| Payload not modified | Ensure payload is returned from function |
| JSON parse errors | Add try-catch with fallback |

## Security Controls

For complete security documentation including `userAccess`, `roleRestrictions`, `roleMap`, examples, and editing security on existing skills, see the `nowassist-skills-advanced-guide` topic.

Quick reference — security controls are mandatory:

```
securityControls: {
    userAccess: {
        $id: Now.ID['skill_user_access'],  // $id is CRITICAL — missing $id causes sync errors
        type: 'authenticated',
    },
    roleMap: ['admin', 'itil'],  // Use roleMap for ZP10+ (name-based, preferred)
}
```

## Complete Example

```
import { NowAssistSkillConfig } from "@servicenow/sdk/core";

export const incidentAnalyzer = NowAssistSkillConfig(
  {
    $id: Now.ID["incident_analyzer_skill"],
    name: "Incident Analyzer",
    inputs: [
      {
        $id: Now.ID["incident_analyzer_number_input"],
        name: "incident number",
        mandatory: true,
        dataType: "string",
        testValues: "INC0010001",
      },
    ],
    tools: (t) => {
      const getIncident = t.InlineScript("GetIncident", {
        $id: Now.ID["incident_analyzer_getincident_tool"],
        script: `(function(context) {
                    var gr = new GlideRecord('incident');
                    gr.addQuery('number', context.getValue('incident_number'));
                    gr.query();
                    if (gr.next()) {
                        return {
                            number: gr.getValue('number'),
                            short_description: gr.getValue('short_description'),
                            priority: gr.getValue('priority')
                        };
                    }
                    return { error: 'Incident not found' };
                })(context)`,
      });
      return { GetIncident: getIncident };
    },
    securityControls: {
      userAccess: {
        $id: Now.ID["incident_analyzer_user_access"],
        type: "roles",
        roles: ["itil"],
      },
      roleRestrictions: ["<ROLE_SYS_ID>"],
    },
    deploymentSettings: {
      uiAction: {
        $id: Now.ID["incident_analyzer_uiaction"],
        table: "incident",
      },
      nowAssistPanel: {
        enabled: true,
        roles: ["now_assist_panel_user"],
      },
    },
  },
  {
    providers: [
      {
        provider: "Now LLM Service",
        prompts: [
          {
            name: "Analyze",
            versions: [
              {
                $id: Now.ID["incident_analyzer_prompt_v1"],
                model: "llm_generic_small_v2",
                promptState: "draft",
                prompt: (p) => `## Role
You are an incident analysis specialist.

## Context
Incident details: ${p.tool.GetIncident.output}

## Instructions
1. Review the incident number, description, and priority.
2. Identify root cause based on available information.
3. Provide actionable recommendations.

## Output
**Summary:** [Brief overview]
**Root Cause:** [Identified cause or 'Requires investigation']
**Recommendations:** [Numbered action items]`,
              },
            ],
          },
        ],
      },
    ],
  },
);
```

## Related

- See the `nowassist-skills-tools-guide` topic for tool configuration, script guidelines, and anti-patterns

- See the `nowassist-skills-advanced-guide` topic for provider/model discovery, security controls, URL construction, editing skills, validation rules, and troubleshooting

- See the `nowassistskillconfig-api` topic for complete API reference

- See the `developing-apps-guide` topic for project setup, authentication, and build workflow

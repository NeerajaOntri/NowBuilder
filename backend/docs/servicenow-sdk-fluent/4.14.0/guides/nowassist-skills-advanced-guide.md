Version: 4.14.0

# AI Skills — Advanced Guide

Advanced configuration for AI Skills: provider and model discovery, security controls, deployment options, skill URL construction, validation rules, and troubleshooting. Read the companion AI Skills Guide for core concepts (inputs, tools, prompts, complete examples).

## Provider and Model Configuration

### 3-Level Hierarchy

The GenAI configuration follows a 3-level structure:

- Provider (e.g., "Now LLM Service", "Azure OpenAI", "AWS Claude")

- Provider API (e.g., "Now LLM Generic", "Chat Completions", "Amazon Bedrock Chat Completions")

- Model (e.g., `llm_generic_small_v2`, `gpt-4o`, `claude_large`)

### Querying Available Providers

Follow every step below in order — including the approval check (Step 1c) — before presenting any provider list. Skipping Step 1c can surface providers the instance steward has not approved. Present all approved providers and let the user choose — never pre-select or recommend a provider.

Step 1 — Query provider mappings:

```
now-sdk query sys_generative_ai_provider_mapping -q 'external=true' -f 'sys_id,provider,provider_api,provider_implementation,gen_ai_provider' -o json
```

- `provider` is the mapping name (NOT the UI display name).

- `gen_ai_provider` is a reference sys_id pointing to `sys_gen_ai_provider`.

- `provider_implementation` is the flow sys_id used in `providerAPI.id`.

Step 1b — Resolve provider display names (mandatory):

For each unique `gen_ai_provider` sys_id from Step 1:

```
now-sdk query sys_gen_ai_provider -q 'sys_id=<gen_ai_provider_sys_id>' -f 'gen_ai_provider,integration_type' -o json
```

The `gen_ai_provider` field on `sys_gen_ai_provider` is the source of truth for the provider name used in code and shown to users.

| Mapping name ( `sys_generative_ai_provider_mapping.provider` ) | Display name ( `sys_gen_ai_provider.gen_ai_provider` ) |
| `Now LLM Generic` | `Now LLM Service` |
| `Amazon Bedrock` | `AWS Claude` |
| `Google Cloud AI Studio` | `Google Gemini` |
| `Azure OpenAI` / `Azure AI serverless` | `Azure OpenAI` |
| `OpenAI` | `Open AI` |
| `IBM watsonx` | `IBM Watson` |
| `Custom LLM` | `Custom LLM Provider` |
| `Perplexity AI Websearch` | `Perplexity` |

### Step 1c — Approval Checking (Two-Tier)

Only providers approved by the instance steward may be presented to users.

Tier 1 — Steward override (check first):

```
now-sdk query sys_gen_ai_routing_selection -f 'selected_providers,selected_routing,fallback' -o json
```

If a row exists and `selected_providers` is non-empty, this is the authoritative approved list — skip Tier 2.

Tier 2 — Instance default (only if Tier 1 has no row):

```
now-sdk query sys_gen_ai_provider_routing -q 'default=true' -f 'supported_providers,routing,region' -o json
```

If multiple `default=true` rows share the same `routing` value, take the intersection of `supported_providers` — a provider must appear in every row to be approved.

Step 2 — Query models per provider API:

```
now-sdk query sys_generative_ai_model_config -q 'provider=<mapping_sys_id>^active=true^lifecycle_state=active^usage_mode!=restricted' -f 'model,model_display_name,max_tokens' -o json
```

Run a separate query for each mapping from Step 1. Do NOT use the `model_configs` field from the mapping — it may be stale.

Step 3 — Filter: Remove providers that are either not approved (per Step 1c above) or have zero models (Step 2). Only providers that are both approved AND have at least one model may be shown.

### Field Mappings

| What You Need | Table | Column | Code Property |
| Provider name (UI/code) | `sys_gen_ai_provider` | `gen_ai_provider` | `provider` key |
| Provider API flow | `sys_generative_ai_provider_mapping` | `provider_implementation` | `providerAPI.id` |
| Provider API type | — | — | `providerAPI.type` (always `"sys_hub_flow"` ) |
| Model identifier | `sys_generative_ai_model_config` | `model` | `model` |
| Model display name | `sys_generative_ai_model_config` | `model_display_name` | Display only |
| Provider grouping | `sys_gen_ai_provider` | `integration_type` | Grouping only (OEM vs BYOK) |

`providerAPI` is optional when `provider_implementation` is missing from the query result — omit the entire `providerAPI` object and the build will auto-add it.

No static provider list here. The mapping table in Step 1b above is illustrative only. Always query the instance (Steps 1–3) for actual availability — never assume a provider is available without querying.

### Code Example

```
providers: [
  {
    provider: "AWS Claude", // from sys_gen_ai_provider.gen_ai_provider
    providerAPI: {
      type: "sys_hub_flow",
      id: "52f46aeb9f2c5210da502fca9a0a1cda", // from provider_implementation (optional)
    },
    prompts: [
      {
        name: "Main Prompt",
        versions: [
          {
            $id: Now.ID["my_skill_prompt_v1"],
            model: "claude_large", // from sys_generative_ai_model_config.model
            promptState: "draft",
            prompt: (p) => `/* prompt content */`,
          },
        ],
      },
    ],
  },
];
```

## Security Controls

### userAccess

| Type | Configuration | Use Case |
| Authenticated | `{ $id: Now.ID['ua'], type: 'authenticated' }` | General, non-sensitive |
| Role-Based | `{ $id: Now.ID['ua'], type: 'roles', roles: ['itil'] }` | Sensitive data |

`$id` is required on `userAccess`. Missing `$id` causes sync errors that reset `userAccess` to defaults (see UserAccess Sync Error Recovery).

The `maint` role is never allowed — reject it and ask for a different role.

#### UserAccess Role Format Verification

⚠️ Unresolved inconsistency — verify against the platform schema before relying on this field. The Role-Based example above uses role names (`roles: ['itil']`), matching the Complete Example in the `nowassist-skills-guide` topic. However, the UserAccess Sync Error Recovery workflow below reconstructs `userAccess.roles` using sys_ids (`roles: ['<role_sys_id_1>', ...]`). These cannot both be correct. Until confirmed against a real instance or the `NowAssistSkillConfig` type definitions, treat role names as the default — it matches the majority of examples in this guide — but validate the actual accepted format before shipping a skill that depends on it.

### roleRestrictions and roleMap

| Field | Accepts | Maps to | Use when |
| `roleRestrictions` | role sys_ids , `Role` objects, or `DbRecord<'sys_user_role'>` | `sys_agent_access_role_configuration.role_list` (legacy glide_list) | Pre-ZP10 instances, or sys_ids match across targets |
| `roleMap` | role names , `Role()` objects, or `DbRecord<'sys_user_role'>` | `sys_agent_access_role_mapping` (M2M reference table) | ZP10 / AP3+ — preferred for cross-instance portability |

At least one must be non-empty — build fails if both are absent.

### Determining Which to Use

Query `sys_db_object` to check if the new M2M table exists:

```
now-sdk query sys_db_object -q 'name=sys_agent_access_role_mapping' -f 'name' -o json
```

| Result | Use | Storage |
| Record found (table exists) | `roleMap` | Role NAME strings |
| No record (table missing) | `roleRestrictions` | Role SYS_IDS (look up from `sys_user_role` ) |

### Security Control Examples

Example 1 — Name-based (recommended for ZP10+):

```
securityControls: {
    userAccess: { $id: Now.ID['skill_user_access'], type: 'authenticated' },
    roleMap: ['admin', 'itil'],
}
```

Example 2 — sys_id-based (legacy / pre-ZP10):

```
securityControls: {
    userAccess: { $id: Now.ID['skill_user_access'], type: 'roles', roles: ['itil'] },
    roleRestrictions: ['282bf1fac6112285017366cb5f867469'],
}
```

Example 3 — Both fields (migration window):

```
securityControls: {
    userAccess: { $id: Now.ID['ua'], type: 'authenticated' },
    roleRestrictions: ['2831a114c611228501d4ea6c309d626d'], // works on pre-ZP10
    roleMap: ['itil'],                                       // works cross-instance on ZP10+
}
```

### Editing Security on Existing Skills

When adding roles to an existing skill:

- Run the table-existence check first.

- If table exists — do NOT touch existing `roleRestrictions`. Add new roles only to `roleMap` using name strings. Create the `roleMap` property if absent.

- If table missing — add role sys_ids to `roleRestrictions`. Look up sys_ids from `sys_user_role`.

- Never remove or migrate existing `roleRestrictions` entries. Never add sys_ids to `roleMap`.

### Security Troubleshooting

| Problem | Solution |
| Skill not appearing for user | Verify user has role in `userAccess.roles` |
| `roleRestrictions must contain only role sys_ids` | Replace role names with sys_ids from `sys_user_role` |
| `roleMap must contain role names, not sys_ids` | Replace sys_id strings with role names |
| `must have at least one of roleRestrictions or roleMap` | Populate at least one field |
| `roleMap` install failure / table-not-found | Instance lacks `sys_agent_access_role_mapping` — switch to `roleRestrictions` or upgrade |

## Deployment Configuration

### Deployment Options

| Channel | Configuration | When to Use |
| UI Action | `uiAction: { $id: Now.ID['skill_uiaction'], table: 'incident' }` | Button on record form |
| ServiceNow Otto Panel | `nowAssistPanel: { enabled: true }` | Chat interface |
| Flow Action | `flowAction: true` | Flow Designer integration |
| None | Omit `deploymentSettings` | Programmatic only |

### UI Action — actions_access Validation

Before using a table for `uiAction`, verify it supports UI Actions:

```
now-sdk query sys_db_object -q 'name=<table_name>' -f 'name,actions_access' -o json
```

If `actions_access` is `false`, the table cannot have UI Actions until enabled. Update the record or choose a different deployment channel.

### UIActionConfig Properties

| Property | Required | Description |
| `$id` | Yes | Unique identifier `Now.ID['skill_uiaction']` |
| `table` | Yes | Target table (e.g., `'incident'` ) |
| `script` | No | Script that invokes the skill (auto-generated on first install; update post-deploy for formatting) |

### Inline UI Action Auto-Generation

Pass only `$id` and `table` — everything else is auto-generated:

```
deploymentSettings: {
    uiAction: { $id: Now.ID['my_skill_uiaction'], table: 'incident' }
}
```

Auto-generation creates:

- `sys_ui_action` record with skill invocation script

- `sys_ux_form_action` record for UI compatibility

- Condition checking if skill is active

- Auto-mapped inputs from prompt configuration

### UI Action Response Formatting (Post-Deploy)

The auto-generated script displays raw JSON via `gs.addInfoMessage(JSON.stringify(skillResponse))`. After the first install, replace that line with:

```
var displayText = "";
if (
  skillResponse &&
  typeof skillResponse === "object" &&
  skillResponse.hasOwnProperty("model_output")
) {
  displayText = String(skillResponse.model_output || "");
} else if (typeof skillResponse === "string") {
  try {
    var parsed = JSON.parse(skillResponse);
    if (
      parsed &&
      typeof parsed === "object" &&
      parsed.hasOwnProperty("model_output")
    ) {
      displayText = String(parsed.model_output || "");
    } else {
      displayText = skillResponse;
    }
  } catch (pe) {
    displayText = skillResponse;
  }
} else {
  displayText = JSON.stringify(skillResponse);
}
displayText = displayText
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;");
displayText = displayText.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
displayText = displayText.replace(
  /(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g,
  "<i>$1</i>",
);
displayText = displayText.replace(/\n/g, "<br/>");
gs.addInfoMessage(displayText);
```

Post-deploy workflow:

- Query the generated UI Action: `now-sdk query sys_ui_action -q 'sys_scope=<scope>^name=<skill_name>' -f 'sys_id,script' -o json`

- Replace the `gs.addInfoMessage(JSON.stringify(skillResponse))` line with the block above

- Add the full modified script to `deploymentSettings.uiAction.script` in your Fluent code

- Rebuild — the formatted script is now baked into the definition

### NAP Configuration

Simple mode (default) — roles-based filtering:

```
deploymentSettings: {
    nowAssistPanel: {
        enabled: true,
        // roles optional — defaults to ['now_assist_panel_user']
        roles: ['now_assist_panel_user', 'access_analyzer_ai_user'],
    },
}
```

Advanced mode — custom condition script:

```
deploymentSettings: {
    nowAssistPanel: {
        enabled: true,
        conditionMode: 'advanced',
        conditionScript: `(function executeCondition(/* glide record */ current) {
            return current.getValue('priority') === '1';
        })(current);`,
    },
}
```

| Mode | `roles` omitted | `roles` provided |
| `simple` (default) | Defaults to `'now_assist_panel_user'` | Uses provided roles |
| `advanced` | Left empty — `conditionScript` governs access | Uses provided roles |

`conditionScript` is optional in advanced mode — a default template is used if omitted. Providing `conditionScript` without `conditionMode: 'advanced'` causes a build error.

### NAP vs UI Action Decision Guide

| Aspect | NAP (Otto Panel) | UI Action |
| Access point | Chat interface | Form button |
| Record context | Optional / explicit | Automatic |
| Interaction | Multi-turn | Single invocation |
| Scope | Global | Table-specific |

## Editing Existing Skills

### Edit Workflow

- Read the existing `.now.ts` file in `src/fluent/now-assist-skills/`

- Identify what needs to change

- Preserve unchanged configuration

- Update `testValues` if inputs changed

- Build, install, and verify

### ExplicitId Mechanism

When editing a skill that has no source `.now.ts` file (e.g., created via UI):

- Query `sys_one_extend_capability` for the skill's sys_id

- Query `sn_nowassist_skill_config` for the full configuration

- Create `NowAssistSkillConfig` using `$id: Now.ID['<actual_sys_id>']` from step 1

- Build and install — the `explicitId` mechanism binds to the existing record without creating a duplicate

### Change Impact Matrix

| Change | Also Update |
| Add input | Update `testValues` , update prompts to reference new input |
| Remove input | Remove all prompt references, check tool dependencies |
| Add tool | Update prompts, add to `return` statement in tools callback |
| Change provider/model | Verify availability, may need prompt adjustments |
| Change `userAccess` | If switching to `roles` , provide role names (matches the Role-Based example — but see the UserAccess Role Format Verification note above, which flags this as unresolved) |

## Post-Creation: Skill URL

### Query Workflow

After creating a skill, query the required sys_ids to construct the Skill Builder URL.

1. Get instance name:

```
now-sdk query sys_properties -q 'name=instance_name' -f 'value' -o json
```

Steps 2–5 below reuse `<scope_sys_id>` — the sys_id of the app's `sys_scope` record (see the `nowassist-skills-guide` topic's Resolving `<scope_sys_id>` note). `sys_scope` is a reference field — passing the scope name string instead of its sys_id will silently return zero results.

2. Get capability_id:

```
now-sdk query sys_one_extend_capability -q 'name=<skill_name>^sys_scope=<scope_sys_id>' -f 'sys_id,sys_scope' -o json
```

3. Get config_id (use `skill_id`, not `name`):

```
now-sdk query sn_nowassist_skill_config -q 'skill_id=<capability_id>^sys_scope=<scope_sys_id>' -f 'sys_id' -o json
```

4. Get capability_definition_id:

```
now-sdk query sys_one_extend_capability_definition -q 'capability=<capability_id>^sys_scope=<scope_sys_id>' -f 'sys_id' -o json
```

5. Get prompt_id (most recent):

```
now-sdk query sys_generative_ai_config -q 'definition=<capability_definition_id>^sys_scope=<scope_sys_id>^ORDERBYDESCsys_created_on' -f 'sys_id' -o json --limit 1
```

### Handling Empty Results

Any of the 5 queries above can return zero rows immediately after install — the platform sometimes takes a few seconds to index new `sys_one_extend_capability` / `sn_nowassist_skill_config` records. This is the most common reason the Skill URL step gets silently skipped — treat it as an expected transient state, not a dead end.

- Retry once after a short delay (a few seconds) before concluding the record doesn't exist.

- If still empty after retry, do NOT fabricate a sys_id or guess a URL. Your response MUST explicitly state: which numbered query returned no results, the query you ran, and that the Skill URL could not be constructed as a result. Suggest the user re-check via the Skill Builder UI or re-run the query chain shortly after.

- Never omit this outcome silently. A response with a missing URL and no explanation is treated the same as skipping step 13 entirely (see the `nowassist-skills-guide` topic's step 14 gate) — it will fail that self-check.

### URL Format

```
https://<instance_name>.service-now.com/now/now-assist-skillkit/skill/<capability_id>/params/prompt-id/<prompt_id>/config-id/<config_id>
```

Commonly hallucinated wrong format — do NOT use:
`now/nowassist/skillkit/capability/{id}/definition/{id}/prompt/{id}`

Key differences: the segment is `now-assist-skillkit` (hyphenated), the resource is `skill` (not `capability`), and parameters use `/params/prompt-id/` and `/config-id/`.

### Validation Checklist

Before presenting the URL, verify:

-  Path starts with `now/now-assist-skillkit/skill/`

-  Contains `/params/prompt-id/` (NOT `/definition/` or `/prompt/`)

-  Contains `/config-id/` (NOT `/definition/`)

-  Uses exactly 3 sys_ids: `capability_id`, `prompt_id`, `config_id`

-  All sys_ids are real values from queries — no placeholders

-  All four records share the same `sys_scope` value

-  `config_id`'s `skill_id` matches `capability_id`

## Validation Rules

### Required Fields

| Rule | Description |
| R1 | `$id` required — unique identifier |
| R2 | `name` required |
| R3 | `securityControls` required — must include `userAccess` and at least one of `roleRestrictions` / `roleMap` |
| R4 | `providers` array required with at least one provider |
| R5 | Each provider must have `prompts` with at least one version |
| R6 | Each prompt version must have `$id` , `model` , `promptState` , and `prompt` |

### Deployment Validation

| Rule | Description |
| D1 | UI Action table must have `actions_access = true` in `sys_db_object` — verify before using |

### Tool Validation

| Rule | Description |
| T1 | Every tool must have `$id` for stable identity |
| T2 | Script, FlowAction, and Subflow tools require `$capabilityId` |
| T3 | Tool inputs and outputs require `$id` |
| T4 | InlineScript must wrap code in IIFE: `(function() { ... })();` |
| T5 | Script tools must reference an existing Script Include |
| T6 | WebSearch must use `searchType: 'ai_answers'` |

### Security Validation

| Rule | Description |
| S1 | `userAccess` must include `$id: Now.ID['key']` — missing `$id` causes sync errors (critical) |
| S2 | `userAccess.type` must be `'authenticated'` or `'roles'` |
| S3 | `roleRestrictions` must contain role sys_ids (not names) |
| S4 | `maint` role is not allowed |
| S5 | If `userAccess.type` is `'roles'` , the `roles` array must have at least one entry |

### Prompt Validation

| Rule | Description |
| P1 | `promptState` must always be `'draft'` |
| P2 | Prompt must follow the mandatory 4-section structure: `## Role` , `## Context` , `## Instructions` , `## Output` (see the `nowassist-skills-guide` topic) |
| P3 | `filterCondition` keys must exactly match input attribute names, case-sensitive (including spaces) |
| P4 | No array indexing in prompts: `${p.tool.Tool.output.items[0]}` causes regex timeout |

### Valid Enums

| Property | Valid Values | Wrong Values |
| `dataType` | `'string'` , `'numeric'` , `'boolean'` , `'glide_record'` , `'simple_array'` , `'json_object'` , `'json_array'` | `'text'` , `'number'` , `'record'` |
| `promptState` | `'draft'` , `'finalized'` , `'published'` , `'archived'` | `'active'` , `'enabled'` |
| `userAccess.type` | `'authenticated'` , `'roles'` | `'all'` , `'public'` , `'any'` |
| `providerAPI.type` | `'sys_hub_flow'` , `'sys_hub_action_type_definition'` , `'sys_script_include'` , `'one_api_system_executor'` | `'flow'` , `'action'` |

### Common Hallucinations

| Wrong | Correct | Notes |
| `{ userAccess }` (shorthand) | `{ userAccess: userAccess }` | ShorthandPropertyAssignment not allowed |
| `userAccess: { type: '...' }` | `userAccess: { $id: ..., type: '...' }` | `$id` is required — missing causes sync errors |
| `providerAPI: 'Now LLM Generic'` | `providerAPI: { type: '...', id: '...' }` | Must be an object, not a string |
| `prompts: (p) => [...]` | `prompts: [{ name, versions: [...] }]` | `prompts` is an array, not a function |
| `outputs: { ... }` | Omit entirely | 5 standard outputs auto-generated |
| `dataType: 'record'` | `dataType: 'glide_record'` | Use exact enum value |
| `dataType: 'text'` | `dataType: 'string'` | Use exact enum value |
| `promptState: 'published'` | `promptState: 'draft'` | Always use `'draft'` in code |
| `roleRestrictions: ['admin']` | `roleRestrictions: ['<sys_id>']` | Must use sys_ids, not role names |
| `${p.tool.WebSearch.output}` | `${p.tool.WebSearch.response}` | WebSearch uses `.response` |
| `${p.input.user query}` | `${p.input['user query']}` | Bracket notation for names with spaces |
| Multiple `glide_record` inputs | Only ONE allowed | Use tools for additional record lookups |

### Property Naming

Always use camelCase for properties:

| Wrong | Correct |
| `short_description` | `shortDescription` |
| `test_values` | `testValues` |
| `data_type` | `dataType` |
| `prompt_state` | `promptState` |
| `role_restrictions` | `roleRestrictions` |
| `user_access` | `userAccess` |

## Troubleshooting

### Common Errors

| Error | Solution |
| InlineScript doesn't accept `$capabilityId` | `$capabilityId` is NOT supported for InlineScript/WebSearch. Only use `$id` . `$capabilityId` is only for Script, Subflow, FlowAction. |
| Input name with spaces in prompt | Use bracket notation: `${p.input['shift requirement']}` , not `${p.input.shift requirement}` |
| Script execution failed | `context.getValue()` uses snake_case: `'incident_number'` not `'incident number'` |
| testValues on glide_record requires tableSysId | `tableSysId` must be the sys_id of the test record when `testValues` is provided |
| filterCondition key mismatch | Keys must match input attribute names exactly (case-sensitive) |
| promptState validation error | Always use `promptState: 'draft'` |
| UI Action not created | Verify table has `actions_access = true` : `now-sdk query sys_db_object -q 'name=<table>' -f 'name,actions_access' -o json` |
| Skill not in Otto Panel | Set `nowAssistPanel: { enabled: true }` and publish in platform |
| `maint` role rejected | Use `admin` , `itil` , or other appropriate roles instead |
| Skill name too long | Shorten to 40 characters |

### Type Errors

| Error | Solution |
| `Type 'string' not assignable to ExplicitKey` | Use `Now.ID['key']` for all `$id` properties, not plain strings |
| `ShorthandPropertyAssignment` | Use `{ tool: tool }` not `{ tool }` |
| `Type 'string' not assignable to ToolOutputRef` | Decision `field` needs a tool ref ( `getData.field` ); `value` is a plain string |
| `Type '{ script }' not assignable` | Tool input values don't accept `{ type: 'script' }` — use refs or strings |
| `WebSearch requires query` | `query` must be `t.input.name` , `"string"` , or `tool.output` — not a script object |
| `Missing $id on tool input/output` | Tool inputs and outputs require `$id` — add to each object |

### UserAccess Sync Error Recovery

Problem: After multiple syncs, `userAccess` with type `roles` resets to `authenticated` without `$id`, losing role configurations.

Root Cause: Missing or invalid `Now.ID` on `userAccess`.

Recovery:

- Query the deployed ACL:

```
now-sdk query sys_security_acl -q 'nameCONTAINS<skill_sys_id>' -f 'sys_id,name' -o json
```

- Query associated roles:

```
now-sdk query sys_security_acl_role -q 'sys_security_acl=<acl_sys_id>' -f 'sys_user_role' -o json
```

- Reconstruct `userAccess` with a proper `$id`:

```
securityControls: {
    userAccess: {
        $id: Now.ID['skill_name_acl'],  // REQUIRED for stable identity
        type: 'roles',
        roles: ['<role_sys_id_1>', '<role_sys_id_2>']
    },
    roleRestrictions: [/* existing */]
}
```

- Build and install to apply the fix.

Prevention: Always include `$id: Now.ID['unique_key']` in `userAccess`.

### Anti-Patterns

| Anti-Pattern | Solution |
| Underscores in input/output names | Use spaces: `"Incident Number"` not `"incident_number"` |
| Spaces in `context.getValue()` | Use snake_case: `context.getValue('incident_number')` |
| Missing security controls | Always configure `securityControls` before anything else |
| No input validation in scripts | Validate and sanitize all inputs before database operations |
| Detailed error messages to users | Return generic errors; log details with `gs.error()` |
| Importing Glide APIs | `GlideRecord` , `gs` , `GlideAggregate` are globally available — never import |
| `maxTokens` too high | Ensure `maxTokens` is within model limits |

### Debugging Tips

- Start simple — add tools one at a time, verify each works before adding the next

- Use `gs.info()` in scripts and check Application Logs for output

- Use `testValues` on inputs for sample data during development

- Check tool output patterns — Script/InlineScript use `.output`, WebSearch/Skill use `.response`, FlowAction/Subflow use `.outputName`

## Related

- AI Skills Guide — Core concepts, inputs, tools, prompts, complete examples

- See the `developing-apps-guide` topic for project setup, authentication, and build workflow

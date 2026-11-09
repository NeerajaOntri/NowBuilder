Version: 4.14.0

# ServiceNow Fluent Overview

ServiceNow Fluent is a domain-specific language (DSL) based on TypeScript for defining the metadata files [sys_metadata] that make up applications. It includes APIs for tables, roles, ACLs, business rules, Automated Test Framework tests, and more.

## Cross-Cutting Language Constructs

Some Fluent features apply across every API rather than belonging to a specific record type — `Now.include`, `Now.attach`, `Now.ref`, the data helpers (`Duration`, `TemplateValue`, etc.), and the `$override` escape hatch. These live in the `fluent/` folder of the SDK docs and all share the `fluent-language` tag. Use that tag to discover them as a group: `now-sdk explain fluent-language` returns every cross-cutting topic. Read these first when working in any `.now.ts` file — they apply regardless of which API you're calling.

Developers define metadata in a few lines of code instead of through a form or builder tool user interface. Applications created or converted with ServiceNow platform tools or the ServiceNow SDK support developing in ServiceNow Fluent.

ServiceNow Fluent supports two-way synchronization, which allows changes to metadata to be synced from other Now Platform user interfaces into source code and changes to source code to be synced back to metadata across the instance.

## File Structure

Fluent metadata is defined in `.now.ts` files. A typical project structure:

```
src/
    fluent/
        business-rules/
            log-state-change.now.ts
        tables/
            to-do.now.ts
    server/
        show-state-update.js
now.config.json
package.json
```

## Usage

In `.now.ts` files, import APIs from `@servicenow/sdk/core` and define metadata:

```
import { Table, StringColumn, DateColumn, BooleanColumn, IntegerColumn } from '@servicenow/sdk/core'

export const x_snc_example_to_do = Table({
    name: 'x_snc_example_to_do',
    schema: {
        deadline: DateColumn({ label: 'deadline' }),
        task: StringColumn({ label: 'Task', maxLength: 120, mandatory: true }),
        active: BooleanColumn({ label: 'Active' }),
        state: StringColumn({
            label: 'State',
            choices: {
                ready: 'Ready',
                in_progress: 'In Progress',
                completed: 'Completed',
            },
        }),
        priority: IntegerColumn({ label: 'Priority' }),
    },
})
```

For sample/demo data, use the Record API, and be sure to set `installMethod: 'demo'` via the `$meta` property:

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['example_id0'],
    $meta: { installMethod: 'demo' },
    table: 'x_snc_example_to_do',
    data: {
        state: 'ready',
        task: 'Create a ServiceNow Fluent application',
        active: true,
        priority: 1,
    },
})
```

## Server-Side Scripts and Modules

For server-side scripts, use JavaScript modules with `import`/`export`. This is the preferred approach — modules provide typed Glide API access, code reuse, and full IDE support. Place module files under `src/server/` and import them from `.now.ts` files:

```
import { BusinessRule } from '@servicenow/sdk/core'
import { showStateUpdate } from '../server/show-state-update'

BusinessRule({
    $id: Now.ID['br0'],
    table: 'x_snc_example_to_do',
    script: showStateUpdate,
    name: 'LogStateChange',
    when: 'after',
    action: ['update'],
})
```

For detailed guidance on module imports, exports, Glide APIs, and Script Include patterns, see the `module-guide` topic.

## Controlling the ECMAScript Version of Server-Side Scripts

Any API that has a server-side script field (`BusinessRule`, `Acl`, `ScriptInclude`, `ScriptAction`, `ScheduledScript`, `UiPage`, `AliasTemplate`, `InboundEmailAction`, `CatalogItem`, `CatalogItemRecordProducer`, `RestApi` routes, `StateModel` transition conditions, the instance scan check APIs, `SPWidget`, and `SPMenu`, among others) accepts an optional `$meta.useEsLatest` flag:

```
import { ScriptInclude } from '@servicenow/sdk/core'

ScriptInclude({
    $id: Now.ID['my-script-include'],
    name: 'MyScriptInclude',
    $meta: { useEsLatest: true },
    script: Now.include('../../server/ScriptInclude/MyScriptInclude.server.js'),
})
```

Set `useEsLatest: true` to run that record's server-side script field(s) with the latest ECMAScript version the platform supports, instead of whatever the application's `sys_app`/`now.config` default is. Omit `useEsLatest` entirely to leave the app-level default in place — most records don't need to set this. When a record has more than one script field (e.g. `RestApi` routes with `headers`/`parameters`, or an ACL with both `script` and role conditions), `useEsLatest` applies to all script fields defined for that entity, not just one.

## Deleting Fluent Code

Every record defined in Fluent has its identity tracked in `keys.ts`, which maps each `$id` to the record it produced (exception is coalesce tables that dont require `$id` on APIs). Removing the Fluent code that defines a record (e.g. a `Table()`, `BusinessRule()`, or `Record()` call) does not simply make that record disappear from the build. Because the `keys.ts` entry still exists with no matching Fluent code, the build treats this as an intentional deletion: it marks the entry deleted in `keys.ts` and generates a delete record for it. That delete record ships as part of the app package and removes the record from the instance the app is installed on, including through future app upgrades.

This tracked-deletion behavior is what makes app upgrades reliable — it's how Fluent knows to clean up a record on customer instances after you remove it from source. But it also means deleting Fluent code has a real, persistent effect beyond the current file, so it should be done deliberately:

- If the record was already installed to an instance and the deletion should propagate through upgrades: deleting the Fluent code and leaving the `keys.ts` entry in place is correct — that's what generates and applies the delete record.

- If the record was never installed anywhere, or the deletion has already fully propagated to production and no longer needs tracking: delete the Fluent code and remove its matching entry from `keys.ts` in the same change. If the `keys.ts` entry is left behind, a delete record is still generated even though that isn't the intent.

### Warning for AI Agents/LLMs

Never delete a `Table()`, `BusinessRule()`, `Record()`, or other API call from a `.now.ts` file as a quick way to "remove" something, and never do so without telling the user first. Because the two cases above look identical in the code — the difference is install history, which the code alone can't reveal — an agent cannot safely infer which one applies. Before deleting Fluent code, confirm with the user whether the record has been installed anywhere and whether the deletion should propagate through upgrades, and update `keys.ts` accordingly.

## Core Difference between UI Pages and UI Formatters

- UI Formatter -- Used inside forms to add non-field content

- UI Page -- Used outside forms as standalone pages

If the request mentions "on the form" or similar keywords (activities, process flow, stages, timeline, attached knowledge, checklist, breadcrumb, CI relationships, contextual search, variable editor, formatters), use UI Formatters. If it's a standalone page/application, use UI Pages.

## AI Integration with LLM

For AI-powered capabilities (sentiment analysis, text generation, summarization), use ServiceNow's `sn_generative_ai.LLMClient` API in server-side scripts:

```
var llmClient = new sn_generative_ai.LLMClient()
var prompt = 'Your specific AI task prompt here'

try {
    var result = llmClient.call({ prompt: prompt })
    if (result.status === 'Success') {
        var response = result.response.trim()
    } else {
        gs.error(result.response)
    }
} catch (e) {
    gs.error(e.message)
}
```

The recommended pattern is to create a Script Include for LLM operations, then call it from Business Rules, Scripted REST APIs, or via GlideAjax from client scripts.

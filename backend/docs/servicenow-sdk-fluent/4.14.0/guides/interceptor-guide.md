Version: 4.14.0

# Interceptors

Guide for creating and maintaining ServiceNow Interceptors (`sys_wizard`) using the Fluent API. An Interceptor presents a question/decision panel before a user creates a new record on an intercepted table, guiding them through a branching flow of Answers to route the user to the right destination form, URL, or follow-up question. For `'multipleChoice'` answers, `sys_wizard_choice` wizard choices are not authored through Fluent — configure them manually on the instance after deploying, see "Post-Install configuration" below.

## When to Use

- 
Replacing the default "New" form for a table with a "What type of X would you like to create?" decision panel (e.g. intercepting `incident.do` to ask what kind of incident before showing the form)

- 
Presenting a fixed list of destination options, each navigating to a different URL, catalog item, or record producer

- 
Branching a decision-panel flow across multiple questions (a "leading question" answer advances to another question)

- 
Presenting a static or dynamically-sourced multiple-choice list as one of several answer options

- 
Gating certain destination options to specific roles at runtime

Note: use `DataPolicy`/`UiPolicy` instead when the goal is validating or controlling fields on the destination form itself, not choosing which form to show. Interceptors run before a record exists — they never see or set field values on the eventual record.

## Instructions

- Always give every `InterceptorAnswer` its own `$id`. `sys_wizard_answer` has no safe natural key — `order` defaults to `100` for every new answer, and `name` is not reliably unique. There is no valid coalesce strategy other than an explicit `$id` per answer.

- The top-level `Interceptor`'s `name` is its identity — never set `$id` on it. `sys_wizard` coalesces on `name`, so `Interceptor` has no `$id` property at all; two `Interceptor(...)` calls with the same `name` resolve to the same record. Give each question a distinct, descriptive `name`, and renaming an existing one creates a new record on the instance. Before authoring a new `Interceptor`, verify the chosen `name` is unique by querying the instance — query `sys_wizard` filtered by `name` (see the `query-guide` topic). An accidental match silently coalesces your new question into the existing record (and overwrites its fields) instead of creating a separate one.

- Set `type` to select which other fields apply. Only one variant's fields do anything: `'answer'` → `targetUrl`; `'leadingQuestion'` → `nextQuestion`; `'multipleChoice'` → `sys_wizard_choice` records (added manually in instance); `'button'` → `buttonLabel` (the `answer` field is stored but not displayed for buttons); `'externalChoice'` → `table`/`element`/`dependentValue`.

- Verify the destination table has a form available before configuring an Answer that navigates to it. For `type: 'answer'`, `targetUrl` typically points at a table's new-record form (e.g. `'<table>.do?sys_id=-1'`) or a catalog item — confirm that table (or catalog item) already has an active form/view configured on the target instance before authoring; a table with no accessible form sends the user to a broken or unusably empty page. When `targetUrl` includes `sysparm_query` to pre-populate fields on that form (e.g. `'<table>.do?sys_id=-1&sysparm_query=category=hardware'`), each referenced field must also be configured on the destination form — a field left off the form silently drops its pre-populated value. This is not validated at build time — there is no diagnostic for it. Query `sys_ui_form`/`sys_ui_view` for the table, or check View Designer on the instance, before authoring.

- `backPanel`, `nextPanel`, and `nextQuestion` are references to other `sys_wizard` records. They accept a raw sys_id string, a `Record<'sys_wizard'>`, or an `Interceptor(...)` expression. For a question defined in the same project, pass its `Interceptor(...)` call's return value directly. For pre-existing platform questions or questions in another app, use the known sys_id string.

- `intercepts` is a single `*.do` path string, e.g. `'incident.do'`. The platform stores it as a plain string, and every out-of-box interceptor targets a single table.

- Setting `intercepts` does not create Answers automatically. Each destination option must be explicitly authored as an entry in `answers` — there is no auto-population from the intercepted table's schema or existing catalog items.

- `roles` on an Answer is a runtime visibility filter, not a build-time access check. An Answer with `roles: ['itil']` still builds and installs successfully for developers without that role — the role gate is only enforced when an end user views the decision panel at runtime.

- `script` is available on any Answer type, not just `'button'` — it runs when that Answer is selected, independent of navigation. It is not gated to a specific `type`. Interceptor scripts are typically short one-liners (e.g. `current.priority = '1'; current.update();`) and are usually written inline. For a longer script, extract it to a separate file and reference it with `Now.include('./script.js')` instead — see the `now-include-guide` topic.

- `type: 'yesNo'` and `type: 'freeformText'` only use `payloadName` at runtime. Other fields are stored but have no effect. When the user's request describes a yes/no question or a free-text input (e.g. "ask whether the request is urgent" or "add a justification box"), use these types with a `payloadName` — that is an explicit request. Only fall back to `'answer'` or `'externalChoice'`/`'multipleChoice'` when the user does not mention yes/no or free-text semantics.

- `table` and `element` must always be provided together for `'externalChoice'` (see "Choosing between `multipleChoice` and `externalChoice`" in Key Concepts for when to prefer this type). The platform reads `sys_choice` dropdown values for the given `table.element` combination — it does NOT list records (rows) from the table. To let users pick from actual table records, use a `CatalogItemRecordProducer` with a Reference variable instead. Setting one without the other is silently ignored by the platform. `dependentValue` is optional — only supply it when `element` is itself a dependent choice list (e.g. `subcategory` depending on `category`); simple choice lists like `state` do not need it.

- `'multipleChoice'` requires manually authoring `sys_wizard_choice` records on the instance after deploying — see "Post-Install configuration" below, and "Choosing between `multipleChoice` and `externalChoice`" in Key Concepts for when to use it instead of `externalChoice`.

## API Reference

See the `interceptor-api` topic for the full property reference, including the `InterceptorAnswer` type.

## Key Concepts

### The two-level hierarchy

An Interceptor is a logical "decision panel" made of one Interceptor (question) and any number of Answers. For `'multipleChoice'` answers, `sys_wizard_choice` sub-choices are added manually on the instance post-install — see "Post-Install configuration" below.

```
Interceptor (sys_wizard)               "What would you like to create?"
  └── answers: InterceptorAnswer[]     (sys_wizard_answer) "Hardware request", "Software request", ...

Deploying the top-level `Interceptor({...})` call creates `sys_wizard` and `sys_wizard_answer` records. 

### The `type` selector and its field clusters

| `type` value | Platform code | Relevant fields | What happens when selected |
|---|---|---|---|
| `'answer'` (default) | `1` | `targetUrl` | Navigates the browser to `targetUrl` |
| `'leadingQuestion'` | `2` | `nextQuestion` | Advances to another Interceptor question (by sys_id) |
| `'multipleChoice'` | `3` | `sys_wizard_choice` records (added manually on the instance post-install) | Presents choices as a options |
| `'button'` | `6` | `buttonLabel`, `script` | Renders a button labeled `buttonLabel`; runs `script` when clicked |
| `'externalChoice'` | `9` | `table`, `element`, `dependentValue` | Sources choices from `sys_choice` dropdown values for a column on another table — does NOT list records from the table |
| `'yesNo'` | `4` | `payloadName` | Renders a yes/no toggle and captures the selection under `payloadName`; use when the user requests a yes/no question |
| `'freeformText'` | `5` | `payloadName` | Renders a text input and captures the value under `payloadName`; use when the user requests a free-text field |

`script` and `roles` are available on every Answer regardless of `type`.

### Flow navigation vs. Answer selection

There are two independent ways an Interceptor flow branches, and they are not mutually exclusive:

- **`backPanel` / `nextPanel`** (on the Interceptor itself) define the *default* previous/next question in a linear flow — used when the selected Answer doesn't specify its own destination.
- **`nextQuestion`** (on an Answer with `type: 'leadingQuestion'`) overrides the flow for that specific Answer, branching to a different question than `nextPanel` would.

All three fields accept a raw sys_id string, a `Record<'sys_wizard'>`, or an `Interceptor(...)` expression — see Instruction 6.

### Choosing between `multipleChoice` and `externalChoice`

Both types present a selectable list of choices, but they differ in how those choices are sourced:

| Aspect | `'externalChoice'` | `'multipleChoice'` |
|--------|-------------------|-------------------|
| Choice source | Existing `sys_choice` dropdown on a table | Custom `sys_wizard_choice` records, added manually on the instance |
| Setup | Set `table` + `element` (2 fields) | Manual post-install step — create each `sys_wizard_choice` record on the instance |
| Drift risk | None — choices stay in sync with the source table | N/A — there is no Fluent source for choices; they always live only on the instance |
| Use when | Choices already exist as a dropdown on a platform table (e.g. `state`, `priority`, `category`) | Choices are unique to this interceptor and don't exist elsewhere |

**Default to `'externalChoice'`** when the user wants to show choices from a known table column. Only use `'multipleChoice'` when the choices are custom to this interceptor and do not correspond to any existing `sys_choice` dropdown.

## Examples

For per-type examples (`'answer'`, `'leadingQuestion'`, `'multipleChoice'`, `'externalChoice'`, `'yesNo'`, `'freeformText'`, dependent choice lists, and a combined advanced example), see the `interceptor-api` topic. The examples below cover edge cases and patterns not shown there.

### Minimal — required fields only

The simplest possible Interceptor: a question with no answers yet.

```typescript fluent
import { Interceptor } from '@servicenow/sdk/core'

Interceptor({
    name: 'Minimal question',
    question: 'What would you like to create?',
})
```

### Pre-populating fields via `targetUrl` query parameters

An `'answer'` Answer's `targetUrl` can pre-fill fields on the destination form using `sysparm_query` — a `^`-separated encoded query string appended as a query parameter — but only if each referenced field is actually configured on that form (see Instruction 5). Here, `category` and `subcategory` must both be on `incident`'s form for the pre-populated values to show up when the form loads; a field left off the form silently drops its value instead of erroring. For a multi-word value inside `sysparm_query`, use a literal space as the third Answer below shows.

```
import { Interceptor } from '@servicenow/sdk/core'

Interceptor({
    name: 'Choose hardware type',
    question: 'What type of hardware do you need?',
    answers: [
        {
            $id: Now.ID['hardware-type-laptop'],
            answer: 'Laptop',
            type: 'answer',
            targetUrl: 'incident.do?sys_id=-1&sysparm_query=category=hardware^subcategory=laptop',
            order: 100,
            active: true,
        },
        {
            $id: Now.ID['hardware-type-monitor'],
            answer: 'Monitor',
            type: 'answer',
            targetUrl: 'incident.do?sys_id=-1&sysparm_query=category=hardware^subcategory=monitor',
            order: 200,
            active: true,
        },
        {
            $id: Now.ID['hardware-type-docking-station'],
            answer: 'Docking station',
            type: 'answer',
            // Use a literal space for a multi-word value inside sysparm_query
            targetUrl: 'incident.do?sys_id=-1&sysparm_query=category=hardware^subcategory=docking station',
            order: 300,
            active: true,
        },
    ],
})
```

### `'button'` — scripted answer with role gating

A button-style Answer that runs a script when clicked, visible only to specific roles.

```
import { Interceptor } from '@servicenow/sdk/core'

Interceptor({
    name: 'Escalation question',
    question: 'Does this need immediate escalation?',
    answers: [
        {
            $id: Now.ID['escalation-question-escalate'],
            type: 'button',
            buttonLabel: 'Escalate',
            script: "current.priority = '1'; current.update();",
            roles: ['itil', 'incident_manager'],
            order: 100,
            active: true,
        },
    ],
})
```

### No sub-choices yet — placeholder multipleChoice

A `'multipleChoice'` Answer where the choices can be added later in the instance.

```
import { Interceptor } from '@servicenow/sdk/core'

Interceptor({
    name: 'Placeholder choice question',
    question: 'Pick one (choices coming later)',
    answers: [
        {
            $id: Now.ID['placeholder-choice-answer'],
            answer: 'To be defined',
            type: 'multipleChoice',
        },
    ],
})
```

### Flow navigation — `backPanel` across two questions

`backPanel` sets the default previous question independently of any single Answer's `nextQuestion`.

```
import { Interceptor } from '@servicenow/sdk/core'

Interceptor({
    name: 'Change window confirmation',
    question: 'Step 2: Confirm the change window',
    // sys_id of "Step 1: What type of change is this?", deployed separately
    backPanel: '82ca0be019af4745b235703c4c68a675',
    answers: [
        {
            $id: Now.ID['change-window-confirm-answer'],
            answer: 'Confirm',
            type: 'answer',
            targetUrl: 'chg_task.do?sys_id=-1',
            order: 100,
            active: true,
        },
    ],
})
```

### Referencing another question defined in the same project

To point `backPanel`/`nextPanel`/`nextQuestion` at a question defined earlier in the same project, pass the target `Interceptor(...)` call's own return value directly — prefer this over the raw sys_id string shown above, which only works for a question that already exists on the instance:

```
const hardwareQuestion = Interceptor({ name: 'Hardware category', question: '...' })
Interceptor({
    name: 'Next question',
    answers: [{ $id: Now.ID['a'], type: 'leadingQuestion', nextQuestion: hardwareQuestion }],
})
```

## Post-Install configuration

Fluent defines the `'multipleChoice'` Answer itself (`sys_wizard_answer`), but `sys_wizard_choice` — the actual wizard choices shown under it — has no Fluent representation and is not created by `now-sdk install`. Configure it on each instance the app is deployed to, after install.

After running `now-sdk install`, the CLI summary should list every record that was created or updated, including the `sys_wizard_answer` for your `'multipleChoice'` Answer, with a direct link, for example:

```
✓ sys_wizard_answer  Choose a severity
   → https://<instance>.service-now.com/sys_wizard_answer.do?sys_id=<answer-sys-id>
```

Open that link, then for each choice you want under this Answer, create a new `sys_wizard_choice` record (related list, or `sys_wizard_choice_list.do`) with:

- `text` — the label shown to the user

- `value` — the value stored when the choice is selected

- `answer` — this `sys_wizard_answer` record

- `order` — distinct per choice under this Answer (collisions are scoped per-parent Answer — see Avoidance below)

Because these records live only on the instance, re-deploying never creates, updates, or removes them — adding, renaming, or re-valuing a choice later is a manual instance edit, repeated per environment.

## Avoidance

`name` is Interceptor's unique key and its coalesce identity — changing it creates a new record and orphans the old one.

- Never assume a new `Interceptor`'s `name` is unique without checking — query `sys_wizard` filtered by `name` before authoring; an accidental match coalesces into the existing record instead of creating a new one.

- Never omit `$id` on an `InterceptorAnswer` — there is no safe coalesce key for `sys_wizard_answer`; `$id` is the only stable identity.

- Never configure a `targetUrl` Answer against a table with no form available — verify the destination table (or catalog item) has an active form/view configured on the instance before authoring; the plugin does not validate this at build time.

- Never reference a field in `targetUrl` query parameters that isn't on the destination form — a pre-populate parameter for a field the form doesn't expose is silently dropped.

- Never use `+`or `%20` for a space in a `sysparm_query` value — it is not decoded and shows up as a literal `+` character on the form; use a literal space instead.

- Never rely on the `order` default for more than one sibling Answer or Choice — always set explicit, distinct values. Collision is scoped per-parent: two choices under different Answers never collide regardless of `order`.

- For a question defined in the same project, pass its `Interceptor(...)` return value directly into `backPanel`/`nextPanel`/`nextQuestion` — it resolves to the target's generated sys_id. Use a raw sys_id string only for a question that already exists on the instance (deployed separately, or defined in another app).

- Never set `answer` on a `'button'` Answer — it is stored but not displayed; use `buttonLabel` for the visible text.

- Never set `table` without `element` (or `element` without `table`) for `'externalChoice'` — the platform ignores an incomplete pair.

- Never assume `intercepts` alone produces a working decision panel — always author at least one Answer.

- Never treat `roles` on an Answer as a build-time or access-control mechanism — it is a runtime-only visibility filter with no build-time enforcement.

- Do not generate `type: 'yesNo'` or `type: 'freeformText'` Answers unless the user's request implies yes/no or free-text semantics — only `payloadName` has runtime effect for these types, so always set it. Natural-language cues like "yes/no question", "urgent?", "justification box", or "free-text field" count as explicit requests.

- Never author `sys_wizard_choice` records with `Record()`/`Now.table()` —  wizard choices must be added manually on the instance post-install (see "Post-Install configuration" above), not through the Fluent build.

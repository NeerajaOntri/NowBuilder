Version: 4.14.0

# Interceptor

Creates an Interceptor (`sys_wizard`) that presents a question/decision panel before a user creates a new record on an intercepted table, guiding them through a branching flow of Answers to the right destination form, URL, or follow-up question.

## Signature

```
Interceptor(config)
```

## Usage

```
import { Interceptor } from '@servicenow/sdk/core'

Interceptor({
    name: 'Choose request type',
    question: 'What would you like to create?',
    answers: [
        {
            $id: Now.ID['choose-request-type-hardware'],
            answer: 'Hardware request',
            type: 'answer',
            targetUrl: 'sc_cat_item.do?sys_id=-1',
            order: 100,
            active: true,
        },
    ],
})
```

## Parameters

### config

`Interceptor`

an object containing api properties:

Properties:

- 
name (required): `string`
Internal label for this question panel. Not shown to the end user. Identifies the record — two `Interceptor`s with the same `name` coalesce into a single record. Renaming an existing Interceptor creates a new record on the instance and deletes the old one

- 
question (optional): `string`
Question text presented to the user

- 
backPanel (optional): `string | Record<'sys_wizard'> | Interceptor`
Previous question/panel in the flow. Reference to `sys_wizard`; accepts a raw sys_id string, a `Record<'sys_wizard'>` reference, or an `Interceptor(...)` expression

- 
nextPanel (optional): `string | Record<'sys_wizard'> | Interceptor`
Default next question/panel in the flow, used when the selected answer doesn't specify its own `nextQuestion`. Reference to `sys_wizard`; accepts a raw sys_id string, a `Record<'sys_wizard'>` reference, or an `Interceptor(...)` expression

- 
intercepts (optional): `string`
`*.do` page path this Interceptor triggers on instead of the table's default new-record form, e.g. `'incident.do'`

- 
answers (optional): `InterceptorAnswer[]`
Answer options presented to the user for this question

- $id (required): `string | number | ExplicitKey<string>` -- Required per-answer identifier; `sys_wizard_answer` has no safe natural key

- name (optional): `string` -- Internal label; when omitted, the build plugin copies `answer` into the generated record

- answer (optional): `string` -- Text shown to the user for this option ("User Prompt" on the platform form). Not displayed when `type` is `'button'`

- type (optional, default: `'answer'`): `'answer' | 'leadingQuestion' | 'multipleChoice' | 'yesNo' | 'freeformText' | 'button' | 'externalChoice' | string` -- Controls which of this answer's other fields are used.

- targetUrl (optional): `string` -- Destination URL. Used when `type` is `'answer'`

- nextQuestion (optional): `string | Record<'sys_wizard'> | Interceptor` -- Next Interceptor question. Used when `type` is `'leadingQuestion'`. Accepts a raw sys_id string, a `Record<'sys_wizard'>`, or an `Interceptor(...)` expression.

- buttonLabel (optional): `string` -- Visible text shown on the button. Used when `type` is `'button'`; the `answer` field is not displayed for buttons

- table (optional): `keyof Tables` -- Table whose choice-list values (`sys_choice` rows) to source from. Used when `type` is `'externalChoice'`. This pulls the dropdown options defined for `element` on this table — it does NOT query records (rows) from the table itself. In a scoped app, must be in the same scope as this definition (prefixed `<scope>_`); to target an out-of-box table, use a global-scope app or a scoped table that extends it. Not validated against real table existence at build time — query `sys_db_object` on the target instance to confirm the table exists before authoring

- element (optional): `string` -- Choice column on `table` whose `sys_choice` dropdown values populate the answer's options. Used when `type` is `'externalChoice'`. The platform reads from `sys_choice` rows for this column — it does not list records from the table. Like `table`, this is a plain string not validated against the real column at build time — query `sys_dictionary` (filtered by `name=<table>^element=<element>`) on the target instance to confirm the column exists and has a `dropdown` choice type before authoring

- dependentValue (optional): `string` -- Optional value of the parent field when `element` is a dependent choice list on `table` (e.g. `subcategory` depending on `category`). Used when `type` is `'externalChoice'`; omit for simple choice lists like `state`

- script (optional): `string` -- Script executed when this answer is selected. Not gated to a specific `type`

- roles (optional): `(string | Role)[]` -- Role names or `Role` objects allowed to see this answer at runtime. Not enforced at build time — this is a runtime visibility filter, not a build-time access check. The underlying `roles` field is ACL- and dictionary-restricted to the `admin` role for read/write on the platform's standard UI; Fluent can still set it at install time via the generated XML (which bypasses UI-level ACLs), but a human editing the value afterward through the platform form needs the `admin` role

- order (optional, default: `100`): `number` -- Sort order among sibling answers under the same question — give each sibling a distinct value or their display order becomes unpredictable

- active (optional, default: `true`): `boolean` -- Whether this answer is presented to the user

- payloadName (optional): `string` -- Platform-internal payload correlation name

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit/view access for other developers after the application is installed.

- `'read'`: Others can see the record but not change it

- `'protected'`: Others cannot change this record

- Omit to allow other developers to customize this record

## Examples

### Basic Interceptor question

A question with two direct-answer options.

```
/**
 * @title Basic Interceptor question
 * @description A question with two direct-answer options
 */
import { Interceptor } from '@servicenow/sdk/core'

Interceptor({
    name: 'Choose request type',
    question: 'What would you like to create?',
    answers: [
        {
            $id: Now.ID['interceptor-basic-hardware'],
            answer: 'Hardware request',
            type: 'answer',
            targetUrl: 'sc_cat_item.do?sys_id=-1&sysparm_category=hardware',
            order: 100,
            active: true,
        },
        {
            $id: Now.ID['interceptor-basic-software'],
            answer: 'Software request',
            type: 'answer',
            targetUrl: 'sc_cat_item.do?sys_id=-1&sysparm_category=software',
            order: 200,
            active: true,
        },
    ],
})
```

### Interceptor with multiple choice answer

```
/**
 * @title Interceptor with multiple choice answer
 * @description An answer with sub-choices created via the Record API
 */
import { Interceptor, Record } from '@servicenow/sdk/core'

Interceptor({
    name: 'Multiple choice priority',
    question: 'How urgent is this?',
    answers: [
        {
            $id: Now.ID['interceptor-with-multiple-choice-priority'],
            answer: 'Select a priority level',
            type: 'multipleChoice',
            order: 100,
            active: true,
        },
    ],
})
```

### Interceptor with leading question

An answer that advances to another Interceptor question instead of navigating to a URL directly.

```
/**
 * @title Interceptor with leading question
 * @description An answer that advances to another Interceptor question instead of navigating to a URL directly
 */
import { Interceptor } from '@servicenow/sdk/core'

Interceptor({
    name: 'Leading question chooser',
    question: 'What would you like to create?',
    answers: [
        {
            $id: Now.ID['interceptor-with-leading-question-hardware'],
            answer: 'Hardware request',
            type: 'leadingQuestion',
            // sys_id of the target question, captured after deploying it separately
            nextQuestion: 'ce0487629b954f3c9618b3b901865ea2',
            order: 100,
            active: true,
        },
    ],
})
```

### Interceptor with external choice answer

Sources selectable values dynamically from a choice list on another table.

```
/**
 * @title Interceptor with external choice answer
 * @description Sources selectable values dynamically from a choice list on another table
 */
import { Interceptor } from '@servicenow/sdk/core'

Interceptor({
    name: 'External choice status',
    question: 'Select a status',
    answers: [
        {
            $id: Now.ID['interceptor-with-external-choice-status'],
            answer: 'Choose from status list',
            type: 'externalChoice',
            table: 'incident',
            element: 'state',
            order: 100,
            active: true,
        },
    ],
})
```

### Interceptor with external choice from a dependent choice list

Use `dependentValue` only when the chosen `element` is itself a dependent choice list (e.g. `subcategory` depends on `category` on `incident`).

```
/**
 * @title Interceptor with external choice from a dependent choice list
 * @description Scopes a dependent choice list by supplying the parent-field value
 */
import { Interceptor } from '@servicenow/sdk/core'

Interceptor({
    name: 'External choice dependent subcategory',
    question: 'Which subcategory?',
    answers: [
        {
            $id: Now.ID['interceptor-with-external-choice-subcategory'],
            answer: 'Choose a subcategory',
            type: 'externalChoice',
            table: 'incident',
            element: 'subcategory',
            dependentValue: 'Network',
            order: 100,
            active: true,
        },
    ],
})
```

### Interceptor with yesNo and freeformText answers

Captures a yes/no selection and a free-text input from the user. Both types require `payloadName` — it is the only field with runtime effect.

```
/**
 * @title Interceptor with yesNo and freeformText answers
 * @description Captures a yes/no selection and a free-text input from the user
 */
import { Interceptor } from '@servicenow/sdk/core'

Interceptor({
    name: 'Input capture details',
    question: 'Additional details',
    answers: [
        {
            $id: Now.ID['interceptor-with-input-capture-urgent'],
            type: 'yesNo',
            answer: 'Is this request urgent?',
            payloadName: 'urgent',
            order: 100,
        },
        {
            $id: Now.ID['interceptor-with-input-capture-justification'],
            type: 'freeformText',
            answer: 'Justification',
            payloadName: 'justification',
            order: 200,
        },
    ],
})
```

### Advanced Interceptor

Combines direct answers, a leading question, a multiple choice answer, and a scripted button answer in one question.

```
/**
 * @title Advanced Interceptor
 * @description Combines direct answers, a leading question, a multiple choice answer, and a scripted button answer in one question
 */
import { Interceptor } from '@servicenow/sdk/core'

Interceptor({
    name: 'Advanced request chooser',
    question: 'What would you like to create today?',
    intercepts: 'incident.do',
    backPanel: '82ca0be019af4745b235703c4c68a675',
    answers: [
        {
            $id: Now.ID['interceptor-advanced-direct'],
            answer: 'Report an issue',
            type: 'answer',
            targetUrl: 'incident.do?sys_id=-1',
            order: 100,
            active: true,
        },
        {
            $id: Now.ID['interceptor-advanced-leading'],
            answer: 'Request hardware',
            type: 'leadingQuestion',
            nextQuestion: 'ce0487629b954f3c9618b3b901865ea2',
            order: 200,
            active: true,
        },
        {
            $id: Now.ID['interceptor-advanced-choice'],
            answer: 'Select a priority',
            type: 'multipleChoice',
            order: 300,
            active: true,
        },
        {
            $id: Now.ID['interceptor-advanced-button'],
            type: 'button',
            buttonLabel: 'Escalate',
            script: "current.priority = '1'; current.update();",
            roles: ['itil'],
            order: 400,
            active: true,
        },
    ],
})
```

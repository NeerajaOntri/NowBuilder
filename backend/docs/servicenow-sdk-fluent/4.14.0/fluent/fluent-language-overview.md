Version: 4.14.0

# The Fluent Language

ServiceNow Fluent is a declarative, TypeScript-based domain-specific language (DSL) for defining ServiceNow application metadata — tables, business rules, ACLs, roles, ATF tests, and more — as source code instead of database records.

Most metadata types have a dedicated, typed API (`Table`, `BusinessRule`, `Acl`, and so on) — browse the API Reference section in the sidebar for the full list. Metadata types that don't have a dedicated API can be represented with `Record()`, which can define a record on any table.

## Why "Fluent"?

The name is a deliberate pun. Being fluent in a language means expressing yourself clearly and accurately, with minimal effort, and moving through it with ease. That's the goal for ServiceNow development itself: write metadata in a few lines of typed code instead of clicking through forms and builder UIs, and get the same protections — autocomplete, type checking, dependency enforcement — that professional developers expect from any other language.

## What problem does it solve?

Database-driven ServiceNow development stores every piece of configuration as an auto-generated XML record. A single business rule looks like this:

```
<?xml version="1.0" encoding="UTF-8"?>
<record_update table="sys_script">
  <sys_script action="INSERT_OR_UPDATE">
    <name>Validate Category</name>
    <collection>x_myapp_item</collection>
    <when>before</when>
    <action_insert>true</action_insert>
    <action_update>true</action_update>
    <active>true</active>
    <order>100</order>
    <script><![CDATA[(function executeRule(current, previous) {
    if (!current.getValue('category')) {
        current.setValue('category', 'general');
    }
})(current, previous);]]></script>
    <sys_id>96372fc457764b3b8f36b23a787cfcc4</sys_id>
  </sys_script>
</record_update>
```

That format has none of the design-time protections a real programming language gives you. The script is a raw string with no type checking, buried inside a record that's mostly platform bookkeeping. It's verbose, full of data that has nothing to do with the rule's actual behavior, and it produces difficult merge conflicts in Git. The directory structure is also rigid — every path has platform-specific meaning, with little room to organize code the way your team actually wants to.

Fluent replaces that with actual code:

```
import { BusinessRule } from '@servicenow/sdk/core'
import { validateCategory } from '../server/business-rules/validate-category'

BusinessRule({
    $id: Now.ID['validate-category'],
    name: 'Validate Category',
    table: 'x_myapp_item',
    when: 'before',
    action: ['insert', 'update'],
    script: validateCategory,
})
```

```
// src/server/business-rules/validate-category.ts
import { GlideRecord } from '@servicenow/glide'

export function validateCategory(current: GlideRecord<'x_myapp_item'>, previous: GlideRecord<'x_myapp_item'>) {
    if (!current.getValue('category')) {
        current.setValue('category', 'general')
    }
}
```

Same record, but now it's something an IDE can autocomplete, a compiler can type-check, and a reviewer can actually read in a pull request diff, AI Agents can reason with — and the script itself is a typed function with full Glide API support, syntax checking, editor compatibility, and not a string.

Notice `Now.ID[...]` above has no matching `import` — `Now` is a global the SDK registers automatically during build and through the language server, so it's available in any `.now.ts` file without importing it.

## Design principles

A few principles shape how the language is designed and where it's headed:

- Minimize weirdness. Favor industry standards over proprietary solutions. If the SDK has to build something itself, it should feel familiar to a JavaScript/TypeScript developer, not like a ServiceNow-specific dialect to relearn.

- Source code is the source of truth. Anything that establishes a relationship with a live instance — a dependency, a table reference — is informative, not authoritative. The SDK can warn you at compile time when your code and an instance disagree, but your source is never overridden by what's on the instance.

- Couple with abstractions, not specific tools. The SDK targets JavaScript/TypeScript and modules generally, not a single package manager or bundler, so it doesn't lock you into tooling decisions that age poorly.

- Convention and configuration. Strong defaults keep setup minimal, but conventions can be overridden through configuration (`now.config.json`) rather than being rigid rules baked into the file structure.

- Incremental adoption. You don't have to convert an entire app to start using Fluent. Hybrid apps — some tables and business rules in Fluent, the rest still in legacy XML — are fully supported, and `transform` converts pieces over time.

- No magic. Dependencies are explicit. There's no implicitly-available API relying on what happens to exist on an instance; the type-safe Fluent APIs make dependencies checkable at compile time instead of only failing at runtime.

## Two-way sync

Fluent isn't a one-way export. Changes made through other Now Platform interfaces (Studio, forms) can be pulled back into your source with `transform` (see Pulling Changes Made Directly on an Instance), and changes made in source are pushed to an instance with `install`. Neither direction is a dead end — you're not choosing between "code" and "the platform UI" permanently, just picking which one is authoritative for a given change.

## Directives

A handful of comment directives give you fine-grained control over the compiler and `transform`, without needing a config file or CLI flag. Each is a plain `//` comment placed directly above the statement (or, for the file-scoped ones, at the top of the file) it should apply to:

| Directive | Scope | What it does |
| `// @fluent-ignore` | One statement | Suppresses a specific compiler diagnostic on that statement. Use it when you've deliberately chosen a configuration the compiler warns about and don't want the warning to keep showing up. |
| `// @fluent-disable-sync` | One statement | Tells `transform` to never overwrite this statement, even if the corresponding record changes on the instance. Useful for a value you want to manage from code only, regardless of what happens on the platform side. |
| `// @fluent-disable-sync-for-file` | The whole file | Same as `@fluent-disable-sync` , but for every statement in the file. Place it at the top of a `.now.ts` file to exempt it entirely from `transform` . |

`@fluent-ignore` is unrelated to sync — it only silences a diagnostic. The other two only affect `transform`; they don't change what `build`/`install` does with the statement.

These are Fluent-specific — they only affect Fluent's own diagnostics and `transform`, not the TypeScript compiler. For an actual TypeScript type error, use TypeScript's own directives instead: `// @ts-expect-error` (preferred — errors if the line stops erroring, so you notice a stale suppression) or `// @ts-ignore`, each placed on the line above the error, ideally with a short comment explaining why the bypass is needed.

Use directives as a last resort. Every directive — Fluent's or TypeScript's — silences something the compiler is actively trying to tell you. Sometimes that's the right call, but it's easy to reach for one to make a warning go away without fixing what's actually wrong underneath, and a suppressed diagnostic doesn't get revisited on its own. Treat directives as a debt: leave a comment explaining why it's there, and re-check them when you upgrade the SDK — a diagnostic you suppressed may no longer apply, or a later version may fix the underlying issue outright, making the directive not just unnecessary but a mask over a bug it was hiding.

## Cross-cutting language constructs

Some Fluent features apply across every API rather than belonging to one specific record type: `Now.include`, `Now.attach`, `Now.ref`, `Now.del`, `Now.ID`, the data helpers (`Duration`, `TemplateValue`, etc.), and the `$override` escape hatch. Each has its own guide in this section — read them once, since they apply no matter which API you're calling in a `.now.ts` file. Every doc in this section shares the `fluent-language` tag, so `now-sdk explain fluent-language` returns the whole set at once.

## Getting started

If you haven't scaffolded a project yet, start with the Developing ServiceNow Apps with the Now SDK guide — it covers `init`, writing your first `.now.ts` file, and the build/install loop. This page is about why Fluent looks the way it does; that one is the step-by-step walkthrough.

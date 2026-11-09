Version: 4.14.0

# Getting Started with the ServiceNow SDK and Fluent

A concise walkthrough for going from zero to a deployed app with the ServiceNow SDK: scaffold a project (new or existing), author metadata with Fluent, then build and deploy to an instance.

## Why the SDK?

ServiceNow apps are normally built by clicking through Studio or Forms on the ServiceNow instance and making changes through the UI in low/no code fashion. That works, but it's hard to code-review, hard to diff, and easy to lose track of what changed. The SDK lets you define that same metadata as Fluent code which is a subset of Typescript, so you get version control, IDE autocomplete, type checking, and a real build step, all before anything touches an instance.

## What is Fluent?

Fluent is the TypeScript-based language you'll actually be writing — a typed DSL that maps directly to ServiceNow metadata like tables, business rules, and ACLs. See The Fluent Language for the full picture of what it is, why it's designed the way it is, and how it compares to XML-based development.

## Prerequisites

- Node.js 20+ and npm

- A ServiceNow instance (a PDI works fine) with admin access

- Basic familiarity with TypeScript and pro code tooling

### Authentication

Before you can `init` from an instance or `install` an application, you need to authenticate to that instance and store those credentials on your local computer.

```
npx @servicenow/sdk auth --add <instance-url>
```

This will start an interactive session and creates a default credential in your computer's credential store, used for any communication with the instance. If you wish to specify which credential alias and instance to use when running commands with the sdk, use the `--auth <alias>` argument on any command that interacts with an instance.

To see what credentials you have stored locally, use `--list`:

```
npx @servicenow/sdk auth --list
```

For CI/CD or agent-driven setups where an interactive prompt isn't possible, pass credentials directly instead: `--username` skips the username prompt, and `--password-stdin` pipes the password through stdin (same pattern as `docker login --password-stdin`):

```
echo "$SN_PASSWORD" | npx @servicenow/sdk auth --add <instance-url> \
    --type basic --alias <alias> --username <user> --password-stdin
```

Credentials end up stored exactly the same way as the interactive flow. The password never appears in `ps`, shell history, or log files. `--password-stdin` only applies to `--type basic`; it's ignored for `--type oauth`, which uses a browser-based code grant instead.

## 1. Scaffold a project

Every project starts with `init`. Run it with `npx` so you don't need a global install — it always pulls the latest SDK.

### New application

```
npx @servicenow/sdk init \
  --appName "My App" \
  --packageName "my-app" \
  --scopeName "x_acme_my_app"
```

Omit the flags to answer prompts interactively instead. Either way, `init` writes files into your current directory — create an empty folder first if you don't want to mix it with anything else.

Why a scope name? ServiceNow apps live in a scope (`x_<company_code>_<app_name>`) so their tables, roles, and scripts don't collide with the base platform or other apps. Find your company code under the `sn_appauthor.all_company_keys` system property, your application scope must begin with this for install to work.

### Existing application (bring it into the SDK)

Already have an app on an instance? Turning your scoped app into Fluent can be done with `init` and the `--from` argument, to download your existing application.  This will preserve it as xml in the metadata folder, so there are no changes to Fluent code yet and your application is unchanged but ready for Fluent development.

Configure your authentication if you have not done so already with the instance you wish to use.

Use `init` to initialize from an existing application:

```
npx @servicenow/sdk init --from <sys_id_of_sys_app_record>
```

This scaffolds the project locally and pulls the app's metadata down as XML into a `metadata/` folder. You can optionally convert any of that to Fluent — see Convert XML in your metadata folder to Fluent below.

### Finish setup

```
npm install
```

You should now have a project that looks roughly like this:

```
metadata/**/*.xml      # Existing XML metadata for your applications
src/
  fluent/              # Fluent files go here
    generated/
      keys.ts          # Keys file for storing metadata sys_id values
now.config.json        # App scope, name, and other application level configuration
package.json
```

`now.config.json` holds your app's scope and name — not instance connection info, which is managed separately via `auth`:

```
{
  "scope": "x_acme_my_app",
  "scopeId": "26571502d0a642339adf60a7edf6fab9",
  "name": "My App",
  "tsconfigPath": "./src/server/tsconfig.json"
}
```

Run `npx @servicenow/sdk dependencies` any time to fetch TypeScript type definitions for platform APIs and tables on your connected instance — this is what powers IDE autocomplete for `GlideRecord<'incident'>` and similar types.

## 2. Write metadata with Fluent

By default, Fluent metadata is stored as `.now.ts` files in your `src/fluent/` folder (configurable in `now.config.json`). Each one calls typed functions imported from `@servicenow/sdk/core` — the same way you'd write any TypeScript module.  Fluent is a statically analyzed language that gets transformed into a ServiceNow installable artifact.  The Fluent code you write will not be run locally, and dynamic features such as if/else and for loops will not compile. See The Fluent Language to learn more about why Fluent is designed this way.

```
// src/fluent/business-rules/uppercase-short-description.now.ts
import { BusinessRule } from '@servicenow/sdk/core'

BusinessRule({
    $id: Now.ID['uppercase-short-description'],
    name: 'Uppercase Short Description',
    table: 'incident',
    when: 'after',
    action: ['insert', 'update'],
    script: `(current) => {
        current.short_description = current.short_description.toString().toUpperCase()
    }`,
})
```

If you scaffolded from an existing app (`init --from`), its records are sitting in `metadata/` as raw XML. Converting that to Fluent is optional but recommended — see Convert XML in your metadata folder to Fluent below.

## 3. Build

```
npm run build
```

This compiles and validates every `.now.ts` file — checking references, types, and structure — and writes deployable output locally. Nothing touches your instance yet.

Why a separate build step? Catching a bad reference or malformed definition here is instant and free. Catching it after deploying to an instance means digging through an update set. Fix build errors before moving on.

## 4. Install

Push the most recent build output to the instance you authenticated against in the Prerequisites section

```
npm run deploy
```

Always rebuild before you install. `install` doesn't rebuild for you — if `build` failed, address that before running `install`.

## The loop

Once the project is set up, day-to-day work is just:

- Edit or add `.now.ts` files (and any server scripts they reference).

- `npm run build`

- `npm run deploy`

- Check the result on your instance, repeat.

## CLI Commands Reference

The commands you'll use most:

| Command | Purpose |
| `auth` | Authenticate. `--add <url>` to add, `--list` to check, `--use <alias>` to set default. |
| `build` | Compile Fluent source files. Validates syntax and reports errors. |
| `install` | Push built artifacts to the instance. Requires prior `auth` . |
| `transform` | Convert existing instance records or metadata XML into Fluent source. |

See the CLI Reference for every command and flag, including `query`, `dependencies`, `explain`, and `pack`.

## Keeping Fluent in sync

Fluent code and the instance can drift apart — someone edits a record through Studio, or you have XML in your metadata folder you wish to convert to Fluent or update existing Fluent code with the changes. `transform` handles both cases.

### Pull changes made directly on the instance

If a record was changed on instance in Studio (or anywhere else) instead of through Fluent, run `transform` with no `--from` flag. It reads directly from your authenticated instance and updates the matching `.now.ts` files locally:

Note: This will overwrite any local changes, so stash or commit first if needed

```
now-sdk transform
```

Scope it to specific records instead of the whole app with `--table` (and optionally `--id` for a single record):

```
npx @servicenow/sdk transform --table sys_script --id <sys_id>
```

### Convert XML in your metadata folder to Fluent

The SDK bundles any XML in your `metadata/` folder into the build to include with your app — it doesn't need to be converted to build and deploy. If you wish to convert it to Fluent, use the `transform` command with the `--from` argument:

```
#For All Files:
npx @servicenow/sdk transform --from ./metadata

##Individual File:
npx @servicenow/sdk transform --from ./metadata/path_to_xml_file.xml
```

Why convert instead of leaving it as XML? Untransformed XML still builds and deploys fine, but you lose the type checking, autocomplete, and diffability that make Fluent worth using. Transform incrementally — a directory, or the whole app — whenever you're ready to work on a given piece.

Converted files move into your Fluent source tree and are removed from `metadata/` once the conversion succeeds.

## Git is your source of truth

Everything in this guide is designed to be committed to Git — `.now.ts` files, server scripts (`.js`, `.html`, `.ts`, etc), `now.config.json`, `package.json`, and any XML in `metadata/`. Once your app is converted to Fluent and the SDK is used for development, Git, not a developer instance, is the source of truth for your application's state — the same as any modern application development paradigm.

Why does this matter? Storing application state on a developer instance means the "real" version of your app can be in an unreliable state based on whatever changes someone last made, with no history, no review, and no way to reliably reproduce it elsewhere. Treating Git as the source of truth is what makes proper SDLC — code review, branching, promotion through environments — possible at all. A developer instance should be treated as disposable and reproducible from Git, not as the record of what your app actually is.

In practice, this means:

- Commit `.now.ts` changes (and any XML you haven't converted yet) as you go — don't let uncommitted state accumulate on a single instance.

- Treat `transform` (pulling instance changes back into Fluent) as the bridge back to Git whenever a change was made outside your normal flow, not as a substitute for committing.

- Merge changes through a pull request, not a direct push, and let a pipeline — not a developer running `install` by hand — build and promote that merged code into your next instance (e.g. dev → test). This gives you review and a repeatable, auditable path onto each environment.

- From there, use App Repo and your CI/CD system (`now-sdk cicd`) to move the packaged application the rest of the way through your environments (e.g. test → prod), rather than promoting from the dev instance.

See SDLC on ServiceNow and CI Integration below for how this fits into a full pipeline.

## Where to go next

- The Fluent Language — what Fluent is, why it's designed this way, and its core principles

- Fluent Overview — cheat sheet of cross-cutting language constructs to know before writing any `.now.ts` file

- Dependencies — download type definitions for your application's tables, roles, and Script Includes

- SDLC on ServiceNow — the end-to-end SDLC whitepaper: planning, sandboxes, testing, and release with the SDK

- CI Integration — automating build, install, and promotion in a CI/CD pipeline

- Official docs: ServiceNow SDK

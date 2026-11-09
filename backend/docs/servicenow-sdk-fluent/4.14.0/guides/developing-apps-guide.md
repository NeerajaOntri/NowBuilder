Version: 4.14.0

# Developing ServiceNow Apps with the Now SDK

Guide for ServiceNow app development using the Now SDK: project setup, fluent authoring, build/deploy workflow, and CLI reference. Start here when working on a new ServiceNow application or with the Now SDK before consulting artifact-specific guides.

## When to Use

- Setting up a new ServiceNow application project from scratch

- Working with the ServiceNow SDK (`@servicenow/sdk`) CLI commands

- Scaffolding project structure, modules, or fluent definitions

- Building, deploying, or iterating on a ServiceNow app locally

- Authenticating the SDK against a ServiceNow instance

- Answering questions about SDK capabilities, fluent language, or project configuration

## Prerequisites

- Node.js 20 or later (LTS recommended)

- npm (bundled with Node.js)

- Access to a ServiceNow instance (PDI or enterprise) with admin or developer credentials

## Installation

### Non-Interactive Scaffolding (Recommended for Agents)

The scope name must be formatted as `x_<vendor_prefix>_<app_name>`, where `<app_name>` should reflect the name of the app being created, and the entire scope name (including the `x_` prefix) is capped at 18 characters and must match the pattern `(x|sn)_[a-z0-9_]+`.

MUST: `init` does not look up the vendor prefix or check for scope-name collisions on its own — run both of these queries yourself and pick your `--scopeName` from their results before invoking `init` (see the `query` topic for how to run a query):

- Query the `sys_properties` table for `name=glide.appcreator.company.code` and read its `value` to get the vendor prefix. If empty, use the generated name at your own risk.

- Query the `sys_scope` table filtered by `scope=<candidate_name>` to confirm it's free. A matching record means the scope already exists — pick a different app name or confirm you intend to target that existing app. Skipping this turns a silent collision into a conflicting install later.

Create a new application:

```
npx @servicenow/sdk init \
  --appName "My App" \
  --packageName "my-app" \
  --scopeName "x_my_app" \
  --template "base"
```

Convert an existing application from an instance:

```
npx @servicenow/sdk init --from <sys_id_of_sys_app_record>
```

Use `--auth <alias>` to pick which stored credentials to use instead of the default (see Authentication). See Converting Existing Applications below for converting from an existing repo instead, and for turning the pulled-down XML into Fluent.

`init` creates files in the current working directory. It does not create a subdirectory.

After scaffolding, install dependencies:

```
npm install
```

MUST: Do not run `npm run deploy` (or `now-sdk install`) right after scaffolding. Tell the user their application is scaffolded and ready for development. Only run `npm run deploy` later, once they're ready to push changes to their instance (see Build & Install Cycle).

### Interactive Scaffolding

```
npx @servicenow/sdk init
```

Prompts for app scope, name, and target instance. Run `npm install` after completion, then let the user know the app is ready for development — don't run `npm run deploy` until they ask to install it to their instance.

## CLI Commands Reference

| Command | Purpose |
| `init` | Scaffold a new project. Flags: `--appName` , `--packageName` , `--scopeName` , `--template` . |
| `auth` | Authenticate. `--add <url> --type basic|oauth` to add, `--list` to check, `--use <alias>` to set default. |
| `build` | Compile fluent source files. Validates syntax and reports errors. |
| `install` | Push built artifacts to the instance. Requires prior `auth` . |
| `transform` | Convert XML metadata into fluent source ( `--from` ), or pull live changes made directly on an instance back into `.now.ts` files (no `--from` ). |
| `download` | Download specific records or update sets from an instance. |
| `query` | Query instance data via Table API. Use `-o json` for structured output. See query-guide.md . |
| `dependencies` | Fetch TypeScript type definitions for platform APIs. |
| `clean` | Remove build output and cached artifacts. |
| `pack` | Package the app into a ZIP with update set XML and `package_inventory.csv` (SHA-256 manifest). |

## Project Structure

```
src/
  fluent/
    index.now.ts           # Main fluent entry point
    example.now.ts         # Example fluent definition
    tsconfig.json          # Fluent TypeScript config
  server/
    script.ts              # Example server-side script
    tsconfig.json          # Server TypeScript config
now.config.json            # App metadata: scope, scopeId, name
package.json
```

Organize artifacts by type using kebab-case naming:

```
src/fluent/
  business-rules/
    my-rule.now.ts
  client-scripts/
    my-script.now.ts
```

### now.config.json

```
{
  "scope": "x_my_app",
  "scopeId": "26571502d0a642339adf60a7edf6fab9",
  "name": "My App"
}
```

Does not contain instance connection info -- that is managed via `auth`.

See now.config.json reference

## Development Workflow

- `init` -- Scaffold the project (one-time).

- `npm install` -- Install SDK and dependencies (one-time).

- `auth` -- Authenticate against your instance (or verify existing auth with `--list`).

- Write fluent -- Create `.now.ts` files under `src/fluent/`. Write server module scripts in `src/server/` or with Now.include.

- `build` -- Compile and validate fluent definitions.

- `install` -- Install compiled artifacts on the instance.

- Iterate -- Repeat steps 4-6.

For brownfield projects, use `init --from` to pull down existing app metadata as XML, then `transform` to convert it into Fluent source (see Converting Existing Applications below).

### Build & Install Cycle

After writing or editing fluent definitions, run the build then the deploy command. This is the core inner-loop you repeat on every change when ready to push changes to an instance

Prefer the `package.json` npm scripts over the underlying `now-sdk build` / `now-sdk install` commands — a complete application may have additional build steps wired into those scripts.

```
# 1. Compile and validate fluent source into deployable artifacts
npm run build

# 2. Push the built artifacts to the authenticated instance
npm run deploy
```

- `npm run build` (runs `now-sdk build`) transpiles the SDK project and writes the output artifacts. Build errors (invalid references, type mismatches, malformed definitions) are reported here -- fix them before deploying.

- `npm run deploy` (runs `now-sdk install`) deploys the most recent build output to the instance selected via `auth`. It requires a prior successful `build` and valid credentials to be configured already.

- MUST: Ensure build has passed before deploying! A failed build leaves the previous artifacts in place, so deploying without rebuilding pushes stale output.

## Converting Existing Applications

### From an Instance

See Non-Interactive Scaffolding above for converting a scoped application already installed on an instance (`init --from <sys_id>`).

### From an Existing Repository

If the app already has a git repo with XML metadata:

```
npx @servicenow/sdk init --from <path_to_repo>
```

Existing metadata XML and supporting files are placed inside the `metadata` folder, and fluent configuration files are added alongside them.

### Converting XML to Fluent DSL

After initializing from an instance or repo, application metadata will be in the `metadata` folder in its original XML form. Use `transform` to convert XML files into Fluent code:

```
# Transform a single file
npx @servicenow/sdk transform --from metadata/update/sys_script_<sys_id>.xml

# Transform the whole app at once
npx @servicenow/sdk transform --from .

# Transform a specific directory
npx @servicenow/sdk transform --from metadata/update
```

Transformed files are scaffolded into the generated directory (configurable in `now.config.json`) and removed from `metadata` upon successful conversion.

Note: Records that exist as both a fluent entity (`.now.ts` file) and an XML file in `metadata` will use the XML version on `build`. Remove converted XML files to avoid conflicts.

Run `npx @servicenow/sdk transform --help` for the full list of options.

### Pulling Changes Made Directly on an Instance

`transform` isn't only for one-time XML conversion — it also keeps Fluent in sync with changes made outside of it. If a record was edited in Studio (or anywhere else on the instance) instead of through Fluent, run `transform` with no `--from` flag. It reads directly from your authenticated instance and updates the matching `.now.ts` files locally:

```
npx @servicenow/sdk transform
```

Note: This overwrites local changes to any record it updates — commit or stash first if you have uncommitted work.

Scope it to specific records instead of the whole app with `--table` (and optionally `--id` for a single record):

```
npx @servicenow/sdk transform --table sys_script --id <sys_id>
```

## Authentication

### Checking Existing Credentials

```
npx now-sdk auth --list
```

### Adding Credentials (Interactive)

```
npx now-sdk auth --add <instance-url> --type <basic|oauth>
```

- `basic`: Username and password. Suitable for local development and PDIs.

- `oauth`: OAuth-based. Suitable for enterprise instances.

Prompts for alias, username, and password. Credentials are encrypted and stored in
`~/.now-sdk/credentials.enc`, with only the encryption key kept in your OS keychain or
credential manager. Override the storage location with the `SN_SDK_CREDENTIALS_DIR`
environment variable.

Credentials are stored per-user, not per-project. If you have multiple projects on the
same machine pinned to different `now-sdk` versions spanning this change, an older
version won't see credentials added or changed via a newer version, and vice versa —
run `now-sdk auth --add` again under whichever version needs them.

### Setting a Default

```
npx now-sdk auth --use <alias>
```

### Adding Credentials (Non-Interactive)

Pass `--username` to skip the username prompt and `--password-stdin` to pipe the password through stdin instead of being prompted. Useful for agent-driven setup (Claude Code, scripts) where typing into the prompt isn't possible. Same pattern as `docker login --password-stdin`:

```
echo "$SN_PASSWORD" | npx now-sdk auth --add <instance-url> \
    --type basic --alias <alias> --username <user> --password-stdin
```

Credentials are stored exactly the same way as the interactive flow — subsequent `now-sdk deploy --auth <alias>` calls work as expected. The password never appears in `ps`, shell history, or log files.

`--password-stdin` only applies to basic auth; with `--type oauth` it is ignored (OAuth uses a browser-based code grant). Empty stdin or running with `--password-stdin` outside a pipe produces a clear error rather than hanging.

### Multi-Factor Authentication (Basic Auth)

If a basic-auth instance enforces MFA, the CLI prompts for your 6-digit TOTP code (from your authenticator app) during login — the input is masked and submits automatically once you've typed 6 digits, no need to press Enter:

```
? Enter MFA code (6 digits): ******
```

Basic auth negotiates a fresh session on every command (not just `auth --add`), so this prompt can appear on any command that authenticates — `deploy`, `install`, `query`, etc. — whenever the current session has expired. A rejected code is retried up to 3 times before the command fails.

Each code can only be used once. ServiceNow rejects a TOTP code that's already been submitted, even if it's technically still within its 30-second validity window — this is standard anti-replay protection, not a bug. If you re-run a command quickly and reuse the same code, expect it to fail; wait for your authenticator app to generate a new code for each attempt.

This prompt requires an interactive terminal. In a non-interactive context (CI/CD, scripts, `--password-stdin`), an MFA challenge fails immediately with a clear error — use a pre-authenticated session via `SN_SDK_SESSION_TOKEN` / `SN_SDK_SESSION_COOKIE` instead (see auth-token-guide.md and CI Integration below).

### Non-Interactive (CI/CD)

See CI Integration 'ci-integration' topic for more information

## Key Concepts

### Fluent Language

See the `fluent-language-overview` topic for what Fluent is and why it's designed this way. In practice, defining an artifact looks like this:

```
import { BusinessRule } from '@servicenow/sdk/core'
import { myScriptFunction } from '../server/script'

BusinessRule({
  $id: Now.ID['my-rule'],
  name: 'Uppercase Short Description',
  table: 'incident',
  when: 'after',
  action: ['insert', 'update'],
  order: 100,
  script: myScriptFunction,
})
```

- The `Now` global (e.g. `Now.ID[...]`) is available with no import — the SDK registers it automatically during build and through the language server.

- Import artifact types from `@servicenow/sdk/core`.

- Server-side logic is written as functions in `src/server/` and passed via the `script` property.  See `module` topic for more information

### TypeScript Types

Run `npx now-sdk dependencies` to fetch type definitions for platform APIs and tables on the connected ServiceNow instance, enabling IDE autocompletion.

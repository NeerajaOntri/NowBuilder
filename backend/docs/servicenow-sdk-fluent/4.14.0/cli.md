Version: 4.14.0

# now-sdk CLI Reference

Reference documentation for every `now-sdk` command

## auth

Authenticate to an instance and store, update, view, or print user credentials for
accessing an instance on your system. Credentials are encrypted (AES-256-GCM) and stored
in `~/.now-sdk/credentials.enc`, with only the encryption key kept in your OS keychain or
credential manager — passwords and long-lived secrets (refresh tokens) are never printed
by `--list` or `--print`. Override the storage location with the `SN_SDK_CREDENTIALS_DIR`
environment variable. Exactly one of `--add`, `--delete`, `--use`, `--list`, or `--print`
is required.

The alias set with `--add --alias` (or chosen interactively) can be passed to the
`--auth` flag of `init`, `transform`, `dependencies`, `install`, `download`, `query`, and `exec`
to select which stored credentials to use.

Mutually exclusive: `--add`, `--delete`, `--use`, `--list`, `--print` (exactly one required)

Usage

```
now-sdk auth --add https://<instancename>.service-now.com --type basic
now-sdk auth --delete bar
now-sdk auth --use bar
now-sdk auth --list
now-sdk auth --print
```

| Flag | Alias | Type | Required | Default | Description |
| `--add` |  | string | no | - | Instance name or url to store authentication credentials for |
| `--delete` |  | string | no | - | Alias of authentication credential to delete |
| `--use` |  | string | no | - | Alias of authentication credential to use by default |
| `--list` |  | boolean | no | - | List all available authentication credentials |
| `--print` |  | string | no | - | Print a live auth token for the given alias (or the default credential if omitted) for use in manual API calls |
| `--format` |  | string | no | `headers` | Output format for `--print` (choices: `headers` , `bearer` , `env` ) |
| `--type` |  | string | no | - | Type of authentication to use for new authentication credential (choices: `basic` , `oauth` ) |
| `--alias` |  | string | no | - | The alias to use for new authentication credential |

`--print` writes a live, short-lived auth token to stdout. It resolves the credential the same
way the instance-touching commands do (refreshing OAuth, negotiating a basic-auth session).

For worked examples, run `now-sdk explain auth-token-guide`.

## init

Initialize a new ServiceNow custom application, apply a template to an existing
application, or convert a legacy ServiceNow application from an instance or directory
within the current directory structure.

Mutually exclusive: `--from` vs. `--scope-name`/`--app-name`

Usage

```
now-sdk init
now-sdk init --app-name "My App" --scope-name x_myco_app --package-name my-app
now-sdk init --from <sys_id-or-path>
```

| Flag | Alias | Type | Required | Default | Description |
| `--from` |  | string | no | - | SYS_ID of a legacy application from instance or file path to a directory containing legacy Scoped App to convert into a fluent App (conflicts with `--scope-name` / `--app-name` ) |
| `--app-name` |  | string | no | - | Name of ServiceNow App project |
| `--package-name` |  | string | no | - | Package Name for the project, must follow npm naming conventions |
| `--scope-name` |  | string | no | - | Scope name (must start with vendor prefix if applicable and cannot be greater than 18 characters) |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--template` |  | string | no | - | Template to use for the project (choices are dynamically generated from available project templates; see below) |

After `init`, install the project's third-party dependencies with your package manager
(e.g. `npm install`) before running `now-sdk build`.

## download <directory>

Download all application metadata (XML) from an application on an instance, unpacked
into the given directory — useful for comparing against the metadata in your local
application. Use a directory other than your project's `metadata` directory. Updates to
JavaScript modules are not included when downloading application metadata from an
instance.

Usage

```
now-sdk download ./downloaded-app
now-sdk download ./downloaded-app --incremental
```

| Parameter | Type | Required | Description |
| `<directory>` | string | yes | Path to expand application |

| Flag | Alias | Type | Required | Default | Description |
| `--source` |  | string | no | current directory | Path to the directory that contains package.json configuration |
| `--incremental` |  | boolean | no | `false` | Download application metadata from the instance in incremental mode |

## build [source]

Compile sources into app files and generate installable package.

Usage

```
now-sdk build
now-sdk build --frozen-keys
```

| Parameter | Type | Required | Description |
| `[source]` | string | no | Path to the directory that contains package.json configuration (default: current directory) |

| Flag | Alias | Type | Required | Default | Description |
| `--frozen-keys` |  | boolean | no | `false` | Validate that Keys/SysIds are up to date for CI build |
| `--error-on-conflict` |  | boolean | no | `false` | Treat sys_id conflicts between Fluent and XML as errors instead of warnings (Fluent-to-Fluent conflicts are always errors) |
| `--skip-clean` |  | boolean | no | `false` | Skip cleaning build output directories before building |
| `--legacy-choices` |  | boolean | no | - | Generate choice set XML with sys_choice_set wrapper (v3 destructive behavior) instead of sys_choice_v2 (v4 additive merge) |
| `--source-map` |  | boolean | no | `false` | Generate a source-manifest.json in the output directory mapping build output back to source |

`--frozen-keys` compares `src/fluent/generated/keys.ts` before and after the build (the
file is always regenerated on build). If it changed and `--frozen-keys` is set, the
build fails with "Keys file is out-of-date" — re-run the build without `--frozen-keys`
to update it and commit the result.

## install

Install or update application on instance.

Usage

```
now-sdk install
now-sdk install --auth my-instance --reinstall
```

| Flag | Alias | Type | Required | Default | Description |
| `--source` |  | string | no | current directory | Path to the directory that contains package.json configuration |
| `--reinstall` | `-r` | boolean | no | `false` | Uninstall and reinstall the application on the instance to ensure metadata on instance matches installation package. Warning: metadata created on-instance that is not present locally will be lost |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--open-browser` | `-b` | boolean | no | `false` | Open sys_app page in the default browser on successful install |
| `--info` | `-i` | boolean | no | `false` | Get information from instance for most recent install of this app |
| `--async` |  | boolean | no | `true` | Install the app asynchronously (falls back to synchronous install if not supported) |
| `--demo-data` |  | boolean | no | `true` | Install demo data |
| `--skip-flow-activation` |  | boolean | no | `false` | Skip activating (publishing) flows after install |

## dependencies [sysIds..]

Download configured dependencies in now.config.json and typescript type definitions for
use in the application.

Mutually exclusive: `--type-defs-only` vs. `--fluent-only`

Usage

```
now-sdk dependencies
now-sdk dependencies --type-defs-only
now-sdk dependencies --add tables incident problem --scope global
now-sdk dependencies --add sys_security_acl "*" --scope x_my_app
```

| Parameter | Type | Required | Description |
| `[sysIds..]` | string[] | no | System IDs to add when using `--add` flag |

| Flag | Alias | Type | Required | Default | Description |
| `--directory` |  | string | no | current directory | Path to the directory that contains package.json configuration |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--type-defs-only` |  | boolean | no | - | Download only script type definitions (glide.*.d.ts) (conflicts with `--fluent-only` ) |
| `--fluent-only` |  | boolean | no | - | Download only fluent types from now.config.json dependencies (conflicts with `--type-defs-only` ) |
| `--add` |  | string | no | - | Add new dependency items; requires `--scope` and at least one sys_id/ `*` positional |
| `--scope` |  | string | no | - | Scope for dependencies (e.g., global, x_my_app). Required when using `--add` |

`--add` accepts either a raw table name (e.g. `sys_security_acl`) or one of these
recognized aliases: `tables` (→ `sys_db_object`), `roles` (→ `sys_user_role`),
`actions`/`triggers`/`subflows` (automation content). Note these aliases are plural
only — `table`/`role` (singular) are not recognized. Pass `"*"` as the sole positional
to add every item of that table/alias from the given `--scope` instead of listing sys_ids
individually, e.g. `now-sdk dependencies --add tables "*" --scope global`.

## transform

Download and convert XML records from instance or from a local path into Fluent source
code.

Mutually exclusive: `--from` vs. `--auth` (offline file transform vs. online instance transform)

Usage

```
now-sdk transform --auth my-instance
now-sdk transform --from ./legacy-update-set.xml
now-sdk transform --table sys_script
```

| Flag | Alias | Type | Required | Default | Description |
| `--from` |  | string | no | - | Path to local XML file(s)/directory to transform (conflicts with `--mode` / `--auth` ) |
| `--directory` |  | string | no | current directory | Path to the directory that contains package.json configuration |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--format` | `-f` | boolean | no | `true` | Automatically format new and updated source code after transforming |
| `--table` |  | string | no | - | Comma-separated table names to transform by table hierarchy. When used with `--id` , transforms a specific record with its relationships. (Table-based Transform group; requires `--table` for `--force` ) |
| `--force` |  | boolean | no | `false` | Allow transforming descendant tables without their parent hierarchy (use with `--table` ) |

## clean [source]

Clean output directory.

Usage

```
now-sdk clean
```

| Parameter | Type | Required | Description |
| `[source]` | string | no | Path to the directory that contains package.json configuration (default: current directory) |

No additional options.

## pack [source]

Zip built app into installable artifact.

Usage

```
now-sdk pack
```

| Parameter | Type | Required | Description |
| `[source]` | string | no | Path to the directory that contains package.json configuration (default: current directory) |

| Flag | Alias | Type | Required | Default | Description |
| `--skip-package-inventory` |  | boolean | no | `false` | Skip generating package_inventory.csv in the output |

`package_inventory.csv` is a manifest of SHA-256 file hashes for the packaged app, in
the same format ServiceNow's platform generates on-instance — useful for install/upgrade
tooling that needs to detect unchanged files without re-processing them.

## explain [topic]

Display documentation for a Fluent SDK topic — API reference, guides, or skills bundled
with the SDK. Search is by name, tag, or keyword; a topic name typically follows the
`<name>-api` (e.g. `businessrule-api`) or `<name>-guide` naming convention, but any
matching keyword works too.

Usage

```
now-sdk explain BusinessRule
now-sdk explain --list
now-sdk explain flow --list --peek
```

| Parameter | Type | Required | Description |
| `[topic]` | string | no | Topic name or keyword to search for |

| Flag | Alias | Type | Required | Default | Description |
| `--list` | `-l` | boolean | no | - | List topics. Combine with a topic to filter (e.g., `--list flow` ) |
| `--format` |  | string | no | `pretty` | Output format: `pretty` for terminal, `raw` for plain markdown (choices: `pretty` , `raw` ) |
| `--peek` | `-p` | boolean | no | - | Show a brief summary instead of the full document |

## query <table>

Query records from a ServiceNow table on the instance.

Usage

```
now-sdk query incident --query "active=true^priority<=2" --limit 10
now-sdk query sys_user --fields name,email --output json
```

| Parameter | Type | Required | Description |
| `<table>` | string | yes | ServiceNow table name (e.g. incident, sys_user) |

| Flag | Alias | Type | Required | Default | Description |
| `--query` | `-q` | string | yes | - | Encoded query string (sysparm_query), e.g. `"active=true^priority<=2"` |
| `--limit` |  | number | no | `100` | Maximum records per page (sysparm_limit) |
| `--offset` |  | number | no | `0` | Starting offset (sysparm_offset) |
| `--fields` | `-f` | string | no | - | Comma-separated list of fields to return (sysparm_fields) |
| `--display-value` |  | string | no | `false` | Return display values (sysparm_display_value): `true` , `false` , or `all` for both (choices: `true` , `false` , `all` ) |
| `--exclude-reference-link` |  | boolean | no | `true` | Exclude reference link metadata (sysparm_exclude_reference_link) |
| `--no-count` |  | boolean | no | `false` | Skip total count calculation for better performance (sysparm_no_count) |
| `--timeout` |  | number | no | `30000` | Per-request timeout in milliseconds. Each page fetch is bounded by this value |
| `--view` |  | string | no | - | UI view to determine which fields to return (sysparm_view) |
| `--query-category` |  | string | no | - | Query category for extended queries (sysparm_query_category) |
| `--query-no-domain` |  | boolean | no | `false` | Ignore domain separation when querying (sysparm_query_no_domain) |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--output` | `-o` | string | no | - | Output format: `json` for a machine-readable envelope, `raw` to unquote the `--select` result (choices: `json` , `raw` ) |
| `--select` | `-s` | string | no | - | Dot/bracket path to extract from the output (e.g. `"records[0].sys_id"` ). Implies machine-readable output; pair with `--output raw` for direct use in shell command substitution |

## exec [script]

Execute a script on the instance. The script runs server-side through the same processor as the platform's Scripts - Background page, and its output is printed line by line. Exits non-zero if the script reports an error.

Aliases: `execute`

Pass `--output json` or `--select` for scripting: that silences the status logging so stdout carries only the result. Add `--server-logs` to also see the instance's session log, including stack traces.

The script is taken from the positional argument, `--file`, or piped stdin, in that order. Scripts still running after four hours are cancelled by the instance.

Every run is recorded on the instance's own Script Execution History, under the authenticated user, and both that record and the rollback context it produced are printed as links. `--reason` is appended to the script as a comment, so why the script was run is stored alongside it.

Mutually exclusive: `[script]` vs. `--file`

Defaults from the local project: `--scope` defaults from `now.config.json` (`scopeId`) when run inside a Fluent project

Usage

```
now-sdk exec "gs.info(gs.getProperty('glide.buildname'))"
now-sdk exec --file ./scripts/backfill.js --scope x_acme_app
now-sdk exec --reason "backfill missing priority values" --file ./scripts/backfill.js
now-sdk exec --server-logs --file ./scripts/backfill.js
cat ./scripts/backfill.js | now-sdk exec
BUILD=$(now-sdk exec "gs.info(gs.getProperty('glide.buildname'))" --select output[0] --output raw)
```

| Parameter | Type | Required | Description |
| `[script]` | string | no | Script to run on the instance. Omit to read from `--file` or piped stdin |

| Flag | Alias | Type | Required | Default | Description |
| `--file` | `-f` | string | no | - | Path to a file containing the script to run |
| `--scope` |  | string | no | `scopeId` from `now.config.json` | Scope to run the script in: an application sys_id, a scope name, or `global` . An unknown scope is an error, never a silent fall back to global |
| `--reason` |  | string | no | - | Why the script is being run, recorded with it on the script's Script Execution History record |
| `--record-for-rollback` |  | boolean | no | `true` | Create a rollback context, so the script's record changes can be reverted from its Script Execution History record |
| `--timeout` |  | number | no | `300000` | How long to wait for the script's response, in milliseconds. Giving up stops the CLI waiting, not the script, which runs to completion on the instance |
| `--server-logs` |  | boolean | no | `false` | Print the instance's session log for the run, including stack traces. With `--output json` , adds it to the envelope as `log` |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--output` | `-o` | string | no | - | Output format: `json` for a machine-readable envelope ( `{ ok, scope, scopeId, output, errors, executionHistoryId, rollbackContextId, log? }` ), `raw` to unquote the `--select` result (choices: `json` , `raw` ) |
| `--select` | `-s` | string | no | - | Dot/bracket path to extract from the output (e.g. `"output[0]"` ). Implies machine-readable output; pair with `--output raw` for direct use in shell command substitution |

## cicd <command>

Run sn_cicd operations against an instance (test suites, app repo install/publish).

### cicd install

Install an application from the application repository onto the instance.

Mutually exclusive: `--scope` vs. `--app-sys-id`

Defaults from the local project: when run from inside a Fluent project directory
and neither `--scope` nor `--app-sys-id` is given, `--app-sys-id` is filled in
automatically from `now.config.json` (`scopeId`). If `--app-version` is also omitted, it
defaults from `package.json` (`version`). This lets `cicd install` run unchanged across
pipeline stages without hardcoding the app/version. See the
CI Integration guide
for a full promotion pipeline example.

Usage

```
now-sdk cicd install --app-sys-id <sys_id> --app-version 1.0.0
now-sdk cicd install --auth prod
```

| Flag | Alias | Type | Required | Default | Description |
| `--scope` |  | string | no | - | Scope name of the application to install, e.g. x_myapp_scope (conflicts with `--app-sys-id` ; prefer `--app-sys-id` when known) |
| `--app-sys-id` |  | string | no | - | sys_id of the application (sys_app) to install (conflicts with `--scope` ). Defaults from now.config.json (scopeId) when run inside a Fluent project and neither `--scope` nor `--app-sys-id` is given |
| `--app-version` |  | string | no | - | Version of the application to install. Defaults from package.json (version) when run inside a Fluent project |
| `--base-app-version` |  | string | no | - | Version of the base application to install alongside this application |
| `--auto-upgrade-base-app` |  | boolean | no | - | Automatically upgrade the base application if required |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--output` | `-o` | string | no | - | Output format: `json` for a machine-readable envelope, `raw` to unquote the `--select` result (choices: `json` , `raw` ) |
| `--select` | `-s` | string | no | - | Dot/bracket path to extract from the output (e.g. `"result.links.progress.id"` ). Implies machine-readable output; pair with `--output raw` for direct use in shell command substitution |
| `--wait` |  | boolean | no | `true` | Wait for the operation to finish by polling its progress |
| `--poll-timeout` |  | number | no | `900000` | Maximum time in milliseconds to wait for the operation to finish |

### cicd publish

Publish an application to the application repository.

Mutually exclusive: `--scope` vs. `--app-sys-id`

Defaults from the local project: same auto-defaulting as `cicd install` —
`--app-sys-id` from `now.config.json` (`scopeId`) and `--app-version` from
`package.json` (`version`) when omitted and run inside a Fluent project directory. See
the CI Integration guide.

Usage

```
now-sdk cicd publish --scope x_myco_app --app-version 1.0.1
now-sdk cicd publish --auth test
```

| Flag | Alias | Type | Required | Default | Description |
| `--scope` |  | string | no | - | Scope name of the application to publish (conflicts with `--app-sys-id` ; prefer `--app-sys-id` when known) |
| `--app-sys-id` |  | string | no | - | sys_id of the application (sys_app) to publish (conflicts with `--scope` ). Defaults from now.config.json (scopeId) when run inside a Fluent project and neither `--scope` nor `--app-sys-id` is given |
| `--dev-notes` |  | string | no | - | Developer notes to record for this published version |
| `--app-version` |  | string | no | - | Version to assign to the published application. Defaults from package.json (version) when run inside a Fluent project |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--output` | `-o` | string | no | - | Output format: `json` for a machine-readable envelope, `raw` to unquote the `--select` result (choices: `json` , `raw` ) |
| `--select` | `-s` | string | no | - | Dot/bracket path to extract from the output (e.g. `"result.links.progress.id"` ). Implies machine-readable output; pair with `--output raw` for direct use in shell command substitution |
| `--wait` |  | boolean | no | `true` | Wait for the operation to finish by polling its progress |
| `--poll-timeout` |  | number | no | `900000` | Maximum time in milliseconds to wait for the operation to finish |

### cicd rollback

Roll back an installed application to a previous version.

Mutually exclusive: `--scope` vs. `--app-sys-id`

Defaults from the local project: `--app-sys-id` defaults from `now.config.json`
(`scopeId`) when omitted and run inside a Fluent project directory, same as
`install`/`publish`. `--app-version` is not auto-defaulted — the target rollback
version can't be inferred from the current project state, so it must be specified
explicitly.

Usage

```
now-sdk cicd rollback --app-version 1.0.0
```

| Flag | Alias | Type | Required | Default | Description |
| `--scope` |  | string | no | - | Scope name of the application to roll back (conflicts with `--app-sys-id` ; prefer `--app-sys-id` when known) |
| `--app-sys-id` |  | string | no | - | sys_id of the application (sys_app) to roll back (conflicts with `--scope` ). Defaults from now.config.json (scopeId) when run inside a Fluent project and neither `--scope` nor `--app-sys-id` is given |
| `--app-version` |  | string | no | - | Version expected after the rollback completes. For rolling back an App Customization install, set this to the base application version expected afterward |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--output` | `-o` | string | no | - | Output format: `json` for a machine-readable envelope, `raw` to unquote the `--select` result (choices: `json` , `raw` ) |
| `--select` | `-s` | string | no | - | Dot/bracket path to extract from the output (e.g. `"result.links.progress.id"` ). Implies machine-readable output; pair with `--output raw` for direct use in shell command substitution |
| `--wait` |  | boolean | no | `true` | Wait for the operation to finish by polling its progress |
| `--poll-timeout` |  | number | no | `900000` | Maximum time in milliseconds to wait for the operation to finish |

### cicd testsuite run

Run an ATF test suite on the instance. Provide either `--test-suite-sys-id` or
`--test-suite-name`.

Mutually exclusive: `--test-suite-sys-id` vs. `--test-suite-name`

Usage

```
now-sdk cicd testsuite run --test-suite-name "My Test Suite"
```

| Flag | Alias | Type | Required | Default | Description |
| `--test-suite-sys-id` |  | string | no | - | sys_id of the test suite to run (conflicts with `--test-suite-name` ) |
| `--test-suite-name` |  | string | no | - | Name of the test suite to run (conflicts with `--test-suite-sys-id` ) |
| `--browser-name` |  | string | no | - | Browser to run UI-based tests in (choices: `any` , `chrome` , `firefox` , `edge` , `ie` , `safari` ) |
| `--browser-version` |  | string | no | - | Browser version to run UI-based tests in |
| `--os-name` |  | string | no | - | Operating system to run UI-based tests on |
| `--os-version` |  | string | no | - | Operating system version to run UI-based tests on |
| `--run-in-cloud` |  | boolean | no | `false` | Run the suite using the ATF Cloud Runner instead of a manual/scheduled client runner |
| `--is-performance-run` |  | boolean | no | `false` | Run the suite as a Performance Test instead of a standard functional test |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--output` | `-o` | string | no | - | Output format: `json` for a machine-readable envelope, `raw` to unquote the `--select` result (choices: `json` , `raw` ) |
| `--select` | `-s` | string | no | - | Dot/bracket path to extract from the output (e.g. `"result.links.progress.id"` ). Implies machine-readable output; pair with `--output raw` for direct use in shell command substitution |
| `--wait` |  | boolean | no | `true` | Wait for the operation to finish by polling its progress |
| `--poll-timeout` |  | number | no | `900000` | Maximum time in milliseconds to wait for the operation to finish |

### cicd testsuite watch

Wait for a previously started test suite run to complete, polling for status.

Usage

```
now-sdk cicd testsuite watch --progress-id <progress_id>
```

| Flag | Alias | Type | Required | Default | Description |
| `--progress-id` |  | string | yes | - | Progress id returned by `cicd testsuite run` |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--output` | `-o` | string | no | - | Output format: `json` for a machine-readable envelope, `raw` to unquote the `--select` result (choices: `json` , `raw` ) |
| `--select` | `-s` | string | no | - | Dot/bracket path to extract from the output (e.g. `"result.links.progress.id"` ). Implies machine-readable output; pair with `--output raw` for direct use in shell command substitution |
| `--wait` |  | boolean | no | `true` | Wait for the operation to finish by polling its progress |
| `--poll-timeout` |  | number | no | `900000` | Maximum time in milliseconds to wait for the operation to finish |

### cicd testsuite result

Fetch a test suite run's detailed result (including child suite results) by its result
id.

Usage

```
now-sdk cicd testsuite result --result-id <result_id>
```

| Flag | Alias | Type | Required | Default | Description |
| `--result-id` |  | string | yes | - | sys_id of the test suite result, typically the links.results.id reported by `cicd testsuite run` |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--output` | `-o` | string | no | - | Output format: `json` for a machine-readable envelope, `raw` to unquote the `--select` result (choices: `json` , `raw` ) |
| `--select` | `-s` | string | no | - | Dot/bracket path to extract from the output (e.g. `"result.links.progress.id"` ). Implies machine-readable output; pair with `--output raw` for direct use in shell command substitution |

### cicd test run

Run a single ATF test on the instance and wait for its pass/fail result. Provide either
`--test-sys-id` or `--test-name`.

Mutually exclusive: `--test-sys-id` vs. `--test-name`

Usage

```
now-sdk cicd test run --test-name "My ATF Test"
```

| Flag | Alias | Type | Required | Default | Description |
| `--test-sys-id` |  | string | no | - | sys_id of the ATF test (sys_atf_test) to run (conflicts with `--test-name` ) |
| `--test-name` |  | string | no | - | Name of the ATF test (sys_atf_test) to run; resolved to a sys_id before starting (conflicts with `--test-sys-id` ). Fails if the name matches zero or more than one test |
| `--run-in-cloud` |  | boolean | no | - | Run UI-based steps on the ATF Cloud Runner instead of a scheduled client runner |
| `--capture-node-logs` |  | boolean | no | `false` | Capture node (browser) logs during the run |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--output` | `-o` | string | no | - | Output format: `json` for a machine-readable envelope, `raw` to unquote the `--select` result (choices: `json` , `raw` ) |
| `--select` | `-s` | string | no | - | Dot/bracket path to extract from the output (e.g. `"result.links.progress.id"` ). Implies machine-readable output; pair with `--output raw` for direct use in shell command substitution |
| `--wait` |  | boolean | no | `true` | Wait for the operation to finish by polling its progress |
| `--poll-timeout` |  | number | no | `900000` | Maximum time in milliseconds to wait for the operation to finish |

### cicd test watch

Wait for a previously started single ATF test run to finish, polling for its pass/fail
result.

Usage

```
now-sdk cicd test watch --progress-id <progress_id>
```

| Flag | Alias | Type | Required | Default | Description |
| `--progress-id` |  | string | yes | - | Progress id returned by `cicd test run` |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--output` | `-o` | string | no | - | Output format: `json` for a machine-readable envelope, `raw` to unquote the `--select` result (choices: `json` , `raw` ) |
| `--select` | `-s` | string | no | - | Dot/bracket path to extract from the output (e.g. `"result.links.progress.id"` ). Implies machine-readable output; pair with `--output raw` for direct use in shell command substitution |
| `--wait` |  | boolean | no | `true` | Wait for the operation to finish by polling its progress |
| `--poll-timeout` |  | number | no | `900000` | Maximum time in milliseconds to wait for the operation to finish |

### cicd test result

Fetch a single ATF test's result (status, output, link) by its result id.

Usage

```
now-sdk cicd test result --result-id <result_id>
```

| Flag | Alias | Type | Required | Default | Description |
| `--result-id` |  | string | yes | - | sys_id of the ATF test result (sys_atf_test_result), typically the resultId reported by `cicd test watch` |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--output` | `-o` | string | no | - | Output format: `json` for a machine-readable envelope, `raw` to unquote the `--select` result (choices: `json` , `raw` ) |
| `--select` | `-s` | string | no | - | Dot/bracket path to extract from the output (e.g. `"result.links.progress.id"` ). Implies machine-readable output; pair with `--output raw` for direct use in shell command substitution |

### cicd test logs

Fetch an ATF test result's logs, optionally filtered by a regular
expression.

Node logs only exist for a run started with `--capture-node-logs`. Logs are attached to
test results by default when there is a test failure. Searching a result
that has no logs fails with `No logs found for test result <result_id>`.

An invalid regex is reported by the server: `Invalid filter regex: <detail>`.

Usage

```
# All captured lines, up to --limit
now-sdk cicd test logs --result-id <result_id>

# Only lines matching a pattern.
now-sdk cicd test logs --result-id <result_id> --pattern 'error|fail'
```

| Flag | Alias | Type | Required | Default | Description |
| `--result-id` |  | string | yes | - | sys_id of the ATF test result (sys_atf_test_result) to search |
| `--pattern` |  | string | no | - | Regular expression to filter log lines by; only matching lines are returned. Omit to return all captured lines. |
| `--limit` |  | number | no | `100` | Maximum number of lines to return. |
| `--auth` | `-a` | string | no | - | Credential alias to use for authentication with instance |
| `--output` | `-o` | string | no | - | Output format: `json` for a machine-readable envelope, `raw` to unquote the `--select` result (choices: `json` , `raw` ) |
| `--select` | `-s` | string | no | - | Dot/bracket path to extract from the output (e.g. `"result.links.progress.id"` ). Implies machine-readable output; pair with `--output raw` for direct use in shell command substitution |

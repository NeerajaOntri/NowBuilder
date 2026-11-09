Version: 4.14.0

# Running Scripts on the Instance

`now-sdk exec` runs a server-side script on the authenticated ServiceNow instance, the same way the platform's Scripts - Background page does. Scripts run with your instance permissions and can change or delete data, so AI agents must always get the user's approval before running one.

```
now-sdk exec "<script>" [options]
now-sdk exec --file ./scripts/backfill.js [options]
cat ./scripts/backfill.js | now-sdk exec [options]
```

## Rules for AI agents

- Always ask the user before running `now-sdk exec`. Never run a script on your own initiative, even one that looks read-only. Before running, show the user:

- the full script (or the file path and its contents)

- the target instance (the credential alias, or the default)

- the scope it will run in (see Choosing the scope)

- the flags you intend to pass, especially `--no-record-for-rollback`

- Get approval for each run. Approval for one script does not cover a changed script, a different scope, or a different instance.

- Use `now-sdk query` when it is enough. Reading records, column metadata, sys_ids or choice values does not need a script. `now-sdk query` is read-only and uses the Table API (see `now-sdk explain query-guide`).

- Pass `--reason` so the run can be traced later on the instance.

- Keep rollback on. Don't pass `--no-record-for-rollback` unless the user asks for it.

## Options

### Script source

- `[script]` — the script as a positional argument

- `--file, -f` — path to a file containing the script

- piped stdin — used when neither of the above is given

The positional argument and `--file` can't be used together.

### Where it runs

- `--scope` — application scope name, application sys_id, or `global`. Defaults to the project's scope (see below)

- `--auth, -a` — credential alias (omit for default)

### Safety and traceability

- `--reason` — why the script is being run. Saved with the script on its Script Execution History record

- `--record-for-rollback` (default `true`) — create a rollback context so the script's record changes can be reverted

### Waiting and output

- `--timeout` (default `300000`) — how long to wait for a response, in ms

- `--output, -o` — `json` for a machine-readable envelope, or `raw` to unquote the `--select` result

- `--select, -s` — dot/bracket path to extract from the output, e.g. `output[0]`

- `--server-logs` — also print the instance's session log, including stack traces

## Choosing the scope

The scope is picked in this order:

- `--scope`, when passed. `global` runs in global. A name or sys_id that doesn't match an application on the instance is an error. The script never quietly falls back to global.

- The project's scope, when `now-sdk exec` is run inside a Fluent project. Exec uses the nearest `now.config.json` in the current directory or any parent directory. The app must already be installed on the instance. If it isn't, exec stops with an error instead of running in global. Install the app first, or pass `--scope`.

- Global, when neither applies.

If the target application is inactive, exec prints a warning and still runs.

In normal output, the CLI logs `Running on <instance> in scope '<scope>'` before the script runs, and `Ran in scope '<scope>'` after. Check it matches what the user approved.

## Output

In normal mode, exec prints a "Use wisely." warning, the script's output line by line, then links to the run's records:

```
Scripts run with your instance permissions and can change or delete data, much like Scripts - Background. Use wisely.
Running on https://dev12345.service-now.com in scope 'x_acme_app'
Ran in scope 'x_acme_app'
<script output lines>
Execution history: https://dev12345.service-now.com/sys_script_execution_history.do?sys_id=...
Rollback context: https://dev12345.service-now.com/sys_rollback_context.do?sys_id=...
```

Script errors are printed as `Script execution error: ...` and the command exits non-zero.

- `gs.addErrorMessage(...)` and `gs.addInfoMessage(...)` aren't part of the output and don't fail the run, including when a platform business rule calls them. They only appear in `--server-logs`. A business rule that refuses a change usually reports it this way, so check `--server-logs` when a change didn't happen.

- The output includes log lines from platform code the script triggers, not just the script's own `gs.info(...)` calls.

- The instance keeps only the last 50,001 lines of a run, counting log lines too. Past that, the earliest lines are lost. Exec warns when a run reaches the cap.

### Machine-readable output (`-o json`)

`--output json` or `--select` silences the status logging and the warning, so stdout carries only the result.

Script ran:

```
{"ok": true, "scope": "x_acme_app", "output": ["..."], "errors": [], "scopeId": "...", "executionHistoryId": "...", "rollbackContextId": "..."}
```

- `ok` — `false` if the script reported errors (it still ran)

- `output` — the script's output lines

- `errors` — error messages the script reported

- `scopeId` — sys_id of the scope the script was sent to run in (`global` for the global scope)

- `executionHistoryId` — sys_id of the Script Execution History record

- `rollbackContextId` — sys_id of the rollback context, when one was created

- `log` — the instance's session log lines, only with `--server-logs`

Request failed (bad scope, app not installed, auth or network error):

```
{"ok": false, "error": {"message": "No application found with scope 'x_bogus' on the instance"}}
```

Check `ok` before using `output`. The command exits non-zero in both failure cases.

### Extracting a value

```
BUILD=$(now-sdk exec "gs.info(gs.getProperty('glide.buildname'))" \
  --select 'output[0]' --output raw)
```

A path that doesn't resolve prints `null` (or an empty string with `--output raw`).

## Traceability and rollback

Every run is recorded on the instance's Script Execution History (`sys_script_execution_history`), under the authenticated user. The record holds the script, including the `--reason` text, which is appended to the script as a comment.

With `--record-for-rollback` on (the default), the instance also creates a rollback context when the script changes records. Scopes listed in the instance property `glide.script_processor.scopes_with_rollback_always_on` always record for rollback, even with `--no-record-for-rollback`. Exec reports the rollback context whenever the instance created one. To undo the script's record changes, open the execution history or rollback context link that exec printed and use the platform's rollback action. Rollback covers record changes only. It can't undo side effects like sent emails, outbound REST calls or scheduled jobs that already ran.

## Timeouts

`--timeout` only controls how long the CLI waits. When it expires, the script keeps running on the instance until it finishes. Running the command again starts a second copy, so don't retry a timed-out script without checking whether the first run finished (look at its Script Execution History record).

For long-running scripts, raise `--timeout`. The instance always cancels scripts still running after four hours.

## Recipes

```
# Run a backfill in the project's scope, with a reason
now-sdk exec --file ./scripts/backfill.js --reason "backfill missing priority values"

# Run in a specific app scope
now-sdk exec --file ./scripts/fix.js --scope x_acme_app

# Run in global from inside a project
now-sdk exec "gs.info(gs.getUserName())" --scope global

# Long-running script: wait up to 30 minutes
now-sdk exec --file ./scripts/long-backfill.js --timeout 1800000

# Against a specific instance
now-sdk exec --auth test-instance --file ./scripts/check.js
```

## Permissions

Running scripts needs the `admin` role on the instance. Without it, exec fails with `403 Forbidden`.

Users with the `snc_read_only` role always run in the platform's restricted sandbox mode, and the instance keeps no execution history for their runs. Exec warns when this happens.

## Tips

- Log results with `gs.info(...)` — that's what becomes the `output` lines

- For metadata changes, change the Fluent source and use `now-sdk install` instead. A script's changes aren't part of the app

- Use `--server-logs` to see the instance's session log and stack traces when a script fails or behaves unexpectedly

## Related

- query-guide.md — read-only instance queries with `now-sdk query`

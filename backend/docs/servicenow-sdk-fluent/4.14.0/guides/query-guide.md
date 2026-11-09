Version: 4.14.0

# Querying the Instance

`now-sdk query` runs a read-only Table REST API query against the authenticated ServiceNow instance. Use it for live, instance-specific data — column metadata, existing sys_ids, choice values, role memberships, scope info, etc.

```
now-sdk query <table> --query '<encoded_query>' [options]
```

## Options

### Required

- `<table>` — table name (e.g., `incident`, `sys_dictionary`)

- `--query, -q` — encoded query string, e.g. `active=true^priority<=2`

### Paging

- `--limit` (default `100`) — page size

- `--offset` (default `0`) — starting offset

### Field shaping

- `--fields, -f` — comma-separated field list (dramatically reduces response size)

- `--display-value` — `true` | `false` | `all` (default `false`)

- `--exclude-reference-link` (default `true`) — omit Table API links for reference fields

- `--no-count` — skip X-Total-Count header (faster on big tables)

- `--view` — UI view for field selection

### Other

- `--output, -o` — `json` for a machine-readable envelope, or `raw` to unquote the `--select` result

- `--select, -s` — dot/bracket path to extract from the output, e.g. `records[0].sys_id`; implies machine-readable output even without `-o`

- `--auth, -a` — credential alias (omit for default)

- `--timeout` (default `30000`) — per-request timeout in ms

- `--query-category` — category for extended queries (advanced)

- `--query-no-domain` — ignore domain separation (advanced)

## Output (`-o json`)

Success:

```
{"ok": true, "hasMore": false, "nextOffset": null, "records": [...]}
```

- `hasMore` — `true` if more records exist

- `nextOffset` — offset for the next page when `hasMore` is true

Error:

```
{"ok": false, "error": {"message": "Table API request failed: 404 Not Found", "status": 404, "table": "bogus_table"}}
```

- `message` — error description

- `status` — HTTP status code (when available)

- `table` — the table that was queried

Check `ok` before consuming `records`.

## Extracting values with `--select` / `--output raw`

`--select` walks the `-o json` envelope with a dot/bracket path and prints just that value — no need to reach for `jq` for a single field. Add `--output raw` to unquote strings so the result drops directly into `$()` for shell scripting:

```
# Pretty JSON of one field
now-sdk query sys_user_role -q 'name=admin' -f sys_id --select 'records[0].sys_id'
# "62826bf03710200044e0bfc8bcbe5df4"

# Same, unquoted for command substitution
roleId=$(now-sdk query sys_user_role -q 'name=admin' -f sys_id \
  --select 'records[0].sys_id' --output raw)
echo "$roleId"
# 62826bf03710200044e0bfc8bcbe5df4
```

`--select` alone (without `-o json`) still silences normal log output and switches to a single machine-readable line — you don't need both flags together. A path that doesn't resolve (e.g. no matching record) prints `null` (or an empty string with `--output raw`) rather than throwing, so check for that before using the value:

```
appId=$(now-sdk query sys_scope -q 'scope=x_acme_app' -f sys_id \
  --select 'records[0].sys_id' --output raw)
if [ -z "$appId" ]; then
  echo "No app found with scope x_acme_app" >&2
  exit 1
fi
```

For anything beyond a single field path (filters, projections across multiple records, wildcards), pipe the full `-o json` output to `jq` instead — `--select` only covers the common "grab one value out of a known shape" case. This is also how you feed a resolved sys_id into other `now-sdk` commands that need one, e.g. a `now-sdk cicd` test suite run (see `now-sdk cicd --help`).

## Pagination

Use `hasMore` and `nextOffset` to page through large result sets:

```
# First page
now-sdk query incident -q 'active=true' -f 'number' --limit 100 -o json
# {"ok":true,"hasMore":true,"nextOffset":100,"records":[...]}

# Next page
now-sdk query incident -q 'active=true' -f 'number' --limit 100 --offset 100 -o json
# {"ok":true,"hasMore":false,"nextOffset":null,"records":[...]}
```

Loop until `hasMore` is `false` or `null`.

## Recipes

```
# Table columns
now-sdk query sys_dictionary \
  -q 'name=incident^elementISNOTEMPTY' \
  -f 'element,column_label,internal_type,reference,mandatory' -o json

# Table inheritance
now-sdk query sys_db_object -q 'name=incident' \
  -f 'name,super_class,label' --display-value all -o json

# Resolve name → sys_id
now-sdk query sys_user_role -q 'name=admin' -f 'sys_id,name' -o json
now-sdk query sys_scope -q 'scope=x_acme_app' -f 'sys_id,scope,name' -o json

# Check for collision
now-sdk query sys_script \
  -q 'name=My Rule^collection=incident' -f 'sys_id,name' -o json
# If records.length > 0, record exists

# ACLs on a table
now-sdk query sys_security_acl \
  -q 'name=incident^ORnameSTARTSWITHincident.' \
  -f 'sys_id,name,operation,active' -o json

# Large result set (paginate using hasMore/nextOffset)
now-sdk query incident -q 'active=true' --limit 500 \
  -f 'number,short_description' -o json

# Resolve name → sys_id and use it immediately in a shell variable
scopeId=$(now-sdk query sys_scope -q 'scope=x_acme_app' -f sys_id \
  --select 'records[0].sys_id' --output raw)
```

## Tips

- Always pass `--fields` — bare queries return every column

- Use `^` for AND, `^OR` for OR, `STARTSWITH`/`CONTAINS`/`IN` for matching

- `--display-value all` gets both raw and display values in one call

- Read-only — for mutations, use `now-sdk install`

## Related

- ci-integration.md — piping a resolved sys_id into `now-sdk cicd` operations (ATF test suites, app repo install/publish) in a pipeline

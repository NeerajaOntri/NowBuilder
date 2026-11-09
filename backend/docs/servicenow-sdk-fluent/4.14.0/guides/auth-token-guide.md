Version: 4.14.0

# Printing an Auth Token for Manual API Calls

`now-sdk auth --print` outputs a live authentication token for a stored credential so you can call any ServiceNow REST API by hand. It resolves the credential the same way the SDK does at request time (refreshing an OAuth access token, or negotiating a fresh UI session for basic auth) and writes the result to stdout so it drops straight into `curl` or a shell variable.

```
now-sdk auth --print [alias] --format headers|bearer|env
```

- `[alias]` — which stored credential to print. Omit it to use your default credential.

- `--format` — what to print (default `headers`). See below.

Only the short-lived, request-time token is ever printed. Your stored password and OAuth refresh token are never emitted.

## Formats

### `headers` (default)

Prints the HTTP header line(s) needed to authenticate a request, one per line. This is the only format that works for every auth mode:

```
# OAuth credential
now-sdk auth --print --format headers
# Authorization: Bearer <access_token>

# Basic-auth credential
now-sdk auth --print --format headers
# X-UserToken: <token>
# Cookie: <session cookie>
```

A basic-auth token is not usable on its own — it needs the matching session cookie — which is why basic auth prints both lines.

### `bearer`

Prints just the raw OAuth bearer token. Valid only for OAuth credentials:

```
TOKEN=$(now-sdk auth --print prod --format bearer)
```

A basic-auth credential errors here (it has no standalone bearer token) and points you at `--format headers`.

### `env`

Prints `export` statements for the pre-authenticated-session environment variables the CLI already understands. `eval` them to load the session into your shell:

```
eval "$(now-sdk auth --print --format env)"
```

For an OAuth credential this exports `SN_SDK_INSTANCE_URL` and `SN_SDK_SESSION_BEARER_TOKEN`; for basic auth it exports `SN_SDK_INSTANCE_URL`, `SN_SDK_SESSION_TOKEN`, and `SN_SDK_SESSION_COOKIE`. Any subsequent `now-sdk` command in that shell then authenticates straight from the environment as a pre-authenticated session — no keychain lookup, no re-login. These are the same variables documented for CI in ci-integration.md.

## Calling the API with curl

Run `--format headers` to print the exact header line(s), then pass each one to `curl` as its own `-H`:

```
now-sdk auth --print --format headers
# X-UserToken: <token>
# Cookie: <session cookie>

curl -H "X-UserToken: <token>" -H "Cookie: <session cookie>" \
  "https://<instance>.service-now.com/api/now/table/incident?sysparm_limit=1"
```

An OAuth credential prints a single `Authorization` header, so the call is just:

```
now-sdk auth --print --format headers
# Authorization: Bearer <token>

curl -H "Authorization: Bearer <token>" \
  "https://<instance>.service-now.com/api/now/table/incident?sysparm_limit=1"
```

### bash/zsh convenience

To avoid copying the lines by hand in a script, read them straight into `-H` arguments. This is bash/zsh only, does not port to PowerShell/cmd:

```
curl_headers=()
while IFS= read -r line; do curl_headers+=(-H "$line"); done \
  < <(now-sdk auth --print --format headers)
curl "${curl_headers[@]}" \
  "https://<instance>.service-now.com/api/now/table/incident?sysparm_limit=1"
```

Because an OAuth credential prints a single header, you can also inline it directly:

```
curl -X POST -H "$(now-sdk auth --print --format headers)" \
  -H 'Content-Type: application/json' \
  -d '{"short_description":"Created via curl"}' \
  "https://<instance>.service-now.com/api/now/table/incident"
```

## Choosing a credential

```
# List credentials — the default is marked with *
now-sdk auth --list

# Print the default credential
now-sdk auth --print

# Print a specific alias
now-sdk auth --print prod --format bearer
```

## Tips

- stdout carries only the token; logs and errors go to stderr, and stdout is empty on failure — so capturing the output is safe in any shell, even with `--debug`.

- The printed token has your full instance permissions and is short-lived — treat it as a secret and don't write it to disk or logs.

## Related

- developing-apps-guide.md — setting up and storing instance credentials with `now-sdk auth --add`

- query-guide.md — the built-in read-only query command, for cases you don't need a manual API call

- ci-integration.md — the `SN_SDK_SESSION_*` / CI credential environment variables

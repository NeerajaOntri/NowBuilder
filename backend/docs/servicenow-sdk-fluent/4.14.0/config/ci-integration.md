Version: 4.14.0

# CI Integration

Guide for running the Now SDK in CI/CD pipelines: non-interactive authentication for `now-sdk install`, validating that `keys.ts` is committed via `now-sdk build --frozenKeys`, and the conventions that keep pipeline runs reproducible.

## When to Use

- CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins, etc.) building or installing a Fluent app.

- Container builds, scheduled jobs, or scripted environments where interactive prompts aren't possible.

- Pre-merge checks that need to fail fast when developers forget to commit generated artifacts.

## Builds: `--frozenKeys`

`now-sdk build` regenerates `src/fluent/generated/keys.ts` (the registry mapping `Now.ID['...']` identifiers to ServiceNow sys_ids) every time it runs. When a developer adds new Fluent records, the build appends a new entry to `src/fluent/generated/keys.ts`. That generated file must be committed to source control along with the Fluent code that introduced the identifier — see the keys.ts guide.

`--frozenKeys` is the CI-side enforcement of that rule.  This will ensure that keys was not modified by the build, and if any change a build error will occur.

### Usage

```
now-sdk build --frozenKeys
```

After building, the CLI compares `keys.ts` content before and after. If anything changed during the build, it fails with:

```
Keys file is out-of-date. To update it, run the build again without frozen keys.
```

This means a developer pushed Fluent code that introduces a new or modified identifier (or modifies a coalesce key) without checking in the updated `keys.ts`.

### Why this matters

`keys.ts` is the source of truth for record identity. If a pipeline builds without it being committed:

- Deploys produce different sys_ids on every machine. The same `Now.ID['my-rule']` resolves to a freshly-generated sys_id on each developer/CI machine, so the same logical record ends up with different IDs across environments.

- Updates become inserts. ServiceNow uses sys_id for record identity. A mismatch means the install creates a duplicate record instead of updating the existing one — corrupting the target instance.

- Subsequent merges hide the problem. Once a stale `keys.ts` lands in `main`, every later branch picks up the wrong IDs.

Running `--frozenKeys` in CI catches this before merge. It's the same build the developer should have run locally, with a guard that errors instead of silently rewriting the file.

### Recommended placement in the pipeline

Run `now-sdk build --frozenKeys` as a pre-merge / pull-request check, before the install step:

```
# GitHub Actions example
- name: Verify keys.ts is up to date
  run: now-sdk build --frozenKeys
```

If the keys check fails, the developer's fix is simple: run `now-sdk build` locally, commit the updated `keys.ts`, and push.

## Authentication for `now-sdk install`

Non-interactive authentication for `now-sdk install`. The CLI reads credentials from environment variables instead of the local keychain, so it works in CI/CD pipelines and other headless environments. Two auth types are supported: oauth (OAuth 2.0 `client_credentials` grant, recommended) and basic (username + password).

### When to Run `now-sdk install` from CI

Use this for a main-branch pipeline that deploys changes to the next-stage instance (typically a shared test / integration / dev instance). The pipeline installs the just-built app to that instance so QA, integration tests, and downstream environments can pick up the latest changes automatically after merge.

Do not use `now-sdk install` from CI to deploy to production instances. Production deploys should go through ServiceNow's standard application promotion mechanisms — the App Repo, or guided application install/upgrade — so that change management, approvals, and rollback work the way the platform expects.

### Enabling CI Mode

CI mode is gated by a single env var:

```
export SN_SDK_NODE_ENV=SN_SDK_CI_INSTALL
```

When set, the CLI reads credentials from env vars instead of the keychain. Choose the auth type with `SN_SDK_AUTH_TYPE`:

| `SN_SDK_AUTH_TYPE` | Behavior |
| `oauth` | Use `SN_SDK_OAUTH_CLIENT_ID` + `SN_SDK_OAUTH_CLIENT_SECRET` (OAuth `client_credentials` ). Recommended. |
| unset or `basic` | Use `SN_SDK_USER` + `SN_SDK_USER_PWD` (basic auth). Default for backward compatibility. |

Any other value is rejected with an error before any network call.

### OAuth Client Credentials

Token-based, no user password ever leaves your secret store. The CLI fetches a fresh access token at the start of each run.

Preferred over Basic Auth because it doesn't expose a real user's credentials to the pipeline: the client secret authenticates the CI system itself rather than impersonating a person's login, so a leaked secret can be rotated without touching anyone's account password, and there's no live password sitting in a CI variable that a compromised job could exfiltrate and reuse elsewhere.

#### Environment Variables

| Variable | Required | Value |
| `SN_SDK_NODE_ENV` | yes | `SN_SDK_CI_INSTALL` |
| `SN_SDK_AUTH_TYPE` | yes | `oauth` |
| `SN_SDK_INSTANCE_URL` | yes | Full instance URL |
| `SN_SDK_OAUTH_CLIENT_ID` | yes | OAuth Application Registry `client_id` |
| `SN_SDK_OAUTH_CLIENT_SECRET` | yes | OAuth Application Registry `client_secret` |

#### Example

```
export SN_SDK_NODE_ENV=SN_SDK_CI_INSTALL
export SN_SDK_AUTH_TYPE=oauth
export SN_SDK_INSTANCE_URL=https://your-instance.service-now.com
export SN_SDK_OAUTH_CLIENT_ID=<CLIENT_ID_HERE>
export SN_SDK_OAUTH_CLIENT_SECRET=<CLIENT_SECRET_HERE>

# run now-sdk build --frozenKeys before install (see Builds: --frozenKeys above)
now-sdk install
```

The CLI calls `${SN_SDK_INSTANCE_URL}/oauth_token.do` once at startup with `grant_type=client_credentials`, then uses the returned access token for all subsequent requests. There is no refresh token in this grant — each invocation fetches a fresh token.

#### ServiceNow Instance Configuration

OAuth requires one-time setup on the instance. Complete all three steps or the token endpoint will reject the request.

##### 1. Configure the Service User

This user will be mapped as the `OAuth application user` in step 3. It must:

- Have `admin` role sufficient to install your app.

- Have `Identity Type = Human` on the `sys_user` record. The SDK's installer processor requires a human type user account.

##### 2. Enable the `client_credentials` grant on instance

System property `glide.oauth.inbound.client.credential.grant_type.enabled` must exist and be set to `true`. If the property does not already exist on the instance, create it in `sys_properties` with:

- Name: `glide.oauth.inbound.client.credential.grant_type.enabled`

- Type: `true | false`

- Value: `true`

See ServiceNow KB1645212 for details: https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB1645212

Without the system property set to `true`, the token endpoint will reject `grant_type=client_credentials` regardless of how the OAuth app is configured.

##### 3. Create or open the OAuth Application Registry

System OAuth → Application Registry → New → New Inbound Integration Experience → New Integration → OAuth Client Credentials Grant

- Set `Name` to desired name for this entry like "SDK CI"

- Set `Provider Name` to `ServiceNow SDK` (value is not important, but must manually type in)

- Set `OAuth application user` to the user from step 1

- Set `Allow access only to APIs in selected scope` to `false` (leave it unchecked)

- Save and skip assigning auth scope warning

- Do not use OIDC providers for this registry — they don't issue tokens for the `client_credentials` grant

Note the Client ID and Client Secret — these become `SN_SDK_OAUTH_CLIENT_ID` and `SN_SDK_OAUTH_CLIENT_SECRET`.

### Basic Auth

Simplest setup — username and password of an instance user. Prefer OAuth Client Credentials above for anything beyond quick iteration.

#### Environment Variables

| Variable | Required | Value |
| `SN_SDK_NODE_ENV` | yes | `SN_SDK_CI_INSTALL` |
| `SN_SDK_AUTH_TYPE` | no | `basic` (or unset) |
| `SN_SDK_INSTANCE_URL` | yes | Full instance URL, e.g. `https://your-instance.service-now.com` |
| `SN_SDK_USER` | yes | Username |
| `SN_SDK_USER_PWD` | yes | Password |

#### Example

```
export SN_SDK_NODE_ENV=SN_SDK_CI_INSTALL
export SN_SDK_AUTH_TYPE=basic
export SN_SDK_INSTANCE_URL=https://your-instance.service-now.com
export SN_SDK_USER=ci-user
export SN_SDK_USER_PWD=...

# run now-sdk build --frozenKeys before install (see Builds: --frozenKeys above)
now-sdk install
```

Avoid for production CI: every run sends the password to the instance, and rotating it means rotating in every pipeline secret store.

### Choosing an Auth Type

|  | OAuth Client Credentials | Basic |
| Setup effort | One-time OAuth app + entity profile + service user setup | None — uses existing user |
| Credential rotation | Rotate client secret (no password change) | Rotate user password |
| Network surface | Password never sent; token fetched once per run | Password sent on every request |
| Best for | Production CI, regulated environments | PDIs, sandbox, fast iteration |

## Promotion and Testing with `now-sdk cicd`

`now-sdk install` deploys your local build straight to an instance — the post-merge deploy to a test instance described above. To run ATF tests as a gate, and to promote an already-built version across instances the way the platform expects (rather than `now-sdk install` to production), use `now-sdk cicd`, which drives the sn_cicd REST API. These are the App Repo mechanisms the install section points to for production.

CI/CD pipeline using now-sdk
Developers iterate locally against a dev instance (the develop cycle), then push a PR, which triggers the pipeline. The pipeline builds and installs to the test instance, runs ATF tests there, and publishes to the Application Repository from the test instance, then installs the published version to staging or production instances. The install step can be reverted with cicd rollback.

dev instance (local)

test instance

staging / prod

Develop
code · test

iterate

Push PR
opens PR

triggers

Build + Install
build · install

Test
cicd testsuite run

Publish
cicd publish

Install
cicd install

failure stops the pipeline

cicd rollback

A typical post-validation promotion flow, run from inside the Fluent project directory:

```
# 1. Run an ATF test suite on the test instance; a failure exits non-zero and gates the pipeline
now-sdk cicd testsuite run --test-suite-name "Regression Suite" -o json

# 2. Publish the validated version to the Application Repository, from the test instance
now-sdk cicd publish -o json

# 3. Install that published version onto a downstream instance (staging, prod, ...)
now-sdk cicd install -o json
```

- `--app-sys-id` and `--app-version` default automatically from the project's `now.config.json` (`scopeId`) and `package.json` (`version`) when omitted and run from inside the Fluent project — so `publish`/`install` work unchanged across stages. Pass them explicitly to pin one version across stages that run from a different directory or machine.

- Every command exits non-zero on failure (a failed test, a failed install), so `set -e` or the step's exit code gates the pipeline — no parsing status fields by hand.

- Each `now-sdk cicd` command authenticates using the CI env vars from the Authentication section above — before each step, ensure `SN_SDK_INSTANCE_URL` and the rest of the auth vars are set correctly for that step's target instance (e.g. the test instance for `testsuite run`/`publish`, the downstream instance for `install`).

Run `now-sdk cicd --help`, and `now-sdk cicd <command> --help` (e.g. `now-sdk cicd install --help`), for every command and its full option set — including `--wait`/polling behavior, extracting values with `--select`, running a single ATF test (`cicd test run`), and rollback (`cicd rollback`).

## Troubleshooting

| Symptom | Likely Cause |
| `Keys file is out-of-date. To update it, run the build again without frozen keys.` | Developer added or changed an identifier without committing the regenerated `keys.ts` . Run `now-sdk build` locally, commit the file, push. |
| `Unsupported value for SN_SDK_AUTH_TYPE` | Typo. Must be exactly `basic` or `oauth` . |
| `CI basic auth is missing required environment variables: ...` | One of `SN_SDK_INSTANCE_URL` / `SN_SDK_USER` / `SN_SDK_USER_PWD` is unset. |
| `CI OAuth client_credentials is missing required environment variables: ...` | One of `SN_SDK_INSTANCE_URL` / `SN_SDK_OAUTH_CLIENT_ID` / `SN_SDK_OAUTH_CLIENT_SECRET` is unset. |
| `401 {"error":"server_error","error_description":"access_denied"}` from `/oauth_token.do` | Missing `OAuth application user` mapping on the OAuth app (step 3), `client_credentials` grant not enabled, or `glide.oauth.inbound.client.credential.grant_type.enabled` not set to `true` . |
| `User <name> is not allowed to access com.glide.ui.ng.AngularProcessor` after token is issued | Mapped service user has `Identity Type = Machine` . Change to `Human` on the `sys_user` record. |
| `401 invalid_client` | Client ID or secret typo. Re-copy from the Application Registry record. |
| `401 Unauthorized` on basic auth | Username/password incorrect, or the user lacks roles for the operation. |

Check System Logs → All filtered to `Source = OAuth` (for OAuth) or `Source = Transaction` (for basic) for the precise platform-side error — response bodies are deliberately vague but the logs name the actual cause.

## Security Notes

- Never commit credentials to source control. Use your CI provider's secret store (GitHub Actions secrets, GitLab CI variables, Jenkins Credentials, etc.).

- Use a dedicated service user rather than reusing a person's account — auditing, rotation, and role narrowing are all easier.

- For OAuth, rotate the client secret regularly. The `client_credentials` grant has no refresh token, so each CLI run fetches a fresh access token from the secret.

- For basic, rotate the password regularly and prefer a service account with the minimum roles required for the operations performed.

Version: 4.14.0

# Connection & Credential Alias Templates

Guide for creating Connection & Credential Alias Templates (`sys_alias_templates`) using the
Fluent API. Alias templates define the wizard form fields and default values shown when a user
sets up a connection alias in ServiceNow, driving integrations built on Integration Hub Spokes.

## When to Use

- Building an Integration Hub Spoke that needs a connection alias

- Defining the setup wizard for an outbound HTTP integration

- Providing default connection URLs and credential defaults for users of your spoke

- Collecting custom configuration alongside connection/credential fields via `additionalFields`

- Automating post-connection setup steps (e.g., creating related records) via `postProcessScript`

## Auth Types

The platform wizard offers 8 configuration templates. Pick the one that matches your
integration's auth flow:

| Wizard option | When to use |
| Basic Auth | Username + password |
| API Key | Single API key / token |
| OAuth Authorization Code | Auth code flow, user-named OAuth entity |
| OAuth Authorization Code (Auto Naming) | Auth code flow, OAuth entity name auto-derived |
| OAuth Client Credentials | Server-to-server, no user redirect |
| OAuth JWT Bearer | JWT-signed assertion, user-named entities |
| OAuth JWT Bearer (Auto Naming) | JWT-signed assertion, names auto-derived |
| Other Configuration | Blank template — custom schema from scratch |

## Key Concepts

### Field naming convention

Fields in `dynamicDataSchema` use dot-notation to map to backing record fields:

- `connection.<field>` → the field on the connection record (e.g. `connection.connection_url`)

- `credential.<field>` → the field on the credential record (e.g. `credential.user_name`)

- `credential.oauth_entity.<field>` → a field on the nested OAuth entity record

- `credential.jwt_provider.<field>` → a field on the nested JWT provider record

- `additional.<field>` → arbitrary extra data passed to the post-process script

### Credential tables

All OAuth-based templates use `oauth_2_0_credentials` (not `oauth_entity`). The
`oauth_entity` key inside `defaultDataTemplate` is the nested OAuth provider configuration,
not the credential table name.

| Auth type | `credential.table` |
| Basic Auth | `basic_auth_credentials` |
| API Key | `api_key_credentials` |
| OAuth Authorization Code | `oauth_2_0_credentials` |
| OAuth Client Credentials | `oauth_2_0_credentials` |
| OAuth JWT Bearer | `oauth_2_0_credentials` |

### Script lifecycle

| Script | When it fires | Typical use |
| `preEditScript` | Before the wizard form renders | Pre-populate or override field defaults |
| `onEditScript` | Each time the user edits a field | Keep dependent fields in sync |
| `postProcessScript` | After connection & credential are saved | Create related records, call external APIs |

All scripts receive: `aliasId`, `connectionSysId`, `jsonDefaultData`, `jsonDynamicData`.

## Instructions

- Pick the auth type that matches your integration. See the table above — the type
determines the `credential.table` and the nested `oauth_entity` / `jwt_provider` structure
in `defaultDataTemplate`.

- Copy the matching example below and replace placeholders if needed. Every `<...>` token is a
placeholder. Replace `<provider-name>`, `<provider-domain-name>`, and `<instance-name>` if the value applies to every integration
with real values. Leave password/secret/key fields empty — these are filled in at setup time.

- Use `Now.include()` for scripts. Keep `preEditScript`, `onEditScript`, and
`postProcessScript` in separate `.js` files.

- In scripts, access fields using bracket notation. Use `dynamicData['additional.environment']`,
not `dynamicData.additional.environment` — field names contain dots.

- Do not put real secrets in `defaultDataTemplate`. Use empty strings `""` for
passwords, client secrets, and API keys.

- Optionally wire up a test action. Set `testAction` to a Flow Designer action
that validates the connection created from this template. Three ways to provide it:

- Custom Action — define a new action using `Action()` (see `wfa-custom-action-guide`).

- `Record<'sys_hub_action_type_definition'>` — define a new action using the Record API.

- sys_id string — reference an existing action by querying the instance.

## Avoidance

- Do not use `oauth_entity` as `credential.table` — the correct table for all OAuth
types is `oauth_2_0_credentials`. `oauth_entity` is only a key inside `defaultDataTemplate`.

- Do not skip the `connection.` / `credential.` prefix on `dynamicDataSchema` field names.
Without it the platform cannot map user input to the created records.

- Do not use `type: 'text'` for passwords. Always use `type: 'password'`.

- Do not write long scripts inline. Use `Now.include('./script.js')` instead.

- Do not use dot notation in scripts. Field names like `'additional.environment'` contain dots,
so use `dynamicData['additional.environment']`, not `dynamicData.additional.environment`.

- Do not omit fields from `defaultDataTemplate` that are defined in `dynamicDataSchema`.
Every field in `dynamicDataSchema` (connection, credential, or additional fields) must have
a corresponding entry in `defaultDataTemplate` — even if the default value is an empty string.
This ensures the platform has default values for all wizard fields.

## API Reference

For the full property reference, see the `aliastemplate-api` topic.

## Examples

### Basic Auth

Username and password backed by `basic_auth_credentials`. The platform wizard option is
"HTTP Connection with Basic Auth Credential".

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const BasicAuthTemplate = AliasTemplate({
    $id: Now.ID['<provider-name>-basic-auth'],
    name: '<provider-name> Spoke — Basic Auth',
    dynamicDataSchema: {
        connectionFields: [
            {
                name: 'connection.name',
                label: 'Connection Name',
                type: 'text',
                defaultValue: '<provider-name> Spoke Connection',
                mandatory: true,
            },
            {
                name: 'connection.connection_url',
                label: 'Connection URL',
                type: 'text',
                defaultValue: 'https://<provider-domain-name>.com',
                mandatory: true,
            },
        ],
        credentialFields: [
            {
                name: 'credential.user_name',
                label: 'User Name',
                type: 'text',
                defaultValue: '',
                mandatory: true,
            },
            {
                name: 'credential.password',
                label: 'Password',
                type: 'password',
                defaultValue: '',
                mandatory: true,
            },
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: '',
            connectionUrl: '',
        },
        credential: {
            table: 'basic_auth_credentials',
            name: '<provider-name> Spoke Credential',
            user_name: '<user-name>',
            password: '',
        },
    },
})
```

### API Key

Single API key backed by `api_key_credentials`. The platform wizard option is
"HTTP Connection with API Key Credential".

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const ApiKeyTemplate = AliasTemplate({
    $id: Now.ID['<provider-name>-api-key'],
    name: '<provider-name> Spoke — API Key',
    dynamicDataSchema: {
        connectionFields: [
            {
                name: 'connection.name',
                label: 'Connection Name',
                type: 'text',
                defaultValue: '<provider-name> Spoke Connection',
                mandatory: true,
            },
            {
                name: 'connection.connection_url',
                label: 'Connection URL',
                type: 'text',
                defaultValue: 'https://<provider-domain-name>.com',
                mandatory: true,
            },
        ],
        credentialFields: [
            {
                name: 'credential.api_key',
                label: 'API Key',
                type: 'password',
                defaultValue: '',
                mandatory: true,
            },
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: '',
            connectionUrl: '',
            useMid: false,
        },
        credential: {
            table: 'api_key_credentials',
            name: '<provider-name> Spoke Credential',
            api_key: '', // LEAVE EMPTY — This is set while creating the credential
        },
    },
})
```

### OAuth Authorization Code

OAuth 2.0 authorization code flow backed by `oauth_2_0_credentials`. The OAuth entity is
named manually. The platform wizard option is
"HTTP Connection with OAuth Authorization Code grant type".

The `oauth_entity` key inside `defaultDataTemplate.credential` is the nested OAuth
provider configuration — it is not the credential table name.

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const OAuthAuthCodeTemplate = AliasTemplate({
    $id: Now.ID['<provider-name>-oauth-auth-code'],
    name: '<provider-name> Spoke — OAuth Authorization Code',
    dynamicDataSchema: {
        connectionFields: [
            {
                name: 'connection.name',
                label: 'Connection Name',
                type: 'text',
                defaultValue: '<provider-name> Spoke Connection',
                mandatory: true,
            },
            {
                name: 'connection.connection_url',
                label: 'Connection URL',
                type: 'text',
                defaultValue: 'https://<provider-domain-name>.com',
                mandatory: true,
            },
        ],
        credentialFields: [
            {
                name: 'credential.oauth_entity.name',
                label: 'OAuth Entity Name',
                type: 'text',
                mandatory: true,
            },
            {
                name: 'credential.oauth_entity.client_id',
                label: 'OAuth Client ID',
                type: 'text',
                mandatory: true,
            },
            {
                name: 'credential.oauth_entity.client_secret',
                label: 'OAuth Client Secret',
                type: 'password',
                mandatory: true,
            },
            {
                name: 'credential.oauth_entity.redirect_url',
                label: 'OAuth Redirect URL',
                type: 'text',
                defaultValue: 'https://<instance-name>.service-now.com/oauth_redirect.do',
                mandatory: true,
            },
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: '',
            connectionUrl: '',
            useMid: false,
        },
        credential: {
            table: 'oauth_2_0_credentials',
            name: '<provider-name> Spoke Credential',
            oauth_entity: {
                name: '<provider-name> Spoke OAuth',
                type: 'consumer',
                default_grant_type: 'authorization_code',
                client_id: '',              // LEAVE EMPTY
                client_secret: '',          // LEAVE EMPTY
                auth_url: 'https://<provider-domain-name>.com/oauth2/auth',
                token_url: 'https://<provider-domain-name>.com/oauth2/token',
                revoke_token_url: 'https://<provider-domain-name>.com/oauth2/revoke',
                redirect_url: '',
                code_challenge_method: 'S256',
                public_client: false,
                use_mutual_auth: false,
                oauth_api_script: '3e3a3a11c333210016194ffe5bba8f70',
                oauth_entity_scope: [
                    { name: 'email', oauth_entity_scope: 'users:read.email' },
                ],
                oauth_entity_profile: [
                    {
                        name: '<provider-name> Profile',
                        grant_type: 'authorization_code',
                        default: true,
                        oauth_entity_profile_scope: ['users:read.email'],
                    },
                ],
            },
        },
    },
})
```

### OAuth Authorization Code (Auto Naming)

Auto-naming variants differ from standard Auth Code template above:

- `credential.oauth_entity.name` field removed from `dynamicDataSchema`

- `credential.name` and `oauth_entity.name` in `defaultDataTemplate` set to `""`

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const OAuthAuthCodeAutoNamingTemplate = AliasTemplate({
    $id: Now.ID['<provider-name>-oauth-auth-code-auto'],
    name: '<provider-name> Spoke — OAuth Authorization Code (Auto Naming)',
    dynamicDataSchema: {
        connectionFields: [
            {
                name: 'connection.name',
                label: 'Connection Name',
                type: 'text',
                defaultValue: '<provider-name> Spoke Connection',
                mandatory: true,
            },
            {
                name: 'connection.connection_url',
                label: 'Connection URL',
                type: 'text',
                defaultValue: 'https://<provider-domain-name>.com',
                mandatory: true,
            },
        ],
        credentialFields: [
            // No oauth_entity.name — name is auto-derived from connection alias name
            {
                name: 'credential.oauth_entity.client_id',
                label: 'OAuth Client ID',
                type: 'text',
                mandatory: true,
            },
            {
                name: 'credential.oauth_entity.client_secret',
                label: 'OAuth Client Secret',
                type: 'password',
                mandatory: true,
            },
            {
                name: 'credential.oauth_entity.redirect_url',
                label: 'OAuth Redirect URL',
                type: 'text',
                defaultValue: 'https://<instance-name>.service-now.com/oauth_redirect.do',
                mandatory: true,
            },
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: '',
            connectionUrl: '',
            useMid: false,
        },
        credential: {
            table: 'oauth_2_0_credentials',
            name: '',   // Auto-derived from connection alias name
            oauth_entity: {
                name: '<provider-name> Spoke OAuth',
                type: 'consumer',
                default_grant_type: 'authorization_code',
                client_id: '',
                client_secret: '',
                auth_url: 'https://<provider-domain-name>.com/oauth2/auth',
                token_url: 'https://<provider-domain-name>.com/oauth2/token',
                revoke_token_url: 'https://<provider-domain-name>.com/oauth2/revoke',
                redirect_url: '',
                code_challenge_method: 'S256',
                public_client: false,
                use_mutual_auth: false,
                oauth_api_script: '3e3a3a11c333210016194ffe5bba8f70',
                oauth_entity_scope: [
                    { name: 'email', oauth_entity_scope: 'users:read.email' },
                ],
                oauth_entity_profile: [
                    {
                        name: '',   // Auto-derived
                        grant_type: 'authorization_code',
                        default: true,
                        oauth_entity_profile_scope: ['users:read.email'],
                    },
                ],
            },
        },
    },
})
```

### OAuth Client Credentials

Server-to-server OAuth 2.0 — no user redirect, no `auth_url`. The platform wizard
option is "HTTP Connection with OAuth Client Credentials grant type".

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const OAuthClientCredsTemplate = AliasTemplate({
    $id: Now.ID['<provider-name>-oauth-client-creds'],
    name: '<provider-name> Spoke — OAuth Client Credentials',
    dynamicDataSchema: {
        connectionFields: [
            {
                name: 'connection.name',
                label: 'Connection Name',
                type: 'text',
                defaultValue: '<provider-name> Spoke Connection',
                hint: 'Display name for the Connection',
                mandatory: true,
            },
            {
                name: 'connection.connection_url',
                label: 'Connection URL',
                type: 'text',
                defaultValue: 'https://<provider-domain-name>.com',
                hint: 'Connection URL for provider',
                mandatory: true,
            },
        ],
        credentialFields: [
            {
                name: 'credential.oauth_entity.client_id',
                label: 'OAuth Client ID',
                type: 'text',
                hint: 'Client ID for provider',
                mandatory: true,
            },
            {
                name: 'credential.oauth_entity.client_secret',
                label: 'OAuth Client Secret',
                type: 'password',
                hint: 'Client Secret for provider',
                mandatory: true,
            },
            {
                name: 'credential.oauth_entity.token_url',
                label: 'OAuth Token URL',
                type: 'text',
                defaultValue: 'https://<provider-domain-name>.com/oauth2/token',
                hint: 'Token URL for provider',
                mandatory: true,
            },
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: '',
            connectionUrl: '',
        },
        credential: {
            table: 'oauth_2_0_credentials',
            name: '<provider-name> Spoke Credential',
            oauth_entity: {
                name: '<provider-name> Spoke OAuth',
                type: 'consumer',
                default_grant_type: 'client_credentials',
                client_id: '',
                client_secret: '',
                token_url: 'https://<provider-domain-name>.com/oauth2/token',
                code_challenge_method: 'S256',
                public_client: false,
                use_mutual_auth: false,
                oauth_api_script: '3e3a3a11c333210016194ffe5bba8f70',
                oauth_entity_scope: [
                    { name: 'email', oauth_entity_scope: 'users:read.email' },
                ],
                oauth_entity_profile: [
                    {
                        name: '<provider-name> Profile',
                        grant_type: 'client_credentials',
                        default: true,
                        oauth_entity_profile_scope: ['users:read.email'],
                    },
                ],
            },
        },
    },
})
```

### OAuth JWT Bearer

OAuth 2.0 with JWT-signed assertions. Requires a keystore for signing. Includes both
an OAuth entity and a JWT provider. The platform wizard option is
"HTTP Connection with OAuth JWT Bearer grant type".

The `dynamicDataSchema` includes a `radio` field for the keystore group (upload vs use
existing). The `defaultDataTemplate` has a nested `jwt_provider` alongside `oauth_entity`.

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const OAuthJwtBearerTemplate = AliasTemplate({
    $id: Now.ID['<provider-name>-oauth-jwt-bearer'],
    name: '<provider-name> Spoke — OAuth JWT Bearer',
    dynamicDataSchema: {
        connectionFields: [
            {
                name: 'connection.name',
                label: 'Connection Name',
                type: 'text',
                defaultValue: '<provider-name> Spoke Connection',
                hint: 'Display name for the Connection',
                mandatory: true,
            },
            {
                name: 'connection.connection_url',
                label: 'Connection URL',
                type: 'text',
                defaultValue: 'https://<provider-domain-name>.com',
                hint: 'Connection URL for provider',
                mandatory: true,
            },
        ],
        credentialFields: [
            {
                name: 'credential.oauth_entity.name',
                label: 'OAuth Entity Name',
                type: 'text',
                mandatory: true,
            },
            {
                name: 'credential.oauth_entity.client_id',
                label: 'OAuth Client ID',
                type: 'text',
                hint: 'Client ID for provider',
                mandatory: true,
            },
            {
                name: 'credential.oauth_entity.client_secret',
                label: 'OAuth Client Secret',
                type: 'password',
                hint: 'Client Secret for provider',
                mandatory: true,
            },
            {
                name: 'credential.oauth_entity.redirect_url',
                label: 'OAuth Redirect URL',
                type: 'text',
                defaultValue: 'https://<instance-name>.service-now.com/oauth_redirect.do',
                hint: 'Callback URL for provider',
                mandatory: true,
            },
            {
                name: 'credential.jwt_provider.name',
                label: 'JWT Provider Name',
                type: 'text',
                mandatory: true,
            },
            {
                name: 'credential.jwt_provider.jwt_claim_validation[0].value',
                label: 'Not Before (nbf) Claim value',
                type: 'text',
                defaultValue: '',
                hint: 'Time before which JWT is deemed invalid',
                mandatory: true,
            },
            {
                name: 'credential.jwt_provider.jwt_keystore_aliases.name',
                label: 'JWT Keystore Alias Name',
                type: 'text',
                mandatory: true,
            },
            {
                name: 'credential.jwt_provider.jwt_keystore_aliases.kid',
                label: 'Key ID (kid)',
                type: 'text',
                defaultValue: '',
                hint: 'Indicates which key was used to secure the JWS',
                mandatory: true,
            },
            {
                name: 'credential.jwt_provider.jwt_keystore_aliases.signing_keystore-group',
                label: 'Keystore Group',
                type: 'radio',
                groups: [
                    {
                        name: 'credential.jwt_provider.jwt_keystore_aliases.signing_keystore-upload',
                        label: 'Upload Keystore',
                        defaultGroup: true,
                        fields: [
                            {
                                name: 'credential.jwt_provider.jwt_keystore_aliases.signing_keystore_name',
                                label: 'Keystore Name',
                                type: 'text',
                                mandatory: true,
                            },
                            {
                                name: 'credential.jwt_provider.jwt_keystore_aliases.signing_key_password',
                                label: 'Keystore Password',
                                type: 'password',
                                mandatory: true,
                            },
                            {
                                name: 'credential.jwt_provider.jwt_keystore_aliases.signing_keystore_file',
                                label: 'Keystore',
                                type: 'file',
                                mandatory: true,
                            },
                        ],
                    },
                    {
                        name: 'credential.jwt_provider.jwt_keystore_aliases.signing_keystore-existing',
                        label: 'Use Existing Keystore',
                        fields: [
                            {
                                name: 'credential.jwt_provider.jwt_keystore_aliases.signing_key_password',
                                label: 'Keystore Password',
                                type: 'password',
                                mandatory: true,
                            },
                            {
                                name: 'credential.jwt_provider.jwt_keystore_aliases.signing_keystore',
                                label: 'Keystore',
                                type: 'reference',
                                table: 'sys_certificate',
                                query: 'active=true^type=key_store',
                                mandatory: true,
                            },
                        ],
                    },
                ],
            },
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: '<provider-name> Spoke Connection',
            connectionUrl: 'https://<provider-domain-name>.com',
            useMid: false,
        },
        credential: {
            table: 'oauth_2_0_credentials',
            name: '<provider-name> Spoke Credential',
            oauth_entity: {
                name: '<provider-name> Spoke OAuth',
                type: 'consumer',
                default_grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                client_id: '<provider-client-id>',
                client_secret: '',          // LEAVE EMPTY
                auth_url: 'https://<provider-domain-name>.com/oauth2/auth',
                token_url: 'https://<provider-domain-name>.com/oauth2/token',
                revoke_token_url: 'https://<provider-domain-name>.com/oauth2/revoke',
                redirect_url: 'https://<instance-name>.service-now.com/oauth_redirect.do',
                code_challenge_method: 'S256',
                public_client: false,
                use_mutual_auth: false,
                oauth_api_script: '3e3a3a11c333210016194ffe5bba8f70',
                oauth_entity_scope: [
                    { name: 'email', oauth_entity_scope: 'users:read.email' },
                ],
                oauth_entity_profile: [
                    {
                        name: '<provider-name> Profile',
                        grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                        default: true,
                        oauth_entity_profile_scope: ['users:read.email'],
                    },
                ],
            },
            jwt_provider: {
                name: '<provider-name> Spoke JWT Provider',
                jwt_api_script: '9ef6af86ff10330001d3cd6bd53bf144',
                jwt_claim_validation: [
                    { name: 'nbf', is_standard: true, data_type: 'string', value: 'nbf-claim-value' },
                ],
                jwt_keystore_aliases: {
                    name: '<provider-name> Spoke JWT Key',
                    kid: '<provider-key-id>',
                    signing_algorithm: 'rsa_256',
                    signing_keystore: '',
                    signing_keystore_name: '',
                    signing_keystore_file: '',
                    signing_key_password: '', // LEAVE EMPTY
                },
            },
        },
    },
})
```

### OAuth JWT Bearer (Auto Naming)

Auto-derived naming for credential, OAuth entity, and JWT provider. Platform wizard: "HTTP Connection with OAuth JWT Bearer grant type (Auto Naming Enabled)".

Differences from standard JWT Bearer:

- `credential.oauth_entity.name` and `credential.jwt_provider.name` removed

- `jwt_claim_validation[0].value` and `jwt_keystore_aliases.kid` not mandatory

- `signing_keystore_name` removed from Upload Keystore group

- `credential.name` and `oauth_entity.name` in `defaultDataTemplate` are `""`

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const OAuthJwtBearerAutoNamingTemplate = AliasTemplate({
    $id: Now.ID['<provider-name>-oauth-jwt-bearer-auto'],
    name: '<provider-name> Spoke — OAuth JWT Bearer (Auto Naming)',
    dynamicDataSchema: {
        connectionFields: [
            {
                name: 'connection.name',
                label: 'Connection Name',
                type: 'text',
                defaultValue: '<provider-name> Spoke Connection',
                hint: 'Display name for the Connection',
                mandatory: true,
            },
            {
                name: 'connection.connection_url',
                label: 'Connection URL',
                type: 'text',
                defaultValue: 'https://<provider-domain-name>.com',
                hint: 'Connection URL for provider',
                mandatory: true,
            },
        ],
        credentialFields: [
            // No oauth_entity.name or jwt_provider.name — auto-derived
            {
                name: 'credential.oauth_entity.client_id',
                label: 'OAuth Client ID',
                type: 'text',
                hint: 'Client ID for provider',
                mandatory: true,
            },
            {
                name: 'credential.oauth_entity.client_secret',
                label: 'OAuth Client Secret',
                type: 'password',
                hint: 'Client Secret for provider',
                mandatory: true,
            },
            {
                name: 'credential.oauth_entity.redirect_url',
                label: 'OAuth Redirect URL',
                type: 'text',
                defaultValue: 'https://<instance-name>.service-now.com/oauth_redirect.do',
                hint: 'Callback URL for provider',
                mandatory: true,
            },
            {
                name: 'credential.jwt_provider.jwt_claim_validation[0].value',
                label: 'Not Before (nbf) Claim value',
                type: 'text',
                defaultValue: '',
                hint: 'Time before which JWT is deemed invalid',
                mandatory: false,
            },
            {
                name: 'credential.jwt_provider.jwt_keystore_aliases.kid',
                label: 'Key ID (kid)',
                type: 'text',
                defaultValue: '',
                hint: 'Indicates which key was used to secure the JWS',
                mandatory: false,
            },
            {
                name: 'credential.jwt_provider.jwt_keystore_aliases.signing_keystore-group',
                label: 'Keystore Group',
                type: 'radio',
                groups: [
                    {
                        name: 'credential.jwt_provider.jwt_keystore_aliases.signing_keystore-upload',
                        label: 'Upload Keystore',
                        defaultGroup: true,
                        fields: [
                            // No signing_keystore_name in auto-naming variant
                            {
                                name: 'credential.jwt_provider.jwt_keystore_aliases.signing_key_password',
                                label: 'Keystore Password',
                                type: 'password',
                                mandatory: true,
                            },
                            {
                                name: 'credential.jwt_provider.jwt_keystore_aliases.signing_keystore_file',
                                label: 'Keystore',
                                type: 'file',
                                mandatory: true,
                            },
                        ],
                    },
                    {
                        name: 'credential.jwt_provider.jwt_keystore_aliases.signing_keystore-existing',
                        label: 'Use Existing Keystore',
                        fields: [
                            {
                                name: 'credential.jwt_provider.jwt_keystore_aliases.signing_key_password',
                                label: 'Keystore Password',
                                type: 'password',
                                mandatory: true,
                            },
                            {
                                name: 'credential.jwt_provider.jwt_keystore_aliases.signing_keystore',
                                label: 'Keystore',
                                type: 'reference',
                                table: 'sys_certificate',
                                query: 'active=true^type=key_store',
                                mandatory: true,
                            },
                        ],
                    },
                ],
            },
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: '',
            connectionUrl: 'https://<provider-domain-name>.com',
            useMid: false,
        },
        credential: {
            table: 'oauth_2_0_credentials',
            name: '',   // Auto-derived from connection alias name
            oauth_entity: {
                name: '<provider-name> Spoke OAuth',
                type: 'consumer',
                default_grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                client_id: '<provider-client-id>',
                client_secret: '',
                auth_url: 'https://<provider-domain-name>.com/oauth2/auth',
                token_url: 'https://<provider-domain-name>.com/oauth2/token',
                revoke_token_url: 'https://<provider-domain-name>.com/oauth2/revoke',
                redirect_url: 'https://<instance-name>.service-now.com/oauth_redirect.do',
                code_challenge_method: 'S256',
                public_client: false,
                use_mutual_auth: false,
                oauth_api_script: '3e3a3a11c333210016194ffe5bba8f70',
                oauth_entity_scope: [
                    { name: 'email', oauth_entity_scope: 'users:read.email' },
                ],
                oauth_entity_profile: [
                    {
                        name: '',   // Auto-derived
                        grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                        default: true,
                        oauth_entity_profile_scope: ['users:read.email'],
                    },
                ],
            },
            jwt_provider: {
                name: '<provider-name> Spoke JWT Provider',
                jwt_api_script: '9ef6af86ff10330001d3cd6bd53bf144',
                jwt_claim_validation: [
                    { name: 'nbf', is_standard: true, data_type: 'string', value: 'nbf-claim-value' },
                ],
                jwt_keystore_aliases: {
                    name: '<provider-name> Spoke JWT Key',
                    kid: '<provider-key-id>',
                    signing_algorithm: 'rsa_256',
                    signing_keystore: '',
                    signing_keystore_name: '<provider-name> Spoke JWT KeyStore',
                    signing_keystore_file: '',
                    signing_key_password: '',
                },
            },
        },
    },
})
```

### Other Configuration

Blank template — `dynamicDataSchema` and `defaultDataTemplate` start empty. Use this when
none of the above auth types fit your integration. The platform wizard option is
"Other Configuration".

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const CustomTemplate = AliasTemplate({
    $id: Now.ID['<provider-name>-custom'],
    name: '<provider-name> Spoke — Custom',
    dynamicDataSchema: {
        connectionFields: [
            // Add your connection fields here
        ],
        credentialFields: [
            // Add your credential fields here
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: '',
            connectionUrl: '',
        },
        credential: {
            table: 'basic_auth_credentials', // Change to match your auth type
            name: '',
        },
    },
})
```

## Additional Fields Examples

Use `additionalFields` to collect custom configuration data beyond standard connection and credential fields. Additional fields are passed to `postProcessScript` for custom processing.

### Example 1: API Configuration with Environment Selection

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const ApiWithEnvironmentTemplate = AliasTemplate({
    $id: Now.ID['api-with-environment'],
    name: 'API Connection with Environment',
    dynamicDataSchema: {
        connectionFields: [
            {
                name: 'connection.name',
                label: 'Connection Name',
                type: 'text',
                defaultValue: 'API Connection',
                mandatory: true,
            },
            {
                name: 'connection.connection_url',
                label: 'Base URL',
                type: 'text',
                defaultValue: 'https://api.example.com',
                mandatory: true,
            },
        ],
        credentialFields: [
            {
                name: 'credential.api_key',
                label: 'API Key',
                type: 'password',
                mandatory: true,
            },
        ],
        additionalFields: [
            {
                name: 'additional.environment',
                label: 'Environment',
                type: 'choice',
                mandatory: true,
                choices: ['dev', 'staging', 'production'],
            },
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: '',
            connectionUrl: '',
        },
        credential: {
            table: 'api_key_credentials',
            name: 'API Credential',
            api_key: '',
        },
        additional: {
            environment: 'dev',
            api_version: 'v1',
            timeout: '30',
        },
    },
    postProcessScript: Now.include('./process-environment-config.js'),
})
```

### Script Examples

All script types receive the same four parameters: `aliasId`, `connectionSysId`, `jsonDefaultData`, `jsonDynamicData`. Always use bracket notation to access fields: `dynamicData['connection.name']` not `dynamicData.connection.name`.

preEditScript - Runs before form render, returns `Array<{ name, value }>`:

```
(function execute(aliasId, connectionSysId, jsonDefaultData, jsonDynamicData) {
    var prePopulatedFields = [];
    var instanceName = gs.getProperty('instance_name');

    prePopulatedFields.push({
        name: 'credential.oauth_entity.redirect_url',
        value: 'https://' + instanceName + '.service-now.com/oauth_redirect.do'
    });
    return prePopulatedFields;
})(aliasId, connectionSysId, jsonDefaultData, jsonDynamicData);
```

onEditScript - Runs on field change, returns void (modifies `dynamicData` in place):

```
(function execute(aliasId, connectionSysId, jsonDefaultData, jsonDynamicData) {
    var dynamicData = JSON.parse(jsonDynamicData);
    var environment = dynamicData['additional.environment'];

    if (environment === 'dev') {
        dynamicData['connection.connection_url'] = 'https://dev-api.example.com';
    } else if (environment === 'production') {
        dynamicData['connection.connection_url'] = 'https://api.example.com';
    }
    // No return - dynamicData modified in place
})(aliasId, connectionSysId, jsonDefaultData, jsonDynamicData);
```

postProcessScript - Runs after save, returns void:

```
(function execute(aliasId, connectionSysId, jsonDefaultData, jsonDynamicData) {
    var dynamicData = JSON.parse(jsonDynamicData);
    var environment = dynamicData['additional.environment'];

    var configGR = new GlideRecord('x_my_app_config');
    configGR.setValue('connection_alias', aliasId);
    configGR.setValue('environment', environment);
    configGR.insert();
})(aliasId, connectionSysId, jsonDefaultData, jsonDynamicData);
```

## Related Topics

- `aliastemplate-api` — Full property reference for `AliasTemplate`

- `alias-guide` — Creating Connection & Credential Aliases that reference templates

- `now-include-guide` — Using `Now.include()` to reference external script files

- `wfa-flow-guide` — Wiring your spoke connection alias to a Flow Designer action

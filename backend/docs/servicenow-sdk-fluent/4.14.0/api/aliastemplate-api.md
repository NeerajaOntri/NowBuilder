Version: 4.14.0

# AliasTemplate

Creates a Connection & Credential alias template (`sys_alias_templates`): a reusable
definition that controls the form fields and default values shown when a user
sets up a connection alias on the ServiceNow platform. Templates drive the wizard
UI that collects connection URLs, credentials, and other integration settings.

## Signature

```
AliasTemplate(config)
```

## Usage

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const MyHttpTemplate = AliasTemplate({
    $id: Now.ID['my-http-template'],
    name: 'My HTTP REST Template',
    dynamicDataSchema: {
        connectionFields: [
            { name: 'connectionUrl', label: 'Base URL', type: 'text', mandatory: true },
        ],
        credentialFields: [
            { name: 'username', label: 'Username', type: 'text', mandatory: true },
            { name: 'password', label: 'Password', type: 'password', mandatory: true },
        ],
    },
    defaultDataTemplate: {
        connection: { table: 'http_connection', name: 'My HTTP Connection', connectionUrl: 'https://api.example.com' },
        credential: { table: 'basic_auth_credentials', name: 'My HTTP Credential' },
    },
})
```

## Parameters

### config

`AliasTemplate`

The alias template configuration object.

Properties:

- 
$id (required): `string | number | ExplicitKey<string>`
Unique identifier for this alias template record. Use `Now.ID['kebab-name']` to
generate a stable sys_id tied to your application scope.

- 
name (required): `string`
Display name for the template shown in admin views and the connection alias picker.

- 
dynamicDataSchema (required): `DynamicDataSchema`
Structured definition of the form fields rendered by the Connection & Credential
wizard. See DynamicDataSchema below.

- 
defaultDataTemplate (required): `DefaultDataTemplate`
Default values pre-populated into the connection and credential records created
from this template. See DefaultDataTemplate below.

- 
preEditScript (optional): `string | ((aliasId: string, connectionSysId: string, jsonDefaultData: string, jsonDynamicData: string) => Array<{ name: string; value: unknown }>)`
Script that runs before the dynamic data form is rendered. Must return an array
of `{ name, value }` pairs to pre-populate additional fields shown in the edit view.
Use an inline string, `Now.include('./pre-edit.js')` to reference a separate file, or import
a server module function from `src/server/` (app_modules pattern).
See Using server modules below.

- 
onEditScript (optional): `string | ((aliasId: string, connectionSysId: string, jsonDefaultData: string, jsonDynamicData: string) => void)`
Script that runs each time the template's form is edited. Use it to keep dependent
fields in sync. Inline string, `Now.include('./on-edit.js')`, or import a server module function.
See Using server modules below.

- 
postProcessScript (optional): `string | ((aliasId: string, connectionSysId: string, jsonDefaultData: string, jsonDynamicData: string) => void)`
Script that runs after a connection or credential is created from this template.
Inline string, `Now.include('./post-process.js')`, or import a server module function.
See Using server modules below.

- 
testAction (optional): `string | Record<'sys_hub_action_type_definition'> | ReturnType<typeof Action>`
Reference to a Flow Designer action that tests a connection created from this
template. Pass a sys_id string, a `Record()` reference, or an `Action()` call.

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit/view access for other developers after the application is installed.

- read: Others can see the template logic but not change it.

- protected: Others cannot change this template.

- Omit to allow other developers to customize this template.

Note — script field defaults: When a script field is omitted, the build plugin
writes a default IIFE stub to the underlying XML column. The stub documents the
available arguments but performs no action. Scripts that match the default stub are
automatically omitted when the record is transformed back to Fluent code, keeping
round-trips clean. Only provide a value when you need custom logic.

### Using server modules

You can reference server-side JavaScript functions stored in `src/server/` (the app_modules pattern)
for any of the three script fields. This approach keeps script logic modular and testable.

Script parameters:

All script functions receive four parameters:

- `aliasId` (string) — sys_id of the alias record

- `connectionSysId` (string) — sys_id of the connection record

- `jsonDefaultData` (string) — JSON string of default data (parse with `JSON.parse()`)

- `jsonDynamicData` (string) — JSON string of dynamic data (parse with `JSON.parse()`)

Key points:

- Module files must be in `src/server/` directory

- Import with relative path and `.js` extension: `'../server/aliasHelpers.js'`

- Functions receive four individual parameters

- The build system automatically transforms module references to inline scripts

- Module functions are validated at build time for correct signatures

See the Template with Server Module Functions example below.

### DynamicDataSchema

Controls the fields shown in the Connection & Credential wizard form.

```
dynamicDataSchema: {
    connectionFields: DynamicDataSchemaField[]
    credentialFields: DynamicDataSchemaField[]
    additionalFields?: DynamicDataSchemaField[]
}
```

- 
connectionFields (required): `DynamicDataSchemaField[]`
Fields shown in the Connection section of the wizard (URL, host, port, etc.).

- 
credentialFields (required): `DynamicDataSchemaField[]`
Fields shown in the Credential section of the wizard (username, password, token, etc.).

- 
additionalFields (optional): `DynamicDataSchemaField[]`
Extra fields not categorised as connection or credential fields.

#### DynamicDataSchemaField

Each field definition shares these base properties:

- 
name (required): `string`
Identifier for the field — used as the key in the data object passed to scripts.

- 
label (optional): `string`
Human-readable label displayed above the field in the wizard form.

- 
type (required): `BasicFieldType | 'radio' | 'choice' | 'reference'`
Widget rendered for this field. `BasicFieldType` covers `'text' | 'date' | 'number' | 'password' | 'checkbox' | 'file'`.

- 
defaultValue (optional): `string | boolean | number`
Value pre-filled in the field when the wizard opens.

- 
hint (optional): `string`
Help text displayed below the field.

- 
mandatory (optional): `boolean`
When `true`, the wizard blocks progression until this field is filled.

The field definition is a discriminated union based on `type` — certain types
require additional properties:

| `type` | Extra required properties |
| `'text'` , `'password'` , `'date'` , `'number'` , `'checkbox'` , `'file'` | none |
| `'radio'` | `groups: GroupSchema[]` |
| `'choice'` | `choices: (string | ChoiceSchema)[]` |
| `'reference'` | `table: TableName` , `query?: string` |

`GroupSchema` — radio button group:

- name (required): `string` — Unique identifier for the group.

- label (optional): `string` — Display label shown next to the radio button.

- fields (required): `DynamicDataSchemaField[]` — Nested fields revealed when this group is selected.

- defaultGroup (optional): `boolean` — When `true`, this group is pre-selected when the wizard opens. Maps to `default_group`.

`ChoiceSchema` — dropdown option. Pass a plain string (used as both name and label) or an object:

- name (required): `string` — Value stored when this choice is selected.

- label (required): `string` — Display text shown to the user.

### DefaultDataTemplate

Specifies default values used when new connection and credential records are
created from this template.

```
defaultDataTemplate: {
    connection?: { table: ConnectionType, name: string, connectionUrl: string, ... }
    credential?: { table: TableName, name?: string, ... }
    additional?: { [key: string]: unknown }
}
```

- 
connection (optional): `object`
Defaults for the connection record.

- table (required): `'http_connection' | 'jdbc_connection' | 'orch_Jms_ds' | 'sys_connection'`
Backing ServiceNow table for the connection record. Determines which connection
form is presented to the user.

- name (required): `string` — Default display name for the connection record.

- connectionUrl (required): `string` — Default value for the connection URL field.

- useMid (optional): `boolean` — Whether to default to using a MID Server.

- Any additional keys are passed as default field values for the connection record.

- 
credential (optional): `object`
Defaults for the credential record.

- table (required): `TableName` — Backing table for the credential record.
Determines which credential form is shown (basic auth, certificate, OAuth, etc.).

- name (optional): `string` — Default display name for the credential record.

- Any additional keys are passed as default field values for the credential record.

- 
additional (optional): `{ [key: string]: unknown }`
Freeform extra data made available to the `postProcessScript` for creating custom
records alongside the connection and credential.

## Examples

### HTTP REST API Template

Basic HTTP connection template with username/password credentials and a pre-filled
base URL.

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const HttpRestTemplate = AliasTemplate({
    $id: Now.ID['http-rest-template'],
    name: 'HTTP REST API Template',
    dynamicDataSchema: {
        connectionFields: [
            { name: 'connectionUrl', label: 'Base URL', type: 'text', mandatory: true },
            { name: 'useMid', label: 'Use MID Server', type: 'checkbox' },
        ],
        credentialFields: [
            { name: 'username', label: 'Username', type: 'text', mandatory: true },
            { name: 'password', label: 'Password', type: 'password', mandatory: true },
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: 'HTTP REST Connection',
            connectionUrl: 'https://api.example.com',
        },
        credential: {
            table: 'basic_auth_credentials',
            name: 'HTTP REST Credential',
        },
    },
})
```

### OAuth2 Template with Radio Groups and Scripts

Advanced template that lets users pick an OAuth2 flow via radio buttons, with
pre-edit and post-process scripts and a test action.

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const OAuthApiTemplate = AliasTemplate({
    $id: Now.ID['oauth-api-template'],
    name: 'OAuth2 API Template',
    dynamicDataSchema: {
        connectionFields: [
            { name: 'baseUrl', label: 'API Base URL', type: 'text', mandatory: true },
            {
                name: 'authFlow',
                label: 'Auth Flow',
                type: 'radio',
                mandatory: true,
                groups: [
                    {
                        name: 'client_credentials',
                        label: 'Client Credentials',
                        fields: [
                            { name: 'tokenUrl', label: 'Token URL', type: 'text', mandatory: true },
                        ],
                    },
                    {
                        name: 'auth_code',
                        label: 'Authorization Code',
                        fields: [
                            { name: 'authUrl', label: 'Authorization URL', type: 'text', mandatory: true },
                            { name: 'tokenUrl', label: 'Token URL', type: 'text', mandatory: true },
                        ],
                    },
                ],
            },
        ],
        credentialFields: [
            { name: 'clientId', label: 'Client ID', type: 'text', mandatory: true },
            { name: 'clientSecret', label: 'Client Secret', type: 'password', mandatory: true },
        ],
    },
    defaultDataTemplate: {
        connection: { table: 'http_connection', name: 'OAuth2 Connection', connectionUrl: 'https://api.example.com' },
        credential: { table: 'basic_auth_credentials', name: 'OAuth2 Credential' },
    },
    preEditScript: Now.include('./pre-edit.js'),
    postProcessScript: Now.include('./post-process.js'),
    testAction: 'b7e1f3a2d4c589012e3f45678b9abc12',
})
```

### Template with Choice Dropdown and Additional Data

Template that uses a choice field for environment selection and stores extra
metadata in `additional` for post-processing.

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const DataPipelineTemplate = AliasTemplate({
    $id: Now.ID['data-pipeline-template'],
    name: 'Data Pipeline Template',
    dynamicDataSchema: {
        connectionFields: [
            { name: 'jdbcUrl', label: 'JDBC URL', type: 'text', mandatory: true },
            {
                name: 'environment',
                label: 'Environment',
                type: 'choice',
                mandatory: true,
                choices: [
                    { name: 'dev', label: 'Development' },
                    { name: 'staging', label: 'Staging' },
                    { name: 'prod', label: 'Production' },
                ],
            },
        ],
        credentialFields: [
            { name: 'username', label: 'DB User', type: 'text', mandatory: true },
            { name: 'password', label: 'DB Password', type: 'password', mandatory: true },
        ],
    },
    defaultDataTemplate: {
        connection: { table: 'jdbc_connection', name: 'Data Pipeline Connection', connectionUrl: 'jdbc:postgresql://db.example.com:5432/sales' },
        credential: { table: 'basic_auth_credentials', name: 'Data Pipeline Credential' },
        additional: {
            schema: 'public',
            maxPoolSize: 10,
        },
    },
    postProcessScript: Now.include('./post-process.js'),
})
```

### API Key Authentication Template

Template that uses an API key credential field stored as a password, backed by the
`api_key_credentials` table.

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const ApiKeyTemplate = AliasTemplate({
    $id: Now.ID['api-key-auth-template'],
    name: 'API Key Auth Template',
    dynamicDataSchema: {
        connectionFields: [
            {
                name: 'connection.name',
                label: 'Connection Name',
                type: 'text',
                hint: 'Display name for the connection',
                mandatory: true,
            },
            {
                name: 'connection.connection_url',
                label: 'Connection URL',
                type: 'text',
                hint: 'Base URL for API requests',
                mandatory: true,
            },
        ],
        credentialFields: [
            {
                name: 'credential.api_key',
                label: 'API Key',
                type: 'password',
                hint: 'API key for authentication',
                mandatory: true,
            },
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: 'My API Connection',
            connectionUrl: 'https://api.example.com',
            useMid: false,
        },
        credential: {
            table: 'api_key_credentials',
            name: 'My API Credential',
        },
    },
})
```

### Template with Additional Schema Fields and Scripts

Template that adds extra fields outside the connection/credential sections via
`additionalFields`, and uses `Now.include()` to reference external script files for
the pre-edit and post-process hooks. The `additional` key in `defaultDataTemplate`
passes those extra values to the post-process script.

```
import { AliasTemplate } from '@servicenow/sdk/core'

export const AdditionalFieldsTemplate = AliasTemplate({
    $id: Now.ID['additional-fields-template'],
    name: 'Additional Fields Template',
    dynamicDataSchema: {
        connectionFields: [
            {
                name: 'connection.connection_url',
                label: 'Connection URL',
                type: 'text',
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
                name: 'additional.account_name',
                label: 'Account Name',
                type: 'text',
                hint: 'Name of the account record to create after setup',
                mandatory: true,
            },
        ],
    },
    defaultDataTemplate: {
        connection: {
            table: 'http_connection',
            name: 'My Connection',
            connectionUrl: 'https://api.example.com',
        },
        credential: {
            table: 'api_key_credentials',
            name: 'My Credential',
        },
        additional: {
            account_name: '',
        },
    },
    preEditScript: Now.include('./pre-edit.js'),
    postProcessScript: Now.include('./post-process.js'),
})
```

### Template with Server Module Functions

Template that uses the app_modules pattern to reference server-side JavaScript functions
for script logic. This approach keeps script logic modular and testable.

```
// src/server/aliasHelpers.js
export function validateCredentials(aliasId, connectionSysId, jsonDefaultData, jsonDynamicData) {
    const defaultData = JSON.parse(jsonDefaultData)
    const dynamicData = JSON.parse(jsonDynamicData)
    
    // Validation logic here
    return [
        { name: 'validated', value: true },
        { name: 'timestamp', value: new Date().toISOString() }
    ]
}

export function setupConnection(aliasId, connectionSysId, jsonDefaultData, jsonDynamicData) {
    const defaultData = JSON.parse(jsonDefaultData)
    const dynamicData = JSON.parse(jsonDynamicData)
    
    // Post-process logic here
    // Create related records, call external APIs, etc.
}
```

```
// src/connection-credentials/AliasTemplate.now.ts
import { AliasTemplate } from '@servicenow/sdk/core'
import { validateCredentials, setupConnection } from '../server/aliasHelpers.js'

export const ModularTemplate = AliasTemplate({
    $id: Now.ID['modular-template'],
    name: 'Modular Template with Server Functions',
    dynamicDataSchema: {
        connectionFields: [
            { name: 'connectionUrl', label: 'Base URL', type: 'text', mandatory: true },
        ],
        credentialFields: [
            { name: 'apiKey', label: 'API Key', type: 'password', mandatory: true },
        ],
    },
    defaultDataTemplate: {
        connection: { table: 'http_connection', name: 'Connection', connectionUrl: '' },
        credential: { table: 'api_key_credentials', name: 'Credential' },
    },
    preEditScript: validateCredentials,
    postProcessScript: setupConnection,
})
```

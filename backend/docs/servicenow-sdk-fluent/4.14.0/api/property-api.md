Version: 4.14.0

# Property

Creates a System Property -- a key-value configuration setting read at runtime via `gs.getProperty()` (`sys_properties`). Properties allow admins to tune application behavior without code changes.

## Signature

```
Property(config)
```

## Parameters

### config

`Property<'string' | 'boolean' | 'image' | 'password2' | 'date_format' | 'integer' | 'choicelist' | 'time_format' | 'color' | 'uploaded_image' | 'password' | 'timezone' | 'short_string'>`

an object containing the following properties:

Properties:

- 
$id (required): `string | number | ExplicitKey<string>`

- 
name (required): `string`
Name of the property

- 
$meta (optional): `object`

- installMethod: `'first install' | 'demo' | 'once'`
Map a record to an output folder that loads only in specific circumstances.
'first install' - > 'unload',
'demo' -> 'unload.demo'

- 
choices (optional): `string[]`
Comma-separated values for a choice list

- 
description (optional): `string`
A brief, descriptive phrase describing the function of the property

- 
ignoreCache (optional): `boolean`
Determines whether to flush this property's value from all other server-side caches

- 
isPrivate (optional): `boolean`
If true, exclude this property from being imported via update sets

- 
roles (optional): `object`
The roles that have access to this property

- 
read (optional): `(string | Role)[]`

- 
write (optional): `(string | Role)[]`

- 
suffix (optional): `string`
Short identifier for the property (`sys_properties.suffix`). Defaults to the portion of `name` after the application scope prefix (e.g. `timeout` for `x_acme_app.timeout`). Set this explicitly to use a different value, e.g. `suffix: 'request_timeout'`.

- 
type (optional): `'' | 'string' | 'boolean' | 'image' | 'password2' | 'date_format' | 'integer' | 'choicelist' | 'time_format' | 'color' | 'uploaded_image' | 'password' | 'timezone' | 'short_string'`
Data type for the property

- 
value (optional): `string | number | boolean`
The desired value for the property

## See

- https://docs.servicenow.com/csh?topicname=property-api-now-ts.html&version=latest

## Examples

### Basic System Property

Create a simple string property with minimal configuration

```
/**
 * @title Basic System Property
 * @description Create a simple string property with minimal configuration
 */
import { Property } from '@servicenow/sdk/core'

Property({
    $id: Now.ID['test'],
    name: 'x_test.my_property',
    value: 'hello',
})
```

### Private Boolean Property

Create a private boolean property for feature flags

```
/**
 * @title Private Boolean Property
 * @description Create a private boolean property for feature flags
 */
import { Property } from '@servicenow/sdk/core'
Property({
    $id: Now.ID['bool_prop'],
    name: 'x_test.enable_feature',
    type: 'boolean',
    value: 'true',
    description: 'Enable the new feature',
    isPrivate: true,
})
```

### Property with Role-Based Access

Create a property with read/write role restrictions and value choices

```
/**
 * @title Property with Role-Based Access
 * @description Create a property with read/write role restrictions and value choices
 */
import { Property } from '@servicenow/sdk/core'

Property({
    $id: Now.ID['test'],
    name: 'x_test.my_property',
    type: 'string',
    value: 'hello',
    description: 'My property',
    choices: ['a', 'b', 'c'],
    ignoreCache: true,
    roles: {
        read: ['admin'],
        write: ['activity_admin'],
    },
})
```

For guidance on property types, runtime access, and configuration patterns, see the `property-guide` topic.

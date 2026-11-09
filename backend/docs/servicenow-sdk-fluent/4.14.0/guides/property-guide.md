Version: 4.14.0

# System Properties

Guide for creating ServiceNow System Properties using the Fluent API. Properties store key-value configuration for applications, read at runtime using `gs.getProperty()`, and allow admins to tune behavior without code changes.

## When to Use

- Adding configurable settings to an application (feature flags, thresholds, URLs)

- Storing values that admins should be able to change without modifying code

- Creating properties that business rules, scheduled scripts, or client code read at runtime

## Instructions

- Set `$id`: Every Property requires a unique `$id`. Use `Now.ID` notation (e.g., `$id: Now.ID['my_property']`) for all properties, including updates to existing OOB properties. See the `now-id-guide` topic for details on `Now.ID` notation.

- Name with scope prefix: Custom app property names must start with the application scope (e.g., `x_snc_example.my_setting`). Use dot notation to organize hierarchically. Exception: platform `glide.*` properties use no scope prefix -- see "Platform configuration properties" below.

- Choose the right type: Use `string` for text, `integer` for numbers, `boolean` for flags, `choicelist` for constrained options (provide a `choices` array of strings), `password`/`password2` for secrets. The `value` field type must match.

- Set access roles: Use the `roles` property to control who can read and write the property. Restrict write access to admin roles for sensitive settings.

- Use `isPrivate` for sensitive data: Set `isPrivate: true` for properties that should not be visible in the property list UI (e.g., API keys, internal thresholds).

- Provide a description: Always add a `description` explaining what the property controls and what valid values are -- this is what admins see when configuring the app.

## Key Concepts

### When to Use Properties vs Other Patterns

- Properties -- For values that change between environments or that admins tune (timeouts, feature flags, URLs)

- Business rules -- For logic that responds to data changes. Do not store logic in properties.

- Script includes -- For reusable code. Properties store data, not behavior.

### Caching

Properties are cached by default for performance. Set `ignoreCache: true` only for properties that must reflect changes immediately (rare). Most properties should keep the default (`false`).

## Platform Configuration Properties

When configuring platform-level features (accessibility, keyboard navigation, session behavior, UI settings, notifications, integrations), use `glide.*` property names in global scope.

- Use global scope. `glide.*` properties always belong to global scope.

- Do not add a scope prefix to the property `name` -- `glide.*` names are intentionally unprefixed.

- Property names vary across ServiceNow versions -- do not assume a property exists or guess its name. Verify the exact property name from the task description, ServiceNow documentation, or the `sys_properties` table on your instance. Known namespace prefixes: accessibility → `glide.ui.accessibility`; session → `glide.ui.session`; notifications → `glide.email`.

- If the property does not exist, create it with the full `glide.*` name and no scope prefix.

## Updating an Existing OOB Property

`sys_properties` coalesces on the `name` column — if you define a Property whose `name` matches an existing record on the instance, the build updates it in place rather than creating a duplicate. You do not need the existing record's `sys_id`.

Use `Now.ID` for `$id` as usual. Set `name` to the exact existing property name:

```
import { Property } from '@servicenow/sdk/core'

Property({
    $id: Now.ID['some-existing-property'],
    name: 'glide.ui.some_existing_property',
    type: 'string',
    value: 'updated_value',
})
```

The platform matches on `name` and updates the existing record. The `$id` is a project-internal identifier only.

## Avoidance

- Never omit the scope prefix from custom app property names -- scoped app properties without a scope prefix (e.g., `x_snc_example.*`) will fail validation. Exception: platform `glide.*` properties intentionally have no scope prefix.

- Never store large data in properties -- they are for simple configuration values, not data blobs

- Never use `ignoreCache: true` unless necessary -- it forces a database read on every `gs.getProperty()` call, impacting performance

## API Reference

For the full property reference, see the `property-api` topic.

## Examples

### Basic String Property

```
import { Property } from '@servicenow/sdk/core'

Property({
    $id: Now.ID['email-enabled'],
    name: 'x_snc_example.email.enabled',
    type: 'boolean',
    value: true,
    description: 'Enable or disable email notifications for the application',
    roles: {
        read: ['admin'],
        write: ['admin'],
    },
})
```

### Property with Role References

```
import { Property, Role } from '@servicenow/sdk/core'

const managerRole = Role({
    $id: Now.ID['manager_role'],
    name: 'x_snc_example.manager',
})

const adminRole = Role({
    $id: Now.ID['admin_role'],
    name: 'x_snc_example.admin',
    containsRoles: [managerRole],
})

Property({
    $id: Now.ID['1234'],
    name: 'x_snc_example.some.new.prop',
    type: 'string',
    value: 'hello',
    description: 'A new property',
    roles: {
        read: ['admin'],
        write: [adminRole, managerRole],
    },
    ignoreCache: false,
    isPrivate: false,
})
```

For the full Role API reference, see the `Role` topic.

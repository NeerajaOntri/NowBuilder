Version: 4.14.0

# GraphQL APIs

Guide for creating ServiceNow scripted GraphQL APIs using the Fluent API. A GraphQL API pairs an SDL schema with resolvers that fetch field data, secured by a schema-gate ACL for the whole API and field-level path-based ACLs enforced at query time.

## When to Use

- Exposing application data through a typed GraphQL schema instead of REST endpoints

- Letting clients request exactly the fields they need in a single query

- Securing individual schema fields with path-based ACLs rather than one all-or-nothing gate

- Resolving polymorphic results (unions and interfaces) with type resolvers

## Instructions

- Write the schema first: Define your types in SDL and set it on `schema`. Keep it inline for small schemas, or move it to a file with `Now.include('./schema.graphql')`. The platform compiles the SDL when the record is inserted.

- Bind resolvers to paths: Each `GraphQLResolver` needs its own `$id`, a unique `name`, and a `paths` array of `Type:field` entries (e.g. `Query:hello`). One resolver can serve several paths. The plugin creates one resolver mapping (`sys_graphql_resolver_mapping`) per path.

- Keep resolver scripts in server modules: Import a named function from `src/server` so the resolver body is type-checked and reusable. Inline script strings and `Now.include('./resolver.js')` are supported for raw script content, but writing the function inline in `script` is a build error. For fields with arguments, read them with `env.getArguments()`.

- Add type resolvers for unions and interfaces: For each union or interface in the SDL, add a `GraphQLTypeResolver` with its own `$id`, a `typeName` matching the SDL type, and a `script` that returns the concrete type name.

- Secure the API, then the fields: Reference schema-gate ACLs from `enforceAcl` to control access to the whole API. Secure individual fields with standalone `Acl({ type: 'graphql', ... })` records whose slash-delimited `name` follows the query path, such as `/xSncMyApp/catalogGql/items/cost`. Resolver mapping paths such as `Item:cost` use a separate format.

## Key Concepts

### Namespace and Query Envelope

`namespace` is the key the API is reached under inside the platform GraphQL envelope. A query targets `POST /api/now/graphql` and wraps fields under `{ <applicationNamespace> { <namespace> { ... } } }`. The application namespace and schema namespace also form the prefix of the runtime ACL paths for the API's fields.

`applicationNamespace` is derived from the application scope, camel-cased with separators removed: scope `x_snc_my_app` becomes `xSncMyApp`, so queries are wrapped as `{ xSncMyApp { myApi { ... } } }`. Setting it explicitly is only honored in global scope, where the platform's own value depends on instance settings and the caller's roles. The build cannot read those, so it falls back to `now`, which is why a global-scope app should set it explicitly. The value must be a valid GraphQL name and 40 characters or fewer. In a scoped app the value is always derived; an explicit value that differs from the derived one is reported as a hint and ignored.

`namespace` must be a valid GraphQL name: a letter or underscore, followed by letters, digits, or underscores. Two APIs in the same application namespace cannot share a namespace, and the build reports an error if they do.

### Security Model

Security is two-tier. Keep the authentication, ACL authorization, and internal-role gates enabled unless you have a specific reason to weaken them.

- `enforceAcl`: the schema-gate ACLs (`sys_security_acl`) applied to the whole API. Reference `Acl` objects by variable or by `sys_id`.

- Field-level path ACLs: standalone `Acl({ type: 'graphql', ... })` records whose `name` follows the slash-delimited query path (for example `/xSncMyApp/myApi/secret`). The path starts with `applicationNamespace` and `namespace`, followed by the field names used in the query tree. It uses neither the raw application scope nor the resolver mapping format. A denied field resolves to `null`; a user with the `admin` role overrides the check unless `adminOverrides` is false.

See the `graphqlapi-api` topic for the full property reference.

### Contextual ACL Depth

`contextualAclMaxDepth` bounds how deep field-level path ACLs are enforced. Depth is measured on the runtime ACL path, which counts the application namespace and schema namespace as its first two segments: `/xSncMyApp/catalogGql/items` is depth 3 and `/xSncMyApp/catalogGql/items/cost` is depth 4. The default of 4 therefore covers top-level and second-level schema fields. Count the slash-separated segments of the ACL name you need enforced and set the value to at least that number.

### Resolvers and Type Resolvers

- Resolvers fetch the data for a field. `paths` binds one resolver to the schema fields it serves. Use `$id` to keep the same resolver record stable if you later rename it.

- Type resolvers decide which concrete type a union or interface value is, so the engine knows which fields to resolve next. Use `$id` to keep the same type-resolver record stable if you later rename the SDL type.

## Avoidance

- Never weaken the security gates without reason -- setting any `requires*` flag to `false` or leaving `enforceAcl` empty removes a layer of access control.

- Never omit child `$id`s -- resolver and type-resolver names can change, so `$id` is what keeps updates attached to the original records.

- Never reuse a resolver name, path, or type-resolver `typeName` -- each must be unique within the API. Duplicates are reported as build errors.

- Never set `contextualAclMaxDepth` below the segment count of a path ACL you need enforced -- `/xSncMyApp/catalogGql/items/cost` needs at least 4, and deeper fields are not ACL-checked.

- Avoid inline scripts for non-trivial resolvers -- use named server-module functions so scripts stay editable, reusable, and type-checked.

## API Reference

For the full property reference (GraphQLApi, resolvers, type resolvers), see the `graphqlapi-api` topic.

## Examples

### Minimal GraphQL API

```
import { GraphQLApi } from '@servicenow/sdk/core'
import { resolveHello } from '../server/hello-resolver'

GraphQLApi({
    $id: Now.ID['gql-hello'],
    name: 'Hello GraphQL',
    namespace: 'helloGql',
    schema: `
      type Query {
        hello: String
      }
    `,
    resolvers: [
        {
            $id: Now.ID['hello-resolver'],
            name: 'helloResolver',
            paths: ['Query:hello'],
            script: resolveHello,
        },
    ],
})
```

### Secured API with a Field-Level Path ACL

```
import { GraphQLApi, Acl } from '@servicenow/sdk/core'
import { resolveItems } from '../server/items-resolver'

const schemaGate = Acl({
    $id: Now.ID['gql-gate'],
    type: 'graphql',
    name: 'catalogGql',
    operation: 'execute',
    roles: ['catalog_reader'],
})

Acl({
    $id: Now.ID['gql-cost-field'],
    type: 'graphql',
    name: '/xSncMyApp/catalogGql/items/cost',
    operation: 'execute',
    roles: ['catalog_admin'],
})

GraphQLApi({
    $id: Now.ID['gql-catalog'],
    name: 'Catalog GraphQL',
    namespace: 'catalogGql',
    enforceAcl: [schemaGate],
    schema: `
      type Item { name: String cost: Float }
      type Query { items: [Item] }
    `,
    resolvers: [
        {
            $id: Now.ID['items-resolver'],
            name: 'itemsResolver',
            paths: ['Query:items'],
            script: resolveItems,
        },
    ],
})
```

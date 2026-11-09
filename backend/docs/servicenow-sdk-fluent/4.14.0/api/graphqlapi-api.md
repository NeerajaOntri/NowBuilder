Version: 4.14.0

# GraphQLApi

Creates a scripted GraphQL API (`sys_graphql_schema`) with its resolvers and type resolvers, secured by schema-gate and field-level path-based GraphQL ACLs.

## Signature

```
GraphQLApi(config)
```

## Parameters

### config

`GraphQLApi`

Properties:

- 
$id (required): `string | number | ExplicitKey<string>`

- 
name (required): `string`
The name of the GraphQL API.

- 
applicationNamespace (optional): `string`
The top-level namespace in the query envelope (for example `xSncMyApp` in `{ xSncMyApp { myApi { ... } } }`). Derived from the application scope, so `x_snc_my_app` becomes `xSncMyApp`. Only honored in global scope, where the platform's own value depends on instance settings and the caller's roles. The build cannot read those, so it falls back to `now`, which is why a global-scope app should set this explicitly. Must be a valid GraphQL name and 40 characters or fewer.

- 
namespace (required): `string`
The API namespace used in the query envelope and in runtime ACL paths (for example `myApi` in `{ xSncMyApp { myApi { ... } } }`). Must be a valid GraphQL name: a letter or underscore, followed by letters, digits, or underscores. Two APIs in the same application namespace cannot share a namespace.

- 
schema (required): `string`
The schema definition language (SDL) for the API. Inline, or `Now.include('./schema.graphql')`. The platform compiles it on insert.

- 
resolvers (optional): `GraphQLResolver[]`
Resolvers that fetch field data, each bound to one or more schema paths.

- 
$id (required): `string | number | ExplicitKey<string>`
Stable identifier for the resolver record.

- 
name (required): `string`
Identifier for the resolver, unique within the schema. The `paths` it serves point back to this name.

- 
script (required): `((env: any) => unknown) | string`
Server script that resolves the field value. Use a named function imported from a server module in `src/server`, an inline string, or `Now.include('./resolver.js')`. Writing the function inline is a build error. For fields with arguments, read them with `env.getArguments()`.

- 
paths (required): `string[]`
Schema fields this resolver serves, each in `Type:field` form (for example `Query:hello`). One resolver mapping (`sys_graphql_resolver_mapping`) is created per path.

- 
typeResolvers (optional): `GraphQLTypeResolver[]`
Type resolvers for the unions and interfaces in the schema.

- 
$id (required): `string | number | ExplicitKey<string>`
Stable identifier for the type resolver record.

- 
typeName (required): `string`
Name of the union or interface type in the SDL this resolver applies to.

- 
script (required): `((env: any) => unknown) | string`
Server script that returns the concrete type name. Read the object being resolved with `env.getObject()`. Use a named function imported from a server module in `src/server`, an inline string, or `Now.include('./typeResolver.js')`. Writing the function inline is a build error.

- 
active (optional): `boolean`
Indicates whether the API can serve requests. Defaults to true.

- 
enforceAcl (optional): `(string | Acl)[]`
Schema-gate ACLs (`sys_security_acl`) that control access to the whole API. Accepts ACL `sys_id`s or `Acl` references. Field-level path ACLs are standalone `Acl({ type: 'graphql', ... })` records named after the slash-delimited query path, which starts with the application namespace and namespace, such as `/xSncMyApp/myApi/items/cost`.

- 
requiresAuthentication (optional): `boolean`
If true, callers must be authenticated. Defaults to true.

- 
requiresAclAuthorization (optional): `boolean`
If true, the schema-gate ACLs in `enforceAcl` are enforced. Defaults to true.

- 
requiresSncInternalRole (optional): `boolean`
If true, callers must hold the `snc_internal` role. Defaults to true.

- 
contextualAclMaxDepth (optional): `number`
The maximum path depth at which field-level path ACLs are enforced. Depth counts every segment of the runtime ACL path, including the two envelope segments, so `/xSncMyApp/myApi/hello` is depth 3 and `/xSncMyApp/myApi/items/cost` is depth 4. Defaults to 4, which covers top-level and second-level fields; fields deeper than this are not ACL-checked.

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit/view access for other developers after the application is installed.

- read: Others can see the schema and resolver logic but not change it.

- protected: Others cannot change this GraphQL API.

- Omit to allow other developers to customize this GraphQL API.

## The resolver environment (`env`)

Each script receives the platform's GraphQL resolution environment as its `env` argument. `env` is typed `any`, so its methods are not autocompleted — use this reference. Resolvers and type resolvers receive different environments:

Resolver scripts get a resolver environment:

- `env.getArguments()` — the field's arguments, keyed by argument name

- `env.getSource()` — the result of the parent field's fetch (the object this field is resolved on). Returns `null` for a top-level field such as `Query:hello`, which has no parent.

Type-resolver scripts get a type-resolution environment:

- `env.getArguments()` — the field's arguments, keyed by argument name

- `env.getObject()` — the object returned by the data fetcher, used to pick the concrete type

- `env.getTypeName()` — the name of the union or interface type being resolved

## See

- https://docs.servicenow.com/csh?topicname=graphqlapi-api-now-ts.html&version=latest

## Examples

### Simple GraphQL API

Create a GraphQL API with one resolver bound to a single schema path

```
/**
 * @title Simple GraphQL API
 * @description Create a GraphQL API with one resolver bound to a single schema path
 */
import { GraphQLApi } from '@servicenow/sdk/core'
import { resolveHello } from '../server/hello-resolver'

GraphQLApi({
    $id: Now.ID['graphql-simple'],
    name: 'Simple GraphQL',
    namespace: 'simpleGql',
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

server/hello-resolver.js

```
export function resolveHello(env) {
    return 'Hello, World!'
}
```

### GraphQL API with Field Arguments

Read GraphQL field arguments from the resolver environment with `env.getArguments()`

```
/**
 * @title GraphQL API with Field Arguments
 * @description Resolve a single record by reading field arguments from env.getArguments()
 */
import { GraphQLApi } from '@servicenow/sdk/core'
import { resolveMovie } from '../server/movie-resolver'

GraphQLApi({
    $id: Now.ID['graphql-movie'],
    name: 'Movie GraphQL',
    namespace: 'movieApi',
    schema: `
      type Movie {
        id: ID!
        title: String
      }

      type Query {
        movie(id: ID!): Movie
      }
    `,
    resolvers: [
        {
            $id: Now.ID['movie-resolver'],
            name: 'movieResolver',
            paths: ['Query:movie'],
            script: resolveMovie,
        },
    ],
})
```

server/movie-resolver.js

```
const movies = [
    { id: '1', title: 'Inception' },
    { id: '2', title: 'The Matrix' },
]

export function resolveMovie(env) {
    const { id } = env.getArguments()
    return movies.find((movie) => movie.id === id) || null
}
```

### GraphQL API with Field-Level Path ACLs

Secure the whole API with a schema-gate ACL and a single field with a path ACL

```
/**
 * @title GraphQL API with Field-Level Path ACLs
 * @description Secure the whole API with a schema-gate ACL and a single field with a path ACL
 */
import { GraphQLApi, Acl } from '@servicenow/sdk/core'
import { helloResolver, secretResolver } from '../server/query-resolver'

const schemaGate = Acl({
    $id: Now.ID['gql-schema-gate'],
    type: 'graphql',
    name: 'simpleGql',
    operation: 'execute',
    roles: ['graphql_reader'],
})

Acl({
    $id: Now.ID['gql-secret-field'],
    type: 'graphql',
    name: '/xSncMyApp/simpleGql/secret',
    operation: 'execute',
    roles: ['admin'],
})

GraphQLApi({
    $id: Now.ID['graphql-secured'],
    name: 'Secured GraphQL',
    namespace: 'simpleGql',
    enforceAcl: [schemaGate],
    contextualAclMaxDepth: 5,
    schema: `
      type Query {
        hello: String
        secret: String
      }
    `,
    resolvers: [
        {
            $id: Now.ID['hello-resolver'],
            name: 'helloResolver',
            paths: ['Query:hello'],
            script: helloResolver,
        },
        {
            $id: Now.ID['secret-resolver'],
            name: 'secretResolver',
            paths: ['Query:secret'],
            script: secretResolver,
        },
    ],
})
```

server/query-resolver.js

```
export function helloResolver(env) {
    return 'Hello, World!'
}

export function secretResolver(env) {
    return 'classified'
}
```

### GraphQL API with a Type Resolver

Resolve the concrete type of a union with a type resolver

```
/**
 * @title GraphQL API with a Type Resolver
 * @description Resolve the concrete type of a union with a type resolver
 */
import { GraphQLApi } from '@servicenow/sdk/core'
import { resolveSearch, resolveSearchResult } from '../server/search-resolvers'

GraphQLApi({
    $id: Now.ID['graphql-union'],
    name: 'Union GraphQL',
    namespace: 'unionGql',
    schema: `
      type Article { headline: String }
      type Video { duration: Int }
      union SearchResult = Article | Video
      type Query { search: SearchResult }
    `,
    resolvers: [
        {
            $id: Now.ID['search-resolver'],
            name: 'searchResolver',
            paths: ['Query:search'],
            script: resolveSearch,
        },
    ],
    typeResolvers: [
        {
            $id: Now.ID['search-result-resolver'],
            typeName: 'SearchResult',
            script: resolveSearchResult,
        },
    ],
})
```

server/search-resolvers.js

```
export function resolveSearch(env) {
    return { headline: 'GraphQL in Fluent' }
}

export function resolveSearchResult(env) {
    return env.getObject().duration ? 'Video' : 'Article'
}
```

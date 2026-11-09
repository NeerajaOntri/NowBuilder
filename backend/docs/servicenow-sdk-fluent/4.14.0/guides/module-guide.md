Version: 4.14.0

# JavaScript Modules

JavaScript modules are the modern, preferred approach for all server-side code in Fluent projects. Modules support `import`/`export`, provide access to typed Glide APIs via `@servicenow/glide`, enable code reuse across your application, and integrate with third-party npm libraries.

## When to Use

Use modules for server-side scripts in APIs that accept function types. Not all APIs support modules — some `script` properties only accept strings. If the compiler or build rejects a module import (for example, a type error such as `Type '() => void' is not assignable to type 'string'`, or a similar diagnostic), the API does not support modules and you should use `Now.include()` instead (see the `now-include-guide` topic). The exact error will vary depending on the structure of your module export and the API you're targeting.

APIs that support modules (accept functions):

- BusinessRule, ScriptAction, UiAction — `script` property

- RestApi route handlers — `script` property

- CatalogItemRecordProducer — `script` and `postInsertScript` properties

- ScheduledScript — `script` property

APIs that require Now.include() or inline strings:

- ScriptInclude, ClientScript — `script` is string-only

- CatalogClientScript, CatalogUiPolicy, UiPolicy — script fields are string-only

- SPWidget — all script fields are string-only

- Record API — data values are strings

### Additional use cases

- Organizing reusable server-side code into importable files

- Importing Glide APIs (`gs`, `GlideRecord`, etc.) for use in module files

- Adding third-party npm libraries to an application

## Instructions

- Module file location in src Module files must be placed in the `serverModules` directory defined in `now.config.json`, which defaults to `src/server`

- Import Glide APIs explicitly: In module files, `gs`, `GlideRecord`, and other Glide APIs are NOT automatically available. You must import them from `@servicenow/glide`. Analyze your script for ALL ServiceNow APIs used and import each one.

- Exception -- Script Include classes: When writing Script Include class files (`Class.create` pattern), do NOT import Glide APIs. They are automatically available in Script Include execution context. Only import other Script Include classes from `@servicenow/glide/<scopeName>`.

- Use `export`/`import` in modules, `require` in scripts: Modules use ES module syntax (`export`/`import`). Business rules, script includes, and other server scripts use `require` to consume module exports.

- Declare dependencies in package.json: Third-party npm libraries must be declared in `dependencies`. Never modify versions of existing dependencies unless explicitly requested.

- Verify Glide API methods exist: Only use methods explicitly defined in `@servicenow/glide` type definitions. Do not assume methods exist based on naming conventions.

- Use `GlideDateTime` instead of `gs.nowDateTime()` -- `gs.nowDateTime()` is not allowed in scoped applications.

- Use Typescript for creating module code unless instructed to use Javascript explicitly

## Key Concepts

### Import Patterns

- Glide APIs in modules: `import { gs, GlideRecord } from '@servicenow/glide'`

- Namespaced APIs: `import { RESTAPIRequest } from '@servicenow/glide/sn_ws_int'`

- Script Include classes: `import { MyClass } from '@servicenow/glide/x_my_scope'`

- Global-scope Script Includes: `import { global } from '@servicenow/glide/global'`, then use `new global.MyClass()`

- Module code in scripts: `const { myFunction } = require('path/to/module')`

### Script Include Module Rules

This is the most common source of errors:

- Module files with normal functions -- MUST import Glide APIs from `@servicenow/glide`

- Module files with Script Include classes (`Class.create`) -- must NOT import Glide APIs (they are auto-available)

- Consuming Script Include classes from other modules -- import from `@servicenow/glide/<scopeName>` for scoped Script Includes, or `@servicenow/glide/global` for Script Includes defined in the global scope (including platform ones like `AbstractAjaxProcessor`)

### Exposing Modules Through Script Includes

Many platform features still require script includes — GlideAjax, cross-scope APIs, and extension points that call script includes by name. When your logic lives in a module but needs to be accessible through these mechanisms, create a script include that acts as a thin bridge using `require()`. See the "Bridging Modules Through Script Includes" section in the `script-include-guide` topic for the full pattern and examples.

### Subpath Imports

Use subpaths in `package.json` to create shorthand imports:

```
{
    "imports": {
        "#calc": "calculus",
        "#derivative": "calculus/derivative"
    },
    "dependencies": {
        "calculus": "1.0.0"
    }
}
```

Then use the shorthand:

```
import { derivative } from '#derivative'
import * as calculus from '#calc'
```

### Limitations

- Modules work only within the application scope -- no cross-scope module sharing

- Node.js APIs are not supported

- Third-party libraries cannot access ServiceNow APIs such as GlideRecord and other imports from `@servicenow/glide`

- CommonJS modules from third-party libs are supported when bundled through Rollup with the CommonJS plugin (the SDK handles this automatically); see the `npm-libraries-guide` topic for compatible packages

- Modern ECMAScript syntax is largely supported, with some features disallowed for security or platform reasons — see the `javascript-compatibility-guide` topic for details and caveats

## Avoidance

- Never use Glide APIs without importing them in module files -- they are NOT globally available in module context

- Never import Glide APIs in Script Include class files -- they ARE globally available in that context

- Never reference Script Include classes via scope-prefix dot notation in modules -- `new x_myapp.MyUtils()` or `new global.MyUtils()` only works in non-module server scripts, where the platform injects those namespace objects automatically. Modules don't get that injection, so the reference is `undefined` and fails at runtime. Always import instead: `import { MyUtils } from '@servicenow/glide/x_myapp'` for scoped classes, or `import { global } from '@servicenow/glide/global'` for global-scope classes.

- Importing a Script Include class with no generated type declaration fails to compile (e.g. `Cannot find module '@servicenow/glide/global' or its corresponding type declarations.`) -- try regenerating types with `now-sdk dependencies` first. If the generated `.d.ts` still doesn't include the class, add a manual `.d.ts` declaration for it and wire that file into your module `tsconfig.json`'s `include`.

- Never use methods not in `@servicenow/glide` type definitions -- ServiceNow's Glide objects have specific, limited APIs

- Never modify existing dependency versions in package.json -- only add new dependencies

- Never use `gs.nowDateTime()` in scoped apps -- use `new GlideDateTime().getDisplayValue()` instead

## Examples

### Full Pattern: Business Rule with Module

This is the recommended pattern for server-side scripts. Write the logic in a module file and import it in the `.now.ts` definition:

Fluent definition (`src/fluent/business-rules/validate-request.now.ts`):

```
import '@servicenow/sdk/global'
import { BusinessRule } from '@servicenow/sdk/core'
import { validateRequest } from '../../server/business-rules/validate-request'

BusinessRule({
    $id: Now.ID['validate-request'],
    name: 'Validate Request',
    table: 'x_myapp_request',
    when: 'before',
    action: ['insert', 'update'],
    script: validateRequest,
})
```

Module file (`src/server/business-rules/validate-request.ts`):

```
import { gs, GlideRecord } from '@servicenow/glide'

export function validateRequest(current: GlideRecord<'x_myapp_request'>, previous: GlideRecord<'x_myapp_request'>) {
    const title = current.getValue('short_description')
    if (!title) {
        gs.addErrorMessage('Short description is required')
        current.setAbortAction(true)
    }
}
```

### Exporting from a Module

```
function myFunction() {}
const myVariable = 'value'

// Named exports for multiple features
export { myFunction, myVariable }
```

### Importing in Another Module

```
import { feature } from 'path/to/module'
```

### Importing in a Server Script (Business Rule, etc.)

```
const { feature } = require('path/to/module')
```

### Importing Glide APIs in a Module

```
import { gs } from '@servicenow/glide'
import { GlideRecord } from '@servicenow/glide'

// Namespaced APIs
import { RESTAPIRequest, RESTAPIResponse } from '@servicenow/glide/sn_ws_int'
```

### Using Script Include Classes from Modules

```
import { RecordUtils } from '@servicenow/glide/x_my_scope'

export function onRecordInsert(current, previous) {
    var recordUtils = new RecordUtils()
}
```

### Using Global-Scope Script Includes from Modules

Script Includes defined in the global scope -- whether your own or platform-provided (`AbstractAjaxProcessor`, etc.) -- are imported via `@servicenow/glide/global`, not a scope name:

```
import { gs } from '@servicenow/glide'
import { global } from '@servicenow/glide/global'

export function info(message: string) {
    const scriptInclude = new global.ScriptIncludeName()
    const result = scriptInclude.run()
    gs.info(result)
}
```

### Adding Dependencies in package.json

```
{
    "name": "test",
    "version": "1.0.0",
    "dependencies": {
        "math": "1.0.0"
    }
}
```

When adding new dependencies, NEVER modify the versions of existing dependencies. Only add the new entry.

Version: 4.14.0

# NPM Library Compatibility

Reference of npm libraries tested in the Australia release of the ServiceNow platform. For the authoritative list, see the official Third-party library support documentation. Libraries are categorized into three tiers: supported, limited support, and unsupported.

## How to Use

Add the library to `dependencies` in `package.json`:

```
{
    "dependencies": {
        "lodash": "4.17.21"
    }
}
```

Then import in a module file (`src/server/`):

```
import _ from 'lodash'
import { format } from 'date-fns'
```

Or via `require()` in a server script:

```
const _ = require('lodash')
```

See the `module-guide` topic for the full module system documentation.

## Supported third-party libraries

These libraries have been tested and validated for use with the ServiceNow SDK:

- `@langchain/textsplitters`

- `acorn`

- `bn.js`

- `camelcase`

- `chance`

- `clone`

- `date-fns`

- `dayjs`

- `debug`

- `diff`

- `docxtemplater`

- `extend`

- `html-parser-lite`

- `iconv-lite`

- `inherits`

- `ini`

- `js-yaml`

- `lodash`

- `lru-cache`

- `marked`

- `mime`

- `mime-types`

- `moment`

- `moment-timezone`

- `ms`

- `openai`

- `path-to-regexp`

- `pdf-lib`

- `pizzip`

- `ramda`

- `reflect-metadata`

- `saxes`

- `semver`

- `strip-ansi`

- `tslib`

- `underscore`

- `uuid`

- `validator`

- `xtend`

## Third-party libraries with limited support

These libraries work partially but are constrained by server-side scripting features not currently supported by the JavaScript engine:

- `@aws-sdk/client-s3`

- `effect`

- `fast-csv`

- `underscore.string`

- `util`

## Unsupported third-party libraries

These libraries have been tested and do not work with the ServiceNow server-side runtime:

- `@faker-js/faker`

- `ajv`

- `archiver`

- `axios`

- `deep-equal`

- `eml-parser`

- `exceljs`

- `jszip`

- `jws`

- `minimatch`

- `qs`

- `unzipper`

## Important Notes

- No Glide API access by default: Libraries run in a pure JavaScript sandbox and cannot call `GlideRecord`, `gs`, or other ServiceNow APIs by default; pass data to/from libraries explicitly instead. This is configurable per-library via the `trustedModules` property in `now.config.json`, which grants Glide API access to the listed packages. Only mark a library trusted if you control its source, typically one developed in-house.

- CommonJS compatibility required: The SDK bundles modules using Rollup with the CommonJS plugin. Libraries that only provide ES module builds without a CommonJS fallback may not work.

- Declare in `dependencies`: Always use `dependencies`, not `devDependencies`, for libraries used in server-side code that gets deployed.

- Limited and unsupported libraries: Libraries with limited or no support are constrained by server-side scripting features not currently supported by the JavaScript engine. See the `javascript-compatibility-guide` topic for details on feature support.

- Exact versions: Use exact version numbers (no `^` or `~`) to ensure reproducible builds.

- Node.js-specific sub-modules: Some libraries have optional sub-modules that use Node.js APIs (`fs`, `child_process`). Avoid importing those sub-paths directly.

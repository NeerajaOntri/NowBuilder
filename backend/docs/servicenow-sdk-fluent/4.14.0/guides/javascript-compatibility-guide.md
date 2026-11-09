Version: 4.14.0

# JavaScript Compatibility

Reference for ECMAScript features supported on the ServiceNow server-side JavaScript engine. For the full per-feature matrix, see the official JavaScript engine feature support documentation.

## JavaScript Modes

ServiceNow has two server-side JavaScript modes:

- ECMAScript 2021 (ES12) mode — the default for Fluent/SDK projects. Supports modern syntax documented below.

- ES5 Standards mode — a restricted mode used by legacy scripts. Most ES6+ features are "Not Supported" and many builtins (`Promise`, `Proxy`, typed arrays, `WeakMap`/`WeakSet`, generators) are "Disallowed".

The JavaScript mode is configured at the app level. Check the `jsLevel` field in your `now.config.json` to see which mode your project targets (defaults to `latest`, which maps to ES12 mode).

The tables below apply to ES12 mode. For the full per-feature matrix including ES5 mode, see the official docs link above.

## Supported Syntax Features

### ES6 / ES2015

| Feature | Example |
| `let` / `const` | `const name = 'Alice'; let count = 0` |
| Arrow functions | `const add = (a, b) => a + b` |
| Classes | `class Animal { constructor(name) { this.name = name } }` |
| Template literals | ``Hello, ${name}!`` |
| Destructuring (objects) | `const { id, name } = record` |
| Destructuring (arrays) | `const [first, ...rest] = items` |
| Spread operator | `const merged = { ...defaults, ...overrides }` |
| Rest parameters | `function sum(...nums) { return nums.reduce((a, b) => a + b, 0) }` |
| Default parameters | `function greet(name = 'World') { return \` Hello, ${name}!` }` |
| Computed property names | `const key = 'foo'; const obj = { [key]: 'bar' }` |
| `for...of` | `for (const item of items) { ... }` |
| `Promise` | `new Promise((resolve, reject) => { ... })` |
| `Map` / `Set` | `const m = new Map(); const s = new Set()` |
| `WeakMap` / `WeakSet` | `const cache = new WeakMap()` |
| `Symbol` | `const id = Symbol('id')` |
| Shorthand properties | `const obj = { name, value }` |
| Method shorthand | `const obj = { greet() { return 'hi' } }` |
| `Object.assign()` | `Object.assign(target, source)` |
| Generators (basic) | `function* gen() { yield 1; yield 2 }` |

### ES2016

| Feature | Example |
| Exponentiation operator | `2 ** 10 // 1024` |
| `Array.prototype.includes` | `[1, 2, 3].includes(2) // true` |

### ES2017

| Feature | Example |
| `async` / `await` (basic) | `async function fetchData() { const result = await query() }` |
| `Object.entries()` | `for (const [key, val] of Object.entries(obj)) { ... }` |
| `Object.values()` | `Object.values(config).forEach(v => process(v))` |
| `String.prototype.padStart` | `'5'.padStart(3, '0') // '005'` |
| `String.prototype.padEnd` | `'hi'.padEnd(5, '.') // 'hi...'` |

### ES2018

| Feature | Example |
| Object rest properties | `const { a, ...rest } = obj` |
| Object spread properties | `const copy = { ...original, extra: true }` |
| `Promise.prototype.finally` | `fetch().then(handle).finally(cleanup)` |
| RegExp named capture groups | `/(?<year>\d{4})-(?<month>\d{2})/.exec(str)` |
| RegExp lookbehind assertions | `/(?<=\$)\d+/.exec('$100')` |
| RegExp `s` (dotAll) flag | `/foo.bar/s.test('foo\nbar')` |
| RegExp Unicode property escapes | `/\p{Script=Greek}/u` |

### ES2019

| Feature | Example |
| `Array.prototype.flat` | `[[1, 2], [3]].flat() // [1, 2, 3]` |
| `Array.prototype.flatMap` | `[1, 2].flatMap(x => [x, x * 2])` |
| `Object.fromEntries` | `Object.fromEntries([['a', 1], ['b', 2]])` |
| `String.prototype.trimStart` | `'  hello'.trimStart()` |
| `String.prototype.trimEnd` | `'hello  '.trimEnd()` |
| Optional catch binding | `try { ... } catch { ... }` |

### ES2020

| Feature | Example |
| Optional chaining ( `?.` ) | `const city = user?.address?.city` |
| Nullish coalescing ( `??` ) | `const label = value ?? 'default'` |
| `BigInt` | `const big = 9007199254740993n` |
| `globalThis` | `globalThis.myGlobal = 'value'` |
| `Promise.allSettled` | `await Promise.allSettled([p1, p2])` |
| `String.prototype.matchAll` | `for (const match of str.matchAll(/\d+/g)) { ... }` |

### ES2021

| Feature | Example |
| Logical assignment ( `&&=` , `||=` , `??=` ) | `config.debug ??= false` |
| `String.prototype.replaceAll()` | `str.replaceAll('foo', 'bar')` |
| `Promise.any()` | `await Promise.any([p1, p2])` |
| Numeric separators | `const billion = 1_000_000_000` |

### ES2022

| Feature | Example |
| Public instance class fields | `class Foo { x = 1 }` |
| Public static class fields | `class Foo { static COUNT = 0 }` |
| `Array.prototype.at()` | `[1, 2, 3].at(-1) // 3` |
| `Object.hasOwn()` | `Object.hasOwn(obj, 'key')` |
| `String.prototype.at()` | `'hello'.at(-1) // 'o'` |
| Error cause | `throw new Error('failed', { cause: originalError })` |
| Class static initialization blocks | `class Foo { static { /* init */ } }` |

## Supported Built-in Objects

| Object | Notes |
| `Promise` | Full support including `.all()` , `.allSettled()` , `.any()` , `.race()` |
| `Map` / `Set` / `WeakMap` / `WeakSet` | `Map` and `Set` have full support. `WeakMap` / `WeakSet` have most features but `.has` / `.get` / `.delete` on primitives are disallowed |
| `Symbol` | Full support including well-known symbols |
| `Proxy` | Full support in ES12 mode |
| Typed Arrays | `Int8Array` , `Uint8Array` , `Float32Array` , `Float64Array` , etc. |
| `ArrayBuffer` / `DataView` | Full support |
| `JSON` | `JSON.parse()` , `JSON.stringify()` |
| `RegExp` | Named capture groups, lookbehind assertions, dotAll flag, Unicode escapes |

## Caveats / Not Fully Supported

The following features have limitations or are explicitly disallowed:

| Feature | Status | Notes |
| `async` methods in classes | Disallowed | Use async arrow functions in class methods instead |
| `async` generators / `for-await-of` | Disallowed |  |
| `WeakRef` / `FinalizationRegistry` | Disallowed |  |
| `SharedArrayBuffer` / `Atomics` | Disallowed |  |
| `new Function()` | Disallowed |  |
| `Reflect` | Disallowed | All Reflect methods are disallowed |
| Generators (advanced) | Disallowed | `%GeneratorPrototype%` methods, `yield` operator precedence, and shorthand generator constructors are disallowed. Basic `function*` and `yield` work. |
| Proper tail calls | Disallowed |  |
| Subclassable builtins | Disallowed | `Array` , `RegExp` , `Function` , `Promise` , `Error` , `Map` , `Set` cannot be subclassed |
| Private instance class fields/methods | Not Supported | Private static fields/methods ARE supported |
| `RegExp` match indices ( `d` flag) | Not Supported |  |
| Ergonomic brand checks for private fields | Not Supported |  |
| Temporal dead zone for `let` / `const` | Not Supported |  |

## Module System

### ES Modules (module files)

Module files in `src/server/` use ES module syntax:

```
import { helper } from './utils'
export function myFunction() { ... }
```

### CommonJS (server scripts)

Business rules, scheduled scripts, and other server scripts use `require()`:

```
const { myFunction } = require('./path/to/module')
```

Third-party npm libraries that use CommonJS are supported when bundled through Rollup with the CommonJS plugin (the SDK handles this automatically).

## What Is NOT Supported

The runtime is not a Node.js environment. These APIs are unavailable:

- Node.js built-ins: `fs`, `path`, `process`, `child_process`, `os`, `http`, `https`, `stream`, `buffer` (as a Node.js module), `crypto` (Node.js module)

- Browser APIs: `window`, `document`, `localStorage`, `sessionStorage`, `fetch`, `XMLHttpRequest`, `navigator`

- Node.js globals: `__dirname`, `__filename`, `process.env`

Use ServiceNow Glide APIs (`GlideRecord`, `gs`, `GlideHTTPClient`, etc.) for server-side I/O.

## Migration from ES5

Common patterns updated to modern syntax:

```
// ES5: var and function declarations
var name = record.getValue('name')
function formatName(first, last) {
    return first + ' ' + last
}

// Modern: const/let and arrow functions
const name = record.getValue('name')
const formatName = (first, last) => `${first} ${last}`
```

```
// ES5: Class.create() (still the convention for Script Includes)
var MyClass = Class.create()
MyClass.prototype = {
    initialize: function(config) { this.config = config },
    type: 'MyClass',
}

// Modern: ES6 class (works on the platform, but Class.create is the ServiceNow convention for script includes)
class MyClass {
    constructor(config) { this.config = config }
}
```

```
// ES5: manual null checks
var city = user && user.address && user.address.city

// Modern: optional chaining
const city = user?.address?.city
```

```
// ES5: ternary for defaults
var label = value !== null && value !== undefined ? value : 'default'

// Modern: nullish coalescing
const label = value ?? 'default'
```

```
// ES5: Promise chains
fetchData()
    .then(function(result) { return process(result) })
    .catch(function(err) { gs.error(err.message) })

// Modern: async/await
async function run() {
    try {
        const result = await fetchData()
        return process(result)
    } catch (err) {
        gs.error(err.message)
    }
}
```

Version: 4.14.0

# atf.executeTest / atf.setReusableTestOutputs

Invokes a reusable ATF test (`sys_atf_test_callable` — see the reusable-test overload on
`Test`) as a single step from another test, similar to a subflow.
`atf.setReusableTestOutputs` is the companion call used inside a reusable test's own
`configurationFunction` to populate the outputs `atf.executeTest` reads back. Both are methods on
the `atf` builder passed into every `Test(...)`'s `configurationFunction` — there's no standalone
import for either.

## atf.executeTest

### Signature

```
atf.executeTest(reusableTest, config, inputs)
```

There are two overloads, depending on how the reusable test is referenced.

### Typed overload

Use when the reusable test was declared with `Test(..., { isReusable: true })` in this project (or
imported via `now-sdk dependencies`). Inputs/outputs are type-checked against the referenced
test's declared schema, and excess/misspelled input keys are a compile-time error.

#### Parameters

- 
reusableTest (required): `ReturnType<typeof Test>`
A reusable test reference, i.e. the value returned by a `Test(..., { isReusable: true })` call.

- 
config (required): `object`

- $id (required): `ExplicitKey | string | number` — unique identifier for the step record

- active (optional): `boolean` — whether the step is active. Defaults to `true`.

- description (optional): `string` — description of the step

- notes (optional): `string` — field to store useful notes about the step

- timeout (optional): `Duration` — sets the timeout duration for the step

- warning (optional): `string` — warning message that displays in the step form

- 
inputs (required): matches the referenced test's declared `inputs` schema exactly — every
declared input must be supplied, and no keys beyond the declared schema are allowed. This holds
regardless of each column's `mandatory` setting — see the note on `mandatory` under
Test / Reusable Tests.

Returns: an object typed to the referenced test's declared `outputs` schema, readable by later
steps (e.g. `result.myOutput`).

### Sys_id overload

Use when invoking a reusable test this project doesn't have a `Test(..., { isReusable: true })`
declaration for — e.g. one that only exists on the target instance, or came from another
application scope without a local Fluent declaration. Inputs/outputs are not type-checked
against the referenced test's real schema.

#### Parameters

- 
reusableTest (required): `string`
The sys_id of the reusable test (`sys_atf_test_callable`) to invoke.

- 
config (required): same shape as the typed overload's `config`.

- 
inputs (required): `Record<string, unknown>`
Input values keyed by name. Not validated against the real test's schema — a typo or missing
mandatory input isn't caught until the test runs on the instance.

Returns: `any` — property access on the result isn't type-checked either.

## atf.setReusableTestOutputs

Populates a reusable test's declared output variables from within its own body. Only valid inside
a reusable `Test(..., { isReusable: true })`'s own `configurationFunction` — calling it anywhere
else (a standard test, or a different reusable test's inputs) is a build-time error.

### Signature

```
atf.setReusableTestOutputs(outputs, config, values)
```

### Parameters

- 
outputs (required): the enclosing reusable test's own `outputs` schema handle — pass the
`configurationFunction`'s third parameter through unchanged, e.g.
`(atf, inputs, outputs) => { atf.setReusableTestOutputs(outputs, ..., ...) }`. This isn't itself
readable/writable as a value — it only exists to give `atf.setReusableTestOutputs` the schema to
type-check `values` against.

- 
config (required): same shape as `atf.executeTest`'s `config` (`$id`, `active`,
`description`, `notes`, `timeout`, `warning`).

- 
values (required): one entry per declared output column, e.g. `{ myOutput: 'some value' }`.
Each value may also be a reference into a prior step's output or the test's own `inputs` (e.g.
`inputs.myString`, or a bound step variable's property) — this compiles to a
`{{callable_input[...]}}`/`{{step[...]}}` GEM reference under the hood, same as any other step
input.

Returns: `void`

## See

- https://docs.servicenow.com/csh?topicname=atf-reusable-test-now-ts.html&version=latest

- Test / Reusable Tests

## Examples

### Typed atf.executeTest Example

Declare a reusable test with a typed input/output, then invoke it by reference — inputs and the
returned output are both type-checked against the declared schema.

```
/**
 * @title Typed atf.executeTest Example
 * @description Declare a reusable test and invoke it by reference from another test
 */

import { Test, StringColumn } from '@servicenow/sdk/core'

export const greetUser = Test(
    {
        $id: Now.ID['greet_user'],
        name: 'Greet User',
        isReusable: true,
        inputs: {
            userName: StringColumn({}),
        },
        outputs: {
            greeting: StringColumn({}),
        },
    },
    (atf, inputs, outputs) => {
        atf.server.log({
            $id: Now.ID['log_greeting'],
            log: inputs.userName,
        })

        atf.setReusableTestOutputs(
            outputs,
            { $id: Now.ID['set_outputs'] },
            { greeting: 'Hello!' }
        )
    }
)

Test(
    {
        $id: Now.ID['caller_test'],
        name: 'Caller Test',
    },
    (atf) => {
        const result = atf.executeTest(
            greetUser,
            { $id: Now.ID['greet_user_step'] },
            { userName: 'Jane Doe' }
        )

        atf.server.log({
            $id: Now.ID['log_result'],
            log: result.greeting,
        })
    }
)
```

### Sys_id atf.executeTest Example

Invoke a reusable test that exists on the target instance but has no local `Test(...)` declaration
in this project — reference it by sys_id instead.

```
/**
 * @title Sys_id atf.executeTest Example
 * @description Invoke a reusable test by sys_id when there's no local Fluent declaration for it
 */

import { Test } from '@servicenow/sdk/core'

Test(
    {
        $id: Now.ID['caller_test'],
        name: 'ATF Test',
    },
    (atf) => {
        atf.executeTest(
            '6c0faa0edbe444eb9bba912671591a0c',
            { $id: Now.ID['run_reusable'] },
            {}
        )
    }
)
```

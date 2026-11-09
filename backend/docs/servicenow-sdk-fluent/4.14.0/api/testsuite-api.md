Version: 4.14.0

# TestSuite

Creates an Automated Test Framework test suite (`sys_atf_test_suite`) — a named, orderable collection of `Test(...)` records, optionally nested under a parent suite. This API is authoring only: it produces the suite/membership metadata, but does not trigger or schedule a run. Running a suite (on-demand, scheduled, or via CI/CD) is done through ATF's existing UI, scheduler, and CI/CD integration.

## Signature

```
TestSuite(config)
```

## Parameters

### config

`TestSuite`

Properties:

- 
$id (required): `ExplicitKey | string | number`
Unique identifier for the record

- 
name (required): `string`
Suite name, shown in the ATF Test Suites list and picker

- 
active (optional): `boolean`
Whether the suite is available to run. Defaults to `true`.

- 
description (optional): `string`
Description of what this suite covers

- 
protectionPolicy (optional): `'read' | 'protected'`
Controls edit/view access for other developers after the application is installed.

- read: Others can see the script logic but not change it.

- protected: Others cannot change this record.

- 
tests (optional): `readonly TestSuiteEntry[]`
The tests that belong to this suite, in run order — order comes from each entry's position in this array by default, not a separate authored field. Each entry is either a bare `Test(...)` reference/sys_id, or `{ test, abortOnFailure, order }` to stop the suite early if a specific test fails, or to pin a specific numeric `order` (an escape hatch for preserving custom/gapped order values already set on the instance). Fluent errors at build time if the same test (by resolved sys_id, regardless of which reference form is used) appears more than once in this array.

- 
testFilter (optional): `string`
Encoded query against `sys_atf_test` used to dynamically determine this suite's membership (maps to `sys_atf_test_suite.input_filter`). ATF evaluates this filter and keeps `sys_atf_test_suite_test` membership rows in sync with the matching tests whenever the suite is saved on the instance — this sync happens on the platform, not during a Fluent build. Combining this with an explicit `tests` list is allowed by the platform, but the two mechanisms can conflict: a manually-listed test that doesn't match `testFilter` may be removed the next time the suite is saved on the instance. Fluent emits a build-time hint when both are set.

- 
parent (optional): `TestSuite | string`
Parent suite to nest this suite under (maps to `sys_atf_test_suite.parent`). Accepts a `TestSuite(...)` reference or a raw sys_id. When passed as a `TestSuite(...)` reference, the parent must already be declared/constructed before this suite references it (normal declare-before-use), which structurally rules out a cycle. A raw sys_id string equal to this suite's own `$id` is rejected with a build-time error; a longer cycle built from raw sys_id strings across multiple suites isn't statically detected by Fluent and is instead caught by the platform when the suite is saved on the instance.

### TestSuiteEntry

One entry in a suite's `tests` list.

| Form | Type | Description |
| Bare reference | `ReturnType<typeof Test> | string` | Runs with `abortOnFailure: false` . |
| Object form | `{ test: ReturnType<typeof Test> | string, abortOnFailure?: boolean, order?: number }` | `abortOnFailure` stops the rest of the suite's tests immediately if this one fails. Ignored by ATF's cloud/parallel test runner, which always runs every test in the suite regardless of this setting. `order` pins this entry's numeric run-order value instead of deriving it from array position — use to preserve existing custom/gapped order values (100, 200, 300, ...) when adopting Fluent for a suite that already has them. Entries without `order` still derive it from position; pinned and derived entries can mix freely. Collisions with another entry's final order trigger a build-time hint, since ATF doesn't guarantee run order between ties. |

## See

- https://docs.servicenow.com/csh?topicname=atf-test-suite-now-ts.html&version=latest

## Examples

### Basic Test Suite Example

Group two existing tests into a suite, running the second one first with `abortOnFailure` set.

```
/**
 * @title Basic Test Suite Example
 * @description Group existing tests into an ordered, runnable suite
 */

import { Test, TestSuite } from '@servicenow/sdk/core'

const loginTest = Test({ $id: Now.ID['login_test'], name: 'User can log in' }, (atf) => {
    atf.server.log({ $id: Now.ID['log_login'], log: 'Checking login' })
})

const checkoutTest = Test({ $id: Now.ID['checkout_test'], name: 'User can check out' }, (atf) => {
    atf.server.log({ $id: Now.ID['log_checkout'], log: 'Checking checkout' })
})

export const smokeSuite = TestSuite({
    $id: Now.ID['smoke_suite'],
    name: 'Smoke Suite',
    tests: [{ test: loginTest, abortOnFailure: true }, checkoutTest],
})
```

### Nested Test Suite Example

Nest a suite under a parent suite using the `parent` property.

```
/**
 * @title Nested Test Suite Example
 * @description Nest a suite under a parent suite so both run together
 */

import { Test, TestSuite } from '@servicenow/sdk/core'

const loginTest = Test({ $id: Now.ID['login_test'], name: 'User can log in' }, (atf) => {
    atf.server.log({ $id: Now.ID['log_login'], log: 'Checking login' })
})

export const regressionSuite = TestSuite({
    $id: Now.ID['regression_suite'],
    name: 'Full Regression',
})

export const authSuite = TestSuite({
    $id: Now.ID['auth_suite'],
    name: 'Authentication',
    tests: [loginTest],
    parent: regressionSuite,
})
```

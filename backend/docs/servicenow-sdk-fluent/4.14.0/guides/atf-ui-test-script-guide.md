Version: 4.14.0

# UI Test Script (TestingLibrary) Guide

Author ATF tests for custom UI components using `atf.uiTestScript.runTest()` and the TestingLibrary API. Use this when a UI cannot be tested through the standard `atf.form.*` or `atf.catalog.*` steps — Angular/React widgets embedded in workspaces, custom SPAs or UI-page apps, and `now-*` web components. The test body runs in the client test runner with all API globals injected, so no imports are needed inside the script.

This guide complements the ATF guide (the 11 standard categories) and the `Test` API reference. It covers when to use UI Test Script, the full TestingLibrary API surface, web-component DOM discovery, multi-persona tests, passing data between steps, and a self-review checklist.

## When to Use

- Testing a custom UI component (Angular/React widget, embedded SPA, custom workspace) not reachable via `atf.form.*` / `atf.catalog.*`

- Driving `now-*` web components (custom elements with shadow DOM) — UI Builder macroponents, workspace components, apps wrapping `@servicenow/react-components`

- End-to-end workflows that interact with rendered DOM (click, type, navigate) and assert on-screen outcomes

Do not use it for standard forms, catalog items, or pure server-side logic — use the standard ATF categories for those.

## Coverage Rules

- 
Cover all custom UI. Every custom UI page, workspace component, widget, or SPA using `now-*` web components must have at least one `atf.uiTestScript` test — even purely presentational components. For each component, cover the primary user flow AND each significant conditional state (empty state, error, success/confirmation, controls toggling enabled/disabled based on input). Separate conditional paths into separate test cases.

- 
Reconcile on changes. If this task changed or removed existing UI, bring the existing tests back in sync BEFORE authoring any new ones. Sort the UI changes this task touched into three buckets and act per bucket:

- Added UI → ADD a test covering the new component/page.

- Changed UI — the component still exists but its behavior, structure, or accessible names changed → UPDATE the existing test's `.script.js` in place. Do NOT delete-and-re-add.

- Removed UI — the component or page no longer exists → DELETE its test. Query the obsolete test's `sys_id` (`runQuery` on `sys_atf_test`), then emit `Now.del('sys_atf_test', '<sysId>')` as a top-level statement and `build_install`. Do NOT rely on just deleting the `.now.ts` source file — build-agent apps default to a configuration project, where removing source does NOT prune the already-installed record (the build only warns). `Now.del()` is what actually removes it; also delete the now-dead source file so the test isn't re-authored. A test that queries a name no longer in the DOM is a defect.

The delete-vs-update decision hinges on one question per affected component: does the component or page still exist after this edit? If yes → update the test in place. If no → delete it. Delete a test ONLY when the UI it covers is gone — if the structure or accessible names merely changed, update, do not delete.

Verify before you finish. If (and only if) this task removed any UI, confirm that no surviving test still queries a selector or accessible name that no longer exists: walk your "removed" bucket and check each maps to zero remaining tests before considering the work done. If the task removed nothing, there is nothing to check — do not go hunting.

## Instructions

### Test File Structure

```
import { Test } from '@servicenow/sdk/core'
import '@servicenow/sdk/global'

Test(
    {
        $id: Now.ID['my_test'],
        name: 'Custom UI: <Workflow Name>',
        description: 'What this test verifies',
        active: true,
    },
    (atf) => {
        atf.uiTestScript.runTest({
            $id: Now.ID['testinglibrary_step'],
            script: Now.include('./my_workflow_test.script.js'),
        })
    }
)
```

- `$id` must be globally unique for the test and for each step.

- Steps execute sequentially.

### Writing the test description

Every `Test()` must set a `description` that makes the test self-explanatory to someone who never saw the app. State two things:

- What it validates — name the specific behavior: the UI component, page, or interaction being tested. Be concrete — name the component, the action, and the condition, not "tests the page".

- How it validates it — the mechanism: what the test navigates to, what action it performs, and what assertion proves the behavior. For a conditional state, say which side this case covers.

Write 1–2 sentences, tied to the assertion the test actually makes so the description and steps cannot drift apart.

Examples:

- ✅ "Navigates to the daily-grind home page as a standard user, selects service type 'Food' and quantity 3, submits the request, then asserts the confirmation modal shows with the correct total — the success path of the order submission flow."

- ✅ "Opens the request detail page with an existing record, asserts the status chip shows 'Pending', then clicks Approve and asserts it transitions to 'Approved' — the approval conditional state."

- ❌ "Tests the custom UI component." / "Verifies the page works." — must name the component/page, the user action, and what was asserted.

### Preferred pattern — external `.js` file via `Now.include()`

Keep the script body in a `.js` file next to the `.now.ts` file and reference it with `Now.include('./file.script.js')`. This gives the IDE full JavaScript syntax highlighting and autocompletion instead of treating the body as an opaque string.

```
src/fluent/atf/
  my_workflow_test.now.ts
  my_workflow_test.script.js      ← TestingLibrary script body here
```

```
// my_workflow_test.script.js — plain JS, all globals pre-injected, no imports needed
await sn_atf.navigate('/now/my-app/home')
// ... test steps
```

- Inline template literals are acceptable only for trivial one-liners, or when the script must interpolate a prior step's output (see Passing Data into a script).

- For multi-step tests, use one `.js` file per step: `my_workflow_test.step1.js`, etc.

- Default location — put the `.now.ts` and its `.js` files under `src/fluent/atf/` (create it if absent), not in `ui-pages/` or beside the component source. If the app already has ATF tests elsewhere, follow that convention.

## Critical Rules

- Navigate first, with a relative URL. Start every script with `await sn_atf.navigate('/now/path')`. Prefer relative URLs over `https://instance.service-now.com/...` so the test runs on any instance.

- Choose the query family by timing. `findBy*` for dynamic/async content (it polls), `getBy*` for content already present. `queryBy*` for conditional checks (returns `null` for 0 matches).

- Always `await` async queries. `findBy*`, `getAllBy*`, and `queryBy*` (async in this runtime) return Promises; omitting `await` is a silent bug. `expect(element).*` assertions are synchronous and throw immediately — `await` is harmless but unnecessary.

- Use top-level `await` directly. The script body already runs in an async context. If you wrap logic in `async function`/`async () => {}`, you must await the call — an un-awaited wrapper returns a pending promise and the test completes before it runs (a silent false pass).

- Strict mode: one element per query. Every `getBy*`/`queryBy*`/`findBy*` must resolve to exactly one element or it throws. When multiple match, use `exact: true` with the full accessible name, scope with `within()`, or use `findAllBy*` and index: `(await screen.findAllByRole('button'))[0]`.

- Shadow DOM is pierced automatically. Standard `findByRole`, `getByText`, etc. find elements inside web components — no `>>` or `:shadow` syntax exists or is needed.

- `within()` does not cross a slot boundary. A web component's slotted content (e.g. a modal body projected through `<slot>`) is light-DOM of the host, not a descendant of the shadow element carrying the role (e.g. `dialog`), so `within(dialog).findBy*` misses it. Query slotted controls from `screen` (names are usually unique) or scope to the host's light-DOM container. `screen` queries pierce shadow DOM — a failed scoped query usually means a slot boundary, not a piercing problem.

- `now-*` text inputs commit on `change` (blur), not per keystroke. After `await user.type(input, text)` into a `now-input` (or similar `now-*` field), commit by blurring: `await user.tab()`. Until committed, the typed text shows but the component's bound state stays empty, so any control gated on it (a button disabled until filled) never enables. Do not rely on Enter inside a `now-modal` — the dialog captures Enter as its default action; Tab commits, Enter does not. Other `now-*` controls commit differently — verify per component. After `user.tab()`, the value commits asynchronously — before the next action that depends on it, read the app source to determine: if a downstream element changes state (e.g. a button becomes enabled based on the input value), use `await waitFor(() => expect(btn).toBeEnabled())`; if nothing in the DOM reflects the commit, use `await sn_atf.delay(500)` as a fallback.

- Accessible names can be state-dependent. A control's name may change as the user interacts (a button "Add a tip" becomes "Tip: $2.00 ✓"; toggles, counts). Query by the name valid at that point in the journey, and never re-query a control by a name an earlier action changed. A label that is a conditional/template expression in source changes at runtime — confirm the active value from the rendered DOM.

- Wrap element-state assertions in `waitFor` by default. `expect(el).*` checks state once, but state settles asynchronously (visible after animation, enabled after selection, text after re-render). Put `toBeVisible`/`toBeEnabled`/`toBeDisabled`/`toHaveTextContent`/`toHaveValue`/`toBeChecked` inside `await waitFor(() => expect(el)…)`. It is free when already settled and correct when not. A redundant `toBeVisible()` right after a `findBy*` can simply be dropped — the `findBy*` already proved the element appeared. Reserve bare `expect` for synchronous value checks (array `.length`, a `.textContent` compare).

- Never nest `findBy*` inside `waitFor()`. `findBy*` already polls internally; wrapping it creates conflicting timeouts and confusing errors. Use `findBy*` directly with its own `timeout`. Use `waitFor()` only to poll something with no built-in polling (a `queryBy*` result, a state predicate).

- Query options go inside the opts object. `findBy*`/`getBy*` accept exactly `(query, opts?)` — the `timeout` belongs in `opts`: `findByRole('button', { name: 'Submit', timeout: 15000 })`, not as a third argument (silently ignored).

- Assert the real outcome, not the UI's success signal. A success toast can lie (an app may show it without checking the server response). For a write workflow, verify the persisted record with an `atf.server.recordQuery`/`recordValidation` step, not just the UI message.

- Run every UI test as a dedicated test user. The test's first step is `atf.server.createUser({ roles: [appRole] })` with the app's existing `Role` record or its sys_id (a role name leaves the user with no role); it impersonates the new user, so the `runTest()` steps that follow run as them. If no app role grants access to its tables (no roles, or a role with no ACLs), the app is admin-only: create the user with the `admin` role's sys_id, don't add roles or ACLs, and tell the user. Never impersonate an existing user unless the user explicitly asks you to.

- A persona needs the access to perform its actions. `atf.server.createUser({ roles: [] })` makes a user with no roles, so ACL-gated operations are denied — often silently, while the UI still flashes success. Grant the app's role(s) the journey requires. Don't use `enforceSecurity:false` on a server step to get around ACLs; report the access gap instead. It also wouldn't help: the UI step runs as the real impersonated user and is still blocked.

- Assert display values, not stored values. Lists and forms render the display label of choice/reference fields (a stored `pending` displays as `Pending`). Assert on the display label.

- No `sleep()`. It is not a global and throws `ReferenceError`. Use `await waitFor(...)` or a `findBy*` with a `timeout`.

- Max script length is 8000 characters. Split long workflows across multiple steps or `Test()` blocks.

## Discovering the Real DOM for Web-Component UIs

Many ServiceNow UIs render web components (custom elements with shadow DOM; ServiceNow's are typically `now-*`-namespaced) rather than plain HTML. A common case: React wrappers from `@servicenow/react-components`, where a source `<Button>Save</Button>` does not render as an HTML `<button>` — it becomes a custom element whose tag, role, and accessible name the app source does not reveal (they may come from an attribute or a slot, not the JSX child). You cannot assume the mapping from an authoring component to its rendered tag/role/name — it varies by library, component, and version.

That mapping lives in the component-library source (`@servicenow/react-components` and the `now-*` packages), which you can read directly under `node_modules/@servicenow/*` — the app JSX cannot tell you. Auto-piercing lets queries reach inside these components, but only once you know the real roles and names.

When the UI under test is built from web components, learn each component's real DOM rather than guessing. Discover in this order:

- `inspect_component_dom` with `appScope` — primary path. Pass `appScope` (the active app scope, e.g. `x_snc_my_app`) with `deminify: true` and `raw: true`. `raw: true` includes the app's own source files (e.g. `app.tsx`) from the bundle's `sourcesContent` — essential for recovering app-specific prop values that drive accessible names (e.g. `headerLabel` on a modal). This is the primary path in metadata-only environments (ServiceNow Studio), where the app's source files are NOT on disk. Sweep the scope; an app usually has more than one map — raise `limit` if needed. If the scope has no maps or `sourcesContent` is empty, fall back to `componentName` (no `appScope`, default `raw: false`) to inspect individual platform components.

- `ui_diagnostics` with `collectDOM: true` — confirm the live rendered DOM. Confirms real tags, roles, and accessible names as the browser sees them. Conditionally-rendered UI (modals, menus, popovers) is not in the initial snapshot — capture it after the action that opens it. A bare `ui_diagnostics` without `collectDOM: true`, or a snapshot taken before the app mounts, returns only the page shell.

- Local source via `fs_read_file` — when the project filesystem is mounted. A good source when the app and component-library source are on disk (e.g. Glider IDE). Typically absent in metadata-only environments (Studio) — when `fs_read_file` returns nothing, identify which platform components the app uses from its entry source file in `originalSources` and run a follow-up `inspect_component_dom` for each using `componentName`. Use the returned source to answer: does a text prop render as an accessible `<label>`? (`findByLabelText`); does an array prop render each item as an interactive element? (`findByRole`). Enumerate the whole journey, not one component at a time — the components a test touches span child components (a page renders modals, panels, menus). Follow the component tree from the entry page into its children; a missed component is the step a test stalls on.

- `atf-cloud-runner` MCP (Playwright) — final fallback. When the steps above can't resolve the DOM (bundle source map lacks `sourcesContent`, and `ui_diagnostics` snapshot is empty or incomplete because the app renders asynchronously or the DOM only appears after an interaction), drive the page in a real browser and read the fully-rendered DOM — including after the action that reveals conditionally-shown UI. This MCP is only connected when the ATF cloud-runner session is established this turn — use it only when its tools are actually present.

Shadow DOM does not block test authoring. `now-*` components always render with shadow DOM — this is expected and normal, not a complexity signal. Testing Library's `findByRole`, `findByLabelText`, `findByText`, and `findByPlaceholderText` pierce shadow DOM automatically. Never skip writing `atf.uiTestScript` tests because of shadow DOM — if `inspect_component_dom` shows `now-input`, `now-button`, or other platform web components, proceed with authoring tests using the selectors you discovered.

Base `getByRole` / `getByText` / `getByLabelText` on the discovered roles and accessible names — never on the authoring source. Model interactions from real behavior: read what a control actually does before scripting it (whether a click also closes a dialog, whether a separate confirm/Apply step exists and is enabled). Don't synthesize a generic "select then confirm" sequence — an invented or disabled step desyncs the test from the app's real state. Escalate through steps 1 → 4 only as far as needed — steps 1–2 resolve most apps.

## TestingLibrary API

All of the following are available as globals inside `script`. No imports needed.

### Screen queries

| Prefix | Async | Behavior |
| `getBy*` | sync (await anyway) | Throws if not found or >1 match — for immediately-present, unique elements |
| `findBy*` | async | Polls up to timeout, throws if not found or >1 match — for dynamic content |
| `queryBy*` | async | `null` if 0 matches, throws if >1 — for conditional checks |
| `getAllBy*` | async | Returns `HTMLElement[]` , throws if none |
| `findAllBy*` | async | Returns `HTMLElement[]` , waits for at least one |
| `queryAllBy*` | sync (await anyway) | Returns `HTMLElement[]` , never throws (may be empty) |

Query suffixes (each available across all six prefixes): `ByRole`, `ByText`, `ByLabelText`, `ByPlaceholderText`, `ByTestId`, `ByDisplayValue`, `BySelector`, `ByAltText`, `ByTitle`.

```
await screen.findByRole('button', { name: 'Submit', exact: true, timeout: 15000 })
await screen.getByLabelText('Description')
await screen.findAllByRole('row')
const maybe = await screen.queryByRole('alert') // null if absent
```

- `ByRoleOptions`: `{ name?, description?, exact?, hidden?, level?, checked?, expanded?, pressed?, current?, selected?, busy?, value?, queryFallbacks?, suggest? }` — `name`/`description` accept `string | RegExp`.

- `ByTextOptions`: `{ exact?, selector?, ignore? }` — `selector` narrows element types; `ignore` excludes a CSS selector (default `'script, style'`).

- `ByLabelTextOptions`: `{ exact?, selector? }`.

- `getByTag` and `getByName` do not exist — use `getBySelector('tagname')` / `getBySelector('[name="value"]')`.

- The `normalizer` option is accepted for API compatibility but has no effect — normalize the query string yourself.

### Interactions — the `user` global

Query results are raw `HTMLElement` objects; element methods like `.fill()`, `.isVisible()`, `.check()` are not available on them. Use `user` for all interactions (each method takes the element as the first argument):

```
await user.click(el)
await user.dblClick(el)
await user.type(el, text)            // realistic key-by-key input (preferred for React/Angular)
await user.clear(el)
await user.selectOptions(el, values) // string | string[]
await user.deselectOptions(el, values)
await user.upload(el, files)         // File | File[]
await user.hover(el) / await user.unhover(el)
await user.keyboard('[Tab]')         // page-level; e.g. '[Enter]', '{Shift>}A{/Shift}'
await user.tab()                     // Tab to next focusable; user.tab({ shift: true }) for back
await user.copy() / user.cut() / user.paste()
```

`user` has no `.fill()`, `.impersonate()`, `.navigate()`, or `.evaluate()` — those last three are on `sn_atf`. For focus/blur/scroll, use native DOM on the raw element (`el.focus()`, `el.blur()`, `el.scrollIntoView()`).

### `sn_atf` — ServiceNow APIs

```
// Navigation (test iframe)
await sn_atf.navigate('/now/path')   // prefer relative URLs; 30s timeout
await sn_atf.reload(); await sn_atf.goBack(); await sn_atf.goForward()

// Run a function in the test iframe's JS realm — access g_form, g_user, $j, GlideAjax, document
const v = await sn_atf.evaluate(() => g_form.getValue('number'))

// Impersonation — accepts sys_id OR user_name; reloads iframe; auto-reverts at step end
await sn_atf.impersonate('atf.approver') // user_name set via fieldValues on the test's createUser step, never an existing user

// Waits & delays
await sn_atf.waitForElementToBeRemoved(el, { timeout })
await sn_atf.delay(ms)                // last resort; prefer waitFor/findBy*

// Shadow-piercing DOM helpers
sn_atf.querySelector(root, css); sn_atf.querySelectorAll(root, css); sn_atf.getActiveElement(doc?)

// Attachments / uploads
await sn_atf.getAttachmentFile(sysId)            // → File
await sn_atf.upload(elOrSysId, files?)
await sn_atf.uploadInWS(source, table?, sysId?); await sn_atf.uploadInSP(source, table?, sysId?)
await sn_atf.uploadInSCVariable(source, varName); await sn_atf.uploadInSPVariable(source, varName, opts?)
```

`DTL` is not available in scripts — its former `DTL.utils.*` helpers are on `sn_atf` (e.g. `sn_atf.delay`, `sn_atf.querySelector`).

### Assertions — `expect`

Element assertions (synchronous; throw on failure): `toBeVisible`, `toBeHidden`, `toBeEnabled`, `toBeDisabled`, `toBeChecked`, `toBePartiallyChecked`, `toHaveFocus`, `toBeInTheDocument`, `toBeEmptyDOMElement`, `toHaveTextContent`, `toHaveValue`, `toHaveAttribute`, `toHaveClass`, `toHaveStyle`, `toHaveAccessibleName`, `toHaveAccessibleDescription`, `toHaveRole`, `toContainElement`, `toHaveFormValues`, `toHaveDisplayValue`, `toBeRequired`, `toBeValid`, `toBeInvalid`, `toHaveErrorMessage`. Invert any with `.not`.

Plain-value assertions (for `location.href`, `document.title`, `el.textContent`, strings/numbers): `toBe`, `toEqual`, `toStrictEqual`, `toBeTruthy`, `toBeFalsy`, `toBeNull`, `toBeUndefined`, `toBeDefined`, `toBeNaN`, `toContain`, `toMatch`, `toHaveLength`, `toBeGreaterThan(OrEqual)`, `toBeLessThan(OrEqual)`.

### Utilities

```
await waitFor(() => expect(el).toBeVisible(), { timeout, interval })  // retries until callback stops throwing
const inner = within(panel)                                          // scoped Screen — all query variants work
screen.debug(el?, maxLength?)                                        // log container HTML (incl. shadow DOM)
const recordId = steps('step-sys-id').record_id                     // prior step output (dotwalks references)
const firstName = params('first_name')                              // parameterized-test value
```

Synchronous element predicates (for `.find()`/`.filter()` callbacks): `isVisible`, `isHidden`, `isEnabled`, `isDisabled`, `isChecked`, `isPartiallyChecked`, `isInDocument`, `isEmpty`, `hasFocus`, `hasClass`, `hasAttribute`, `hasText`, `hasValue`, `hasRole`, `hasStyle`, `hasFormValues`, `hasAccessibleName`, `hasAccessibleDescription`, `containsElement`, `hasDisplayValue`, `isRequired`, `isValid`, `isInvalid`, `hasErrorMessage`.

## Multi-Persona Tests (Impersonation)

When a workflow spans multiple users (submit as requester, approve as manager):

Each persona is a user the test creates with `atf.server.createUser`, never an existing user unless the user explicitly asks you to.

- Within a single step — `await sn_atf.impersonate('username')` inside the script; the session auto-reverts at step end. Use when no server-side assertions are needed between persona changes.

- Across steps — an `atf.server.impersonate()` step between `atf.uiTestScript.runTest()` steps. Use when you need intermediate server-side validation, or completely separate script steps per persona.

```
import { Role, Test } from '@servicenow/sdk/core'
import '@servicenow/sdk/global'

// The app's roles, usually imported from where the app defines them
const requesterRole = Role({ name: 'x_myapp.requester' })
const approverRole = Role({ name: 'x_myapp.approver' })

Test(
    { $id: Now.ID['multi_persona_test'], name: 'Custom UI: Submit and Approve', active: true },
    (atf) => {
        const approver = atf.server.createUser({
            $id: Now.ID['step_create_approver'],
            roles: [approverRole],
            impersonate: false,
        })
        atf.server.createUser({ $id: Now.ID['step_create_requester'], roles: [requesterRole] })
        atf.uiTestScript.runTest({
            $id: Now.ID['step_as_requester'],
            script: Now.include('./multi_persona_test.requester.js'),
        })
        atf.server.impersonate({
            $id: Now.ID['step_switch_to_approver'],
            user: approver.user, // reference field: a sys_user sys_id, NOT a username
        })
        atf.uiTestScript.runTest({
            $id: Now.ID['step_as_approver'],
            script: Now.include('./multi_persona_test.approver.js'),
        })
    }
)
```

- Each `atf.uiTestScript.runTest()` step runs as the user currently set by the ATF context — switching users requires an `atf.server.impersonate()` step in between.

- Split the script at every persona boundary — one step per persona.

- `atf.server.impersonate()`'s `user` is a reference field — it takes a `sys_user` sys_id (or a `Record<'sys_user'>`), not a username/display name. (The within-script `sn_atf.impersonate('username')` does take a username — different API.)

- Place `atf.server.recordQuery`/`recordValidation` steps between UI steps to verify database state before continuing.

## Passing Data into a script

Use a prior step's output inside a later `script` with the `steps(stepSysId)` global — it supports dotwalking like server-side GlideElement (`steps(id).record_id`, `steps(id).assigned_to.department.name`) and returns an empty string for unknown steps/paths. Use `==` (not `===`) for string comparisons.

To embed the sys_id of a Fluent-authored step into the script, interpolate the step return value's property access in a template literal. The build plugin converts the `PropertyAccessShape` to a GEM expression (`{{step['uuid'].record_id}}`) that the ATF framework substitutes before the script runs.

```
import { Test } from '@servicenow/sdk/core'
import '@servicenow/sdk/global'

Test(
    { $id: Now.ID['view_request_test'], name: 'Custom UI: View Created Request', active: true },
    (atf) => {
        const insertStep = atf.server.recordInsert({
            $id: Now.ID['step_insert_request'],
            table: 'sn_travel_request',
            fieldValues: { short_description: 'ATF test request' },
        })

        // Now.include() cannot be used when the script needs GEM interpolation — use an inline
        // template literal so the ${...} is preserved.
        atf.uiTestScript.runTest({
            $id: Now.ID['step_view_request'],
            script: `
                await sn_atf.navigate(location.origin + '/now/my-app/record/' + '${insertStep.record_id}')
                const heading = await screen.findByRole('heading', { name: 'ATF test request' })
                await waitFor(() => expect(heading).toBeVisible())
            `,
        })
    }
)
```

Anti-patterns that do not work:

- Module-level constants interpolated into step fields. Declaring `const ROUTE = '/now/...'` and interpolating `${ROUTE}` causes a build error (`Failed to cast IdentifierShape to PropertyAccessShape`) and is discarded by bi-directional sync. Write test data as inline literals. The only supported TypeScript-level interpolation is a property access on a step return value.

- External values (e.g. a database lookup result) interpolated into the file. Such values are not TypeScript variables. Write the resolved value as a literal string — for a reference field, the resolved sys_id literal.

Alternative — find by a predictable unique value instead of a sys_id: navigate to a list and `findByText('ATF Test - Do Not Delete')`, using a fixed recognizable string the script controls.

## What Is NOT Available

| Do NOT use | Use instead |
| `page.*` / `locator.*` (browser-automation APIs) | `screen.*` queries and `user.*` interactions |
| `element.fill(text)` / `user.fill(...)` | `await user.type(element, text)` |
| `element.isVisible()` / `.value()` / `.check()` | `expect(element).*` , or native `element.value` / `element.textContent` |
| `keyboard.press(...)` / standalone `keyboard` | `await user.keyboard('[Tab]')` / `await user.tab()` |
| `sleep(ms)` | `await waitFor(...)` or `findBy*` with `timeout` |
| `createUser()` as a global | `user` is pre-injected; create users via `atf.server.createUser` step |
| `waitForElementToBeRemoved(el)` (top-level) | `await sn_atf.waitForElementToBeRemoved(el)` |
| `screen.navigate()` / `screen.evaluate()` | `sn_atf.navigate()` / `sn_atf.evaluate()` |
| `user.impersonate()` / `user.navigate()` | `sn_atf.impersonate()` / `sn_atf.navigate()` |
| `DTL.*` / `DTL.utils.*` | `sn_atf.delay()` , `sn_atf.querySelector()` , … |
| `expect.assertions()` / `assert.*` / `chai.*` | `expect(element).*` matchers |
| `require(...)` / `import ...` inside the script | all globals are pre-injected |
| `process.*` / `fs.*` / Node built-ins | not available (sandboxed `Function` context) |
| `describe` / `beforeEach` / `afterEach` | no-ops; `test()` / `it()` bodies run sequentially |

Accessing any unlisted name throws a `ReferenceError` that lists the available APIs.

## When an Authored Test Fails

Do NOT attempt to fix the test without first calling `atf-triage` with the `result_sys_id`. Only after receiving the triage report should you make any changes — based on what the report found. Do NOT give up or report the failure as unfixable without first attempting a fix based on the triage findings.

## Self-Review Checklist

Scan the generated `script` before building and verify:

-  Files are under `src/fluent/atf/` (unless the app uses a different ATF folder).

-  `script` uses `Now.include('./file.script.js')` (inline only for trivial scripts or GEM interpolation).

-  No un-awaited async wrapper; top-level `await` used directly.

-  No strict-mode violations — multi-match queries use `exact: true`, `within()`, or `findAllBy*` + indexing.

-  Regex `name` patterns are safe — prefer `{ name: 'X', exact: true }` over `/X$/i` (which also matches "+ X").

-  Repeating-item details (cards/rows) are scoped with `within()` on the containing item.

-  No `findBy*` nested inside `waitFor()`; no third argument to query methods.

-  Element-state assertions are wrapped in `waitFor` (or dropped as redundant right after a `findBy*`).

-  `now-*` inputs committed after typing (`await user.tab()`).

-  Clear inputs before retyping into a reopened modal — if the same modal is opened a second time, the input may retain its previous value; `user.type()` appends to existing text. When the input may already have a value, `await user.clear(element)` before `user.type()`.

-  No `within()` across a slot boundary.

-  No module-level constants or external values interpolated into step fields; step outputs use property-access syntax.

-  `atf.server.*` reference fields use sys_ids; the within-script `sn_atf.impersonate()` uses a username.

-  Real outcome asserted (server record), not just a UI success message.

-  Each persona has the roles/ACLs its actions require.

-  Assertions target display values, not stored values.

## Troubleshooting: server-side errors during data submission

When the failure occurs during a submit/save — a network/response error or unexpected HTTP status, not at a selector or navigation step — the interaction succeeded but the server rejected the write. Likely causes: field-level ACLs denying writes for the impersonated user (even with the expected role), a server-side script throwing during save, or other permission gaps.

Investigate: identify which save failed and which user was active; check whether a record was created and which fields were saved vs. left empty (empty fields that were submitted indicate a field-level ACL block); review the table's write ACLs and the roles they require against the impersonated user's roles. Resolve by granting the needed role in `atf.server.createUser`, adding field entitlements, or fixing the app's ACL/script — not by loosening the test. If the cause cannot be determined, surface the findings rather than making blind changes.

## Examples

### Custom UI Test Script

Test a custom UI component with the TestingLibrary API. Keep the script body in a sibling `.js` file via `Now.include()` so the IDE provides JavaScript syntax highlighting.

```
/**
 * @title Custom UI Test Script Example
 * @description Verify a custom UI component workflow using the TestingLibrary API
 */

import { Test } from '@servicenow/sdk/core'

export const submitButtonWorkflow = Test(
    {
        $id: Now.ID['submit_button_test'],
        name: 'Custom UI: Submit Button Workflow',
        description: 'Verifies the submit button creates a record and shows confirmation',
        active: true,
    },
    (atf) => {
        atf.uiTestScript.runTest({
            $id: Now.ID['testinglibrary_step'],
            script: Now.include('./submit_button_test.script.js'),
        })
    }
)
```

The referenced `submit_button_test.script.js` is plain JavaScript — all globals are pre-injected, no imports needed:

```
await sn_atf.navigate('/now/my-app/home')

const descInput = await screen.findByLabelText('Description')
await user.type(descInput, 'ATF test submission')
await user.tab() // commit a now-* input value by blurring (it commits on change, not per keystroke)

const submitBtn = await screen.findByRole('button', { name: 'Submit', exact: true })
await user.click(submitBtn)

const confirmation = await screen.findByText('Submitted successfully', { timeout: 10000 })
await waitFor(() => expect(confirmation).toBeVisible())
```

## Avoidance

- Do not infer selectors from the authoring source for web-component UIs — discover the real rendered roles and names first.

- Do not hardcode `sys_id` values — resolve them and write the resolved literal.

- Do not treat a UI success message as proof — verify the persisted record.

- Do not create generic/template tests — each test should reflect a real user workflow.

- Do not split one workflow across unrelated `Test()` blocks, or combine unrelated workflows into one.

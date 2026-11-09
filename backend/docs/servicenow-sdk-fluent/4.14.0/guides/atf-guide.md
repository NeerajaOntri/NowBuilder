Version: 4.14.0

# Implementing Tests Guide

Create ServiceNow Automated Test Framework (ATF) test cases using Fluent APIs across 13 ATF categories: server, form, REST, catalog, email, app navigator, reporting, responsive dashboard, uiTestScript (custom UI), list and related list operations, and Service Portal variants (form_SP, catalog_SP). This guide covers test strategy, category selection, step configuration, and the full API surface for each ATF namespace.

## When to Use

- Generating automated test cases for a ServiceNow application

- Testing forms, APIs, catalog items, dashboards, or server-side logic

- Building end-to-end workflow tests combining multiple ATF categories

- Validating email notifications, report visibility, or navigation menus

## Instructions

### Strategic Approach

- Analyze the application context -- examine custom tables, forms, APIs, catalog items, related lists, dashboards, and business logic.

- Develop a test strategy -- propose up to 3 representative test cases reflecting critical workflows before expanding coverage.

- Select ATF categories -- map each test interaction to the appropriate `atf.*` namespace (see table below).

- Implement test steps using the category-specific Fluent ATF APIs.

Cover every piece of custom logic. If the app has any custom logic, it gets a test -- however simple the app looks. Custom logic includes business rules, client scripts, UI policies, data policies, ACLs/roles, field-level conditions (mandatory / visible / read-only), default / calculated / derived values, validation, and choice / state transitions or side-effects (notifications, related-record updates, flows). Where a rule has both sides, cover a positive AND a negative case. Only when the app genuinely has no custom logic at all -- a plain table with default platform behavior -- does a single basic CRUD test suffice.

Editing an existing app -- reconcile, don't just add. If the task changed or removed existing logic (not only added new logic), bring the existing ATF tests back in sync BEFORE authoring any new ones. Sort the logic this task touched into three buckets and act per bucket:

- Added logic -- ADD a test (positive AND negative where the rule has both sides).

- Changed logic -- the rule / UI policy / notification still exists but its behavior changed -- UPDATE its existing test in place. Do NOT delete-and-re-add; editing the existing test IS the update.

- Removed logic -- the rule / UI policy / notification no longer exists after this edit -- DELETE its test. Query the obsolete test's `sys_id` (`runQuery` on `sys_atf_test`), then emit `Now.del('sys_atf_test', '<sysId>')` as a top-level statement and re-install. Do NOT rely on just deleting the `.now.ts` source file -- in a configuration project (build-agent apps default to this) removing source does NOT prune the already-installed record; the build only warns "delete them manually". `Now.del()` is what removes it; also delete the dead source file so the test isn't re-authored. Re-query after install to confirm the record (and any lingering `sys_atf_test_step` children) is gone.

The delete-vs-update decision hinges on one question per affected rule: does the rule still exist after my edit? If yes -- update the test in place. If no -- delete it. Delete a test ONLY when its underlying rule is gone; if the behavior merely changed, update, do not delete. Anchor "removed" to what you actually did (you deleted the rule's source / the rule's record is gone after this install), not a guess.

Deleting the test for removed logic is as mandatory as adding a test for new logic -- a test that still asserts deleted or changed behavior is a defect, and adding new tests does not excuse leaving stale ones behind.

Verify before you finish. If (and only if) this task removed any logic, confirm that no surviving test still asserts a removed rule: walk your "removed" bucket and check each maps to zero remaining tests. If the task removed nothing, there is nothing to check -- do not go hunting.

Cover a rule's full trigger set. When a rule fires on more than one database operation (e.g. both insert and update), exercise each path, not just one: an insert case AND a separate update case. Use `atf.server.recordInsert` for the insert path and `atf.server.recordUpdate` for the update path, each followed by its own `atf.server.recordValidation`.

Look up the table before using it in a step. Before writing any step that interacts with a table (such as `setFieldValue`, `recordInsert`, `recordUpdate`, etc.), look up that table's field definitions on the instance: which fields are mandatory, and each field's type. Include fields inherited from a parent table (e.g. `incident` inherits most of its fields from `task`). When a server-side step creates a record (e.g. `recordInsert`), give every mandatory field a valid value. When a step needs a reference to another record (a user, group, role, or any other record), use an earlier step's output if the test created that record, otherwise look its `sys_id` up on the instance -- never hard-code one.

### Category Selection

| Interaction type | ATF namespace | Use for |
| UI navigation | `atf.applicationNavigator` | Verify menus/modules visible, navigate to modules |
| Custom UI (UI pages, SPAs, workspace/UIB components, `now-*` web components) | `atf.uiTestScript` | Not reachable via `atf.form` / `atf.catalog` -- see the atf-ui-test-script-guide doc before ruling this out |
| Lists and related lists | `atf.list` | Filter/validate related lists, check record presence, click list UI actions |
| Form interactions | `atf.form` | Open/submit forms, set/validate fields, click UI actions |
| Forms in Service Portal | `atf.form_SP` | Same as form but in Service Portal context |
| REST API validation | `atf.rest` | Send HTTP requests, assert status codes/headers/payload |
| Server-side logic | `atf.server` | Impersonation, CRUD operations, record validation, logging |
| Service Catalog | `atf.catalog` | Open/order catalog items, set/validate variables |
| Catalog in Service Portal | `atf.catalog_SP` | Same as catalog but in portal -- plus order guides and multi-row variable sets |
| Email testing | `atf.email` | Validate outbound emails, generate inbound emails |
| Reporting | `atf.reporting` | Assert report visibility |
| Dashboards | `atf.responsiveDashboard` | Assert dashboard visibility and sharing |

### Test File Structure

Every ATF test file must:

```
import { Test } from "@servicenow/sdk/core";
import "@servicenow/sdk/global";

Test({
  $id: Now.ID['test_id'],
  name: 'test name',
  description: 'meaningful description -- see "Writing the Test Description"',
  failOnServerError: true
}, (atf) => {
  // Steps execute sequentially
  atf.<category>.<method>({
    $id: Now.ID['step_id'],
    ...params
  });
});
```

- `$id` must be globally unique for both the test and each step.

- Steps execute sequentially -- capture earlier step outputs in variables to pass to later steps.

### Writing the Test Description

Every `Test()` should set a `description` that makes the test self-explanatory to someone who never saw the app. State two things:

- What it validates -- name the specific behavior: the business rule, data policy, UI policy, ACL, field condition (mandatory/visible/read-only), calculated/default value, or state transition. Be concrete -- name the field, rule, table, and triggering condition, not "validates the form".

- How it validates it -- the mechanism: the data the test sets up, the action it performs, and the assertion that proves the behavior. For a both-sides condition, say which side this case covers (condition holds vs. does not hold).

Write 1-2 sentences, tied to the assertion the test actually makes so the description and steps cannot drift apart.

Examples:

- ✅ "Inserts an incident with state=7 (Closed) and an assignment group, then asserts it is excluded from the daily-digest query -- the negative side of the digest's `state NOT IN 6,7` filter."

- ✅ "Sets Priority=1 on the Change form and asserts Justification becomes mandatory (condition-holds side of the UI policy); the paired case with Priority=3 asserts it stays optional."

- ❌ "Tests the incident form." / "Validates the business rule." (neither what specifically nor how)

### Category Selection Guidance

- 
Prefer UI-based categories (`atf.form`, `atf.catalog`) over `atf.server` for interactions that users normally perform through the UI.

- 
Use `atf.server` only when backend assertions, data setup, or server-only operations are needed.

- 
Testing a Script Include (or other server-side-only logic): use `atf.server.runServerSideScript`. There is no UI for a Script Include, so instantiate the class and invoke its methods inside the script, then assert the result server-side (e.g., throw on mismatch, or run Jasmine specs). Do NOT try to exercise a Script Include through `atf.form`/`atf.catalog`.

- 
When the user mentions Service Portal, use the `_SP` variants (`atf.form_SP`, `atf.catalog_SP`).

- 
Combine categories within a single test for end-to-end workflows.

- 
Related lists are ubiquitous by default (Attachments, Approvals, Journal Entries, and any list arising purely from a reference field) -- only add an `atf.list` test when a client script, UI policy, or a relationship this app defines actually drives that related list's visibility, membership, or filtering, not default platform behavior.

- 
Determine this by checking, not assuming. This is how you resolve the point above -- run the three searches below before concluding a related list has no custom logic behind it, rather than skipping straight to "no test needed." Do not treat "the user didn't mention this" as evidence that nothing exists -- pre-existing logic (written before this conversation started) is invisible unless you look. Before ruling `atf.list` out for a target table, search the three places below. Filter for relevance, don't just dump every record on the table -- these tables carry many OOB/platform rows unrelated to related lists at all; a match only counts if its content or purpose actually touches list/related-list behavior, not merely that it exists on the table. Test whatever you find touching the related list -- do not filter by who authored it or when, or by what scope it lives in; a match is in scope whether it's OOB or custom, and whether it lives in Global or the app currently being developed. A client script, UI policy, or relationship driving this behavior is just as often in Global scope as in this app's own scope -- do not add a scope restriction to these searches.

- Client script -- `sys_script_client` on the table, filtered to content, e.g. `scriptLIKEhideRelatedList^ORscriptLIKEshowRelatedList^ORscriptLIKEaddRelatedList`.

- UI policy -- query `sys_ui_policy` with two separate pure-`^AND` queries (never combine them with `^OR` -- see note below): `table=<table>^run_scripts=true^script_trueLIKErelatedlist` and `table=<table>^run_scripts=true^script_falseLIKErelatedlist`. `relatedlist` (case-insensitive) is deliberately the broad substring, not the specific method name -- it catches `hideRelatedList`/`showRelatedList`/`addRelatedList` and any other RelatedList-touching call in one term, confirmed against real live examples on other tables (e.g. "Hide the Time series exclusions related list...", "Show/Hide activities related list..."), so `incident` returning no matches means this table genuinely has none, not that the search missed something. `run_scripts=true` matters because `script_true`/`script_false` are ignored entirely when it's false. Do not merge the two queries with `^OR`: ServiceNow's encoded-query `^OR` does not distribute an earlier `^AND` term across the whole chain, so `run_scripts=true^script_trueLIKEx^ORscript_falseLIKEx` silently lets `run_scripts=false` records back in through the second branch (confirmed by testing this exact pattern against a real instance -- a pure `^AND`-only chain scopes correctly, but the moment `^OR` enters the string, only the term immediately before it stays scoped). UI Policy Actions themselves can't target a related list at all (no field reference exists for one) -- `script_true`/`script_false` running raw GlideForm API calls (the same `g_form.hideRelatedList()`/`showRelatedList()` a client script would use) is the only way a UI policy record could actually touch a related list, which is why this is a narrower check than the other two.

- Relationship this app defines -- `sys_relationship` where `basic_apply_to` (or `apply_to`) is this table, for a relationship record (surfaces as a `REL:<sys_id>` related list per the Related list value format note below), as opposed to a related list arising from a plain reference field or an OOB platform relationship.

Those tables are examples of where to look, not the limit of what counts -- any logic that conditionally affects a related list's visibility, membership, or filtering is in scope, however and wherever it's implemented.

- 
Before ruling out `atf.list` for a table, verify you actually ran the searches above. Concluding "nothing affects this table's related lists" without having queried `sys_script_client`, `sys_ui_policy`, and `sys_relationship` for that table is not a determination -- it's an assumption, and is exactly the failure mode this section exists to prevent. If you have not run them, STOP and run them now, even if you're already authoring a different category of test for this app.

- 
Map found logic to the best-fit `atf.list` method, not a default. Once a match is found, re-read the found script's actual behavior against every method in the API Reference: atf.list table below (`relatedListVisibility`, `applyFilterToList`, `recordPresentInList`, `openRecordInList`, `listUIActionVisibility`, `clickListUIAction`) and pick the one(s) that match what the logic actually does -- a hide/show branch maps to `relatedListVisibility`; logic that filters/narrows a list's records maps to `applyFilterToList`; logic gating a list UI action maps to `listUIActionVisibility`/`clickListUIAction`. Cover every distinct branch/condition the found logic has (e.g. both the true and false side of an `if`), even though the user's request didn't mention list steps explicitly. Only skip `atf.list` once the search above comes back empty.

- 
Once `atf.list` is warranted for a related list, consider all 5 read-only methods against it, not just whichever one obviously matches the found logic's branching behavior. A related list worth testing for visibility (`relatedListVisibility`) or filtering (`applyFilterToList`) is often also worth testing for membership (`recordPresentInList`), navigation (`openRecordInList`), and whether any list-level UI actions are visible on it (`listUIActionVisibility`) -- none of these need additional logic to be meaningful, just a related list already confirmed to be driven by something found in the sweep. `clickListUIAction` is excluded from this default consideration since it actually executes the action (real side effects); only add it when there's a specific reason to verify the action's behavior, not just as a default check. Create simple prerequisite data (`atf.server.recordInsert`) if the child table has no existing records to test presence/navigation against.

- 
Enumerate every surviving candidate before writing any test -- a literal list, not a mental note. If the sweep finds more than one item (e.g. a client script AND a relationship), do not stop as soon as the first one becomes a test -- "I wrote a test" is not "I covered everything I found." After authoring, walk that same list again and confirm each entry maps to a test you actually wrote before finishing.

- 
Report what the sweep found, not just what you decide to test. State every candidate found and whether you're testing it, as you go, before moving to authoring -- don't reason through this silently and only surface the final test list. Visible findings are what let a check that quietly returns an unexpected empty result get caught immediately, instead of only surfacing after tests are already written and you have to ask what query was actually run.

- 
When found logic populates or restricts a related list, prefer validating the underlying data/rule with `atf.server.recordValidation` on the affected record. Add `atf.list` only when the list-level UI behavior itself -- visibility, filtering, list UI actions -- not just the record it shows, is what needs verifying.

## Key Concepts

- Test data setup: At the start of every test, create a dedicated test user and impersonate it with `atf.server.createUser` (it impersonates the new user by default) or `atf.server.createUser` followed by `atf.server.impersonate`. Never impersonate an existing user unless the user explicitly asks you to. See User context and access. Use `atf.server.recordInsert` to create prerequisite data.

- Assertion chaining: After `atf.form.submitForm`, follow with `atf.server.recordValidation` to verify the record was created correctly server-side.

- One validation per record state: Put every expected field value for a record in a single `atf.server.recordValidation`, joining the conditions with `^` (e.g. `fieldValues: 'discount_percent=15^total=4.25'`). Don't add one step per field. Add another `recordValidation` on the same record only when checking a different point in time, e.g. after a `recordUpdate`.

- Form UI flavors: `standard_ui`, or the sys_id of a `sys_ux_page_registry` record for any other workspace.

- Navigator styles: `ui15`, `ui16`, `polaris`.

- Catalog variable format: `IO:<sys_id>=<value>` joined with `^` and ending with `^EQ`.

- Encoded queries: Field value conditions use ServiceNow encoded query syntax (e.g., `short_description=Test^priority=1`).

- Related list value format: `atf.list`'s `relatedList` parameter is not a guessable string -- valid values are dynamically generated per-table by the platform, in the format `<child_table>.<field>` (e.g. `task.parent`, `task_ci.task`), not `<table>_<table>`. Some are relationship-based instead, prefixed `REL:<sys_id>`. This can't be inferred from types -- before authoring, run this via `run_script` against the target instance to get real values for a table: `var lists = new ATFRelatedListUtil().getRelatedLists('incident'); for (var i in lists) gs.info(lists[i].label + ' => ' + lists[i].value);` (must run in Global scope).

## User context and access

Test as a dedicated user with the app's role, not as admin.

- Always create and impersonate a dedicated test user first, with the app's role. Never impersonate an existing user (admin or anyone else) unless the user explicitly asks you to.

- Pass the role as a reference to the app's existing `Role()` record or its sys_id, e.g. `atf.server.createUser({ firstName: 'Test', lastName: 'Customer', roles: [appUserRole] })`.

- A role name (`roles: ['x_app.user']`) isn't resolved: the user is created with no role.

- `createUser` impersonates the new user by default (`impersonate: true`), so every later step runs as that user. If you set `impersonate: false`, follow it with `atf.server.impersonate({ user: <the created user> })`.

- If no app role grants access to its tables (no roles, or a role with no ACLs), the app is admin-only: create the test user with the `admin` role's sys_id, don't add roles or ACLs to the app while writing tests, and tell the user only admins can use it.

- Don't bypass the impersonated user: no `enforceSecurity: false`, and no switching to admin to insert or validate. If a step fails on access, report the access gap to the user.

- If the behavior needs a second user (e.g. an approver), create and impersonate another dedicated test user for it. Never an existing one.

## API Reference: atf.server

### Methods

| Method | Description | Key Output |
| `impersonate` | Impersonate a user for the test | `{ user }` |
| `createUser` | Create a user with roles and groups | `{ user }` |
| `log` | Log a message to test results | void |
| `runServerSideScript` | Run an arbitrary server-side script -- e.g. exercise a Script Include or run Jasmine specs | `{ table, record_id }` |
| `recordQuery` | Query records with encoded query | `{ table, first_record }` |
| `recordInsert` | Insert a record | `{ table, record_id }` |
| `recordValidation` | Validate record meets conditions | void |
| `recordUpdate` | Update a record's fields | void |
| `recordDelete` | Delete a record | void |
| `searchForCatalogItem` | Search catalog items | `{ catalog_item_id }` |
| `checkoutShoppingCart` | Checkout cart | `{ request_id }` |
| `replayRequestItem` | Replay a previous request item | `{ table, req_item }` |

### impersonate

| Name | Type | Mandatory | Description |
| `user` | `string | Record<'sys_user'>` | Yes | User to impersonate |

### createUser

| Name | Type | Mandatory | Description |
| `firstName` | `string` | No | First name. Default: `""` |
| `lastName` | `string` | No | Last name. Default: `""` |
| `fieldValues` | `Partial<Data<'sys_user'>>` | No | Additional user fields (JSON). Default: `{}` |
| `groups` | `Array<string | Record<'sys_user_group'>>` | No | Groups to add. Default: `[]` |
| `roles` | `Array<string | Role>` | No | Roles to grant, as `Role` record references or role sys_ids. Role names are not resolved: the user gets no role. Default: `[]` |
| `impersonate` | `boolean` | No | Impersonate the user for the rest of the test. Default: `true` |

### runServerSideScript

Runs a script on the server. This is the step to use when testing a Script Include or any server-side-only logic that has no UI. Supports custom assertions (outputs, stepResult, assertEqual) and Jasmine test suites (describe/it/expect).

| Name | Type | Mandatory | Description |
| `script` | `string` | No | Server-side script to run. Instantiate the Script Include and assert its output here. |
| `jasmineVersion` | `string` | No | Jasmine version to use. Currently only `'3.1'` is supported (default; may change in future platform releases). |

Available in script context:

- `outputs` — Set output variables for later steps

- `steps(SYS_ID)` — Retrieve output variables from earlier steps

- `params` — Access parameterized test data

- `stepResult.setOutputMessage(msg)` — Log message to step results

- `assertEqual(assertion)` — Compare `assertion.shouldbe` vs `assertion.value`

- Return `true`/`false` to pass/fail step (ignored by Jasmine tests)

```
import { Test } from '@servicenow/sdk/core';
import '@servicenow/sdk/global';

// Example 1: Script Include with custom assertion
Test({
  $id: Now.ID['script_include_test'],
  name: 'Script Include compute test',
  description: 'Validates MyScriptInclude.compute() using a custom assertion',
}, (atf) => {
  atf.server.runServerSideScript({
    $id: Now.ID['test_script_include'],
    jasmineVersion: '3.1', // Current version; may change in future
    script: `
      (function(outputs, steps, params, stepResult, assertEqual) {
        var helper = new MyScriptInclude();
        var result = helper.compute(2, 3);
        assertEqual({ name: 'compute result', shouldbe: 5, value: result });
        outputs.computed_value = result;
        stepResult.setOutputMessage('Script Include test passed');
      })(outputs, steps, params, stepResult, assertEqual);
    `,
  });
});

// Example 2: Jasmine test suite
Test({
  $id: Now.ID['jasmine_suite_test'],
  name: 'MyScriptInclude Jasmine suite',
  description: 'Runs a Jasmine describe/it suite against MyScriptInclude',
}, (atf) => {
  atf.server.runServerSideScript({
    $id: Now.ID['jasmine_suite'],
    jasmineVersion: '3.1',
    script: `
      (function(outputs, steps, params, stepResult, assertEqual) {
        describe('MyScriptInclude', function() {
          it('should compute sum correctly', function() {
            var helper = new MyScriptInclude();
            expect(helper.compute(2, 3)).toBe(5);
          });
        });
      })(outputs, steps, params, stepResult, assertEqual);
      jasmine.getEnv().execute();
    `,
  });
});
```

### recordInsert / recordUpdate

| Name | Type | Mandatory | Description |
| `table` | `TableName` | Yes | Target table |
| `fieldValues` | `Partial<Data<T>>` | Yes | Field-value map (snake_case keys) |
| `assert` | `string` | No | `'record_successfully_inserted'` / `'record_not_inserted'` / `'record_successfully_updated'` / `'record_not_updated'` |
| `enforceSecurity` | `boolean` | No | Default: `true` |
| `recordId` | `string` | Yes (update only) | sys_id of record to update |

### recordValidation

| Name | Type | Mandatory | Description |
| `table` | `TableName` | Yes | Table to validate against |
| `recordId` | `string` | Yes | sys_id of record |
| `fieldValues` | `string` | Yes | Encoded query condition. Combine every expected field with `^` in one step, e.g. `discount_percent=15^total=4.25` |
| `assert` | `string` | No | `'record_validated'` / `'record_not_found'` |

## API Reference: atf.form

### Methods

`openNewForm`, `openExistingRecord`, `submitForm`, `setFieldValue`, `fieldValueValidation`, `fieldStateValidation`, `uiActionVisibility`, `clickUIAction`, `clickModalButton`, `declarativeActionVisibility`, `clickDeclarativeAction`

### Key Properties

openNewForm: `table` (required), `view`, `formUI` (default: `"standard_ui"`)

setFieldValue: `table` (required), `fieldValues` (required, JSON object), `formUI`

submitForm: `assert` (`""`, `"form_submitted_to_server"`, `"form_submission_canceled_in_browser"`), `formUI`. Returns `{ table, record_id }`.

fieldValueValidation: `table`, `conditions` (encoded query), `formUI`

fieldStateValidation: `table`, `visible[]`, `notVisible[]`, `readOnly[]`, `notReadOnly[]`, `mandatory[]`, `notMandatory[]`, `formUI`

clickUIAction: `table`, `uiAction` (sys_id), `assert`, `actionType` (`"ui_action"` or `"declarative_action"`), `formUI`

## API Reference: atf.rest

### Methods

`sendRestRequest`, `assertStatusCodeName`, `assertStatusCode`, `assertResponseTime`, `assertResponseHeader`, `assertResponsePayload`, `assertResponseJSONPayloadIsValid`, `assertJsonResponsePayloadElement`, `assertResponseXMLPayloadIsWellFormed`, `assertXMLResponsePayloadElement`

### sendRestRequest

| Name | Type | Mandatory | Description |
| `path` | `string` | Yes | API path (e.g., `/api/now/table/incident` ) |
| `body` | `string` | Yes | JSON string request body |
| `auth` | `string` | Yes | `'basic'` , `'mutual'` , or `''` |
| `method` | `string` | No | `'get'` , `'post'` , `'put'` , `'delete'` , `'patch'` |
| `queryParameters` | `object` | No | Key-value query params |
| `headers` | `object` | No | Key-value request headers |

### Assert Methods

- `assertStatusCode`: `statusCode` (number), `operation` (`'equals'`, `'not_equals'`, `'less_than'`, etc.)

- `assertResponsePayload`: `responseBody` (string), `operation` (`'contains'`, `'equals'`, etc.)

- `assertJsonResponsePayloadElement`: `elementName` (JSON path), `elementValue`, `operation`

## API Reference: atf.catalog

### Methods

`openCatalogItem`, `addItemToShoppingCart`, `setCatalogItemQuantity`, `orderCatalogItem`, `validatePriceAndRecurringPrice`, `validateVariableValue`, `variableStateValidation`, `setVariableValue`, `openRecordProducer`, `submitRecordProducer`

### Key Properties

openCatalogItem: `catalogItem` (sys_id, required)

setVariableValue: `catalogItem` (sys_id), `variableValues` (format: `IO:<sys_id>=<value>^IO:<sys_id>=<value>^EQ`)

orderCatalogItem: `assert` (`'form_submitted_to_server'` or `'form_submission_cancelled_in_browser'`). Returns `{ request_id, cart }`.

Important sequencing: `openCatalogItem` must precede `orderCatalogItem`. `openRecordProducer` must precede `submitRecordProducer`.

## API Reference: atf.email

### Methods

| Method | Description |
| `validateOutboundEmail` | Filter sys_email table for sent emails |
| `validateOutboundEmailGeneratedByNotification` | Filter by notification source |
| `validateOutboundEmailGeneratedByFlow` | Filter by flow source |
| `generateInboundEmail` | Generate a new inbound email |
| `generateInboundReplyEmail` | Generate an inbound reply |
| `generateRandomString` | Generate test data string |

### generateInboundEmail

`from`, `to`, `subject`, `body` (all required strings). Returns `{ output_email_record }`.

## API Reference: atf.applicationNavigator

### Methods

- `moduleVisibility`: Check if modules are visible in navigation. `navigator` (`'ui15'`, `'ui16'`, `'polaris'`), `visibleModules[]`, `notVisibleModules[]`.

- `navigateToModule`: Navigate to a module. `module` (sys_id).

- `applicationMenuVisibility`: Check if app menus are visible. `visible[]`, `notVisible[]`.

## API Reference: atf.reporting

### reportVisibility

`report` (sys_id of `sys_report`), `assert` (`'can_view_report'` or `'cannot_view_report'`).

## API Reference: atf.responsiveDashboard

### responsiveDashboardVisibility

`dashboard` (sys_id of `pa_dashboards`), `assert` (`'dashboard_is_visible'` or `'dashboard_is_not_visible'`).

### responsiveDashboardSharing

`dashboard` (sys_id), `assert` (`'can_share_dashboard'` or `'cannot_share_dashboard'`).

## API Reference: atf.list

### Methods

| Method | Description | Key Output |
| `relatedListVisibility` | Check related lists are visible/not visible on the current form | void |
| `applyFilterToList` | Apply a filter to a list, narrowing it to matching records | `{ first_record }` |
| `recordPresentInList` | Check a specific record is/isn't present in a list | void |
| `openRecordInList` | Open a specific record from a list | void |
| `listUIActionVisibility` | Check UI actions are visible/not visible on a list | void |
| `clickListUIAction` | Click a UI action on a list | void |

Every method except `relatedListVisibility` takes `listType` (`'related_list'` default, or `'list'`), `relatedList` (which related list/list view -- see Related list value format in Key Concepts), and `relatedListTable` (the table the list's records live in -- `recordId` and `applyFilterToList`'s `first_record` output are typed against this table, not `table`).

Important sequencing: `applyFilterToList` is typically used to narrow to a record before `recordPresentInList`/`openRecordInList`/`clickListUIAction`. `listUIActionVisibility` (can I see the action) generally precedes `clickListUIAction` (exercise it) when both are being verified.

### Worked Example -- All 6 Methods

Demonstrates correct parameter usage for every `atf.list` method, chained on a real, out-of-the-box related list (`incident`'s "Task -> Parent", `task.parent`) -- this shows the API mechanics correctly, it is NOT an example of when to use `atf.list` (see Category Selection Guidance above -- only author these steps when a client script, UI policy, or relationship actually drives the behavior, never for a plain related list with nothing behind it like this one).

```
import { Test } from '@servicenow/sdk/core'

Test({ $id: Now.ID['list_test'], name: 'ATF List Test' }, (atf) => {
    atf.list.relatedListVisibility({
        $id: Now.ID['rl_vis'],
        table: 'incident',
        visible: ['task.parent'],
    })

    const filterResult = atf.list.applyFilterToList({
        $id: Now.ID['apply_filter'],
        table: 'incident',
        relatedList: 'task.parent',
        relatedListTable: 'task',
        filterConditions: 'active=true^EQ',
        assert: 'records_match_filter',
    })

    atf.list.recordPresentInList({
        $id: Now.ID['record_present'],
        table: 'incident',
        relatedList: 'task.parent',
        relatedListTable: 'task',
        recordId: filterResult.first_record,
        assert: 'record_present',
    })

    atf.list.openRecordInList({
        $id: Now.ID['open_record'],
        table: 'incident',
        relatedList: 'task.parent',
        relatedListTable: 'task',
        recordId: filterResult.first_record,
    })

    atf.list.listUIActionVisibility({
        $id: Now.ID['list_ui_action_visibility'],
        table: 'incident',
        relatedList: 'task.parent',
        relatedListTable: 'task',
        visible: ['Update'],
    })

    atf.list.clickListUIAction({
        $id: Now.ID['click_list_ui_action'],
        table: 'incident',
        relatedList: 'task.parent',
        relatedListTable: 'task',
        listAction: '<real sys_ui_action sys_id on the child table>',
        actionType: 'list_banner_button',
        assert: 'page_reloaded_or_redirected',
    })
})
```

Not yet runtime-confirmed. This demonstrates correct parameter shape and chaining, verified against the real serialization/install pipeline when originally built -- it has not been confirmed to actually pass when executed via the ATF test runner. Re-verify if a real gap surfaces here.

## Service Portal Variants

### atf.form_SP

Same methods as `atf.form` with additional `portal` and `page` properties plus `openServicePortalPage` method. Uses `form_SP` namespace.

### atf.catalog_SP

Same methods as `atf.catalog` with additional `portal` and `page` properties, plus: `openOrderGuide`, `navigatewithinOrderGuide`, `validateOrderGuideItem`, `reviewOrderGuideSummary`, `saveCurrentRowOfMultiRowVariableSet`, `addRowToMultiRowVariableSet`.

## Test Suites

Group related `Test()` records into an ordered, runnable collection with `TestSuite()` (see `testsuite-api` for the full reference). Reach for a suite when a set of tests should be run and reported on together -- e.g. all tests covering one feature area, or a smoke-test set that gates a build -- rather than run individually one at a time.

```
import { Test, TestSuite } from '@servicenow/sdk/core'

const loginTest = Test({ $id: Now.ID['login_test'], name: 'User can log in' }, (atf) => {
    atf.server.log({ $id: Now.ID['log_login'], log: 'Checking login' })
})
const checkoutTest = Test({ $id: Now.ID['checkout_test'], name: 'User can check out' }, (atf) => {
    atf.server.log({ $id: Now.ID['log_checkout'], log: 'Checking checkout' })
})

const smokeSuite = TestSuite({
    $id: Now.ID['smoke_suite'],
    name: 'Smoke Suite',
    // Order comes from array position. abortOnFailure stops the suite early on that test's failure.
    tests: [{ test: loginTest, abortOnFailure: true }, checkoutTest],
})
```

Nest a suite under a broader one with `parent` (must reference an already-declared suite):

```
const regressionSuite = TestSuite({ $id: Now.ID['regression_suite'], name: 'Full Regression' })

const authSuite = TestSuite({
    $id: Now.ID['auth_suite'],
    name: 'Authentication',
    tests: [loginTest],
    parent: regressionSuite,
})
```

`TestSuite()` is authoring only -- it produces the suite/membership metadata (`sys_atf_test_suite`, `sys_atf_test_suite_test`). Triggering or scheduling an actual run of the suite is done through ATF's own UI, scheduler, or CI/CD integration, not through Fluent.

## Avoidance

- Do not overuse `atf.server` for tasks that form or catalog APIs handle directly.

- Do not hardcode `sys_id` values -- always look them up.

- Do not skip mandatory fields when using `setFieldValue` or `recordInsert`.

- Do not call sequence-dependent steps out of order.

- Do not create generic or template-based tests -- each test should reflect real usage scenarios.

- Do not use workspace name strings (e.g. `service_operations_workspace`) for `formUI` -- they 404. Use the workspace's `sys_ux_page_registry` sys_id.

## Example: End-to-End Form Test

```
import "@servicenow/sdk/global";
import { Test } from "@servicenow/sdk/core";

Test({
  $id: Now.ID["validate_incident_form"],
  name: "Create and Validate Incident",
  description: "Opens a new incident form, sets fields, submits, and validates",
  failOnServerError: true
}, (atf) => {
  const testUser = atf.server.createUser({
    $id: Now.ID["create_test_user"],
    firstName: "Test",
    lastName: "Caller",
    roles: ["<itil role sys_id, looked up on the instance>"]
  });

  atf.form.openNewForm({
    $id: Now.ID["open_new_incident"],
    table: "incident",
    formUI: "standard_ui"
  });

  atf.form.setFieldValue({
    $id: Now.ID["set_fields"],
    table: "incident",
    fieldValues: {
      short_description: "Email server is down",
      caller_id: testUser.user
    },
    formUI: "standard_ui"
  });

  const result = atf.form.submitForm({
    $id: Now.ID["submit_form"],
    assert: "form_submitted_to_server",
    formUI: "standard_ui"
  });

  atf.server.recordValidation({
    $id: Now.ID["validate_record"],
    table: "incident",
    recordId: result.record_id,
    fieldValues: "short_description=Email server is down",
    assert: "record_validated"
  });
});
```

## Example: REST API Test

```
import "@servicenow/sdk/global";
import { Test } from "@servicenow/sdk/core";

Test({
  $id: Now.ID["scaffold_api_test"],
  name: "Scaffold API Test",
  failOnServerError: true
}, (atf) => {
  atf.rest.sendRestRequest({
    $id: Now.ID["send_request"],
    path: "/api/now/fluent/scaffold",
    body: "",
    auth: "basic",
    method: "get",
    queryParameters: { new: "true" },
    headers: {}
  });

  atf.rest.assertStatusCode({
    $id: Now.ID["assert_status"],
    operation: "equals",
    statusCode: 200
  });

  atf.rest.assertResponseJSONPayloadIsValid({
    $id: Now.ID["assert_json_valid"]
  });

  atf.rest.assertJsonResponsePayloadElement({
    $id: Now.ID["assert_result"],
    elementName: "result",
    operation: "equals",
    elementValue: "success"
  });
});
```

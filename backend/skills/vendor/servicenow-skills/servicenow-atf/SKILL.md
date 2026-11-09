---
name: servicenow-atf
description: ServiceNow Automated Test Framework (ATF) - tests, test steps, suites, server-side script tests, form and UI test steps, impersonation, running tests in a sub-production instance, and what to test before promoting changes. Use when asked to test a business rule, script include, form behaviour or flow, or to plan regression tests.
license: Apache-2.0
metadata:
  category: quality
  version: "1.1"
---

# Automated Test Framework (ATF)

## Building blocks
- **Test** (`sys_atf_test`) - an ordered list of **test steps** (`sys_atf_step`).
- **Test suite** (`sys_atf_test_suite`) - groups tests; can be scheduled.
- **Step types**: Server (Record Insert / Update / Query / Validation / Delete, Run Server Side Script,
  Impersonate, Create a User), Form (Open a New Form, Set Field Values, Field Values Validation,
  UI Action Visibility, Click a UI Action, Submit a Form), Service Catalog, REST, and
  *Run UI Test Script* for client-side journeys on classic and Now Experience pages.
- Data created by a test is rolled back when the test ends.

## Rules
1. Run ATF in sub-production only (`sn_atf.runner.enabled` must be true); never in production.
2. One behaviour per test; name it for the rule it proves ("Resolve requires close notes").
3. Impersonate the persona (itil, requester) instead of testing as admin, so ACLs and UI policies apply.
4. Business rule: Record Insert/Update with the triggering values → Record Validation of the result,
   plus a negative case (the save is rejected).
5. Script include: *Run Server Side Script* with Jasmine-style `expect(...)` assertions on public methods.
6. Client script / UI policy: Open a New Form → Set Field Values → Field State Validation.
7. Flow: insert the trigger record, then validate the flow's effect (or use the flow testing API).
8. Group tests in a suite per application; run it before every promotion.

## What nowBuilder does
nowBuilder doesn't create ATF tests yet; after deploying it says how to test each artifact, and can
describe the ATF test steps for the user to create in Automated Test Framework → Tests.

Version: 4.14.0

# Data Lookup

Guide for creating ServiceNow Data Lookup definitions (`dl_definition`) using the Fluent API. A Data Lookup connects a source table to a configurable matcher table and defines which source fields are used to find a matching row and which values are copied back to the source record. In simple terms: “when field A has value X and field B has value Y, set field C to value Z.”. Use Data Lookup when a user wants to auto-fill, auto-populate, or automatically set one or more fields on a record based on a combination of other field values — for example, automatically setting Priority from Impact and Urgency — and the mapping should be admin-maintainable as configuration records without scripting. Data Lookup covers all three triggers natively: form field change, record insert, and record update. If you find yourself reaching for a Business Rule (for insert/update) plus a Client Script (for onChange) to implement the same deterministic field-population logic, use Data Lookup instead.

## When to Use

Use DataLookup when:

- The user wants one or more fields on a standard table record to be populated automatically based on the values of other fields.

- The requirement can be expressed as: “when field A has value X and field B has value Y, set field C to value Z.”

- The output values are determined by a finite, deterministic set of configured field combinations.

- The mapping should be maintained as data/configuration records by admins, rather than implemented as hardcoded script logic.

- The same input field values should consistently produce the same output field values.

- The behavior should run when users change relevant values on the form, when records are inserted, or when records are updated, depending on the requested behavior.

- The values are applied back to fields on the source record after a matching configured row is found.

- The scenario is field derivation or field mapping, not procedural automation.

Common requirement phrases that indicate Data Lookup (recognize these and choose Data Lookup first):

- "auto-fill", "auto-populate", "automatically fill", "automatically populate", "automatically set"

- "based on [field1] and [field2], populate/set [field3]"

- "admins should be able to maintain/configure the combinations as records"

- "values should update when fields change on the form AND when records are saved/created/updated"

- "populate from a combination of inputs", "fill based on field combination", "set field based on other fields"

- "eligible/allowed values determined by a combination", "matrix of values", "mapping table"

- Any Impact/Urgency → Priority matrix, or similar N-input → M-output deterministic mapping

Always prefer Data Lookup over Business Rule + Client Script combinations when ALL of the following are true:

- The mapping is deterministic: the same inputs always produce the same outputs

- The mapping should be admin-maintainable as data records (not hardcoded in a script)

- The behavior is needed both on form field change AND on record insert/update

If you find yourself planning a Business Rule (for insert/update) alongside a Client Script (for onChange) to implement the same field-population logic, that is the exact pattern Data Lookup was designed to replace — use Data Lookup instead.

## Key Concepts

### How a Data Lookup Works

On insert or update, the platform queries the matcher table using the match rules. If a matching row is found, its values are copied into the source record via the set rules.

### Source Table and Matcher Table

- Source table (`sourceTable`): The table whose records receive the copied values. In a scoped app (non-global, non-`sn_`/`now_`), must be in the same scope as the `DataLookup` definition (e.g., `x_myapp_orders`). For OOB tables such as `incident`, use a global-scope app or a scoped extension table.

- Matcher table (`matcherTable`): Holds the mapping matrix as data rows. Must extend `dl_matcher`. Valid options: `u_` prefixed tables (created via admin UI), `dl_u_` prefixed OOB platform tables (e.g., `dl_u_priority`), or `x_`/`sn_`/`now_` scoped tables defined with `extends: 'dl_matcher'` — must be in the same scope as the `DataLookup`.

### Match Rules

Each rule compares a source record field against a matcher column. All rules must pass for the lookup to trigger. Use `exactMatch: true` for choice, string, and reference fields; use the default (`false`) for numeric or range-based fields.

- `$id` (required), `sourceField`, `matcherField`, `exactMatch` (default `false`)

### Set Rules

Each rule copies one value from a matcher column into a source record field when the lookup applies.

- `$id` (required), `targetField` (written to source), `matcherField` (read from matcher), `alwaysReplace` (default `false` — set `true` to overwrite existing values)

### Trigger Configuration

| Property | Default | Behavior |
| `runOnInsert` | `true` | Runs when the source record is first saved |
| `runOnUpdate` | `false` | Runs each time the source record is updated |
| `runOnFormChange` | `true` | Runs on client-side form change before save |

### Name Length Constraint

The `name` field must be 40 characters or fewer. Names that exceed 40 characters cause a build error.

### Matcher Table Seed Data — active Field Required

Tables that extend dl_matcher inherit an active boolean field (with default_value: "true" in the dictionary). However, the Fluent Record() API does not apply dictionary default values when inserting records. The Data Lookup engine queries the matcher table with an implicit active=true filter — records where active is null or false will never match.

Always explicitly include active: true in the data block of every Record() targeting a dl_matcher-extended table:

```
import { Record } from '@servicenow/sdk/core'

Record({
    $id: Now.ID['my-matcher-row'],
    table: 'x_myapp_my_matcher',
    data: {
        active: true,  // REQUIRED — without this, the Data Lookup engine ignores the row
        match_field: 'some_value',
        setter_field: 42,
    },
})
```

#### Scope consideration

Both `sourceTable` and `matcherTable` must be in the same scope as the data lookup definition when the app is scoped (non-global). A build error is emitted if either table is from a different scope. For OOB source tables, see the scope guidance in the Examples section below.

## Instructions

### Step 1 — Design the Matcher Table Schema

Identify all the fields that will be used for matching (inputs) and all the fields that will be copied to the source record (outputs). For each:

- Match field on source table: note the field name and type (choice, reference, string, integer)

- Setter field on source table: note the field name and type

- Source table `StringColumn` with choices: if a match or setter field is a choice-type field, define the `choices` property on that `StringColumn` in the source table's `Table()` schema. The same choices must appear on both the source table column and the corresponding matcher table column.

The matcher table needs one column for each match field and one column for each setter field, with column types matching the source table field types (e.g., `StringColumn` with `choices` for string fields in matcher table, etc.).

### Step 2 — Create the Matcher Table

Define the matcher table using `Table()` with `extends: 'dl_matcher'`. Add a `ChoiceColumn`, `ReferenceColumn`, `StringColumn`, or other appropriate column for each match and setter field.

Note on Choice Fields: When your app owns a table (source or matcher), always define the `choices` property directly on the `StringColumn` (or `ChoiceColumn`) in that table's `Table()` schema — both the source table and the matcher table must have matching `choices` on any column used for matching. Use `ChoiceSet` only when adding choices to a field your app does not own (e.g., an inherited field from a global table like `task`). By default, the SDK generates choices in v3 format (`sys_choice_set`), which is supported on all platform versions but uses destructive delete-all-then-insert behavior. If you only target instances with v4 loader support (Brazil+, Australia P4+, Zurich P11+) and want additive, non-destructive updates instead, add `"legacyChoices": false` to `now.config.json` to switch to v4 format (`sys_choice_v2`). See the End-to-End — Custom Source Table example for how choices are mirrored across both tables.

### Step 3 — Plan the Data Matrix

Before writing the `DataLookup` definition, plan the mapping matrix — the set of rows that will be entered on the instance after deployment. This determines:

- How many columns the matcher table needs

- Whether the combination of match columns is sufficient to uniquely identify each row

### Step 4 — Define the DataLookup

Create the `DataLookup()` definition referencing the source and matcher tables. Add `matchRules` for each input field pair and `setRules` for each output field pair.

### Step 5 — Configure Trigger Behavior

Choose the right trigger combination:

- Default (insert + form change only): omit `runOnUpdate`

- Always enforce on every save (e.g., "always overwrite even if manually changed"): add `runOnUpdate: true` and use `alwaysReplace: true` on the relevant set rules

- Insert only, no client-side behavior: add `runOnFormChange: false`

- Update only: add `runOnInsert: false, runOnUpdate: true, runOnFormChange: false`

### Step 6 — Seed Data Rows Using Record()

For each row in the mapping matrix, create one `Record()` call targeting the matcher table. Each record represents one combination of input values → output values. Use the choice field internal values (not display labels) for choice columns and the sys_id string for reference columns.

Give each row a descriptive `$id` key that encodes the match values (e.g., `Now.ID['incident-routing-row-network-vpn']`) so the same sys_id is preserved across builds.

Always explicitly include `active: true` in the data block of every `Record()` targeting a `dl_matcher` extended table.

### Step 7 — Use `$id` for Stable Identity

Every `DataLookup`, `DataLookupMatchRule`, and `DataLookupSetRule` must have `$id: Now.ID['identifier']`.

## Examples

### End-to-End — OOB Source Table, Single Match Field, Multiple Setters

Scenario: When creating a Problem, I would like to be able select the level of Impact and Urgency of the issue I am dealing with So that the system can automatically set the Priority.

Important: When performing data lookup operations on an OOB table (e.g. Problem, Incident), check your app scope first. If your app is global-scoped, you can reference the OOB table directly. If your app is scoped (non-global), you must create a scoped source table that extends the OOB table and use that as the source instead.

Rule: If your app is global-scoped, reference the OOB table (e.g. `'problem'`, `'incident'`) directly as `sourceTable`. If your app is scoped, create a scoped table with `extends: 'problem'` (or `extends: 'incident'`) and use that scoped table name as `sourceTable` and `matcherTable` scope instead.

Step 1 — Define the matcher table:

```
import { Table, IntegerColumn } from '@servicenow/sdk/core'

export const u_problem_priority_matcher = Table({
    $id: Now.ID['problem-priority-matcher'],
    name: 'u_problem_priority_matcher',
    label: 'Problem Priority Matcher',
    extends: 'dl_matcher',
    schema: {
        u_impact: IntegerColumn({ label: 'Impact' }),
        u_urgency: IntegerColumn({ label: 'Urgency' }),
        u_priority: IntegerColumn({ label: 'Priority' }),
    },
})
```

Step 2 — Define the DataLookup:

```
import { DataLookup } from '@servicenow/sdk/core'

export const ProblemPriorityLookup = DataLookup({
    $id: Now.ID['problem-priority-lookup'],
    name: 'Problem Priority Lookup',
    sourceTable: 'problem',
    matcherTable: 'u_problem_priority_matcher',
    runOnInsert: true,
    runOnUpdate: true,
    runOnFormChange: true,
    matchRules: [
        {
            $id: Now.ID['problem-priority-match-impact'],
            sourceField: 'impact',
            matcherField: 'u_impact',
            exactMatch: true,
        },
        {
            $id: Now.ID['problem-priority-match-urgency'],
            sourceField: 'urgency',
            matcherField: 'u_urgency',
            exactMatch: true,
        },
    ],
    setRules: [
        {
            $id: Now.ID['problem-priority-set-priority'],
            targetField: 'priority',
            matcherField: 'u_priority',
            alwaysReplace: true,
        },
    ],
})
```

Step 3 — Seed the mapping matrix using Record():

```
import { Record } from '@servicenow/sdk/core'

// Impact High (1) combinations
Record({
    $id: Now.ID['priority-row-high-high'],
    table: 'u_problem_priority_matcher',
    data: { active: true, u_impact: 1, u_urgency: 1, u_priority: 1 },
})

Record({
    $id: Now.ID['priority-row-high-medium'],
    table: 'u_problem_priority_matcher',
    data: { active: true, u_impact: 1, u_urgency: 2, u_priority: 2 },
})
```

### End-to-End — Custom Source Table (Custom App)

Scenario: A custom Loan application table where Loan Type and employment type determine Interest Rate, eligible loan amount, and repayment period.

Step 1 — Define the source table:

```
import '@servicenow/sdk/global'
import { Table, StringColumn, DecimalColumn, IntegerColumn, ReferenceColumn } from '@servicenow/sdk/core'

export const x_internal_emplo_2_loan_request = Table({
    name: 'x_internal_emplo_2_loan_request',
    label: 'Loan Request',
    accessibleFrom: 'public',
    allowWebServiceAccess: true,
    autoNumber: {
        prefix: 'LR',
        number: 1000,
        number_of_digits: 7,
    },
    schema: {
        employee: ReferenceColumn({
            label: 'Employee',
            referenceTable: 'sys_user',
            mandatory: true,
        }),
        loan_type: StringColumn({
            label: 'Loan Type',
            choices: {
                personal_loan: { label: 'Personal Loan', sequence: 0 },
                education_loan: { label: 'Education Loan', sequence: 1 },
                vehicle_loan: { label: 'Vehicle Loan', sequence: 2 },
            },
            dropdown: 'dropdown_with_none',
            mandatory: true,
            maxLength: 40,
        }),
        employment_type: StringColumn({
            label: 'Employment Type',
            choices: {
                full_time: { label: 'Full-Time', sequence: 0 },
                part_time: { label: 'Part-Time', sequence: 1 },
                contract: { label: 'Contract', sequence: 2 },
            },
            dropdown: 'dropdown_with_none',
            mandatory: true,
            maxLength: 40,
        }),
        requested_amount: DecimalColumn({
            label: 'Requested Amount',
            mandatory: true,
        }),
        eligible_loan_limit: DecimalColumn({
            label: 'Eligible Loan Limit',
            readOnly: true,
            readOnlyOption: 'instance_configured',
        }),
        interest_rate: DecimalColumn({
            label: 'Interest Rate (%)',
            readOnly: true,
            readOnlyOption: 'instance_configured',
        }),
        repayment_period: IntegerColumn({
            label: 'Repayment Period (Months)',
            readOnly: true,
            readOnlyOption: 'instance_configured',
        }),
    },
})
```

Step 2 — Define the matcher table extended from dl_matcher:

```
import '@servicenow/sdk/global'
import { Table, StringColumn, DecimalColumn, IntegerColumn } from '@servicenow/sdk/core'

export const x_internal_emplo_2_loan_eligibility = Table({
    name: 'x_internal_emplo_2_loan_eligibility',
    label: 'Loan Eligibility',
    extends: 'dl_matcher',
    accessibleFrom: 'public',
    allowWebServiceAccess: true,
    schema: {
        loan_type: StringColumn({
            label: 'Loan Type',
            choices: {
                personal_loan: { label: 'Personal Loan', sequence: 0 },
                education_loan: { label: 'Education Loan', sequence: 1 },
                vehicle_loan: { label: 'Vehicle Loan', sequence: 2 },
            },
            dropdown: 'dropdown_with_none',
            mandatory: true,
            maxLength: 40,
        }),
        employment_type: StringColumn({
            label: 'Employment Type',
            choices: {
                full_time: { label: 'Full-Time', sequence: 0 },
                part_time: { label: 'Part-Time', sequence: 1 },
                contract: { label: 'Contract', sequence: 2 },
            },
            dropdown: 'dropdown_with_none',
            mandatory: true,
            maxLength: 40,
        }),
        eligible_loan_limit: DecimalColumn({
            label: 'Eligible Loan Limit',
            mandatory: true,
        }),
        interest_rate: DecimalColumn({
            label: 'Interest Rate (%)',
            mandatory: true,
        }),
        repayment_period: IntegerColumn({
            label: 'Repayment Period (Months)',
            mandatory: true,
        }),
    },
})
```

Step 3 — Define the DataLookup:

```
import '@servicenow/sdk/global'
import { DataLookup } from '@servicenow/sdk/core'

export const LoanEligibilityLookup = DataLookup({
    $id: Now.ID['loan-eligibility-lookup'],
    name: 'Loan Eligibility Lookup',
    sourceTable: 'x_internal_emplo_2_loan_request',
    matcherTable: 'x_internal_emplo_2_loan_eligibility',
    runOnInsert: true,
    runOnUpdate: true,
    runOnFormChange: true,
    matchRules: [
        {
            $id: Now.ID['loan-match-loan-type'],
            sourceField: 'loan_type',
            matcherField: 'loan_type',
            exactMatch: true,
        },
        {
            $id: Now.ID['loan-match-employment-type'],
            sourceField: 'employment_type',
            matcherField: 'employment_type',
            exactMatch: true,
        },
    ],
    setRules: [
        {
            $id: Now.ID['loan-set-eligible-limit'],
            targetField: 'eligible_loan_limit',
            matcherField: 'eligible_loan_limit',
            alwaysReplace: true,
        },
        {
            $id: Now.ID['loan-set-interest-rate'],
            targetField: 'interest_rate',
            matcherField: 'interest_rate',
            alwaysReplace: true,
        },
        {
            $id: Now.ID['loan-set-repayment-period'],
            targetField: 'repayment_period',
            matcherField: 'repayment_period',
            alwaysReplace: true,
        },
    ],
})
```

Step 4 — Seed the mapping matrix using Record() in Matcher table:

```
import '@servicenow/sdk/global'
import { Record } from '@servicenow/sdk/core'

// Personal Loan + Full-Time
Record({
    $id: Now.ID['eligibility-personal-fulltime'],
    table: 'x_internal_emplo_2_loan_eligibility',
    data: {
        active: true,
        loan_type: 'personal_loan',
        employment_type: 'full_time',
        eligible_loan_limit: 500000,
        interest_rate: 8,
        repayment_period: 24,
    },
})

// Personal Loan + Part-Time
Record({
    $id: Now.ID['eligibility-personal-parttime'],
    table: 'x_internal_emplo_2_loan_eligibility',
    data: {
        active: true,
        loan_type: 'personal_loan',
        employment_type: 'part_time',
        eligible_loan_limit: 200000,
        interest_rate: 10,
        repayment_period: 12,
    },
})
// Add more combinations as needed
```

## Avoidance

- Never set `name` longer than 40 characters — The build will fail with an error; count characters before committing to a name

- Never omit `$id` — Every `DataLookup`, `DataLookupMatchRule`, and `DataLookupSetRule` requires its own `$id`. Each rule is stored as a separate record on the instance; without a stable `$id`, rebuilding from a fresh checkout creates duplicate records

- Never omit `active: true` on matcher table records — Records without `active: true` are excluded from lookups entirely

- Never set all three trigger flags to `false` — A lookup that never triggers is inert; if disabling temporarily, use `active: false` instead

- Avoid `alwaysReplace: true` on fields users may fill in manually — It overwrites user-entered values on every trigger; use `false` (default) when users should retain the ability to set the field themselves

- Never use display labels as choice field values in `Record()` data — Use the choice internal value (e.g., `'network'`, `'high'`), not the display label (e.g., `'Network'`, `'High'`). The platform matches on internal values

- Never omit `choices` on source table `StringColumn` fields used as match inputs — if the field is a choice-type field, the `choices` property must be set on its `StringColumn` in the source `Table()` schema. Omitting it means the field behaves as a plain string and dropdowns will not render correctly. The matcher table column must mirror the same choices.

- Never reference tables from a different scope — Both `sourceTable` and `matcherTable` must be in the same scope as the `DataLookup` definition when the app is scoped. A cross-scope reference (e.g., a table from `x_otherapp_` used in a `x_myapp_` lookup) emits a build error. To use OOB tables, use a global-scope app or a scoped extension table.

- Do not use a Business Rule, Client Script, or Assignment Rule to implement deterministic field mapping — When the rule is "based on this combination of field values, set these other values" and the mapping is maintainable as data rows, always use DataLookup. See the `business-rule-guide`, `client-script-guide`, and `assignment-rule-guide` topics for those alternatives

- Do not use DataLookup for procedural automation — DataLookup is for field derivation only. For notifications, tasks, external calls, or UI-only behavior, use Flow, Business Rule, Notification, UI Policy, Client Script, or another appropriate metadata type

## Related Topics

See `business-rule-guide`, `assignment-rule-guide`, `table-guide` topics.

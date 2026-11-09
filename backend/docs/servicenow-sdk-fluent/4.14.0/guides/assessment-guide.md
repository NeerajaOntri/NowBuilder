Version: 4.14.0

# Assessment & Survey Guide

Guide for creating ServiceNow Assessments and Surveys (`asmt_metric_type`) using the Fluent API. Surveys collect user feedback through simple, unscored questionnaires; assessments evaluate, score, and rank assessable records with weighted and normalized results. Both share the same nested structure: type → categories → metrics → definitions. This framework only defines the survey/assessment and its in-platform delivery (a generated instance in the recipient's assessment queue) — it does not email a survey link or send a notification, so to send, email, or notify a recipient you must pair it with an Email Notification.

For change risk assessments, see risk-assessment-guide.md.

## When to Use

- Creating a scored assessment to evaluate records in a target table (e.g. security posture of CI services)

- Creating an unscored survey to collect feedback (e.g. onboarding questionnaire, NPS survey)

- Defining categories (sections) to group related questions

- Defining metrics (questions) with various answer types (yes/no, numeric scale, choice, etc.)

- Defining metric definitions (answer options) for choice, scale, and ranking questions

- Setting up conditional questions that depend on the answer to a sibling question

Delivery — building this alone does NOT notify anyone. When the trigger condition matches (for the service-request example, when the request is closed or cancelled per your `condition`), the framework generates an in-platform assessment/survey instance and assigns it to the recipient, who then completes it from their assessment queue. That trigger is a server-side business rule — for a scored assessment the plugin generates it automatically (see Generating and Assigning Assessable Records and instruction #8). The business rule's only job is to fire that generation when the condition matches; it is not a delivery mechanism. As a result, nothing built here emails a survey link or sends a notification — the recipient learns about the survey only if they open their assessment queue.

If the request involves sending, emailing, or notifying the recipient, this guide alone is not enough — you MUST also add a delivery mechanism. Read the relevant guide and build it before treating the task as complete:

- Email the recipient a survey link → Email Notification guide

Only skip this when the requirement is explicitly for an in-platform-only survey. Do not report the survey as done when the user asked to send or notify — an in-platform instance with no notification means the recipient never learns they have a survey to take.

Generating the survey URL. The link that opens a survey in Employee Center (ESC) is `<instance-url>/esc?id=take_survey&type_id=<asmt_metric_type sys_id>`. A Fluent assessment's `$id` becomes its `asmt_metric_type` sys_id at build time, so reference that `$id` directly instead of looking the record up by name with a `GlideRecord` at runtime. In the example below, `satisfactionSurvey` is the `Assessment` defined with `$id: Now.ID['service_request_satisfaction_survey']`:

```
var instanceUrl = gs.getProperty('glide.servlet.uri');
var surveyUrl = instanceUrl + 'esc?id=take_survey&type_id=${satisfactionSurvey.$id}';
template.print(surveyUrl);
```

`${satisfactionSurvey.$id}` (the `type_id`) is interpolated at build time, so the real sys_id is baked into the generated mail script — no `GlideRecord('asmt_metric_type')` lookup by name on every send, and it can't break if the assessment is renamed. This link opens the survey for that assessment type in Employee Center.

## Instructions

- Choose evaluation method first and set it explicitly. Use `evaluationMethod: 'assessment'` (default) for scored evaluations against a `table`, or `'survey'` for unscored questionnaires. This determines which fields are required. Omitting `evaluationMethod` always creates an assessment, which requires `table` and `scaleFactor` — so surveys must set `evaluationMethod: 'survey'`.

- Set the target table. For assessments, `table` is required — it identifies which records are being assessed. Surveys do not use a target table — `table` and `condition` are managed internally and omitted from the Fluent output.

- `condition` is an encoded query that restricts which `table` records get assessed at all (e.g. only `active=true^priority=1`). It's evaluated by the auto-generated trigger business rule (see #8) before an assessment instance is ever generated — records that don't match are skipped entirely. This is different from a metric's own `condition` (see #6), which only controls whether a single question applies once an assessment instance already exists.

- Always set `condition` explicitly for scored assessments, even when you intend to cover every record (e.g. `'active=true'`). Leaving it unset means the trigger business rule fires for every record ever inserted/updated on `table`, silently generating an assessment instance for records the assessment was never meant to cover. State the scope in code rather than relying on the empty-string default.

- Apply the same rule to a category's `filter` (see Category-Level Overrides below): set it explicitly for every category, scoped to that category's subset of records, rather than leaving it blank and inheriting the assessment's full record set implicitly.

- Getting `condition`/`filter` wrong doesn't just widen or narrow scope — it can silently block assignment entirely. If the assessment's `condition` matches nothing, `Generate Assessable Records` produces zero assessable records overall. If a category's `filter` is narrower than (or inconsistent with) the assessment's `condition`, that specific category can end up with zero assessable records even while other categories have some. Either way, you'll have successfully "generated assessable records" and still be unable to assign the assessment to an assessor — see Generating and Assigning Assessable Records, platform check #1. Keep a category's `filter` consistent with (a subset of, not disjoint from) the assessment's own `condition`, as the examples in this guide do.

- Structure questions in categories. Every metric belongs to a category. Categories group related questions and contribute to the overall score via `weight`.

- Use the correct `dataType`. Each metric's `dataType` determines the answer widget and which type-specific fields are available. Common types: `yesNo`, `numericScale`, `choice`, `string`, `likertScale`.

- Add definitions for choice-based questions. For `choice`, `multipleSelection`, `likertScale`, `numericScale`, `imageScale`, and `ranking` data types, provide `definitions` mapping stored values to display labels.

- Conditional questions. Use `dependsOn` with `Now.ref('asmt_metric', '<sibling-id>')` to reveal a question only when the parent question has a specific answer. Pair with the matching display condition for the parent's data type:

- `displayedWhenYesNo` — when the parent is `yesNo` (`'1'` for Yes, `'0'` for No)

- `displayedWhen` — when the parent is `choice`, `multipleSelection`, or another definition-based type (value is the definition key)

- `displayedWhenCheckbox` — when the parent is `checkbox`

- `displayedWhenTemplate` — when the parent is `template`

- For a scripted alternative, use the metric's own `condition` (an encoded query, evaluated against the assessable record) instead of `dependsOn`/`displayedWhen*` (which key off a sibling metric's answer).

- Publishing validation. When `state` is `'published'` and `evaluationMethod` is `'assessment'`, the plugin validates that at least one category exists and each category has at least one metric. Invalid configurations produce build errors.

- Auto-generated business rules. For `evaluationMethod: 'assessment'`, the plugin creates two `sys_script` business rules on the target `table`: a trigger rule (`when: 'after'`) that runs `AssessmentUtils.checkRecord()` guarded by this assessment's `condition`, and a delete rule (`when: 'before'`) that runs `AssessmentUtils.checkDeleteRecord()` to clean up assessment instances when a source record is deleted. The generated sys_ids are stored in `businessRule` and `deleteBusinessRule` so they round-trip during bi-directional sync — do not set these manually. A third, conditional business rule is also generated when `userField` needs to stay in sync — see #11 below.

- Scoring. Use `scoringType: 'percentage'` (default) or `'allOrNothing'`. Set `weight` on categories and metrics to control relative contribution. Use `scaleFactor` on the assessment type to set the scale — it must be an integer (e.g. `1`, `10`, `100`); floats produce a build error.

- Duration. Use `assessmentDuration: Duration({ days, hours, minutes, seconds })` to set how long an assessment instance stays open. Defaults to `Duration({ days: 14 })`.

- Scheduled assessments. Use `scheduleType: 'scheduled'` with `schedulePeriod` (`'noLimit'`, `'onlyOnce'`, `'weekly'`, `'monthly'`, `'yearly'`, or `'daily'`) to regenerate assessment instances automatically. The plugin creates a `sys_trigger` job and stores its sys_id in `scheduleJob`. Use `'onDemand'` (the default) to create instances only via UI actions or scripts.

- Building/deploying an assessment never assigns it to any records by itself — that's true for both `scheduleType` values. The build only ships the `asmt_metric_type` definition (plus, for a scored assessment, the trigger/delete business rules — see #8). Publishing, generating assessable records, and assigning the assessment to assessors are all separate, on-instance steps — see Generating and Assigning Assessable Records for the full workflow and how it differs between `'onDemand'` and `'scheduled'`.

- Set `userField` when `scheduleType` is `'scheduled'` and you need per-record ownership to stay current. If the assessment is a scored, scheduled assessment (`state: 'published'`) and you set `userField` (e.g. `'assigned_to'` or `'managed_by'`) to identify who's being assessed on each record, the plugin auto-generates a third business rule on `table`: it runs after update, guarded by an advanced condition that only matches when `userField`'s value actually changed, and calls `AssessmentUtils.updateAssessableRecordCategoryUser()` to update the category-user assignment on that record's already-generated assessable records. Without `userField` set (or without all three of scored + scheduled + published), this rule is never created — assessable records keep whatever user they were generated with, even if the record's `userField` value changes later. The generated sys_id is stored in `userFieldBusinessRule` so it round-trips during bi-directional sync — do not set it manually. This is distinct from the initial `userField`-based assignment covered in the linked section above — this rule only keeps an already-assigned record in sync afterward.

- Type-safe field references. `userField` and `filterField` are generic — when you specify `table`, they autocomplete to column names from that table's schema. For example, `table: 'incident'` restricts `userField` to columns like `caller_id`, `assigned_to`, etc.

- Answer collection methods. Use `method` to control how a metric is populated: `assessment` (default) for answers collected during the assessment, `defaultAnswerFromField` or `defaultAnswerFromScript` to pre-populate a default value, and `script` to compute the value entirely. Pair with `sourceField`, `defaultAnswer`, `script`, and `condQuestion` (`always`, `ifFieldEmpty`, `ifScriptEmpty`) as needed.

## Key Concepts

### Assessment vs Survey

Surveys and assessments are two different applications in ServiceNow. Although they may look similar to the respondent, assessments go deeper and are designed for tasks a survey would not seek to achieve.

Use surveys to get user feedback. Surveys usually look at the outputs of a process or system and ask for views on how these are perceived by those being surveyed. They do not examine much detail of what is happening inside the process. If Service Portal is installed, users can access and complete assigned surveys through the My Assessments and Survey widget within the portal.

Common survey use cases include:

- General customer CSAT survey

- Feedback on a task activity, such as when a request is closed

- Public survey for non-ServiceNow users

- Employee onboarding or NPS survey

Use assessments to collect detailed insights and evaluate the results. An assessment allows you to evaluate, score, and rank items, and provide normalized/weighted results. For an assessment to work, it must have an assessable record — for example, Project, Vendors, or Sales — which is not a requirement for surveys.

With assessments, you can collect feedback from a broad base of category users and stakeholders across your organization. You can create a single assessment to get feedback from different cross-functional units — for example, Procurement, Finance, HR, and Legal — by assigning different parts of the assessment to different stakeholders. You can group related metrics into categories and set weights for each response. You can also collect responses and format decision matrices and plot the collected data to report findings.

Common assessment use cases include:

- Vendor assessment

- Demand assessment

- Project assessment

- GRC audit assessment

- Security assessment

- Sales/employee assessment

In summary, surveys are ideal for simple use cases like getting feedback or a CSAT score. Assessments are useful when you need deeper, more insightful feedback to evaluate, rank, and see the normalized score of multiple records together so that you can make decisions faster.

| Aspect | Assessment | Survey |
| `evaluationMethod` | `'assessment'` (default) | `'survey'` |
| Scored | Yes | No |
| Target table | Required ( `table` ) | Not used (managed internally) |
| `scaleFactor` | Required (integer) | Not used |
| Business rule | Auto-generated | Not created |
| Use when | Evaluating records (CIs, vendors, users) | Collecting feedback (NPS, onboarding, employee surveys) |

### Record Hierarchy

```
asmt_metric_type (Assessment/Survey)
├── asmt_metric_category (Category/Section)
│   ├── asmt_metric (Question/Metric)
│   │   └── asmt_metric_definition (Answer Option)
│   └── asmt_metric (Question/Metric)
└── asmt_metric_category (Category/Section)
    └── ...
```

Foreign keys (`metric_type`, `category`, `metric`) are wired automatically from the nesting structure.

### Data Types

| `dataType` | DB value | Widget | Type-specific fields |
| `yesNo` | `boolean` | Yes/No toggle | `correctAnswerYesNo` |
| `numericScale` | `numericscale` | Numeric slider | `min` , `max` , `correctAnswer` |
| `likertScale` | `scale` | Likert scale | `scaleDefinition` ( `low` / `high` ), `definitions` |
| `choice` | `choice` | Radio buttons | `correctAnswerChoice` , `randomizeAnswers` , `definitions` |
| `multipleSelection` | `multiplecheckbox` | Checkboxes | `definitions` |
| `string` | `string` | Text input | `stringOption` ( `singleLine` / `singleLineWide` / `multiline` ) |
| `number` | `long` | Number input | `min` , `max` , `correctAnswer` |
| `date` | `date` | Date picker | — |
| `dateTime` | `datetime` | Date/time picker | — |
| `reference` | `reference` | Reference picker | `referenceTable` |
| `attachment` | `attachment` | File upload | — |
| `checkbox` | `checkbox` | Checkbox | `correctAnswerCheckbox` |
| `ranking` | `ranking` | Drag-to-rank | `definitions` |
| `ratings` | `rating` | Star rating | — |
| `percentage` | `percentage` | Percentage input | `min` , `max` , `correctAnswer` |
| `template` | `template` | Template | `template` , `correctAnswerTemplate` |
| `imageScale` | `imagescale` | Image selection | `definitions` (with `selectedImage` / `unselectedImage` ) |
| `custom` | `custom` | Custom widget | `customMetric` |
| `duration` | `duration` | Duration picker | `duration` |

### Conditional Questions

To make a question appear only when another question has a specific answer:

```
metrics: [
    {
        $id: Now.ID['q-parent'],
        name: 'Do you have a laptop?',
        question: 'Do you have a laptop?',
        dataType: 'yesNo',
        order: 100,
    },
    {
        $id: Now.ID['q-child'],
        name: 'Rate your laptop',
        question: 'Rate your laptop setup experience.',
        dataType: 'likertScale',
        scaleDefinition: 'high',
        order: 200,
        // Only shown when the parent question is answered "Yes"
        dependsOn: Now.ref('asmt_metric', 'q-parent'),
        displayedWhenYesNo: '1',
    },
]
```

### Metric Definitions (Answer Options)

For choice-based and scale data types (`choice`, `multipleSelection`, `likertScale`, `numericScale`, `imageScale`, `ranking`), provide `definitions` keyed by stored value. Use shorthand (string label) or full config:

```
definitions: {
    '1': 'Strongly Disagree',           // shorthand
    '2': 'Disagree',
    '3': { label: 'Neutral', normalizationInput: 50 },  // full config
    '4': 'Agree',
    '5': { label: 'Strongly Agree', normalizationInput: 100 },
}
```

The definition key is written to the `value` field on `asmt_metric_definition`, which is a numeric column on the platform. Use integer keys only; non-numeric strings are rejected by the platform and produce a build diagnostic.

Order defaults to the entry's position (`100`, `200`, …) when omitted. The `metric` FK and coalesce on `(metric, value)` are handled automatically — no `$id` needed on definitions.

Auto-generation for `numericScale`: When a `numericScale` metric has no explicit `definitions`, the plugin automatically generates one `asmt_metric_definition` record per integer from `min` to `max` (matching the platform's behaviour). Each auto-generated definition has `value`, `display`, and `order` all set to the integer value. Provide explicit `definitions` to override this default.

### Metric Display and Behaviour

Common options that apply to most metric data types:

| Property | Purpose |
| `mandatory` | Require an answer. Defaults to `false` . |
| `readOnly` | Render the metric as read-only. Defaults to `false` . |
| `active` | Whether the metric is active. Defaults to `true` . |
| `allowNotApplicable` | Let the assessor mark the metric "not applicable". Defaults to `false` . |
| `allowAdditionalInformation` | Allow free-text additional information alongside the answer. Defaults to `false` . |
| `additionalInformationLabel` | Label for the additional-information field. Defaults to `"Additional Information"` . |
| `hideLabel` | Hide the metric label in the rendered survey. Defaults to `false` . |
| `weight` | Relative contribution to the category score. Defaults to `10` . |
| `order` | Display order within the category. Defaults to `100` . |
| `condition` | Encoded query controlling when the metric applies, evaluated against the assessable record. Use this for record-attribute-based logic (e.g. `priority=1` ); use `dependsOn` / `displayedWhen*` for logic based on a sibling question's answer. |

### Category-Level Overrides

Categories (`asmt_metric_category`) support the same base fields as the top-level assessment, plus:

| Property | Purpose |
| `scoringType` | Override the scoring strategy for this category ( `'percentage'` or `'allOrNothing'` ). |
| `roles` | Roles required to view or take this category. |
| `filter` | Encoded query filtering which records this category applies to (evaluated against the assessable record, same shape as the assessment-level `condition` but scoped to one category). Set this explicitly on every category rather than leaving it blank — an unset `filter` applies the category to every record the assessment covers, which is easy to get wrong silently. |
| `createStakeholders` | Auto-create stakeholder records for this category. Defaults to `false` . |
| `details` | Additional rich-text details shown with the category. |

The `metric_type` and `category` foreign keys are wired automatically from the nesting structure.

### Scorecard & Decision-Matrix Filters (`filterField`)

Assessments ship with a built-in scorecard (`assessment_admin`/`admin` role required). It is opened per assessable record — All > Assessments > Assessable Records, open a record, then Related Links > View Scorecard (admins can also add a UI action / Related Link to view it from other tables). Every rating shown is an average for the selected time range, recalculated each time the scorecard is opened. The scorecard offers several views:

- Averages — compares the record's current ratings in each metric category with the average, minimum, and maximum of all assessable records in the filter, over the trailing twelve months (TTM).

- Categories — bar chart of average ratings per category for the selected interval.

- Category Metrics — weighted average result for each metric within a category.

- Head to Head Compare — compares this record's TTM ratings against another assessable record of the same type.

- History — compares current category ratings against the previous three years or four quarters.

- Live Feed — Live Feed conversations for the assessable record.

The `filter` referenced by the Averages view (the pool of assessable records it compares against, and the filter menu the viewer picks from) is what these top-level fields configure:

| Property | DB field | Purpose |
| `filterField` | `display_field` | The field used to identify filter-menu choices on decision matrices and scorecards. Selecting a value scopes the comparison pool. |
| `filterCondition` | `filter_condition` | Optional encoded query restricting which records appear in the matrix. |
| `defaultMatrixFilter` | `default_filter` | The filter selected by default when the matrix opens. |
| `displayAllFilters` | `display_all_filters` | Show all available filters rather than just the default. |

`filter_table` is wired automatically. The filter table is always the assessment's own `table`, so there is no separate `filterTable` property to set — the plugin populates `filter_table` from `table` (and leaves it empty for surveys). Just set `table`; `filterField` names the column on it.

Segmenting vs ranking. Assessment scores are computed per assessable record (one instance per `table` record), and the scorecard is always viewed from a single assessable record. Setting `filterField` to a column (e.g. `'assignment_group'` on `incident`) adds that field to the scorecard's filter menu, so the Averages view compares a record against the average/min/max of others within the same group. This segments the comparison — it does not produce a leaderboard that ranks every group against each other. For a "rank all assignment groups by average score" dashboard, build a report or Performance Analytics indicator that aggregates the assessment-instance scores grouped by `assignment_group`. `filterField` is not merely a display label (despite mapping to `display_field`) — it drives the filter/comparison scope, not a group ranking.

```
// Enable filtering/comparing scorecard averages within an assignment group.
// filter_table is derived from `table` automatically — no filterTable needed.
Assessment({
    $id: Now.ID['post-resolution-feedback'],
    name: 'Post-Resolution Feedback',
    evaluationMethod: 'assessment',
    table: 'incident',
    scaleFactor: 5,
    filterField: 'assignment_group', // adds assignment group to the scorecard filter menu
    // ...categories/metrics
})
```

## Common Patterns

### Scheduled IT Assessment

```
import { Assessment } from '@servicenow/sdk/core'

Assessment({
    $id: Now.ID['it-security-assessment'],
    name: 'IT Security Risk Assessment',
    evaluationMethod: 'assessment',
    table: 'cmdb_ci_service',
    condition: 'operational_status=1',
    description: 'Evaluates the security posture of IT services.',
    scaleFactor: 10,
    // 'published' + 'scheduled' + userField together auto-generate a third business
    // rule that keeps each service's assessable records reassigned to whoever is
    // currently in managed_by, instead of staying pinned to whoever it was when the
    // assessment was first generated (see instruction #11).
    state: 'published',
    userField: 'managed_by',
    active: true,
    scheduleType: 'scheduled',
    schedulePeriod: 'weekly',
    assessmentDuration: Duration({ days: 14 }),
    categories: [
        {
            $id: Now.ID['cat-access-control'],
            name: 'Access Control',
            weight: 50,
            order: 100,
            // Matches the assessment's own condition above (not narrower, not
            // disjoint) — a filter that excluded these records would leave this
            // category with zero assessable records and block assignment to
            // assessors even after Generate Assessable Records succeeds.
            filter: 'operational_status=1',
            metrics: [
                {
                    $id: Now.ID['q-mfa'],
                    name: 'Multi-factor authentication enabled',
                    question: 'Is MFA enforced for all privileged accounts?',
                    dataType: 'yesNo',
                    weight: 30,
                    order: 100,
                    mandatory: true,
                    correctAnswerYesNo: '1',
                },
                {
                    $id: Now.ID['q-access-review'],
                    name: 'Access review frequency',
                    question: 'How often are user access reviews conducted?',
                    dataType: 'choice',
                    weight: 20,
                    order: 200,
                    mandatory: true,
                    definitions: {
                        '1': { label: 'Monthly', normalizationInput: 100, order: 100 },
                        '2': { label: 'Quarterly', normalizationInput: 75, order: 200 },
                        '3': { label: 'Annually', normalizationInput: 50, order: 300 },
                        '4': { label: 'Never', normalizationInput: 0, order: 400 },
                    },
                },
            ],
        },
    ],
})
```

### Unscored Feedback Survey

```
import { Assessment } from '@servicenow/sdk/core'

Assessment({
    $id: Now.ID['nps-survey'],
    name: 'Customer NPS',
    evaluationMethod: 'survey',
    description: 'Net Promoter Score survey.',
    anonymizeResponses: true,
    categories: [
        {
            $id: Now.ID['nps-cat'],
            name: 'Net Promoter Score',
            metrics: [
                {
                    $id: Now.ID['nps-q'],
                    name: 'How likely are you to recommend us?',
                    question: 'On a scale of 0-10, how likely are you to recommend us?',
                    dataType: 'numericScale',
                    min: 0,
                    max: 10,
                    mandatory: true,
                },
                {
                    $id: Now.ID['nps-comment'],
                    name: 'Additional comments',
                    question: 'Please share any additional feedback.',
                    dataType: 'string',
                    stringOption: 'multiline',
                },
            ],
        },
    ],
})
```

### Multi-Category Employee Onboarding Survey

A survey with multiple categories, conditional follow-up questions, and no scoring

```
import { Assessment } from '@servicenow/sdk/core'

Assessment({
    $id: Now.ID['employee-onboarding-survey'],
    name: 'Employee Onboarding Survey',
    evaluationMethod: 'survey',
    description: 'Collects anonymous feedback on the onboarding experience.',
    anonymizeResponses: true,
    categories: [
        {
            $id: Now.ID['cat-workspace'],
            name: 'Workspace & Tools',
            metrics: [
                {
                    $id: Now.ID['q-laptop-ready'],
                    name: 'Laptop ready on day one',
                    question: 'Was your laptop ready on your first day?',
                    dataType: 'yesNo',
                    mandatory: true,
                },
                {
                    $id: Now.ID['q-laptop-issue'],
                    name: 'Laptop issue details',
                    question: 'Please describe the laptop issue.',
                    dataType: 'string',
                    stringOption: 'multiline',
                    // Only shown when the laptop was not ready
                    dependsOn: Now.ref('asmt_metric', 'q-laptop-ready'),
                    displayedWhenYesNo: '0',
                },
                {
                    $id: Now.ID['q-tools-rating'],
                    name: 'Tools setup rating',
                    question: 'How would you rate the setup of your tools and accounts?',
                    dataType: 'likertScale',
                    scaleDefinition: 'high',
                    order: 200,
                    definitions: {
                        1: 'Very Dissatisfied',
                        2: 'Dissatisfied',
                        3: 'Neutral',
                        4: 'Satisfied',
                        5: 'Very Satisfied',
                    },
                },
            ],
        },
        {
            $id: Now.ID['cat-manager'],
            name: 'Manager & Team',
            metrics: [
                {
                    $id: Now.ID['q-manager-intro'],
                    name: 'Manager introduction',
                    question: 'Did your manager introduce you to the team?',
                    dataType: 'yesNo',
                    mandatory: true,
                },
                {
                    $id: Now.ID['q-onboarding-comments'],
                    name: 'Additional feedback',
                    question: 'Any other feedback about your onboarding experience?',
                    dataType: 'string',
                    stringOption: 'multiline',
                },
            ],
        },
    ],
})
```

### Vendor Assessment with Multiple Data Types

Demonstrates additional data types: `choice`, `multipleSelection`, `number`, `percentage`, `date`, `reference`, `checkbox`, `likertScale` with `definitions`, and `ranking`

```
import { Assessment } from '@servicenow/sdk/core'

Assessment({
    $id: Now.ID['vendor-assessment'],
    name: 'Vendor Security Assessment',
    table: 'core_company',
    condition: 'vendor=true',
    scaleFactor: 100,
    // userField alone doesn't auto-generate the category-user-sync business rule —
    // scheduleType also has to be 'scheduled' (this assessment defaults to 'onDemand')
    // and state has to be 'published' (this one defaults to 'draft'). See instruction #11.
    userField: 'contact',
    categories: [
        {
            $id: Now.ID['cat-security'],
            name: 'Security & Compliance',
            weight: 60,
            order: 100,
            // Matches the assessment's own condition above — see the equivalent
            // comment on the Scheduled IT Assessment example's category filter.
            filter: 'vendor=true',
            metrics: [
                {
                    $id: Now.ID['q-encryption'],
                    name: 'Encryption standard',
                    question: 'Which encryption standard does the vendor use?',
                    dataType: 'choice',
                    weight: 20,
                    order: 100,
                    mandatory: true,
                    definitions: {
                        '1': { label: 'AES-256', normalizationInput: 100 },
                        '2': { label: 'AES-128', normalizationInput: 50 },
                        '3': 'Other',
                    },
                },
                {
                    $id: Now.ID['q-encryption-details'],
                    name: 'Other encryption details',
                    question: 'Please describe the encryption standard used.',
                    dataType: 'string',
                    stringOption: 'multiline',
                    order: 150,
                    // Only shown when option 3 ('Other') is selected on the encryption question
                    dependsOn: Now.ref('asmt_metric', 'q-encryption'),
                    displayedWhen: '3',
                },
                {
                    $id: Now.ID['q-certifications'],
                    name: 'Certifications held',
                    question: 'Which certifications does the vendor hold?',
                    dataType: 'multipleSelection',
                    order: 200,
                    definitions: {
                        '1': 'ISO 27001',
                        '2': 'SOC 2 Type II',
                        '3': 'GDPR Compliant',
                    },
                },
                {
                    $id: Now.ID['q-compliance-rating'],
                    name: 'Compliance confidence',
                    question: "Rate your confidence in the vendor's compliance programme.",
                    dataType: 'likertScale',
                    scaleDefinition: 'high',
                    weight: 15,
                    order: 300,
                    definitions: {
                        1: 'Strongly Disagree',
                        2: 'Disagree',
                        3: 'Neutral',
                        4: 'Agree',
                        5: 'Strongly Agree',
                    },
                },
                {
                    $id: Now.ID['q-priority-ranking'],
                    name: 'Rank improvement areas',
                    question: 'Rank the following areas by improvement priority.',
                    dataType: 'ranking',
                    order: 400,
                    definitions: {
                        '1': 'Access Controls',
                        '2': 'Data Encryption',
                        '3': 'Security Monitoring',
                    },
                },
            ],
        },
        {
            $id: Now.ID['cat-operational'],
            name: 'Operational Details',
            weight: 40,
            order: 200,
            filter: 'vendor=true',
            metrics: [
                {
                    $id: Now.ID['q-security-staff'],
                    name: 'Number of security staff',
                    question: 'How many dedicated security staff does the vendor have?',
                    dataType: 'number',
                    weight: 20,
                    order: 100,
                    min: 0,
                    max: 1000,
                },
                {
                    $id: Now.ID['q-uptime'],
                    name: 'Guaranteed uptime',
                    question: 'What is the guaranteed uptime percentage?',
                    dataType: 'percentage',
                    weight: 20,
                    order: 200,
                    min: 0,
                    max: 100,
                    correctAnswer: 99,
                },
                {
                    $id: Now.ID['q-cert-expiry'],
                    name: 'Certificate expiry date',
                    question: 'When does the security certificate expire?',
                    dataType: 'date',
                    order: 300,
                },
                {
                    $id: Now.ID['q-account-manager'],
                    name: 'Account manager',
                    question: 'Who is the designated account manager?',
                    dataType: 'reference',
                    referenceTable: 'sys_user',
                    order: 400,
                },
                {
                    $id: Now.ID['q-nda-signed'],
                    name: 'NDA signed',
                    question: 'Has the vendor signed an NDA?',
                    dataType: 'checkbox',
                    weight: 10,
                    order: 500,
                    correctAnswerCheckbox: '1',
                },
            ],
        },
    ],
})
```

## Anti-Patterns

- Don't set `metric_type` or `category` manually — these FKs are wired automatically from the nesting.

- Don't create business rules for assessments manually — the plugin auto-generates a trigger and a delete `sys_script` for `evaluationMethod: 'assessment'`. The `businessRule` and `deleteBusinessRule` fields are stored for round-trip; do not set them manually.

- Don't use `$id` on metric definitions — definitions coalesce on `(metric, value)` automatically.

- Don't publish without categories/metrics — the plugin validates published assessments have content.

- Don't use `evaluationMethod: 'assessment'` without `table` — the assessment needs a target table.

- Don't forget `evaluationMethod: 'survey'` for surveys — omitting it defaults to `'assessment'`, which requires `table` and `scaleFactor`.

- Don't use a float for `scaleFactor` — it must be an integer (e.g. `10`, not `10.5`). The plugin emits a build error for non-integer values.

- Don't leave `condition` (assessment) or `filter` (category) unset "by default" — an empty condition/filter silently means every record on `table` is in scope. Always write out the intended scope explicitly, even when that scope is broad (e.g. `condition: 'active=true'`).

## See Also

- Risk Assessment Guide — change risk assessment variant with thresholds

- Assessment API Reference

- RiskAssessment API Reference

- https://docs.servicenow.com/csh?topicname=assessments-landing-page.html&version=latest

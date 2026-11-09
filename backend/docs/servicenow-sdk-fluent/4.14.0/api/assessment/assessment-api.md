Version: 4.14.0

# Assessment

Creates a ServiceNow assessment/survey definition (`asmt_metric_type`) together with its categories (`asmt_metric_category`) and questions/metrics (`asmt_metric`) as a single nested entity. The plugin wires the `metric_type` and `category` foreign keys automatically from the nesting structure, so you never set them by hand.

Choice/union values below are the friendly API values you write in Fluent code; the plugin maps them to the underlying database values (noted per field). For example, `scoringType: 'percentage'` is written to the database as `percent`.

## Parameters

### config

`AssessmentConfig` — the assessment/survey definition (`asmt_metric_type`).

| Property | Required | Type | Description |
| `$id` | yes | `string | number | ExplicitKey<string>` | Fluent record identifier. |
| `name` | yes | `string` | Display name of the assessment/survey. Maps to `name` (max 255). |
| `domain` | no | `string` | Domain sys_id assigned to the assessment and all nested records (categories, metrics, definitions). Use `'global'` for the global domain. Defaults to `'global'` . Maps to `sys_domain` . |
| `domainPath` | no | `string` | Domain path for the assessment and its nested records. Required when `domain` is set to a non-global domain; the platform uses this for domain visibility filtering. Defaults to `'/'` (global domain path). Maps to `sys_domain_path` . |
| `table` | no | `TableName` | The table this assessment is about (the source records being assessed). Maps to `table` . Required when `evaluationMethod` is `'assessment'` (the default); optional for `'survey'` . |
| `description` | no | `string` | Rich-text description of the assessment. Maps to `description` (max 1000). |
| `introduction` | no | `string` | Introduction HTML shown to the assessor before the survey begins. Maps to `introduction` (max 8000). |
| `endNote` | no | `string` | Closing note HTML shown after the survey is submitted. Maps to `end_note` (max 8000). |
| `hideSurveyIntroductionNotes` | no | `boolean` | Suppress the introduction note. Defaults to false. Maps to `not_show_intro_note` . |
| `active` | no | `boolean` | Whether the assessment is active and can be issued. Defaults to true. |
| `sourceTable` | no | `TableName` | Alternate source table used to generate assessable records. Maps to `source_table` . |
| `condition` | no | `string` | Encoded query selecting which records get assessed (max 1000). |
| `scoringType` | no | `'percentage' | 'allOrNothing'` | Strategy used to score responses. Defaults to `percentage` . The plugin maps `percentage` → `percent` , `allOrNothing` → `absolute` . Maps to `scoring_type` . |
| `evaluationMethod` | no | `'assessment' | 'survey'` | Whether this definition behaves as a scored assessment evaluated against `table` records, or as an unscored survey with no target table. Defaults to `assessment` . When `assessment` , `table` and `scaleFactor` are required. Maps to `evaluation_method` . |
| `scaleFactor` | no | `number` | Score scale factor. Required when `evaluationMethod` is `'assessment'` (the default); optional for `'survey'` . Maps to `scale_factor` . |
| `scheduleType` | no | `'scheduled' | 'onDemand'` | Trigger model for generating assessment instances. Defaults to `onDemand` . The plugin maps `'onDemand'` to the backend value `'on_demand'` automatically. Maps to `schedule_type` . |
| `schedulePeriod` | no | `'noLimit' | 'onlyOnce' | 'weekly' | 'monthly' | 'yearly' | 'daily'` | Recurrence period label used with `scheduleType: 'scheduled'` . The plugin maps `noLimit` → `0` , `onlyOnce` → `2` , `weekly` → `3` , `monthly` → `4` , `yearly` → `6` , `daily` → `11` . Maps to `schedule_period` . |
| `assessmentDuration` | no | `Duration | { days?: number, hours?: number, minutes?: number, seconds?: number }` | How long an assessment instance stays open ( `glide_duration` ). Defaults to `Duration({ days: 14 })` ( `'1970-01-15 00:00:00'` ). Maps to `duration` . |
| `allowRetake` | no | `boolean` | Allow assessors to retake the assessment. Defaults to false. Maps to `allow_retake` . |
| `anonymizeResponses` | no | `boolean` | Anonymize responses. Defaults to false. Maps to `anonymize` . |
| `roles` | no | `(string | Role)[]` | Roles required to take the assessment ( `sys_user_role` ). Maps to `roles` . |
| `userField` | no | `string` | Field on the source table identifying the user being assessed. Maps to `user_field` . |
| `filterField` | no | `string` | Field on the filter table (the assessment's own `table` , wired to `filter_table` automatically) used to identify filter-menu choices on decision matrices and scorecards. Selecting a value scopes the pool of assessable records a scorecard's Averages view compares against (avg/min/max over the trailing twelve months) — e.g. `'assignment_group'` on `incident` to filter/compare within a group. It segments the comparison; it does not by itself rank every group. Mandatory in the dictionary. Maps to `display_field` . |
| `returnUrl` | no | `string` | Public URL for anonymous or one-click surveys (max 500). Maps to `url` . |
| `liveFeed` | no | `boolean` | Publish events to the live feed. Defaults to false. Maps to `live_feed` . |
| `chatSurvey` | no | `boolean` | Expose the survey through chat / Virtual Agent. Defaults to false. Maps to `chat_survey` . |
| `oneClickSurvey` | no | `boolean` | Enable one-click survey links. Defaults to false. Maps to `one_click_survey` . |
| `portalPagination` | no | `'category' | 'question' | 'none'` | Portal pagination mode. Defaults to `category` . Maps to `portal_pagination` . |
| `owners` | no | `(string | Record<'sys_user'>)[]` | Survey owners ( `glide_list` to `sys_user` ). Maps to `survey_owners` . |
| `sendNotifications` | no | `boolean` | Notify the assessed user when an instance is created. Defaults to true. Maps to `notify_user` . |
| `notifyIfOverdue` | no | `boolean` | Notify when an assessment instance is overdue. Defaults to false. Maps to `notify_if_overdue` . |
| `assessmentManager` | no | `string | Record<'sys_user'>` | User to notify on overdue instances. Maps to `overdue_notify_user` . |
| `signature` | no | `string | Record<'asmt_signature'>` | Signature definition to require on completion. Maps to `signature` . |
| `enforceCondition` | no | `boolean` | Enforce the condition strictly. Defaults to false. Maps to `enforce_condition` . |
| `displayAllFilters` | no | `boolean` | Show all filters on the assessment. Defaults to false. Maps to `display_all_filters` . |
| `filterCondition` | no | `string` | Filter condition (encoded query, max 1000). Maps to `filter_condition` . |
| `defaultMatrixFilter` | no | `string` | Default filter (encoded query). Maps to `default_filter` . |
| `state` | no | `'draft' | 'published'` | Publish lifecycle state. Defaults to `draft` . Maps to `publish_state` . When `evaluationMethod` is `'assessment'` (the default), publishing requires at least one category, and each category must have at least one metric. |
| `sampleMetric` | no | `string | Record<'asmt_metric'>` | Sample metric used for previews. Maps to `sample_metric` . |
| `allowPublic` | no | `boolean` | Allow the assessment to be taken by public (unauthenticated) users. Defaults to false. Read-only on the platform — set only if your build plugin writes it explicitly. Maps to `allow_public` . |
| `categories` | no | `CategoryConfig[]` | The categories (sections) of the assessment. See categories . |
| `businessRule` | no | `string` | Auto-generated — do not set manually. sys_id of the trigger `sys_script` business rule created for scored assessments. Exposed so the value round-trips during bi-directional sync, preserving the generated rule's sys_id across rebuilds. Maps to `business_rule` . |
| `deleteBusinessRule` | no | `string` | Auto-generated — do not set manually. sys_id of the delete `sys_script` business rule created for scored assessments. Exposed so the value round-trips during bi-directional sync, preserving the generated rule's sys_id across rebuilds. Maps to `delete_business_rule` . |
| `scheduleJob` | no | `string` | Auto-generated — do not set manually. sys_id of the recurring `sys_trigger` job created when `scheduleType` is `'scheduled'` . Exposed so the value round-trips during bi-directional sync, preserving the generated job's sys_id across rebuilds. Maps to `job` . |
| `userFieldBusinessRule` | no | `string` | Auto-generated — do not set manually. sys_id of the business rule that keeps assessable-record category-user assignment in sync with `userField` . Only created for a scored assessment when `scheduleType` is `'scheduled'` , `userField` is set, and `state` is `'published'` . Exposed so the value round-trips during bi-directional sync, preserving the generated rule's sys_id across rebuilds. Maps to `user_field_business_rule` . |

Auto-generated/read-only columns are intentionally not exposed: `user_field_business_rule`, `enable_ui_action`, `disable_ui_action`, and the `sys_*` system fields. `filter_table` is also not exposed — the plugin wires it to the assessment's own `table` automatically (empty for surveys).

`businessRule`, `deleteBusinessRule`, `scheduleJob`, and `userFieldBusinessRule` are exposed (not hidden) even though they are auto-generated. They carry the generated record's sys_id so those values can round-trip during bi-directional sync and remain stable across rebuilds. They should never be set manually in Fluent source.

Auto-generated business rules: When `evaluationMethod` is `'assessment'` (the default), the plugin auto-creates two `sys_script` business rules and links their sys_ids into `businessRule`/`deleteBusinessRule`: a trigger rule on `table` for insert/update (`when: 'after'`) whose script calls `AssessmentUtils.checkRecord()` guarded by `AssessmentUtils.conditionCheck()` against this assessment's own `condition`, and a delete rule (`when: 'before'`) whose script calls `AssessmentUtils.checkDeleteRecord()` to clean up instances when a source record is deleted. Neither is created for `evaluationMethod: 'survey'`.

Auto-generated schedule job requires manual activation: When `scheduleType` is `'scheduled'`, the plugin auto-creates one `sys_trigger` job and links its sys_id into `scheduleJob` (`job`). The job's `script` calls `(new SNC.AssessmentCreation()).createAssessments('<assessment sys_id>')` to regenerate assessment instances on `schedulePeriod`'s cadence. It is created with `state: 0` and no `next_action` — that field is computed by the platform scheduler, not by the build — so it is not active by default: deploying it does not make it start firing. After deploying, open the job under System Scheduler > Scheduled Jobs (or the `sys_trigger` list) and activate/re-save it there before relying on it. Not created when `scheduleType` is `'onDemand'` (the default).

Auto-generated user-field business rule: A third `sys_script` business rule is created on `table`, linked into `userFieldBusinessRule`, only when the assessment is scored, `scheduleType` is `'scheduled'`, `userField` is set, and `state` is `'published'` — all four at once. It runs after update (`order: 300`), gated by an advanced `condition` of `(new global.AssessmentUtils().conditionCheck(current, '<userField>VALCHANGES^EQ'))` so it only fires when `userField`'s value actually changed, and its script calls `AssessmentUtils.updateAssessableRecordCategoryUser(current.getUniqueValue(), '<assessment sys_id>', previous.getValue('<userField>'), current.getValue('<userField>'))` to update the category-user assignment on that record's already-generated assessable records.

### categories

`CategoryConfig[]` — a section within the assessment (`asmt_metric_category`). The `metric_type` foreign key is set automatically from the parent assessment.

| Property | Required | Type | Description |
| `$id` | yes | `string | number | ExplicitKey<string>` | Fluent record identifier. |
| `name` | yes | `string` | Category/section name. Maps to `name` (max 255). |
| `description` | no | `string` | Rich-text description. Maps to `description` (max 1000). |
| `details` | no | `string` | Additional rich-text details. Maps to `details` (max 8000). |
| `weight` | no | `number` | Relative weight of this category in the overall score. Mandatory in the dictionary; defaults to 10. Maps to `weight` . |
| `order` | no | `number` | Display order within the assessment (lower sorts first). Defaults to 1. Maps to `order` . |
| `scoringType` | no | `'percentage' | 'allOrNothing'` | Scoring strategy for this category. Defaults to `percentage` . The plugin maps `percentage` → `percent` , `allOrNothing` → `absolute` . Maps to `scoring_type` . |
| `roles` | no | `(string | Role)[]` | Roles required to view or take this category. Maps to `roles` . |
| `filter` | no | `string` | Encoded query that filters which records this category applies to (max 4000). Maps to `filter` . |
| `createStakeholders` | no | `boolean` | Auto-create stakeholder records for this category. Defaults to false. Maps to `create_stakeholders` . |
| `questionBankEvaluationMethod` | no | `'assessment' | 'survey' | 'quiz' | 'legacyAttestation' | 'attestation' | 'testPlan' | 'riskAssessment' | 'vendorRiskAssessment' | 'rating'` | Evaluation method used when sourcing questions from a question bank. Read-only on the platform. Maps to `qb_evaluation_method` . |
| `table` | no | `TableName` | Table this category's records are drawn from. Read-only on the platform. Maps to `table` . |
| `metrics` | no | `MetricConfig[]` | The questions/metrics in this category, as an array. See metrics . |

Not exposed: `metric_type` (auto-wired FK), `total_metrics` (auto-computed), and `sys_*` system fields.

### metrics

`MetricConfig[]` — the category's questions, as an array. Each `MetricConfig` (an `asmt_metric`) is a discriminated union keyed on `dataType`: only the fields valid for the chosen `dataType` are available, and required-per-type fields (e.g. `referenceTable` for `dataType: 'reference'`) are enforced at compile time. The `metric_type` and `category` foreign keys are set automatically from the nesting.

To make one question depend on another, set `dependsOn` to a reference to the sibling, e.g. `Now.ref('asmt_metric', 'q-laptop')`; the plugin resolves it to the target metric's sys_id.

The table below lists every field. Type-specific fields (`stringOption`, `scaleDefinition`, `referenceTable`, `correctAnswerChoice`, `randomizeAnswers`, `correctAnswerCheckbox`, `correctAnswerYesNo`, `template`, `correctAnswerTemplate`, `duration`, `customMetric`, and `min`/`max`/`correctAnswer`) are only available on their matching `dataType` branch.

| Property | Required | Type | Description |
| `$id` | yes | `string | number | ExplicitKey<string>` | Fluent record identifier. |
| `name` | yes | `string` | The question label shown to the assessor. Maps to `name` (max 255). |
| `question` | yes | `string` | Rich-text question body. Mandatory in the dictionary. Maps to `question` (max 512). |
| `description` | no | `string` | Help/description text for the question. Maps to `description` (max 1000). |
| `details` | no | `string` | Additional rich-text details about the metric. Maps to `details` (max 8000). |
| `dataType` | yes | `'attachment' | 'checkbox' | 'choice' | 'custom' | 'date' | 'dateTime' | 'duration' | 'imageScale' | 'likertScale' | 'multipleSelection' | 'number' | 'numericScale' | 'percentage' | 'ranking' | 'ratings' | 'reference' | 'string' | 'template' | 'yesNo'` | The answer data type, which drives the rendered answer widget and is the discriminant for the metric union (the available fields depend on this value). Friendly values map to the backend `datatype` (e.g. `yesNo` → `boolean` , `number` → `long` , `likertScale` → `scale` , `numericScale` → `numericscale` , `dateTime` → `datetime` , `imageScale` → `imagescale` , `multipleSelection` → `multiplecheckbox` , `ratings` → `rating` ). |
| `scored` | no | `boolean` | Whether the metric contributes to the assessment score. Defaults to false. Maps to `scored` . |
| `weight` | no | `number` | Relative weight of this metric within its category. Mandatory in the dictionary; defaults to 10. Maps to `weight` . |
| `order` | no | `number` | Display order within the category (lower sorts first). Mandatory in the dictionary; defaults to 100. Maps to `order` . |
| `mandatory` | no | `boolean` | Whether an answer is required. Defaults to false. Maps to `mandatory` . |
| `readOnly` | no | `boolean` | Render the metric as read-only. Defaults to false. Maps to `read_only` . |
| `active` | no | `boolean` | Whether the metric is active. Defaults to true. Maps to `active` . |
| `scaleDefinition` | no | `'low' | 'high'` | Likert scale direction (for `dataType: 'likertScale'` ). Mandatory in the dictionary; defaults to `high` . Maps to `scale` . |
| `min` | no | `number` | Minimum numeric value. Mandatory in the dictionary; defaults to 0. Maps to `min` . |
| `max` | no | `number` | Maximum numeric value. Mandatory in the dictionary; defaults to 10. Maps to `max` . |
| `correctAnswer` | no | `number` | Expected correct answer for scored numeric questions. Maps to `correct_answer` . |
| `correctAnswerChoice` | no | `string | string[]` | Correct answer for `dataType: 'choice'` ( `glide_list` to `asmt_metric_definition` ). Maps to `correct_answer_choice` . |
| `correctAnswerTemplate` | no | `string | string[]` | Correct answer for `dataType: 'template'` ( `glide_list` to `asmt_template_definition` ). Maps to `correct_answer_template` . |
| `correctAnswerYesNo` | no | `string` | Correct answer for `dataType: 'yesNo'` (Yes/No). Maps to `correct_answer_yesno` . |
| `correctAnswerCheckbox` | no | `string` | Correct answer for `dataType: 'checkbox'` . Maps to `correct_answer_checkbox` . |
| `allowNotApplicable` | no | `boolean` | Allow the assessor to mark the metric "not applicable". Defaults to false. Maps to `allow_not_applicable` . |
| `allowAdditionalInformation` | no | `boolean` | Allow free-text additional information alongside the answer. Defaults to false. Maps to `allow_add_info` . |
| `additionalInformationLabel` | no | `string` | Label for the additional-information field. Defaults to "Additional Information". Maps to `add_info_label` . |
| `randomizeAnswers` | no | `boolean` | Randomize the order of answer choices. Defaults to false. Maps to `randomize_answers` . |
| `hideLabel` | no | `boolean` | Hide the metric label in the rendered survey. Defaults to false. Maps to `hide_label` . |
| `dependentPlugin` | no | `'Software Asset Management' | 'Core' | 'CMDB' | 'Procurement' | 'Cost Management' | 'Asset Management'` | Dependent plugin value. The plugin maps these labels to backend values like `com.snc.core` , `com.snc.cmdb` , etc. Maps to `plugin` . |
| `dependsOn` | no | `string | Now.ref('asmt_metric', ...) | Record<'asmt_metric'>` | Conditional question: the sibling metric this one depends on. Reference it with `Now.ref('asmt_metric', '<id-or-sys_id>')` , a `Record<'asmt_metric'>` , or a raw sys_id; the plugin resolves it to the target's sys_id. Maps to `depends_on` . |
| `condQuestion` | no | `'ifFieldEmpty' | 'ifScriptEmpty' | 'always'` | When the dependent/default question is asked. Defaults to `always` . The plugin maps `ifFieldEmpty` → `emptyfield` , `ifScriptEmpty` → `emptyscript` . Maps to `cond_question` . |
| `displayedWhen` | no | `string | string[]` | The dependent answer value(s) that reveal this metric (used with `dependsOn` ), as a `glide_list` to `asmt_metric_definition` . Maps to `displayed_when` . |
| `displayedWhenYesNo` | no | `string` | Reveal value when the parent metric is Yes/No. Maps to `displayed_when_yesno` . |
| `displayedWhenCheckbox` | no | `string` | Reveal value when the parent metric is a checkbox. Maps to `displayed_when_checkbox` . |
| `displayedWhenTemplate` | no | `string | string[]` | Reveal value when the parent metric is a template ( `glide_list` to `asmt_template_definition` ). Maps to `displayed_when_template` . |
| `condition` | no | `string` | Encoded query controlling when the metric applies (max 1000). Maps to `condition` . |
| `referenceTable` | no | `TableName` | Target table for a `reference` dataType metric. Maps to `reference_table` . |
| `sourceField` | no | `string` | Field the metric reads from (data-collection metrics). Maps to `source_field` . |
| `template` | no | `string | Record<'asmt_template'>` | Assessment template backing this metric. Maps to `template` . |
| `script` | no | `string` | Server script for scripted metrics (max 4000). Prefer `Now.include('./metric.js')` . Maps to `script` . |
| `defaultAnswer` | no | `string` | Field on the source record used to pre-populate the default answer. Maps to `default_value_field` . |
| `duration` | no | `string` | Duration value for duration-type metrics ( `glide_duration` ). Maps to `duration` . |
| `method` | no | `'assessment' | 'defaultAnswerFromField' | 'defaultAnswerFromScript' | 'script'` | Collection method for the metric. Defaults to `assessment` . The plugin maps `defaultAnswerFromField` → `condfield` , `defaultAnswerFromScript` → `condscript` . Maps to `method` . |
| `stringOption` | no | `'singleLine' | 'singleLineWide' | 'multiline'` | Rendering style for string-answer metrics. Defaults to `singleLine` . The plugin maps `singleLine` → `short` , `singleLineWide` → `wide` . Maps to `string_option` . |
| `fieldValidation` | no | `string | Record<'sys_cs_field_script_validator'>` | Field script validator applied to the answer. Maps to `field_validation` . |
| `maximumNormalizationInput` | no | `boolean` | Use the maximum value as the normalization input. Defaults to false. Maps to `maximum_normalization_input` . |
| `valueParameters` | no | `string` | Name/value parameters for the metric ( `simple_name_values` , max 4000). Maps to `value_parameters` . |
| `context` | no | `string | Record<'sys_cs_virtual_agent_context'>` | Virtual Agent context for chat-based surveys. Maps to `context` . |
| `customMetric` | no | `string | Record<'asmt_custom_metric'>` | Custom metric definition backing this metric. Maps to `custom_metric` . |
| `maxWeight` | no | `number` | Maximum weight used when normalizing scores. Defaults to `0` . Maps to `max_weight` . |
| `definitions` | no | `{ [value: string]: string | MetricDefinitionConfig }` | Answer options / scale points ( `asmt_metric_definition` ), keyed by the option's stored `value` . Each entry is a display label (shorthand) or a config object. Applicable to `choice` , `likertScale` , `numericScale` , `imageScale` , `multipleSelection` , and `ranking` . See definitions . |

Not exposed: `metric_type` (auto-wired FK), `auto_gen` and `plugin` (internal), and `sys_*` system fields.

### definitions

`{ [value: string]: string | MetricDefinitionConfig }` — the metric's answer options / scale points (`asmt_metric_definition`), keyed by each option's stored `value`. The value is either a display label string (shorthand) or a `MetricDefinitionConfig` object. The `metric` foreign key is wired automatically and each row coalesces on `(metric, value)`, so no `$id` is needed. When `order` is omitted it defaults to the entry's position (`100`, `200`, …).

The `asmt_metric_definition.value` column is numeric on the platform, so definition keys must be integer strings. Non-integer keys produce a build diagnostic.

| Property | Required | Type | Description |
| `label` | yes | `string` | Display label shown to the assessor. Maps to `display` . |
| `order` | no | `number` | Display order (lower sorts first). Defaults to the entry's position. Maps to `order` . |
| `normalizationInput` | no | `number` | Score normalization input. Maps to `normalization_input` . |
| `selectedImage` | no | `string` | Image shown when this option is selected (for `dataType: 'imageScale'` ). Maps to `selected_image` . |
| `unselectedImage` | no | `string` | Image shown when this option is not selected (for `dataType: 'imageScale'` ). Maps to `unselected_image` . |

```
// shorthand (value -> label) and full config object can be mixed
definitions: {
    1: 'Initial',
    2: 'Repeatable',
    5: { label: 'Optimizing', normalizationInput: 100 },
}
```

Auto-generation for `numericScale`: When a `numericScale` metric has no explicit `definitions`, the plugin automatically generates one `asmt_metric_definition` record per integer from `min` to `max` (matching the platform's behaviour). Each auto-generated definition has `value`, `display`, and `order` all set to the integer value. Provide explicit `definitions` to override this default.

## See

- RiskAssessment — change risk assessment variant

- Assessment Guide — Generating and Assigning Assessable Records — publishing, generating assessable records, and assigning to assessors

- https://docs.servicenow.com/csh?topicname=assessments-landing-page.html&version=latest

## Examples

### Scored Onboarding Survey

Create an assessment with two categories and a conditional follow-up question

```
/**
 * @title Scored Onboarding Survey
 * @description Create an assessment with two categories and a conditional follow-up question
 */
import { Assessment } from '@servicenow/sdk/core'
Assessment({
    $id: Now.ID['onboarding-survey'],
    name: 'New Hire Onboarding Survey',
    table: 'sys_user',
    description: 'Collects feedback on the onboarding experience.',
    active: true,
    scoringType: 'percentage',
    anonymizeResponses: true,
    roles: ['hr_admin'],
    categories: [
        {
            $id: Now.ID['cat-setup'],
            name: 'Workspace Setup',
            weight: 50,
            order: 100,
            // `metrics` is an array. To make a follow-up question depend on another,
            // reference the sibling via `Now.ref('asmt_metric', '<id>')` — the plugin
            // resolves it to the target metric's sys_id.
            metrics: [
                {
                    $id: Now.ID['q-laptop'],
                    name: 'Did you receive your laptop on day one?',
                    question: 'Did you receive your laptop on day one?',
                    dataType: 'yesNo',
                    scored: false,
                    weight: 10,
                    order: 100,
                    mandatory: true,
                },
                {
                    $id: Now.ID['q-setup-rating'],
                    name: 'Rate the ease of workspace setup',
                    question: 'Rate the ease of workspace setup',
                    dataType: 'likertScale',
                    scaleDefinition: 'high',
                    scored: false,
                    weight: 20,
                    order: 200,
                    dependsOn: Now.ref('asmt_metric', 'q-laptop'),
                    displayedWhenYesNo: '0',
                    definitions: {
                        1: 'Strongly Disagree',
                        2: 'Disagree',
                        3: 'Neutral',
                        4: 'Agree',
                        5: 'Strongly Agree',
                    },
                },
            ],
        },
        {
            $id: Now.ID['cat-feedback'],
            name: 'Open Feedback',
            weight: 50,
            order: 200,
            metrics: [
                {
                    $id: Now.ID['q-comments'],
                    name: 'Any additional comments?',
                    question: 'Any additional comments?',
                    dataType: 'string',
                    stringOption: 'multiline',
                    scored: false,
                },
            ],
        },
    ],
})
```

### Vendor Assessment with Multiple Data Types

Demonstrates additional data types: `choice` with `definitions`, `multipleSelection`, `number`, `date`, `reference`, `checkbox`, and `percentage`

```
/**
 * @title Vendor Assessment with Multiple Data Types
 * @description Shows choice, multipleSelection, number, date, reference, checkbox, and percentage metrics
 */
import { Assessment } from '@servicenow/sdk/core'
Assessment({
    $id: Now.ID['vendor-data-types'],
    name: 'Vendor Data-Type Showcase',
    table: 'core_company',
    scaleFactor: 100,
    categories: [
        {
            $id: Now.ID['cat-vendor-info'],
            name: 'Vendor Information',
            weight: 100,
            order: 100,
            metrics: [
                {
                    $id: Now.ID['q-encryption'],
                    name: 'Encryption standard',
                    question: 'Which encryption standard does the vendor use?',
                    dataType: 'choice',
                    scored: false,
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
                    $id: Now.ID['q-regions'],
                    name: 'Data residency regions',
                    question: 'In which regions does the vendor store data?',
                    dataType: 'multipleSelection',
                    order: 200,
                    definitions: {
                        '1': 'European Union',
                        '2': 'United States',
                        '3': 'Asia Pacific',
                    },
                },
                {
                    $id: Now.ID['q-employees'],
                    name: 'Number of security staff',
                    question: 'How many dedicated security staff does the vendor have?',
                    dataType: 'number',
                    scored: false,
                    weight: 20,
                    order: 300,
                    min: 0,
                    max: 1000,
                },
                {
                    $id: Now.ID['q-cert-expiry'],
                    name: 'Certificate expiry date',
                    question: 'When does the security certificate expire?',
                    dataType: 'date',
                    order: 400,
                },
                {
                    $id: Now.ID['q-account-manager'],
                    name: 'Account manager',
                    question: 'Who is the designated account manager?',
                    dataType: 'reference',
                    referenceTable: 'sys_user',
                    order: 500,
                },
                {
                    $id: Now.ID['q-nda-signed'],
                    name: 'NDA signed',
                    question: 'Has the vendor signed an NDA?',
                    dataType: 'checkbox',
                    scored: false,
                    weight: 10,
                    order: 600,
                    correctAnswerCheckbox: '1',
                },
                {
                    $id: Now.ID['q-uptime'],
                    name: 'Guaranteed uptime',
                    question: 'What is the guaranteed uptime percentage?',
                    dataType: 'percentage',
                    scored: false,
                    weight: 20,
                    order: 700,
                    min: 0,
                    max: 100,
                    correctAnswer: 99,
                },
            ],
        },
    ],
})
```

### Minimal Survey

Create a simple single-category survey with one question

```
/**
 * @title Minimal Survey
 * @description Create a simple single-category survey with one question
 */
import { Assessment } from '@servicenow/sdk/core'
Assessment({
    $id: Now.ID['nps-survey'],
    name: 'Customer NPS',
    table: 'customer_account',
    categories: [
        {
            $id: Now.ID['nps-cat'],
            name: 'Net Promoter Score',
            metrics: [
                {
                    $id: Now.ID['nps-q'],
                    name: 'How likely are you to recommend us?',
                    question: 'How likely are you to recommend us?',
                    dataType: 'numericScale',
                    min: 0,
                    max: 10,
                    scored: false,
                },
            ],
        },
    ],
})
```

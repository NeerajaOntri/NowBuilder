Version: 4.14.0

# RiskAssessment

Creates a ServiceNow change risk assessment definition (`change_risk_asmt`) together with its risk thresholds (`change_risk_asmt_threshold`), categories (`asmt_metric_category`), and questions/metrics (`asmt_metric`) as a single nested entity. The plugin wires the `metric_type`, `category`, and `assessment` foreign keys automatically from the nesting structure.

`change_risk_asmt` extends `asmt_metric_type`. The plugin hardcodes `table` to `'change_request'` and `evaluation_method` to `'risk_assessment'` — these values are not configurable by the user.

Choice/union values below are the friendly API values you write in Fluent code; the plugin maps them to the underlying database values (noted per field). For example, `scoringType: 'percentage'` is written to the database as `percent`.

## Parameters

### config

`RiskAssessmentConfig` — the change risk assessment definition (`change_risk_asmt`).

| Property | Required | Type | Description |
| `$id` | yes | `string | number | ExplicitKey<string>` | Fluent record identifier. |
| `name` | yes | `string` | Display name of the risk assessment. Maps to `name` (max 255). |
| `domain` | no | `string` | Domain sys_id assigned to the assessment and its nested records (categories, metrics, definitions). Thresholds do not inherit domain. Use `'global'` for the global domain. Defaults to `'global'` . Maps to `sys_domain` . |
| `domainPath` | no | `string` | Domain path for the assessment and its nested records (categories, metrics, definitions). Required when `domain` is set to a non-global domain; the platform uses this for domain visibility filtering. Defaults to `'/'` (global domain path). Maps to `sys_domain_path` . |
| `description` | no | `string` | Rich-text description of the assessment. Maps to `description` (max 1000). |
| `introduction` | no | `string` | Introduction HTML shown before the assessment begins. Maps to `introduction` (max 8000). |
| `endNote` | no | `string` | Closing note HTML shown after submission. Maps to `end_note` (max 8000). |
| `hideSurveyIntroductionNotes` | no | `boolean` | Suppress the introduction note. Defaults to `false` . Maps to `not_show_intro_note` . |
| `active` | no | `boolean` | Whether the assessment is active. Defaults to `true` . |
| `sourceTable` | no | `TableName` | Alternate source table. Maps to `source_table` . |
| `condition` | no | `string` | Encoded query selecting which change requests get assessed (max 1000). |
| `scoringType` | no | `'percentage' | 'allOrNothing'` | Scoring strategy. Defaults to `percentage` . The plugin maps `percentage` → `percent` , `allOrNothing` → `absolute` . Maps to `scoring_type` . |
| `scaleFactor` | no | `number` | Score scale factor. Defaults to `0` . Maps to `scale_factor` . |
| `scheduleType` | no | `'scheduled' | 'onDemand'` | Trigger model. Defaults to `onDemand` . Maps to `schedule_type` . |
| `schedulePeriod` | no | `'noLimit' | 'onlyOnce' | 'weekly' | 'monthly' | 'yearly' | 'daily'` | Recurrence period. Maps to `schedule_period` . |
| `assessmentDuration` | no | `{ days?: number, hours?: number, minutes?: number, seconds?: number }` | How long the assessment stays open. Defaults to 14 days. Maps to `duration` . |
| `allowRetake` | no | `boolean` | Allow retaking. Defaults to `false` . Maps to `allow_retake` . |
| `anonymizeResponses` | no | `boolean` | Anonymize responses. Defaults to `false` . Maps to `anonymize` . |
| `roles` | no | `(string | Role)[]` | Roles required to take the assessment. Maps to `roles` . |
| `userField` | no | `string` | Field identifying the assessed user. Maps to `user_field` . |
| `filterField` | no | `string` | Field on the filter table used for decision-matrix filter-menu choices and scorecard-average grouping. Maps to `display_field` . |
| `returnUrl` | no | `string` | URL for anonymous surveys (max 500). Maps to `url` . |
| `liveFeed` | no | `boolean` | Publish to live feed. Defaults to `false` . Maps to `live_feed` . |
| `chatSurvey` | no | `boolean` | Expose via Virtual Agent. Defaults to `false` . Maps to `chat_survey` . |
| `oneClickSurvey` | no | `boolean` | Enable one-click links. Defaults to `false` . Maps to `one_click_survey` . |
| `portalPagination` | no | `'category' | 'question' | 'none'` | Portal pagination mode. Defaults to `category` . Maps to `portal_pagination` . |
| `owners` | no | `(string | Record<'sys_user'>)[]` | Assessment owners. Maps to `survey_owners` . |
| `sendNotifications` | no | `boolean` | Notify on instance creation. Defaults to `true` . Maps to `notify_user` . |
| `notifyIfOverdue` | no | `boolean` | Notify on overdue. Defaults to `false` . Maps to `notify_if_overdue` . |
| `assessmentManager` | no | `string | Record<'sys_user'>` | Overdue notification user. Maps to `overdue_notify_user` . |
| `signature` | no | `string | Record<'asmt_signature'>` | Signature definition. Maps to `signature` . |
| `enforceCondition` | no | `boolean` | Enforce condition strictly. Defaults to `false` . Maps to `enforce_condition` . |
| `displayAllFilters` | no | `boolean` | Show all filters. Defaults to `false` . Maps to `display_all_filters` . |
| `filterCondition` | no | `string` | Filter condition (max 1000). Maps to `filter_condition` . |
| `defaultMatrixFilter` | no | `string` | Default filter (encoded query). Maps to `default_filter` . |
| `state` | no | `'draft' | 'published'` | Publish state. Defaults to `draft` . Maps to `publish_state` . Publishing requires at least one category with at least one metric. |
| `sampleMetric` | no | `string | Record<'asmt_metric'>` | Sample metric for previews. Maps to `sample_metric` . |
| `allowPublic` | no | `boolean` | Allow public users. Defaults to `false` . Maps to `allow_public` . |
| `thresholds` | no | `RiskThresholdConfig[]` | Risk thresholds mapping score ranges to risk levels. See thresholds . |
| `categories` | no | `CategoryConfig[]` | Categories/sections of the assessment. See categories . |

Hardcoded fields: `table` is always `change_request` and `evaluation_method` is always `risk_assessment`. These are not configurable.

No auto-generated business rule: Unlike `Assessment`, the `RiskAssessment` plugin does not auto-create a `sys_script` business rule.

### thresholds

`RiskThresholdConfig[]` — risk threshold rows (`change_risk_asmt_threshold`). Each threshold maps a minimum score to a risk level. The `assessment` foreign key is wired automatically from the parent risk assessment. Each threshold is identified by its own `$id` (there is no coalesce key — multiple rows with the same risk/score combination are allowed).

| Property | Required | Type | Description |
| `$id` | yes | `string | number | ExplicitKey<string>` | Fluent record identifier. Each threshold must have a unique `$id` . |
| `risk` | yes | `'high' | 'moderate' | 'low'` | Risk level label. Maps to `risk` (choice). |
| `scoreGreaterThan` | yes | `number` | Minimum score that triggers this risk level. Maps to `score_greater_than` (integer). |

### categories

Same as Assessment → categories. The `table` on each category is always set to `change_request` by the plugin.

### metrics

Same as Assessment → metrics.

### definitions

Same as Assessment → definitions.

## See

- Assessment — base assessment/survey variant

- https://docs.servicenow.com/csh?topicname=change-risk-assessment.html&version=latest

## Examples

### Change Risk Assessment with Thresholds

Create a risk assessment with three threshold levels and two question categories

```
/**
 * @title Change Risk Assessment
 * @description Evaluate change requests to determine the associated risk level
 */
import { RiskAssessment } from '@servicenow/sdk/core'
RiskAssessment({
    $id: Now.ID['change-risk-assessment'],
    name: 'Change Risk Assessment',
    description: 'Evaluates change requests to determine the associated risk level.',
    active: true,
    scaleFactor: 10,
    state: 'draft',
    thresholds: [
        { $id: Now.ID['threshold-high'], risk: 'high', scoreGreaterThan: 70 },
        { $id: Now.ID['threshold-moderate'], risk: 'moderate', scoreGreaterThan: 30 },
        { $id: Now.ID['threshold-low'], risk: 'low', scoreGreaterThan: 0 },
    ],
    categories: [
        {
            $id: Now.ID['cat-change-impact'],
            name: 'Change Impact',
            description: 'Assess the scope and impact of the proposed change.',
            weight: 60,
            order: 100,
            metrics: [
                {
                    $id: Now.ID['q-affected-cis'],
                    name: 'Number of affected CIs',
                    question: 'How many configuration items are affected by this change?',
                    dataType: 'numericScale',
                    scored: false,
                    weight: 30,
                    order: 100,
                    mandatory: true,
                    min: 1,
                    max: 5,
                },
                {
                    $id: Now.ID['q-downtime-required'],
                    name: 'Downtime required',
                    question: 'Does this change require downtime for any production services?',
                    dataType: 'yesNo',
                    scored: false,
                    weight: 40,
                    order: 200,
                    mandatory: true,
                    correctAnswerYesNo: '0',
                },
                {
                    $id: Now.ID['q-rollback-plan'],
                    name: 'Rollback plan exists',
                    question: 'Is there a documented rollback plan for this change?',
                    dataType: 'yesNo',
                    scored: false,
                    weight: 30,
                    order: 300,
                    mandatory: true,
                    correctAnswerYesNo: '1',
                },
            ],
        },
        {
            $id: Now.ID['cat-change-readiness'],
            name: 'Change Readiness',
            description: 'Evaluate the preparedness and testing of the change.',
            weight: 40,
            order: 200,
            metrics: [
                {
                    $id: Now.ID['q-testing-completed'],
                    name: 'Testing completed',
                    question: 'Has the change been tested in a non-production environment?',
                    dataType: 'yesNo',
                    scored: false,
                    weight: 50,
                    order: 100,
                    mandatory: true,
                    correctAnswerYesNo: '1',
                },
                {
                    $id: Now.ID['q-change-complexity'],
                    name: 'Change complexity',
                    question: 'Rate the overall complexity of this change.',
                    dataType: 'numericScale',
                    scored: false,
                    weight: 50,
                    order: 200,
                    mandatory: true,
                    min: 1,
                    max: 5,
                    correctAnswer: 2,
                },
            ],
        },
    ],
})
```

### Minimal Risk Assessment

Create a risk assessment with thresholds only (no categories)

```
/**
 * @title Minimal Risk Assessment
 * @description A minimal risk assessment with just thresholds
 */
import { RiskAssessment } from '@servicenow/sdk/core'
RiskAssessment({
    $id: Now.ID['simple-risk'],
    name: 'Simple Change Risk',
    thresholds: [
        { $id: Now.ID['t-high'], risk: 'high', scoreGreaterThan: 80 },
        { $id: Now.ID['t-moderate'], risk: 'moderate', scoreGreaterThan: 40 },
        { $id: Now.ID['t-low'], risk: 'low', scoreGreaterThan: 0 },
    ],
})
```

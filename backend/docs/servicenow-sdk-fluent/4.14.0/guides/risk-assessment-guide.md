Version: 4.14.0

# Change Risk Assessment Guide

Guide for creating ServiceNow Change Risk Assessments (`change_risk_asmt`) using the Fluent API. A risk assessment evaluates change requests to determine a risk level (high, moderate, or low) based on scored questions and configurable thresholds.

`change_risk_asmt` extends `asmt_metric_type`. The plugin hardcodes `evaluation_method` to `risk_assessment` (not configurable) and defaults `table` to `change_request`. `table` is inherited from the base assessment type; change risk assessments are intended to target `change_request`.

For general assessments and surveys, see assessment-guide.md.

## Prerequisites

### Plugin Gate (HARD STOP)

Critical — hard requirement: `RiskAssessment` writes to `change_risk_asmt` and `change_risk_asmt_threshold`, and these tables only exist when the `com.snc.change_management.risk_assessment` plugin (Change Management - Risk Assessment) is active on the target instance. On a base instance without this plugin the tables are absent, so:

Check:

- Query the instance for table `sys_plugins` where `source=com.snc.change_management.risk_assessment`, retrieving field `active`.

Result evaluation:

| Result | Action |
| ✅ Plugin found and active ( `records` non-empty with `active` = `true` ) | Proceed to Instructions |
| 🛑 Plugin not found ( `records` empty), or found but not active | HARD STOP — do not continue with risk assessment creation. Inform the user that the `com.snc.change_management.risk_assessment` plugin (Change Management - Risk Assessment) is not active on this instance and must be activated before proceeding. Once the plugin is active, then build and install. |

You can also confirm in the platform UI: All → System Definition → Plugins, search for Change Management - Risk Assessment, and activate it if it is not already active.

## When to Use

- Creating a change risk assessment to evaluate risk levels of change requests

- Defining risk thresholds that map score ranges to risk levels (high, moderate, low)

- Scoring change requests based on impact, complexity, readiness, and other risk factors

## Instructions

- Only `name` is required. All other fields are optional or have sensible defaults.

- `evaluation_method` is hardcoded; `table` defaults to `change_request`. The plugin always writes `evaluation_method` as `risk_assessment`. `table` defaults to `change_request` and is inherited from the base assessment type, but change risk assessments are intended to target `change_request` — avoid overriding it.

- Define thresholds with `$id`. Each threshold maps a minimum score to a risk level. Thresholds are identified by `$id` (not coalesced) — multiple thresholds with the same risk/score combination are allowed.

- No auto-generated business rule. Unlike `Assessment`, the `RiskAssessment` plugin does not create `sys_script` business rules. The inherited `businessRule` and `deleteBusinessRule` fields are preserved for round-trip during bi-directional sync — do not set them manually.

- Categories and metrics work the same as Assessment. Use categories to group questions, and metrics for individual questions. See assessment-guide.md for details on data types, conditional questions, and definitions.

- `condition` (top-level) is an encoded query restricting which `change_request` records get evaluated at all — e.g. `type=emergency` to only risk-assess emergency changes. Since there's no auto-generated business rule (see #4), the plugin writes it straight to the `change_risk_asmt.condition` column instead of gating a trigger script.

- `filter` on a category is an encoded query restricting which change requests that specific category applies to, letting different sections of the assessment apply to different subsets of changes.

- `condition` on a metric restricts when that individual question applies, based on attributes of the change request being assessed (as opposed to `dependsOn`/`displayedWhen*`, which key off a sibling question's answer).

- Always set `condition` explicitly, even when you intend to cover every change request (e.g. `'active=true'`), and set every category's `filter` explicitly too, kept consistent with (a subset of, not disjoint from) that `condition`. Unlike a scored `Assessment`, `RiskAssessment` has no manual "generate assessable records" step to re-run — the platform's Change Management process creates assessable records automatically. So an unset or mismatched `condition`/`filter` doesn't just widen scope: it means that automatic process has nothing to create for a given change request or category, and the Risk Assessment button on that change request shows blank for that section with no separate step available to fix it after the fact (see Post-Deployment Steps to Verify below).

- Publishing validation. The plugin validates `publish_state` — publishing requires at least one category with at least one metric.

- `scaleFactor` must be an integer and defaults to `0`. Use whole numbers like `1`, `10`, or `100`. Floats produce a build error.

## Key Concepts

### How Risk Thresholds Work

Thresholds define the cutoff scores for each risk level. The platform evaluates thresholds from highest `scoreGreaterThan` to lowest — the first threshold whose minimum score is met determines the risk level.

| Threshold | `risk` | `scoreGreaterThan` | Meaning |
| High | `high` | 70 | Score > 70 → high risk |
| Moderate | `moderate` | 30 | Score > 30 → moderate risk |
| Low | `low` | 0 | Score > 0 → low risk |

### Record Hierarchy

```
change_risk_asmt (Risk Assessment)
├── change_risk_asmt_threshold (Threshold)
├── change_risk_asmt_threshold (Threshold)
├── change_risk_asmt_threshold (Threshold)
├── asmt_metric_category (Category/Section)
│   ├── asmt_metric (Question/Metric)
│   │   └── asmt_metric_definition (Answer Option)
│   └── asmt_metric (Question/Metric)
└── asmt_metric_category (Category/Section)
    └── ...
```

Foreign keys are wired automatically:

- `assessment` on thresholds → parent risk assessment

- `metric_type` on categories → parent risk assessment

- `category` on metrics → parent category

- `metric` on definitions → parent metric

### RiskAssessment vs Assessment

| Aspect | RiskAssessment | Assessment |
| Table | `change_risk_asmt` | `asmt_metric_type` |
| Target table | Defaults to `change_request` | Configurable via `table` |
| Evaluation method | Always `risk_assessment` (not a writable property) | `assessment` or `survey` |
| Thresholds | Yes ( `change_risk_asmt_threshold` ) | No |
| Business rule | Not created | Auto-generated for assessments |
| Threshold identity | `$id` (no coalesce) | N/A |

### Post-Deployment Steps to Verify

Unlike a scored `Assessment`, a `RiskAssessment` does not need you to manually generate assessable records — the platform's Change Management process creates them automatically as a change request moves through its workflow. After deployment, open a `change_request` record and click its Risk Assessment related button/UI action to verify what actually shows up:

- Shows the risk assessment's heading, but the details/categories underneath are blank → an assessable record exists for this change request (so the heading renders), but nothing displays underneath. Before assuming the deployment is broken, check, in order:

- Does `condition` (top-level) actually match this change request, and does every category's `filter` also match it — kept consistent with `condition` rather than narrower/disjoint from it (see instruction #5)?

- Does at least one metric category have at least one assessable record associated with it for this change request?

- Has the category's assigned user been made a stakeholder by being associated with at least one assessable record from that metric category?

- If a domain plugin is installed, is at least one assessable record visible to that user in its domain?

- Shows a different risk assessment than the one you deployed → likely an ordering/precedence issue, not a `condition`/`filter` issue. When more than one `change_risk_asmt` definition can apply to the same change request, the platform picks one to display based on the risk assessments' relative ordering/priority on the instance. Check that ordering rather than assuming your deployment didn't take effect. This ordering isn't currently exposed through `RiskAssessmentConfig` in Fluent, so it has to be verified/adjusted directly on the instance.

## Common Patterns

### Full Risk Assessment with Thresholds and Questions

```
import { RiskAssessment } from '@servicenow/sdk/core'

RiskAssessment({
    $id: Now.ID['change-risk-assessment'],
    name: 'Change Risk Assessment',
    description: 'Evaluates change requests to determine the associated risk level.',
    active: true,
    scaleFactor: 10,
    state: 'draft',
    // Always set explicitly, even to cover every change request — an unset
    // condition means every change_request insert/update is in scope, and a
    // category filter that ends up disjoint from it silently leaves that
    // category with zero assessable records (see instruction #5).
    condition: 'active=true',
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
            // Matches the assessment's own condition above (not narrower, not
            // disjoint) — see the comment on `condition` above.
            filter: 'active=true',
            metrics: [
                {
                    $id: Now.ID['q-affected-cis'],
                    name: 'Number of affected CIs',
                    question: 'How many configuration items are affected by this change?',
                    dataType: 'numericScale',
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
            filter: 'active=true',
            metrics: [
                {
                    $id: Now.ID['q-testing-completed'],
                    name: 'Testing completed',
                    question: 'Has the change been tested in a non-production environment?',
                    dataType: 'yesNo',
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
                    weight: 20,
                    order: 200,
                    mandatory: true,
                    min: 1,
                    max: 5,
                    correctAnswer: 2,
                },
                {
                    $id: Now.ID['q-change-type'],
                    name: 'Change type',
                    question: 'What type of change is being implemented?',
                    dataType: 'choice',
                    weight: 15,
                    order: 300,
                    mandatory: true,
                    definitions: {
                        '1': { label: 'Standard', normalizationInput: 0 },
                        '2': { label: 'Normal', normalizationInput: 50 },
                        '3': { label: 'Emergency', normalizationInput: 100 },
                    },
                },
                {
                    $id: Now.ID['q-approval-confidence'],
                    name: 'Approval confidence',
                    question: 'Rate your confidence in the change approval process.',
                    dataType: 'likertScale',
                    scaleDefinition: 'high',
                    weight: 15,
                    order: 400,
                    definitions: {
                        1: 'Very Low',
                        2: 'Low',
                        3: 'Moderate',
                        4: 'High',
                        5: 'Very High',
                    },
                },
            ],
        },
    ],
})
```

### Minimal Risk Assessment (Thresholds Only)

```
import { RiskAssessment } from '@servicenow/sdk/core'

RiskAssessment({
    $id: Now.ID['simple-risk'],
    name: 'Simple Change Risk',
    // Always set explicitly, even with no categories yet — see instruction #5.
    condition: 'active=true',
    thresholds: [
        { $id: Now.ID['t-high'], risk: 'high', scoreGreaterThan: 80 },
        { $id: Now.ID['t-moderate'], risk: 'moderate', scoreGreaterThan: 40 },
        { $id: Now.ID['t-low'], risk: 'low', scoreGreaterThan: 0 },
    ],
})
```

## Anti-Patterns

- Don't set `evaluationMethod` on `RiskAssessment`. `RiskAssessmentConfig` does not expose `evaluationMethod`; the plugin always writes `risk_assessment`. Don't override `table`; it defaults to `change_request` and change risk assessments are intended to target that table.

- Don't create a business rule manually — the risk assessment plugin does not create `sys_script` business rules.

- Don't set `businessRule` or `deleteBusinessRule` manually — these are inherited round-trip fields, not generated by the risk assessment plugin.

- Don't omit `$id` on thresholds — thresholds have no coalesce key and require explicit identification.

- Don't publish without categories/metrics — the plugin validates published assessments have content.

- Don't use `Assessment()` for risk assessments — use `RiskAssessment()` which maps to `change_risk_asmt`.

- Don't use a float for `scaleFactor` — it must be an integer (e.g. `10`, not `10.5`).

- Don't leave `condition` (top-level) or `filter` (category) unset "by default" — an empty `condition` means every `change_request` insert/update is in scope, and a category `filter` left unset or inconsistent with `condition` can leave that category with zero assessable records, blocking assignment even after assessable records are otherwise generated (see instruction #5).

## See Also

- Assessment Guide — general assessments and surveys

- Assessment API Reference

- RiskAssessment API Reference

- https://docs.servicenow.com/csh?topicname=change-risk-assessment.html&version=latest

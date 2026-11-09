# Flow designs as ServiceNow Fluent source

`backend/app/ai/flow_sdk.py` turns a flow row (record + numbered steps) into ServiceNow Fluent source
following the Flow API reference (`backend/docs/servicenow-australia/application-development/servicenow-sdk/fluent-flow-api.md`):

```typescript
import { action, Flow, wfa, trigger } from '@servicenow/sdk/automation';
export const p1_escalation = Flow({ $id: Now.ID["p1_escalation"], name: "P1 Escalation", description: "...", runAs: 'system' },
    wfa.trigger(trigger.record.created, { $id: Now.ID["p1_escalation_trigger"] }, { table: "incident", condition: "priority=1" }),
    (params) => {
        const step1 = wfa.action(action.core.lookUpRecord, { $id: ... }, { table: "sys_user_group", conditions: `sys_id=${wfa.dataPill(params.trigger.current.assignment_group, 'reference')}` });
        wfa.flowLogic.if({ $id: ..., condition: `${wfa.dataPill(step1.Record.manager, 'reference')}ISNOTEMPTY` }, () => { ... });
        wfa.flowLogic.else({ $id: ... }, () => { ... });
    });
```

- Action names, input names and types come from `data/flow_catalog.json`, read out of
  `@servicenow/sdk-core` (regenerate with `tools/build_flow_catalog.py`). Unknown actions or inputs,
  missing mandatory inputs, and unsupported triggers or logic **fail closed** with the reason shown on
  the card (`export_report`).
- Data pills: `{{trigger.current.<field>}}`, `{{step<n>.<Output>}}`, `{{item.<field>}}` (inside For
  Each). `{{plan.<row id>}}` is replaced by another plan row's deployed sys_id before export.
- Nesting: `inside: <step>` places a step in an If / Else If / Else / For Each body.
- Values are escaped so a design can't inject code into the source (`tests/test_flow_sdk_export.py`
  runs `node --check` on the output).

`backend/app/services/sdk_deploy.py` writes the source to the configured SDK project, runs
`now-sdk build` and `now-sdk install`, and `read_back_flow` confirms the flow in `sys_hub_flow`. Setup:
`SDK_DEPLOYMENT_SETUP.md`.

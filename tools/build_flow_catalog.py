"""Turns the raw dump into nowBuilder's flow catalogue, keyed by Flow Designer display name."""
import json, pathlib, re

raw = json.loads(pathlib.Path("catalog_raw.json").read_text())

TRIGGER_API = {
    "created-trigger": "trigger.record.created",
    "created-or-updated-trigger": "trigger.record.createdOrUpdated",
    "updated-trigger": "trigger.record.updated",
    "daily-trigger": "trigger.scheduled.daily",
    "monthly-trigger": "trigger.scheduled.monthly",
    "repeat-trigger": "trigger.scheduled.repeat",
    "run-once-trigger": "trigger.scheduled.runOnce",
    "weekly-trigger": "trigger.scheduled.weekly",
    "inbound-email-trigger": "trigger.application.inboundEmail",
    "knowledge-management-trigger": "trigger.application.knowledgeManagement",
    "remote-table-query-trigger": "trigger.application.remoteTableQuery",
    "service-catalog-trigger": "trigger.application.serviceCatalog",
    "sla-task-trigger": "trigger.application.slaTask",
}

# wfa.flow_logic's fixed set. Display names are what Flow Designer shows in the step list.
LOGIC = {
    "If": "if", "Else If": "elseIf", "Else": "else", "For Each": "forEach",
    "Try": "tryCatch", "Catch": "tryCatch", "Wait For A Duration": "waitForADuration",
    "Exit Loop": "exitLoop", "End Flow": "endFlow", "Skip Iteration": "skipIteration",
    "Do The Following In Parallel": "doInParallel", "Set Flow Variables": "setFlowVariables",
    "Append To Flow Variables": "appendToFlowVariables",
    "Assign Subflow Outputs": "assignSubflowOutputs", "Do The Following Until": "doTheFollowingUntil",
}


def tidy(io):
    out = {}
    for k, v in (io or {}).items():
        f = {"label": v.get("label"), "type": v.get("type"), "mandatory": v.get("mandatory", False)}
        if v.get("reference"):
            f["reference"] = v["reference"]
        if v.get("choices"):
            f["choices"] = sorted(v["choices"])
        if v.get("dependent"):
            f["dependent"] = v["dependent"]
        out[k] = f
    return out


actions = {}
for key, d in raw["action"].items():
    actions[d["name"]] = {"api": f"action.core.{key}", "sys_id": d["sys_id"],
                          "description": re.sub(r"<[^>]+>", " ", d.get("description") or "").strip()[:300],
                          "inputs": tidy(d.get("inputs")), "outputs": tidy(d.get("outputs"))}

triggers = {}
for key, d in raw["trigger"].items():
    api = TRIGGER_API.get(key)
    if not api:
        raise SystemExit(f"No API name mapped for trigger {key}")
    triggers[d["name"]] = {"api": api, "sys_id": d["sys_id"], "inputs": tidy(d.get("inputs"))}

out = {
    "note": ("The Flow Designer vocabulary the ServiceNow SDK (Fluent) can express, read out of "
             "@servicenow/sdk-core's own built-in definitions. Keyed by the display name Flow Designer "
             "shows, which is also what sys_hub_action_type_definition.name holds. Regenerate with "
             "tools/build_flow_catalog.py when the SDK is upgraded."),
    "sdk_version": "4.14.0",
    "actions": dict(sorted(actions.items())),
    "triggers": dict(sorted(triggers.items())),
    "logic": dict(sorted(LOGIC.items())),
}
pathlib.Path("flow_catalog.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
print("actions", len(actions), "triggers", len(triggers), "logic", len(LOGIC))

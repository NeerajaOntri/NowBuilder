# Example: client script

**Request:** (the client half of "show the caller's open incident count")

```json
{"record": {"name": "Show caller open incident count", "table": "incident", "type": "onChange",
            "field_name": "caller_id", "ui_type": "10", "active": "true", "isolate_script": "true",
            "description": "Asks CallerIncidentCount for the caller's open incidents."},
 "script": "function onChange(control, oldValue, newValue, isLoading, isTemplate) {\n    if (isLoading || newValue === '') {\n        return;\n    }\n    var ga = new GlideAjax('CallerIncidentCount');\n    ga.addParam('sysparm_name', 'getOpenCount');\n    ga.addParam('sysparm_caller', newValue);\n    ga.getXMLAnswer(function (answer) {\n        g_form.hideFieldMsg('caller_id', true);\n        g_form.showFieldMsg('caller_id', getMessage('Open incidents for this caller: ') + answer, 'info');\n    });\n}"}
```

**Request:** "Warn before saving a P1 incident without an assignment group" (onSubmit, no server call):

```json
{"record": {"name": "Confirm P1 without group", "table": "incident", "type": "onSubmit", "field_name": "",
            "ui_type": "10", "active": "true", "isolate_script": "true",
            "description": "Asks for confirmation when a P1 has no assignment group."},
 "script": "function onSubmit() {\n    if (g_form.getValue('priority') == '1' && g_form.getValue('assignment_group') === '') {\n        return confirm(getMessage('This P1 incident has no assignment group. Save anyway?'));\n    }\n    return true;\n}"}
```

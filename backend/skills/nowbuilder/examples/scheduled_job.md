# Example: scheduled job

**Request:** "Every night at 1 AM, close incidents that have been Resolved for more than 7 days."

```json
{"record": {"name": "Close incidents resolved over 7 days", "run_type": "daily", "run_time": "01:00:00",
            "run_dayofweek": "", "run_dayofmonth": "", "run_period": "", "active": "true"},
 "script": "(function () {\n    var days = parseInt(gs.getProperty('incident.autoclose.days', '7'), 10);\n    var gr = new GlideRecord('incident');\n    gr.addQuery('state', 6);\n    gr.addQuery('resolved_at', '<', gs.daysAgoStart(days));\n    gr.setLimit(500);\n    gr.query();\n    var closed = 0;\n    while (gr.next()) {\n        gr.setValue('state', 7);\n        gr.update();\n        closed++;\n    }\n    gs.info('Close resolved incidents: {0} closed', closed);\n})();"}
```

Patterns: wrap the script in an IIFE; limit the rows per run (`setLimit`) so a backlog is worked off
over several runs; read thresholds from a system property (plan the property as its own row);
log a one-line summary. `run_type` weekly needs `run_dayofweek` (1 Monday … 7 Sunday), monthly needs
`run_dayofmonth`, periodically needs `run_period` (HH:MM:SS).

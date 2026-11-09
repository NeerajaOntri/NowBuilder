# Example: script include (+ the client script that calls it)

**Request:** "When the caller changes on an incident, show how many open incidents they have."

Script include (client-callable):
```json
{"record": {"name": "CallerIncidentCount", "api_name": "", "client_callable": "true", "access": "public",
            "active": "true", "description": "GlideAjax: open incident count for a caller."},
 "script": "var CallerIncidentCount = Class.create();\nCallerIncidentCount.prototype = Object.extendsObject(global.AbstractAjaxProcessor, {\n    getOpenCount: function () {\n        var callerId = this.getParameter('sysparm_caller');\n        if (!callerId || !gs.hasRole('itil')) {\n            return '0';\n        }\n        var ga = new GlideAggregate('incident');\n        ga.addQuery('caller_id', callerId);\n        ga.addActiveQuery();\n        ga.addAggregate('COUNT');\n        ga.query();\n        return ga.next() ? ga.getAggregate('COUNT') : '0';\n    },\n    isPublic: function () {\n        return false;\n    },\n    type: 'CallerIncidentCount'\n});"}
```

Server-only include (called from business rules or flows):
```json
{"record": {"name": "IncidentUtils", "api_name": "", "client_callable": "false", "access": "public",
            "active": "true", "description": "Shared incident helpers."},
 "script": "var IncidentUtils = Class.create();\nIncidentUtils.prototype = {\n    initialize: function () {},\n    openCountForGroup: function (groupId) {\n        var ga = new GlideAggregate('incident');\n        ga.addQuery('assignment_group', groupId);\n        ga.addActiveQuery();\n        ga.addAggregate('COUNT');\n        ga.query();\n        return ga.next() ? parseInt(ga.getAggregate('COUNT'), 10) : 0;\n    },\n    type: 'IncidentUtils'\n};"}
```

Assumption to add to the plan for any client-callable include: "Non-admin users need an ACL on
CallerIncidentCount (Access Controls related link, role itil) - add it as security_admin."

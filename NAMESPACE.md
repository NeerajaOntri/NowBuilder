# nowBuilder namespace

nowBuilder is ServiceNow only. MetaFlow (Salesforce) is a separate product. Nothing from Salesforce is
kept here, and new code uses the ServiceNow names below.

## Words

| Use this (ServiceNow) | Never this (Salesforce / MetaFlow) |
|---|---|
| instance (`Instance`, `instance_id`, `instances`) | org, `SalesforceOrg`, `org_id` |
| instance type: Development / Test / Production | org type: Developer / Sandbox / Production |
| table (`incident`, `task`, `u_my_table`) | object (`Account`, `My_Object__c`) |
| field / dictionary entry (`sys_dictionary`) | custom field (`__c`) |
| artifact: business rule, script include, client script, UI policy, UI action | component: Apex class, trigger, LWC, flow, layout, profile |
| record in a table (`sys_script`, `sys_script_include`, …) | metadata file under `force-app/` |
| Table API `/api/now/table/<table>` | Metadata API, Tooling API, SOQL |
| encoded query (`active=true^collection=incident`) | SOQL `WHERE` |
| update set (`sys_update_set`) | deployment / package.xml |
| ATF (Automated Test Framework) | Apex tests, code coverage |
| GlideRecord, GlideAjax, `gs`, `g_form`, `current`, `previous` | Apex, SOQL, Lightning |
| ES5 (ES2021 only in scoped apps that turn it on) | Apex syntax |
| Application Registry OAuth client | Connected App |
| PDI (Personal Developer Instance) | Developer Edition / scratch org |
| `NOWBUILDER_*` settings | `METAFLOW_*` settings |

## Where ServiceNow things live

| What | Where |
|---|---|
| Sign-in, Table API client, reading the instance | `backend/app/services/servicenow.py` (`ServiceNowClient`, `ARTIFACT_TABLES`) |
| Instance connections API | `backend/app/routers/instances.py` → `/api/instances` |
| Instance model | `backend/app/models.py` → `Instance` (table `instances`) |
| AI tools the chat uses | `backend/app/ai/tools.py` → `get_table_schema`, `search_instance_artifacts`, `get_instance_artifact` |
| AI prompts (nowBuilder's own rules) | `backend/skills/nowbuilder/*.md` |
| ServiceNow knowledge (26 skills, never edited) | `backend/skills/vendor/servicenow-skills/` |
| Which skills go with which artifact | `backend/skills/manifest.json` → `artifactTypes` |
| Git layout for pushed work (Chunk 4) | `servicenow/<table>/<name>.js` (script) and `.json` (the record's other fields), `backend/app/services/github.py` |
| Fake instance for tests | `backend/tests/fake_snow.py` |
| Frontend: instances | `frontend/src/instances.jsx` (context), `pages/InstancesSettingsPage.jsx`, switcher in `components/AppShell.jsx` |
| CSS for instance cards and the switcher | `inst-*` classes in `frontend/src/styles.css` |

## Artifact types (first scope)

| type key | Table | Name field | Table field |
|---|---|---|---|
| `business_rule` | `sys_script` | `name` | `collection` |
| `script_include` | `sys_script_include` | `name` | (none) |
| `client_script` | `sys_script_client` | `name` | `table` |
| `ui_policy` | `sys_ui_policy` | `short_description` | `table` |
| `ui_action` | `sys_ui_action` | `name` | `table` |

New types (ACLs, scheduled jobs, scripted REST, flows, catalog items) are added in three places: `ARTIFACT_TABLES`
in `servicenow.py`, `artifactTypes` in `manifest.json` (with their skills), and the `enum` in `ai/skills.py`'s tool definitions.

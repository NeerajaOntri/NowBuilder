# nowBuilder

AI-powered ServiceNow development that works like Now Assist for creators: describe what you need in
a chat (or attach a BRD, or pick a Jira story) and nowBuilder reads your connected ServiceNow
instance, plans the artifacts, writes and checks each one, and **deploys them into the instance**.

Works with any instance you connect in Settings → ServiceNow instances; the one selected at the top of the page is the one it reads and deploys to. Nothing in `.env` needs changing to switch instances.

## What happens when you type a prompt

```
prompt ──► read the instance ──► plan (one row per artifact) ──► write each record + script
       ──► check against the instance (fields, tables, actions, script rules) ──► fix once with AI
       ──► deploy: Table API into a new update set  +  flows with the ServiceNow SDK
       ──► read every record back ──► reply with what is live, with links
```

| Artifact | Table | How it reaches the instance |
|---|---|---|
| Business rule | `sys_script` | Table API, update set |
| Script include | `sys_script_include` | Table API, update set |
| Client script | `sys_script_client` | Table API, update set |
| UI policy (+ field actions) | `sys_ui_policy`, `sys_ui_policy_action` | Table API, update set |
| UI action | `sys_ui_action` | Table API, update set |
| Notification | `sysevent_email_action` | Table API, update set |
| Data policy (+ field rules) | `sys_data_policy2`, `sys_data_policy_rule` | Table API, update set |
| Scheduled job | `sysauto_script` | Table API, update set |
| System property | `sys_properties` | Table API, update set |
| Event registration | `sysevent_register` | Table API, update set |
| Script action | `sysevent_script_action` | Table API, update set |
| Table | `sys_db_object` | Table API, update set |
| Field (+ choice values) | `sys_dictionary`, `sys_choice` | Table API, update set |
| Flow | `sys_hub_flow` | ServiceNow SDK (Fluent) into the scoped app "nowBuilder Automation" (`setup-flows.ps1` once) |

Nothing reaches the instance until you click: on the plan card choose the rows, click **Approve**, then
**Deploy** (Production asks for a confirmation as well). The chat never deploys on its own, even when the
prompt says "deploy it". Table API rows go into a new update set named `nowBuilder - <plan title>`,
which is left as the connected user's **current update set** (refresh ServiceNow and it shows in the
globe / update set picker; set `NOWBUILDER_KEEP_UPDATE_SET_CURRENT=false` to put the previous one back).
Flows install with the ServiceNow SDK. Each record is read back before it is reported as deployed; if a
row didn't go in (for example the SDK was still setting up), the button becomes **Deploy the remaining
N** and finishes it. **Check again** re-runs the checks against the instance. Roll back from the plan
card (flows installed by the SDK stay installed; deactivate them in Flow Designer).

nowBuilder doesn't build form/list layouts, ACLs, Scripted REST APIs, catalog items, portal widgets,
ATF tests, import sets, reports, Virtual Agent topics or data (users, groups, CIs): for those it explains
exactly what to create, and still plans and deploys every part it can.

## Run locally (Windows)

Step by step, with troubleshooting: **`START_HERE.md`**. In short (Python 3.12/3.13 and Node.js 20+ installed):

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1            # once
powershell -ExecutionPolicy Bypass -File .\start-backend.ps1    # terminal 1
powershell -ExecutionPolicy Bypass -File .\start-frontend.ps1   # terminal 2 -> http://localhost:5173
# in the app: sign up, Settings -> AI provider, Settings -> ServiceNow instances -> Connect
powershell -ExecutionPolicy Bypass -File .\setup-flows.ps1      # once, for flow deployment
```

Tests: `cd backend; .venv\Scripts\python -m pytest` (ServiceNow and the AI are faked: `tests/fake_snow.py`).

## Try these prompts

- "When a P1 incident is created, email the assignment group and the caller."
- "Make Subcategory mandatory on incident when Category is Hardware."
- "Add an *Escalate* button on the incident form for itil users that sets priority to 1 and adds a work note."
- "Create a script include that returns the number of open incidents for a group, callable from a client script, and an onChange client script on incident.assignment_group that shows it."
- "Create a flow: when a P1 incident is created, look up the assignment group, and if it has a manager, add a work note; otherwise log it." (needs Node.js 20+ on the backend machine)
- "Create a table to track vendor contracts with vendor, contract value, start and end dates, and a status of draft, active or expired."
- "Show me 10 open incidents with number, priority and short description."

## Connecting an instance

- **Username and password** (basic auth): the address and a user with the **admin** role.
- **OAuth client**: create one under **System OAuth → Application Registry → Create an OAuth API
  endpoint for external clients**, then enter its client ID and secret with the username and password.

The connected user needs to create the artifacts, create `sys_update_set` records, change its own
`sys_user_preference` (current update set) and read `sys_update_xml` (`GET
/api/instances/{id}/deployment-readiness` checks the reads). A developer instance hibernates when idle;
wake it at developer.servicenow.com.

## Layout

| Folder | What |
|---|---|
| `backend/` | Python 3.12+, FastAPI, SQLAlchemy (SQLite for dev, Postgres hosted), httpx (Table API), any AI provider |
| `backend/skills/` | `nowbuilder/*.md` (rules), `nowbuilder/examples/` (a checked worked example per artifact type), `vendor/servicenow-skills/` (32 ServiceNow topic skills), `manifest.json` |
| `backend/docs/` | Bundled ServiceNow documentation (Australia release) the AI can search offline |
| `backend/app/services/auto_deploy.py` | Prompt-to-instance delivery: fix once, deploy, flows via SDK, report |
| `backend/app/ai/flow_sdk.py` | Flow design → ServiceNow Fluent source |
| `frontend/` | React 18, JavaScript (JSX), Vite |

## What "trained" means here

The AI provider's model isn't fine-tuned. nowBuilder grounds it on every turn: the skill files in
`backend/skills/` (rules, ServiceNow best practice, exact record fields), the bundled ServiceNow
documentation, and - most important - what it reads from your instance. To change how it behaves,
edit the skill files (the tests in `tests/test_prompt_contract.py` guard the parts the product needs).

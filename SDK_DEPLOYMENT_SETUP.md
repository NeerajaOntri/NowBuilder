# Deploying flows (ServiceNow SDK) - automatic

Business rules, script includes, client scripts, UI policies, UI actions and notifications deploy
through the Table API into an update set. **Flows** can't (a flow is spread over several `sys_hub_*`
tables plus a compiled snapshot), so nowBuilder writes each flow as ServiceNow Fluent code and
installs it with the official ServiceNow SDK into a scoped application on your instance.

**You don't set up the SDK yourself.** The backend does it the first time a flow is deployed.

## What you need

1. **Node.js 20 or later** on the computer that runs the backend. You already use npm for the
   frontend; check with `node -v`. If it's lower than v20, install the LTS from https://nodejs.org
   and restart VS Code.
2. **Internet access** from that computer (the first flow downloads `@servicenow/sdk` 4.14.0 from npm).
3. The instance connected in Settings → ServiceNow instances with **Username and password**
   (an admin user, no multi-factor sign-in). nowBuilder uses that same sign-in for the SDK.

That's all. Leave `NOWBUILDER_SDK_AUTO_SETUP=true` in `backend/.env`.

## Do the one-time setup now (recommended)

After you've connected the instance in the app, run this once in a terminal and watch it finish:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-flows.ps1          # from the project folder
# or: cd backend; .\.venv\Scripts\python -m app.sdk_setup
```

It prints every step:
1. creates the scoped app project in `backend\data\sdk\<instance>_service_now_com\` (one per connected instance) (scope
   `x_<your vendor prefix>_nbuild`, read from the instance's `glide.appcreator.company.code`),
2. `npm install` - downloads `@servicenow/sdk` 4.14.0 (the slow part: a few minutes, sometimes 10+
   on a slow connection),
3. `now-sdk auth --add ... --password-stdin` - stores the SDK sign-in from your saved connection
   (in `backend\data\sdk\credentials`; the password never goes on the command line).

It then runs a harmless SDK command (`now-sdk auth --list`) to prove the SDK actually loads. Only
then is the project marked ready (`.nowbuilder-ready`). If a module is missing (for example
`Cannot find module 'lodash/noop'` from a half-finished download) it installs that package, or
deletes `node_modules` and installs again. Only one setup runs at a time (a lock file), so the
background setup and this command never write the same folder together.

When it says **Ready**, flows deploy from the chat in about a minute.

You don't have to run it: connecting (or *Check connection*) starts the same setup in the background,
and its output goes to `backend\data\sdk\setup_<instance>_service_now_com.log`. If a flow is deployed
before that finishes, the card shows **SDK setting up**. Say **deploy it** in the chat when the log
shows it's done.

## What happens for each flow

The flow is written to `src\fluent\nowbuilder_<flow_name>.now.ts`, then `now-sdk build` and
`now-sdk install --auth <alias>` run (flows are activated on install), and the flow is read back from
`sys_hub_flow`. The card shows **Deployed, active** with a link, or the SDK's own error.

## Check it's ready

Start the backend, sign in, open http://localhost:8000/docs → `GET /api/sdk/readiness`.
`"node": "v22..."` and `"ready_for_local_build": true` mean flows will deploy. If `node` is null,
install Node.js and restart the backend.

## If a flow fails

The card shows the SDK's own error. Common ones:

| Error says | Do this |
|---|---|
| Node.js isn't installed | Install Node.js 20+, restart the backend |
| `auth --add` failed / 401 | Update the instance sign-in in Settings; the user must not need MFA |
| vendor prefix couldn't be read | Add `NOWBUILDER_SDK_SCOPE=x_<prefix>_nbuild` to `backend/.env` (prefix: System Properties → `glide.appcreator.company.code`) |
| scope already exists / conflict | Set `NOWBUILDER_SDK_SCOPE` to a new name (max 18 characters) |
| `Cannot find module ...` | `setup-flows.ps1 -Reset` (deletes the SDK download and installs it again), then "deploy it" |
| `npm install` failed / didn't finish | Run `python -m app.sdk_setup` to see the npm output; check internet / proxy (`npm config get proxy`), then run it again |
| build error about an action input | Use Fix with AI on the row, then "deploy it" in the chat |

To start the SDK setup over: `powershell -ExecutionPolicy Bypass -File .\setup-flows.ps1 -Reset`.

## Optional settings (`backend/.env`)

```
NOWBUILDER_SDK_AUTO_SETUP=true          # false = flows are designs only
NOWBUILDER_SDK_SCOPE=                   # force a scope name (x_<prefix>_...)
NOWBUILDER_SDK_PROJECT_DIR=             # use your own `now-sdk init` project instead
NOWBUILDER_SDK_INSTANCE_URL=             # optional: only install into this one instance (empty = any connected instance)
NOWBUILDER_SDK_ACTIVATE_FLOWS=true      # false = install flows inactive
NOWBUILDER_SDK_WAIT_SECONDS=300         # how long a chat deploy waits for a setup in progress
NOWBUILDER_SDK_SETUP_TIMEOUT=3600       # limit for one setup step (npm install)
```

## Notes

- Flows install into the scoped app, not into the `nowBuilder - …` update set the Table API rows go into.
- Rolling a plan back removes Table API records. To remove a flow, deactivate or delete it in Flow
  Designer.
- What the exporter supports: Created / Updated / Created or Updated / Daily / Service Catalog /
  Inbound Email / SLA Task triggers; every core action (Look Up Record(s), Create / Update / Delete
  Record, Create Task, Ask For Approval, Send Notification, Send Email, Log, …); If / Else If / Else /
  For Each / End Flow. Spoke actions, subflows, Try/Catch, parallel blocks and Weekly / Monthly /
  Repeat schedules stay "Build by hand".

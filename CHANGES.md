# Changes (Nov 2026)

## Instance and delivery
- Works with any instance you connect; no instance is configured in `.env`. Nothing else about the instance is hard-coded: user, scope and
  vendor prefix come from the connection and the instance itself.
- **Prompt → plan → you click Deploy** (Now Assist-style): a prompt becomes a checked plan; nothing is
  deployed until the user clicks **Approve**, then **Deploy** on the plan card. Table API rows go into a
  new update set `nowBuilder - <title>` that stays the user's current update set (visible in the globe
  picker after a refresh), flows install with the ServiceNow SDK, everything is read back.
  **Deploy the remaining N** finishes rows that didn't go in. Never Production without confirmation.
  (`NOWBUILDER_AUTO_DEPLOY=true` brings back deploying from the chat; off by default.)
- **Check again** shows what it found, and plans left "busy" by a stopped backend are released.
- Design documents (HR/BRD use cases) are mapped section by section onto the plan
  (`skills/nowbuilder/design-documents.md`); a "changes" trigger condition must use the Updated trigger
  (checked before deploy).

- **One application per plan** (from the request or design document: "Application: Global", a
  scope name). Before writing, nowBuilder makes it the user's current application and creates the
  update set in it; each record's `sys_scope` is read back. Flows of a Global plan install into a Global
  SDK application ("nowBuilder Global"); if the instance can't take one (needs Australia+), the flow
  goes into nowBuilder's scoped app and the card says why. An earlier scoped copy of the same flow is
  deactivated so nothing runs twice. Flows into someone else's scoped app are refused by the check.
- `python -m app.sdk_probe` writes `data/sdk_probe.md` from `now-sdk explain` (local, read-only), to add
  Wait / Do the following until from the SDK's own documentation.

- **Loops inside the flow** (from the official Fluent SDK 4.14 docs): "Do the following until"
  (`wfa.flowLogic.doTheFollowing` + `until`) and "Wait for a duration" (`waitForADuration`,
  `Duration({...})`) are written into the flow itself; no business-rule / event workaround.
- **Send Email body with record values, no manual step**: the Fluent action API says `ah_body` takes no data
  pills, and an inline script there fails at run time ("fd_data is not defined"). The trigger record's
  pills are written the way Flow Designer stores a pill in an input value (`{{trigger.current.<field>}}`),
  so the flow resolves them when it runs; an SDK that refuses that gets [placeholders] automatically
  (`NOWBUILDER_FLOW_BODY_PILLS=placeholders` forces them).
- **Loop exit conditions**: `pill IN a,b` becomes `pill=a^ORpill=b` (the instance rejects IN after a pill).
- **Asks first, like Now Assist**: the application (Global or which app, with the user's current one
  offered) and anything a wrong guess would get wrong, as 2-3 numbered questions with defaults; cites
  the Fluent / ServiceNow docs it used.
- **Global flows: Global → nowBuilder Global application → scoped app**, each refusal reported with the
  SDK's own reason. **Global flows go into Global itself** where the instance allows: now.config.json `scope`/`scopeId` "global" with
  `packageResolverVersion` "2.0.0" (per the now.config.json reference); an earlier copy in nowBuilder's
  apps is deactivated.
- The AI's documentation search now includes the full ServiceNow SDK / Fluent 4.14 docs
  (`servicenow-sdk-fluent/…`).
- Renamed to **nowBuilder** everywhere.

- **Design document**: every plan card has *Design document* - a Word technical design (overview,
  application, assumptions, each component's settings, script or flow steps, checks, deployment evidence
  and per-row test steps) built from the plan itself.
- **Instance health check** (Settings → ServiceNow instances → *Health check*): reads the active custom
  business rules, client scripts, script includes and UI actions and reports what breaks best practice,
  with a score, a link to each record and *Fix with nowBuilder*. Read-only.
- **Move to another instance**: a deployed plan's update set is copied to another connected instance as
  a retrieved update set (preview first); the target's admin previews and commits it there.
- **Catalog items and record producers** with their variables are now built (Table API), with checked
  examples; catalog and category are looked up by title.
- **Explain & review** of any existing artifact, and **quick starts** on the workspace home.
- Health check flags `current.update()` in after business rules too.

- **Diagram** on every plan card: flowcharts (SVG, no extra packages) of how nowBuilder built the plan
  (request → read the instance → design → checks → deploy) and of what each component does at run time -
  start, Yes/No decisions, actions, loops drawn back to where they repeat - with conditions in words.
- **Fix with AI no longer loops on client scripts**: a setting whose column differs between releases
  (`sys_script_client.field_name` / `field`) is written to the column the instance's own schema has
  (`ArtifactSpec.aliases`), in the checks and the deployment.
- Removed the quick-start blocks; the home text covers every ServiceNow area.

- **GlideAjax contract**: a row that depends on another is written against that row's real script
  (method and parameter names), and a check fails a client script whose GlideAjax method or
  `sysparm_` parameters don't match the script include it calls (in the plan or on the instance).

- **More checks on what the AI writes, for every prompt**: every script is parsed as JavaScript (Node.js,
  `node --check`) so a syntax mistake is a check error before deploy; every event a script fires
  (`gs.eventQueue`) or a script action / notification listens for must be registered on the instance or
  in the plan; Fix with AI sees the scripts of related rows so both sides of a contract stay in step.

## What it builds
- Business rules, script includes, client scripts, UI policies, UI actions, notifications, **data
  policies, scheduled jobs, system properties, event registrations, script actions** (Table API), and
  **flows** (ServiceNow SDK / Fluent).
- Fields ServiceNow needs are set by the deployer: business rule `advanced`, notification
  `generation_type` (engine / event / triggered), the table on UI policy actions and data policy
  rules, scheduled job times as 1970-01-01 HH:MM:SS.
- The column check compares what is actually written with the instance table (nowBuilder's own
  settings such as `triggered_by_flow` are not reported as missing columns).

## Flows
- Exporter follows the Fluent Flow API: nested If / Else If / Else / For Each, data pills with types,
  Daily schedules, `{{plan.<row>}}` references to other rows (e.g. the notification a Send
  Notification step sends).
- Inputs the SDK only accepts as fixed text (Html type, e.g. Send Email's `ah_body` - build error
  TS228) are caught before building; the AI uses notification + Send Notification for email with
  record values.
- SDK setup is automatic and self-checking: project per instance in `backend/data/sdk/`, `npm install`,
  npm 11 install-script approval + rebuild, a test command before it is marked ready, repair of
  missing modules, one setup at a time (lock file). `setup-flows.ps1 [-Reset]` runs it with output on screen.

## Knowledge ("training")
- `skills/nowbuilder/*.md`: the delivery rules, a topic recipe table (incident, problem, change,
  request, knowledge, CMDB, SLA, HR, CSM, users/groups, email, scheduling, configuration, events).
- `skills/nowbuilder/examples/`: a worked example per artifact type, loaded only for that type and
  kept valid by `tests/test_skill_examples.py`.
- `skills/vendor/servicenow-skills/`: 26 skills reviewed against the bundled Australia documentation
  plus 6 new ones - events & scheduled jobs, Service Portal, ATF, import sets, reporting, Virtual
  Agent & Now Assist.

## Running
- `setup.ps1`, `start-backend.ps1`, `start-frontend.ps1`, `setup-flows.ps1` - see `START_HERE.md`.
- Removed: outdated deployment notes, the old SDK spike, duplicate docs, bundled `.venv` /
  `node_modules` / old database.

## Renamed to nowBuilder (4 Nov 2026)
- Product name, settings (`NOWBUILDER_...` in `backend/.env`), database (`nowbuilder.db`), skills
  folder (`backend/skills/nowbuilder/`), update sets (`nowBuilder - <title>`), the SDK app for new
  setups ("nowBuilder Automation", scope `x_<vendor prefix>_nbuild`) and flow files
  (`src/fluent/nowbuilder_<flow>.now.ts`).
- SDK projects prepared before the rename keep working without a new download; redeploying a flow
  replaces its old file. The app already installed on an instance keeps its original name and scope
  (ServiceNow can't rename an installed scope).

## Any connected instance (4 Nov 2026)
- No instance is configured in `.env` any more: `NOWBUILDER_DEFAULT_INSTANCE_URL` (form pre-fill) and
  `NOWBUILDER_SDK_INSTANCE_URL` (install pin) are empty by default and optional.
- A chat always works in the instance selected at the top of the page; switching instances moves the
  chat (and its next plans and deployments) to the new one.
- Flows get their own SDK project and sign-in per instance (`backend/data/sdk/<instance>/`), set up in
  the background when the instance is connected.

## Tables topic (4 Nov 2026)
- New deployable types: **table** (`sys_db_object`, extends a parent by name - resolved to its sys_id
  on deploy) and **field** (`sys_dictionary`, with choice values in `sys_choice`).
- Checks: global `u_` names, no duplicate tables or fields, field type must exist in the instance
  (`sys_glide_object`), referenced and parent tables must exist, choice fields need values. Other rows
  in the same plan may use the new table and fields (the checks know about them before deployment).
- Deploy order: tables, then fields, then everything else; rollback removes them in reverse.
- `servicenow-tables-forms-lists` skill extended with the record columns, field types and limits;
  worked examples `examples/table.md`, `examples/field.md`; planning and topic tables updated.

- SDK setup approves each held-back npm package on its own (npm rejected the whole request when one listed package was not waiting, so no rebuild ran).

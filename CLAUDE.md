# nowBuilder: notes for Claude Code

nowBuilder is an AI-powered **ServiceNow** development platform, a sister product of MetaFlow
(Salesforce) built from the same base. A user describes a requirement in a chat (or attaches a BRD, or
picks a Jira story); nowBuilder reads their connected ServiceNow instance and designs business rules,
script includes, client scripts, UI policies and UI actions. Later chunks add plans, checks, Fix with AI
and deploying into an update set (see Status).

Owner: Vasu (vasu.dharavath8@gmail.com). Developing on Windows, VS Code, PowerShell. Connected
instance: whichever is connected and selected in the app (no instance is configured in `.env`). Automated
tests still run against `tests/fake_snow.py`.

**Naming**: ServiceNow words only (instance, table, artifact, update set, Table API). See `NAMESPACE.md`
for the full word list and where each ServiceNow part lives; never bring Salesforce names back.

## Run, test, build

```powershell
# backend (terminal 1)
cd backend; .venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --reload-dir app   # http://localhost:8000/docs (never reload on data/)
python -m pytest                             # all backend tests; ServiceNow + AI are faked

# frontend (terminal 2)
cd frontend; npm run dev                     # http://localhost:5173 (proxies /api to :8000)
npm run build                                # run after every frontend change
```

Always run `pytest` and `npm run build` before saying a change is done. Add tests with every backend
change (patterns: `tests/fake_snow.py` in-memory instance used through the real `ServiceNowClient`,
scripted LLMs in `tests/test_chat.py` and `tests/test_instances.py`).

Hosting is the same as MetaFlow: root `Dockerfile` (frontend built, served by the backend from
`/app/static`), `render.yaml` Blueprint (one Docker web service + Postgres), env vars prefixed
`NOWBUILDER_`. Never change `NOWBUILDER_ENCRYPTION_KEY` after the first deploy.

## Architecture

| Area | Where |
|---|---|
| FastAPI app, routers | `backend/app/main.py`, `backend/app/routers/` (auth, instances, ai_settings, chats, workspace, integrations, platform) |
| ServiceNow connection: URL normalising, basic auth, OAuth password grant + refresh, Table API, reading the instance | `backend/app/services/servicenow.py` (`ServiceNowClient`: `query/get/insert/update/delete`, `whoami`, `table_schema` with inherited fields, `search_artifacts`, `get_artifact`; `ARTIFACT_TABLES`; `DEFAULT_TRANSPORT` swapped in tests) |
| Settings → ServiceNow instances | `backend/app/routers/instances.py` (`/api/instances`: list, connect, test, patch, select, delete); frontend `pages/InstancesSettingsPage.jsx` |
| Models | `backend/app/models.py` (`Instance`: url, instance_type Development/Test/Production, auth_method basic/oauth, encrypted password / client secret / tokens, release, user, roles, is_admin, status). `Plan` / `FixProposal` are kept for Chunk 2+ |
| Workspaces, members, roles, invites, limits | `backend/app/services/workspace.py` (`Ctx`, `instances()`, `selected_instance()`, `check_instance_room`), `routers/workspace.py`; frontend `pages/AdminPage.jsx`, `workspaceApi.js` |
| Platform admin, accounts and email, AI provider + credits, Jira/GitHub | Same as MetaFlow (`services/platform.py`, `routers/auth.py`, `services/mailer.py`, `ai/providers.py`, `ai/usage.py`, `services/jira.py`, `services/github.py`). `github.py` commits files under `servicenow/<table>/`; Push to Git comes back with deploys in Chunk 4 |
| AI: prompts from skills | `backend/app/ai/skills.py` (`Skills.build_prompt(stage, artifact_types, text)`: nowBuilder rules, then `alwaysSkills`, then the artifact types' skills, then the 3 skills that best match the message) |
| AI: chat turn | `backend/app/ai/chat_engine.py` (tools, `propose_plan`, `deploy_plan`) |
| AI: plans | `backend/app/ai/planning.py` (`PlanBuilder`: save, generate each row, check; auto-deploy only when `NOWBUILDER_AUTO_DEPLOY` is on) |
| Prompt → instance delivery | `backend/app/services/auto_deploy.py` (`allowed()`, `AutoDeployer`: one Fix-with-AI pass, Table API rows into an update set via `services/deploy.py`, flows via `services/sdk_deploy.py`, read-back, result for the model) |
| Flows as code | `backend/app/ai/flow_sdk.py` (design → Fluent source, nesting, `{{plan.<id>}}` refs), `services/sdk_deploy.py` (automatic SDK project per instance, `now-sdk auth --password-stdin`, `build/install`, `read_back_flow`) |
| AI: tools | `backend/app/ai/tools.py` (`get_table_schema`, `search_instance_artifacts`, `get_instance_artifact`, `get_flow_actions`, `query_instance_records`, docs search, `get_skill_file`) |
| Prompts and ServiceNow knowledge | `backend/skills/`: `nowbuilder/*.md` (nowBuilder rules, they win), `nowbuilder/examples/` (one checked worked example per type), `vendor/servicenow-skills/` (32 skills, reviewed Nov 2026 against the bundled Australia docs: global/ES5 examples, record field tables), `manifest.json` (stages, artifact types → skills) |
| Frontend | `frontend/src/`: React 18 + JavaScript (JSX) + Vite, no UI library; `instances.jsx` (workspace context: `instances`, `selected`, `ai`, `ws`, `can`), `components/AppShell.jsx` (nav, instance switcher, user menu), `pages/HomePage.jsx`, `pages/WorkspacePage.jsx`, `components/Markdown.jsx` (Copy on code blocks) |

## Product rules (agreed with the owner)

- **Same product shape as MetaFlow**, for ServiceNow: workspaces, roles, platform admin, any AI provider,
  credits, Jira stories, the chat. Salesforce-only features (Org Intelligence, Import, Migration, page
  layouts, flows, Apex tests, rollback by Metadata API) are gone; their ServiceNow versions come in later chunks.
- **Scope**: business rules, script includes, client scripts, UI policies (+ actions), UI actions, notifications,
  data policies (+ rules), scheduled jobs, system properties, event registrations, script actions, tables and fields through the
  Table API (`app/ai/artifacts.py` SPECS); flows (`sys_hub_flow`) through the ServiceNow SDK.
- **Now Assist-style delivery, button deploys** (owner, 4 Nov): a prompt becomes a checked plan; it is
  deployed only when the user clicks Approve → Deploy on the plan card (`NOWBUILDER_AUTO_DEPLOY`
  false by default; the chat has no `deploy_plan` tool then). The update set stays current
  (`NOWBUILDER_KEEP_UPDATE_SET_CURRENT`). Never Production without confirmation. Only rows without
  check errors deploy; every record is read back before it is called deployed.
- **Application (scope)**: `Plan.application` (global or a scope) from the request/document; every
  row goes there (`services/application.py`: `apps.current_app` preference + update set `application`,
  `sys_scope` read back). Global flows: SDK Global app in `data/sdk/<host>/global/`, fallback to the
  scoped app with `application_note`.
- **Connecting**: basic auth or OAuth password grant (`/oauth_token.do`, Application Registry client).
  The address is normalised to `https://<host>` (`dev410284` → `https://dev410284.service-now.com`, http
  refused). Connecting reads the user (`sys_user`), roles (`sys_user_has_role`) and release
  (`glide.buildname`). Without `admin` it still connects, with a warning. Hibernating PDIs, 401, 403, 429 all
  become plain messages. Secrets are encrypted; OAuth renews with the refresh token, then the saved password.
- **Instance types**: Development / Test / Production; production shows red and will always confirm before deploys.
- **Limits**: `NOWBUILDER_MAX_INSTANCES` (2) and `NOWBUILDER_MAX_MEMBERS` (3) per workspace on the
  Standard plan; Starter 1/2, Team 3/4, Business 5/10. Per-member instance access (`Membership.instance_ids`)
  and each member's own selected instance (`Membership.selected_instance_id`).
- **Chat**: reads the instance before answering (tables with inherited fields, existing artifacts on the
  table, flow actions). It only claims a deployment the instance confirmed. ES5 unless the user says
  ES2021 scoped app.
- Everything else (accounts, email, platform admin, AI provider, credits) follows MetaFlow's rules.

## Conventions

- Python 3.12+, type hints, small functions; user-facing errors are plain sentences that say what to do.
  No secrets in logs, responses or prompts.
- Prompts live in `backend/skills/nowbuilder/*.md`, not Python strings. Vendored skills are edited only to
  correct them against ServiceNow documentation; `tests/test_prompt_contract.py` pins the prompt contract.
- Frontend is plain JavaScript. Sentence case, plain words, every async action shows progress and a real
  error. Must work at 390px. Keep the visual language (IBM Plex, blue accent, white cards).

## Status (3 Nov 2026)

| Chunk | Scope | Status |
|---|---|---|
| 0 | Base from MetaFlow: accounts, workspaces, roles, platform admin, email, AI provider, credits, Jira | Done |
| 1 | ServiceNow instances (basic + OAuth), switcher, chat reads the instance with tools, ServiceNow skills | Done |
| 2 | Plans: one row per artifact, generated records + scripts, streamed plan card | Done |
| 3 | Checks, Fix with AI, Edit | Done |
| 4 | Approve → deploy into a named update set (Table API), rollback, Push to Git | Done |
| 4b | Flows via ServiceNow SDK, button-only deploys, update set left current, design documents | Done (348 tests) |
| 5 | Home stats, instance intelligence | |
| 6 | Import sets, instance-to-instance moves | |

Known gaps: the deployment path is tested against the fake instance; run a first real deploy on
the connected instance with a low-risk script include and check the update set. SDK flow installs need Node.js 20+ on
the backend host; the SDK project is created automatically under `data/sdk/` (background on connect,
or `python -m app.sdk_setup` with visible output; `SDK_DEPLOYMENT_SETUP.md`). The deployment lock is per process.

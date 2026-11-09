# Start here: run nowBuilder step by step (Windows)

nowBuilder works like Now Assist for creators: you describe what you need, it reads your
connected ServiceNow instance, makes a plan, writes and checks every artifact, and deploys it into
the instance. Nothing about your instance is hard-coded: the instance address, user, scope and
vendor prefix all come from the connection you make in Settings (the connect form is only
pre-filled from `NOWBUILDER_DEFAULT_INSTANCE_URL` in `backend\.env`).

## You need (once per computer)
- **Python 3.12 or 3.13** - https://www.python.org/downloads/ (tick "Add python.exe to PATH")
- **Node.js 20 or later (LTS)** - https://nodejs.org
- VS Code. Check in a terminal: `py --version` and `node -v`.

## 1. Open the project
Unzip, then in VS Code **File → Open Folder** and pick the folder that contains `backend`,
`frontend` and this file (the `nowBuilder` folder inside the zip).
Open a terminal: **Terminal → New Terminal**.

## 2. Install everything (once)
```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```
It creates `backend\.venv`, installs the Python packages, makes `backend\.env` if missing, and runs
`npm install` for the frontend. Wait for **Done**.

(Coming from an earlier copy? Copy your old account database into the new `backend` folder and
name it `nowbuilder.db`, and copy the old `backend\data` folder too (it holds the ServiceNow SDK
download, so flows don't need setting up again). Use the `backend\.env` from this zip: it holds the
same keys, with the settings renamed to `NOWBUILDER_...`.)

## 3. Start the backend (terminal 1, keep it open)
```powershell
powershell -ExecutionPolicy Bypass -File .\start-backend.ps1
```
Ready when it shows `Uvicorn running on http://127.0.0.1:8000`.

## 4. Start the web app (terminal 2, keep it open)
Click **+** in the terminal panel, then:
```powershell
powershell -ExecutionPolicy Bypass -File .\start-frontend.ps1
```
Open **http://localhost:5173**.

## 5. In the app
1. **Sign up** (or sign in).
2. **Settings → AI provider**: pick your provider, paste the API key, **Verify**.
3. **Settings → ServiceNow instances → Connect**: enter the address
   with your instance address (for example https://dev12345.service-now.com). Choose **Username and password**, an **admin** user without
   multi-factor sign-in, type **Development**.

## 6. Prepare flow deployment (terminal 3, once)
Flows are installed with the official ServiceNow SDK. Download it and sign it in:
```powershell
powershell -ExecutionPolicy Bypass -File .\setup-flows.ps1
```
Wait for **Ready** (5-15 minutes the first time). If an earlier attempt failed or was interrupted:
```powershell
powershell -ExecutionPolicy Bypass -File .\setup-flows.ps1 -Reset
```
Business rules, script includes, client scripts, UI policies, UI actions, notifications, tables and
fields don't need this step.

## 7. Try it
In **AI workspace**, send for example:
- `Make subcategory mandatory on incident when category is hardware.`
- `When a priority 1 incident is created, email the assignment group.`
- `Create a flow "SF Test 1 - Incident log": when an incident is created, log an info message with the incident number and short description.`

The plan card fills in, every row is checked against your instance, and rows that pass are deployed:
scripts and records into a new update set `nowBuilder - <title>`, flows into the scoped app
"nowBuilder Automation". The reply lists what is live with links. If something is held, the card
says why; fix it (Fix with AI) and say **deploy it**.

## Next time
Terminal 1: `powershell -ExecutionPolicy Bypass -File .\start-backend.ps1`
Terminal 2: `powershell -ExecutionPolicy Bypass -File .\start-frontend.ps1`

## If something goes wrong
| You see | Do |
|---|---|
| `py` / `node` not recognized | Install Python / Node.js (above), reopen VS Code |
| Card: "SDK setting up" | Wait for `setup-flows.ps1` to say Ready, then say "deploy it" |
| Card: "SDK install failed" with `Cannot find module` | `setup-flows.ps1 -Reset`, then "deploy it" |
| `npm install` fails or hangs | Check internet / proxy: `npm ping` should print PONG |
| 401 / sign-in errors | Settings → ServiceNow instances → Update sign-in |
| Instance unreachable | A developer instance hibernates: wake it at developer.servicenow.com |

More: `SDK_DEPLOYMENT_SETUP.md` (flows), `README.md` (what it builds), `CHANGES.md` (what changed).

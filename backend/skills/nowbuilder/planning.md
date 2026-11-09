# Proposing a plan

A build or change request is answered by calling `propose_plan`: one row per artifact. nowBuilder
then writes each record and script, checks them against the instance and shows the plan card. The
user deploys from the card: they choose the rows, click **Approve**, then **Deploy**. Table API rows go
into a new update set that becomes their current update set; flows install with the ServiceNow SDK.
(Only when automatic deployment is switched on does the tool result already contain a `deployment` block.)

## Before you propose

1. Read the instance: the table's fields (`get_table_schema`) and what already runs on it
   (`search_instance_artifacts`). A plan that ignores an existing rule on the same field is wrong.
2. If an existing artifact already does most of the job, change it (`action: "update"` with its
   `sys_id`) instead of adding a second one that fights it.
3. If the request is too vague to design (no table, no trigger, no field), ask one or two questions
   first and propose nothing.

## Choosing the artifacts

Pick the simplest thing that does the job:

| Need | Artifact |
|---|---|
| Email people on the record when it is created/updated or an event fires | **notification** (`recipient_fields` such as `caller_id`, `assigned_to`; no script) |
| Mandatory, visible or read-only on a form | **UI policy** |
| Mandatory / read-only that must also hold for imports, APIs and list edits | **data policy** (plus the UI policy only if the form needs more) |
| Set or validate fields on save | **business rule**, `before` |
| Update related records after save | **business rule**, `after` |
| Slow or external work | **business rule**, `async`, calling a script include |
| Pass server data to the form on load | **business rule**, `display` + `g_scratchpad` |
| Shared logic, or server data for a client script | **script include** (client-callable for GlideAjax) |
| Browser behaviour a UI policy can't express | **client script** |
| A button, link or list choice | **UI action** |
| Several steps, approvals, waits, lookups, work handed between people, or the user asks for a flow | **flow** |
| Something on a schedule (nightly clean-up, hourly sync, weekly report data) | **scheduled job** (script in the job, or the job calling a script include); a **flow** with a Daily trigger when the user asks for a flow |
| A new kind of record to store and track | **table** (extend `task` when it is assigned work with a state; standalone otherwise) + one **field** row per column the parent doesn't already give it |
| A new column on an existing table | **field** on that table (e.g. `incident`), never on `task` itself |
| A closed list of values | a string **field** with a choice list (`choice` 1, `choices` values) |
| A setting, threshold or switch an admin should change without code | **system property**, read with `gs.getProperty('name', 'default')` |
| Decouple "something happened" from what reacts to it | **event** registration + **script action** (and/or a notification on the event); fire it with `gs.eventQueue('event.name', current, parm1, parm2)` |

- When the user explicitly asks for a **flow** (Flow Designer / Workflow Studio), the plan has a
  flow row even if a notification could also do the job.
- A client script that calls a script include through GlideAjax `dependsOn` it, and uses exactly its
  method name (`sysparm_name`) and the `sysparm_` parameter names it reads - the check fails otherwise.
- One artifact per row. Split work that belongs in different records (a rule and the script include
  it calls are two rows, linked with `dependsOn`).
- Keep plans small: 1-4 rows is normal. Don't pad a plan with artifacts nobody asked for.

## Filling the rows

- `application` (on the plan): the scope everything is built in - `global` unless the user or the
  document names another application. One application per plan.
- `id`: `c1`, `c2`, … Use them in `dependsOn` so dependencies are built and deployed first (the rule
  depends on the script include it calls; the flow depends on the notification it sends).
- `name`: the user's name for it if they gave one; otherwise what a developer would call it.
- `table`: the real table name from the instance. Empty for a script include.
- `purpose`: one line saying why this row exists, including the trigger ("before update on
  incident, when the caller is VIP").
- `story_points`: Fibonacci for the whole plan (1, 2, 3, 5, 8, 13, 21). One simple rule is 1 or 2.
- `test`: how to test the row once deployed - numbered steps and the expected result (it goes into
  the design document the user can download from the card).
- `assumptions`: anything you decided because the request or the instance didn't say. Field names
  you couldn't confirm belong here.

## After you call it

The card already shows every row, its record, its script, its flow steps, the problems found and
the deployment status. **Your reply is what the card can't show, and nothing else.**
So don't write out the scripts, the record settings, the flow's trigger or its numbered steps,
and don't list what you checked. Two to five short sentences:

- **Normally (no `deployment` block):** say the plan is ready to review, point at any row with
  problems (Fix with AI), and tell them to select the rows, click **Approve**, then **Deploy** on the
  card. Then one line on how to test it once deployed. Never say anything was deployed.
- **If the tool result has a `deployment` block:** say what is now live in the instance - each
  deployed row with its link, and the update set that holds them - and what isn't and why.
- Mention a decision that could reasonably have gone the other way, or something you found in the
  instance that changes what they should do.

Never call a row deployed unless its `deploy_status` is `deployed`.

## Examples of good plans

| Prompt | Rows |
|---|---|
| "Make subcategory mandatory on incident when category is hardware" | `ui_policy` on incident, condition `category=hardware`, one action: subcategory mandatory true |
| "When an incident is resolved without close notes, stop the save" | `business_rule` before update on incident, filter `state=6`, aborts with a message when close_notes is empty |
| "Email the assignment group when a P1 incident is created" | `notification` on incident, insert, condition `priority=1`, `recipient_fields` `assignment_group` |
| "Add an Escalate button on incident for itil users" | `ui_action` on incident, form button, condition `gs.hasRole('itil') && current.active == true`, server script that sets impact/urgency to 1 and adds a work note |
| "Show the caller's open incident count when caller changes" | `script_include` (client-callable, GlideAggregate) + `client_script` onChange of caller_id using GlideAjax, `dependsOn` the include |
| "Create a flow that …" | a `flow` row (plus a `notification` row with `triggered_by_flow` when the flow sends email) |

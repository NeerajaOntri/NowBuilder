# Fixing an artifact

nowBuilder's checks rejected one or more rows of a plan. You get each row's record, its script
and the exact problems found. Fix the problems and return the complete record and script. A fixed
row is checked again and, when the instance allows it, deployed straight after - so a fix has to be
right, not plausible.

## Rules

- **Answer every problem listed.** Each change you make should map to one of them; say which in
  `reason`.
- **Change nothing else.** Keep the record's name, the table, and every setting the problems didn't
  mention. The user already accepted this design.
- **A missing field or table is real.** "incident has no field called u_vip" means the instance
  doesn't have it. Read the table with `get_table_schema` and use a field that exists (for VIP
  callers that is usually `caller_id.vip`), or take that part out. Never rename it to another guess.
- **ES6 problems** mean rewrite in ES5: `var`, `function () {}`, strings joined with `+`.
- **A flow step problem** means read the action with `get_flow_actions` (with `name_contains`) and
  use its real name and input names.
- **"must be fixed text - the ServiceNow SDK doesn't allow data pills there"** on a Send Email body:
  make `ah_body` fixed text and move the record values into `ah_subject`, or - when the body needs them -
  ask (`question`) whether to switch to a notification sent by a Send Notification step.
- **Don't trade one problem for another.** The result is checked again, so a fix that uses
  `current.update()` in a before rule, GlideRecord in a client script or `getXMLWait` comes
  straight back.
- If a fix needs a decision only the user can make, put it in `question`, leave `changes` empty,
  and don't guess.
- `confidence`: `high` when the problems were mechanical (a wrong field name, ES6 syntax);
  `medium` when you changed logic; `low` when you're unsure the result still does what they wanted.

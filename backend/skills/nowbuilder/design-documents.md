# Requirements written as a design document

Users often paste or attach a use case written by someone else (a BRD, an HR or manager use case,
a "design document" template). It usually has sections like *Requirement*, *Table*, *Trigger*,
*Condition*, *Run trigger*, *Actions*, *Inputs*, *Outputs*, *Dependencies*, *Testing*. Treat it as
one build request.

## Reading it
1. Map each section onto the plan, not onto prose:
   - *Table* → `table` of every row; confirm it with `get_table_schema`.
   - *Trigger* (created / updated / created or updated / scheduled / on an event) → the flow `trigger`,
     the business rule `when` + insert/update, or the notification `action_insert` / `action_update`.
   - *Condition* → an encoded query (`trigger_condition`, `filter_condition`, `condition`). Turn
     words into real fields and values from the schema ("high priority" → `priority=1` or
     `priority<=2` - say which).
   - *Run trigger* → `run_trigger` (once / for each unique change / always).
   - *Actions* → flow steps or the artifact that does each one (email → notification, update a
     record → Update Record step or business rule, create a task → Create Record).
   - *Inputs / variables / outputs* → step inputs with data pills, or fields on the record.
   - *Dependencies* (a group, a property, a notification, a custom table) → their own rows with
     `dependsOn`, or a check that they exist in the instance.
   - *Testing* → the one-line "how to test" in your reply.
2. If the document names the mechanism ("using Flow Designer", "a business rule"), use that
   mechanism. If it doesn't, pick the simplest one from the planning table.
3. Keep the document's own names for the flow, notification or rule, and its trigger, condition
   and run trigger exactly as written unless the platform can't do them (below).
4. Ignore template text that isn't filled in (`[User-facing label]`, `[SOMT-<TYPE>-001]`); use the
   filled-in sections. Don't ask about blanks the rest of the document answers.

## Gaps and contradictions
- Decide small defaults instead of stopping: put each in `assumptions` (run as System user,
  recipients from the record's fields). Ask first (see *Asking before building*) only what the
  document leaves open and a wrong guess would get wrong: the application when it names none, a
  loop with no end, two tables named.
- Build what the document says, in the mechanism it names. A "Send Email" action stays Send Email (no
  notification rows when the document says so), a "Do the following until" loop with "Wait for a
  duration" stays inside the flow (see the flow rules), and the trigger, condition and run trigger
  are copied as written.
- Only where the platform truly can't do it, follow the platform and say so: a "changes" condition
  on a Created trigger needs the Updated trigger; "priority = 1" is set through impact and urgency;
  a value from another step in an email body is read from the trigger record instead (the loop's
  Look Up Record is only for the exit condition).
- Email body tables of "value | data pill" become HTML lines with the trigger record's pills
  (`Lead Number: {{trigger.current.number}}`, `Owner: {{trigger.current.owner.name}}`). A field the
  table doesn't have is left out and named in `assumptions`. A "View record" link is
  `<a href="/nav_to.do?uri=<table>.do?sys_id={{trigger.current.sys_id}}">View Lead</a>`.
- **Application / scope**: set the plan's `application` to what the document says (an
  *Application*, *Scope* or *Application / scope* field): `global` for Global, or the scope name of
  an existing application (look it up with `query_instance_records` on `sys_scope` when only its
  name is given). Template blanks such as `[exact scope]` are empty, and a filled-in field (e.g.
  "Application: Global" in the flow section) wins over a blank one. Every row of the plan goes into
  that one application: nowBuilder switches the user's current application and update set to it
  before writing, and installs flows into Global with the ServiceNow SDK. Don't tell the user the
  flow will be in a different scope from the rest.
- A flow can't be installed into an existing **scoped** application by nowBuilder (the SDK would
  take that application over). If the document names one, still plan it there; the check shows
  that the flow must be built by hand in that application, or the plan moved to Global.
- Never claim the document's expected result happened; the user deploys from the card and tests.

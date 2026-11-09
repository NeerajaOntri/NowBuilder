---
name: servicenow-update-sets
description: Moving ServiceNow changes between instances with update sets - what is and isn't captured, batching, previewing, resolving collisions and problems, backing out, naming conventions, and when to use source control or the app repository instead. Use when promoting changes dev to test to prod, troubleshooting a preview error, or planning a release.
license: Apache-2.0
metadata:
  category: foundations
  version: "1.1"
---

# Update Sets

## When to use
- Promoting global-scope customizations between instances.
- Preview errors ("Could not find a record...", collisions).
- Planning a release or a back-out.

## Key facts
- An update set (`sys_update_set`) is a container of **customer updates** (`sys_update_xml`) - XML snapshots of configuration records at the time they were last changed.
- **Captured:** tables marked as application files - scripts, business rules, UI policies, dictionary, forms, ACLs, notifications, flows, properties (definition), etc.
- **Not captured:** data records (users, groups, group memberships, CIs, incidents, KB articles), scheduled job executions, homepage personalisations, most records you only *use*. Move data with *Export to XML* / import sets, or with *Add to Update Set* only if your org has an approved method.
- Updates are tied to **one scope**. A global update set can't hold scoped updates and vice versa (batches can group them).
- Target flow: complete on source → retrieve on target (or import XML) → **Preview** → resolve problems → **Commit**.
- Changes are captured into the **current update set of the user making them** (the `sys_update_set` user preference). Changes made through the Table API are captured the same way, so set the integration user's current update set first and put it back afterwards.
- **Batch update sets** (parent/child) let you preview and commit several sets in order.

## Rules
1. Never work in the **Default** update set. Create a named set before you start; check the picker every session.
2. Naming: `<ticket>_<short description>_<v>`, e.g. `STRY0012345_AI_triage_BR_v1`. Add a description listing the stories.
3. Keep sets small and cohesive; one story or feature per set, grouped by a batch for a release.
4. Don't move or merge sets after completing unless you understand the ordering; merging hides history.
5. **Preview every time.** Resolve each problem deliberately:
   - *Missing reference* → the referenced record is data or in another set: move it first or accept if it exists on target.
   - *Collision / newer on target* → someone changed the record on target; compare, then accept remote or skip.
6. Commit to test first, run tests (ATF), then prod - the same sets in the same order.
7. Never "fix in prod". If you must, capture the fix in prod and bring it back to dev immediately.
8. Back out with *Back Out* on the committed set only for recent sets; otherwise ship a corrective set.
9. **Scoped apps:** prefer source control or the application repository over update sets.
10. Don't delete customer updates to "clean" a set; a delete is itself an update and needs to travel.

## Review checklist
- [ ] All sets in the batch are Complete
- [ ] Preview clean on test, problems resolved and noted
- [ ] Data dependencies moved (groups, roles assignments, properties values)
- [ ] ATF suite passes on test
- [ ] Commit order recorded; back-out plan written
- [ ] Prod preview reviewed by a second person

## Anti-patterns
- One giant "Sprint 14" set with 900 updates and 30 stories.
- Capturing test data in update sets.
- Ignoring preview warnings and committing anyway.
- Changing records in test/prod so the next commit collides.

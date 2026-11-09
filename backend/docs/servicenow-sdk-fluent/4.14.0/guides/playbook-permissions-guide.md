Version: 4.14.0

# Playbook permissions guide

Practical guide for granting access to a playbook, its lanes, and its activities. Permissions control who can view, launch, restart, and manage a playbook and act on the stages/lanes and activities inside it at runtime, expressed declaratively in Fluent.

## When to Use

Use permissions when you need to control who can see or act on a playbook. This covers playbook-wide actions (view, launch on demand, restart, cancel) as well as more granular actions on the work inside it — restarting a stage/lane, restarting an individual activity, or adding optional activities to a lane at runtime. Grant these to specific users, user groups, roles, or user criteria. Permissions are optional — omit them and the platform defaults apply.

There are two levels:

- Playbook permissions — declared in the 2nd `PlaybookDefinition` argument, alongside `triggers`.

- Lane permissions — declared on an individual lane's `config.permissions`.

## Permission sets and reference kinds

At both levels, permissions are grouped by the kind of thing being granted access. Each entry is a permission set: one reference plus the access flags granted to it.

| Group | Reference field | Accepts |
| `users` | `user` | a data pill to a `sys_user` record |
| `userGroups` | `userGroup` | a data pill to a `sys_user_group` record |
| `roles` | `role` | a `sys_user_role` sysId string or a data pill |
| `userCriterias` | `userCriteria` | a `sys_user_criteria` sysId string |

Each reference should be specified once within its group — listing the same user (or group/role/criteria) twice is a build error.

Note on `user` / `userGroup`: these are normally data pills. A plain sysId string is only accepted for playbook permissions when the playbook's `executionType` is not `record_driven` (currently only `'on_demand'`); for `record_driven` playbooks (the default) and for all lane permissions, `user` and `userGroup` must be data pills.

## Playbook permissions

Playbook permissions are a callback that receives `params` and returns the permission groups. The callback form gives pills access to `params.parentRecord`:

```
import { PlaybookDefinition, wfa } from '@servicenow/sdk/automation'

PlaybookDefinition(
    { $id: Now.ID['my_playbook'], label: 'My Playbook', parentTable: 'incident' },
    {
        permissions: (params) => ({
            users: [
                {
                    user: wfa.playbook.dataPill(params.parentRecord.assigned_to),
                    view: true,
                    launch: true,
                    cancel: true,
                },
            ],
            roles: [
                { role: 'b453c203c3213100ad408039dfba8fb0', view: true, restart: true },
            ],
            userCriterias: [
                { userCriteria: 'fb1166d64fff0200086eeed18110c7ab', view: true },
            ],
        }),
        triggers: [/* ... */],
    },
    { lanes: (params) => ({ /* ... */ }) }
)
```

### Options

Each playbook permission set accepts these flags:

- `view` (required) — Can see the playbook. `view` gates every other option: another permission on a set only takes effect when that same set also has `view: true`. Setting another option without `view` is a build error.

- `launch` — Can launch the playbook on demand.

- `laneAddOptionalActivity` — Can add optional activities to a lane at runtime.

- `restart` — Can restart the whole playbook.

- `laneRestart` — Can restart a stage/lane.

- `activityRestart` — Can restart an individual activity.

- `cancel` — Can cancel the playbook.

on_demand playbooks: at least one permission set must grant `launch: true` — otherwise there is no way to launch the playbook. This is a build error, and it fires even if `permissions` is omitted entirely. See `playbook-api#execution-types`.

## Lane permissions

Lane permissions are a plain object on the lane's `config.permissions`. The `params` for any pills comes from the enclosing `lanes` callback (there is no separate permissions callback):

```
lanes: (params) => ({
    triage: wfa.playbook.lane({
        config: {
            $id: Now.ID['triage_lane'],
            label: 'Triage',
            order: 1,
            startRule: wfa.playbook.run.Immediately(),
            restartRule: 'RUN_ONLY_ONCE',
            permissions: {
                users: [
                    { user: wfa.playbook.dataPill(params.parentRecord.assigned_to), view: true, activityRestart: true },
                ],
                roles: [
                    { role: 'cc0f1ea25323021052c0ddeeff7b1268', view: true },
                ],
            },
        },
        activities: (params) => ({ /* ... */ }),
    }),
})
```

### Options

Lane permission sets support a reduced set, and unlike the playbook these flags are independent — `view` does not gate the others:

- `view` — Can view this lane.

- `addOptionalActivity` — Can add optional activities to this lane at runtime.

- `restart` — Can restart this stage/lane.

- `activityRestart` — Can restart an individual activity in this lane.

Lane `user` and `userGroup` must be data pills (sysId strings are not accepted); `role` and `userCriteria` follow the same rules as the playbook level.

## Referencing the parent record

When the playbook declares a `parentTable`, `params.parentRecord` is available inside `permissions` and is dot-walkable. Wrap it in `wfa.playbook.dataPill(...)` to grant access to whoever a field on the triggering record points to:

```
// The user in the incident's "Assigned to" field
user: wfa.playbook.dataPill(params.parentRecord.assigned_to)

// A group referenced by a field on the parent record
userGroup: wfa.playbook.dataPill(params.parentRecord.assignment_group)
```

on_demand playbooks: `params.parentRecord` is not present at all when the playbook's `executionType` is `'on_demand'` — referencing it in the `permissions` callback is a compile error (`Property 'parentRecord' does not exist on type ...`), since on-demand playbooks have no triggering record and cannot declare a `parentTable`. See `playbook-api#execution-types`.

## Referencing an activity's output

To grant access based on an activity's output — for example, the user produced by an approval or lookup activity — reference the activity by its `$id` with `wfa.playbook.activityRef(...)`. This works even though the activity is not in lexical scope where permissions are declared (permissions can't see lane/activity variables):

```
user: wfa.playbook.dataPill(
    wfa.playbook.activityRef(Now.ID['approval_step']).outputs.approver
)
```

- The `Now.ID['...']` key must match the `$id` of an activity defined in the same playbook (validated at build time).

- Only activity outputs are referenceable — the path must start with `outputs.` followed by a specific output field.

## See

- `playbook-datapills-guide` — data pill usage and formats

- `playbook-lanes-guide` — lane configuration

- `playbook-api` — full API reference

Version: 4.14.0

# Flow Logic

The `wfa.flowLogic` namespace provides control flow operators for branching, looping, and flow control within Flow and Subflow bodies.

## Usage Pattern

All flow logic constructs follow this invocation shape:

```
wfa.flowLogic.<construct>(
  { $id: Now.ID['logic_id'], ...params },
  callback?
)
```

## wfa.flowLogic.if

Evaluates a condition and executes the callback if true.

### Signature

```
wfa.flowLogic.if(
  params: {
    $id: string,
    condition: string,
    label?: string,
    annotation?: string
  },
  body: () => void
)
```

### Parameters

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `condition` | `string` | Yes | - | Encoded query expression to evaluate |
| `label` | `string` | No | - | Display label for this branch |
| `annotation` | `string` | No | - | Description/comment |

## wfa.flowLogic.elseIf

Evaluates a condition if previous conditions were false. Must follow `if` or `elseIf`.

### Signature

```
wfa.flowLogic.elseIf(
  params: {
    $id: string,
    condition: string,
    label?: string,
    annotation?: string
  },
  body: () => void
)
```

### Parameters

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `condition` | `string` | Yes | - | Encoded query expression to evaluate |
| `label` | `string` | No | - | Display label for this branch |
| `annotation` | `string` | No | - | Description/comment |

## wfa.flowLogic.else

Executes callback if all previous conditions were false. Must follow `if` or `elseIf`.

### Signature

```
wfa.flowLogic.else(
  params: {
    $id: string,
    annotation?: string
  },
  body: () => void
)
```

### Parameters

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `annotation` | `string` | No | - | Description/comment |

## wfa.flowLogic.forEach

Iterates over an array, executing the callback for each item.

### Signature

```
wfa.flowLogic.forEach<TArray>(
  items: TArray,
  config: {
    $id: string,
    annotation?: string
  },
  body?: (item: ExtractArrayElement<TArray>) => void
)
```

### Parameters

| Parameter | Type | Required | Default | Description |
| `items` | `TArray` | Yes | - | Array to iterate (use data pill with array type) |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `annotation` | `string` | No | - | Description/comment |
| `body` | `function` | No | - | Callback receiving each item |

### Supported Data Pill Types

- `'array.object'` — For `lookUpRecords` results and object arrays

- `'array.string'` — For string arrays (no item parameter)

## wfa.flowLogic.exitLoop

Immediately exits the enclosing loop (`forEach` or `doTheFollowing`).

### Signature

```
wfa.flowLogic.exitLoop(
  params: {
    $id: string,
    annotation?: string
  }
)
```

### Parameters

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `annotation` | `string` | No | - | Description/comment |

## wfa.flowLogic.skipIteration

Skips the current iteration of the enclosing loop (`forEach` or `doTheFollowing`) and continues with the next iteration.

### Signature

```
wfa.flowLogic.skipIteration(
  params: {
    $id: string,
    annotation?: string
  }
)
```

### Parameters

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `annotation` | `string` | No | - | Description/comment |

## wfa.flowLogic.endFlow

Immediately terminates flow execution.

### Signature

```
wfa.flowLogic.endFlow(
  params: {
    $id: string,
    annotation?: string
  }
)
```

### Parameters

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `annotation` | `string` | No | - | Description/comment |

## wfa.flowLogic.doInParallel

Executes multiple code blocks in parallel within a flow.

### Signature

```
const parallel = wfa.flowLogic.doInParallel(
  params: {
    $id: string,
    annotation?: string
  },
  ...blocks: (() => void | object)[]
)
// parallel.output_0, parallel.output_1, … — the outputs each block returned
```

### Parameters

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `annotation` | `string` | No | - | Description/comment |
| `blocks` | `() => void | object` | Yes | - | One or more arrow functions to execute in parallel. A block may `return { ... }` named action outputs to expose them (see Output Bindings). |

### Output Bindings

A block may `return { ... }` the action variables it wants to expose to code after the `doInParallel`. Assign the call to a `const` and dot-walk each block's outputs positionally via `output_<blockIndex>`:

```
const parallel_1 = wfa.flowLogic.doInParallel(
  { $id: Now.ID["parallel_1"] },
  () => {
    const lookup = wfa.action(action.core.lookUpRecord, { $id: Now.ID["lookup"] }, { ... });
    return { lookup };          // block 0
  },
  () => {
    wfa.action(action.core.log, { $id: Now.ID["log"] }, { ... });   // block 1, no output exposed
  },
);

// Reference block 0's `lookup` output after the block:
wfa.flowLogic.if(
  { $id: Now.ID["check"], condition: `${wfa.dataPill(parallel_1.output_0.lookup.__dont_treat_as_error__, "boolean")}=true` },
  () => { ... },
);
```

- `output_<N>` is the block's positional index (`output_0`, `output_1`, …), not a name.

- Only an action declared directly in a block is exposed. An action nested inside an `if`/`elseIf`/`else`/`forEach`/`doTheFollowing` container within the block is not reachable from outside the container — the container exposes no outputs, matching Flow Designer, where a step inside such a container cannot be referenced from outside it.

- Only the outputs a block actually `return`s are exposed; a side-effect-only block returns nothing.

- Hoisting is scoped to `doInParallel`/`tryCatch` — an action output can be exposed to code outside its scope only from a `doInParallel` branch or a `tryCatch` arm. An `if`/`elseIf`/`else`/`forEach`/`doTheFollowing` does not expose its inner actions (its result carries no action outputs to dot-walk); wrap the logic in a `doInParallel` branch or `tryCatch` arm when you need to expose an output downstream.

### Important Constraints

- No nesting — `doInParallel` cannot be used inside another `doInParallel` block

- Minimum 1 block — At least one parallel block is required

- Each block is an arrow function: `() => { ... }`

- Independent execution — blocks may complete in any order; only expose an output for downstream use, never rely on one block reading another block's output mid-run.

## wfa.flowLogic.tryCatch

Creates a try-catch block for error handling in flows.

### Signature

```
const output = wfa.flowLogic.tryCatch(
  params: {
    $id: string,
    annotation?: string
  },
  handlers: {
    try: () => void | object,
    catch: (tryOutputs) => void | object
  }
)
// output.<name> — the outputs either arm returned
```

### Parameters

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `annotation` | `string` | No | - | Description/comment |
| `handlers` | `object` | Yes | - | Object with `try` and `catch` arrow functions |

### Handlers Object

| Property | Type | Required | Description |
| `try` | `() => void | object` | Yes | Arrow function containing code to attempt. May `return { ... }` named outputs. |
| `catch` | `(tryOutputs) => void | object` | Yes | Arrow function to execute if the try block fails. Receives the try arm's outputs as its `tryOutputs` parameter; may `return { ... }` named outputs. |

### Output Bindings

Either arm may `return { ... }` the actions it wants to expose. Assign the call to a `const` and dot-walk the merged outputs directly — there is no `output_N` (the two arms are `try`/`catch`, not positional):

```
const output = wfa.flowLogic.tryCatch(
  { $id: Now.ID["try_catch_1"] },
  {
    try: () => {
      const lookup = wfa.action(action.core.lookUpRecord, { $id: Now.ID["lookup"] }, { ... });
      return { lookup };
    },
    // The catch arm receives the try arm's outputs as `tryOutputs`, so it can inspect a
    // try-arm action (e.g. its failure status) — it must NOT reference the outer `output` const.
    catch: (tryOutputs) => {
      wfa.action(action.core.log, { $id: Now.ID["log"] }, {
        log_level: "error",
        log_message: `${wfa.dataPill(tryOutputs.lookup.__action_status__.message, "string")}`,
      });
    },
  },
);

// output.lookup.<...> is now in scope after the block.
```

- Only an action declared directly in an arm is exposed. An action nested inside an `if`/`elseIf`/`else`/`forEach`/`doTheFollowing` container within the arm is not reachable from outside the container.

- Hoisting is scoped to `doInParallel`/`tryCatch` — an `if`/`elseIf`/`else`/`forEach`/`doTheFollowing` does not expose its inner actions; wrap the logic in a `doInParallel` branch or `tryCatch` arm when you need to hoist an output.

### Important Notes

- Both `try` and `catch` must be arrow functions

- `tryCatch` blocks can be nested

- The catch block executes only if an error occurs in the try block

- Catch reads try-arm outputs via `tryOutputs` — a catch arm references a try-arm action through its `tryOutputs` parameter (`tryOutputs.<name>`), never through the outer `const` (that would be a self-reference the build cannot resolve). The parameter is optional to declare: `catch: () => { ... }` still compiles.

## wfa.flowLogic.doTheFollowing

Executes the body repeatedly until an exit condition is met (do-while semantics — the body always runs at least once, and the exit condition is checked only after each run).

### Signature

```
wfa.flowLogic.doTheFollowing(
  params: {
    $id: string,
    label?: string,
    annotation?: string
  },
  body: () => {
    wfa.action(action.core.<coreAction>, { $id: string }, { ... })  // one or more actions
    wfa.flowLogic.until(condition: string)                          // required — must be the last statement
  }
)
```

### Parameters

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `label` | `string` | No | - | Display label for this loop |
| `annotation` | `string` | No | - | Description/comment |
| `body` | `() => void` | Yes | - | Loop body; must call `wfa.flowLogic.until(...)` as its last statement |

### The `wfa.flowLogic.until()` function

`wfa.flowLogic.until()` sets the loop's exit condition. It is a member of the same `wfa.flowLogic` namespace as `doTheFollowing` — no separate import is needed. See Important Notes below for the last-statement requirement.

```
wfa.flowLogic.until(value: string): string
```

| Parameter | Type | Required | Description |
| `value` | `string` | Yes | Encoded query expression checked after each iteration; may reference `wfa.dataPill(...)` values, including outputs from actions declared earlier in the same body |

### Example

```
wfa.flowLogic.doTheFollowing(
  { $id: Now.ID['do_until_1'], label: 'Retry until resolved' },
  () => {
    const result = wfa.action(
      action.core.lookUpRecord,
      { $id: Now.ID['check_status'] },
      { table_name: 'incident', conditions: `sys_id=${wfa.dataPill(params.trigger.current.sys_id, 'string')}` }
    );
    wfa.flowLogic.until(`${wfa.dataPill(result.Record.state, 'string')}=6`);
  }
);
```

### Important Notes

- Do-While Semantics — The body always executes at least once; the exit condition is checked only after the body runs.

- `wfa.flowLogic.until(...)` Required — A `body` without a `wfa.flowLogic.until(...)` call fails validation at build time.

- `wfa.flowLogic.until(...)`, Not `return` — Using `return` instead of calling `wfa.flowLogic.until(...)` does not satisfy the loop and still fails validation.

- Must Be the Last Statement — `wfa.flowLogic.until(...)` must be the final statement in `body`; any statement after it fails validation at build time.

- Cross-Statement Datapill Access — Because `wfa.flowLogic.until(...)` runs after the body, it can reference data pills from actions declared earlier in the same body.

## wfa.flowLogic.appendToFlowVariables

Appends element(s) to array-typed flow variables.

### Signature

```
wfa.flowLogic.appendToFlowVariables<V>(
  params: {
    $id: string,
    annotation?: string
  },
  variables: V,
  values: Partial<{
    [K in keyof V]: V[K] extends Array<infer E> 
      ? E | E[] | unknown[] | string 
      : never
  }>
)
```

### Parameters

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `annotation` | `string` | No | - | Description/comment |
| `variables` | `V` | Yes | - | Flow variables schema (pass `params.flowVariables` ) |
| `values` | `object` | Yes | - | Key/value pairs where keys are array variable names |

### Value Types

For each array variable, you can append:

- Single element — `{ arrayVar: singleElement }`

- Array of elements — `{ arrayVar: [elem1, elem2, elem3] }`

- Data pill — `{ arrayVar: wfa.dataPill(...) }`

- Template string — `{ arrayVar: 'template expression' }`

### Important Constraints

- Array.Object only — Only supports `FlowArray({ elementType: FlowObject(...) })` variables

- Array elements must be objects or datapill expressions — When appending an array literal, each element must be an object or a datapill expression

- Compile-time safety — TypeScript enforces that target variables are arrays

## wfa.flowLogic.waitForADuration

Pauses flow execution for a specified duration. Supports explicit durations, relative durations, and percentage-based durations.

### Signature

```
wfa.flowLogic.waitForADuration(
  params: WaitForADurationParams
): WaitForADurationOutputs
```

`WaitForADurationParams` is `$id` plus one of three discriminated variants determined by `durationType`:

### Explicit Duration (`durationType: 'explicit_duration'`)

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `durationType` | `'explicit_duration'` | Yes | - | Duration variant selector |
| `duration` | `Duration` | No | - | The duration to wait. When omitted, platform uses zero duration |
| `schedule` | `Record<'cmn_schedule'> | string` | No | - | Optional schedule for business-hours calculation |
| `annotation` | `string` | No | - | Description/comment |
| `uuid` | `string` | No | - | UUID for referencing this instance's outputs as datapills |

### Relative Duration (`durationType: 'relative_duration'`)

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `durationType` | `'relative_duration'` | Yes | - | Duration variant selector |
| `duration` | `Duration` | Yes | - | The duration to offset |
| `relativeOperator` | `'before' | 'after'` | Yes | - | Whether to wait before or after the reference datetime |
| `relativeDatetime` | `string` | Yes | - | Reference datetime for the relative calculation |
| `schedule` | `Record<'cmn_schedule'> | string` | No | - | Optional schedule for business-hours calculation |
| `annotation` | `string` | No | - | Description/comment |
| `uuid` | `string` | No | - | UUID for referencing this instance's outputs as datapills |

### Percentage Duration (`durationType: 'percentage_duration'`)

| Parameter | Type | Required | Default | Description |
| `$id` | `string` | Yes | - | Unique identifier ( `Now.ID['value']` ) |
| `durationType` | `'percentage_duration'` | Yes | - | Duration variant selector |
| `percentage` | `number` | Yes | - | Percentage value for percentage-based duration |
| `percentageDatetime` | `string` | Yes | - | Reference datetime for percentage-based calculation |
| `schedule` | `Record<'cmn_schedule'> | string` | No | - | Optional schedule for business-hours calculation |
| `annotation` | `string` | No | - | Description/comment |
| `uuid` | `string` | No | - | UUID for referencing this instance's outputs as datapills |

### Return Value

| Field | Type | Description |
| `total_duration` | `Duration` | The total duration that was waited |
| `scheduled_end_date_time` | `datetime` | The scheduled end date/time when the wait completed |

## wfa.flowLogic.assignSubflowOutputs

Assigns the subflow's output values from within the subflow body, mapping declared output names to values, datapill references, or template literals. This is the recommended way to set subflow outputs based on step results. Type-only helper — erased at runtime.

### Signature

```
wfa.flowLogic.assignSubflowOutputs(
  definition: { $id: string, annotation?: string },
  variables: TOutputs,         // always pass params.outputs
  values: Partial<TOutputs>    // fields to assign; omitted fields are undefined
)
```

### Parameters

| Parameter | Type | Required | Description |
| `$id` | `string` | Yes | Unique identifier for this assignment node |
| `annotation` | `string` | No | Description/comment |
| `variables` | `TOutputs` | Yes | Always pass `params.outputs` -- do not construct a custom object |
| `values` | `Partial<TOutputs>` | Yes | Key/value pairs to assign. Values may be literals or data pills |

⚠️ Type-only helper. This call is erased at runtime; it exists for compile-time type safety.

## wfa.flowLogic.setFlowVariables

Assigns values to flow-scoped variables declared in the Flow or Subflow config `flowVariables` property. Each call produces a `sys_hub_flow_logic_instance_v2` record whose `values` field contains the serialized assignment JSON.

### Signature

```
wfa.flowLogic.setFlowVariables(
  definition: { $id: string, annotation?: string },
  variables: FlowSchemaType<S>,
  values: { [K in keyof FlowSchemaType<S>]?: FlowSchemaType<S>[K] | string }
)
```

### Parameters

| Parameter | Type | Required | Description |
| `$id` | `string` | Yes | Unique identifier ( `Now.ID['value']` ) |
| `annotation` | `string` | No | Description/comment |
| `variables` | `FlowSchemaType<S>` | Yes | Flow variables schema — always pass `params.flowVariables` |
| `values` | `Partial record` | Yes | Key/value pairs of variables to set. Omitted keys are unchanged. |

### Value Types

For each variable entry in `values`, you can supply:

- Typed literal — `{ myVar: 'hello' }`, `{ count: 42 }`

- Data pill — `{ myVar: wfa.dataPill(params.trigger.current.short_description, 'string') }`

- Template string — `{ myVar: 'template expression' }`

- Inline script — `{ myVar: wfa.inlineScript('return fd_data.trigger.current.number;') }`

`null` and `undefined` are not valid — omit the key instead of setting it to null.

### Important Notes

- Always pass `params.flowVariables` as the `variables` argument — never construct a custom object.

- Only the keys listed in `values` are updated; other flow variables retain their current values.

- Flow variables are scoped to the current flow or subflow execution — they are not visible to called subflows.

## Condition Syntax Reference

Flow logic conditions use ServiceNow encoded query format.

### Comparison Operators

| Operator | Description | Example |
| `=` | Equals | `priority=1` |
| `!=` | Not equals | `state!=6` |
| `<` | Less than | `priority<3` |
| `<=` | Less or equal | `priority<=2` |
| `>` | Greater than | `priority>3` |
| `>=` | Greater or equal | `priority>=2` |

### Empty/Not Empty Operators

| Operator | Description | Example |
| `ISEMPTY` | Field is empty | `assigned_toISEMPTY` |
| `ISNOTEMPTY` | Field has value | `assignment_groupISNOTEMPTY` |

### List Operators

| Operator | Description | Example |
| `IN` | In list | `stateIN1,2,3` |
| `NOT IN` | Not in list | `stateNOT IN6,7` |

### String Operators

| Operator | Description | Example |
| `STARTSWITH` | Starts with | `numberSTARTSWITHINC` |
| `ENDSWITH` | Ends with | `emailENDSWITH@company.com` |
| `LIKE` | Contains | `short_descriptionLIKEfailed` |

### Logical Operators

| Operator | Description | Example |
| `^` or `^AND` | Logical AND | `priority=1^active=true` |
| `^OR` | Logical OR | `priority=1^ORpriority=2` |
| `^NQ` | New query (OR group) | `priority=1^NQstate=2` |

For usage patterns, examples, best practices, and end-to-end flow logic examples, see the Flow Logic Guide.

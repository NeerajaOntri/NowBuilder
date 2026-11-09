Version: 4.14.0

# Encoded Queries

How to build well-formed ServiceNow encoded query strings — the compact field-operator-value syntax used by most `condition` and `filter` fields across the Fluent APIs (Business Rules, ACLs, SLAs, Data Policies, UI Policies, Email Notifications, Flow triggers, and more) and by `now-sdk query --query`.

An encoded query is a single string that expresses one or more filter conditions. It is the same string the platform stores when you build a filter in the UI, and the same value the GlideRecord `addEncodedQuery()` API accepts. Whenever a Fluent API exposes a `condition`, `conditions`, `filter`, or `whenToApply`-style string, that string is an encoded query.

## Anatomy

A single condition is three parts with no spaces:

```
<field><operator><value>
```

```
active=true
priority<=2
short_descriptionLIKEnetwork
```

Multiple conditions are joined with separators:

```
active=true^priority<=2
```

- `^` — AND: both conditions must match

- `^OR` — OR: either the preceding or following condition matches

- `^NQ` — NewQuery (OR): starts a new independent query; a record matches if it satisfies any of the `^NQ`-separated groups

```
// active AND priority <= 2
condition: 'active=true^priority<=2'

// priority 1 OR priority 2
condition: 'priority=1^ORpriority=2'

// (active=true AND priority=1)  OR  (active=false AND category=hardware)
condition: 'active=true^priority=1^NQactive=false^category=hardware'
```

Precedence: `^OR` binds only to the single condition immediately before and after it. To express grouped OR logic across multiple ANDed conditions, use `^NQ` to start a fresh group.

## Operators

### Comparison

| Operator | Meaning | Example |
| `=` | equals | `state=1` |
| `!=` | not equals | `state!=6` |
| `>` | greater than | `priority>2` |
| `>=` | greater than or equal | `priority>=2` |
| `<` | less than | `priority<3` |
| `<=` | less than or equal | `priority<=2` |
| `BETWEEN` | within an inclusive range (numbers/dates) | `priorityBETWEEN1@3` |

### String matching

| Operator | Meaning | Example |
| `LIKE` | contains | `short_descriptionLIKEoutage` |
| `NOTLIKE` | does not contain | `short_descriptionNOTLIKEtest` |
| `STARTSWITH` | begins with | `numberSTARTSWITHINC` |
| `ENDSWITH` | ends with | `numberENDSWITH001` |

### Empty / presence

| Operator | Meaning | Example |
| `ISEMPTY` | field has no value | `assigned_toISEMPTY` |
| `ISNOTEMPTY` | field has any value | `assigned_toISNOTEMPTY` |
| `ANYTHING` | matches all rows (no filter) | `assigned_toANYTHING` |

### Sets

| Operator | Meaning | Example |
| `IN` | value is in a comma-separated list | `stateIN1,2,3` |
| `NOT IN` | value is not in the list | `stateNOT IN6,7,8` |

### Dates

| Operator | Meaning | Example |
| `ON` | on a relative/named date range | `sys_created_onONToday@javascript:gs.beginningOfToday()@javascript:gs.endOfToday()` |
| `NOTON` | not on a date range | `sys_created_onNOTONToday@...@...` |
| `>=` / `<=` | with `javascript:` date functions | `sys_created_on>=javascript:gs.daysAgoStart(7)` |

Date values frequently use `javascript:` glide functions:

```
sys_created_on>=javascript:gs.daysAgoStart(7)
sys_created_on<javascript:gs.beginningOfToday()
```

## Values

- Booleans: `active=true` / `active=false` (some choice/boolean fields store `1`/`0`).

- Choice fields: use the stored value, not the label — `state=2`, not `state=In Progress`.

- Reference fields: use the sys_id — `assignment_group=8a4dde73c6112278017a6a4baf547aa7`.

- Empty value: an equals with nothing after it tests for empty — `assignment_group=`.

- Multiple values (IN): comma-separated, no spaces around commas — `stateIN1,2,3`.

## Escaping values

There are two distinct layers to think about: the query syntax (characters that mean something to ServiceNow) and the TypeScript string literal (characters that mean something to the compiler). Both matter because a Fluent `condition` is a TS string that the platform later parses as an encoded query.

### Reserved characters in the query syntax

These characters are structural — the platform interprets them, so a value that contains one cannot be expressed literally:

| Character | Role in the query | Why it's a problem in a value |
| `^` | condition separator ( `^` , `^OR` , `^NQ` , `^EQ` , `^ORDERBY` ) | a value containing `^` is read as the start of a new condition |
| `,` | item separator inside `IN` / `NOT IN` lists | a value containing `,` is split into multiple list items |
| `@` | range separator for `BETWEEN` / `ON` | a value containing `@` is read as a range delimiter |
| `=` `!` `<` `>` | operator characters | only meaningful in the operator position, but avoid leading a value with them |

ServiceNow provides no escape character for these inside encoded query values. If the data you need to match genuinely contains a `^`, a comma (in an `IN` list), or an `@` (in a range), an encoded query cannot express it precisely. Work around it instead:

- Match on a substring that excludes the reserved character with `LIKE` — e.g. for a value `A^B`, use `fieldLIKEA` (accepting that it is a looser match).

- For reference-qualifier scenarios, switch to a scripted qualifier (`javascript:` / a reference qualifier function) where you have full control over the comparison rather than encoding it as a literal.

- Filter on a different, cleaner field (such as a sys_id) when one is available.

### Whitespace

Spaces inside a value are significant — `short_descriptionLIKE outage` searches for `" outage"` with a leading space. Never pad values for readability. The only operator that legitimately contains a space is `NOT IN`.

### TypeScript string-literal escaping

Because the condition is a TS string, escape characters that the compiler cares about — independently of the query syntax:

- 
Apostrophe in a single-quoted string — escape with `\'`, or switch the surrounding quotes to double quotes:

```
condition: 'short_descriptionLIKEO\'Brien'      // escaped apostrophe
condition: "short_descriptionLIKEO'Brien"       // or use double quotes
```

- 
Backslash — a literal backslash in the value must be doubled (`\\`), since `\` is the TS escape character:

```
condition: 'pathLIKEC:\\\\temp'                 // matches the value  C:\temp
```

- 
Datapill / dynamic values — use a template literal (backticks) so you can interpolate without quote juggling. The interpolated value is inserted verbatim, so it must still respect the query-syntax rules above:

```
condition: `priority=${wfa.dataPill(params.inputs.priority, 'integer')}`
```

The TS-literal escaping (`\'`, `\\`) only affects what string the compiler produces. It does not escape the query-syntax characters in the previous section — once the compiler hands the finished string to the platform, `^`, `,`, and `@` are still structural.

## Dot-walking

Walk through reference fields with `.` to filter on a related record's field:

```
// VIP callers only
condition: 'caller_id.vip=true'

// assigned to anyone in the Network department
condition: 'assigned_to.department.name=Network'
```

## Dynamic filters

`DYNAMIC` references a dynamic filter option (`sys_filter_option_dynamic`) by sys_id — for example, "Me", "My groups", or a custom dynamic filter:

```
// assigned to the current user (the "Me" dynamic filter)
condition: 'assigned_toDYNAMIC90d1921e5f510100a9ad2572f2b477fe'
```

## Ordering

Append ordering clauses to sort results (used by list filters and queries, ignored by most boolean condition fields):

| Clause | Meaning |
| `^ORDERBY<field>` | sort ascending by field |
| `^ORDERBYDESC<field>` | sort descending by field |

```
active=true^ORDERBYDESCsys_created_on
priority<=2^ORDERBYpriority^ORDERBYDESCsys_updated_on
```

## The trailing `^EQ` marker

You will often see queries that end in `^EQ`:

```
condition: 'active=true^EQ'
```

`^EQ` is the end-of-query marker that the platform's condition builder appends when it saves a filter. It is optional in hand-written queries — `'active=true'` and `'active=true^EQ'` behave identically. Include it if you are copying a query verbatim from the platform; omit it for cleaner, hand-authored conditions.

## Generating a query from the UI

The fastest way to get a correct, complex encoded query is to let the platform build it:

- Open the list for the table in the ServiceNow UI.

- Build the filter with the condition builder (the funnel icon).

- Click Run, then right-click the breadcrumb at the top of the list.

- Choose Copy query — this places the encoded query string on your clipboard.

Paste that string directly into your `condition` field. You can then simplify it (e.g. drop the trailing `^EQ`) for readability.

You can also verify a query against live data without leaving the SDK:

```
now-sdk query incident --query 'active=true^priority<=2^ORDERBYDESCsys_created_on' --fields number,priority
```

See the `query` topic for the full `now-sdk query` reference.

## Common mistakes

- Using `AND` / `OR` words instead of separators. Use `^` and `^OR`, never the literal words `AND`/`OR`.

- Adding spaces. `priority = 2` is wrong; write `priority=2`. (The one exception is the `NOT IN` operator, which contains a space.)

- Using choice labels instead of values. Filter on the stored value (`state=2`), not the display label.

- Expecting `^OR` to group. `^OR` only joins the two adjacent conditions. Use `^NQ` to OR together multi-condition groups.

- Quoting values. Do not wrap values in quotes inside the query string — `short_descriptionLIKEoutage`, not `short_descriptionLIKE"outage"`.

## Where encoded queries appear in Fluent

The same syntax is used by the `condition` / `filter` string on many APIs, including:

- Business Rules — `condition` (`business-rule-guide`)

- ACLs — `condition` (`security-guide`)

- Data Policies — `conditions` (`data-policy-guide`)

- UI Policies and Catalog UI Policies — `condition`

- SLAs — start/stop/pause/reset conditions (`sla-api`)

- Email Notifications — `condition` (`email-notification-guide`)

- Flow / Subflow record triggers — trigger `condition` (`wfa-trigger-guide`)

- Assignment Rules — `condition` (`assignment-rule-guide`)

- `now-sdk query` — `--query` (`query` topic)

In every case the value is a plain encoded query string built from the rules above.

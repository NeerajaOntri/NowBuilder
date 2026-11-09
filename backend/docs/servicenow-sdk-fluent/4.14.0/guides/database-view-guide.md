Version: 4.14.0

# Database Views

Guide for creating ServiceNow Database Views (`sys_db_view`) using the Fluent API. A Database View is a read-only virtual table that SQL-joins two or more real tables into a single reportable pseudo-table, exposing selected columns from each joined table under a per-table variable prefix. Use it when you need to report across, or build lists/queries on top of, data that already lives in other tables — a Database View stores no data of its own.

## When to Use

Use DatabaseView when:

- You need to report on, list, create a dashboard or query data that spans two or more existing tables joined together (e.g. incidents joined to their caller's user record).

- The requirement is read-only reporting/querying — the view itself never receives writes.

- You need a LEFT OUTER JOIN so rows from one table still appear even when there's no match in a joined table (e.g. "incidents with no assignment group").

- The mapping is a straightforward join on existing fields, not a computed or scripted aggregation.

Avoid these alternatives when a Database View applies:

- Do not create a new table just to store a computed or aggregated value — if the underlying data already exists in related tables, join it with a view instead. (A new table is only correct when new data must be written, e.g. logging an event that doesn't exist yet.)

- Do not write a Script Include to manually aggregate across GlideRecord queries when the same result can be produced by a Database View plus a report/widget — this applies even for multi-hop chains.

- Dot-walking a single reference field in a widget is fine for one-hop, per-record lookups — but once you need to group or aggregate by a related field, even one hop away, use a Database View instead.

Note: use `Table()` instead when you need a real table that stores its own data — a Database View has no schema or columns of its own; it only exposes columns that already exist on the tables it joins.
Note: use `List()` instead when you're defining a UI list layout for a single table's own columns, not joining multiple tables together.

## Key Concepts

### How a Database View Is Structured

A `DatabaseView` is three levels of records working together as one entity:

- The view (`sys_db_view`) — `name`, `label`, `plural`, `description`.

- Joined tables (`tables[]`, one `sys_db_view_table` record each) — which table to join, the join type, join order, and an optional join predicate (`whereClause`).

- Selected fields (`fields[]` per table, one `sys_db_view_table_field` record each) — which columns from that joined table to expose in the view. Commonly empty — many real views join a table purely to supply a join condition via `whereClause` without exposing any of its columns.

### Join Order and the Base Table

The first entry in `tables[]` (lowest `order` value, default `100`) is effectively the base/primary table of the join. Subsequent tables (higher `order`) are joined against it using `whereClause`. Put the most selective or smallest table first — join order affects query performance on large tables.

### Inner Join vs Left Join

- `leftJoin: false` (default) — INNER JOIN. Only rows with a match in every joined table appear in the view.

- `leftJoin: true` — LEFT OUTER JOIN. All rows from the tables joined so far appear; columns from this table are empty where there's no match. Use this for "find records with no related X" style reporting (e.g. incidents with no assignment group).

### The `whereClause` Is a Raw Join Predicate, Not an Encoded Query

`whereClause` is not a ServiceNow encoded query — it does not use `^` for AND or `^OR` for OR the way encoded query strings do. It's a raw predicate over `variablePrefix`-qualified field names, using comparison and logical operators (`=`, `!=`, `<`, `<=`, `>`, `>=`, `&&`, `||`), e.g. `inc_caller_id=usr_sys_id`. Use `||` to OR together multiple conditions, e.g. `inc_rfc=chg_sys_id || chg_parent=inc_sys_id` matches incidents related to an RFC OR incidents that are the parent of a change request. `LIKE` and `CONTAINS` are not supported — to match against the full dataset, join tables on `sys_id` using `=`. Each table's `variablePrefix` disambiguates its fields within these predicates — every table must have its own prefix.

### Variable Prefix Rules

`variablePrefix` disambiguates a joined table's columns inside `whereClause` (e.g. `usr` for the `sys_user` table, referenced as `usr_sys_id`). The platform rejects prefixes containing an underscore or exceeding 30 characters, and the plugin additionally rejects two tables in the same view sharing the same prefix.

Best practice: use only lowercase characters in `variablePrefix`. This isn't enforced by the platform or the plugin, but ServiceNow's documentation notes that using uppercase characters may prevent you from viewing the database view in a list.

### Name Normalization

The platform silently normalizes `name` (lowercase, non-alphanumeric characters replaced with `_`) before storing it, and aborts the save if a real table or another Database View already has the resulting name. Because `name` is the coalesce key used to identify this record across rebuilds, supply an already-normalized name — the plugin emits a build error if the supplied name doesn't already match its normalized form, since a mismatch would cause the next build to create a duplicate view instead of updating this one.

Scope prefix: in a customer scope (any scope starting with `x_`), `name` must also carry the scope prefix (e.g. `x_acme_my_view`). For global scope, `name` must start with the custom `u_` prefix. Internal `sn_`/`now_` scoped apps are exempt from the prefix requirement.

### Field Selection Is Optional Per Table

`fields` on a `tables[]` entry is optional. A table can be joined purely to constrain the result set through a join condition (via `whereClause`) without exposing any of its own columns — this is common and not an incomplete configuration.

But once a table's `fields` list is non-empty, it becomes an allowlist for that table — including for the join engine itself. If any `whereClause` in the view — including this table's own — references one of this table's columns, that column must appear in this table's own `fields` list or the join fails.

### Calculated Columns via Function Fields

Add a calculated column on top of the joined data (e.g. concatenating two joined columns) with a function field: a `Table({ augments })` call targeting the view's `name`, using `functionDefinition` on a `Column()` in its `schema`, with `glidefunction:` syntax referencing the view's `variablePrefix`-qualified columns (e.g. `glidefunction:concat(usr_name,' - ',inc_short_description)`). See the `table-augments-guide` topic for the full `augments` pattern, and the example below.

### Feeding Dashboards and Widgets

A database view works as a data source anywhere a table can, but dashboards and widgets are the preferred ServiceNow approach for reporting and data analysis. The `Dashboard()` API (see the `dashboard-api` topic) consumes a view per widget through `componentProps.dataSources[]` entries: each data source's `tableOrViewName` property accepts the view's `name`, and `metrics`/`groupBy` drive the same aggregation a `GlideAggregate` query would perform against the view directly.

Classic reports (`sys_report`) can also reference the view's `name` in their `table` field via the generic `Record()` API, but new reporting should generally be built with dashboards. See the example below.

### Platform Limitations

- Table rotation — a database view cannot be created on a table that participates in table rotation. This is unlikely to affect the ITSM-style joins used throughout this guide: table rotation cannot be applied to `sys_import` tables or to any table that extends Task `[task]` — which rules out `incident`, `problem`, `change_request`, `sc_task`, and every other task-derived table. Where rotation does commonly apply is on high-volume log/queue tables, e.g. `ecc_queue`/`ecc_queue_event` (ECC Queue), `em_event` (Event Management), `sys_history_set` (History), `sys_flow_log` (Flow Designer execution logging), and `cmdb_ire_incomplete_payloads` (CMDB IRE).

- FTP exports — database view tables are not included in FTP exports.

- Clone data preservers — database view tables cannot be added as a data preserver in clone requests.

- Query performance — the accumulated performance impact grows with the number of joined tables and the size of their underlying data. Base `whereClause` predicates on indexed fields to keep query performance acceptable, in addition to ordering the smallest/most selective table first (see "Join Order and the Base Table" above).

## Instructions

- Identify the tables to join and their join order — put the most selective/smallest table first (`order: 100`), then add joined tables at increasing `order` values (`200`, `300`, ...).

- Assign a unique `variablePrefix` to every table — short, no underscores, 30 characters or fewer, and unique within the view.

- Decide inner vs left join per non-base table — use `leftJoin: true` only when you need unmatched rows from prior tables to still appear.

- Write `whereClause` predicates using `{variablePrefix}_{field}` on both sides of the comparison, not encoded-query syntax — combine multiple conditions with `&&`/`||` rather than `^`/`^OR`, and avoid `LIKE`/`CONTAINS`, which aren't supported.

- Select only the fields you need to expose — omit `fields` entirely on tables joined purely to supply a join condition.

- Supply an already-normalized `name` — lowercase, with any non-alphanumeric character replaced by `_`. Do not rely on the platform to normalize it for you; a mismatch is a build error.

- In a customer scope (any scope starting with `x_`), prefix `name` with the scope (e.g. `x_acme_my_view`); in the global scope, prefix `name` with `u_` instead. Internal `sn_`/`now_` scoped apps are exempt (see "Name Normalization" above).

- Give every joined table a `$id`

- Give every field a `$id`

## API Reference

See the `databaseview-api` topic for the full property reference.

## Examples

### Basic — Single Table, No Field Selection

The simplest valid view — joins one table with no exposed columns.

```
import { DatabaseView } from '@servicenow/sdk/core'

DatabaseView({
    name: 'x_snc_database_view_basic',
    tables: [{ $id: Now.ID['database-view-basic-table'], table: 'incident', variablePrefix: 'inc' }],
})
```

### With Field Selection — Two-Table Inner Join

Joins incidents to their caller and exposes selected columns from each table.

```
import { DatabaseView } from '@servicenow/sdk/core'

DatabaseView({
    name: 'x_snc_database_view_with_fields',
    label: 'Incidents With Selected Fields',
    tables: [
        {
            $id: Now.ID['database-view-with-fields-table'],
            table: 'incident',
            variablePrefix: 'inc',
            fields: [
                { $id: Now.ID['guide-with-fields-number'], field: 'number' },
                { $id: Now.ID['guide-with-fields-short-description'], field: 'short_description' },
                { $id: Now.ID['guide-with-fields-priority'], field: 'priority' },
            ],
        },
    ],
})
```

### With Left Join — Include Rows With No Match

Reports on incidents even when they have no assignment group, using `leftJoin: true` and a `whereClause` predicate.

```
import { DatabaseView } from '@servicenow/sdk/core'

DatabaseView({
    name: 'x_snc_database_view_left_join',
    description: 'Incidents joined to assignment group, including incidents with no group',
    tables: [
        { $id: Now.ID['database-view-left-join-incident-table'], table: 'incident', variablePrefix: 'inc', order: 100 },
        {
            $id: Now.ID['database-view-left-join-group-table'],
            table: 'sys_user_group',
            variablePrefix: 'grp',
            order: 200,
            leftJoin: true,
            whereClause: 'inc_assignment_group=grp_sys_id',
            fields: [
                { $id: Now.ID['guide-left-join-group-sys-id'], field: 'sys_id' },
                { $id: Now.ID['guide-left-join-group-name'], field: 'name' },
            ],
        },
    ],
})
```

### Advanced — Multiple Tables, Field Selection, and a Left Join Combined

Combines an inner join (caller) with a left join (assignment group), field selection on every table, and explicit join ordering.

```
import { DatabaseView } from '@servicenow/sdk/core'

DatabaseView({
    name: 'x_snc_database_view_advanced',
    label: 'Incidents With Caller And Group',
    plural: 'Incidents With Caller And Group',
    description: 'Joins incidents to caller and assignment group for reporting',
    tables: [
        {
            $id: Now.ID['database-view-advanced-incident-table'],
            table: 'incident',
            variablePrefix: 'inc',
            order: 100,
            fields: [
                { $id: Now.ID['guide-advanced-incident-number'], field: 'number' },
                { $id: Now.ID['guide-advanced-incident-short-description'], field: 'short_description' },
                { $id: Now.ID['guide-advanced-incident-caller-id'], field: 'caller_id' },
                { $id: Now.ID['guide-advanced-incident-assignment-group'], field: 'assignment_group' },
            ],
        },
        {
            $id: Now.ID['database-view-advanced-caller-table'],
            table: 'sys_user',
            variablePrefix: 'usr',
            order: 200,
            whereClause: 'inc_caller_id=usr_sys_id',
            fields: [
                { $id: Now.ID['guide-advanced-caller-sys-id'], field: 'sys_id' },
                { $id: Now.ID['guide-advanced-caller-name'], field: 'name' },
                { $id: Now.ID['guide-advanced-caller-email'], field: 'email' },
            ],
        },
        {
            $id: Now.ID['database-view-advanced-group-table'],
            table: 'sys_user_group',
            variablePrefix: 'grp',
            order: 300,
            leftJoin: true,
            whereClause: 'inc_assignment_group=grp_sys_id',
            fields: [
                { $id: Now.ID['guide-advanced-group-sys-id'], field: 'sys_id' },
                { $id: Now.ID['guide-advanced-group-name'], field: 'name' },
            ],
        },
    ],
})
```

### End-to-End Example — Custom Tables, Database View, and Dashboard

This example builds an Equipment Manager that creates custom tables to track inventory and loaner equipment, then generates a Database View to join four tables into a single reporting surface consumed by a Dashboard.

#### Step 1 — Define Custom Tables

```
// src/fluent/tables.now.ts
import { Table, StringColumn, ChoiceColumn, ReferenceColumn, DateColumn } from '@servicenow/sdk/core'

export const x_example_app_equipment = Table({
    name: 'x_example_app_equipment',
    label: 'Loaner Equipment',
    display: 'name',
    allowWebServiceAccess: true,
    schema: {
        name: StringColumn({
            label: 'Equipment Name',
            mandatory: true,
            maxLength: 100,
        }),
        type: ChoiceColumn({
            label: 'Equipment Type',
            mandatory: true,
            choices: {
                laptop: 'Laptop',
                tablet: 'Tablet',
                phone: 'Phone',
                monitor: 'Monitor',
            },
            dropdown: 'dropdown_with_none',
        }),
        serial_number: StringColumn({
            label: 'Serial Number',
            mandatory: true,
            maxLength: 100,
        }),
        status: ChoiceColumn({
            label: 'Availability Status',
            mandatory: true,
            choices: {
                available: 'Available',
                on_loan: 'On Loan',
                maintenance: 'In Maintenance',
                retired: 'Retired',
            },
            default: 'available',
            dropdown: 'dropdown_with_none',
        }),
    },
})

export const x_example_app_loan = Table({
    name: 'x_example_app_loan',
    label: 'Equipment Loan',
    display: 'equipment',
    allowWebServiceAccess: true,
    schema: {
        equipment: ReferenceColumn({
            label: 'Equipment',
            referenceTable: 'x_example_app_equipment',
            mandatory: true,
        }),
        borrower: ReferenceColumn({
            label: 'Borrower',
            referenceTable: 'sys_user',
            mandatory: true,
        }),
        loan_date: DateColumn({
            label: 'Loan Date',
            mandatory: true,
        }),
        due_date: DateColumn({
            label: 'Due Date',
            mandatory: true,
        }),
        return_date: DateColumn({
            label: 'Return Date',
        }),
        status: ChoiceColumn({
            label: 'Loan Status',
            mandatory: true,
            choices: {
                active: 'Active',
                returned: 'Returned',
                overdue: 'Overdue',
            },
            default: 'active',
            dropdown: 'dropdown_with_none',
        }),
    },
})
```

#### Step 2 — Create the Database View

The Database View joins four tables into a single flat, reportable surface:

- Loan (base table, `order: 100`) — the primary data

- Equipment (inner join, `order: 200`) — joined via `ln_equipment = eq_sys_id`

- User (inner join, `order: 300`) — joined via `ln_borrower = usr_sys_id`

- Department (left join, `order: 400`) — joined via `usr_department = dept_sys_id` (left join because some users may not have a department)

Key points:

- Every table's `fields` list must include any column referenced in a `whereClause` — including that table's own `sys_id` when another table joins against it.

- `variablePrefix` cannot contain underscores and must be unique within the view.

- Use `leftJoin: true` when unmatched rows (e.g., users without a department) should still appear.

```
// src/fluent/database-view.now.ts
import { DatabaseView } from '@servicenow/sdk/core'

DatabaseView({
    name: 'x_example_app_loan_report',
    label: 'Loan Details Report View',
    plural: 'Loan Details Report Views',
    description: 'Joins loans with equipment, borrower, and department for cross-table reporting',
    tables: [
        // Base table — the loan records
        {
            $id: Now.ID['view-loan-table'],
            table: 'x_example_app_loan',
            variablePrefix: 'ln',
            order: 100,
            fields: [
                { $id: Now.ID['view-ln-sys-id'], field: 'sys_id' },
                { $id: Now.ID['view-ln-equipment'], field: 'equipment' },
                { $id: Now.ID['view-ln-borrower'], field: 'borrower' },
                { $id: Now.ID['view-ln-loan-date'], field: 'loan_date' },
                { $id: Now.ID['view-ln-due-date'], field: 'due_date' },
                { $id: Now.ID['view-ln-return-date'], field: 'return_date' },
                { $id: Now.ID['view-ln-status'], field: 'status' },
            ],
        },
        // Inner join — equipment details
        {
            $id: Now.ID['view-equipment-table'],
            table: 'x_example_app_equipment',
            variablePrefix: 'eq',
            order: 200,
            whereClause: 'ln_equipment=eq_sys_id',
            fields: [
                { $id: Now.ID['view-eq-sys-id'], field: 'sys_id' },
                { $id: Now.ID['view-eq-name'], field: 'name' },
                { $id: Now.ID['view-eq-type'], field: 'type' },
                { $id: Now.ID['view-eq-serial-number'], field: 'serial_number' },
            ],
        },
        // Inner join — borrower user record
        {
            $id: Now.ID['view-user-table'],
            table: 'sys_user',
            variablePrefix: 'usr',
            order: 300,
            whereClause: 'ln_borrower=usr_sys_id',
            fields: [
                { $id: Now.ID['view-usr-sys-id'], field: 'sys_id' },
                { $id: Now.ID['view-usr-name'], field: 'name' },
                { $id: Now.ID['view-usr-email'], field: 'email' },
                { $id: Now.ID['view-usr-department'], field: 'department' },
            ],
        },
        // Left join — department (some users may not have one)
        {
            $id: Now.ID['view-department-table'],
            table: 'cmn_department',
            variablePrefix: 'dept',
            order: 400,
            leftJoin: true,
            whereClause: 'usr_department=dept_sys_id',
            fields: [
                { $id: Now.ID['view-dept-sys-id'], field: 'sys_id' },
                { $id: Now.ID['view-dept-name'], field: 'name' },
            ],
        },
    ],
})
```

#### Step 3 — End-to-End Example (Tables, Database View, Dashboard)

This example builds a Retail Store Monitor that creates custom tables to track regions, stores, and inventory items, then generates a Database View to join three tables into a single reporting surface consumed by a Dashboard.

##### Step 1 — Define Custom Tables

This example uses three custom tables that form a reference chain: Region ← Store ← Inventory Item. The Store table has a reference field to Region, and the Inventory Item table has a reference field to Store.

| Table | Purpose | Key fields | Reference |
| Region ( `x_retail_store_mo_region` ) | Geographic region | name, description | — |
| Store ( `x_retail_store_mo_store` ) | Retail store | name, region, address, manager, status | region → Region |
| Inventory Item ( `x_retail_store_mo_inventory` ) | Inventory in a store | name, store, category, quantity, unit_price | store → Store |

Create a `Form()` layout for each table so users can add and edit records. See the `table-guide` topic for creating tables and columns, and the `form-layout-guide` topic for arranging fields on forms.

##### Step 2 — Create the Database View

The Database View joins three tables into a single flat, reportable surface:

Inventory Item (base table, order: 100) — the primary data with quantity and unit price
Store (inner join, order: 200) — joined via inv_store = str_sys_id
Region (inner join, order: 300) — joined via str_region = reg_sys_id
Key points:

The view chains through two hops (Inventory → Store → Region) using inner joins — only inventory items with a valid store AND a valid region appear.
Every table's fields list includes sys_id and any column referenced in a whereClause (e.g., store on Inventory is needed for the Store join, region on Store is needed for the Region join).
variablePrefix values (inv, str, reg) are short, contain no underscores, and are unique within the view.
The Dashboard consumes this view using variablePrefix-qualified field names (e.g., inv_unit_price, reg_name).

```
// src/fluent/database-view.now.ts
import { DatabaseView } from '@servicenow/sdk/core'

DatabaseView({
    name: 'x_retail_store_mo_inv_region',
    label: 'Inventory by Region',
    plural: 'Inventory by Region',
    description: 'Joins inventory items through stores to regions for inventory value reporting',
    tables: [
        // Base table — inventory items
        {
            $id: Now.ID['view-inventory-table'],
            table: 'x_retail_store_mo_inventory',
            variablePrefix: 'inv',
            order: 100,
            fields: [
                { $id: Now.ID['view-inv-sys-id'], field: 'sys_id' },
                { $id: Now.ID['view-inv-name'], field: 'name' },
                { $id: Now.ID['view-inv-quantity'], field: 'quantity' },
                { $id: Now.ID['view-inv-unit-price'], field: 'unit_price' },
                { $id: Now.ID['view-inv-store'], field: 'store' },
                { $id: Now.ID['view-inv-category'], field: 'category' },
            ],
        },
        // Inner join — store details
        {
            $id: Now.ID['view-store-table'],
            table: 'x_retail_store_mo_store',
            variablePrefix: 'str',
            order: 200,
            whereClause: 'inv_store=str_sys_id',
            fields: [
                { $id: Now.ID['view-str-sys-id'], field: 'sys_id' },
                { $id: Now.ID['view-str-name'], field: 'name' },
                { $id: Now.ID['view-str-region'], field: 'region' },
            ],
        },
        // Inner join — region details
        {
            $id: Now.ID['view-region-table'],
            table: 'x_retail_store_mo_region',
            variablePrefix: 'reg',
            order: 300,
            whereClause: 'str_region=reg_sys_id',
            fields: [
                { $id: Now.ID['view-reg-sys-id'], field: 'sys_id' },
                { $id: Now.ID['view-reg-name'], field: 'name' },
            ],
        },
    ],
})
```

#### Step 3 — Build a Dashboard on the View

The Dashboard consumes both the raw tables (for KPI counts) and the Database View (for grouped breakdowns by region and category). It uses three widget types:

| Widget | Component | Data Source | Purpose |
| Total Inventory Items | single-score | Inventory table, no filter | KPI count |
| Open Stores | single-score | Store table, status=open | KPI count |
| Inventory Value per Region | vertical-bar | Database view, grouped by reg_name, SUM on inv_unit_price | Bar chart |
| Items by Category | pie | Database view, grouped by inv_category | Pie chart |

Key points:
tableOrViewName accepts either a real table name or a database view name.
For view-backed widgets, field and groupBy use variablePrefix-qualified names (e.g., inv_unit_price, reg_name, inv_category).
aggregateFunction: 'SUM' with field: 'inv_unit_price' computes total inventory value; 'COUNT' counts records.
Widget position uses a grid coordinate system (x, y) with width/height in grid units.

```
// src/fluent/dashboard.now.ts
import { Dashboard } from '@servicenow/sdk/core'

Dashboard({
    $id: Now.ID['retail-dashboard'],
    name: 'Retail Store Monitor',
    description: 'Business owner dashboard showing inventory value and distribution across regions',
    tabs: [
        {
            $id: Now.ID['dashboard-overview-tab'],
            name: 'Inventory Overview',
            widgets: [
                // ─── KPI: Total Inventory Items ───
                {
                    $id: Now.ID['widget-total-items'],
                    component: 'single-score',
                    componentProps: {
                        dataSources: [
                            {
                                label: 'Total Inventory Items',
                                sourceType: 'table',
                                tableOrViewName: 'x_retail_store_mo_inventory',
                                filterQuery: '',
                                id: 'ds_total_items',
                            },
                        ],
                        headerTitle: 'Total Inventory Items',
                        metrics: [
                            {
                                dataSource: 'ds_total_items',
                                id: 'metric_total_items',
                                aggregateFunction: 'COUNT',
                                axisId: 'primary',
                            },
                        ],
                    },
                    height: 10,
                    width: 6,
                    position: { x: 0, y: 0 },
                },
                // ─── KPI: Open Stores ───
                {
                    $id: Now.ID['widget-total-stores'],
                    component: 'single-score',
                    componentProps: {
                        dataSources: [
                            {
                                label: 'Total Stores',
                                sourceType: 'table',
                                tableOrViewName: 'x_retail_store_mo_store',
                                filterQuery: 'status=open',
                                id: 'ds_total_stores',
                            },
                        ],
                        headerTitle: 'Open Stores',
                        metrics: [
                            {
                                dataSource: 'ds_total_stores',
                                id: 'metric_total_stores',
                                aggregateFunction: 'COUNT',
                                axisId: 'primary',
                            },
                        ],
                    },
                    height: 10,
                    width: 6,
                    position: { x: 6, y: 0 },
                },
                // ─── Bar Chart: Inventory Value per Region ───
                {
                    $id: Now.ID['widget-value-by-region'],
                    component: 'vertical-bar',
                    componentProps: {
                        dataSources: [
                            {
                                label: 'Inventory Value by Region',
                                sourceType: 'table',
                                tableOrViewName: 'x_retail_store_mo_inv_region',
                                filterQuery: '',
                                id: 'ds_value_by_region',
                            },
                        ],
                        headerTitle: 'Total Inventory Value per Region',
                        metrics: [
                            {
                                dataSource: 'ds_value_by_region',
                                id: 'metric_value_region',
                                aggregateFunction: 'SUM',
                                field: 'inv_unit_price',
                                axisId: 'primary',
                            },
                        ],
                        groupBy: [
                            {
                                dataSource: 'ds_value_by_region',
                                id: 'group_region',
                                field: 'reg_name',
                                axisId: 'primary',
                            },
                        ],
                    },
                    height: 14,
                    width: 6,
                    position: { x: 0, y: 10 },
                },
                // ─── Pie Chart: Inventory Items by Category ───
                {
                    $id: Now.ID['widget-items-by-category'],
                    component: 'pie',
                    componentProps: {
                        dataSources: [
                            {
                                label: 'Inventory by Category',
                                sourceType: 'table',
                                tableOrViewName: 'x_retail_store_mo_inv_region',
                                filterQuery: '',
                                id: 'ds_by_category',
                            },
                        ],
                        headerTitle: 'Inventory Items by Category',
                        metrics: [
                            {
                                dataSource: 'ds_by_category',
                                id: 'metric_category',
                                aggregateFunction: 'COUNT',
                                axisId: 'primary',
                            },
                        ],
                        groupBy: [
                            {
                                dataSource: 'ds_by_category',
                                id: 'group_category',
                                field: 'inv_category',
                                axisId: 'primary',
                            },
                        ],
                    },
                    height: 14,
                    width: 6,
                    position: { x: 6, y: 10 },
                },
            ],
        },
    ],
    visibilities: [],
    permissions: [],
})
```

## Avoidance

- Never supply a `name` that isn't already normalized — lowercase with non-alphanumeric characters replaced by `_`. Since `name` is the coalesce key, a mismatch causes the platform to silently rewrite it, and the next build will create a duplicate view instead of updating the existing one.

- Never omit the scope prefix from `name` — required for every customer scope (starting with x_), and required as the u_ custom prefix in the global scope

- Never reuse the same `variablePrefix` across two tables in one view

- Never put an underscore in `variablePrefix`, or exceed 30 characters — the platform rejects both.

- Never use ServiceNow's encoded-query syntax (`^` for AND, `^OR` for OR) in `whereClause` — it's a raw predicate comparing `{variablePrefix}_{field}` names with operators like `=`, `!=`, `&&`, and `||`, not an encoded query string.

- Never use `LIKE` or `CONTAINS` in `whereClause` — they are not supported operators. To match against the full dataset, join tables on `sys_id` using `=`.

- Never omit `$id` on a `tables[]` entry

- Never omit `$id` on a `fields[]` entry

- Never restrict a table's `fields` list without also including every column any `whereClause` in the view joins against on it — including that table's own `whereClause` joining against its own `sys_id`

- Do not use DatabaseView to store or accept writes — it's read-only; use `Table()` for a table that needs its own schema and data.

- Never design a view around a table that participates in table rotation

- Do not rely on a database view's tables for FTP exports or as a clone data preserver

## Related Topics

- `table-guide` — Create tables, columns, column overrides, and relationships to define the data model that database views query

- `form-layout-guide` — Create form layouts and sections for tables

- `table-augments-guide` — Add custom columns to a platform or cross-scope table

- `list-guide` — Create list layouts that control which columns appear in table list views

- `dashboard-api` — Create dashboards for workspace data visualization and reporting

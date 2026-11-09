Version: 4.14.0

# Dashboard Filters

Interactive filter widgets (`filter`, `filter-group`) for a Platform Analytics `Dashboard()` (`par_dashboard`, short for Performance Analytics Report), and how they drive the other widgets on a dashboard. For the base `Dashboard`/`DashboardWidget` config schema and every other widget type, see the `dashboard-guide` topic -- this guide picks up where that one hands off filter-specific detail.

## `filter`

An interactive dashboard filter is wired via two parts:

- `datasource` (singular, lowercase -- not the `dataSources` array charts
use): where the filter's selectable options come from.

- `targets`: an array of one or more places the selected value is applied.
Each target is a datasource-shaped object. One filter can drive multiple
widgets/tables by listing multiple targets.

Both `datasource.payload` and each `targets[].payload` follow the same three
shapes depending on the field being filtered:

```
// Choice field (e.g. incident.priority) -- fieldType: 'choice'
componentProps: {
  filterName: 'Priority',
  filterComponentType: 'multiselect',   // or 'singleselect'
  datasource: { type: 'table', payload: { table: 'incident', field: 'priority', fieldType: 'choice' } },
  targets: [{ type: 'table', payload: { table: 'incident', field: 'priority', fieldType: 'choice' } }],
}
```

```
// Reference field (e.g. incident.assigned_to -> sys_user)
// datasource points at the REFERENCED table (its records are the options);
// the target points at the reference field on the fact table.
componentProps: {
  filterName: 'Assigned to',
  filterComponentType: 'multiselect',
  datasource: { type: 'table', payload: { table: 'sys_user' } },
  targets: [{ type: 'table', payload: { field: 'assigned_to', table: 'incident', primaryKey: 'sys_id' } }],
}
```

```
// Date field -- filterComponentType: 'date', with a default + allowed ranges
componentProps: {
  filterName: 'Created',
  filterComponentType: 'date',
  dateFilterView: 'reldates-only',       // or 'calendar-reldates'
  defaultSelectedDateRange: { range: 'SN_DYNAMIC_DATERANGE__THIS_WEEK', label: 'This week' },
  datasource: {},                         // date filters carry no options datasource
  targets: [{ type: 'table', payload: { field: 'sys_created_on', table: 'incident', primaryKey: 'sys_id' } }],
}
```

```
// Indicator-sourced (Platform Analytics breakdown) -- options come from a PA breakdown
componentProps: {
  filterName: 'Assistants',
  filterComponentType: 'multiselect',
  datasource: {
    type: 'indicator',
    payload: { targetTable: '<table>', factsTable: '<table>', field: 'sys_id', isChoiceType: false, breakdown: '<breakdown sys_id>' },
  },
  targets: [ /* same indicator payload, or a table target */ ],
}
```

Other supported keys: `filterId` (string; auto-generated if omitted),
`filterComponentType` (`'multiselect'` | `'singleselect'` | `'date'`),
`filterElementType` (e.g. `'pill'`), `filterElementLayout` (e.g. `'vertical'`),
`defaultSelectedItems` (array), `sort` (`'ASC'`/`'DESC'`),
`isShowSelectedValueInPill` (boolean), `enableClearFilter` (boolean),
`primaryActionLabel` (e.g. `'Apply'`), `maxElements` (number, default 500),
`cascadeScope` (string -- links cascading filters), `isDashboard: true`.

## `filter-group`

A container that lays out multiple child filters together with shared
Apply/Clear/Reset controls. The child filters live in
`groupConfiguration.filters[]` -- putting `targets` at the top level alone
renders an empty "No filters configured" group. Each entry in `filters[]` is a
full filter config using the exact same `datasource`/`targets`/`filterComponentType`
shapes as a standalone `filter` (above).

```
componentProps: {
  filterName: 'Incident filters',
  isDashboard: true,
  groupConfiguration: {
    filterId: 'group-incident-filters',
    showLabel: true,
    label: 'Incident filters',
    layout: 'horizontal',      // or 'vertical'
    spacing: 's',
    showSelectedValuesInPill: true,
    showBorder: true,
    showApply: true,
    showClear: true,
    showReset: false,
    showSeparator: true,
    filterMaxWidth: 300,
    filters: [
      {
        filterId: 'fg-priority',
        filterName: 'Priority',
        filterComponentType: 'multiselect',
        dateFilterView: 'calendar-reldates',
        defaultSelectedDateRange: { range: '' },
        defaultSelectedItems: [],
        filterConfigurations: [],
        datasource: { type: 'table', payload: { table: 'incident', field: 'priority', fieldType: 'choice' } },
        targets: [{ type: 'table', payload: { table: 'incident', field: 'priority', fieldType: 'choice' } }],
      },
      {
        filterId: 'fg-assigned-to',
        filterName: 'Assigned to',
        filterComponentType: 'multiselect',
        dateFilterView: 'calendar-reldates',
        defaultSelectedDateRange: { range: '' },
        defaultSelectedItems: [],
        filterConfigurations: [],
        datasource: { type: 'table', payload: { table: 'sys_user' } },
        targets: [{ type: 'table', payload: { field: 'assigned_to', table: 'incident', primaryKey: 'sys_id' } }],
      },
    ],
  },
}
```

`groupConfiguration` also supports `showRoundCorners`, `bare`, `combineActions`,
and `cascadeScope` (for cascading child filters); each child filter additionally
supports `allowedDateRanges` (array of `{range, label}`) when
`filterComponentType: 'date'`.

## How filters drive other widgets

A `filter` or `filter-group` affects other widgets that (a) are in scope of the
filter (see placement below), (b) draw from a table the filter `targets`, and
(c) follow dashboard filters. Data widgets do the latter through
`followFilters: true` and `filterConfigurations: "@state.parFilters"`
(charts/list/single-score/dial/gauge/geomap and the indicator scorecard carry
these by default after install; `list-simple` responds to matching filters too).
Set `followFilters: true` explicitly on any widget you want to follow filters.
The link is the target's table + field: a filter whose `targets` include
`{ table: 'incident', field: 'priority' }` filters every incident-sourced
following widget in scope by priority. To drive multiple tables from one filter,
add more entries to `targets` (each pointing at the relevant table/field). A
filter with no in-scope widget matching its target renders and works but visibly
changes nothing.

Placement decides scope. A filter placed in a tab's `widgets[]` drives only
following widgets on that same tab. A filter placed in the dashboard's
`topLayout.widgets[]` renders in the header, above the tab bar, and drives
following widgets on every tab -- the conventional home for a dashboard's
primary filters. Put shared filters in `topLayout`; keep a filter inside a tab
only when it should scope that tab alone.

```
Dashboard({
  $id: Now.ID['my-dashboard'],
  name: 'My Dashboard',
  // Header filter (above the tabs) -- applies to following widgets on all tabs
  topLayout: {
    widgets: [
      {
        $id: Now.ID['hdr-filter'],
        component: 'filter',
        componentProps: {
          filterName: 'Priority',
          filterComponentType: 'multiselect',
          isDashboard: true,
          datasource: { type: 'table', payload: { table: 'incident', field: 'priority', fieldType: 'choice' } },
          targets: [{ type: 'table', payload: { table: 'incident', field: 'priority', fieldType: 'choice' } }],
        },
        width: 24, height: 6, position: { x: 0, y: 0 },
      },
    ],
  },
  tabs: [ /* widgets here set followFilters: true to follow the header filter */ ],
})
```

## Avoidance

- Do not put a `filter-group`'s child filters in a top-level `targets` array --
they belong in `groupConfiguration.filters[]`, or the group renders "No
filters configured".

- Do not assume a `filter`/`filter-group` narrows a widget automatically --
the following widget also needs `followFilters: true` (and typically
`filterConfigurations: '@state.parFilters'`) and a `targets` table/field
match, or the filter renders and works but visibly changes nothing.

## Examples

### dashboard-widgets-with-filter

A header filter driving two different widget types across a tab.

```
import { Dashboard } from '@servicenow/sdk/core'

export const IncidentOverviewDashboard = Dashboard({
  $id: Now.ID['incident-overview-dashboard'],
  name: 'Incident Overview',
  // Header filter (above the tabs) -- drives following widgets on every tab
  topLayout: {
    widgets: [
      {
        $id: Now.ID['priority-filter'],
        component: 'filter',
        componentProps: {
          filterName: 'Priority',
          filterComponentType: 'multiselect',
          isDashboard: true,
          datasource: { type: 'table', payload: { table: 'incident', field: 'priority', fieldType: 'choice' } },
          targets: [{ type: 'table', payload: { table: 'incident', field: 'priority', fieldType: 'choice' } }],
        },
        width: 24, height: 6, position: { x: 0, y: 0 },
      },
    ],
  },
  tabs: [
    {
      $id: Now.ID['overview-tab'],
      name: 'Overview',
      widgets: [
        {
          // Single-value widget following the header filter
          $id: Now.ID['open-incidents-score'],
          component: 'single-score',
          componentProps: {
            dataSources: [{ sourceType: 'table', tableOrViewName: 'incident', filterQuery: 'active=true', id: 'ds_1' }],
            metrics: [{ dataSource: 'ds_1', aggregateFunction: 'COUNT', axisId: 'primary' }],
            showZero: true,
            followFilters: true,
            filterConfigurations: '@state.parFilters',
          },
          height: 7, width: 12, position: { x: 0, y: 0 },
        },
        {
          // Category-comparison chart also following the same header filter
          $id: Now.ID['by-category-chart'],
          component: 'vertical-bar',
          componentProps: {
            dataSources: [{ sourceType: 'table', tableOrViewName: 'incident', filterQuery: 'active=true', id: 'ds_1' }],
            groupBy: [{ groupBy: [{ dataSource: 'ds_1', groupByField: 'category', isChoice: true }], maxNumberOfGroups: 'ALL', sortBy: 'value', sortByOrder: 'desc' }],
            metrics: [{ dataSource: 'ds_1', aggregateFunction: 'COUNT', axisId: 'primary' }],
            followFilters: true,
            filterConfigurations: '@state.parFilters',
          },
          height: 14, width: 24, position: { x: 12, y: 0 },
        },
      ],
    },
  ],
  visibilities: [],
  permissions: [],
})
```

## Related Topics

- For the base `Dashboard`/`DashboardWidget` config schema, and every other widget type: dashboard-guide.md

- For the base config schema and scaffolding examples: `dashboard-api` topic

Version: 4.14.0

# Dashboard

Creates a Platform Analytics Dashboard -- a configurable layout of widgets organized into tabs for data visualization and reporting (`par_dashboard`, short for Performance Analytics Report). Dashboards support drag-and-drop widget positioning, tab-based organization, role-based permissions, and group/user visibility controls.

## When to Use

- Building a reporting/metrics view backed by live table data, Platform Analytics
indicators, or both, organized into tabs.

- Need drag-and-drop widget layout, or granular per-user/group/role permissions and
visibility rules.

- A `Workspace()` also auto-generates a dashboard page for CRUD entity management --
see the `creating-workspaces-guide` topic instead if that's the goal rather than a
standalone analytics dashboard.

## Instructions

For the full `Dashboard` config schema (`$id`, `name`, `permissions`, `tabs`,
`topLayout`, `visibilities`, etc.) and the base `DashboardWidget` placement fields
(`$id`, `component`, `height`, `width`, `position`), see the `dashboard-api` topic.
This guide picks up from there -- it covers the `component` names and
`componentProps` shapes per widget family, and how widgets interact, none of which
`dashboard-api` documents.

```
import { Dashboard } from '@servicenow/sdk/core'

Dashboard({
  $id: Now.ID['dashboard-guide-example'],
  name: 'My Dashboard',
  tabs: [
    {
      $id: Now.ID['dashboard-guide-example-overview-tab'],
      name: 'Overview',
      widgets: [
        // widgets go here -- see Widget Types below for component/componentProps shapes
      ],
    },
  ],
})
```

- Create the `Dashboard({ tabs: [...] })`; each tab holds a `widgets[]` array.

- For each widget pick a `component` (see Widget Types below for the full family
list), a `componentProps` shape (per family below), and `width`/`height`/`position`
in 48-column grid units (see Grid and sizing).

- Data widgets bind to a table through `dataSources` + `metrics` (+ `groupBy` for
categories, or `trendBy` for time-trend charts). Static widgets need no
datasource. Filters bind via `datasource` + `targets`.

- To make a `filter`/`filter-group` narrow the other widgets, target the same
table/field those widgets draw from (see the `dashboard-filters-guide` topic).

- `now-sdk build && now-sdk deploy`, then open the dashboard to confirm it renders.

Pick the component by intent: single number → `single-score` or `dial`/`gauge`;
categories → `vertical-bar`/`horizontal-bar`/`pareto`/`pie`/`donut`/`semi-donut`;
over time → `column`/`line`/`spline`/`area`/`scatter`/`step`; two dimensions →
`heatmap`, `pivot-table`, `bubble`, or `boxplot`; geography → `geomap`; Platform
Analytics score → `indicator-scorecard`; record rows → `list` (aggregated/grouped)
or `list-simple` (flat table); calendar events → `calendar-report`; interactive
filter → `filter`/`filter-group`; text → `heading`/`rich-text`.

## Widget Types

Each widget's `component` field (see `dashboard-api` for the full `DashboardWidget`
shape) takes a kebab-case name (case-insensitive) or a component sys_id, grouped by
family:

- Category-comparison charts: `pie`, `donut`, `semi-donut`, `vertical-bar`, `horizontal-bar`, `pareto`

- Time-trend charts: `column`, `line`, `spline`, `area`, `scatter`, `step`

- Two-dimension charts: `heatmap`, `pivot-table`, `bubble`, `boxplot`

- Single-value widgets: `single-score`, `dial`, `gauge`

- Other data widgets: `geomap`, `indicator-scorecard`, `list`, `list-simple`, `calendar-report`

- Filters: `filter`, `filter-group` -- see the `dashboard-filters-guide` topic

- Static widgets: `heading`, `rich-text`, `image`

All data-binding for a widget happens inline, inside `componentProps` -- there
is no separate visualization/library object to create or reference. This field is
untyped, so values aren't compile-time checked. A partial `componentProps` is fine
-- install fills in the rest of that component's default keys.

Some props take a sys_id referencing another table -- `mapSysId` on `geomap`, the
indicator and breakdown ids on `indicator-scorecard`. Resolve each one by
querying the table named in that widget's section below (see the
`query-guide` topic); a sys_id that doesn't resolve deploys without error and
renders an empty widget.

### Common header & border props (shared by all data widgets)

Every chart/score/list widget exposes the same "Header and border" controls; set any
of these on any data widget's `componentProps` (all optional). The static `heading`
and `rich-text` widgets and the `filter`/`filter-group` widgets do NOT use this set.

| Control | Key | Type / example |
| Show border | `showBorder` | boolean |
| Show header | `showHeader` | boolean |
| Show header separator | `showHeaderSeparator` | boolean |
| Chart title | `headerTitle` | string |
| Title alignment | `headerTitleAlignment` | `'start'` | `'center'` | `'end'` |
| Description | `description` | string |
| Wrap title | `wrapTitle` | boolean |
| Line of truncation | `lineClamp` | number (e.g. `1` ) |
| Show refresh option | `showRefresh` | boolean |
| Show export options | `showExportOptions` | boolean |

The two "Header background color" / "Title color" pickers store no `componentProps`
key while left at Default; set them on-platform if needed.

### Data wiring basics (shared by every chart-type widget)

`pie`, `donut`, `semi-donut`, `vertical-bar`, `horizontal-bar`, `column`, `line`,
`spline`, `area`, `heatmap`, `pivot-table`, `single-score`, `dial`, `gauge`, and
`geomap` all wire data the same way, through three arrays linked by a shared
`dataSources[].id`:

- dataSources (array, capital `S`): each entry needs `sourceType` (`'table'` |
`'indicator'` | `'pa'`), `tableOrViewName`, `filterQuery`, and an `id` (any
string, e.g. `"ds_1"`).

- groupBy: array of grouping definitions, each containing a `groupBy` array of
`{ dataSource, groupByField, isChoice }`. `groupByField` is a plain field name
for table-sourced widgets (a sys_id `groupByField` only applies to
`indicator`-sourced widgets). Set `isChoice: true` for choice fields (e.g.
`priority`). Also supports `maxNumberOfGroups`, `sortBy`, `sortByOrder`. Omit
entirely for single-value widgets (`single-score`/`dial`/`gauge`).

- metrics: array of `{ dataSource, aggregateFunction, axisId }` (e.g.
`aggregateFunction: 'COUNT'`).

They differ only in cosmetic/formatting keys specific to their chart type (e.g.
`innerRadius` for `dial`, `mapSysId` for `geomap`, `freezeHeader`/
`freezeFirstColumn` for `pivot-table`) -- those are self-explanatory by name and
not covered individually.

Common chart display toggles (all optional): `showLegend`, `legendPosition`,
`showDataLabels`, `dataLabelPosition`, `chartVariation` (e.g. `'stacked'`), axis
controls `xAxisHidden` / `yAxisHidden` / `yAxisStyle` / `xAxisMaxLabelSize`,
tooltip/data-table controls `disableTooltip`, `showClosestSeriesOnHover` (shows
only one data point in the tooltip), `showDataTable`,
`showPercentageOfTotalInTooltip`, legend controls `showLegendValue`,
`legendHorizontalAlignment`, `legendExpandToFit`, axis grid controls `showXGrid`,
`showYGrid`, `yAxisShowGrid`, `yAxisPosition`, `xAxisWrapLabels`,
`xAxisTruncationType` (`hideYAxis0` through `hideYAxis4` hide individual Y axes
when a chart plots multiple metrics on separate axes), empty-state controls
`enableCustomEmptyState` + `emptyStateHeading` + `emptyStateContent`, filter
following `followFilters` and `showFilterIcon`, color selection
`colorConfig: { type: 'default' | ... }`, and drilldown `enableDrilldown`.

### Category-comparison charts: `pie`, `donut`, `semi-donut`, `vertical-bar`, `horizontal-bar`, `pareto`

Wire with one `groupBy` entry (the category dimension) plus `metrics` -- see
Data wiring basics above. `pareto` uses this exact same wiring (its second, cumulative
"% of total" line is automatic, not a prop).

```
componentProps: {
  dataSources: [
    { sourceType: 'table', tableOrViewName: 'incident', filterQuery: 'active=true', id: 'ds_1' },
  ],
  groupBy: [
    { groupBy: [{ dataSource: 'ds_1', groupByField: 'priority', isChoice: true }], maxNumberOfGroups: 'ALL', sortBy: 'value', sortByOrder: 'desc' },
  ],
  metrics: [{ dataSource: 'ds_1', aggregateFunction: 'COUNT', axisId: 'primary' }],
}
```

### Time-trend charts: `column`, `line`, `spline`, `area`, `scatter`, `step`

Wire with `metrics` (each entry needs an `id`) plus a `trendBy` object instead of
a category `groupBy` -- this plots each metric as a trend over a date field.
`scatter` and `step` use this identically; without `trendBy` they render "Invalid
configuration -- A 'Trend By' must be selected":

```
componentProps: {
  dataSources: [{ sourceType: 'table', tableOrViewName: 'incident', filterQuery: 'active=true', id: 'ds_1' }],
  metrics: [{ dataSource: 'ds_1', aggregateFunction: 'COUNT', axisId: 'primary', id: 'metric_1' }],
  trendBy: { trendByFrequency: 'date', trendByFields: [{ field: 'sys_created_on', metric: 'metric_1' }] },
}
```

`trendBy.trendByFields[].metric` must reference a `metrics[].id` -- a `groupBy`
can still be present alongside `trendBy`, but `trendBy` is what makes the chart
plot as a trend rather than as discrete groups.

Also support, under "Additional settings": `period` (aggregation period, e.g.
`'M'`), `autoAggregatePeriods`, and `showForecast`.

### Two-dimension charts: `heatmap`, `pivot-table`, `bubble`, `boxplot`

`heatmap` puts both dimensions in a single `groupBy` entry's `groupBy` array
(no `categoryIndex`, no `newReporting` needed):

```
componentProps: {
  dataSources: [
    { sourceType: 'table', tableOrViewName: 'incident', filterQuery: 'active=true', id: 'ds_1' },
  ],
  groupBy: [
    {
      groupBy: [
        { dataSource: 'ds_1', groupByField: 'priority', isChoice: true },
        { dataSource: 'ds_1', groupByField: 'state', isChoice: true },
      ],
      maxNumberOfGroups: 'ALL',
      sortBy: 'value',
      sortByOrder: 'desc',
    },
  ],
  metrics: [{ dataSource: 'ds_1', aggregateFunction: 'COUNT', axisId: 'primary' }],
}
```

`pivot-table` renders a full 2-D matrix (one dimension as rows, the other as
columns, with row/column totals). It needs four things beyond the base wiring to
render both axes with values in normal view:

- `newReporting: true` and `dataCategory: 'group'` -- selects the
pivot-capable data pipeline (without it the value cells stay blank).

- Two separate `groupBy` entries (not two fields in one entry), each with a
`categoryIndex`: `0` for the row axis, `1` for the column axis.

- `metrics[].id` set (any stable string) plus `numberFormat: { customFormat: false }`
-- gives the value column its identity (otherwise the count column is blank).

- `showFirstGroupAggregate: true`, `showSecondGroupAggregate: true`,
`showTotalAggregate: true` -- renders the second (column) dimension and the
row/column totals.

```
componentProps: {
  newReporting: true,
  dataCategory: 'group',
  showZero: true,
  showFirstGroupAggregate: true,
  showSecondGroupAggregate: true,
  showTotalAggregate: true,
  dataSources: [
    { sourceType: 'table', tableOrViewName: 'incident', filterQuery: 'active=true', id: 'ds_1', dataCategories: ['trend', 'group', 'simple'] },
  ],
  groupBy: [
    { groupBy: [{ dataSource: 'ds_1', groupByField: 'state', isChoice: true }], categoryIndex: 0, maxNumberOfGroups: 'ALL', numberOfGroupsBasedOn: 'NO_OF_GROUP_BASED_ON_PER_METRIC' },
    { groupBy: [{ dataSource: 'ds_1', groupByField: 'priority', isChoice: true }], categoryIndex: 1, maxNumberOfGroups: 'ALL', numberOfGroupsBasedOn: 'NO_OF_GROUP_BASED_ON_PER_METRIC' },
  ],
  metrics: [{ dataSource: 'ds_1', aggregateFunction: 'COUNT', axisId: 'primary', id: 'metric_1', numberFormat: { customFormat: false } }],
}
```

This renders as a full 2-D matrix (e.g. State rows × Priority columns with
row/column grand totals) directly in normal dashboard view -- no edit-mode step
needed.

`bubble` and `boxplot` both take two separate `groupBy` entries (like
`pivot-table`, unlike `heatmap`), but simpler -- no `categoryIndex` or
`newReporting` needed:

```
componentProps: {
  dataSources: [{ sourceType: 'table', tableOrViewName: 'incident', filterQuery: 'active=true', id: 'ds_1' }],
  groupBy: [
    { groupBy: [{ dataSource: 'ds_1', groupByField: 'priority', isChoice: true }], maxNumberOfGroups: 'ALL' },
    { groupBy: [{ dataSource: 'ds_1', groupByField: 'state', isChoice: true }], maxNumberOfGroups: 'ALL' },
  ],
  metrics: [{ dataSource: 'ds_1', aggregateFunction: 'COUNT', axisId: 'primary' }],
}
```

For `bubble`, the two entries are symmetric axes -- `groupBy[0]` plots along x,
`groupBy[1]` along y, and `metrics` sizes each bubble.

For `boxplot`, the two entries are not symmetric: `groupBy[0]` is the category
axis (one box per value), and `groupBy[1]` is the field whose per-category `metrics`
values become that box's distribution. With the example above, each `state` gets
one box, and its quartiles are computed over the COUNT of incidents per `priority`
within that state.

### Single-value widgets: `single-score`, `dial`, `gauge`

Wire with `metrics` only -- no `groupBy` (a single aggregated number, not broken
into categories). `dial`/`gauge` additionally take `minValue`/`maxValue` to set
the gauge range.

```
componentProps: {
  dataSources: [{ sourceType: 'table', tableOrViewName: 'incident', filterQuery: 'active=true', id: 'ds_1' }],
  metrics: [{ dataSource: 'ds_1', aggregateFunction: 'COUNT', axisId: 'primary' }],
  minValue: 0,
  maxValue: 200,
}
```

`dial`/`gauge` range display (all optional): `showRangeLimit` (default true -- draws
the `minValue`/`maxValue` end labels), `showRangeLabels`, `showMaximumRange`, and
`scoreSize` (`'auto'`). `height: 14, width: 12` renders the arc and its value
comfortably. The arc is a fixed half-circle; author the range with
`minValue`/`maxValue` rather than looking for an angle setting.

`single-score`-specific settings:

- Set `showZero: true` -- otherwise a genuine zero-row `COUNT` renders "No
score" instead of "0".

- `height: 7` is sufficient to render the full value.

- Display toggles (all optional booleans): `showMetricLabel`,
`showScoreUpdateTime`, `wrapElements`, plus the common header/border set above.

### `geomap`

Group by a location-bearing field (e.g. `incident.location`, a reference field,
with `isChoice: false`).

`mapSysId` selects which geography to draw. It takes the sys_id of a
`sys_report_map` record. Omit the key and the widget draws `World`.

`sys_report_map` is hierarchical -- `World` is the root, countries/continents are
its children, and a country's states or provinces are that country's children.
The most common top-level maps (stable across instances -- these are seeded OOB
records):

| Map | sys_id |
| World (default) | `93b8a3a2d7101200bd4a4ebfae61033a` |
| United States of America | `6ee51951d7320200bd4a4ebfae610354` |
| Europe | `e20fb587d7230200bd4a4ebfae610322` |
| United Kingdom | `fd851380d7030200bd4a4ebfae610361` |
| Canada | `eeef56050fb012009f5a8fbce1050e06` |
| Australia | `5f1c0d3c0fb012009f5a8fbce1050e2e` |
| India | `04197a82d7301200bd4a4ebfae6103bd` |
| Germany | `25d6b682d7301200bd4a4ebfae610319` |

For any other country, or to drill into a country's states/provinces, query
`sys_report_map` directly rather than relying on a static list -- this always
matches what's actually active on the target instance (see the `query-guide`
topic for how to run a table query). Resolve a country/region by name -- query
`sys_report_map` filtered to `active=true` and `name` matching the country,
fetching `sys_id`, `name`, and `parent` -- records live directly under the
`World` sys_id above as their `parent`. Then list that country's sub-regions
with a second query, filtered to `active=true` and `parent` equal to the
country's sys_id, fetching `sys_id` and `name`.

For example, a request for "a map of the Netherlands" resolves to
`edd2a216d7330200bd4a4ebfae61037d`, and querying with that as `parent` returns
all 12 provinces (Drenthe, Flevoland, Friesland, ...) to group by.

Match the map to the granularity of your grouping values. `World` resolves
country-level values, so grouping by a field whose values are US states means using the
map for that state instead. Grouped values with no matching area in the chosen map are
the usual cause of the mapping-errors message below.

```
componentProps: {
  headerTitle: 'Incidents by location',
  dataSources: [{ sourceType: 'table', tableOrViewName: 'incident', filterQuery: 'active=true', id: 'ds_1' }],
  groupBy: [{ groupBy: [{ dataSource: 'ds_1', groupByField: 'location', isChoice: false }], maxNumberOfGroups: 'ALL' }],
  metrics: [{ dataSource: 'ds_1', aggregateFunction: 'COUNT', axisId: 'primary' }],
  mapSysId: '93b8a3a2d7101200bd4a4ebfae61033a',
  showDataLabels: true,
  showLegend: true,
  legendPosition: 'bottom',
}
```

Size it generously -- `height: 18, width: 16` or wider; a map in a narrow column is
unreadable. Records whose location value can't be mapped to a geography are skipped
with a message ("Some of the data you selected cannot be visualized on the map due
to mapping errors") -- that reflects the underlying location data, not the widget
configuration, and needs no query change.

### `indicator-scorecard`

Driven by Platform Analytics indicators, not table `dataSources`/`groupBy`/
`metrics` wiring.

```
componentProps: {
  heading: 'Top 10 Report Tables',
  scorecardType: 'list',
  sourceType: '1',
  aggregateId: 'default',
  // Which PA indicator(s) to score -- id is a sys_id from the indicator table (pa_indicators)
  indicators: [{ id: '<indicator sys_id>', label: 'PA: Reports' }],
  // Break the score down by a PA breakdown (pa_breakdowns); perPage caps rows
  breakdowns: [{ breakdownId: '<breakdown sys_id>', breakdownLabel: 'Analytics Table', elementIds: [], perPage: 10 }],
  nestedBreakdown: true,
  metrics: { fields: ['lastScore', 'trend'], multiScore: { numberOfPeriods: 30, periodStep: 1, type: 'CUSTOM_INTERVAL' } },
  pageSize: '10',
  sortBy: 'name',
  sortDir: 'desc',
}
```

`indicators[].id` is a sys_id from the `pa_indicators` table and
`breakdowns[].breakdownId` is a sys_id from `pa_breakdowns` -- both must be real
sys_ids that have collected scores on the target instance, there's no
table-query fallback. If those indicators have no computed data in the current
context, the widget renders its header/columns but leaves score cells blank.

Resolve both sys_ids with a table query (see the `query-guide` topic): query
`pa_indicators` filtered by `name` matching the indicator, fetching `sys_id` and
`name`; query `pa_breakdowns` the same way for the breakdown.

`Number of open incidents` is a good default indicator for a quick working example on
the `incident` table.

Breakdown names are not unique -- `Priority` returns six records on a stock instance. If
the scorecard renders its rows but every score cell is blank, try another candidate from
that result set.

The enumerated properties take these values:

- `scorecardType` picks the layout, and is the one major choice for this
widget. `'list'` renders one row per indicator (Latest score column plus an
optional trend sparkline). `'pivot'` renders a matrix, with breakdown elements
down the rows and -- when `swapBreakdownsAsColumns: true` -- also across the
columns. These two are the only values. Everything else below applies to both
layouts unless noted.

- `sourceType` picks how indicators are chosen, and each value pairs with a
different companion property:

- `'1'` -- manually selected: list indicators explicitly in
`indicators: [{ id, label }]` (`id` is a `pa_indicators` sys_id).

- `'0'` -- condition based: drop `indicators` and set `query` to an encoded
query on the indicator table (e.g.
`'indicator.display=true^indicator.benchmarking=false'`); every matching
indicator is scored.

- `'2'` -- indicator group: set `indicatorGroup` to a PA indicator-group
sys_id; the group's members are scored.

- `aggregateId` sets the trend metric's time-series aggregation. `'default'`
scores each period as collected (daily); any other value is the sys_id of a PA
aggregate definition -- running sums/averages (7/28/30/365-day), by
week/month/quarter/year (calendar or fiscal), and to-date variants. It only
affects output when `metrics.fields` includes `'trend'`.

- `metrics` chooses the score columns: `fields: ['lastScore']` for the value
alone, add `'trend'` for the sparkline. `multiScore` controls the trend window
(`numberOfPeriods`, `periodStep`, `type: 'CUSTOM_INTERVAL'`).

- `showBreakdownsOnly` (list layout) shows only the breakdown rows; the pivot
layout instead offers `swapBreakdownsAsColumns` to lay breakdown elements
across columns. `sortBy`/`sortDir`, `pageSize`, and `nestedBreakdown` apply to
both layouts. The shared Header and border, Additional settings,
Presentation, and Chart interaction options are configurable here too
(see "Common header & border props").

Prefer a current-state indicator (an open/active record count, an average,
a percentage) over one scored by same-day creation activity, especially when
demoing against a freshly seeded or bulk-loaded table -- a creation-date
indicator only shows a nonzero score on days matching real record-creation
timestamps, while a current-state indicator reflects real data regardless of
when the underlying records were created. `Number of open incidents` is a good
default choice for a quick working example on the `incident` table.

### Lists: `list`, `list-simple`

Two distinct components, not one, despite both being "a list of records":

- `list` -- aggregation-capable, wired like the chart family: `dataSources`,
`metrics`, `groupByField`, plus `table` and `columns`. Setting `groupByField`
renders as a collapsible grouped list (a count per group value with a "Show
all" expand link), not a flat table -- use `list-simple` for a flat table.

- `list-simple` -- a raw filtered table view, no aggregation at all: wired via
`table`, `query`, `fixedQuery`, `columns` only. No `dataSources`/`metrics` keys.

Shared behavior for both:

- `columns` is a comma-separated string of field names, not an array:
`"columns": "number,short_description,state,substate,vendor,starts,ends"`.

- There is no native sort prop. Sort via `filterQuery`/`fixedQuery` +
`^ORDERBYDESC<field>` -- never append `^ORDERBY` alone; use `^ORDERBYDESC` (or
`^ORDERBY<field>` for ascending) with a field name.

- Size to the expected number of visible rows -- both widgets track row/content
count live rather than enforcing a fixed height.

- `limit` (number) caps the rows fetched.

The two components take opposite naming conventions for their display toggles, and
different keys for their title. Do not copy props from one to the other.

`list` follows the chart family: title via `headerTitle`, toggles named `show*`.

```
componentProps: {
  headerTitle: 'Active incidents by priority',
  table: 'incident',
  dataSources: [{ sourceType: 'table', tableOrViewName: 'incident', filterQuery: 'active=true', id: 'ds_1' }],
  metrics: [{ dataSource: 'ds_1', aggregateFunction: 'COUNT', axisId: 'primary' }],
  groupByField: 'priority',
  columns: 'number,short_description,priority,state',
  limit: 20,
  showLinks: true,
  showViewAll: true,
  showColumnSorting: true,
  wrapCellContent: false,
}
```

Other `list` toggles: `showColumnFiltering`, `showColumnGrouping`,
`showColumnReorder`, `showColumnResizing`, `showInlineEditing`,
`showPersonalization`, `allowListPagination`, `columnLimit`, `maxCharLimit`.

`list-simple` takes its title from `listTitle` -- it ignores `headerTitle` and
renders untitled if you set that instead -- and its toggles are inverted `hide*`
booleans that default to `false`, so set a key only to turn something off.

```
componentProps: {
  listTitle: 'Newest active incidents',
  table: 'incident',
  query: 'active=true^ORDERBYDESCsys_created_on',
  fixedQuery: '',
  columns: 'number,short_description,state,priority',
  limit: 10,
  maxColumns: 4,
  hideRefreshButton: true,
  wordWrap: false,
  showBorder: true,
  followFilters: true,
}
```

Other `list-simple` keys: `hideLinks`, `hideViewAll`, `hideInlineEditing`,
`hidePersonalization`, `hideTitleRowCount`, `hideLastRefreshedText`,
`hideRowSelector`, `hideEmptyStateImage`, `hideDotwalk`, and the column controls
`hideColumnSorting` / `hideColumnFiltering` / `hideColumnGrouping` /
`hideColumnReorder` / `hideColumnResizing`. Note `wordWrap` here, not
`wrapCellContent`, and `maxColumns` to cap visible columns.

### `calendar-report`

Like `list-simple`, this is not wired like the chart family -- no
`dataSources`/`metrics`/`groupBy`/`headerTitle` at all. It's a raw table + date
fields, rendered as a month/week/day calendar:

```
componentProps: {
  componentTitle: 'Opened incidents',
  table: 'incident',
  startDateField: 'opened_at',
  eventDisplayFields: 'priority',
}
```

- `componentTitle` is the title key here -- not `headerTitle`, not `listTitle`.

- `startDateField` takes the field's internal name (e.g. `opened_at`, not the
display label "Opened").

- `endDateField` plots events as spans instead of single-day markers. Set
`hideEndDate: true` to make it optional (a single-day event with no span) --
without that flag, `endDateField` is required.

- `eventDisplayFields` is a comma-separated string of field names to show
on each event (matching the `columns` convention used by `list`/`list-simple`,
not an array): `'priority,active,additional_assignee_list'`.

### Filters: `filter`, `filter-group`

For their full `componentProps` shapes, and how a filter drives other widgets on the
dashboard (`targets`, `followFilters`, placement/scope), see the
`dashboard-filters-guide` topic.

### Static widgets: `heading`, `rich-text`, `image`

Need no datasource -- the safest widget types to author.

- `heading`: `{ label, variant, level }`. `variant` is a style token (e.g.
`'header-secondary'`), `level` is the heading level as a string (`'1'`). Also
supports `align` (`'start'`), `hasNoMargin` (boolean), `wontWrap` (boolean).
Author full-width and short: `width: 48, height: 3`.

```
componentProps: { label: 'Section title', variant: 'header-secondary', level: '1' }
```

- `rich-text`: only meaningful key is `html` (a string of HTML). Its size
legitimately ranges from one line to many paragraphs depending on content, so
size to the expected content rather than a fixed default.

```
componentProps: { html: '<p><b>Note.</b> Any HTML string.</p>' }
```

- `image`: set the image with `src`. Reference an image hosted on the
instance itself (same origin), not an off-instance URL. Store custom images as
records in the `db_image` table (the "Images" list) and reference each one by a
leading slash plus its `name` field, which is the filename including extension
(e.g. a `db_image` record named `sc_placeholder_image.png` is referenced as
`src: '/sc_placeholder_image.png'`). With no `src`, the widget renders a
built-in placeholder image.

```
componentProps: { src: '/sc_placeholder_image.png' }
```

## Grid and sizing

- The widget grid is 48 columns wide, not 12. Author `width`/`position.x`
directly in 48-column terms: half = 24, third = 16, quarter = 12.

- `height`/`position.y` is a separate, unscaled axis from `width`/`position.x`
-- this is not a square grid.

- Some environments auto-scale `width`/`x` by 4x on first install of a new
dashboard (a 12-column normalization, e.g. `12` -> `48`); always author real
48-column values from the start rather than relying on scaling.

### Aspect-ratio guidance for `vertical-bar`

Real production `vertical-bar` widgets cluster at aspect ratio (w/h) 0.6-1.5
(near-square to slightly taller-than-wide) when comparing discrete categories.
Wide-flat ratios (2.5-3.4+) suit genuine time-series charts with many x-axis
points (e.g. 12 months).

Rule of thumb: for <=6-8 discrete categories, target aspect ratio <=1.5 -- roughly
quarter-to-half width (12-24 columns) with height equal to or exceeding width.
Reserve full-width layouts for genuinely wide data (long time series, wide lists)
or widgets where width isn't the perceptual channel (`heading`, `single-score`).

## Avoidance

- Do not put a `filter-group`'s child filters in a top-level `targets` array --
they belong in `groupConfiguration.filters[]`, or the group renders "No
filters configured".

- Do not omit `newReporting: true`, `dataCategory: 'group'`, per-axis
`categoryIndex` (0/1 across two separate `groupBy` entries), or `metrics[].id`

- `numberFormat` on `pivot-table` -- without all four, the value cells render
blank even though the widget deploys without error.

- Do not omit `showZero: true` on `single-score` -- a genuine zero-row `COUNT`
renders "No score" instead of "0".

- Do not sort a `list`/`list-simple` with `^ORDERBY` alone -- always pair it
with a field: `^ORDERBYDESC<field>` (or `^ORDERBY<field>` for ascending).

- Do not pass `columns` as an array -- it's a single comma-separated string of
field names.

- Do not assume a `filter`/`filter-group` narrows a widget automatically --
the following widget also needs `followFilters: true` (and typically
`filterConfigurations: '@state.parFilters'`) and a `targets` table/field
match, or the filter renders and works but visibly changes nothing.

- Do not rely on the platform's 12→48 column auto-scaling on first install --
author real 48-column `width`/`position.x` values from the start.

## See also

- https://docs.servicenow.com/csh?topicname=dashboard-api-now-ts.html&version=latest

- For the base `Dashboard`/`DashboardWidget` config schema and scaffolding
examples, see the `dashboard-api` topic.

- For an auto-generated Workspace with its own dashboard page (CRUD entity
management), see the `creating-workspaces-guide` topic -- it embeds a condensed
Dashboard reference for that use case.

- For interactive filters (`filter`, `filter-group`) and how they drive other
widgets, see the `dashboard-filters-guide` topic.

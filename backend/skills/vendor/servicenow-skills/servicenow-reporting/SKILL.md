---
name: servicenow-reporting
description: ServiceNow reporting and dashboards - reports (sys_report) on tables and database views, report types (list, bar, pie, trend, single score, pivot), filters, group by, scheduled reports, dashboards, Platform Analytics / Performance Analytics indicators and breakdowns, sharing and security. Use when someone wants a report, chart, KPI or dashboard.
license: Apache-2.0
metadata:
  category: analytics
  version: "1.1"
---

# Reports and dashboards

## Reports
- `sys_report`: source table (or database view), type (list, bar, horizontal bar, pie, donut, line,
  trend, time series, single score, pivot table, heatmap, calendar), filter (encoded query), group by /
  stack by, aggregation (count, sum, average on a numeric field).
- Report on the right table: `incident` for incidents, `task_sla` for SLA attainment, `sc_req_item` for
  requests, `metric_instance` for durations, a database view to join tables.
- Filters use encoded queries with relative dates (`opened_atONLast 30 days@javascript:gs.beginningOfLast30Days()@javascript:gs.endOfLast30Days()`).
- Share with roles/groups; reports respect ACLs - users only see rows they may read.
- **Scheduled reports** (`sysauto_report`) email a report as PDF/Excel on a schedule.

## Dashboards and analytics
- Dashboards place report and analytics widgets for a role; use one per audience (agent, manager).
- **Performance / Platform Analytics** for trends over time: indicators (count of open P1 incidents),
  breakdowns (by group, priority), data collector jobs that score daily, targets and thresholds.
- KPIs that need history (backlog trend, MTTR per month) are indicators, not plain reports.

## Rules
1. Start from the question ("Are P1s resolved within SLA?") and pick table + aggregation + time window.
2. Avoid reports on huge tables without a date filter.
3. Use choice values, not labels, in filters; group by stable fields.

## What nowBuilder does
nowBuilder can query records to answer a question now (`query_instance_records`) and designs reports
and dashboards (table, type, filter, grouping) for the user to create in Reports → Create New; it
doesn't write report records.

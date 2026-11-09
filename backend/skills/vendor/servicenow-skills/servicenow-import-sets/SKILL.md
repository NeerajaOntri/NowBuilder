---
name: servicenow-import-sets
description: ServiceNow Import Sets - data sources, staging tables, transform maps, field maps, coalesce, transform scripts (onStart, onBefore, onAfter, onComplete, field scripts), scheduled imports, the Import Set API, and error handling. Use when loading data from files, JDBC, REST or another system into ServiceNow tables.
license: Apache-2.0
metadata:
  category: integration
  version: "1.1"
---

# Import Sets

## Flow of data
Data source (`sys_data_source`: file, JDBC, LDAP, REST/IntegrationHub) → **import set** staging table
(`u_imp_*` / `x_*_imp_*`, extends `sys_import_set_row`) → **transform map** (`sys_transform_map`, source
table → target table) with **field maps** (`sys_transform_entry`) → target records.

## Rules
1. Always stage: never write external data straight into target tables.
2. **Coalesce** on a stable unique key (employee number, correlation_id, serial number) so re-imports
   update instead of duplicating. Without coalesce every row inserts.
3. Field maps for straight copies; a **field script** for conversions (`answer = source.u_state == 'Open' ? 1 : 2;`).
4. Transform scripts (`source`, `target`, `map`, `log`, `action`, `ignore`, `error` are available):
   - `onStart` / `onComplete` - once per transform (counters, summary)
   - `onBefore` - per row before the target is written (`ignore = true;` skips the row)
   - `onAfter` - per row after the write (related records)
5. Reference fields: map to the display value with *Choice action* / *Referenced value field name*, or
   resolve the sys_id in a field script; decide what happens when the reference isn't found (reject / ignore / create).
6. Choice fields: *Choice action* reject or ignore unknown values, never create them silently.
7. Schedule recurring loads with **Scheduled Data Imports** (`scheduled_import_set`); clean old import
   rows (Import Set Deleter).
8. CIs go through the IRE (Identification and Reconciliation), not plain transforms.
9. Check **Import Log** and each row's *State* / *Comment* after every run.

## Import Set API
`POST /api/now/import/{staging_table}` inserts a row and transforms it synchronously; the response
lists each target record and status.

## What nowBuilder does
nowBuilder doesn't create data sources, staging tables or transform maps; it designs them (fields,
coalesce key, field maps, transform scripts) for the user to build in System Import Sets.

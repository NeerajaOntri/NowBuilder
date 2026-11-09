---
name: servicenow-cmdb
description: ServiceNow CMDB - CI class hierarchy (cmdb_ci), relationships (cmdb_rel_ci), the Common Service Data Model (CSDM), Identification and Reconciliation Engine (IRE), Discovery and Service Mapping, data quality with CMDB Health, ownership and CI lifecycle. Use when loading or integrating CI data, designing classes or relationships, analysing impact of a CI outage or change, or improving CMDB data quality.
license: Apache-2.0
metadata:
  category: itsm
  version: "1.1"
---

# CMDB

## Data model
- Root class `cmdb_ci`; classes extend it (e.g. `cmdb_ci_computer` → `cmdb_ci_server` → `cmdb_ci_linux_server`; `cmdb_ci_service`, `cmdb_ci_appl`, `cmdb_ci_db_instance`).
- Relationships: `cmdb_rel_ci` (parent, child, type such as *Depends on::Used by*, *Runs on::Runs*); types in `cmdb_rel_type`.
- **CSDM** (Common Service Data Model) defines how to model business capabilities, business applications, business services, technical services, service offerings and application services, and how tasks reference them.
- **IRE** (Identification and Reconciliation Engine) uses identification rules per class and reconciliation rules per data source to insert or update CIs without duplicates. Script entry point: `sn_cmdb.IdentificationEngine.createOrUpdateCI(source, payload)`.
- **Discovery** (agentless, via MID Server) and **Service Mapping** populate CIs and relationships; **Service Graph Connectors** import from third parties through IRE.

## Rules
1. **Model to CSDM.** Start with services (business service / service offering) and the applications behind them; link incidents, changes and problems to services and CIs.
2. **All CI writes from integrations go through IRE** (Service Graph Connectors, import sets with IRE-enabled transforms, or IdentificationEngine). Never insert directly into `cmdb_ci_*` tables from external tools.
3. Use **existing classes**; extend only when you need attributes and identification rules the parent lacks. Avoid many near-identical custom classes.
4. Every CI has **ownership**: managed by group / support group, and an owner. Support group feeds incident assignment.
5. Track **lifecycle** (operational status, install status) and retire CIs through CMDB Data Manager policies instead of deleting.
6. Prefer **discovered** data over manual entry; define **reconciliation precedence** so the most authoritative source wins per attribute.
7. Measure quality with **CMDB Health** (completeness, correctness - duplicates, orphans, stale - and compliance) and fix the top issues each cycle.
8. Relationships must be meaningful and typed correctly; impact analysis depends on them.
9. Restrict who can edit CIs; most users should read only.

## Impact analysis (how to reason)
1. Start from the CI; walk **upstream** relationships (what depends on it: *Used by*, *Runs*) to applications and services.
2. Collect affected **business services / service offerings** and their criticality.
3. Check open incidents on those services and changes scheduled in the window.
4. Report: affected services, users/teams, current incidents, conflicting changes.

## Anti-patterns
- Spreadsheet imports straight into `cmdb_ci_server` creating duplicates.
- CIs without support group, so incidents can't route.
- Services modelled as a single generic CI with no relationships.
- Deleting CIs that tasks still reference.

## Review checklist
- [ ] CSDM-aligned services and applications
- [ ] IRE for every integration; reconciliation rules set
- [ ] Ownership and support groups populated
- [ ] Lifecycle states maintained; retirement policy
- [ ] CMDB Health monitored

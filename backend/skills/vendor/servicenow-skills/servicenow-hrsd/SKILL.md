---
name: servicenow-hrsd
description: ServiceNow HR Service Delivery (HRSD) - HR cases (sn_hr_core_case and centre-of-excellence tables), HR services, HR profiles, HR criteria, Employee Center, lifecycle events (onboarding, offboarding), HR knowledge, and the strict data-privacy and security model for HR data. Use when configuring HR services or lifecycle events, securing HR data, or building any automation or AI that touches employee HR information.
license: Apache-2.0
metadata:
  category: crm
  version: "1.1"
---

# HR Service Delivery (HRSD)

## Data model
- HR application scope `sn_hr_core`; HR case table `sn_hr_core_case`, with **centre-of-excellence (COE)** tables extending it (e.g. payroll, benefits, employee relations, workforce administration).
- **HR services** (`sn_hr_core_service`) define each offering: COE, template, fulfilment (flow/activities), who can request it.
- **HR profile** `sn_hr_core_profile` holds sensitive employee data, linked to `sys_user`.
- **HR criteria** decide which employees see which services and content.
- **Lifecycle Events** (onboarding, offboarding, transfers) orchestrate activities across HR, IT, facilities - built with activity sets / playbooks.
- **Employee Center** is the employee portal for HR (and other) services and knowledge.

## Rules
1. **Treat all HR data as confidential.** Access only through HR roles (`sn_hr_core.basic`, `case_reader`, `case_writer`, `manager`, `admin`, COE-specific roles). Never grant HR roles to non-HR staff or integration users without a privacy review.
2. **Employee relations / investigations** cases need extra restriction (dedicated COE, restricted case access, no broad reporting).
3. Use **HR criteria**, not scripts, to target services and knowledge to populations (country, legal entity, department).
4. Separate **HR knowledge bases** with HR criteria; never publish HR content in the general IT knowledge base.
5. HR data stays in the HR scope; cross-scope access to HR tables should be denied by default.
6. **Lifecycle events**: model as activity sets (or playbooks) with owners per activity; IT tasks created in ITSM through the integration, not manually.
7. **Logging and integrations:** never log personal data (national IDs, salary, health, address); encrypt or mask sensitive fields; integrations with HRIS (Workday, SuccessFactors) via spokes with least privilege.
8. **Data retention**: follow local law; use data privacy / retention policies to anonymise or purge closed cases.
9. Test access by impersonating an employee, a manager, an HR agent of another COE, and an IT agent - each must see only what they should.

## AI guidance for HRSD
- **Mask PII before sending text to any AI model**: national IDs (SSN, Aadhaar, PAN etc.), bank/card numbers, emails, phone numbers, addresses, salary figures, health details.
- AI may summarise cases for authorised HR agents and draft replies for review; never auto-send to employees and never make employment decisions.
- Restrict AI retrieval to HR knowledge the requesting employee may read (HR criteria).
- Keep AI outputs inside the HR case (work notes visible only to HR roles).

## Anti-patterns
- HR cases visible to IT service desk.
- HR knowledge mixed into IT knowledge base.
- Exporting HR case data to spreadsheets for reporting.
- Sending raw case text with national IDs to an external AI service.

## Review checklist
- [ ] HR roles only; ER cases restricted
- [ ] HR criteria targeting services and knowledge
- [ ] PII masked in logs and AI prompts
- [ ] Lifecycle events with owned activities
- [ ] Retention policy configured
- [ ] Access tested across personas

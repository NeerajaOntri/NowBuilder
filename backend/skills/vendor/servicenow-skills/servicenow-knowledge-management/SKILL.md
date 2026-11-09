---
name: servicenow-knowledge-management
description: ServiceNow Knowledge Management - knowledge bases, categories, article templates, lifecycle (draft, review, published, retired), publish and retire workflows, user criteria for read and contribute, versioning, feedback, KCS practices and search quality. Use when setting up knowledge bases, writing or reviewing articles, controlling who can read articles, or improving self-service deflection.
license: Apache-2.0
metadata:
  category: itsm
  version: "1.1"
---

# Knowledge Management

## Data model
- `kb_knowledge_base` (knowledge base), `kb_category`, `kb_knowledge` (article: number, short_description, text or template fields, kb_knowledge_base, kb_category, workflow_state, valid_to, author, ownership group), `kb_feedback`, `kb_use`.
- **Workflow states:** draft → review → published → retired (plus outdated/pending retirement in some configurations).
- **Article templates** give structured articles (How-to, FAQ, Known error, Troubleshooting).
- **User criteria** on the knowledge base (and optionally on articles/categories): *Can read*, *Can contribute*, *Cannot read*.

## Rules
1. Separate knowledge bases by **audience and security**: IT internal, employee self-service, customer-facing (CSM), HR (restricted). Never mix confidential and public content in one base.
2. Control access with **user criteria**, not roles on individual articles.
3. Use **templates** with fixed sections; one article answers one question or resolves one issue.
4. Titles are the searcher's words: "Reset your VPN client on Windows", not "VPN KB v2".
5. Every article has an **owner group** and a **valid_to** date; review on expiry.
6. Publishing: low-risk internal bases may publish instantly; customer/employee-facing bases go through **review/approval** workflow.
7. **KCS (Knowledge-Centered Service):** agents search first, link the article to the incident (`Attach to incident` / `kb_use`), improve it when it's wrong, create one when none exists.
8. **Known errors** from Problem Management publish into a known error knowledge base.
9. Retire rather than delete; keep versioning on so changes are traceable.
10. Measure: views, helpful ratings, deflection, articles linked to resolved incidents, search terms with no results.

## Article quality checklist
- [ ] Title matches how users ask
- [ ] Applies-to (product, version, OS) stated
- [ ] Numbered steps, one action each
- [ ] Expected result and what to do if it fails
- [ ] No secrets, internal hostnames or personal data in public bases
- [ ] Owner and valid-to set

## AI and knowledge
- Ground AI answers on **published** articles only and show citations (article numbers and links).
- Respect user criteria: retrieve only articles the asking user can read.
- When AI finds no answer, offer to raise a ticket and flag the gap for authors.

## Anti-patterns
- One knowledge base for everything with article-level role hacks.
- Articles that are pasted email threads.
- AI chat answering from drafts or retired articles.

## Review checklist
- [ ] Bases split by audience; user criteria set
- [ ] Templates, owners, valid_to
- [ ] Review workflow for external audiences
- [ ] KCS linking in place; metrics tracked

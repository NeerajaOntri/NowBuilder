# ServiceNow SDK / Fluent documentation (bundled)

- **Source:** ServiceNow's official SDK documentation (the site https://servicenow.github.io/sdk), from
  ServiceNow's public GitHub repository https://github.com/ServiceNow/sdk, branch `docs-gh-pages`.
- **Version:** `4.14.0/` - the same ServiceNow SDK version nowBuilder installs flows with.
- **Pages:** 266, converted from the published HTML to Markdown (headings, tables and code examples kept).
  Main sections: `api/` (Fluent APIs, including `api/flow/` for flows, triggers, actions and flow logic),
  `guides/` (how-to guides), `config/` (now.config.json), `fluent/` (language), `cli.md` (now-sdk commands).
- **How nowBuilder uses them:** they are also indexed in `../servicenow_corpus.sqlite3` (SQLite full-text
  search, paths `servicenow-sdk-fluent/4.14.0/…`). The AI searches and reads them with its
  `search_servicenow_docs` and `read_servicenow_doc` tools while it answers and builds.
- **Refresh or add a version:** `python tools/import_fluent_docs.py --version <x.y.z>` (downloads with git,
  converts, re-indexes).

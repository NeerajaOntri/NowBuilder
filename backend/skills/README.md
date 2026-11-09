# nowBuilder skills

- `manifest.json`: stages (which instructions and tools each AI step gets), the artifact types with
  their skills, and the list of things nowBuilder doesn't build.
- `nowbuilder/*.md`: nowBuilder's own rules - how a prompt becomes a plan, how each artifact is
  written, how flows are designed for the ServiceNow SDK, and how deployment results are reported.
  They win over the vendored skills.
- `vendor/servicenow-skills/`: the ServiceNow skill pack (Apache-2.0), reviewed against the
  ServiceNow documentation (Australia release) and the ServiceNow Fluent / SDK reference. Each
  SKILL.md has a "record" section listing the exact Table API fields nowBuilder writes.

`tests/test_prompt_contract.py` and `tests/test_types.py` check the parts of these prompts the
product relies on; run `python -m pytest` after editing them.

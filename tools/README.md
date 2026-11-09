# tools

## build_flow_catalog.py

Regenerates `backend/app/ai/data/flow_catalog.json`: the Flow Designer vocabulary the ServiceNow
SDK (Fluent) can express — every core action with its real input names, types, mandatory flags and
outputs, plus the triggers and flow logic.

It is read out of the SDK's own built-in definitions rather than written by hand, because the input
names are not guessable and change between releases. Run it after upgrading the SDK:

```bash
cd /tmp && npm pack @servicenow/sdk-core@<version>
tar xzf servicenow-sdk-core-<version>.tgz -C ./core
node tools/dump_flow_definitions.js /tmp/core/package > catalog_raw.json
python tools/build_flow_catalog.py          # writes flow_catalog.json next to catalog_raw.json
```

Then copy the result over `backend/app/ai/data/flow_catalog.json`, bump `sdk_version` if the script
didn't, and run `pytest tests/test_flow_catalog.py` — it checks the catalogue is well formed and
that the exporter's assumptions still hold.

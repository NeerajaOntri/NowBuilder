"""Regression coverage for the read-only Table API model tool."""
from app.ai.tools import ToolRunner
from app.ai.skills import get_skills


class Client:
    def __init__(self):
        self.calls = []

    def query(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return [{"number": "INC001", "short_description": "Test"}]


def test_record_query_uses_read_only_table_api():
    client = Client()
    runner = ToolRunner(get_skills(), client)
    import json
    response, error = runner.run("query_instance_records", {"table": "incident", "limit": 10, "fields": ["number", "short_description"]})
    assert not error
    assert json.loads(response)["records"][0]["number"] == "INC001"
    assert client.calls[0][0] == ("incident", "", ["number", "short_description"])
    assert client.calls[0][1]["limit"] == 10


def test_record_query_rejects_sensitive_or_invalid_requests():
    client = Client()
    runner = ToolRunner(get_skills(), client)
    for request in ({"table": "sys_properties"}, {"table": "incident/foo"},
                    {"table": "incident", "limit": 1000}, {"table": "incident", "fields": ["x/y"]}):
        _, error = runner.run("query_instance_records", request)
        assert error
    assert client.calls == []

"""Unit tests for deployment read-back without network or a ServiceNow instance."""
from types import SimpleNamespace

import pytest

from app.services.deploy import Deployer, DeployError
from .test_plans import BR


class FakeClient:
    url = "https://example.service-now.com"

    def __init__(self, visible=True):
        self.visible = visible
        self.rows = {}

    def insert(self, table, data):
        row = {**data, "sys_id": "a" * 32}
        self.rows[(table, row["sys_id"])] = row
        return row

    def get(self, table, sys_id, fields=None):
        return self.rows.get((table, sys_id)) if self.visible else None


def test_deployer_write_returns_actual_record_id():
    client = FakeClient()
    d = Deployer(client, SimpleNamespace())
    result = d.write({"id": "c1", "name": "Rule", "type": "business_rule", "generated": BR})
    assert client.get(result.table, result.sys_id) is not None
    assert result.sys_id == "a" * 32

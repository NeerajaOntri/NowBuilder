"""Extra guardrails: designs must never become Table API writes; failed children remain tracked."""
from types import SimpleNamespace
import pytest
from app.services.deploy import Deployer, DeployError
from .test_plans import BR

class StubClient:
    url = 'https://dev.example.service-now.com'
    def __init__(self): self.created = []
    def insert(self, table, data):
        self.created.append(table)
        if table == 'sys_ui_policy_action':
            raise RuntimeError('Simulated unexpected child failure')
        return {**data, 'sys_id': 'a' * 32}


def test_flow_refused_before_any_write():
    client = StubClient()
    with pytest.raises(DeployError, match='design-only'):
        Deployer(client, SimpleNamespace()).write({
            'type': 'flow', 'name': 'Do not deploy', 'generated': {}
        })
    assert client.created == []


def test_parent_registration_occurs_before_child_write_failure():
    client = StubClient()
    tracked = []
    generated = {'record': {
        'short_description': 'Test', 'table': 'incident', 'conditions': '',
        'on_load': 'true', 'reverse_if_false': 'true', 'run_scripts': 'false', 'active': 'true'
    }, 'actions': [{'field': 'priority', 'mandatory': 'ignore', 'visible': 'true', 'disabled': 'ignore'}]}
    with pytest.raises(RuntimeError, match='child failure'):
        Deployer(client, SimpleNamespace()).write({
            'id': 'c1', 'type': 'ui_policy', 'name': 'Test', 'generated': generated
        }, on_partial=tracked.append)
    assert len(tracked) == 1
    assert tracked[0].table == 'sys_ui_policy'
    assert tracked[0].sys_id == 'a' * 32

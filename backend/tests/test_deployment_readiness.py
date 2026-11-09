from types import SimpleNamespace
from app.services.deployment_readiness import assess
from app.services.servicenow import ServiceNowError

class FakeClient:
    def __init__(self, blocked=()): self.blocked = blocked; self.calls = []
    def query(self, table, **kwargs):
        self.calls.append(('query', table))
        if table in self.blocked: raise ServiceNowError('permission denied')
        return []

def test_global_scope_never_claims_flow_deployment():
    client = FakeClient()
    inst = SimpleNamespace(is_admin=True, user_sys_id='abc', release='Australia')
    result = assess(client, inst)
    assert result['flow_designer_deployment']['status'] == 'unsupported'
    assert 'global' in result['flow_designer_deployment']['detail']
    assert all(call[0] == 'query' for call in client.calls)

def test_permission_failure_visible():
    client = FakeClient({'sys_update_xml'})
    inst = SimpleNamespace(is_admin=True, user_sys_id='abc', release='Australia')
    result = assess(client, inst)
    assert result['artifact_deployment']['status'] == 'blocked_or_unverified'
    assert result['table_checks']['sys_update_xml']['status'] == 'blocked'

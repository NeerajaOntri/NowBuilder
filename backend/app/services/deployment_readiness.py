"""Non-mutating instance and deployment capability preflight.

Checks are deliberately read-only: don't make test update sets or alter a user's
current update-set preference just to assess readiness.
"""
from __future__ import annotations

from .servicenow import ServiceNowError


def _check_table(client, table: str) -> dict:
    try:
        client.query(table, limit=1, fields=['sys_id'])
        return {'status': 'ok', 'detail': 'Read access verified.'}
    except ServiceNowError as exc:
        return {'status': 'blocked', 'detail': str(exc)}


def assess(client, instance, *, application_scope: str = 'global') -> dict:
    """Return explicit capabilities; never call a write API."""
    tables = {
        'incident': _check_table(client, 'incident'),
        'sys_update_set': _check_table(client, 'sys_update_set'),
        'sys_user_preference': _check_table(client, 'sys_user_preference'),
        'sys_update_xml': _check_table(client, 'sys_update_xml'),
        'sys_hub_flow': _check_table(client, 'sys_hub_flow'),
    }
    admin = bool(getattr(instance, 'is_admin', False))
    have_user = bool(getattr(instance, 'user_sys_id', None))
    update_set_ready = admin and have_user and all(
        tables[name]['status'] == 'ok' for name in ('sys_update_set', 'sys_user_preference', 'sys_update_xml')
    )
    scoped = application_scope != 'global'
    return {
        'mode': 'read_only_preflight',
        'instance_release': getattr(instance, 'release', None),
        'application_scope': application_scope,
        'admin_reported': admin,
        'connected_user_resolved': have_user,
        'table_checks': tables,
        'artifact_deployment': {
            'status': 'ready_for_controlled_test' if update_set_ready else 'blocked_or_unverified',
            'detail': 'Read checks are not proof of write permission, update-set capture or actual deployment.'
        },
        'flow_designer_deployment': {
            'status': 'unsupported',
            'detail': (
                'No implemented Flow Designer build, deploy, activate and verify pipeline. '
                + ('ServiceNow SDK application workflow requires a scoped application; this connection is global. '
                   if not scoped else 'A scoped application is selected, but SDK orchestration remains missing. ')
                + 'Do not write sys_hub_flow records directly as a workaround.'
            ),
        },
        'next_step': 'Run a reviewed, low-risk supported artifact deployment on this PDI; verify its update set. For SDK-based flows, create/select a scoped application and implement SDK orchestration.'
    }

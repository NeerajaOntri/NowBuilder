"""Exporting a flow design as ServiceNow SDK (Fluent) source.

What the SDK can express is read out of its own built-in definitions (`app/ai/data/flow_catalog.json`),
so these tests are about the exporter honouring that vocabulary, not about a hand-written guess at it.
"""
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.ai import flow_catalog
from app.ai.flow_sdk import UnsupportedFlow, export_report, generate_flow_source


def sample():
    return {'record': {'name': 'Change Risk Tagging', 'table': 'change_request',
                       'trigger': 'Created or Updated', 'trigger_condition': 'active=true^impact=1',
                       'run_trigger': 'for each unique change', 'run_as': 'User who initiated session',
                       'description': 'Tags high-impact changes.'},
            'steps': [
                {'step': 1, 'kind': 'action', 'name': 'Update Record', 'detail': 'Tag as high risk.',
                 'inputs': {'table_name': 'change_request', 'record': '{{trigger.current.sys_id}}',
                            'values': {'risk': 'high'}}},
                {'step': 2, 'kind': 'action', 'name': 'Look Up Record', 'detail': 'Find the CAB group.',
                 'inputs': {'table': 'sys_user_group', 'conditions': 'name=CAB'}},
                {'step': 3, 'kind': 'action', 'name': 'Log', 'detail': 'Record what happened.',
                 'inputs': {'log_level': 'warn',
                            'log_message': 'Change {{trigger.current.number}} — CAB {{step2.Record.name}}.'}},
            ]}


# ---------- the catalogue ----------

def test_the_catalogue_came_from_the_sdk_and_covers_the_core_actions():
    names = flow_catalog.action_names()
    assert len(names) >= 30 and flow_catalog.sdk_version()
    for expected in ('Create Record', 'Update Record', 'Look Up Record', 'Look Up Records',
                     'Send Notification', 'Send Email', 'Ask For Approval', 'Log', 'Wait For Condition'):
        assert expected in names, expected


def test_action_names_match_flow_designer_so_they_can_be_checked_against_an_instance():
    """sys_hub_action_type_definition.name holds the same display name, which is how a design,
    the connected instance and the exporter stay in one vocabulary."""
    assert flow_catalog.action('send notification')['api'] == 'action.core.sendNotification'
    assert flow_catalog.action('Send Notification')['inputs']['notification']['mandatory'] is True
    assert flow_catalog.logic('If') == 'if' and flow_catalog.logic('For Each') == 'forEach'
    assert flow_catalog.trigger('Created')['api'] == 'trigger.record.created'


def test_mandatory_and_unknown_inputs_are_reported_from_the_catalogue():
    assert flow_catalog.missing_inputs('Create Record', {'table_name': 'incident'}) == ['values']
    assert flow_catalog.unknown_inputs('Log', {'log_message': 'x', 'colour': 'red'}) == ['colour']


# ---------- exporting ----------

def test_a_multi_action_flow_exports():
    src = generate_flow_source(sample())
    assert 'trigger.record.createdOrUpdated' in src
    assert 'action.core.updateRecord' in src and 'action.core.lookUpRecord' in src
    assert "runAs: 'user'" in src
    assert 'trigger_strategy: "unique_changes"' in src


def test_a_value_that_is_only_a_pill_is_passed_through_not_stringified():
    src = generate_flow_source(sample())
    assert "record: wfa.dataPill(params.trigger.current.sys_id, 'reference')," in src


def test_a_step_whose_output_is_used_gets_a_variable():
    src = generate_flow_source(sample())
    assert 'const step2 = wfa.action(' in src
    assert "wfa.dataPill(step2.Record.name, 'string')" in src
    assert 'const step1' not in src and 'const step3' not in src   # nothing reads those


def test_a_fields_map_becomes_a_template_value_one_column_per_line():
    """Source a person reads before installing it, so the Fields map doesn't go on one long line."""
    src = generate_flow_source(sample())
    assert 'values: TemplateValue({\n                  "risk": "high",\n                })' in src


def test_a_sys_id_inside_a_fields_map_is_typed_as_a_reference():
    """Inside a Fields map the catalogue can't say what each column is, so a whole-value pill
    pointing at a sys_id is read as the reference it is rather than defaulted to a string."""
    data = sample()
    data['steps'][0]['inputs']['values'] = {'assignment_group': '{{step2.Record.sys_id}}',
                                            'work_notes': 'set by {{step2.Record.name}}'}
    data['steps'][0], data['steps'][1] = data['steps'][1], data['steps'][0]   # look up first
    data['steps'][0]['step'], data['steps'][1]['step'] = 2, 1
    src = generate_flow_source(data)
    assert "wfa.dataPill(step2.Record.sys_id, 'reference')" in src
    assert "wfa.dataPill(step2.Record.name, 'string')" in src                 # embedded in text


def test_the_system_user_setting_is_carried_through_and_called_out():
    data = sample()
    data['record']['run_as'] = 'System user'
    src = generate_flow_source(data)
    assert "runAs: 'system'" in src and 'bypasses ACLs' in src


def parses(src: str) -> subprocess.CompletedProcess:
    """node --check on the source. The SDK globals aren't defined here, so this is a parse, not a run."""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / 'flow.mjs'
        f.write_text(src, encoding='utf-8')
        return subprocess.run(['node', '--check', str(f)], text=True, capture_output=True)


def test_the_generated_source_is_valid_javascript():
    r = parses(generate_flow_source(sample()))
    assert r.returncode == 0, r.stderr


def test_escaping_does_not_inject_source():
    data = sample()
    data['steps'][2]['inputs']['log_message'] = 'a"; process.exit(1); //'
    src = generate_flow_source(data)
    assert r'log_message: "a\"; process.exit(1); //",' in src    # one string, not a statement
    assert parses(src).returncode == 0


def test_a_value_cannot_escape_the_template_literal_it_lands_in():
    """A pill value is interpolated, so the design's own backticks and ${...} have to be neutralised
    before the pills go in — otherwise a value is executable, and node --check wouldn't notice."""
    data = sample()
    data['steps'][2]['inputs']['log_message'] = '`${process.exit(1)}` for {{trigger.current.number}}'
    src = generate_flow_source(data)
    line = next(ln for ln in src.split('\n') if 'log_message' in ln)
    assert r'\`\${process.exit(1)}\`' in line          # inert text
    assert line.count('${') == line.count(r'\${') + 1    # exactly one live interpolation: the pill
    assert "wfa.dataPill(params.trigger.current.number, 'string')" in line
    assert parses(src).returncode == 0


def test_a_backslash_in_a_value_stays_a_backslash():
    data = sample()
    data['steps'][2]['inputs']['log_message'] = r'C:\temp for {{trigger.current.number}}'
    src = generate_flow_source(data)
    assert r'C:\\temp' in src and parses(src).returncode == 0


# ---------- what it refuses, and why ----------

def test_a_step_with_only_prose_cannot_be_exported():
    """The old exporter's whole input model. A description isn't a set of inputs."""
    data = sample()
    del data['steps'][0]['inputs']
    report = export_report(data)
    assert not report['exportable'] and report['steps_ready'] == 2
    assert 'gives no inputs' in ' '.join(report['blockers'])


@pytest.mark.parametrize('bad,expected', [
    ({'table_name': 'incident'}, 'needs'),            # values is mandatory
    ({'table_name': 'incident', 'colour': 'red'}, 'no input called colour'),
])
def test_inputs_are_checked_against_the_action(bad, expected):
    data = sample()
    data['steps'][0] = {'step': 1, 'kind': 'action', 'name': 'Create Record', 'detail': 'd', 'inputs': bad}
    assert expected in ' '.join(export_report(data)['blockers']).replace('is required', 'needs')


def test_an_if_without_its_condition_is_not_exported():
    data = sample()
    data['steps'].append({'step': 4, 'kind': 'flow logic', 'name': 'If', 'detail': 'Approved.'})
    report = export_report(data)
    assert not report['exportable']
    assert "needs its condition" in ' '.join(report['blockers'])


def test_try_and_parallel_blocks_are_not_exported_yet():
    data = sample()
    data['steps'].append({'step': 4, 'kind': 'flow logic', 'name': 'Do The Following In Parallel', 'detail': 'x'})
    assert "isn't exported yet" in ' '.join(export_report(data)['blockers'])


def nested():
    """Look up the group; if it has a manager, update the incident inside the If; else log."""
    return {'record': {'name': 'P1 Escalation', 'table': 'incident', 'trigger': 'Created',
                       'trigger_condition': 'priority=1', 'run_trigger': 'once',
                       'run_as': 'System user', 'description': 'Escalate P1s.'},
            'steps': [
                {'step': 1, 'kind': 'action', 'name': 'Look Up Record', 'detail': 'Find the group.',
                 'inputs': {'table': 'sys_user_group', 'conditions': 'sys_id={{trigger.current.assignment_group}}'}},
                {'step': 2, 'kind': 'flow logic', 'name': 'If', 'detail': 'Group has a manager',
                 'condition': '{{step1.Record.manager}}ISNOTEMPTY'},
                {'step': 3, 'kind': 'action', 'name': 'Update Record', 'detail': 'Note it.', 'inside': 2,
                 'inputs': {'table_name': 'incident', 'record': '{{trigger.current.sys_id}}',
                            'values': {'work_notes': 'Escalated to {{step1.Record.name}}'}}},
                {'step': 4, 'kind': 'flow logic', 'name': 'Else', 'detail': 'No manager'},
                {'step': 5, 'kind': 'action', 'name': 'Log', 'detail': 'Log it.', 'inside': 4,
                 'inputs': {'log_level': 'warn', 'log_message': 'No manager for {{trigger.current.number}}'}},
            ]}


def test_steps_inside_an_if_and_else_are_nested_in_their_bodies():
    src = generate_flow_source(nested())
    assert 'wfa.flowLogic.if(' in src and 'wfa.flowLogic.else(' in src
    assert "condition: `${wfa.dataPill(step1.Record.manager, 'reference')}ISNOTEMPTY`" in src
    assert 'const step1 = wfa.action(' in src
    if_at, update_at, else_at, log_at = (src.index(x) for x in
                                         ('wfa.flowLogic.if(', 'action.core.updateRecord', 'wfa.flowLogic.else(', 'action.core.log'))
    assert if_at < update_at < else_at < log_at
    assert parses(src).returncode == 0


def test_for_each_loops_over_records_and_reads_the_item():
    data = nested()
    data['steps'] = [
        {'step': 1, 'kind': 'action', 'name': 'Look Up Records', 'detail': 'Child incidents.',
         'inputs': {'table': 'incident', 'conditions': 'parent_incident={{trigger.current.sys_id}}'}},
        {'step': 2, 'kind': 'flow logic', 'name': 'For Each', 'detail': 'Each child', 'items': '{{step1.Records}}'},
        {'step': 3, 'kind': 'action', 'name': 'Update Record', 'detail': 'Raise it.', 'inside': 2,
         'inputs': {'table_name': 'incident', 'record': '{{item.sys_id}}', 'values': {'priority': '1'}}},
    ]
    src = generate_flow_source(data)
    assert 'wfa.flowLogic.forEach(' in src and 'step1.Records,' in src and '(item) => {' in src
    assert "record: wfa.dataPill(item.sys_id, 'reference')," in src
    assert parses(src).returncode == 0


def test_an_else_has_to_follow_an_if():
    data = nested()
    data['steps'] = [data['steps'][0], data['steps'][3], data['steps'][4]]
    data['steps'][1]['step'], data['steps'][2]['step'], data['steps'][2]['inside'] = 2, 3, 2
    assert 'straight after an If' in ' '.join(export_report(data)['blockers'])


def test_a_reference_to_another_plan_row_is_resolved_before_export():
    from app.ai.flow_sdk import plan_refs, resolve_plan_refs
    data = sample()
    data['steps'].append({'step': 4, 'kind': 'action', 'name': 'Send Notification', 'detail': 'Tell them.',
                          'inputs': {'table_name': 'change_request', 'record': '{{trigger.current.sys_id}}',
                                     'notification': '{{plan.c2}}'}})
    assert plan_refs(data) == {'c2'}
    assert export_report(data)['exportable']                     # fine as a design
    with pytest.raises(UnsupportedFlow, match="haven't been deployed yet"):
        generate_flow_source(data)                                # but not as source until deployed
    src = generate_flow_source(resolve_plan_refs(data, {'c2': 'a' * 32}))
    assert f'notification: "{"a" * 32}"' in src


def test_a_daily_schedule_exports_with_its_time():
    data = sample()
    data['record'].update({'trigger': 'Daily', 'table': '', 'schedule_time': '09:30', 'trigger_condition': ''})
    data['steps'] = [data['steps'][2]]
    data['steps'][0]['step'] = 1
    data['steps'][0]['inputs'] = {'log_level': 'info', 'log_message': 'Daily run'}
    src = generate_flow_source(data)
    assert 'trigger.scheduled.daily' in src and 'Time({ hours: 9, minutes: 30, seconds: 0 })' in src


def test_logic_without_a_body_does_export():
    data = sample()
    data['steps'].append({'step': 4, 'kind': 'flow logic', 'name': 'End Flow', 'detail': 'Stop here.'})
    src = generate_flow_source(data)
    assert 'wfa.flowLogic.endFlow(' in src


@pytest.mark.parametrize('over,expected', [
    ({'trigger': 'Inbound Email Reply'}, 'no Inbound Email Reply trigger'),
    ({'run_as': 'Somebody else'}, 'Unrecognised run-as'),
    ({'table': ''}, 'needs a valid table'),
])
def test_the_flow_itself_fails_closed(over, expected):
    data = sample()
    data['record'].update(over)
    with pytest.raises(UnsupportedFlow, match=re.escape(expected)):
        generate_flow_source(data)


def test_a_subflow_step_is_not_exported():
    data = sample()
    data['steps'][1] = {'step': 2, 'kind': 'subflow', 'name': 'Escalate', 'detail': 'd'}
    assert "subflows aren't exported" in ' '.join(export_report(data)['blockers'])


def test_a_pill_in_the_send_email_body_goes_in_as_a_placeholder():
    """Fluent action API: ah_body "does NOT support data pills -- it only accepts static strings" (TS228)."""
    from app.ai.flow_sdk import manual_pills
    data = sample()
    data['steps'].append({'step': 4, 'kind': 'action', 'name': 'Send Email', 'detail': 'Email the creator.',
                          'inputs': {'table_name': 'change_request', 'record': '{{trigger.current.sys_id}}',
                                     'ah_to': '{{step2.Record.email}}',
                                     'ah_subject': 'Change {{trigger.current.number}} created',
                                     'ah_body': 'Your change {{trigger.current.number}} for {{trigger.current.opened_by.name}}.'}})
    assert export_report(data)['exportable']
    src = generate_flow_source(data)
    # The trigger record's pills are written the way Flow Designer stores a pill in an input value
    assert 'ah_body: "Your change {{trigger.current.number}} for {{trigger.current.opened_by.name}}."' in src
    assert "wfa.inlineScript" not in src and "fd_data" not in src
    assert "ah_subject: `Change ${wfa.dataPill(params.trigger.current.number, 'string')} created`" in src
    assert manual_pills(data) == []                                    # nothing to drag in by hand
    plain = generate_flow_source(data, static_pills='placeholders')    # the fallback if an SDK refuses them
    assert 'ah_body: "Your change [Number] for [Opened by name]."' in plain
    data['steps'][-1]['inputs']['ah_body'] = 'Hi {{step2.Record.name}}'   # another step's pill: by hand
    assert manual_pills(data) == ['Step 4 Send Email ah_body: [Name]']
    assert 'ah_body: "Hi [Name]"' in generate_flow_source(data)


def test_static_only_inputs_come_from_the_catalogue_types():
    assert flow_catalog.static_only_inputs('Send Email') == {'ah_body'}
    assert flow_catalog.static_only_inputs('Send Notification') == set()


def test_do_the_following_until_with_a_wait_is_written_inside_the_flow():
    """Fluent Flow Logic API (SDK 4.14): doTheFollowing(..., () => { ...; wfa.flowLogic.until(cond) }),
    waitForADuration({ durationType: 'explicit_duration', duration: Duration({...}) })."""
    data = {'record': {'name': 'Lead owner email', 'table': 'sn_lead_mgmt_core_lead', 'trigger': 'Created or Updated',
                       'trigger_condition': 'ownerISNOTEMPTY', 'run_trigger': 'always', 'run_as': 'System user'},
            'steps': [
                {'step': 1, 'kind': 'action', 'name': 'Send Email', 'detail': 'first email',
                 'inputs': {'ah_to': '{{trigger.current.owner.email}}', 'ah_subject': 'Lead {{trigger.current.number}}',
                            'ah_body': 'Hi {{trigger.current.first_name}}'}},
                {'step': 2, 'kind': 'flow logic', 'name': 'Do the following until', 'detail': 'repeat',
                 'condition': '{{step4.Record.stage}}IN300_nurturing,400_closed_won,500_closed_lost'},
                {'step': 3, 'kind': 'flow logic', 'name': 'Wait for a duration', 'inside': 2, 'duration': '2 minutes'},
                {'step': 4, 'kind': 'action', 'name': 'Look Up Record', 'inside': 2, 'detail': 'fresh stage',
                 'inputs': {'table': 'sn_lead_mgmt_core_lead',
                            'conditions': 'sys_id={{trigger.current.sys_id}}'}},
                {'step': 5, 'kind': 'action', 'name': 'Send Email', 'inside': 2, 'detail': 'repeat email',
                 'inputs': {'ah_to': '{{trigger.current.owner.email}}', 'ah_subject': 'Lead {{trigger.current.number}}',
                            'ah_body': 'Hi {{trigger.current.first_name}}'}}]}
    report = export_report(data)
    assert report['exportable'], report['blockers']
    src = generate_flow_source(data)
    assert 'wfa.flowLogic.doTheFollowing(' in src
    assert "durationType: 'explicit_duration', duration: Duration({ minutes: 2 })" in src
    assert 'const step4 = wfa.action(' in src
    body = src[src.index('wfa.flowLogic.doTheFollowing('):]
    until = body.index('wfa.flowLogic.until(')
    assert until > body.index('const step4') and until > body.rindex('wfa.action(')     # last statement
    pill = "${wfa.dataPill(step4.Record.stage, 'string')}"
    assert f"wfa.flowLogic.until(`{pill}=300_nurturing^OR{pill}=400_closed_won^OR{pill}=500_closed_lost`)" in src


def test_a_loop_needs_its_until_condition_and_a_wait_its_duration():
    from app.ai.flow_sdk import duration_parts
    assert duration_parts('2 minutes') == {'minutes': 2}
    assert duration_parts('1 hour 30 mins') == {'hours': 1, 'minutes': 30}
    assert duration_parts('00:02:00') == {'minutes': 2}
    assert duration_parts({'seconds': 45}) == {'seconds': 45}
    assert duration_parts('soon') is None
    data = sample()
    data['steps'] = [{'step': 1, 'kind': 'flow logic', 'name': 'Do the following until'},
                     {'step': 2, 'kind': 'flow logic', 'name': 'Wait for a duration', 'inside': 1}]
    blockers = ' '.join(export_report(data)['blockers'])
    assert "needs its 'until' condition" in blockers and 'needs a duration' in blockers


def test_a_pill_list_condition_becomes_or_comparisons():
    from app.ai.flow_sdk import expand_pill_lists
    assert expand_pill_lists('{{step4.Record.stage}}IN300_a,400_b') == '{{step4.Record.stage}}=300_a^OR{{step4.Record.stage}}=400_b'
    assert expand_pill_lists('{{trigger.current.state}}NOT IN6,7^{{trigger.current.active}}=true') == \
        '{{trigger.current.state}}!=6^{{trigger.current.state}}!=7^{{trigger.current.active}}=true'
    assert expand_pill_lists('stateIN1,2') == 'stateIN1,2'          # a field condition (trigger) keeps IN

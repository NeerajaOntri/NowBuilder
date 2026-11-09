import { useEffect, useMemo, useRef, useState } from 'react';
import { planApi, planStream } from '../chatApi';
import { Dialog } from './Dialog';
import { Icon } from './Icon';
import { PlanDiagram } from './PlanDiagram';
import { useWorkspace } from '../instances';
import { api, tokenStore } from '../api';

// The plan as a Word design document, built by the backend from the plan and its deployment.
async function downloadDocument(plan) {
  const res = await fetch(`/api/plans/${plan.id}/document`, { headers: { Authorization: `Bearer ${tokenStore.get()}` } });
  if (!res.ok) throw new Error("Couldn't build the design document. Try again.");
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${(plan.title || 'design').replace(/[^\w -]+/g, '_').slice(0, 80)} - design.docx`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// Copy the deployed update set to another connected instance as a retrieved update set; the target's
// admin previews and commits it there (ServiceNow's own checks), so nothing is committed from here.
function MoveUpdateSet({ plan, onClose }) {
  const { instances } = useWorkspace();
  const source = plan.instance_id;
  const targets = (instances ?? []).filter((i) => i.id !== source && i.status === 'connected');
  const [target, setTarget] = useState(targets[0]?.id ?? '');
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const body = { update_set_id: plan.deployment.update_set.sys_id, target_instance_id: target };
  const go = async (confirm) => {
    setBusy(true); setErr(null);
    try {
      const r = await api(`/api/instances/${source}/promote`, { method: 'POST', json: { ...body, confirm } });
      confirm ? setResult(r) : setPreview(r);
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  const t = targets.find((i) => i.id === target);
  return (
    <Dialog title="Move to another instance" onClose={onClose}>
      {targets.length === 0 && <p className="muted">Connect another instance in Settings → ServiceNow instances first.</p>}
      {targets.length > 0 && !result && (
        <>
          <label className="field"><span>Target instance</span>
            <select value={target} onChange={(e) => { setTarget(e.target.value); setPreview(null); }}>
              {targets.map((i) => <option key={i.id} value={i.id}>{i.name} ({i.instance_type})</option>)}
            </select>
          </label>
          {t?.instance_type === 'Production' && <div className="alert alert-warn small">This is a Production instance.</div>}
          {preview && (
            <div className="small">
              <p><strong>{preview.update_set.name}</strong>: {preview.updates.length} customer update{preview.updates.length === 1 ? '' : 's'}</p>
              <ul>{preview.updates.slice(0, 12).map((u, i) => <li key={i}>{u.type}: {u.target}</li>)}</ul>
              <p className="muted">It arrives on {preview.target} as a retrieved update set. Preview and commit it there.</p>
            </div>
          )}
          {err && <div className="alert alert-error small">{err}</div>}
          <div className="dialog-actions">
            <button className="btn btn-sm" onClick={onClose}>Cancel</button>
            {!preview
              ? <button className="btn btn-sm btn-primary" disabled={busy || !target} onClick={() => go(false)}>{busy ? 'Reading…' : 'Preview'}</button>
              : <button className="btn btn-sm btn-primary" disabled={busy} onClick={() => go(true)}>{busy ? 'Copying…' : `Copy to ${t?.name}`}</button>}
          </div>
        </>
      )}
      {result && (
        <>
          <div className="alert alert-success small">Copied {result.copied} updates; {result.verified} confirmed on the target.</div>
          <p className="small">{result.next} <a href={result.url} target="_blank" rel="noreferrer">Open it</a></p>
          <div className="dialog-actions"><button className="btn btn-sm btn-primary" onClick={onClose}>Done</button></div>
        </>
      )}
    </Dialog>
  );
}

const TYPE_LABEL = {
  business_rule: 'Business rule',
  script_include: 'Script include',
  client_script: 'Client script',
  ui_policy: 'UI policy',
  ui_action: 'UI action',
  notification: 'Notification',
  flow: 'Flow',
  scheduled_job: 'Scheduled job',
  data_policy: 'Data policy',
  system_property: 'System property',
  event: 'Event registration',
  script_action: 'Script action',
  table: 'Table',
  field: 'Field',
};

/** Types nowBuilder designs but can't write: the user builds them by hand. */
const BY_HAND = { flow: 'Flows deploy with the ServiceNow SDK (set up automatically on the backend; needs Node.js 20+). If it can’t, build this one in Flow Designer from the steps below.' };

const FIELD_ORDER = ['name', 'short_description', 'collection', 'table', 'when', 'type', 'field_name', 'action_insert',
  'action_update', 'action_delete', 'action_query', 'condition', 'filter_condition', 'conditions', 'order', 'api_name',
  'client_callable', 'access', 'action_name', 'client', 'onclick', 'form_button', 'form_link', 'list_button',
  'on_load', 'reverse_if_false', 'run_scripts', 'ui_type', 'isolate_script', 'active', 'description', 'comments'];

const LABELS = {
  collection: 'Table', table: 'Table', when: 'When', type: 'Type', field_name: 'Field', order: 'Order',
  action_insert: 'On insert', action_update: 'On update', action_delete: 'On delete', action_query: 'On query',
  condition: 'Condition', filter_condition: 'Filter', conditions: 'When it applies', api_name: 'API name',
  client_callable: 'Client callable', access: 'Accessible from', action_name: 'Action name', client: 'Runs in the browser',
  onclick: 'Onclick', form_button: 'Form button', form_link: 'Form link', list_button: 'List button',
  on_load: 'On load', reverse_if_false: 'Reverse if false', run_scripts: 'Runs scripts', ui_type: 'Shown in',
  isolate_script: 'Isolate script', active: 'Active', description: 'Description', comments: 'Description',
  name: 'Name', short_description: 'Name',
  // notification
  event_name: 'Event', recipient_fields: 'Sent to (fields on the record)', recipient_users: 'Sent to (people)',
  recipient_groups: 'Sent to (groups)', subject: 'Subject', message_html: 'Message', message: 'Message (plain text)',
  weight: 'Weight', send_self: 'Send to whoever triggered it', exclude_delegates: 'Exclude delegates',
  content_type: 'Format',
  // flow
  trigger: 'Trigger', trigger_condition: 'Trigger condition', run_trigger: 'Run trigger', run_as: 'Run as',
};

const UI_TYPE = { 0: 'Desktop', 1: 'Mobile', 10: 'All' };
const ACCESS = { package_private: 'This application scope only', public: 'All application scopes' };
const SOURCE = { record: 'Settings', script: 'Script', instance: 'Instance' };

const errorsOf = (c) => (c.problems ?? []).filter((p) => p.severity === 'error');
// Flows can be chosen too: the backend installs them with the ServiceNow SDK, or says why it can't.
const blocked = (c) => c.status !== 'ready' || errorsOf(c).length > 0;
const appLabel = (a) => (!a || a === 'global' ? 'Global' : a);
const flowDeployed = (c) => c.type === 'flow' && c.deploy?.status === 'deployed';

function pretty(key, value) {
  if (value === 'true') return 'Yes';
  if (value === 'false') return 'No';
  if (key === 'ui_type') return UI_TYPE[value] ?? value;
  if (key === 'access') return ACCESS[value] ?? value;
  return value;
}

function CopyButton({ text, label = 'Copy' }) {
  const [state, setState] = useState(label);
  return (
    <button type="button" className="link-btn small" onClick={async () => {
      try { await navigator.clipboard.writeText(text); setState('Copied'); } catch { setState('Copy blocked'); }
      setTimeout(() => setState(label), 1600);
    }}>{state}</button>
  );
}

/** The design, as the user needs it while they build the flow: the settings, then the steps. */
function stepsAsText(component) {
  const record = component.generated?.record ?? {};
  const steps = component.generated?.steps ?? [];
  const head = ['name', 'table', 'trigger', 'trigger_condition', 'run_trigger', 'run_as', 'description']
    .filter((k) => String(record[k] ?? '').trim())
    .map((k) => `${LABELS[k] ?? k.replace(/_/g, ' ')}: ${record[k]}`);
  const body = steps.map((s) => {
    const extra = [s.inside ? `inside step ${s.inside}` : '', s.condition ? `condition: ${s.condition}` : '',
      s.duration ? `duration: ${typeof s.duration === 'object' ? JSON.stringify(s.duration) : s.duration}` : '']
      .filter(Boolean).join(' · ');
    return `${s.step}. ${s.name} (${s.kind})${extra ? `  [${extra}]` : ''}\n   ${s.detail}`;
  });
  return [...head, '', ...body].join('\n');
}

/** A design-only row still has to be buildable: the instance it belongs to, and the design to hand. */
function ByHand({ component, plan }) {
  const { selected } = useWorkspace();
  const base = String(selected?.url ?? '').replace(/\/+$/, '');
  const steps = component.generated?.steps ?? [];
  const exp = component.export;
  const [state, setState] = useState(null);

  const download = async () => {
    setState('Getting the source…');
    try {
      const src = await planApi.flowSource(plan.id, component.id);
      const url = URL.createObjectURL(new Blob([src], { type: 'text/plain' }));
      const a = Object.assign(document.createElement('a'), {
        href: url, download: `${(component.name || 'flow').replace(/[^\w-]+/g, '_').toLowerCase()}.now.js`,
      });
      a.click();
      URL.revokeObjectURL(url);
      setState('Downloaded');
    } catch (e) {
      setState(e.message);
    }
    setTimeout(() => setState(null), 4000);
  };

  return (
    <div className="pi-note by-hand">
      <p>{BY_HAND[component.type]}</p>
      <div className="by-hand-acts">
        {base && (
          <a className="link-btn small" href={`${base}/$flow-designer.do`} target="_blank" rel="noreferrer">
            Open Flow Designer
          </a>
        )}
        {steps.length > 0 && <CopyButton text={stepsAsText(component)} label="Copy the design" />}
        {exp?.exportable && (
          <button type="button" className="link-btn small" onClick={download}>
            {state ?? 'Download SDK source'}
          </button>
        )}
      </div>
      {exp && !exp.exportable && exp.steps > 0 && (
        <p className="by-hand-why">
          {exp.steps_ready === 0
            ? "This one can't be exported as ServiceNow SDK source: "
            : `${exp.steps_ready} of ${exp.steps} steps could be exported as ServiceNow SDK source, but not all: `}
          {exp.blockers[0]}
        </p>
      )}
      {exp?.exportable && (
        <p className="by-hand-why">
          All {exp.steps} steps can be expressed with the ServiceNow SDK {exp.sdk_version}. Building and
          installing it is a separate step you run yourself, in a scoped app.
        </p>
      )}
    </div>
  );
}

/* ---------- diff of a script before and after a fix ---------- */

function diffLines(before, after) {
  const a = before.split('\n');
  const b = after.split('\n');
  // longest common subsequence, small scripts only
  const n = a.length; const m = b.length;
  const grid = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      grid[i][j] = a[i] === b[j] ? grid[i + 1][j + 1] + 1 : Math.max(grid[i + 1][j], grid[i][j + 1]);
    }
  }
  const out = [];
  let i = 0; let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) { out.push({ kind: 'same', text: a[i], a: i + 1, b: j + 1 }); i += 1; j += 1; }
    else if (grid[i + 1][j] >= grid[i][j + 1]) { out.push({ kind: 'del', text: a[i], a: i + 1 }); i += 1; }
    else { out.push({ kind: 'add', text: b[j], b: j + 1 }); j += 1; }
  }
  while (i < n) { out.push({ kind: 'del', text: a[i], a: i + 1 }); i += 1; }
  while (j < m) { out.push({ kind: 'add', text: b[j], b: j + 1 }); j += 1; }
  return out;
}

/** Changed lines with three lines of context around them. */
function trimmed(lines) {
  const keep = new Set();
  lines.forEach((l, idx) => {
    if (l.kind === 'same') return;
    for (let k = Math.max(0, idx - 3); k <= Math.min(lines.length - 1, idx + 3); k += 1) keep.add(k);
  });
  const out = [];
  let gap = false;
  lines.forEach((l, idx) => {
    if (keep.has(idx)) { out.push(l); gap = false; }
    else if (!gap) { out.push({ kind: 'gap' }); gap = true; }
  });
  return out;
}

function Diff({ path, before, after }) {
  const lines = useMemo(() => trimmed(diffLines(before ?? '', after ?? '')), [before, after]);
  const added = lines.filter((l) => l.kind === 'add').length;
  const removed = lines.filter((l) => l.kind === 'del').length;
  if (!added && !removed) return null;
  return (
    <div className="diff">
      <div className="diff-head">
        <span className="api">{path}</span>
        <span className="diff-count"><span className="plus">+{added}</span> <span className="minus">−{removed}</span></span>
      </div>
      <pre className="diff-body">
        {lines.map((l, idx) => (l.kind === 'gap'
          ? <div key={idx} className="diff-gap">⋯</div>
          : (
            <div key={idx} className={`diff-line${l.kind === 'add' ? ' add' : l.kind === 'del' ? ' del' : ''}`}>
              <span className="ln">{l.a ?? ''}</span>
              <span className="ln">{l.b ?? ''}</span>
              <span className="sign">{l.kind === 'add' ? '+' : l.kind === 'del' ? '−' : ' '}</span>
              <span>{l.text}</span>
            </div>
          )))}
      </pre>
    </div>
  );
}

/* ---------- a row's problems ---------- */

function Problems({ problems }) {
  if (!problems.length) return null;
  return (
    <ul className="row-errors">
      {problems.map((p, i) => (
        <li key={i} className={p.severity === 'warning' ? 'is-blocked' : ''}>
          <span className="err-src">{SOURCE[p.source] ?? p.source}</span>
          <span className="err-text">
            {p.message}
            {p.location && <> <span className="err-loc">{p.location}</span></>}
          </span>
        </li>
      ))}
    </ul>
  );
}

/* ---------- the fix panel ---------- */

function FixPanel({ plan, fix, component, onChanged, canBuild }) {
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const change = (fix.changes ?? []).find((c) => c.id === component.id);
  const original = useMemo(() => {
    try { return JSON.parse(fix.original?.[component.id] ?? '{}'); } catch { return {}; }
  }, [fix, component.id]);

  const act = async (what) => {
    setBusy(what); setError(null);
    try {
      const next = what === 'apply' ? await planApi.applyFix(plan.id, fix.id) : await planApi.rejectFix(plan.id, fix.id);
      onChanged(next);
    } catch (e) { setError(e.message); setBusy(null); }
  };

  if (fix.status === 'needs_user_input') {
    return (
      <div className="fix-panel">
        <div className="fix-head"><Icon name="sparkle" size={15} /><strong>Fix with AI needs an answer</strong></div>
        <p>{fix.question}</p>
        <p className="muted small">Reply in the chat with the answer, then run Fix with AI again.</p>
        {canBuild && (
          <div className="fix-actions">
            <span className="spacer" />
            <button type="button" className="btn btn-sm" disabled={busy} onClick={() => act('reject')}>Dismiss</button>
          </div>
        )}
      </div>
    );
  }
  return (
    <div className="fix-panel">
      <div className="fix-head">
        <Icon name="sparkle" size={15} />
        <strong>Suggested fix</strong>
        <span className={`badge ${fix.confidence === 'high' ? 'badge-ok' : fix.confidence === 'low' ? 'badge-warn' : 'badge-neutral'}`}>
          {fix.confidence} confidence
        </span>
        {fix.attempt > 1 && <span className="badge badge-neutral">attempt {fix.attempt}</span>}
      </div>
      <p>{fix.summary}</p>
      {change?.reason && <ul className="fix-changes"><li>{change.reason}</li></ul>}
      <div className="diffs">
        {change && <Diff path="script" before={original.script ?? ''} after={change.script ?? original.script ?? ''} />}
        {change && (
          <Diff
            path="settings"
            before={JSON.stringify(original.record ?? {}, null, 2)}
            after={JSON.stringify(change.record ?? {}, null, 2)}
          />
        )}
      </div>
      {error && <div className="alert alert-error small" role="alert">{error}</div>}
      {canBuild && (
        <div className="fix-actions">
          <span className="spacer" />
          <button type="button" className="btn btn-sm" disabled={busy} onClick={() => act('reject')}>Reject</button>
          <button type="button" className="btn btn-sm btn-primary" disabled={busy} onClick={() => act('apply')}>
            {busy === 'apply' ? 'Applying…' : 'Apply fix'}
          </button>
        </div>
      )}
    </div>
  );
}

/* ---------- editing a script by hand ---------- */

function Editor({ plan, component, onChanged, onClose }) {
  const [text, setText] = useState(component.generated?.script ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const area = useRef(null);
  const gutter = useRef(null);
  const lines = text.split('\n').length;
  const dirty = text !== (component.generated?.script ?? '');

  const save = async () => {
    setBusy(true); setError(null);
    try { onChanged(await planApi.edit(plan.id, component.id, { script: text })); onClose(); }
    catch (e) { setError(e.message); setBusy(false); }
  };

  return (
    <div className="editor">
      <div className="editor-head">
        <strong>Edit the script</strong>
        <p className="muted small">Saving checks it again, the same way as anything the AI wrote.</p>
      </div>
      <div className="editor-body">
        <div className="editor-gutter" ref={gutter}>
          {Array.from({ length: lines }, (_, i) => <div key={i}>{i + 1}</div>)}
        </div>
        <textarea
          ref={area} className="editor-text" value={text} spellCheck={false} aria-label="Script"
          onScroll={() => { if (gutter.current && area.current) gutter.current.scrollTop = area.current.scrollTop; }}
          onChange={(e) => setText(e.target.value)}
        />
      </div>
      {error && <div className="alert alert-error small" role="alert">{error}</div>}
      <div className="fix-actions">
        <span className="spacer" />
        <button type="button" className="btn btn-sm" onClick={onClose} disabled={busy}>Cancel</button>
        <button type="button" className="btn btn-sm btn-primary" onClick={save} disabled={busy || !dirty}>
          {busy ? 'Saving…' : 'Save and check'}
        </button>
      </div>
    </div>
  );
}

/* ---------- one row ---------- */

function Tick({ state }) {
  const cls = { deployed: 'tick-ok', 'rolled back': 'tick-unknown', 'rollback failed': 'tick-fail',
    'not deployed': 'tick-fail', failed: 'tick-fail', 'verification failed': 'tick-fail' }[state];
  if (!cls) return null;
  const path = state === 'deployed' ? 'M5 8.5 7 10.5 11 5.5' : state === 'rolled back' ? 'M5 8h6' : 'M5.5 5.5l5 5M10.5 5.5l-5 5';
  return (
    <span className={`tick ${cls}`} title={`Deployment: ${state}`}>
      <svg width="22" height="22" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.5" /><path d={path} /></svg>
    </span>
  );
}

function RowStatus({ component }) {
  const { status } = component;
  if (status === 'generating') return <span className="pi-working"><span className="spinner sm" aria-hidden="true" />Writing…</span>;
  if (status === 'failed') return <span className="badge badge-err">Couldn’t write</span>;
  if (status !== 'ready') return <span className="badge badge-neutral">Planned</span>;
  if (flowDeployed(component)) return <span className="badge badge-ok">{component.deploy.active ? 'Deployed, active' : 'Deployed'}</span>;
  if (component.deploy?.status === 'waiting for SDK setup') return <span className="badge badge-accent">SDK setting up — click Deploy again when it’s ready</span>;
  if (BY_HAND[component.type]) return <span className="badge badge-warn">{component.deploy?.status === 'failed' ? 'SDK install failed' : 'Build by hand'}</span>;
  const errors = errorsOf(component).length;
  const warnings = (component.problems ?? []).length - errors;
  if (errors) return <span className="badge badge-err">{errors} problem{errors === 1 ? '' : 's'}</span>;
  if (warnings) return <span className="badge badge-warn">{warnings} warning{warnings === 1 ? '' : 's'}</span>;
  return <span className="badge badge-ok">Checked</span>;
}

function Detail({ component }) {
  const generated = component.generated;
  if (!generated) return <div className="pi-detail"><p>{component.purpose}</p></div>;
  const record = generated.record ?? {};
  const keys = Object.keys(record).sort((a, b) => {
    const ia = FIELD_ORDER.indexOf(a); const ib = FIELD_ORDER.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  });
  const actions = generated.actions ?? [];
  const steps = generated.steps ?? [];
  return (
    <div className="pi-detail">
      {component.purpose && <p>{component.purpose}</p>}
      <dl>
        {keys.map((k) => (
          <div key={k}>
            <dt>{LABELS[k] ?? k.replace(/_/g, ' ')}</dt>
            <dd>{String(record[k] ?? '').trim() ? pretty(k, String(record[k])) : <span className="muted">—</span>}</dd>
          </div>
        ))}
      </dl>
      {steps.length > 0 && (
        <ol className="step-list">
          {steps.map((s) => (
            <li key={s.step}>
              <strong>{s.name}</strong> <span className="tag">{s.kind}</span>
              <div>{s.detail}</div>
            </li>
          ))}
        </ol>
      )}
      {actions.length > 0 && (
        <div className="files"><div className="file">
          <div className="file-name"><span>Field actions</span></div>
          <ul className="assumptions" style={{ padding: '8px 12px 10px 28px' }}>
            {actions.map((a) => (
              <li key={a.field}>
                <span className="tag tag-mono">{a.field}</span>{' '}
                {[a.mandatory !== 'ignore' && `mandatory: ${pretty('m', a.mandatory)}`,
                  a.visible !== 'ignore' && `visible: ${pretty('v', a.visible)}`,
                  a.disabled !== 'ignore' && `read only: ${pretty('d', a.disabled)}`].filter(Boolean).join(', ')}
              </li>
            ))}
          </ul>
        </div></div>
      )}
      {generated.script && (
        <div className="files"><div className="file">
          <div className="file-name">
            <span>{TYPE_LABEL[component.type] ?? component.type} script</span>
            <CopyButton text={generated.script} />
          </div>
          <pre className="code">{generated.script}</pre>
        </div></div>
      )}
    </div>
  );
}

function Row({ plan, component, open, onToggle, picking, picked, onPick, onFix, onChanged, fix, canBuild, busy }) {
  const [editing, setEditing] = useState(false);
  const failed = component.status === 'failed';
  const problems = component.problems ?? [];
  const hasErrors = errorsOf(component).length > 0;
  const deployState = component.deploy?.status;
  const canFix = canBuild && (hasErrors || failed) && !fix && !busy;

  return (
    <li className={`plan-item${failed || hasErrors ? ' has-error' : ''}${picking && blocked(component) ? ' is-locked' : ''}`}>
      <div className="plan-item-row">
        {picking && (
          <label className="pick" title={blocked(component) ? 'This has problems to fix first' : `Include ${component.name}`}>
            <input type="checkbox" checked={picked} disabled={blocked(component)} onChange={onPick} />
            <span className="sr-only">Include {component.name}</span>
          </label>
        )}
        <button type="button" className="plan-item-main" aria-expanded={open} onClick={onToggle}>
          <span className="pi-name">
            <span className="pi-title">{component.name || TYPE_LABEL[component.type]}</span>
            <span className="pi-sub">
              {TYPE_LABEL[component.type] ?? component.type}
              {component.table ? <> · <span className="api">{component.table}</span></> : ''}
              {component.edited ? ' · edited' : ''}
            </span>
          </span>
          <span className="pi-tags">
            <span className={`badge ${component.action === 'update' ? 'act-update' : 'act-create'}`}>
              {component.action === 'update' ? 'Change' : 'New'}
            </span>
            <RowStatus component={component} />
          </span>
          <Icon name="chevron" size={14} className="chev" />
        </button>
        {canFix && <button type="button" className="btn btn-sm btn-fix" onClick={onFix}>Fix with AI</button>}
        <Tick state={deployState} />
      </div>

      {failed && component.error && <p className="pi-error">{component.error}</p>}
      {BY_HAND[component.type] && component.status === 'ready' && !flowDeployed(component) && <ByHand component={component} plan={plan} />}
      <Problems problems={problems} />
      {component.deploy?.message && <p className="pi-note">{component.deploy.message}</p>}
      {component.deploy?.status === 'deployed' && component.deploy?.url && (
        <p className="pi-note">
          <a href={component.deploy.url} target="_blank" rel="noreferrer">Open it in ServiceNow</a>
          {component.deploy.application && <span className="muted"> · in {component.deploy.application}</span>}
        </p>
      )}
      {fix && <FixPanel plan={plan} fix={fix} component={component} onChanged={onChanged} canBuild={canBuild} />}
      {editing && <Editor plan={plan} component={component} onChanged={onChanged} onClose={() => setEditing(false)} />}
      {open && <Detail component={component} />}
      {open && canBuild && !editing && component.generated?.script && (
        <p className="pi-note"><button type="button" className="link-btn" onClick={() => setEditing(true)}>Edit the script</button></p>
      )}
    </li>
  );
}

/* ---------- the deploy dialog ---------- */

function DeployDialog({ plan, instance, onClose, onDeploy }) {
  const [name, setName] = useState(`nowBuilder: ${plan.title}`.slice(0, 80));
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const production = instance?.instance_type === 'Production';
  const rows = (plan.components ?? []).filter((c) => (plan.approval?.ids ?? []).includes(c.id));

  const go = async () => {
    setBusy(true); setError(null);
    try { await onDeploy(name.trim(), confirmed); onClose(); } catch (e) { setError(e.message); setBusy(false); }
  };

  return (
    <Dialog title="Deploy into an update set" onClose={busy ? () => {} : onClose}>
      <div className="dialog-body">
        <p>
          nowBuilder creates a new update set in <strong>{instance?.name ?? 'the connected instance'}</strong>,
          in the <strong>{appLabel(plan.application)}</strong> application, makes them your current application and
          update set, and writes these artifacts into it, so you can see it in the update set picker (globe icon) and
          move it to another instance later. Flows are installed with the ServiceNow SDK into the same application.
        </p>
        <ul className="deploy-list">
          {rows.map((c) => (
            <li key={c.id}><span className="api">{c.name}</span><span className="muted">{TYPE_LABEL[c.type]}</span></li>
          ))}
        </ul>
        <div className="field">
          <label className="field-label" htmlFor="us-name">Update set name</label>
          <input id="us-name" className="input" data-autofocus value={name} maxLength={80}
            onChange={(e) => setName(e.target.value)} />
        </div>
        {production && (
          <label className="check-row">
            <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
            <span>I understand <strong>{instance.name}</strong> is a production instance.</span>
          </label>
        )}
        {error && <div className="alert alert-error small" role="alert">{error}</div>}
      </div>
      <div className="dialog-actions">
        <button type="button" className="btn" onClick={onClose} disabled={busy}>Cancel</button>
        <button type="button" className={`btn ${production ? 'btn-danger-solid' : 'btn-primary'}`}
          disabled={busy || !name.trim() || (production && !confirmed)} onClick={go}>
          {busy ? 'Deploying…' : production ? 'Deploy to production' : 'Deploy'}
        </button>
      </div>
    </Dialog>
  );
}

/* ---------- the card ---------- */

export function PlanCard({ plan: initial, onPlanChange }) {
  const { selected, can, instances } = useWorkspace();
  const [moving, setMoving] = useState(false);
  const [showDiagram, setShowDiagram] = useState(false);
  const [plan, setPlan] = useState(initial);
  const [open, setOpen] = useState({});
  const [picked, setPicked] = useState(null);     // null = not choosing yet
  const [busy, setBusy] = useState(null);         // fixing | deploying | rolling back
  const [progress, setProgress] = useState(null);
  const [notice, setNotice] = useState(null);
  const [error, setError] = useState(null);
  const [dialog, setDialog] = useState(null);

  useEffect(() => { setPlan(initial); }, [initial]);

  const canBuild = can('build');
  const canApprove = can('approve');
  const canDeploy = can(selected?.instance_type === 'Production' ? 'deploy_prod' : 'deploy');
  const components = plan.components ?? [];
  const drafting = Boolean(plan.drafting);
  const working = drafting || Boolean(plan.busy) || components.some((c) => c.status === 'generating');
  const ready = components.filter((c) => c.status === 'ready').length;
  const failed = components.filter((c) => c.status === 'failed').length;
  const validation = plan.validation ?? {};
  const deployment = plan.deployment ?? null;
  const deployed = deployment?.status === 'deployed' || deployment?.status === 'partial';
  // Approved rows not in the instance yet (a flow that waited for the SDK, a row that failed): Deploy again.
  const remaining = (plan.approval?.ids ?? []).filter((id) => components.find((c) => c.id === id)?.deploy?.status !== 'deployed');
  const fixes = plan.fixes ?? [];
  const openFixFor = (id) => fixes.find((f) => ['pending', 'needs_user_input'].includes(f.status) && f.group_ids?.includes(id));

  const update = (next) => { setPlan(next); onPlanChange?.(next); };

  const stream = async (path, body, label) => {
    setBusy(label); setError(null); setNotice(null); setProgress(null);
    try {
      await planStream(path, body, (e) => {
        if (e.type === 'status') setProgress(e.text);
        else if (e.type === 'plan') update({ ...e.plan, fixes: plan.fixes });
        else if (e.type === 'fix') update({ ...e.plan, fixes: [...fixes, e.fix] });
        else if (e.type === 'warning') setNotice(e.message);
        else if (e.type === 'error') setError(e.message);
      });
      const fresh = await planApi.get(plan.id);
      update(fresh);
    } catch (e) { setError(e.message); }
    finally { setBusy(null); setProgress(null); }
  };

  const runFix = (id) => stream(`/api/plans/${plan.id}/fix`, { ids: [id] }, 'fixing');
  const deploy = (updateSetName, confirmProduction) =>
    stream(`/api/plans/${plan.id}/deploy`, { update_set_name: updateSetName, confirm_production: confirmProduction }, 'deploying');
  const rollback = () => stream(`/api/plans/${plan.id}/rollback`, {}, 'rolling back');

  const [checking, setChecking] = useState(false);
  const act = async (fn) => {
    setError(null);
    try { update(await fn()); } catch (e) { setError(e.message); }
  };

  const deployable = components.filter((c) => !blocked(c));
  const chosen = picked ?? deployable.map((c) => c.id);
  const approved = plan.approval?.ids ?? null;

  return (
    <section className={`plan-card${drafting ? ' is-draft' : ''}`} aria-label="Implementation plan">
      <header className="plan-head">
        <div className="plan-head-top">
          <h3>{plan.title || 'Putting a plan together…'}</h3>
          <div className="plan-badges">
            <span className="badge badge-neutral" title="Every artifact in this plan is built in this application">{appLabel(plan.application)}</span>
            {plan.story_points > 0 && <span className="badge badge-neutral">{plan.story_points} points</span>}
            {!working && validation.errors > 0 && <span className="badge badge-err">{validation.errors} to fix</span>}
            {!working && !validation.errors && validation.warnings > 0 && <span className="badge badge-warn">{validation.warnings} warnings</span>}
            {!working && !validation.errors && !validation.warnings && ready > 0 && <span className="badge badge-ok">Checks passed</span>}
            {failed > 0 && <span className="badge badge-err">{failed} didn’t write</span>}
            {plan.status === 'approved' && <span className="badge badge-accent">Approved</span>}
            {deployment?.status === 'deployed' && <span className="badge badge-ok">{plan.approval?.auto ? 'Deployed automatically' : 'Deployed'}</span>}
            {deployment?.status === 'partial' && <span className="badge badge-warn">Partly deployed</span>}
            {deployment?.status === 'rolled_back' && <span className="badge badge-neutral">Rolled back</span>}
          </div>
        </div>
        {plan.summary && <p className="plan-summary">{plan.summary}</p>}
      </header>

      {validation.message && !validation.errors && <p className="block-note block-note-plain">{validation.message}</p>}

      <ul className="plan-items">
        {components.map((c) => (
          <Row
            key={c.id} plan={plan} component={c} canBuild={canBuild} busy={busy}
            open={Boolean(open[c.id])} onToggle={() => setOpen({ ...open, [c.id]: !open[c.id] })}
            picking={picked !== null} picked={chosen.includes(c.id)}
            onPick={() => setPicked(chosen.includes(c.id) ? chosen.filter((x) => x !== c.id) : [...chosen, c.id])}
            onFix={() => runFix(c.id)} onChanged={update} fix={openFixFor(c.id)}
          />
        ))}
        {drafting && <li className="plan-item plan-item-skeleton"><span /></li>}
      </ul>

      {picked !== null && (
        <div className="pick-bar">
          <span>{chosen.length} of {deployable.length} chosen</span>
          <span className="pick-shortcuts">
            <button type="button" className="link-btn" onClick={() => setPicked(deployable.map((c) => c.id))}>Select all</button>
            <button type="button" className="link-btn" onClick={() => setPicked([])}>Clear</button>
            <button type="button" className="link-btn" onClick={() => setPicked(null)}>Cancel</button>
          </span>
        </div>
      )}

      <footer className="plan-foot">
        {working || busy ? (
          <p className="plan-progress">
            <span className="spinner" aria-hidden="true" />
            {progress ?? plan.progress ?? (busy ? `${busy[0].toUpperCase()}${busy.slice(1)}…` : 'Writing the artifacts…')}
          </p>
        ) : (
          <div className="plan-stats">
            <span><strong>{components.length}</strong> artifact{components.length === 1 ? '' : 's'}</span>
            {ready > 0 && <span><strong>{ready}</strong> written</span>}
            {plan.story_points > 0 && <span><strong>{plan.story_points}</strong> story points</span>}
            <span className="spacer" />
            {canBuild && ready > 0 && (
              <button type="button" className="btn btn-sm" disabled={checking}
                onClick={async () => {
                  setChecking(true); setNotice(null);
                  await act(async () => {
                    const next = await planApi.check(plan.id);
                    const v = next.validation ?? {};
                    setNotice(v.errors
                      ? `Checked against ${selected?.name ?? 'the instance'}: ${v.errors} problem${v.errors === 1 ? '' : 's'} to fix${v.warnings ? `, ${v.warnings} warning${v.warnings === 1 ? '' : 's'}` : ''}.`
                      : `Checked against ${selected?.name ?? 'the instance'}: no problems${v.warnings ? ` (${v.warnings} warning${v.warnings === 1 ? '' : 's'})` : ''}.`);
                    return next;
                  });
                  setChecking(false);
                }}>{checking ? 'Checking…' : 'Check again'}</button>
            )}
            {!approved && canApprove && deployable.length > 0 && picked === null && (
              <button type="button" className="btn btn-sm" onClick={() => setPicked(deployable.map((c) => c.id))}>Choose and approve</button>
            )}
            {!approved && canApprove && picked !== null && (
              <button type="button" className="btn btn-sm btn-primary" disabled={!chosen.length}
                onClick={() => act(async () => { const p = await planApi.approve(plan.id, chosen); setPicked(null); return p; })}>
                Approve {chosen.length} artifact{chosen.length === 1 ? '' : 's'}
              </button>
            )}
            {approved && !deployed && canApprove && (
              <button type="button" className="btn btn-sm" onClick={() => act(() => planApi.unapprove(plan.id))}>Unapprove</button>
            )}
            {approved && remaining.length > 0 && canDeploy && (
              <button type="button" className="btn btn-sm btn-primary" onClick={() => setDialog('deploy')}>
                {deployed ? `Deploy the remaining ${remaining.length}…` : 'Deploy…'}
              </button>
            )}
            <button type="button" className="btn btn-sm" aria-pressed={showDiagram} onClick={() => setShowDiagram((v) => !v)}>
              {showDiagram ? 'Hide diagram' : 'Diagram'}
            </button>
            <button type="button" className="btn btn-sm" onClick={() => downloadDocument(plan).catch((e) => setError(e.message))}>
              Design document
            </button>
            {deployed && canDeploy && deployment?.update_set?.sys_id && instances?.length > 1 && (
              <button type="button" className="btn btn-sm" onClick={() => setMoving(true)}>Move to another instance…</button>
            )}
            {deployed && canDeploy && (
              <button type="button" className="btn btn-sm btn-danger-outline" onClick={rollback}>Roll back</button>
            )}
          </div>
        )}
        {moving && <MoveUpdateSet plan={plan} onClose={() => setMoving(false)} />}
        {showDiagram && <PlanDiagram plan={plan} />}

        {error && <div className="alert alert-error small" role="alert">{error}</div>}
        {notice && <div className="alert alert-warn small">{notice}</div>}

        {deployment?.update_set && (
          <p className="plan-next ok">
            {deployment.status === 'rolled_back' ? 'Rolled back from ' : 'Deployed into '}
            <a href={deployment.update_set.url} target="_blank" rel="noreferrer">{deployment.update_set.name}</a>
            {deployment.status === 'deployed' && (deployment.update_set_current
              ? ' — it is now your current update set in the instance (refresh ServiceNow to see it in the update set picker).'
              : ' — review it in the instance, then move it on as usual.')}
          </p>
        )}

        {(plan.assumptions ?? []).length > 0 && (
          <ul className="assumptions">{plan.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul>
        )}

        {!working && !busy && components.length > 0 && !approved && !deployed && (
          <p className="plan-next">
            {validation.errors > 0
              ? 'Fix the problems above, or edit a script yourself, then approve what should go in.'
              : 'Open a row to read its settings and script. Approve what should go in, then deploy it into an update set.'}
          </p>
        )}
      </footer>

      {dialog === 'deploy' && (
        <DeployDialog plan={plan} instance={selected} onClose={() => setDialog(null)} onDeploy={deploy} />
      )}
    </section>
  );
}

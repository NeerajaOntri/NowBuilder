import { useEffect, useState } from 'react';
import { api } from '../api';
import { useWorkspace } from '../instances';

const METHODS = [
  { value: 'basic', label: 'Username and password' },
  { value: 'oauth', label: 'OAuth client' },
];
const METHOD_NAME = { basic: 'Username and password', oauth: 'OAuth (password grant)' };

const TYPES = [
  { value: 'Development', hint: 'Personal developer instance or dev' },
  { value: 'Test', hint: 'Test, QA or UAT instance' },
  { value: 'Production', hint: 'Live instance with real users' },
];

function useAction() {
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const run = async (key, fn) => {
    setBusy(key);
    setError(null);
    try { await fn(); } catch (e) { setError(e.message); } finally { setBusy(null); }
  };
  return { busy, error, setError, run };
}

function TypePicker({ value, onChange }) {
  return (
    <div className="field">
      <span id="inst-type-label" style={{ fontSize: 13, fontWeight: 500 }}>Instance type</span>
      <div className="type-picker" role="radiogroup" aria-labelledby="inst-type-label">
        {TYPES.map((t) => (
          <button type="button" key={t.value} role="radio" aria-checked={value === t.value}
            className={`type-option${t.value === 'Production' ? ' prod' : ''}`} onClick={() => onChange(t.value)}>
            <strong>{t.value}</strong><span>{t.hint}</span>
          </button>
        ))}
      </div>
      {value === 'Production' && (
        <div className="alert alert-warn small">Changes to production affect real users. nowBuilder always asks before deploying, and everything goes into an update set you can review.</div>
      )}
    </div>
  );
}

function OAuthHelp() {
  return (
    <details className="help">
      <summary>How to create the OAuth client in ServiceNow</summary>
      <ol>
        <li>In the instance, open <strong>System OAuth → Application Registry</strong> and click <strong>New</strong>.</li>
        <li>Choose <strong>Create an OAuth API endpoint for external clients</strong>.</li>
        <li>Give it a name (for example nowBuilder) and save. ServiceNow fills in the <strong>Client ID</strong> and generates the <strong>Client Secret</strong>.</li>
        <li>Copy both into this form. nowBuilder signs in once with the username and password, then keeps a refresh token and renews access itself.</li>
      </ol>
    </details>
  );
}

function ConnectForm({ onDone, onCancel }) {
  const [f, setF] = useState({ name: '', instance_type: 'Development', url: '', auth_method: 'basic', username: '', password: '', client_id: '', client_secret: '', auto_deploy: true });
  const { busy, error, run, setError } = useAction();
  // Optional pre-fill (NOWBUILDER_DEFAULT_INSTANCE_URL); usually empty, so any instance can be entered
  useEffect(() => {
    let live = true;
    api('/api/instances/defaults').then((d) => {
      if (live) setF((cur) => ({ ...cur, url: cur.url || d.url || '', auto_deploy: d.auto_deploy ?? true }));
    }).catch(() => {});
    return () => { live = false; };
  }, []);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const oauth = f.auth_method === 'oauth';
  const ready = f.name && f.url && f.username && f.password && (!oauth || (f.client_id && f.client_secret));

  const submit = (e) => {
    e.preventDefault();
    run('connect', async () => {
      const json = { ...f, client_id: oauth ? f.client_id : '', client_secret: oauth ? f.client_secret : '',
      };
      delete json.auto_deploy;
      const inst = await api('/api/instances', { method: 'POST', json });
      onDone(`Connected to ${inst.name}${inst.release ? ` (${inst.release})` : ''}.`);
    });
  };

  return (
    <form className="panel form" onSubmit={submit} noValidate>
      <div className="panel-title"><h2>Connect a ServiceNow instance</h2></div>
      <div className="method-tabs" role="tablist" aria-label="Sign-in method">
        {METHODS.map((m) => (
          <button key={m.value} type="button" role="tab" aria-selected={f.auth_method === m.value} className="method-tab"
            onClick={() => { setF({ ...f, auth_method: m.value }); setError(null); }}>{m.label}</button>
        ))}
      </div>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      <div className="field">
        <label htmlFor="inst-name">Name</label>
        <input id="inst-name" className="input" placeholder="Acme dev" value={f.name} onChange={set('name')} required />
        <span className="hint">How this instance appears in nowBuilder.</span>
      </div>
      <TypePicker value={f.instance_type} onChange={(t) => setF({ ...f, instance_type: t })} />
      <div className="field">
        <label htmlFor="inst-url">Instance address</label>
        <input id="inst-url" className="input" placeholder="https://your-instance.service-now.com" value={f.url} onChange={set('url')} required />
        <span className="hint">The full address, or just the instance name (for example dev12345).</span>
      </div>
      {oauth && <OAuthHelp />}
      <div className="form-row">
        <div className="field">
          <label htmlFor="inst-user">Username</label>
          <input id="inst-user" className="input" autoComplete="off" placeholder="admin" value={f.username} onChange={set('username')} required />
        </div>
        <div className="field">
          <label htmlFor="inst-pass">Password</label>
          <input id="inst-pass" className="input" type="password" autoComplete="off" value={f.password} onChange={set('password')} required />
        </div>
      </div>
      {oauth && (
        <div className="form-row">
          <div className="field">
            <label htmlFor="inst-cid">Client ID</label>
            <input id="inst-cid" className="input api" autoComplete="off" value={f.client_id} onChange={set('client_id')} required />
          </div>
          <div className="field">
            <label htmlFor="inst-cs">Client secret</label>
            <input id="inst-cs" className="input" type="password" autoComplete="off" value={f.client_secret} onChange={set('client_secret')} required />
          </div>
        </div>
      )}
      <p className="muted small">Use an account with the <strong>admin</strong> role. nowBuilder reads tables and scripts, and creates business rules, script includes, client scripts, UI policies, UI actions and notifications in a new update set when it deploys.</p>
      <div className="form-actions">
        {onCancel && <button type="button" className="btn" onClick={onCancel}>Cancel</button>}
        <button className="btn btn-primary" disabled={busy !== null || !ready}>{busy ? 'Connecting…' : 'Connect instance'}</button>
      </div>
    </form>
  );
}

function UpdateSignIn({ inst, onDone, onCancel }) {
  const [f, setF] = useState({ username: inst.username, password: '', client_secret: '' });
  const { busy, error, run } = useAction();
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <form className="form" style={{ padding: '16px 20px', borderTop: '1px solid var(--line)' }}
      onSubmit={(e) => {
        e.preventDefault();
        const json = { username: f.username, password: f.password, ...(f.client_secret ? { client_secret: f.client_secret } : {}) };
        run('save', async () => onDone(await api(`/api/instances/${inst.id}`, { method: 'PATCH', json })));
      }}>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      <div className="form-row">
        <div className="field"><label htmlFor={`u-${inst.id}`}>Username</label>
          <input id={`u-${inst.id}`} className="input" autoComplete="off" value={f.username} onChange={set('username')} /></div>
        <div className="field"><label htmlFor={`p-${inst.id}`}>Password</label>
          <input id={`p-${inst.id}`} className="input" type="password" autoComplete="off" value={f.password} onChange={set('password')} /></div>
      </div>
      {inst.auth_method === 'oauth' && (
        <div className="field"><label htmlFor={`s-${inst.id}`}>New client secret</label>
          <input id={`s-${inst.id}`} className="input" type="password" autoComplete="off" placeholder="Leave blank to keep" value={f.client_secret} onChange={set('client_secret')} /></div>
      )}
      <div className="form-actions">
        <button type="button" className="btn btn-sm" onClick={onCancel}>Cancel</button>
        <button className="btn btn-sm btn-primary" disabled={busy !== null || !f.username || !f.password}>{busy ? 'Checking…' : 'Save and check'}</button>
      </div>
    </form>
  );
}

// The instance's active custom scripts checked against the rules nowBuilder builds with. Read-only.
function HealthReport({ report, onClose }) {
  const [all, setAll] = useState(false);
  const shown = all ? report.findings : report.findings.slice(0, 15);
  const ask = (f) => `/workspace?idea=${encodeURIComponent(`Explain and fix the ${f.type.replace('_', ' ')} "${f.name}"${f.on ? ` on ${f.on}` : ''} (sys_id ${f.sys_id}): ${f.message}`)}`;
  return (
    <section className="org-card-main" aria-label="Health check">
      <div className="org-card-top">
        <span className="health-score">{report.score}</span><span className="muted">/ 100</span>
        <span className="muted small">{report.scanned} custom scripts read · {report.errors} errors · {report.warnings} warnings</span>
        <span className="spacer" /><button className="btn btn-sm" onClick={onClose}>Close</button>
      </div>
      {report.unreadable?.length > 0 && <div className="alert alert-warn small">Couldn't read: {report.unreadable.join('; ')}</div>}
      {report.findings.length === 0 && <div className="alert alert-success small">No problems found in the custom scripts read.</div>}
      {shown.map((f, i) => (
        <div key={i} className={`finding${f.severity === 'error' ? ' error' : ''}`}>
          <div><strong>{f.name}</strong> <small>{f.type.replace('_', ' ')}{f.on ? ` · ${f.on}` : ''}</small></div>
          <div className="small">{f.message}</div>
          <small><a href={f.url} target="_blank" rel="noreferrer">Open in ServiceNow</a> · <a href={ask(f)}>Fix with nowBuilder</a></small>
        </div>
      ))}
      {!all && report.findings.length > 15 && <button className="btn btn-sm" onClick={() => setAll(true)}>Show all {report.findings.length}</button>}
    </section>
  );
}

function InstanceCard({ inst, onChange, onRemoved }) {
  const { busy, error, run } = useAction();
  const { can } = useWorkspace();
  const manage = can('manage_instances');
  const [editing, setEditing] = useState(false);
  const [health, setHealth] = useState(null);
  const prod = inst.instance_type === 'Production';
  const checked = inst.last_checked_at ? new Date(inst.last_checked_at).toLocaleString() : 'Never';
  const call = (key, path, method = 'POST') => run(key, async () => { await api(path, { method }); onChange(); });
  const roles = inst.roles?.length ? inst.roles.slice(0, 8).join(', ') + (inst.roles.length > 8 ? ` and ${inst.roles.length - 8} more` : '') : '—';

  return (
    <article className={`org-card${inst.is_selected ? ' is-selected' : ''}`} aria-label={inst.name}>
      <div className="org-card-main">
        <div className="org-card-top">
          <h3>{inst.name}</h3>
          <span className={`badge ${prod ? 'badge-prod' : 'badge-neutral'}`}>{inst.instance_type}</span>
          {inst.status === 'connected'
            ? <span className="badge badge-ok"><span className="dot" aria-hidden="true" />Connected</span>
            : <span className="badge badge-err"><span className="dot" aria-hidden="true" />Can't connect</span>}
          {inst.is_selected && <span className="badge badge-accent">In use</span>}
        </div>
        {inst.status_message && <div className={`alert ${inst.status === 'error' ? 'alert-error' : 'alert-warn'} small`}>{inst.status_message}</div>}
        {error && <div className="alert alert-error small" role="alert">{error}</div>}
        <dl className="org-meta">
          <div><dt>Address</dt><dd style={{ overflowWrap: 'anywhere' }}>{inst.url}</dd></div>
          <div><dt>Release</dt><dd>{inst.release ?? '—'}</dd></div>
          <div><dt>Signed in as</dt><dd>{inst.user_display_name ? `${inst.user_display_name} (${inst.username})` : inst.username}</dd></div>
          <div><dt>Sign-in</dt><dd>{METHOD_NAME[inst.auth_method]}</dd></div>
          <div><dt>Roles</dt><dd>{roles}</dd></div>
          <div><dt>Last checked</dt><dd>{checked}</dd></div>
          <div><dt>Deploys</dt><dd>{prod ? 'From the plan card, after confirming' : 'From the plan card: Approve, then Deploy'}</dd></div>
        </dl>
      </div>
      {health && <HealthReport report={health} onClose={() => setHealth(null)} />}
      {editing && <UpdateSignIn inst={inst} onCancel={() => setEditing(false)} onDone={() => { setEditing(false); onChange(); }} />}
      <div className="org-card-actions">
        {!inst.is_selected && <button className="btn btn-sm btn-primary" disabled={busy !== null} onClick={() => call('select', `/api/instances/${inst.id}/select`)}>Use this instance</button>}
        <button className="btn btn-sm" disabled={busy !== null} onClick={() => call('test', `/api/instances/${inst.id}/test`)}>{busy === 'test' ? 'Checking…' : 'Check connection'}</button>
        {inst.status === 'connected' && <button className="btn btn-sm" disabled={busy !== null}
          onClick={() => run('health', async () => setHealth(await api(`/api/instances/${inst.id}/health`, { method: 'POST' })))}>
          {busy === 'health' ? 'Scanning…' : 'Health check'}</button>}
        {manage && !editing && <button className="btn btn-sm" onClick={() => setEditing(true)}>Update sign-in</button>}
        <span className="spacer" />
        {manage && <button className="btn btn-sm btn-danger" disabled={busy !== null}
          onClick={() => {
            if (!window.confirm(`Remove ${inst.name}? nowBuilder deletes the saved sign-in. Nothing in the instance changes.`)) return;
            run('delete', async () => { await api(`/api/instances/${inst.id}`, { method: 'DELETE' }); onRemoved(); });
          }}>
          Remove
        </button>}
      </div>
    </article>
  );
}

export function InstancesSettingsPage() {
  const { instances, refresh, can, ws } = useWorkspace();
  const manage = can('manage_instances');
  const lim = ws?.limits.instances;
  const full = Boolean(lim && lim.used >= lim.max);
  const [adding, setAdding] = useState(false);
  const [notice, setNotice] = useState(null);

  if (!instances) return <div className="page-loading" role="status">Loading instances…</div>;
  const showForm = manage && !full && (adding || instances.length === 0);
  const done = async (msg) => { setNotice(msg ? { kind: 'success', text: msg } : null); await refresh(); };

  return (
    <>
      <div className="section-head">
        <div>
          <h1>ServiceNow instances</h1>
          <p className="muted">nowBuilder reads and builds in the instance marked “In use”. Each member chooses the instance they work in.
            {lim && <> This workspace can connect {lim.max} {lim.max === 1 ? 'instance' : 'instances'}; {lim.used} {lim.used === 1 ? 'is' : 'are'} connected.</>}</p>
        </div>
        {!showForm && manage && !full && <button className="btn btn-primary" onClick={() => { setAdding(true); setNotice(null); }}>Connect another instance</button>}
      </div>
      {!manage && <div className="alert alert-info small" style={{ marginBottom: 16 }}>Only workspace admins can connect, update or remove instances. {instances.length === 0 ? 'Ask an admin to connect one, or to give you access to one.' : ''}</div>}
      {manage && full && <div className="alert alert-warn small" style={{ marginBottom: 16 }}>This workspace has {lim.used} of {lim.max} instances connected. To connect a different one, remove one first.</div>}
      {notice && <div className={`alert alert-${notice.kind}`} role="status" style={{ marginBottom: 16 }}>{notice.text}</div>}
      {showForm && (
        <div style={{ marginBottom: 20 }}>
          <ConnectForm onCancel={instances.length ? () => setAdding(false) : undefined} onDone={(msg) => { setAdding(false); done(msg); }} />
        </div>
      )}
      <div className="org-list">
        {instances.map((i) => (
          <InstanceCard key={i.id} inst={i} onChange={() => done(null)} onRemoved={() => done('Instance removed.')} />
        ))}
      </div>
    </>
  );
}

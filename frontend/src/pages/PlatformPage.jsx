import { useCallback, useEffect, useMemo, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { ConfirmDialog, Dialog } from '../components/Dialog';
import { Icon } from '../components/Icon';
import { ago } from '../time';
import { platformApi } from '../platformApi';

const STATUS = {
  pending: { label: 'Waiting for approval', cls: 'badge-warn' },
  active: { label: 'Active', cls: 'badge-ok' },
  suspended: { label: 'Turned off', cls: 'badge-neutral' },
};
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** Platform admins only: every workspace, its plan and limits, approvals, turning workspaces off and on. */
export function PlatformPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState(null);
  const [query, setQuery] = useState('');
  const [editing, setEditing] = useState(null);
  const [toggling, setToggling] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [notice, setNotice] = useState(null);
  const [tab, setTab] = useState('workspaces');

  const load = useCallback(() => platformApi.list().then((d) => { setData(d); setError(null); }).catch((e) => setError(e.message)), []);
  useEffect(() => { if (user?.is_platform_admin) load(); }, [load, user]);

  const shown = filter ?? (data && data.counts.pending > 0 ? 'pending' : 'all');
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data?.workspaces ?? []).filter((w) => (shown === 'all' || w.status === shown)
      && (!q || `${w.name} ${w.owner.name} ${w.owner.email}`.toLowerCase().includes(q)));
  }, [data, shown, query]);

  if (!user?.is_platform_admin) return <Navigate to="/" replace />;

  const saved = (d, text) => {
    setData(d); setNotice(text); setEditing(null); setToggling(null); setDeleting(null);
    window.dispatchEvent(new Event('platform-changed'));  // the top bar's waiting count
  };

  return (
    <div className="section-page">
      <header className="sec-head">
        <span className="sec-ico tone-violet"><Icon name="shield" size={22} /></span>
        <div className="sec-head-main">
          <h1>Platform</h1>
          <p>Every nowBuilder workspace. Approve new sign-ups, choose each workspace's plan and limits, and turn a workspace off or back on. Only platform admins see this page.</p>
        </div>
      </header>

      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {notice && <div className="alert alert-success" role="status">{notice}</div>}

      <div className="tabs" role="tablist" aria-label="Platform">
        <button type="button" role="tab" aria-selected={tab === 'workspaces'} className={`tab${tab === 'workspaces' ? ' on' : ''}`} onClick={() => { setTab('workspaces'); setNotice(null); }}>
          <Icon name="grid" /> Workspaces{data && data.counts.pending > 0 && <span className="tab-count">{data.counts.pending}</span>}
        </button>
        <button type="button" role="tab" aria-selected={tab === 'admins'} className={`tab${tab === 'admins' ? ' on' : ''}`} onClick={() => { setTab('admins'); setNotice(null); }}>
          <Icon name="shield" /> Platform admins
        </button>
      </div>

      {tab === 'admins' ? <Admins /> : <>
      {data && (
        <section className="seats plat-counts" aria-label="Workspaces">
          <div className={`seat${data.counts.pending ? ' attention' : ''}`}>
            <span className="seat-label">Waiting for approval</span>
            <strong>{data.counts.pending}</strong>
            <span className="small muted">{data.signup === 'approval' ? 'New sign-ups wait here until you approve them' : 'Sign-up is open: new workspaces start active'}</span>
          </div>
          <div className="seat">
            <span className="seat-label">Active</span>
            <strong>{data.counts.active}</strong>
            <span className="small muted">Using nowBuilder now</span>
          </div>
          <div className="seat">
            <span className="seat-label">Turned off</span>
            <strong>{data.counts.suspended}</strong>
            <span className="small muted">Their data is kept</span>
          </div>
        </section>
      )}

      <section className="block" aria-labelledby="plat-h">
        <div className="block-head plat-head">
          <h2 id="plat-h">Workspaces</h2>
          <div className="plat-tools">
            <div className="seg" role="tablist" aria-label="Show">
              {(['pending', 'active', 'suspended', 'all']).map((f) => (
                <button key={f} type="button" role="tab" aria-selected={shown === f} className={shown === f ? 'on' : ''} onClick={() => setFilter(f)}>
                  {f === 'all' ? 'All' : STATUS[f].label}{data && f !== 'all' ? ` ${data.counts[f]}` : ''}
                </button>
              ))}
            </div>
            <input className="input input-sm plat-search" type="search" placeholder="Search name or email" aria-label="Search workspaces" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
        </div>
        {!data ? <p className="block-pad muted">Loading…</p> : rows.length === 0 ? (
          <p className="block-pad muted">{query ? 'No workspace matches that search.' : shown === 'pending' ? 'Nobody is waiting for approval.' : 'No workspaces here.'}</p>
        ) : (
          <ul className="plat-list">
            {rows.map((w) => <WorkspaceRow key={w.id} w={w} mine={w.in_use && w.owner.email.toLowerCase() === user.email.toLowerCase()}
              onEdit={() => { setNotice(null); setEditing(w); }} onToggle={() => { setNotice(null); setToggling(w); }} onDelete={() => { setNotice(null); setDeleting(w); }} />)}
          </ul>
        )}
      </section>
      </>}

      {deleting && <DeleteDialog w={deleting} onClose={() => setDeleting(null)}
        onDeleted={(d, name) => saved(d, `${name} is deleted. Its people keep their accounts; if they sign in again they start with a new workspace.`)} />}
      {editing && data && <EditDialog w={editing} plans={data.plans} onClose={() => setEditing(null)} onSaved={saved} />}
      {toggling && (
        <ConfirmDialog title={toggling.status === 'suspended' ? `Turn ${toggling.name} back on?` : `Turn off ${toggling.name}?`}
          confirmLabel={toggling.status === 'suspended' ? 'Turn on' : 'Turn off'} danger={toggling.status !== 'suspended'}
          onCancel={() => setToggling(null)}
          onConfirm={async () => {
            const on = toggling.status === 'suspended';
            const d = await platformApi.update(toggling.id, { status: on ? 'active' : 'suspended' });
            saved(d, on ? `${toggling.name} is on again.` : `${toggling.name} is turned off. Its members see a message saying so.`);
          }}>
          {toggling.status === 'suspended'
            ? <p>Its {plural(toggling.members.used, 'member')} can use nowBuilder again straight away, with their instances and chats as they left them.</p>
            : <p>Its {plural(toggling.members.used, 'member')} won't be able to use nowBuilder until you turn it back on. Nothing is deleted: instances and chats are kept.</p>}
        </ConfirmDialog>
      )}
    </div>
  );
}

function Usage({ label, used, max, extra }) {
  const over = used > max;
  return (
    <div className={`plat-use${over ? ' over' : used >= max ? ' full' : ''}`}>
      <span className="plat-use-label">{label}</span>
      <strong>{used} of {max}</strong>
      {extra && <span className="plat-use-extra">{extra}</span>}
      {over && <span className="plat-use-extra">Over the limit: they can't add more</span>}
    </div>
  );
}

function WorkspaceRow({ w, mine, onEdit, onToggle, onDelete }) {
  const st = STATUS[w.status];
  const when = w.status === 'pending' ? `Signed up ${ago(w.created_at)}` : w.last_activity_at ? `Last active ${ago(w.last_activity_at)}` : `Joined ${ago(w.created_at)}`;
  return (
    <li className={`plat-row plat-${w.status}`}>
      <div className="plat-who">
        <p className="plat-name"><strong>{w.name}</strong> <span className={`badge ${st.cls}`}>{st.label}</span>{mine ? <span className="badge badge-info">Yours</span> : w.platform_admin && <span className="badge badge-neutral">Platform admin</span>}
          {!w.in_use && <span className="badge badge-neutral" title="The owner now works in another workspace, so nobody opens this one.">Not in use</span>}</p>
        <p className="small">{w.owner.name} <span className="muted">{w.owner.email}</span></p>
        <p className="small muted">{when}{w.note ? `. Note: ${w.note}` : ''}</p>
      </div>
      <div className="plat-limits">
        <div className="plat-use">
          <span className="plat-use-label">Plan</span>
          <strong>{w.plan_label}</strong>
          {(w.instances.custom || w.members.custom) && <span className="plat-use-extra">Custom limits</span>}
        </div>
        <Usage label="Instances" used={w.instances.used} max={w.instances.max} />
        <Usage label="Members" used={w.members.used + w.members.invites} max={w.members.max} extra={w.members.invites ? `${w.members.invites} invited` : undefined} />
        <div className="plat-use" title="AI credits used this month (1 credit = 1,000 tokens)">
          <span className="plat-use-label">AI credits</span>
          <strong>{(w.ai_month?.credits ?? 0).toLocaleString()}</strong>
          <span className="plat-use-extra">this month</span>
        </div>
      </div>
      <div className="plat-actions">
        {w.status === 'pending' ? (
          <button type="button" className="btn btn-sm btn-primary" onClick={onEdit}>Review and approve</button>
        ) : (
          <>
            <button type="button" className="btn btn-sm" onClick={onEdit}>Edit plan</button>
            {!w.platform_admin && <button type="button" className="btn btn-sm" onClick={onToggle}>{w.status === 'suspended' ? 'Turn on' : 'Turn off'}</button>}
          </>
        )}
        {!mine && <button type="button" className="btn btn-sm btn-danger" onClick={onDelete}>Delete</button>}
      </div>
    </li>
  );
}

function EditDialog({ w, plans, onClose, onSaved }) {
  const [plan, setPlan] = useState(w.plan);
  const [custom, setCustom] = useState(w.instances.custom || w.members.custom);
  const base = plans.find((p) => p.id === plan) ?? plans[0];
  const [orgs, setOrgs] = useState(String(w.instances.max));
  const [members, setMembers] = useState(String(w.members.max));
  const [note, setNote] = useState(w.note);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const approving = w.status === 'pending';
  const maxOrgs = custom ? Number(orgs) : base.instances;
  const maxMembers = custom ? Number(members) : base.members;
  const valid = Number.isInteger(maxOrgs) && Number.isInteger(maxMembers) && maxOrgs >= 1 && maxMembers >= 1 && maxOrgs <= 500 && maxMembers <= 500;
  const memberUse = w.members.used + w.members.invites;

  const save = async () => {
    setBusy(true); setError(null);
    try {
      const d = await platformApi.update(w.id, {
        plan, max_instances: custom ? maxOrgs : null, max_members: custom ? maxMembers : null, note,
        ...(approving ? { status: 'active'  } : {}),
      });
      onSaved(d, approving ? `${w.name} is approved: ${plural(maxOrgs, 'instance')} and ${plural(maxMembers, 'member')}. ${w.owner.name || 'The owner'} can start now.`
        : `${w.name} now allows ${plural(maxOrgs, 'instance')} and ${plural(maxMembers, 'member')}.`);
    } catch (e) { setError(e.message); setBusy(false); }
  };

  return (
    <Dialog title={approving ? `Approve ${w.name}` : `Plan for ${w.name}`} onClose={busy ? () => {} : onClose} wide>
      <div className="dialog-body plat-edit">
        <p className="small muted">Owner: {w.owner.name} ({w.owner.email}). Uses {plural(w.instances.used, 'instance')} and {plural(memberUse, 'member')}{w.members.invites ? ' including invites' : ''}.</p>
        <fieldset className="plat-plans">
          <legend>Plan</legend>
          {plans.map((p) => (
            <label key={p.id} className={`plat-plan${plan === p.id ? ' on' : ''}`}>
              <input type="radio" name="plan" value={p.id} checked={plan === p.id} onChange={() => { setPlan(p.id); if (!custom) { setOrgs(String(p.instances)); setMembers(String(p.members)); } }} />
              <strong>{p.label}</strong>
              <span>{plural(p.instances, 'instance')}, {plural(p.members, 'member')}</span>
            </label>
          ))}
        </fieldset>
        <label className="check-row">
          <input type="checkbox" checked={custom} onChange={(e) => { setCustom(e.target.checked); if (!e.target.checked) { setOrgs(String(base.instances)); setMembers(String(base.members)); } }} />
          Set custom limits for this workspace
        </label>
        {custom && (
          <div className="plat-nums">
            <div className="field">
              <label htmlFor="pl-orgs">ServiceNow instances</label>
              <input id="pl-orgs" className="input" type="number" min={1} max={500} value={orgs} onChange={(e) => setOrgs(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="pl-members">Members, including invites</label>
              <input id="pl-members" className="input" type="number" min={1} max={500} value={members} onChange={(e) => setMembers(e.target.value)} />
            </div>
          </div>
        )}
        {valid && (maxOrgs < w.instances.used || maxMembers < memberUse) && (
          <p className="alert alert-warn small">This is below what they use now. Nothing is removed; they just can't add more instances or members until they're under the limit.</p>
        )}
        <div className="field">
          <label htmlFor="pl-note">Note <span className="muted">(only platform admins see it)</span></label>
          <input id="pl-note" className="input" maxLength={500} placeholder="For example: paid until 31 Dec, or trial" value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        {error && <div className="alert alert-error small" role="alert">{error}</div>}
      </div>
      <div className="dialog-actions">
        <button type="button" className="btn" disabled={busy} onClick={onClose}>Cancel</button>
        <button type="button" className="btn btn-primary" disabled={busy || !valid} onClick={save}>{busy ? 'Saving…' : approving ? 'Approve' : 'Save'}</button>
      </div>
    </Dialog>
  );
}

function DeleteDialog({ w, onClose, onDeleted }) {
  const [typed, setTyped] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const go = async () => {
    setBusy(true); setError(null);
    try { const d = await platformApi.remove(w.id, typed); onDeleted(d, d.deleted); } catch (e) { setError(e.message); setBusy(false); }
  };
  const people = w.members.used;
  return (
    <Dialog title={`Delete ${w.name}?`} onClose={busy ? () => {} : onClose}>
      <div className="dialog-body plat-edit">
        <p>This deletes the workspace and everything in it, for good: {w.instances.used ? `its ${plural(w.instances.used, 'ServiceNow instance connection')}, ` : ''}every chat, the AI provider key, Jira and GitHub connections, and invites.</p>
        <p className="small muted">{people === 1 ? '1 person loses access to it. ' : people > 1 ? `${people} people lose access to it. ` : ''}Their nowBuilder accounts stay: if they sign in again they start with a new workspace of their own{' '}
          (waiting for approval if sign-up needs approval). Nothing in ServiceNow changes: what was deployed stays in the instances.</p>
        {!w.in_use && <p className="alert alert-warn small">Nobody uses this workspace now: its owner works in another one.</p>}
        <div className="field">
          <label htmlFor="del-name">Type <strong>{w.name}</strong> to confirm</label>
          <input id="del-name" className="input" autoComplete="off" value={typed} onChange={(e) => setTyped(e.target.value)} />
        </div>
        {error && <div className="alert alert-error small" role="alert">{error}</div>}
      </div>
      <div className="dialog-actions">
        <button type="button" className="btn" disabled={busy} onClick={onClose}>Cancel</button>
        <button type="button" className="btn btn-danger-solid" disabled={busy || typed.trim() !== w.name} onClick={go}>{busy ? 'Deleting…' : 'Delete workspace'}</button>
      </div>
    </Dialog>
  );
}

/** Who can open this page. The first admin comes from the server setting; the rest are added here. */
function Admins() {
  const [list, setList] = useState(null);
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [removing, setRemoving] = useState(null);
  useEffect(() => { platformApi.admins().then((r) => setList(r.admins)).catch((e) => setError(e.message)); }, []);
  const add = async (e) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try { setList((await platformApi.addAdmin(email.trim())).admins); setEmail(''); } catch (err) { setError(err.message); }
    setBusy(false);
  };
  return (
    <section className="block" aria-labelledby="adm-h">
      <div className="block-head"><h2 id="adm-h">Platform admins</h2></div>
      <p className="block-pad small muted plat-admin-intro">Platform admins see this page: they approve new workspaces, set plans and limits, and turn off or delete workspaces.
        Add someone by email, even before they sign up. The first admin is set on the server (NOWBUILDER_PLATFORM_ADMINS), so you can never lock yourself out.</p>
      <form className="plat-add" onSubmit={add}>
        <label className="sr-only" htmlFor="adm-email">Email</label>
        <input id="adm-email" className="input" type="email" required placeholder="name@company.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        <button className="btn btn-primary" disabled={busy || !email.trim()}>{busy ? 'Adding…' : 'Add admin'}</button>
      </form>
      {error && <div className="alert alert-error small block-alert" role="alert">{error}</div>}
      {!list ? <p className="block-pad muted">Loading…</p> : (
        <ul className="plat-list">
          {list.map((a) => (
            <li key={a.email} className="plat-row plat-admin-row">
              <div className="plat-who">
                <p className="plat-name"><strong>{a.name || a.email}</strong>{a.is_me && <span className="badge badge-info">You</span>}
                  {!a.signed_up && <span className="badge badge-neutral">Not signed up yet</span>}</p>
                <p className="small muted">{a.name ? a.email : ''}</p>
              </div>
              <p className="small muted plat-admin-src">{a.source === 'server' ? 'Set on the server' : `Added by ${a.added_by} ${ago(a.added_at)}`}</p>
              <div className="plat-actions">
                {a.source === 'app' && !a.is_me && <button type="button" className="btn btn-sm" onClick={() => setRemoving(a)}>Remove</button>}
              </div>
            </li>
          ))}
        </ul>
      )}
      {removing && (
        <ConfirmDialog title={`Remove ${removing.name || removing.email}?`} confirmLabel="Remove admin" danger onCancel={() => setRemoving(null)}
          onConfirm={async () => { setList((await platformApi.removeAdmin(removing.email)).admins); setRemoving(null); }}>
          <p>{removing.name || removing.email} won't see the Platform page any more. Their own workspace and account stay as they are.</p>
        </ConfirmDialog>
      )}
    </section>
  );
}

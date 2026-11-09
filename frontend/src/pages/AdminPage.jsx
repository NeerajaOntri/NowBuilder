import { useCallback, useEffect, useState } from 'react';
import { ConfirmDialog } from '../components/Dialog';
import { Icon } from '../components/Icon';
import { useWorkspace } from '../instances';
import {
  PERMISSION_LABEL, ROLE_INFO, ROLE_LABEL, wsApi } from '../workspaceApi';

const ASSIGNABLE = ['admin', 'developer', 'reviewer', 'viewer'];

function initials(name) {
  return name.split(/\s+/).map((p) => p[0] ?? '').join('').slice(0, 2).toUpperCase() || '?';
}

function daysLeft(iso) {
  const d = Math.ceil((new Date(iso).getTime() - Date.now()) / 86400000);
  return d <= 0 ? 'Expired' : d === 1 ? 'Expires tomorrow' : `Expires in ${d} days`;
}

function CopyLink({ link, email, emailed }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(link); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { /* select instead */ }
  };
  return (
    <div className="invite-link" role="status">
      <p><Icon name="check" /> {emailed
        ? <><strong>Invite sent to {email}.</strong> You can also copy the link and send it yourself. It works once, only for that email address, and expires in 7 days.</>
        : <><strong>Invite ready.</strong> Send this link to {email}. It works once, only for that email address, and expires in 7 days.</>}</p>
      <div className="invite-link-row">
        <input className="input" readOnly value={link} aria-label="Invite link" onFocus={(e) => e.currentTarget.select()} />
        <button type="button" className="btn btn-primary" onClick={copy}><Icon name={copied ? 'check' : 'link'} /> {copied ? 'Copied' : 'Copy link'}</button>
      </div>
    </div>
  );
}

function OrgAccess({ orgs, value, onChange, disabled }

) {
  const all = value === null;
  return (
    <fieldset className="org-access" disabled={disabled}>
      <legend className="sr-only">Instance access</legend>
      <label className="radio"><input type="radio" checked={all} onChange={() => onChange(null)} /> All instances, including ones connected later</label>
      <label className="radio"><input type="radio" checked={!all} onChange={() => onChange(orgs.map((o) => o.id))} /> Only these instances</label>
      {!all && (
        <div className="org-checks">
          {orgs.length === 0 && <p className="small muted">No instances connected yet.</p>}
          {orgs.map((o) => (
            <label key={o.id} className="check">
              <input type="checkbox" checked={value.includes(o.id)}
                onChange={(e) => onChange(e.target.checked ? [...value, o.id] : value.filter((x) => x !== o.id))} />
              {o.name} <span className={`badge ${o.instance_type === 'Production' ? 'badge-prod' : 'badge-neutral'}`}>{o.instance_type}</span>
            </label>
          ))}
        </div>
      )}
    </fieldset>
  );
}

function InviteForm({ data, myRole, onDone, onCancel }) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('developer');
  const [orgIds, setOrgIds] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const roles = ASSIGNABLE.filter((r) => r !== 'admin' || myRole === 'owner');
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const r = await wsApi.invite(email.trim(), role, roles.includes('admin') && role === 'admin' ? null : orgIds);
      onDone(r.link, r.invite.email, r.emailed);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  return (
    <form className="invite-form" onSubmit={submit}>
      <h3>Invite a member</h3>
      {error && <div className="alert alert-error small" role="alert">{error}</div>}
      <div className="invite-grid">
        <div className="field">
          <label htmlFor="inv-email">Email</label>
          <input id="inv-email" className="input" type="email" required autoFocus value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" />
        </div>
        <div className="field">
          <label htmlFor="inv-role">Role</label>
          <select id="inv-role" className="input" value={role} onChange={(e) => setRole(e.target.value)}>
            {roles.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
          </select>
        </div>
      </div>
      <p className="small muted role-hint">{ROLE_INFO[role]}</p>
      {role !== 'admin' && (
        <div className="field">
          <span className="label">Which instances can they use?</span>
          <OrgAccess orgs={data.instances} value={orgIds} onChange={setOrgIds} />
        </div>
      )}
      <div className="form-actions">
        <button type="button" className="btn" onClick={onCancel}>Cancel</button>
        <button className="btn btn-primary" disabled={busy || !email.trim() || (orgIds !== null && orgIds.length === 0)}>{busy ? 'Sending…' : 'Send invite'}</button>
      </div>
    </form>
  );
}

function MemberRow({ m, data, editable, onChanged, onRemove }

) {
  const [editingOrgs, setEditingOrgs] = useState(false);
  const [orgIds, setOrgIds] = useState(m.instance_ids);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const names = (ids) => ids.map((id) => data.instances.find((o) => o.id === id)?.name).filter(Boolean).join(', ');
  const fullAccess = m.role === 'owner' || m.role === 'admin';
  const run = async (fn) => {
    setBusy(true); setError(null);
    try { await fn(); onChanged(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  return (
    <li className={`member${m.status === 'disabled' ? ' is-off' : ''}`}>
      <span className="avatar" aria-hidden="true">{initials(m.name)}</span>
      <div className="member-main">
        <strong>{m.name}{m.is_me && <span className="muted small"> (you)</span>}</strong>
        <span className="small muted member-email">{m.email}</span>
        <span className="small member-orgs">
          <Icon name="cloud" /> {fullAccess ? 'All instances' : m.instance_ids === null ? 'All instances' : m.instance_ids.length ? names(m.instance_ids) : 'No instances'}
          {editable.role && !fullAccess && !editingOrgs && <button type="button" className="link-btn" onClick={() => { setOrgIds(m.instance_ids); setEditingOrgs(true); }}>Change</button>}
        </span>
        {m.status === 'disabled' && <span className="badge badge-warn">Access turned off</span>}
        {editingOrgs && (
          <div className="member-orgs-edit">
            <OrgAccess orgs={data.instances} value={orgIds} onChange={setOrgIds} disabled={busy} />
            <div className="form-actions">
              <button type="button" className="btn btn-sm" disabled={busy} onClick={() => setEditingOrgs(false)}>Cancel</button>
              <button type="button" className="btn btn-sm btn-primary" disabled={busy || (orgIds !== null && orgIds.length === 0)}
                onClick={() => run(async () => { await wsApi.update(m.id, orgIds === null ? { all_instances: true } : { instance_ids: orgIds }); setEditingOrgs(false); })}>Save access</button>
            </div>
          </div>
        )}
        {error && <div className="alert alert-error small" role="alert">{error}</div>}
      </div>
      <div className="member-role">
        {editable.role ? (
          <select className="input input-sm" aria-label={`Role for ${m.name}`} value={m.role} disabled={busy}
            onChange={(e) => run(() => wsApi.update(m.id, { role: e.target.value  }))}>
            {editable.roles.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
          </select>
        ) : <span className={`badge ${m.role === 'owner' ? 'badge-accent' : 'badge-neutral'}`}>{ROLE_LABEL[m.role]}</span>}
      </div>
      <div className="member-actions">
        {editable.role && (
          <>
            <button type="button" className="btn btn-sm" disabled={busy}
              onClick={() => run(() => wsApi.update(m.id, { status: m.status === 'disabled' ? 'active' : 'disabled' }))}>
              {m.status === 'disabled' ? 'Turn on access' : 'Turn off access'}
            </button>
            <button type="button" className="btn btn-sm btn-danger" disabled={busy} onClick={() => onRemove(m)}>Remove</button>
          </>
        )}
      </div>
    </li>
  );
}

function InviteRowView({ inv, canManage, onChanged, onLink }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const run = async (fn) => {
    setBusy(true); setError(null);
    try { await fn(); onChanged(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  return (
    <li className="member is-invite">
      <span className="avatar avatar-pending" aria-hidden="true"><Icon name="clock" /></span>
      <div className="member-main">
        <strong>{inv.email}</strong>
        <span className="small muted">Invited by {inv.invited_by}. {inv.status === 'expired' ? 'Expired' : daysLeft(inv.expires_at)}.</span>
        {error && <div className="alert alert-error small" role="alert">{error}</div>}
      </div>
      <div className="member-role"><span className="badge badge-neutral">{ROLE_LABEL[inv.role]}</span></div>
      <div className="member-actions">
        {canManage && (
          <>
            <button type="button" className="btn btn-sm" disabled={busy} onClick={() => run(async () => { const r = await wsApi.renew(inv.id); onLink(r.link, inv.email, r.emailed); })}>New link</button>
            <button type="button" className="btn btn-sm btn-danger" disabled={busy} onClick={() => run(() => wsApi.revoke(inv.id))}>Revoke</button>
          </>
        )}
      </div>
    </li>
  );
}

function Seats({ data }) {
  const { members, instances: orgs } = data.limits;
  const used = members.active + members.pending;
  return (
    <section className="seats" aria-label="Workspace limits">
      <div className={`seat${used >= members.max ? ' full' : ''}`}>
        <span className="seat-label">Members</span>
        <strong>{used} of {members.max}</strong>
        {members.max <= 12 && <span className="seat-dots" aria-hidden="true">{Array.from({ length: members.max }, (_, i) => <span key={i} className={i < members.active ? 'on' : i < used ? 'pending' : ''} />)}</span>}
        <span className="small muted">{members.pending ? `${members.active} active, ${members.pending} invited` : `${members.active} active`}</span>
      </div>
      <div className={`seat${orgs.used >= orgs.max ? ' full' : ''}`}>
        <span className="seat-label">ServiceNow instances</span>
        <strong>{orgs.used} of {orgs.max}</strong>
        {orgs.max <= 12 && <span className="seat-dots" aria-hidden="true">{Array.from({ length: orgs.max }, (_, i) => <span key={i} className={i < orgs.used ? 'on' : ''} />)}</span>}
        <span className="small muted">{data.instances.map((o) => o.name).join(', ') || 'None connected'}</span>
      </div>
      {data.limits.plan && (
        <div className="seat seat-plan">
          <span className="seat-label">Plan</span>
          <strong>{data.limits.plan}</strong>
          <span className="small muted">Need more instances or members? Ask the nowBuilder team to change your plan.</span>
        </div>
      )}
    </section>
  );
}

function Roles() {
  const { ws } = useWorkspace();
  const [role, setRole] = useState(ws?.me.role ?? 'developer');
  const perms = ws?.roles.find((r) => r.id === role)?.permissions ?? [];
  return (
    <section className="block" aria-label="Roles">
      <div className="block-head"><h2>What each role can do</h2><span className="small muted">You are {ws ? ROLE_LABEL[ws.me.role] : ''}</span></div>
      <div className="role-pick" role="radiogroup" aria-label="Role">
        {(['owner', ...ASSIGNABLE]).map((r) => (
          <button key={r} type="button" role="radio" aria-checked={role === r} className={`role-chip${role === r ? ' on' : ''}`} onClick={() => setRole(r)}>{ROLE_LABEL[r]}</button>
        ))}
      </div>
      <p className="role-desc">{ROLE_INFO[role]}</p>
      <ul className="abilities">
        {PERMISSION_LABEL.map(([p, label]) => {
          const yes = perms.includes(p);
          return <li key={p} className={yes ? 'yes' : 'no'}><span className="ab-mark" aria-hidden="true">{yes ? <Icon name="check" size={13} /> : '–'}</span>{label}<span className="sr-only">{yes ? ': allowed' : ': not allowed'}</span></li>;
        })}
      </ul>
    </section>
  );
}

export function AdminPage() {
  const { ws, can, refresh } = useWorkspace();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState('members');
  const [inviting, setInviting] = useState(false);
  const [link, setLink] = useState(null);
  const [removing, setRemoving] = useState(null);
  const [renaming, setRenaming] = useState(null);
  const manage = can('manage_members');

  const load = useCallback(() => wsApi.members().then((d) => { setData(d); setError(null); }).catch((e) => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);
  const changed = () => { load(); refresh().catch(() => {}); };

  if (!ws) return <div className="page-loading" role="status">Loading…</div>;
  const myRole = ws.me.role;
  const seatsFull = data ? data.limits.members.active + data.limits.members.pending >= data.limits.members.max : false;
  const editableFor = (m) => {
    const ok = manage && !m.is_me && m.role !== 'owner' && (m.role !== 'admin' || myRole === 'owner');
    return { role: ok, roles: ASSIGNABLE.filter((r) => r !== 'admin' || myRole === 'owner') };
  };

  return (
    <div className="section-page">
      <header className="sec-head">
        <span className="sec-ico tone-blue"><Icon name="team" size={22} /></span>
        <div className="sec-head-main">
          {renaming === null ? (
            <h1>{ws.workspace.name} {manage && <button type="button" className="link-btn small" onClick={() => setRenaming(ws.workspace.name)}>Rename</button>}</h1>
          ) : (
            <form className="rename" onSubmit={async (e) => { e.preventDefault(); await wsApi.rename(renaming); setRenaming(null); changed(); }}>
              <input className="input" aria-label="Workspace name" value={renaming} maxLength={80} autoFocus onChange={(e) => setRenaming(e.target.value)} />
              <button className="btn btn-sm btn-primary" disabled={!renaming.trim()}>Save</button>
              <button type="button" className="btn btn-sm" onClick={() => setRenaming(null)}>Cancel</button>
            </form>
          )}
          <p>Members and access. Everyone here shares the workspace's ServiceNow instances, AI provider, Jira, GitHub and chats; their role decides what they can do.
            {!manage && ' Only workspace admins can make changes.'}</p>
        </div>
      </header>

      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {data && <Seats data={data} />}

      <div className="tabs" role="tablist" aria-label="Admin">
        <button type="button" role="tab" aria-selected={tab === 'members'} className={`tab${tab === 'members' ? ' on' : ''}`} onClick={() => setTab('members')}><Icon name="team" /> Members</button>
        <button type="button" role="tab" aria-selected={tab === 'roles'} className={`tab${tab === 'roles' ? ' on' : ''}`} onClick={() => setTab('roles')}><Icon name="shield" /> Roles</button>
      </div>

      {tab === 'roles' ? <Roles /> : !data ? <p className="muted">Loading…</p> : (
        <section className="block" aria-labelledby="mem-h">
          <div className="block-head">
            <h2 id="mem-h">Members <span className="muted">{data.members.length}</span></h2>
            {manage && !inviting && (
              <button type="button" className="btn btn-sm btn-primary" disabled={seatsFull}
                title={seatsFull ? `The workspace is full (${data.limits.members.max} members including invites). Remove a member or revoke an invite first.` : undefined}
                onClick={() => { setInviting(true); setLink(null); }}><Icon name="plus" /> Invite member</button>
            )}
          </div>
          {seatsFull && manage && !inviting && <p className="block-note small">The workspace is full: {data.limits.members.max} members including pending invites. Remove a member or revoke an invite to add someone.</p>}
          {inviting && <InviteForm data={data} myRole={myRole} onCancel={() => setInviting(false)} onDone={(l, email, emailed) => { setInviting(false); setLink({ link: l, email, emailed }); changed(); }} />}
          {link && <CopyLink link={link.link} email={link.email} emailed={link.emailed} />}
          <ul className="member-list v2">
            {data.members.map((m) => <MemberRow key={m.id} m={m} data={data} editable={editableFor(m)} onChanged={changed} onRemove={setRemoving} />)}
            {data.invites.map((inv) => <InviteRowView key={inv.id} inv={inv} canManage={manage} onChanged={changed} onLink={(l, email, emailed) => setLink({ link: l, email, emailed })} />)}
          </ul>
        </section>
      )}

      {removing && (
        <ConfirmDialog title={`Remove ${removing.name}?`} confirmLabel="Remove" danger onCancel={() => setRemoving(null)}
          onConfirm={async () => { await wsApi.remove(removing.id); setRemoving(null); changed(); }}>
          <p>{removing.name} loses access to this workspace straight away. Their chats and plans stay here. You can invite them again later.</p>
        </ConfirmDialog>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { platformApi } from '../platformApi';
import { useAuth } from '../auth';
import { WorkspaceProvider, useWorkspace } from '../instances';
import { Icon } from './Icon';
import { Wordmark } from './Wordmark';

export const NAV = [
  { to: '/', end: true, icon: 'home', label: 'Home' },
  { to: '/workspace', icon: 'sparkle', label: 'AI workspace' },
  { to: '/admin', icon: 'team', label: 'Admin' },
];

/** Closes a popover on outside click or Escape. */
function useDismiss(open, close, ref) {
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !ref.current?.contains(e.target)) close();
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('keydown', handler);
    return () => { document.removeEventListener('mousedown', handler); document.removeEventListener('keydown', handler); };
  }, [open, close, ref]);
}

function Popover({ label, trigger, children, className = '' }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const close = () => setOpen(false);
  useDismiss(open, close, ref);
  useEffect(close, [useLocation().pathname]);
  return (
    <div className={`menu ${className}`} ref={ref}>
      <button type="button" className="menu-trigger" aria-haspopup="menu" aria-expanded={open} aria-label={label} onClick={() => setOpen(!open)}>{trigger(open)}</button>
      {open && <div className="menu-pop" role="menu">{children(close)}</div>}
    </div>
  );
}

function InstanceSwitcher() {
  const { selected, instances, refresh, can, ws } = useWorkspace();
  const room = can('manage_instances') && Boolean(ws && ws.limits.instances.used < ws.limits.instances.max);
  const [busy, setBusy] = useState(null);
  if (!instances) return null;
  if (!selected) return can('manage_instances') ? <Link to="/settings/instances" className="btn btn-sm btn-primary"><Icon name="plus" /> Connect an instance</Link> : null;
  const prod = selected.instance_type === 'Production';
  const use = async (id, close) => {
    setBusy(id);
    try { await api(`/api/instances/${id}/select`, { method: 'POST' }); await refresh(); close(); } finally { setBusy(null); }
  };
  return (
    <Popover label={`Selected instance ${selected.name}, switch instance`} className="org-switch"
      trigger={() => (
        <span className={`org-btn${prod ? ' is-prod' : ''}`}>
          <span className="org-ico"><Icon name="cloud" /><span className={`org-status ${selected.status === 'connected' ? 'ok' : 'bad'}`} /></span>
          <span className="org-txt"><strong>{selected.name}</strong><span className={prod ? 'prod-word' : ''}>{selected.instance_type}</span></span>
          <Icon name="chevron" />
        </span>
      )}>
      {(close) => (
        <>
          <p className="menu-label">Work in</p>
          {instances.map((o) => (
            <button key={o.id} role="menuitemradio" aria-checked={o.is_selected} className={`org-opt${o.is_selected ? ' on' : ''}`}
              disabled={busy !== null} onClick={() => (o.is_selected ? close() : use(o.id, close))}>
              <span className={`org-status ${o.status === 'connected' ? 'ok' : 'bad'}`} />
              <span className="org-opt-txt"><strong>{o.name}</strong><span>{o.instance_type}{o.status !== 'connected' ? ', needs attention' : ''}</span></span>
              {o.is_selected ? <Icon name="check" /> : busy === o.id ? <span className="spin" aria-label="Switching" /> : null}
            </button>
          ))}
          <div className="menu-sep" />
          <Link role="menuitem" to="/settings/instances" className="menu-link"><Icon name="gear" /> Manage instances</Link>
          {room && <Link role="menuitem" to="/settings/instances" className="menu-link"><Icon name="plus" /> Connect another instance</Link>}
        </>
      )}
    </Popover>
  );
}

function UserMenu() {
  const { user, signOut } = useAuth();
  const { ws } = useWorkspace();
  const navigate = useNavigate();
  if (!user) return null;
  const initials = `${user.first_name[0] ?? ''}${user.last_name[0] ?? ''}`.toUpperCase();
  return (
    <Popover label="Account menu" className="user-menu"
      trigger={() => (
        <span className="user-btn">
          <span className="avatar">{initials}</span>
          <span className="user-txt"><strong>{user.first_name} {user.last_name}</strong><span>{ws?.me.role_label ?? ''}</span></span>
          <Icon name="chevron" />
        </span>
      )}>
      {() => (
        <>
          <div className="who"><strong>{user.first_name} {user.last_name}</strong><div className="muted">{user.email}</div>
            {ws && <div className="muted small">{ws.me.role_label} in {ws.workspace.name}</div>}</div>
          <Link role="menuitem" to="/settings/instances" className="menu-link"><Icon name="cloud" /> ServiceNow instances</Link>
          <Link role="menuitem" to="/settings/ai-provider" className="menu-link"><Icon name="key" /> AI provider</Link>
          <Link role="menuitem" to="/settings/jira" className="menu-link"><Icon name="ticket" /> Jira</Link>
          <Link role="menuitem" to="/settings/github" className="menu-link"><Icon name="branch" /> GitHub</Link>
          <Link role="menuitem" to="/admin" className="menu-link"><Icon name="team" /> Members and access</Link>
          <div className="menu-sep" />
          <button role="menuitem" className="menu-link" onClick={() => { signOut(); navigate('/signin'); }}><Icon name="login" /> Sign out</button>
        </>
      )}
    </Popover>
  );
}

function Blocked({ children }) {
  const { blocked, blockedCode } = useWorkspace();
  const { signOut, user } = useAuth();
  const path = useLocation().pathname;
  if (!blocked || (path === '/platform' && user?.is_platform_admin)) return <>{children}</>;
  const pending = blockedCode === 'pending';
  return (
    <main className="main"><div className="container">
      <section className={`blocked${pending ? ' blocked-wait' : ''}`} role={pending ? 'status' : 'alert'}>
        <Icon name={pending ? 'clock' : 'lock'} size={28} />
        <h1>{pending ? 'Your workspace is waiting for approval' : blockedCode === 'suspended' ? 'nowBuilder is turned off for this workspace' : 'No access right now'}</h1>
        <p>{blocked}</p>
        {user && <p className="small muted">Signed in as {user.email}</p>}
        <div className="blocked-actions">
          {pending && <button type="button" className="btn btn-primary" onClick={() => window.location.reload()}>Check again</button>}
          <button type="button" className="btn" onClick={signOut}>Sign out</button>
        </div>
      </section>
    </div></main>
  );
}

/** Main navigation; hidden while the workspace can't be used (waiting for approval, turned off). */
function TopNav() {
  const { blocked } = useWorkspace();
  const { user } = useAuth();
  const path = useLocation().pathname;
  const [waiting, setWaiting] = useState(0);
  const admin = Boolean(user?.is_platform_admin);
  useEffect(() => {  // platform admins: how many new workspaces wait for approval (on each page change and after changes on Platform)
    if (!admin) return;
    const check = () => { platformApi.summary().then((r) => setWaiting(r.pending)).catch(() => {}); };
    check();
    window.addEventListener('platform-changed', check);
    return () => window.removeEventListener('platform-changed', check);
  }, [admin, path]);
  if (blocked) return <div className="topnav" />;
  return (
    <nav className="topnav" aria-label="Main">
      {NAV.map((n) => (
        <NavLink key={n.to} to={n.to} end={n.end}><Icon name={n.icon} /><span>{n.label}</span></NavLink>
      ))}
      {admin && (
        <NavLink to="/platform" aria-label={waiting ? `Platform, ${waiting} waiting for approval` : 'Platform'}>
          <Icon name="shield" /><span>Platform</span>{waiting > 0 && <span className="nav-count">{waiting}</span>}
        </NavLink>
      )}
    </nav>
  );
}

export function AppShell() {
  const path = useLocation().pathname;
  const fullBleed = path.startsWith('/workspace') && path !== '/workspace/stories';  // the chat fills the screen; the stories list is a normal page
  return (
    <WorkspaceProvider>
      <div className="shell">
        <header className="topbar">
          <Wordmark />
          <TopNav />
          <div className="topbar-right">
            <InstanceSwitcher />
            <UserMenu />
          </div>
        </header>
        <Blocked>
          {fullBleed
            ? <main className="main-full"><Outlet /></main>
            : <main className="main"><div className="container"><Outlet /></div></main>}
        </Blocked>
      </div>
    </WorkspaceProvider>
  );
}

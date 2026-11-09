import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import { chatApi } from '../chatApi';
import { Icon } from '../components/Icon';
import { ago } from '../time';
import { useWorkspace } from '../instances';

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

const IDEAS = [
  { icon: 'rule', text: 'Write a before business rule on incident that sets priority 1 for VIP callers' },
  { icon: 'code', text: 'Create a script include with a GlideAjax method that returns the caller’s manager' },
  { icon: 'field', text: 'Make category mandatory on incident when the state is Resolved, without a script' },
  { icon: 'db', text: 'Which business rules and client scripts already run on change_request?' },
];

const TOOLS = [
  { to: '/workspace', icon: 'sparkle', title: 'AI workspace', body: 'Ask about your instance, or describe a business rule, script include, client script, UI policy or UI action.', cta: 'Start building', tone: 'primary' },
  { to: '/workspace/stories', icon: 'ticket', title: 'Build from a Jira story', body: 'Pick a story and nowBuilder designs the scripts and configuration it needs.', cta: 'Open stories', tone: 'blue' },
  { to: '/settings/instances', icon: 'cloud', title: 'ServiceNow instances', body: 'Connect dev, test and production instances. Each member chooses the one they work in.', cta: 'Manage instances', tone: 'green' },
  { to: '/admin', icon: 'team', title: 'Members and access', body: 'Invite your team and decide who can build, approve and deploy.', cta: 'Open admin', tone: 'violet' },
];

function Setup() {
  const { ai, selected, can } = useWorkspace();
  const admin = can('manage_instances');
  const instDone = Boolean(selected && selected.status === 'connected');
  const aiDone = Boolean(ai?.verified);
  const steps = [
    {
      done: instDone, title: 'Connect a ServiceNow instance',
      body: instDone ? `Connected to ${selected.name} (${selected.instance_type}).` : admin ? 'nowBuilder reads your tables and existing scripts so what it builds fits your instance.' : 'Ask a workspace admin to connect an instance or give you access to one.',
      action: admin ? <Link className={`btn btn-sm${instDone ? '' : ' btn-primary'}`} to="/settings/instances">{instDone ? 'Manage instances' : 'Connect instance'}</Link> : <span className="badge badge-neutral">{instDone ? 'Ready' : 'Waiting for an admin'}</span>,
    },
    {
      done: aiDone, title: 'Add your AI provider',
      body: aiDone ? `Using ${ai.model}.` : ai ? (ai.status_message ?? 'Verification failed.') : admin ? 'nowBuilder uses the workspace\'s own API key.' : 'Ask a workspace admin to add the AI provider.',
      action: admin ? <Link className={`btn btn-sm${aiDone || !instDone ? '' : ' btn-primary'}`} to="/settings/ai-provider">{aiDone ? 'Change' : 'Add provider'}</Link> : <span className="badge badge-neutral">{aiDone ? 'Ready' : 'Waiting for an admin'}</span>,
    },
    {
      done: false, locked: !aiDone || !instDone, title: 'Ask your first question',
      body: instDone && aiDone ? 'Ask about your instance or describe what to build.' : 'Available once your instance and AI provider are set up.',
      action: aiDone && instDone ? <Link className="btn btn-sm btn-primary" to="/workspace">Open workspace</Link> : <span className="badge badge-neutral">Not ready</span>,
    },
  ];
  return (
    <ol className="setup" aria-label="Setup" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
      {steps.map((s, i) => (
        <li key={s.title} className={`setup-step${s.done ? ' done' : ''}${s.locked ? ' locked' : ''}`}>
          <span className="step-num" aria-hidden="true">{s.done ? '✓' : i + 1}</span>
          <div><h3>{s.title}<span className="sr-only">{s.done ? ' (done)' : ''}</span></h3><p>{s.body}</p></div>
          {s.action}
        </li>
      ))}
    </ol>
  );
}

function EnvBar({ lastAt }) {
  const { selected, can, ws } = useWorkspace();
  const room = can('manage_instances') && Boolean(ws && ws.limits.instances.used < ws.limits.instances.max);
  const o = selected;
  const prod = o.instance_type === 'Production';
  return (
    <section className={`env-bar${prod ? ' is-prod' : ''}`} aria-label="Selected instance">
      <span className="env-ico"><Icon name="cloud" size={22} /></span>
      <div className="env-main">
        <p className="env-label">Selected instance</p>
        <p className="env-name"><strong>{o.name}</strong>
          {o.status === 'connected' ? <span className="badge badge-ok"><span className="dot" aria-hidden="true" />Connected</span> : <span className="badge badge-err">Needs attention</span>}
          <span className={`badge ${prod ? 'badge-prod' : 'badge-neutral'}`}>{o.instance_type}</span>
          {o.release && <span className="badge badge-neutral">{o.release}</span>}
        </p>
        <p className="env-user small muted">{o.url}, signed in as {o.user_display_name ?? o.username}</p>
      </div>
      <div className="env-last"><Icon name="clock" /><span><span className="env-label">Last chat</span><strong>{lastAt ? ago(lastAt) : 'No chats yet'}</strong></span></div>
      <div className="env-actions">
        <Link className="btn btn-sm" to="/settings/instances">Manage instances</Link>
        {room && <Link className="btn btn-sm" to="/settings/instances"><Icon name="plus" /> Connect another</Link>}
      </div>
    </section>
  );
}

function RecentChats({ chats }) {
  return (
    <section className="block" aria-labelledby="recent-h">
      <div className="block-head"><h2 id="recent-h">Recent chats</h2><Link to="/workspace" className="small">All chats</Link></div>
      {chats === null ? <p className="muted small block-pad">Loading…</p>
        : chats.length === 0 ? <p className="muted small block-pad">No chats yet. Ask a question or start from an idea below.</p>
          : (
            <ul className="recent-chats">
              {chats.slice(0, 6).map((c) => (
                <li key={c.id}>
                  <Link to={`/workspace/${c.id}`}><Icon name={c.jira ? 'ticket' : 'sparkle'} /><span className="rc-title">{c.title}</span>
                    <span className="small muted">{c.by ? `${c.by}, ` : ''}{ago(c.updated_at)}</span></Link>
                </li>
              ))}
            </ul>
          )}
    </section>
  );
}

function Tools() {
  return (
    <section className="block tools-block" aria-labelledby="tools-h">
      <div className="block-head"><h2 id="tools-h">What would you like to do?</h2></div>
      <ul className="tools">
        {TOOLS.map((t) => (
          <li key={t.to}>
            <Link to={t.to} className={`tool tone-${t.tone}`}>
              <span className="tool-ico"><Icon name={t.icon} size={20} /></span>
              <span className="tool-title">{t.title}</span>
              <span className="tool-body">{t.body}</span>
              <span className="tool-cta">{t.cta}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function HomePage() {
  const { user } = useAuth();
  const { instances, ai, selected } = useWorkspace();
  const [chats, setChats] = useState(null);
  const ready = Boolean(selected && selected.status === 'connected' && ai?.verified);

  useEffect(() => {
    if (!ready) return;
    chatApi.list().then(setChats).catch(() => setChats([]));
  }, [ready, selected?.id]);

  if (!instances || ai === undefined) return <div className="page-loading" role="status">Loading…</div>;

  const hero = (
    <div className="hero-copy">
      <p className="hero-chip"><Icon name="sparkle" /> ServiceNow development, designed and checked by AI</p>
      <h1 className="home-hello">{greeting()}, {user?.first_name}<span className="hero-dot">.</span></h1>
      <p className="home-lead">{ready
        ? `Ask about ${selected.name} or describe what you need. nowBuilder reads your tables and existing scripts first, designs it the ServiceNow way, checks it, and deploys it into the instance.`
        : 'Two quick steps and nowBuilder can read your ServiceNow instance and build with you.'}</p>
      {ready && (
        <div className="hero-actions">
          <Link className="btn btn-primary btn-lg" to="/workspace"><Icon name="sparkle" /> Open AI workspace</Link>
          <Link className="btn btn-lg" to="/workspace/stories">Jira stories</Link>
        </div>
      )}
      {ready && <p className="hero-safe small"><Icon name="shield" /> Nothing reaches your instance until you choose the rows on the plan card and click Approve, then Deploy.</p>}
    </div>
  );

  if (!ready) {
    return (
      <div className="home">
        <header className="hero hero-setup">{hero}</header>
        <Setup />
      </div>
    );
  }

  return (
    <div className="home">
      <header className="hero">{hero}</header>
      <EnvBar lastAt={chats?.[0]?.updated_at} />
      <div className="home-grid">
        <div className="home-main"><Tools /></div>
        <aside className="home-side"><RecentChats chats={chats} /></aside>
      </div>
      <section className="ideas" aria-labelledby="ideas-h">
        <div><h2 id="ideas-h">Start from an idea</h2><p className="small muted">Opens the AI workspace with the idea filled in.</p></div>
        <ul>
          {IDEAS.map((i) => (
            <li key={i.text}><Link to={`/workspace?idea=${encodeURIComponent(i.text)}`}><Icon name={i.icon} /><span>{i.text}</span></Link></li>
          ))}
        </ul>
      </section>
    </div>
  );
}

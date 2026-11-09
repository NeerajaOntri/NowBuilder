import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Icon } from '../components/Icon';
import { jiraApi } from '../integrationsApi';
import { useWorkspace } from '../instances';

const CAT = { new: 'st-new', indeterminate: 'st-progress', done: 'st-done' };

function ago(iso) {
  if (!iso) return '';
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (m < 60) return `${Math.max(m, 1)} min ago`;
  if (m < 1440) return `${Math.round(m / 60)} h ago`;
  const d = Math.round(m / 1440);
  return d === 1 ? 'yesterday' : `${d} days ago`;
}

function Details({ k }) {
  const [d, setD] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => { jiraApi.story(k).then(setD).catch((e) => setError(e.message)); }, [k]);
  if (error) return <div className="alert alert-error small">{error}</div>;
  if (!d) return <p className="muted small" role="status"><span className="spinner" aria-hidden="true" /> Loading the story…</p>;
  return (
    <div className="story-details">
      <h4>Description</h4>
      {d.description ? <div className="story-text">{d.description}</div> : <p className="muted small">No description.</p>}
      {d.acceptance && (<><h4>Acceptance criteria</h4><div className="story-text">{d.acceptance}</div></>)}
      {d.subtasks.length > 0 && (<><h4>Sub-tasks</h4><ul className="story-list">{d.subtasks.map((t) => <li key={t.key}><span className="mono">{t.key}</span> {t.summary}</li>)}</ul></>)}
      {d.attachments.length > 0 && (
        <>
          <h4>Attachments</h4>
          <ul className="story-list">
            {d.attachments.map((a) => (
              <li key={a.name}>{a.name}{' '}
                {a.readable ? <span className="badge badge-ok">Read by nowBuilder</span> : <span className="badge badge-neutral" title="nowBuilder reads .docx, .pdf, .txt and .md files up to 5 MB">Not read</span>}
              </li>
            ))}
          </ul>
        </>
      )}
      {(d.labels.length > 0 || d.components.length > 0) && <p className="small muted">Labels and components: {[...d.components, ...d.labels].join(', ')}</p>}
    </div>
  );
}

function StoryCard({ s, canBuild, building, onBuild, onOpen }

) {
  const [open, setOpen] = useState(false);
  return (
    <li className={`story-card${open ? ' open' : ''}`}>
      <div className="story-main">
        <div className="story-top">
          <a className="story-key" href={s.url} target="_blank" rel="noreferrer" title="Open in Jira">{s.key}</a>
          <span className={`story-chip ${CAT[s.status_category] ?? 'st-new'}`}>{s.status}</span>
          {s.priority && <span className="story-chip">{s.priority}</span>}
          {s.type && <span className="story-chip">{s.type}</span>}
          {s.updated && <span className="story-when muted small">Updated {ago(s.updated)}</span>}
        </div>
        <h3 className="story-title">{s.summary}</h3>
        {!open && s.description && <p className="story-desc">{s.description}</p>}
        {open && <Details k={s.key} />}
        <button type="button" className="link-btn small story-more" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? 'Show less' : 'Show the full story'}
        </button>
      </div>
      <div className="story-actions">
        {s.chat_id ? (
          <>
            <button type="button" className="btn btn-primary" onClick={onOpen}><Icon name="sparkle" /> Open chat</button>
            {canBuild && <button type="button" className="link-btn small" onClick={onBuild} disabled={building}>Build again</button>}
          </>
        ) : (
          <button type="button" className="btn btn-primary story-build" onClick={onBuild} disabled={!canBuild || building}
            title={canBuild ? `Plan and build ${s.key} in the AI workspace` : 'Your role can’t build'}>
            {building ? <span className="spinner" aria-hidden="true" /> : <Icon name="code" />} {building ? 'Starting…' : 'Build'}
          </button>
        )}
      </div>
    </li>
  );
}

export function StoriesPage() {
  const navigate = useNavigate();
  const { selected, ai, can } = useWorkspace();
  const [scope, setScope] = useState(() => (localStorageGet('mf.stories.scope') === 'all' ? 'all' : 'mine'));
  const [openOnly, setOpenOnly] = useState(() => localStorageGet('mf.stories.open') !== 'false');
  const [q, setQ] = useState('');
  const [query, setQuery] = useState('');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [building, setBuilding] = useState(null);
  const seq = useRef(0);
  const canBuild = can('build') && Boolean(ai?.verified);

  const load = useCallback(() => {
    const n = ++seq.current;
    setLoading(true);
    jiraApi.stories(scope, openOnly, query)
      .then((d) => { if (n === seq.current) { setData(d); setError(null); } })
      .catch((e) => { if (n === seq.current) { const t = e.message; setError({ text: t, notConnected: t.includes('isn’t connected') || t.includes("isn't connected") }); } })
      .finally(() => { if (n === seq.current) setLoading(false); });
  }, [scope, openOnly, query]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { localStorageSet('mf.stories.scope', scope); localStorageSet('mf.stories.open', String(openOnly)); }, [scope, openOnly]);
  useEffect(() => { const t = setTimeout(() => setQuery(q.trim()), 350); return () => clearTimeout(t); }, [q]);

  const build = async (s, again = false) => {
    setBuilding(s.key);
    try {
      const r = await jiraApi.build(s.key, selected?.id ?? null, again);
      if (r.existing || !r.requirement) navigate(`/workspace/${r.chat.id}`);
      else navigate(`/workspace/${r.chat.id}`, { state: { story: { requirement: r.requirement, attachments: r.attachments ?? [], skipped: r.skipped_attachments ?? [] } } });
    } catch (e) { setError({ text: e.message, notConnected: false }); setBuilding(null); }
  };

  const heading = data?.scope === 'all' ? 'Stories in your spaces' : 'Your assigned stories';

  return (
    <div className="section-page stories-page">
      <header className="sec-head">
        <span className="sec-ico tone-blue"><Icon name="ticket" size={22} /></span>
        <div className="sec-head-main">
          <p className="crumb"><Link to="/workspace">AI workspace</Link></p>
          <h1>Jira stories</h1>
          <p>Pick a story and nowBuilder designs it for {selected ? <strong>{selected.name}</strong> : 'your instance'}: the description, acceptance criteria and readable attachments become the requirement.</p>
        </div>
      </header>

      {error?.notConnected ? (
        <section className="block empty-block">
          <Icon name="ticket" size={28} />
          <h2>Connect Jira to build from stories</h2>
          <p className="muted">{error.text}</p>
          {can('manage_integrations') && <Link className="btn btn-primary" to="/settings/jira">Connect Jira</Link>}
        </section>
      ) : (
        <>
          <div className="stories-bar">
            <div className="seg" role="group" aria-label="Whose stories">
              <button type="button" className={scope === 'mine' ? 'on' : ''} aria-pressed={scope === 'mine'} onClick={() => setScope('mine')}>Assigned to me</button>
              <button type="button" className={scope === 'all' ? 'on' : ''} aria-pressed={scope === 'all'} onClick={() => setScope('all')}>All in spaces</button>
            </div>
            <div className="seg" role="group" aria-label="Status">
              <button type="button" className={openOnly ? 'on' : ''} aria-pressed={openOnly} onClick={() => setOpenOnly(true)}>Open</button>
              <button type="button" className={!openOnly ? 'on' : ''} aria-pressed={!openOnly} onClick={() => setOpenOnly(false)}>Any status</button>
            </div>
            <label className="sr-only" htmlFor="story-q">Search stories</label>
            <input id="story-q" className="input stories-search" placeholder="Search, or type a key like SCRUM-21" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          {!canBuild && (can('build')
            ? <div className="alert alert-warn small">Add the workspace's AI provider in <Link to="/settings/ai-provider">Settings → AI provider</Link> to build from stories.</div>
            : <div className="alert alert-info small">Your role can read stories here but not build them. Ask a workspace admin for the Developer role.</div>)}
          {error && <div className="alert alert-error small" role="alert">{error.text}</div>}
          {data?.note && <div className="alert alert-info small">{data.note}</div>}

          <section className="block stories-block" aria-busy={loading}>
            <div className="block-head">
              <h2>{heading} {data && <span className="muted">({data.stories.length})</span>}</h2>
              <button type="button" className="btn btn-sm" onClick={load} disabled={loading}><Icon name="sync" /> {loading ? 'Loading…' : 'Refresh'}</button>
            </div>
            {!data && loading && <ul className="story-list-v">{[0, 1, 2].map((i) => <li key={i} className="story-card skeleton" aria-hidden="true" />)}</ul>}
            {data && data.stories.length === 0 && (
              <p className="block-pad muted">
                {query ? `No stories match “${query}”.` : scope === 'mine' ? `Nothing ${openOnly ? 'open ' : ''}is assigned to you${data.projects.length ? ` in ${data.projects.join(', ')}` : ''}.` : 'No stories found.'}
              </p>
            )}
            {data && data.stories.length > 0 && (
              <ul className="story-list-v">
                {data.stories.map((s) => (
                  <StoryCard key={s.key} s={s} canBuild={canBuild} building={building === s.key}
                    onBuild={() => build(s, Boolean(s.chat_id))} onOpen={() => navigate(`/workspace/${s.chat_id}`)} />
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function localStorageGet(k) {
  try { return window.localStorage.getItem(k); } catch { return null; }
}
function localStorageSet(k, v) {
  try { window.localStorage.setItem(k, v); } catch { /* private mode */ }
}

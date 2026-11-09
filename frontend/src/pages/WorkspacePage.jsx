import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { chatApi, sendMessage } from '../chatApi';
import { Icon } from '../components/Icon';
import { Markdown } from '../components/Markdown';
import { PlanCard } from '../components/PlanCard';
import { useWorkspace } from '../instances';
import { useAuth } from '../auth';


function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

function Activity({ lines, working }) {
  const [open, setOpen] = useState(false);
  if (!lines.length) return working ? <div className="activity"><span className="spinner" aria-hidden="true" />Thinking…</div> : null;
  if (working) {
    return (
      <ul className="activity live" aria-live="polite">
        {lines.map((l, i) => (
          <li key={i} className={i === lines.length - 1 ? 'current' : 'done'}>
            {i === lines.length - 1 ? <span className="spinner" aria-hidden="true" /> : <span className="tick" aria-hidden="true">✓</span>}
            {l}…
          </li>
        ))}
      </ul>
    );
  }
  return (
    <div className="activity">
      <button type="button" className="link-btn muted-link" aria-expanded={open} onClick={() => setOpen(!open)}>
        Show {lines.length} step{lines.length === 1 ? '' : 's'}
      </button>
      {open && <ul>{lines.map((l, i) => <li key={i}><span className="tick" aria-hidden="true">✓</span>{l}</li>)}</ul>}
    </div>
  );
}

function StoryBar({ jira }) {
  return (
    <div className="story-bar">
      <Icon name="ticket" />
      <span>Built from Jira <a href={jira.url} target="_blank" rel="noreferrer" className="story-key">{jira.key}</a> {jira.summary}</span>
      <Link to="/workspace/stories" className="small">All stories</Link>
    </div>
  );
}

function UserBubble({ text, files }) {
  return (
    <div className="msg msg-user">
      <div className="bubble">
        {files.length > 0 && <div className="file-chips">{files.map((f) => <span key={f} className="file-chip">{f}</span>)}</div>}
        {text && <p className="user-text">{text}</p>}
      </div>
    </div>
  );
}

function AssistantMessage({ m, plan, onPlanChange }) {
  return (
    <div className="msg msg-ai">
      <Activity lines={m.activity} working={false} />
      {plan && <PlanCard plan={plan} onPlanChange={onPlanChange} />}
      {m.content && <Markdown text={m.content} />}
      {m.error && <div className="alert alert-error small">{m.error}</div>}
    </div>
  );
}

export function WorkspacePage() {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const storyStart = useRef(null);
  const { selected, ai, can } = useWorkspace();
  const { user } = useAuth();
  const canBuild = can('build');
  const [chats, setChats] = useState(null);
  const [chat, setChat] = useState(null);
  const [live, setLive] = useState(null);
  const [input, setInput] = useState(() => new URLSearchParams(window.location.search).get('idea') ?? '');  // Home → "Start with an idea"
  const [files, setFiles] = useState([]);
  const [error, setError] = useState(null);
  const [sideOpen, setSideOpen] = useState(false);
  const abortRef = useRef(null);
  const endRef = useRef(null);
  const fileRef = useRef(null);
  const taRef = useRef(null);

  const loadChats = useCallback(() => chatApi.list().then(setChats).catch(() => setChats([])), []);
  useEffect(() => { loadChats(); }, [loadChats]);
  useEffect(() => {
    if (!chatId) { setChat(null); return; }
    if (live) return; // keep the streaming view; we reload when it finishes
    chatApi.get(chatId).then(setChat).catch(() => navigate('/workspace', { replace: true }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatId, navigate]);
  useEffect(() => { endRef.current?.scrollIntoView({ block: 'end' }); },
    [chat?.messages.length, live?.text, live?.activity.length, live?.plan?.components?.length]);
  useEffect(() => {
    const ta = taRef.current;
    if (ta) { ta.style.height = 'auto'; ta.style.height = `${Math.min(ta.scrollHeight, 220)}px`; }
  }, [input]);

  const aiReady = Boolean(ai?.verified) && canBuild;
  const busy = live !== null;

  const send = async (text, story) => {
    const t = text.trim();
    if ((!t && !files.length) || busy || !aiReady) return;
    setError(null);
    const sending = story ? [] : files;
    setInput('');
    if (!story) setFiles([]);
    setLive({ userText: t, files: story ? story.attachments : sending.map((f) => f.name), activity: [], text: '', error: null, plan: null });
    let id = chatId;
    try {
      if (!id) {
        const created = await chatApi.create();
        id = created.id;
        navigate(`/workspace/${id}`);
      }
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      await sendMessage(id, t, sending, (e) => {
        setLive((s) => {
          if (!s) return s;
          switch (e.type) {
            case 'status': return { ...s, activity: [...s.activity, e.text] };
            case 'text': return { ...s, text: s.text + e.delta };
            case 'error': return { ...s, error: e.message };
            // the plan card: a live draft while the AI writes it, then each artifact as it lands
            case 'plan_draft': return s.plan?.id ? s : { ...s, plan: e.plan };
            case 'plan': case 'plan_done': return { ...s, plan: e.plan };
            case 'component': return s.plan?.id === e.plan_id
              ? { ...s, plan: { ...s.plan, components: s.plan.components.map((c) => (c.id === e.component.id ? e.component : c)) } }
              : s;
            default: return s;
          }
        });
      }, ctrl.signal, Boolean(story));
    } catch (e) {
      setError(e.message);
      if (!chatId && !id) { setInput(t); }
    } finally {
      abortRef.current = null;
      if (id) setChat(await chatApi.get(id).catch(() => null));
      setLive(null);
      loadChats();
    }
  };

  // Jira stories → Build: the story is this new chat's first message (sent once)
  useEffect(() => {
    const st = (location.state)?.story;
    if (!st || !chatId || !aiReady || storyStart.current === chatId) return;
    storyStart.current = chatId;
    navigate(location.pathname, { replace: true, state: null });
    send(st.requirement, { attachments: st.attachments });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatId, aiReady, location.state]);

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(input); }
  };

  const newChat = () => { if (!busy) { setChat(null); navigate('/workspace'); taRef.current?.focus(); } };
  const removeChat = async (c) => {
    if (!window.confirm(`Delete “${c.title}”?`)) return;
    await chatApi.remove(c.id).catch(() => {});
    if (c.id === chatId) navigate('/workspace');
    loadChats();
  };

  const messages = chat?.messages ?? [];
  const plansById = new Map((chat?.plans ?? []).map((p) => [p.id, p]));
  // a plan card that changed (fix, approve, deploy) keeps the chat's copy in step
  const replacePlan = (next) => setChat((c) => (c ? { ...c, plans: c.plans.map((p) => (p.id === next.id ? next : p)) } : c));
  const empty = !messages.length && !live;

  const composer = (
    <form className="cmp" onSubmit={(e) => { e.preventDefault(); send(input); }}>
      {error && <div className="alert alert-error small" role="alert">{error}</div>}
      <div className="cmp-box">
        {files.length > 0 && (
          <div className="file-chips cmp-files">
            {files.map((f) => (
              <span key={f.name} className="file-chip"><Icon name="doc" size={13} /> {f.name}
                <button type="button" aria-label={`Remove ${f.name}`} onClick={() => setFiles(files.filter((x) => x !== f))}>×</button>
              </span>
            ))}
          </div>
        )}
        <label htmlFor="prompt" className="sr-only">Ask about ServiceNow or describe a requirement</label>
        <textarea id="prompt" ref={taRef} rows={empty ? 2 : 1} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKey}
          placeholder={aiReady ? (empty ? 'Ask a ServiceNow question, or describe what you need — flows, business rules, scripts, tables, catalog items, notifications and more…' : 'Ask a follow-up, or describe something new…')
            : !canBuild ? 'Your role can read this chat but not send messages' : 'Add your AI provider in Settings to start'} disabled={!aiReady} />
        <div className="cmp-bar">
          <button type="button" className="cmp-tool" title="Attach a BRD (.docx, .pdf, .txt, .md)" onClick={() => fileRef.current?.click()} disabled={busy || !aiReady}>
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 11.5 12.4 20a5.5 5.5 0 0 1-7.8-7.8l8.9-8.9a3.7 3.7 0 0 1 5.2 5.2l-8.9 8.9a1.8 1.8 0 0 1-2.6-2.6l8.2-8.2" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" /></svg>
            <span>Attach</span>
          </button>
          <input ref={fileRef} type="file" hidden multiple accept=".docx,.pdf,.txt,.md"
            onChange={(e) => { setFiles([...files, ...Array.from(e.target.files ?? [])].slice(0, 3)); e.target.value = ''; }} />
          {empty && <Link to="/workspace/stories" className="cmp-tool"><Icon name="ticket" size={15} /><span>Jira story</span></Link>}
          {selected && (
            <span className={`cmp-org${selected.instance_type === 'Production' ? ' prod' : ''}`} title={`nowBuilder reads ${selected.name}`}>
              <span className="cmp-dot" aria-hidden="true" />{selected.name}<span className="cmp-org-type">{selected.instance_type}</span>
            </span>
          )}
          <span className="cmp-spacer" />
          <span className="cmp-hint">Enter to send, Shift+Enter for a new line</span>
          {busy ? (
            <button type="button" className="cmp-send stop" aria-label="Stop" onClick={() => abortRef.current?.abort()}><span className="cmp-stop" aria-hidden="true" /></button>
          ) : (
            <button className="cmp-send" aria-label="Send" disabled={!aiReady || (!input.trim() && !files.length)}>
              <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 15.5V4.5M5 9.5l5-5 5 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </button>
          )}
        </div>
      </div>
    </form>
  );

  return (
    <div className="workspace">
      <aside className={`ws-side${sideOpen ? ' open' : ''}`} aria-label="Chats" onClick={(e) => { if ((e.target).closest('a')) setSideOpen(false); }}>
        <button className="btn btn-primary btn-block" onClick={newChat} disabled={busy || !canBuild}>New chat</button>
        <Link to="/workspace/stories" className="btn btn-block side-stories" onClick={(e) => busy && e.preventDefault()}><Icon name="ticket" /> Jira stories</Link>
        <nav className="chat-list">
          {chats?.length === 0 && <p className="muted small" style={{ padding: '8px 4px' }}>Your chats appear here.</p>}
          {chats?.map((c) => (
            <div key={c.id} className={`chat-link${c.id === chatId ? ' active' : ''}`}>
              <Link to={`/workspace/${c.id}`} title={c.by && c.user_id !== user?.id ? `${c.title} (started by ${c.by})` : c.title} onClick={(e) => busy && e.preventDefault()}>
                {c.title}{c.by && c.user_id !== user?.id && <span className="chat-by">{c.by}</span>}
              </Link>
              {(c.user_id === user?.id || can('manage_members')) && <button className="icon-btn" aria-label={`Delete ${c.title}`} onClick={() => removeChat(c)} disabled={busy}>×</button>}
            </div>
          ))}
        </nav>
      </aside>

      <section className="ws-main">
        <div className="ws-mobilebar">
          <button type="button" className="btn btn-sm" aria-expanded={sideOpen} onClick={() => setSideOpen(!sideOpen)}>Chats</button>
          <span className="ws-mobile-title">{chat?.title ?? 'New chat'}</span>
          <button type="button" className="btn btn-sm" onClick={newChat} disabled={busy}>New</button>
        </div>
        <div className="ws-scroll">
          {empty ? (
            <div className="ws-hero">
              <div className="hero-mark" aria-hidden="true">
                <svg viewBox="0 0 64 56" width="56" height="49">
                  <g fill="#fff" stroke="#cfdcf2" strokeWidth="1.5"><circle cx="20" cy="30" r="13" /><circle cx="44" cy="31" r="12" /><circle cx="32" cy="23" r="16" /><rect x="13" y="29" width="38" height="18" rx="9" /></g>
                  <rect x="19" y="22" width="26" height="16" rx="8" fill="#15233b" />
                  <ellipse className="hero-eye" cx="27.5" cy="30" rx="2.4" ry="3.2" fill="#6fe3ff" /><ellipse className="hero-eye" cx="36.5" cy="30" rx="2.4" ry="3.2" fill="#6fe3ff" />
                  <line x1="32" y1="7" x2="32" y2="2.5" stroke="#9fb4d6" strokeWidth="1.6" strokeLinecap="round" /><circle cx="32" cy="2.5" r="2" fill="#ffb547" />
                </svg>
              </div>
              <p className="hero-hello">{greeting()}{user?.first_name ? `, ${user.first_name}` : ''}</p>
              <h1>What should we build{selected ? <> in <span className="hero-org">{selected.name}</span></> : ''}?</h1>
              <p className="hero-sub">Ask anything about ServiceNow or your instance, or describe a requirement, attach a design document or pick a Jira story. nowBuilder reads your instance and the ServiceNow and Fluent documentation, asks what it needs to know, then plans, builds and deploys it the ServiceNow way.</p>
              {!canBuild && <div className="alert alert-info">Your role can read chats here but not start or change them. Ask a workspace admin for the Developer role.</div>}
              {canBuild && !aiReady && <div className="alert alert-warn">Add your AI provider in <Link to="/settings/ai-provider">Settings → AI provider</Link> to start.</div>}
              {aiReady && !selected && <div className="alert alert-warn">No instance connected. nowBuilder can answer general ServiceNow questions, but <Link to="/settings/instances">connect an instance</Link> so it can read your tables and scripts.</div>}
            </div>
          ) : (
            <div className="thread">
              {chat?.jira && <StoryBar jira={chat.jira} />}
              {messages.map((m) => m.role === 'user'
                ? <UserBubble key={m.id} text={m.content} files={m.attachments.map((a) => a.name)} />
                : <AssistantMessage key={m.id} m={m} plan={plansById.get(m.plan_id)} onPlanChange={replacePlan} />)}
              {live && (
                <>
                  <UserBubble text={live.userText} files={live.files} />
                  <div className="msg msg-ai">
                    <Activity lines={live.activity} working={!live.error} />
                    {live.plan && <PlanCard plan={live.plan} />}
                    {live.text && <Markdown text={live.text} />}
                    {live.error && <div className="alert alert-error small">{live.error}</div>}
                  </div>
                </>
              )}
              <div ref={endRef} />
            </div>
          )}
        </div>

        {composer}
      </section>
    </div>
  );
}

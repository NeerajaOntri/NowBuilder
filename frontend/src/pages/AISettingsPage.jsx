import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { Icon } from '../components/Icon';
import { useWorkspace } from '../instances';

const n = (v) => Math.round(v).toLocaleString();
const monthName = (m) => new Date(`${m}-01T00:00:00`).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
const OP_COLOR = { generate: '#1d5fd6', fix: '#d97a1a', chat: '#7b8798', auto_repair: '#8a5cd6', import_mapping: '#12805a', migration_fix: '#b8321f' };
const norm = (s) => s.toLowerCase().replace(/[^a-z0-9.]+/g, ' ').trim();
const findPreset = (presets, text) => {
  const t = norm(text);
  return t ? presets.find((p) => [p.key, p.label, ...p.aliases].some((a) => norm(a) === t)) ?? null : null;
};

export function AISettingsPage() {
  const { ai, can } = useWorkspace();
  const manage = can('manage_ai');
  if (ai === undefined) return <div className="page-loading" role="status">Loading…</div>;
  return (
    <>
      <div className="section-head">
        <div>
          <h1>AI provider</h1>
          <p className="muted">nowBuilder uses this model to plan requirements, generate components and run Fix with AI. One key is shared by everyone in the workspace.</p>
        </div>
      </div>
      <ProviderPanel manage={manage} />
      {manage && ai && <CreditUsage />}
    </>
  );
}

function ProviderPanel({ manage }) {
  const { ai } = useWorkspace();
  const [open, setOpen] = useState(!ai);
  useEffect(() => { if (!ai) setOpen(true); }, [ai]);
  return (
    <section className="panel ai-provider" aria-labelledby="ai-prov-h">
      <div className="ai-prov-head">
        <span className="ai-prov-icon"><Icon name="sparkle" size={20} /></span>
        <div className="ai-prov-text">
          <h2 id="ai-prov-h">AI provider</h2>
          {ai ? (
            <p className="small">
              <span className={`badge ${ai.verified ? 'badge-ok' : 'badge-err'}`}>{ai.verified ? 'Connected' : 'Not verified'}</span>
              {ai.updated_at && <span className="muted"> Updated {new Date(ai.updated_at).toLocaleDateString()}</span>}
              <span className="muted"> · </span><span>{ai.provider_name || ai.provider}</span><span className="muted"> / </span><span className="api">{ai.model}</span>
            </p>
          ) : <p className="small muted">Not set up yet.</p>}
        </div>
        {manage && ai && (
          <button type="button" className="btn btn-sm" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? 'Close' : 'Change'}
          </button>
        )}
      </div>
      {ai && !ai.verified && <div className="alert alert-error small ai-prov-alert" role="status">{ai.status_message ?? 'The key isn\'t verified.'}</div>}
      {!manage && <p className="small muted ai-prov-note">Only workspace admins can change the AI provider.</p>}
      {manage && open && <ProviderForm onSaved={() => setOpen(false)} />}
    </section>
  );
}

function ProviderForm({ onSaved }) {
  const { ai, setAI } = useWorkspace();
  const [presets, setPresets] = useState([]);
  const [provider, setProvider] = useState(ai?.provider_name || ai?.provider || '');
  const [baseUrl, setBaseUrl] = useState(ai?.kind === 'openai' && ai.base_url ? ai.base_url : '');
  const [model, setModel] = useState(ai?.model ?? '');
  const [apiKey, setApiKey] = useState('');
  const [replacing, setReplacing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api('/api/settings/ai-provider/options').then((o) => setPresets(o.providers)).catch(() => {});
  }, []);

  const preset = useMemo(() => findPreset(presets, provider), [presets, provider]);
  const known = Boolean(preset);
  const showUrl = provider.trim() !== '' && (!preset || preset.kind !== 'anthropic');
  const needsUrl = provider.trim() !== '' && (!preset || preset.needs_base_url);
  const sameProvider = Boolean(ai) && norm(provider) === norm(ai.provider_name || ai.provider);
  const needsKey = !ai || replacing || !sameProvider;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const saved = await api('/api/settings/ai-provider', { method: 'PUT', json: {
        provider: provider.trim(), model: model.trim(), api_key: needsKey ? apiKey.trim() : undefined,
        base_url: showUrl ? baseUrl.trim() || null : null } });
      setAI(saved); setApiKey(''); setReplacing(false);
      if (saved.verified) onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="form ai-form" onSubmit={submit} noValidate>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      <div className="field">
        <label htmlFor="provider">Provider</label>
        <input id="provider" className="input" value={provider} onChange={(e) => setProvider(e.target.value)} autoComplete="off"
          placeholder="For example Anthropic, OpenAI, Google Gemini, Groq" />
        <span className="hint">
          {!provider.trim() ? 'Type the name of your AI provider.'
            : known ? `nowBuilder knows ${preset.label}${preset.kind === 'anthropic' || !preset.needs_base_url ? ', so no address is needed' : ''}.`
            : 'nowBuilder will connect through this provider\'s OpenAI-compatible API: add its base URL.'}
        </span>
      </div>
      {showUrl && (
        <div className="field">
          <label htmlFor="base-url">Base URL {needsUrl ? '' : <span className="muted">(optional)</span>}</label>
          <input id="base-url" className="input api" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} autoComplete="off"
            placeholder={preset?.base_url || preset?.base_url_hint || 'https://api.example.com/v1'} />
          <span className="hint">{needsUrl ? 'The API address that comes before /chat/completions.' : 'Leave empty to use the provider\'s usual address.'}</span>
        </div>
      )}
      <div className="field">
        <label htmlFor="api-key">API key</label>
        {needsKey ? (
          <>
            <input id="api-key" className="input" type="password" autoComplete="off" placeholder={preset?.key_hint || 'Your API key'} value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
            <span className="hint">Stored encrypted. nowBuilder only shows the last 4 characters.{ai && !sameProvider ? ' A different provider needs its own key.' : ''}</span>
          </>
        ) : (
          <div className="key-row">
            <input id="api-key" className="input" value={ai.api_key_masked} readOnly aria-readonly="true" />
            <button type="button" className="btn" onClick={() => setReplacing(true)}>Replace</button>
          </div>
        )}
      </div>
      <div className="field">
        <label htmlFor="model">Model</label>
        <input id="model" className="input api" value={model} onChange={(e) => setModel(e.target.value)} placeholder={preset?.model_hint || 'Model name, exactly as the provider writes it'} />
        <span className="hint">Exactly as the provider writes it.</span>
      </div>
      <div className="form-actions">
        {replacing && ai && <button type="button" className="btn" onClick={() => { setReplacing(false); setApiKey(''); }}>Cancel</button>}
        <button className="btn btn-primary" disabled={busy || !model.trim() || !provider.trim() || (needsKey && !apiKey.trim()) || (needsUrl && !baseUrl.trim())}>
          {busy ? 'Checking…' : 'Save and verify'}
        </button>
      </div>
    </form>
  );
}

function CreditUsage() {
  const { ai } = useWorkspace();
  const [month, setMonth] = useState(undefined);
  const [u, setU] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    setError(null);
    api(`/api/settings/ai-usage${month ? `?month=${month}` : ''}`).then(setU).catch((e) => setError(e.message));
  }, [month, ai?.model]);
  if (error) return <div className="alert alert-error" role="alert">{error}</div>;
  if (!u) return <div className="panel"><p className="muted" style={{ margin: 0 }}>Loading credit usage…</p></div>;
  const maxOp = Math.max(1, ...u.by_operation.map((o) => o.credits));
  return (
    <section className="panel ai-credits" aria-labelledby="ai-cred-h">
      <div className="ai-prov-head">
        <span className="ai-prov-icon ai-cred-icon"><Icon name="bolt" size={20} /></span>
        <div className="ai-prov-text">
          <h2 id="ai-cred-h">AI credit usage</h2>
          <p className="small muted">{monthName(u.month)} · <span className="api">{u.model}</span></p>
        </div>
        <div className="ai-month" role="group" aria-label="Month">
          <button type="button" className="btn btn-sm" onClick={() => setMonth(u.previous)} aria-label="Previous month">‹</button>
          <button type="button" className="btn btn-sm" disabled={!u.next} onClick={() => u.next && setMonth(u.next)} aria-label="Next month">›</button>
        </div>
      </div>
      <p className="ai-used"><strong>{n(u.used)}</strong> credits used in {monthName(u.month)}<span className="muted"> · {n(u.calls)} AI calls</span></p>
      {u.calls > 0 ? (
        <div className="ai-split">
          <div>
            <h3 className="ai-split-h">By operation</h3>
            <ul className="ai-list">
              {u.by_operation.map((o) => (
                <li key={o.key}><span className="ai-dot" style={{ background: OP_COLOR[o.key] ?? '#7b8798' }} />{o.label}
                  <span className="ai-bar"><span style={{ width: `${(o.credits / maxOp) * 100}%`, background: OP_COLOR[o.key] ?? '#7b8798' }} /></span>
                  <span className="ai-cr">{n(o.credits)} cr</span></li>
              ))}
            </ul>
          </div>
          {u.by_member.length > 1 && (
            <div>
              <h3 className="ai-split-h">By member</h3>
              <ul className="ai-list">
                {u.by_member.map((m) => <li key={m.user_id ?? 'x'}>{m.name}<span className="ai-cr">{n(m.credits)} cr</span></li>)}
              </ul>
            </div>
          )}
        </div>
      ) : <p className="small muted">No AI use in {monthName(u.month)} yet.</p>}
      <p className="small muted ai-foot">1 credit = 1,000 tokens the AI reads or writes (prompt text it re-reads counts 10%). Your provider bills the API key for what is actually used.</p>
    </section>
  );
}

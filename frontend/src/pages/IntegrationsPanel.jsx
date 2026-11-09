import { useCallback, useEffect, useState } from 'react';
import { ConfirmDialog } from '../components/Dialog';
import { Icon } from '../components/Icon';
import {
  integrationsApi } from '../integrationsApi';

function Status({ i }) {
  if (!i.connected) return <span className="badge badge-neutral">Not connected</span>;
  return i.status === 'error' ? <span className="badge badge-err">Needs attention</span> : <span className="badge badge-ok"><Icon name="check" size={12} /> Connected</span>;
}

// ---------- Jira ----------

function JiraCard({ jira, manage, onSaved }) {
  const [editing, setEditing] = useState(!jira.connected);
  const [site, setSite] = useState(jira.site ?? '');
  const [email, setEmail] = useState(jira.email ?? '');
  const [token, setToken] = useState('');
  const [spaceKeys, setSpaceKeys] = useState((jira.projects ?? []).join(', '));
  const [projects, setProjects] = useState(jira.projects ?? []);
  const [comments, setComments] = useState(jira.comments ?? true);
  const [all, setAll] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(null);
  const [removing, setRemoving] = useState(false);

  useEffect(() => {
    if (jira.connected && manage) integrationsApi.jiraProjects().then(setAll).catch(() => setAll([]));
  }, [jira.connected, jira.updated_at, manage]);
  useEffect(() => { setProjects(jira.projects ?? []); setComments(jira.comments ?? true); }, [jira.projects, jira.comments]);

  const save = async (e, body) => {
    e?.preventDefault();
    setBusy(true); setError(null); setSaved(null);
    try {
      const fromForm = e ? spaceKeys.split(/[\s,;]+/).map((k) => k.trim().toUpperCase()).filter(Boolean) : null;
      const keys = body?.projects ?? fromForm ?? projects;
      await integrationsApi.saveJira({ site: site.trim(), email: email.trim(), token: token.trim() || null, projects: keys, comments: body?.comments ?? comments });
      setToken(''); setEditing(false);
      setSaved(jira.connected ? 'Saved.' : keys.length ? `Jira is connected. Stories come from ${keys.join(', ')}.` : 'Jira is connected. Pick the spaces your team builds from, or leave none to see every space.');
      onSaved();
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };

  return (
    <section className="block integ-card" aria-labelledby="jira-h">
      <div className="block-head">
        <h2 id="jira-h"><span className="integ-logo jira" aria-hidden="true"><Icon name="ticket" /></span> Jira</h2>
        <Status i={jira} />
      </div>
      <div className="block-pad">
        <p className="muted small">Build from Jira stories in the AI workspace. nowBuilder comments on the story when its plan is ready, deployed or pushed to GitHub.</p>
        {error && <div className="alert alert-error small" role="alert">{error}</div>}
        {saved && <div className="alert alert-success small" role="status">{saved}</div>}
        {jira.connected && !editing && (
          <dl className="integ-facts">
            <div><dt>Site</dt><dd><a href={jira.site} target="_blank" rel="noreferrer">{jira.site?.replace('https://', '')}</a></dd></div>
            <div><dt>Account</dt><dd>{jira.account} <span className="muted">({jira.email})</span></dd></div>
            <div><dt>API token</dt><dd className="mono">{jira.token_masked}</dd></div>
          </dl>
        )}
        {manage && editing && (
          <form className="integ-form" onSubmit={save}>
            <label className="field"><span className="field-label">Jira site</span>
              <input className="input" placeholder="yourcompany.atlassian.net" value={site} onChange={(e) => setSite(e.target.value)} required autoComplete="off" /></label>
            <label className="field"><span className="field-label">Atlassian account email</span>
              <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="off" /></label>
            <label className="field"><span className="field-label">API token</span>
              <input className="input" type="password" value={token} onChange={(e) => setToken(e.target.value)} required={!jira.connected}
                placeholder={jira.connected ? 'Leave empty to keep the saved token' : ''} autoComplete="new-password" />
              <span className="field-hint">Create one at id.atlassian.com → Security → API tokens. nowBuilder sees what this account can see; it's stored encrypted.</span></label>
            <label className="field"><span className="field-label">Space key <span className="muted">(optional)</span></span>
              <input className="input mono" placeholder="SCRUM" value={spaceKeys} onChange={(e) => setSpaceKeys(e.target.value)} autoComplete="off" spellCheck={false} />
              <span className="field-hint">The short key before a story number, like SCRUM in SCRUM-21. Separate several with commas. Leave it empty to see stories from every space the account can see; you can also pick spaces after connecting.</span></label>
            <div className="row-actions">
              {jira.connected && <button type="button" className="btn btn-sm" onClick={() => { setEditing(false); setError(null); }} disabled={busy}>Cancel</button>}
              <button className="btn btn-sm btn-primary" disabled={busy}>{busy ? 'Checking…' : jira.connected ? 'Save' : 'Connect Jira'}</button>
            </div>
          </form>
        )}
        {jira.connected && !editing && (
          <>
            <h3 className="integ-sub">Spaces</h3>
            {manage ? (
              all === null ? <p className="muted small">Loading spaces…</p> : (
                <>
                  <p className="small muted">{projects.length ? 'Stories come from these spaces.' : 'No space chosen: stories come from every space the account can see.'}</p>
                  <div className="chip-picks" role="group" aria-label="Jira spaces">
                    {all.map((p) => {
                      const on = projects.includes(p.key);
                      return (
                        <button key={p.key} type="button" className={`chip-pick${on ? ' on' : ''}`} aria-pressed={on}
                          onClick={() => setProjects(on ? projects.filter((k) => k !== p.key) : [...projects, p.key])}>
                          {on && <Icon name="check" size={12} />}<span className="mono">{p.key}</span> {p.name}
                        </button>
                      );
                    })}
                    {all.length === 0 && <p className="small muted">The account can't see any spaces.</p>}
                  </div>
                </>
              )
            ) : <p className="small">{jira.projects?.length ? jira.projects.join(', ') : 'All spaces the account can see'}</p>}
            <label className="check integ-check">
              <input type="checkbox" checked={comments} disabled={!manage} onChange={(e) => setComments(e.target.checked)} />
              Comment on stories when their plan is ready, deployed or pushed
            </label>
            {manage && (
              <div className="row-actions">
                <button type="button" className="btn btn-sm" onClick={() => setRemoving(true)}>Disconnect</button>
                <button type="button" className="btn btn-sm" onClick={() => { setEditing(true); setSaved(null); setSpaceKeys(projects.join(', ')); }}>Change account</button>
                <button type="button" className="btn btn-sm btn-primary" disabled={busy || (JSON.stringify([...projects].sort()) === JSON.stringify([...(jira.projects ?? [])].sort()) && comments === (jira.comments ?? true))}
                  onClick={() => save(undefined)}>{busy ? 'Saving…' : 'Save spaces'}</button>
              </div>
            )}
          </>
        )}
        {!manage && !jira.connected && <p className="small">Ask a workspace admin to connect Jira.</p>}
      </div>
      {removing && (
        <ConfirmDialog title="Disconnect Jira?" confirmLabel="Disconnect" danger onCancel={() => setRemoving(false)}
          onConfirm={async () => { await integrationsApi.disconnect('jira'); setRemoving(false); setEditing(true); onSaved(); }}>
          <p>The team can't list or build from stories until Jira is connected again. Chats already built from stories stay as they are.</p>
        </ConfirmDialog>
      )}
    </section>
  );
}

// ---------- GitHub ----------

function RepoRow({ org, target, repos, onSave }

) {
  const [editing, setEditing] = useState(!target);
  const [repo, setRepo] = useState(target?.repo ?? '');
  const [branch, setBranch] = useState(target?.branch ?? '');
  const [branches, setBranches] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  useEffect(() => {
    if (!editing || !repo) { setBranches(null); return; }
    let live = true;
    setBranches(null);
    integrationsApi.branches(repo).then((b) => {
      if (!live) return;
      setBranches(b);
      if (!b.includes(branch)) setBranch(repos?.find((r) => r.full_name === repo)?.default_branch ?? b[0] ?? '');
    }).catch((e) => live && setError(e.message));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repo, editing]);
  const save = async (t) => {
    setBusy(true); setError(null);
    try { await onSave(t); setEditing(false); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  return (
    <li className="repo-row">
      <div className="repo-org"><strong>{org.name}</strong> <span className={`badge ${org.instance_type === 'Production' ? 'badge-prod' : 'badge-neutral'}`}>{org.instance_type}</span></div>
      {!editing && target ? (
        <>
          <div className="repo-target"><Icon name="branch" /> <span className="mono">{target.repo}</span> <span className="muted">into</span> <span className="mono">{target.branch}</span></div>
          <div className="row-actions"><button type="button" className="btn btn-sm" onClick={() => setEditing(true)}>Change</button></div>
        </>
      ) : (
        <>
          <div className="repo-pick">
            <label className="sr-only" htmlFor={`repo-${org.id}`}>Repository for {org.name}</label>
            <select id={`repo-${org.id}`} className="input" value={repo} onChange={(e) => setRepo(e.target.value)} disabled={!repos}>
              <option value="">{repos ? 'Choose a repository' : 'Loading repositories…'}</option>
              {repos?.map((r) => <option key={r.full_name} value={r.full_name} disabled={!r.can_push}>{r.full_name}{r.can_push ? '' : ' (read only)'}</option>)}
            </select>
            <label className="sr-only" htmlFor={`branch-${org.id}`}>Base branch for {org.name}</label>
            <select id={`branch-${org.id}`} className="input" value={branch} onChange={(e) => setBranch(e.target.value)} disabled={!branches}>
              {!branches && <option value="">{repo ? 'Loading branches…' : 'Base branch'}</option>}
              {branches?.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
          <div className="row-actions">
            {target && <button type="button" className="btn btn-sm" disabled={busy} onClick={() => save(null)}>Remove</button>}
            {target && <button type="button" className="btn btn-sm" disabled={busy} onClick={() => { setEditing(false); setRepo(target.repo); setBranch(target.branch); }}>Cancel</button>}
            <button type="button" className="btn btn-sm btn-primary" disabled={busy || !repo || !branch} onClick={() => save({ repo, branch })}>{busy ? 'Saving…' : 'Save'}</button>
          </div>
        </>
      )}
      {error && <div className="alert alert-error small repo-err" role="alert">{error}</div>}
    </li>
  );
}

function GitHubCard({ gh, orgs, manage, onSaved }) {
  const [editing, setEditing] = useState(!gh.connected);
  const [token, setToken] = useState('');
  const [repos, setRepos] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [removing, setRemoving] = useState(false);
  useEffect(() => {
    if (gh.connected && manage) integrationsApi.repos().then(setRepos).catch((e) => { setRepos([]); setError(e.message); });
  }, [gh.connected, gh.updated_at, manage]);
  const connect = async (e) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try { await integrationsApi.saveGitHub({ token: token.trim() }); setToken(''); setEditing(false); onSaved(); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  return (
    <section className="block integ-card" aria-labelledby="gh-h">
      <div className="block-head">
        <h2 id="gh-h"><span className="integ-logo gh" aria-hidden="true"><Icon name="branch" /></span> GitHub</h2>
        <Status i={gh} />
      </div>
      <div className="block-pad">
        <p className="muted small">Push approved changes to a branch and open a pull request (with deploys, in the next release). Each ServiceNow instance has its own repository and base branch.</p>
        {error && <div className="alert alert-error small" role="alert">{error}</div>}
        {gh.connected && !editing && (
          <dl className="integ-facts">
            <div><dt>Account</dt><dd>{gh.login}</dd></div>
            <div><dt>Access token</dt><dd className="mono">{gh.token_masked}</dd></div>
          </dl>
        )}
        {manage && editing && (
          <form className="integ-form" onSubmit={connect}>
            <label className="field"><span className="field-label">Fine-grained personal access token</span>
              <input className="input" type="password" value={token} onChange={(e) => setToken(e.target.value)} required autoComplete="new-password" placeholder="github_pat_…" />
              <span className="field-hint">In GitHub: Settings → Developer settings → Fine-grained tokens. Choose only the repositories nowBuilder may use, and give
                Contents and Pull requests <strong>read and write</strong>. Stored encrypted.</span></label>
            <div className="row-actions">
              {gh.connected && <button type="button" className="btn btn-sm" onClick={() => setEditing(false)} disabled={busy}>Cancel</button>}
              <button className="btn btn-sm btn-primary" disabled={busy || !token.trim()}>{busy ? 'Checking…' : gh.connected ? 'Save token' : 'Connect GitHub'}</button>
            </div>
          </form>
        )}
        {gh.connected && !editing && (
          <>
            <h3 className="integ-sub">Repository per instance</h3>
            {orgs.length === 0 && <p className="small muted">Connect a ServiceNow instance first.</p>}
            <ul className="repo-list">
              {orgs.map((o) => manage
                ? <RepoRow key={o.id} org={o} target={gh.repos?.[o.id]} repos={repos}
                    onSave={async (t) => { await integrationsApi.saveGitHub({ repos: { [o.id]: t } }); onSaved(); }} />
                : (
                  <li key={o.id} className="repo-row">
                    <div className="repo-org"><strong>{o.name}</strong></div>
                    <div className="repo-target">{gh.repos?.[o.id] ? <><span className="mono">{gh.repos[o.id].repo}</span> <span className="muted">into</span> <span className="mono">{gh.repos[o.id].branch}</span></> : <span className="muted">Not set</span>}</div>
                  </li>
                ))}
            </ul>
            {manage && (
              <div className="row-actions">
                <button type="button" className="btn btn-sm" onClick={() => setRemoving(true)}>Disconnect</button>
                <button type="button" className="btn btn-sm" onClick={() => setEditing(true)}>Change token</button>
              </div>
            )}
          </>
        )}
        {!manage && !gh.connected && <p className="small">Ask a workspace admin to connect GitHub.</p>}
      </div>
      {removing && (
        <ConfirmDialog title="Disconnect GitHub?" confirmLabel="Disconnect" danger onCancel={() => setRemoving(false)}
          onConfirm={async () => { await integrationsApi.disconnect('github'); setRemoving(false); setEditing(true); onSaved(); }}>
          <p>Push to Git stops working until GitHub is connected again. Pull requests already opened stay in GitHub, and the repository choices are forgotten.</p>
        </ConfirmDialog>
      )}
    </section>
  );
}

function useIntegrations() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const load = useCallback(() => integrationsApi.get().then((d) => { setData(d); setError(null); }).catch((e) => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);
  return { data, error, load };
}

function Head({ title, children }) {
  return (
    <div className="section-head">
      <div><h1>{title}</h1><p className="muted">{children}</p></div>
    </div>
  );
}

export function JiraSettingsPage() {
  const { data, error, load } = useIntegrations();
  return (
    <>
      <Head title="Jira">Connect Jira Cloud so the team can build from stories in the AI workspace. One connection is shared by everyone in the workspace.</Head>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {!data && !error && <p className="muted">Loading…</p>}
      {data && !data.can_manage && <div className="alert alert-info small">Only workspace admins can change Jira settings.</div>}
      {data && <JiraCard jira={data.jira} manage={data.can_manage} onSaved={load} />}
    </>
  );
}

export function GitHubSettingsPage() {
  const { data, error, load } = useIntegrations();
  return (
    <>
      <Head title="GitHub">Connect GitHub so approved plans can be pushed to a branch with a pull request. One connection is shared by everyone in the workspace.</Head>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {!data && !error && <p className="muted">Loading…</p>}
      {data && !data.can_manage && <div className="alert alert-info small">Only workspace admins can change GitHub settings.</div>}
      {data && <GitHubCard gh={data.github} orgs={data.instances} manage={data.can_manage} onSaved={load} />}
    </>
  );
}

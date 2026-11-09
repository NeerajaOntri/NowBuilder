import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { Wordmark } from '../components/Wordmark';
import { AuthScene } from '../components/AuthScene';

export function AuthLayout({ children }) {
  return (
    <div className="auth auth2">
      <aside className="auth-scene">
        <AuthScene />
      </aside>
      <div className="auth-form-side">
        <div className="auth-top">
          <Wordmark />
        </div>
        {children}
        <p className="auth-foot">© {new Date().getFullYear()} nowBuilder. ServiceNow development you review before anything changes.</p>
      </div>
    </div>
  );
}

function useSubmit(fn) {
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try { await fn(); } catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  return { error, busy, submit };
}

export function SignInPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state)?.from ?? '/';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { error, busy, submit } = useSubmit(async () => { await signIn(email, password); navigate(from, { replace: true }); });

  return (
    <AuthLayout>
      <form className="auth-form" onSubmit={submit} noValidate>
        <header>
          <h1>Sign in to nowBuilder</h1>
          <p className="muted">Design, check and build ServiceNow business rules, scripts and UI logic from plain-language requirements.</p>
        </header>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field">
          <div className="label-row">
            <label htmlFor="password">Password</label>
            <Link to="/forgot-password" state={{ email }} className="small">Forgot password?</Link>
          </div>
          <input id="password" className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <button className="btn btn-primary btn-block" disabled={busy || !email || !password}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <p className="auth-switch">New to nowBuilder? <Link to="/create-account" state={{ from }}>Create an account</Link></p>
      </form>
    </AuthLayout>
  );
}

export function CreateAccountPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state)?.from ?? '/';
  const invitedEmail = new URLSearchParams(location.search).get('email') ?? '';
  const [f, setF] = useState({ first_name: '', last_name: '', email: invitedEmail, password: '' });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const tooShort = f.password.length > 0 && f.password.length < 8;
  const { error, busy, submit } = useSubmit(async () => {
    if (f.password.length < 8) throw new Error('Use at least 8 characters for your password.');
    const u = await register({ ...f, email: f.email.trim() });
    navigate(u.email_verified === false ? '/verify-email' : from, { replace: true, state: { from } });
  });

  return (
    <AuthLayout>
      <form className="auth-form" onSubmit={submit} noValidate>
        <header>
          <h1>Create your account</h1>
          <p className="muted">{from.startsWith('/invite/') ? 'Then you join the workspace you were invited to.' : 'Your personal workspace is set up automatically.'}</p>
        </header>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <div className="form-row">
          <div className="field">
            <label htmlFor="first">First name</label>
            <input id="first" className="input" autoComplete="given-name" required value={f.first_name} onChange={set('first_name')} />
          </div>
          <div className="field">
            <label htmlFor="last">Last name</label>
            <input id="last" className="input" autoComplete="family-name" required value={f.last_name} onChange={set('last_name')} />
          </div>
        </div>
        <div className="field">
          <label htmlFor="email">Work email</label>
          <input id="email" className="input" type="email" autoComplete="email" required value={f.email} onChange={set('email')} />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input id="password" className="input" type="password" autoComplete="new-password" required aria-describedby="pw-hint" value={f.password} onChange={set('password')} />
          <span id="pw-hint" className="hint" style={tooShort ? { color: 'var(--danger)' } : undefined}>At least 8 characters.</span>
        </div>
        <button className="btn btn-primary btn-block" disabled={busy || !f.first_name || !f.last_name || !f.email || !f.password}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
        <p className="auth-switch">Already have an account? <Link to="/signin" state={{ from }}>Sign in</Link></p>
      </form>
    </AuthLayout>
  );
}

const CODE_LEN = 6;

/** After sign-up: type the 6-digit code we emailed. */
export function VerifyEmailPage() {
  const { user, setUser, signOut } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state)?.from ?? '/';
  const [digits, setDigits] = useState(Array(CODE_LEN).fill(''));
  const [info, setInfo] = useState(null);
  const [wait, setWait] = useState(0);
  const [notice, setNotice] = useState(null);
  const boxes = useRef([]);
  const code = digits.join('');

  useEffect(() => {
    api('/api/auth/verify').then((r) => {
      if (r.verified) { navigate(from, { replace: true }); return; }
      setInfo(r); setWait(r.resend_in);
    }).catch(() => {});
  }, [from, navigate]);
  useEffect(() => {
    if (wait <= 0) return;
    const t = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);

  const { error, busy, submit } = useSubmit(async () => {
    if (code.length < CODE_LEN) throw new Error('Type all 6 digits of the code.');
    const u = await api('/api/auth/verify', { method: 'POST', json: { code } });
    setUser(u);
    navigate(from, { replace: true });
  });
  const resend = useSubmit(async () => {
    setNotice(null);
    const r = await api('/api/auth/verify/resend', { method: 'POST' });
    setWait(r.resend_in); setDigits(Array(CODE_LEN).fill('')); boxes.current[0]?.focus();
    setNotice(`We sent a new code to ${info?.email ?? user?.email}. Codes work for 10 minutes.`);
  });

  const put = (i, value) => {
    const only = value.replace(/\D/g, '');
    if (!only) { setDigits((d) => d.map((x, j) => (j === i ? '' : x))); return; }
    setDigits((d) => {
      const next = [...d];
      for (let k = 0; k < only.length && i + k < CODE_LEN; k++) next[i + k] = only[k];
      return next;
    });
    boxes.current[Math.min(i + only.length, CODE_LEN - 1)]?.focus();
  };
  const onKey = (i, e) => {
    if (e.key === 'Backspace' && !digits[i] && i > 0) boxes.current[i - 1]?.focus();
    if (e.key === 'ArrowLeft' && i > 0) boxes.current[i - 1]?.focus();
    if (e.key === 'ArrowRight' && i < CODE_LEN - 1) boxes.current[i + 1]?.focus();
  };
  const onPaste = (e) => { e.preventDefault(); put(0, e.clipboardData.getData('text')); };

  return (
    <AuthLayout>
      <form className="auth-form" onSubmit={submit} noValidate>
        <header>
          <h1>Check your email</h1>
          <p className="muted">We sent a 6-digit code to <strong>{info?.email ?? user?.email}</strong>. Type it here to confirm your email. It works for 10 minutes.</p>
        </header>
        {info?.dev_outbox && (
          <div className="alert alert-info small">No mail server is set up on this computer, so emails aren't really sent. <Link to="/dev/outbox" target="_blank">Open the dev outbox</Link> to read the code.</div>
        )}
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        {resend.error && <div className="alert alert-error" role="alert">{resend.error}</div>}
        {notice && <div className="alert alert-success" role="status">{notice}</div>}
        <fieldset className="code-boxes">
          <legend className="sr-only">6-digit code</legend>
          {digits.map((d, i) => (
            <input key={i} ref={(el) => { boxes.current[i] = el; }} className="input code-box" inputMode="numeric" autoComplete={i === 0 ? 'one-time-code' : 'off'}
              aria-label={`Digit ${i + 1}`} maxLength={CODE_LEN} value={d} autoFocus={i === 0}
              onChange={(e) => put(i, e.target.value)} onKeyDown={(e) => onKey(i, e)} onPaste={onPaste} />
          ))}
        </fieldset>
        <button className="btn btn-primary btn-block" disabled={busy || code.length < CODE_LEN}>{busy ? 'Checking…' : 'Confirm email'}</button>
        <p className="auth-switch">
          Didn't get it? Check spam, or{' '}
          {wait > 0 ? <span className="muted">send a new code in {wait}s</span>
            : <button type="button" className="link-btn" disabled={resend.busy} onClick={(e) => resend.submit(e)}>{resend.busy ? 'sending…' : 'send a new code'}</button>}
          .
        </p>
        <p className="auth-switch small">Wrong email? <button type="button" className="link-btn" onClick={() => { signOut(); navigate('/create-account'); }}>Sign out and start again</button></p>
      </form>
    </AuthLayout>
  );
}

/** Forgot password: always the same answer, so the page doesn't reveal which emails have accounts. */
export function ForgotPasswordPage() {
  const start = (useLocation().state)?.email ?? '';
  const [email, setEmail] = useState(start);
  const [sent, setSent] = useState(null);
  const { error, busy, submit } = useSubmit(async () => {
    const r = await api('/api/auth/forgot', { method: 'POST', json: { email: email.trim() } });
    setSent(r.message);
  });
  return (
    <AuthLayout>
      <form className="auth-form" onSubmit={submit} noValidate>
        <header>
          <h1>Reset your password</h1>
          <p className="muted">Type the email you sign in with. We'll send you a link to choose a new password.</p>
        </header>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        {sent ? <div className="alert alert-success" role="status">{sent}</div> : (
          <>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input id="email" className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <button className="btn btn-primary btn-block" disabled={busy || !email.trim()}>{busy ? 'Sending…' : 'Send reset link'}</button>
          </>
        )}
        <p className="auth-switch"><Link to="/signin">Back to sign in</Link></p>
      </form>
    </AuthLayout>
  );
}

/** /reset-password?token=…: choose a new password. Signs out every other session. */
export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const { user, signOut } = useAuth();
  const [check, setCheck] = useState(null);
  const [pw, setPw] = useState('');
  const [again, setAgain] = useState('');
  const [done, setDone] = useState(null);
  useEffect(() => {
    if (!token) { setCheck({ problem: 'This reset link is incomplete. Open the link from the email again, or ask for a new one.' }); return; }
    api(`/api/auth/reset/${encodeURIComponent(token)}`).then((r) => setCheck({ email: r.email })).catch((e) => setCheck({ problem: e.message }));
  }, [token]);
  const { error, busy, submit } = useSubmit(async () => {
    if (pw.length < 8) throw new Error('Use at least 8 characters for your password.');
    if (pw !== again) throw new Error("The two passwords don't match.");
    const r = await api('/api/auth/reset', { method: 'POST', json: { token, password: pw } });
    if (user) signOut();
    setDone(r.message);
  });
  return (
    <AuthLayout>
      <form className="auth-form" onSubmit={submit} noValidate>
        <header>
          <h1>Choose a new password</h1>
          {check?.email && !done && <p className="muted">For <strong>{check.email}</strong>. You'll be signed out everywhere else.</p>}
        </header>
        {!check && <p className="muted">Checking the link…</p>}
        {check?.problem && <><div className="alert alert-error" role="alert">{check.problem}</div><p className="auth-switch"><Link to="/forgot-password">Send a new link</Link></p></>}
        {done && <><div className="alert alert-success" role="status">{done}</div><Link className="btn btn-primary btn-block" to="/signin">Sign in</Link></>}
        {check?.email && !done && (
          <>
            {error && <div className="alert alert-error" role="alert">{error}</div>}
            <div className="field">
              <label htmlFor="pw">New password</label>
              <input id="pw" className="input" type="password" autoComplete="new-password" required value={pw} onChange={(e) => setPw(e.target.value)} aria-describedby="pw-hint" />
              <span id="pw-hint" className="hint">At least 8 characters.</span>
            </div>
            <div className="field">
              <label htmlFor="pw2">Type it again</label>
              <input id="pw2" className="input" type="password" autoComplete="new-password" required value={again} onChange={(e) => setAgain(e.target.value)} />
            </div>
            <button className="btn btn-primary btn-block" disabled={busy || !pw || !again}>{busy ? 'Saving…' : 'Save new password'}</button>
          </>
        )}
      </form>
    </AuthLayout>
  );
}

/** Development only (no mail server): the emails nowBuilder would have sent. */
export function DevOutboxPage() {
  const [mails, setMails] = useState(null);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(0);
  const load = () => api('/api/auth/dev-outbox').then((r) => { setMails(r.emails); setError(null); })
    .catch(() => setError('The dev outbox is only there in development, when no mail server is set up.'));
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, []);
  return (
    <div className="outbox">
      <header className="outbox-head">
        <div><h1>Dev outbox</h1><p className="muted small">Emails nowBuilder would have sent. Only in development without a mail server; it refreshes by itself and clears when the backend restarts.</p></div>
      </header>
      {error && <div className="alert alert-error">{error}</div>}
      {mails && mails.length === 0 && <p className="muted">No emails yet.</p>}
      <ul className="outbox-list">
        {mails?.map((m, i) => (
          <li key={`${m.at}-${i}`} className="outbox-item">
            <button type="button" className="outbox-row" aria-expanded={open === i} onClick={() => setOpen(open === i ? null : i)}>
              <strong>{m.subject}</strong><span className="muted small">To {m.to}, {new Date(m.at).toLocaleTimeString()}</span>
            </button>
            {open === i && <iframe className="outbox-frame" title={m.subject} sandbox="" srcDoc={m.html} />}
          </li>
        ))}
      </ul>
    </div>
  );
}

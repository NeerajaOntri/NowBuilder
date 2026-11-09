import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../auth';
import { Icon } from '../components/Icon';
import { Wordmark } from '../components/Wordmark';
import { ROLE_INFO, wsApi } from '../workspaceApi';

/** /invite/:token: who invited you to which workspace, then join (signing in or creating an account first). */
export function InvitePage() {
  const { token = '' } = useParams();
  const { user, loading, signOut } = useAuth();
  const navigate = useNavigate();
  const [inv, setInv] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const here = `/invite/${token}`;

  useEffect(() => { wsApi.viewInvite(token).then(setInv).catch((e) => setError(e.message)); }, [token]);

  const accept = async () => {
    setBusy(true); setError(null);
    try { await wsApi.accept(token); navigate('/', { replace: true }); } catch (e) { setError(e.message); setBusy(false); }
  };
  const wrongUser = Boolean(user && inv && user.email.toLowerCase() !== inv.email.toLowerCase());

  return (
    <div className="invite-page">
      <Wordmark />
      <main className="invite-card" aria-live="polite">
        {!inv && !error && <p className="muted">Loading the invite…</p>}
        {!inv && error && <><h1>Invite not found</h1><p className="muted">{error}</p><Link className="btn" to="/">Go to nowBuilder</Link></>}
        {inv && (
          <>
            <span className="invite-ico"><Icon name="team" size={26} /></span>
            <h1>Join {inv.workspace}</h1>
            <p className="invite-lead"><strong>{inv.invited_by}</strong> invited <strong>{inv.email}</strong> to work in nowBuilder as a <strong>{inv.role_label}</strong>.</p>
            <p className="small muted">{ROLE_INFO[inv.role]}</p>
            {inv.problem ? <div className="alert alert-error" role="alert">{inv.problem}</div> : (
              <>
                {error && <div className="alert alert-error" role="alert">{error}</div>}
                {loading ? null : !user ? (
                  <div className="invite-actions">
                    {inv.has_account
                      ? <Link className="btn btn-primary btn-lg" to="/signin" state={{ from: here }}>Sign in to join</Link>
                      : <Link className="btn btn-primary btn-lg" to={`/create-account?email=${encodeURIComponent(inv.email)}`} state={{ from: here }}>Create your account</Link>}
                    {inv.has_account
                      ? <Link className="btn btn-lg" to={`/create-account?email=${encodeURIComponent(inv.email)}`} state={{ from: here }}>Create an account</Link>
                      : <Link className="btn btn-lg" to="/signin" state={{ from: here }}>I already have an account</Link>}
                  </div>
                ) : user.email_verified === false && !wrongUser ? (
                  <div className="invite-actions">
                    <Link className="btn btn-primary btn-lg" to="/verify-email" state={{ from: here }}>Confirm your email to join</Link>
                    <p className="small muted">We sent a 6-digit code to {user.email}.</p>
                  </div>
                ) : wrongUser ? (
                  <div className="alert alert-warn">
                    You're signed in as {user.email}. This invite is for {inv.email}.
                    <div className="invite-actions"><button type="button" className="btn btn-sm" onClick={signOut}>Sign out</button></div>
                  </div>
                ) : (
                  <div className="invite-actions">
                    <button type="button" className="btn btn-primary btn-lg" disabled={busy} onClick={accept}>{busy ? 'Joining…' : `Join ${inv.workspace}`}</button>
                    <p className="small muted">You'll leave your own workspace. One workspace per person for now.</p>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}

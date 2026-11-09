import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { AuthProvider, useAuth } from './auth';
import { AppShell } from './components/AppShell';
import { SignInPage, CreateAccountPage, DevOutboxPage, ForgotPasswordPage, ResetPasswordPage, VerifyEmailPage } from './pages/AuthPages';
import { HomePage } from './pages/HomePage';
import { PlatformPage } from './pages/PlatformPage';
import { AdminPage } from './pages/AdminPage';
import { InvitePage } from './pages/InvitePage';
import { StoriesPage } from './pages/StoriesPage';
import { GitHubSettingsPage, JiraSettingsPage } from './pages/IntegrationsPanel';
import { WorkspacePage } from './pages/WorkspacePage';
import { InstancesSettingsPage } from './pages/InstancesSettingsPage';
import { AISettingsPage } from './pages/AISettingsPage';
import { SettingsLayout } from './pages/SettingsLayout';
import './styles.css';

function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="page-loading" role="status">Loading your workspace…</div>;
  if (!user) return <Navigate to="/signin" replace state={{ from: location.pathname }} />;
  if (user.email_verified === false) return <Navigate to="/verify-email" replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}

/** Signed in but the email isn't confirmed yet. */
function NeedsVerification({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/signin" replace />;
  if (user.email_verified !== false) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function GuestOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? <Navigate to="/" replace /> : <>{children}</>;
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/signin" element={<GuestOnly><SignInPage /></GuestOnly>} />
          <Route path="/create-account" element={<GuestOnly><CreateAccountPage /></GuestOnly>} />
          <Route path="/invite/:token" element={<InvitePage />} />
          <Route path="/verify-email" element={<NeedsVerification><VerifyEmailPage /></NeedsVerification>} />
          <Route path="/forgot-password" element={<GuestOnly><ForgotPasswordPage /></GuestOnly>} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/dev/outbox" element={<DevOutboxPage />} />
          <Route element={<RequireAuth><AppShell /></RequireAuth>}>
            <Route index element={<HomePage />} />
            <Route path="admin" element={<AdminPage />} />
            <Route path="platform" element={<PlatformPage />} />
            <Route path="workspace" element={<WorkspacePage />} />
            <Route path="workspace/stories" element={<StoriesPage />} />
            <Route path="workspace/:chatId" element={<WorkspacePage />} />
            <Route path="settings" element={<SettingsLayout />}>
              <Route index element={<Navigate to="instances" replace />} />
              <Route path="instances" element={<InstancesSettingsPage />} />
              <Route path="ai-provider" element={<AISettingsPage />} />
              <Route path="jira" element={<JiraSettingsPage />} />
              <Route path="github" element={<GitHubSettingsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);

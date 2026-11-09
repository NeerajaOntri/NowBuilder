import { NavLink, Outlet } from 'react-router-dom';

export function SettingsLayout() {
  return (
    <div className="settings">
      <nav className="settings-nav" aria-label="Settings">
        <NavLink to="/settings/instances">ServiceNow instances</NavLink>
        <NavLink to="/settings/ai-provider">AI provider</NavLink>
        <NavLink to="/settings/jira">Jira</NavLink>
        <NavLink to="/settings/github">GitHub</NavLink>
      </nav>
      <section><Outlet /></section>
    </div>
  );
}

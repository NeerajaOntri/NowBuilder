import { api } from './api';

export const integrationsApi = {
  get: () => api('/api/integrations'),
  saveJira: (body) =>
    api('/api/integrations/jira', { method: 'PUT', json: body }),
  jiraProjects: () => api('/api/integrations/jira/projects'),
  saveGitHub: (body) =>
    api('/api/integrations/github', { method: 'PUT', json: body }),
  repos: () => api('/api/integrations/github/repos'),
  branches: (repo) => api(`/api/integrations/github/branches?repo=${encodeURIComponent(repo)}`),
  disconnect: (kind) => api(`/api/integrations/${kind}`, { method: 'DELETE' }),
};

export const jiraApi = {
  stories: (scope, open, q) =>
    api(`/api/jira/stories?scope=${scope}&open=${open}${q ? `&q=${encodeURIComponent(q)}` : ''}`),
  story: (key) => api(`/api/jira/stories/${encodeURIComponent(key)}`),
  build: (key, orgId, again = false) =>
    api(`/api/jira/stories/${encodeURIComponent(key)}/build`, { method: 'POST', json: { instance_id: orgId ?? null, again } }),
};

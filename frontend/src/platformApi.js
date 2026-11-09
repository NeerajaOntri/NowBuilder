import { api } from './api';

export const platformApi = {
  summary: () => api('/api/platform/summary'),
  remove: (id, confirm) => api(`/api/platform/workspaces/${id}`, { method: 'DELETE', json: { confirm } }),
  admins: () => api('/api/platform/admins'),
  addAdmin: (email) => api('/api/platform/admins', { method: 'POST', json: { email } }),
  removeAdmin: (email) => api(`/api/platform/admins/${encodeURIComponent(email)}`, { method: 'DELETE' }),
  list: () => api('/api/platform/workspaces'),
  update: (id, change) => api(`/api/platform/workspaces/${id}`, { method: 'PATCH', json: change }),
};

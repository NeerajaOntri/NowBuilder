import { api } from './api';

export const ROLE_LABEL = { owner: 'Owner', admin: 'Admin', developer: 'Developer', reviewer: 'Reviewer', viewer: 'Viewer' };
export const ROLE_INFO = {
  owner: 'Everything, including members, instances, the AI provider, Jira and GitHub. There is one owner.',
  admin: 'Manages members, instances, the AI provider, Jira and GitHub, and can do everything a Developer and Reviewer can.',
  developer: 'Builds (also from Jira stories), fixes and edits, approves, deploys into update sets, including on production, and pushes to GitHub.',
  reviewer: 'Reviews and approves changes. Doesn’t build, change or deploy them.',
  viewer: 'Reads chats and changes. Changes nothing.',
};
export const PERMISSION_LABEL = [
  ['read', 'See chats and changes'],
  ['build', 'Ask the AI, describe requirements, build, fix and edit changes'],
  ['approve', 'Select items and approve changes'],
  ['deploy', 'Deploy to development and test instances'],
  ['deploy_prod', 'Deploy to production instances'],
  ['push', 'Push approved changes to GitHub'],
  ['sync', 'Check instance connections'],
  ['manage_instances', 'Connect, update and remove ServiceNow instances'],
  ['manage_ai', 'Change the AI provider'],
  ['manage_members', 'Invite members and change their access'],
  ['manage_integrations', 'Connect Jira and GitHub'],
];

export const wsApi = {
  me: () => api('/api/workspace'),
  rename: (name) => api('/api/workspace', { method: 'PATCH', json: { name } }),
  members: () => api('/api/workspace/members'),
  invite: (email, role, instance_ids) =>
    api('/api/workspace/invites', { method: 'POST', json: { email, role, instance_ids } }),
  renew: (id) => api(`/api/workspace/invites/${id}/renew`, { method: 'POST' }),
  revoke: (id) => api(`/api/workspace/invites/${id}`, { method: 'DELETE' }),
  update: (id, body) =>
    api(`/api/workspace/members/${id}`, { method: 'PATCH', json: body }),
  remove: (id) => api(`/api/workspace/members/${id}`, { method: 'DELETE' }),
  viewInvite: (token) => api(`/api/invites/${token}`),
  accept: (token) => api(`/api/invites/${token}/accept`, { method: 'POST' }),
};

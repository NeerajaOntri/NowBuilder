import { ApiError, api, messageFrom, tokenStore } from './api';

export const chatApi = {
  list: () => api('/api/chats'),
  create: () => api('/api/chats', { method: 'POST' }),
  get: (id) => api(`/api/chats/${id}`),
  rename: (id, title) => api(`/api/chats/${id}`, { method: 'PATCH', json: { title } }),
  remove: (id) => api(`/api/chats/${id}`, { method: 'DELETE' }),
};

export const planApi = {
  get: (id) => api(`/api/plans/${id}`),
  check: (id) => api(`/api/plans/${id}/check`, { method: 'POST' }),
  edit: (id, componentId, body) => api(`/api/plans/${id}/components/${componentId}`, { method: 'PATCH', json: body }),
  applyFix: (id, fixId) => api(`/api/plans/${id}/fixes/${fixId}/apply`, { method: 'POST' }),
  rejectFix: (id, fixId) => api(`/api/plans/${id}/fixes/${fixId}/reject`, { method: 'POST' }),
  approve: (id, ids) => api(`/api/plans/${id}/approve`, { method: 'POST', json: { ids } }),
  unapprove: (id) => api(`/api/plans/${id}/unapprove`, { method: 'POST' }),
  push: (id, body) => api(`/api/plans/${id}/push`, { method: 'POST', json: body }),
  /** The ServiceNow SDK source for a flow design. Plain text, not JSON. */
  flowSource: async (id, componentId) => {
    const headers = new Headers();
    const token = tokenStore.get();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    let res;
    try {
      res = await fetch(`/api/plans/${id}/components/${componentId}/flow-source`, { headers });
    } catch {
      throw new ApiError(0, "Can't reach nowBuilder. Check your connection.");
    }
    const text = await res.text();
    if (!res.ok) {
      let detail = text;
      try { detail = JSON.parse(text)?.detail ?? text; } catch { /* plain text already */ }
      throw new ApiError(res.status, messageFrom({ detail }, res.status));
    }
    return text;
  },
};

/** POST and read a plan's Server-Sent Events (fix, deploy, rollback). Resolves when it ends. */
export async function planStream(path, body, onEvent, signal) {
  const headers = new Headers({ 'Content-Type': 'application/json' });
  const token = tokenStore.get();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  let res;
  try {
    res = await fetch(path, { method: 'POST', body: JSON.stringify(body ?? {}), headers, signal });
  } catch (e) {
    if (e.name === 'AbortError') return;
    throw new ApiError(0, "Can't reach nowBuilder. Check your connection.");
  }
  if (!res.ok || !res.body) throw await errorFrom(res);
  await readSse(res, onEvent);
}

async function readSse(res, onEvent) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf('\n\n')) >= 0) {
        const chunk = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const line = chunk.split('\n').find((l) => l.startsWith('data: '));
        if (line) onEvent(JSON.parse(line.slice(6)));
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') throw e;
  }
}

async function errorFrom(res) {
  const body = await res.json().catch(() => null);
  if (res.status === 502 || res.status === 504 || (res.status === 500 && body === null)) {
    return new ApiError(res.status, "Can't reach the nowBuilder backend. Make sure it's running (uvicorn app.main:app --reload).");
  }
  return new ApiError(res.status, messageFrom(body, res.status));
}

/** POST a message and read the Server-Sent Events stream. Resolves when the stream ends. */
export async function sendMessage(chatId, text, files, onEvent, signal, story = false) {
  const form = new FormData();
  form.append('text', text);
  if (story) form.append('story', 'true');
  files.forEach((f) => form.append('files', f));
  const headers = new Headers();
  const token = tokenStore.get();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  let res;
  try {
    res = await fetch(`/api/chats/${chatId}/messages`, { method: 'POST', body: form, headers, signal });
  } catch (e) {
    if (e.name === 'AbortError') return;
    throw new ApiError(0, "Can't reach nowBuilder. Check your connection.");
  }
  if (!res.ok || !res.body) throw await errorFrom(res);
  await readSse(res, onEvent);
}

const TOKEN_KEY = 'nowbuilder.token';

export const tokenStore = {
  get: () => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } },
  set: (t) => { try { localStorage.setItem(TOKEN_KEY, t); } catch { /* storage unavailable */ } },
  clear: () => { try { localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ } },
};

export class ApiError extends Error {
  /** `code` names a special case the UI treats differently (for example "pending" = workspace waiting for approval). */
  constructor(status, message, code) { super(message); this.status = status; this.code = code; }
}

export function messageFrom(body, status) {
  const detail = body?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) {
    const d = detail[0];
    const field = d.loc?.[d.loc.length - 1];
    return field ? `${field.replace(/_/g, ' ')}: ${d.msg}` : d.msg;
  }
  if (status >= 500) return `nowBuilder's server had a problem (error ${status}). Check the backend terminal for details.`;
  return `That request was rejected (error ${status}).`;
}

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

export async function api(path, init = {}) {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  let body = init.body;
  if (init.json !== undefined) { headers.set('Content-Type', 'application/json'); body = JSON.stringify(init.json); }
  let res;
  try {
    res = await fetch(path, { ...init, headers, body });
  } catch {
    throw new ApiError(0, "Can't reach nowBuilder. Check your connection.");
  }
  if (res.status === 204) return undefined;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized();
    throw new ApiError(res.status, messageFrom(data, res.status), data?.code);
  }
  return data;
}

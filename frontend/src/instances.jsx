import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, ApiError } from './api';

const Ctx = createContext(null);

/** Connected ServiceNow instances and AI provider status, shared by the top bar, home and settings. */
export function WorkspaceProvider({ children }) {
  const [instances, setInstances] = useState(null);
  const [ai, setAI] = useState(undefined);
  const [ws, setWs] = useState(null);
  const [blocked, setBlocked] = useState(null);
  const [blockedCode, setBlockedCode] = useState(undefined);
  const refresh = useCallback(async () => {
    const [o, a, w] = await Promise.all([api('/api/instances'), api('/api/settings/ai-provider'), api('/api/workspace')]);
    setInstances(o);
    setAI(a);
    setWs(w);
    setBlocked(null);
  }, []);
  useEffect(() => {
    refresh().catch((e) => {
      if (e instanceof ApiError && e.status === 403) { setBlocked(e.message); setBlockedCode(e.code); }
      setInstances([]); setAI(null);
    });
  }, [refresh]);
  const selected = instances?.find((o) => o.is_selected) ?? null;
  const can = useCallback((p) => Boolean(ws?.me.permissions.includes(p)), [ws]);
  return <Ctx.Provider value={{ instances, ai, selected, refresh, setInstances, setAI, ws, can, blocked, blockedCode }}>{children}</Ctx.Provider>;
}

export function useWorkspace() {
  const c = useContext(Ctx);
  if (!c) throw new Error('useWorkspace must be used inside WorkspaceProvider');
  return c;
}

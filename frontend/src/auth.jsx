import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, setUnauthorizedHandler, tokenStore } from './api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(tokenStore.get()));

  const signOut = useCallback(() => { tokenStore.clear(); setUser(null); }, []);

  useEffect(() => {
    setUnauthorizedHandler(signOut);
    if (!tokenStore.get()) return;
    api('/api/auth/me').then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, [signOut]);

  const finish = (r) => { tokenStore.set(r.access_token); setUser(r.user); return r.user; };

  const value = useMemo(() => ({
    user, loading, signOut, setUser,
    signIn: async (email, password) => { finish(await api('/api/auth/login', { method: 'POST', json: { email, password } })); },
    register: async (data) => finish(await api('/api/auth/register', { method: 'POST', json: data })),
  }), [user, loading, signOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}

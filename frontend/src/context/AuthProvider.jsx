import { useCallback, useEffect, useState } from 'react';
import { authApi } from '../services/auth';
import { setOnUnauthorized, tokenStore } from '../services/apiClient';
import { AuthContext } from './auth-context';

// Tracks the authenticated user (with role) and exposes login/logout. The token
// lives in the apiClient's tokenStore; this provider keeps the user in sync and
// reacts to forced logouts (refresh failure) via setOnUnauthorized.
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // Only "loading" if there's a token to validate on mount.
  const [loading, setLoading] = useState(() => !!tokenStore.access);

  // Re-fetch the current user (e.g. after a profile change).
  const refreshUser = useCallback(async () => {
    try {
      setUser(await authApi.me());
    } catch {
      tokenStore.clear();
      setUser(null);
    }
  }, []);

  useEffect(() => {
    setOnUnauthorized(() => setUser(null));
    if (!tokenStore.access) return undefined;
    let active = true;
    (async () => {
      try {
        const me = await authApi.me();
        if (active) setUser(me);
      } catch {
        tokenStore.clear();
        if (active) setUser(null);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const login = async (email, password) => {
    const data = await authApi.login(email, password);
    tokenStore.set(data);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Drop the local session regardless of the network call's outcome.
    }
    tokenStore.clear();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, reload: refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

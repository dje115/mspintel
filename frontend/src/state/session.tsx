/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import type { MeResponse } from "../api/types";

type SessionState = {
  accessToken: string | null;
  refreshToken: string | null;
  me: MeResponse | null;
  currentTenantId: string | null;
  loading: boolean;
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  setCurrentTenantId: (tenantId: string) => void;
  refreshMe: () => Promise<void>;
};

const SessionContext = createContext<SessionState | undefined>(undefined);

const ACCESS_KEY = "mspintel_access_token";
const REFRESH_KEY = "mspintel_refresh_token";
const TENANT_KEY = "mspintel_tenant_id";

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(() => localStorage.getItem(ACCESS_KEY));
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem(REFRESH_KEY));
  const [currentTenantId, setCurrentTenantIdState] = useState<string | null>(() =>
    localStorage.getItem(TENANT_KEY)
  );
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(TENANT_KEY);
    setAccessToken(null);
    setRefreshToken(null);
    setCurrentTenantIdState(null);
    setMe(null);
  }, []);

  const refreshMe = useCallback(async () => {
    if (!accessToken) {
      setLoading(false);
      return;
    }

    try {
      const data = await api.me(accessToken, currentTenantId ?? undefined);
      setMe(data);
      if (!currentTenantId && data.memberships[0]) {
        setCurrentTenantIdState(data.memberships[0].tenant_id);
        localStorage.setItem(TENANT_KEY, data.memberships[0].tenant_id);
      }
    } catch {
      if (!refreshToken) {
        clearSession();
        setLoading(false);
        return;
      }

      try {
        const rotated = await api.refresh(refreshToken);
        localStorage.setItem(ACCESS_KEY, rotated.access_token);
        localStorage.setItem(REFRESH_KEY, rotated.refresh_token);
        setAccessToken(rotated.access_token);
        setRefreshToken(rotated.refresh_token);
        const data = await api.me(rotated.access_token, currentTenantId ?? undefined);
        setMe(data);
      } catch {
        clearSession();
      }
    } finally {
      setLoading(false);
    }
  }, [accessToken, refreshToken, currentTenantId, clearSession]);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const login = useCallback(
    async (nextAccessToken: string, nextRefreshToken: string) => {
      localStorage.setItem(ACCESS_KEY, nextAccessToken);
      localStorage.setItem(REFRESH_KEY, nextRefreshToken);
      setAccessToken(nextAccessToken);
      setRefreshToken(nextRefreshToken);
      setLoading(true);
      await refreshMe();
    },
    [refreshMe]
  );

  const logout = useCallback(async () => {
    if (refreshToken) {
      try {
        await api.logout(refreshToken);
      } catch {
        // local cleanup still happens
      }
    }
    clearSession();
  }, [refreshToken, clearSession]);

  const logoutAll = useCallback(async () => {
    if (accessToken && currentTenantId) {
      try {
        await api.logoutAll(accessToken, currentTenantId);
      } catch {
        // local cleanup still happens
      }
    }
    clearSession();
  }, [accessToken, currentTenantId, clearSession]);

  const setCurrentTenantId = useCallback((tenantId: string) => {
    localStorage.setItem(TENANT_KEY, tenantId);
    setCurrentTenantIdState(tenantId);
    setLoading(true);
  }, []);

  const value = useMemo(
    () => ({
      accessToken,
      refreshToken,
      me,
      currentTenantId,
      loading,
      login,
      logout,
      logoutAll,
      setCurrentTenantId,
      refreshMe
    }),
    [accessToken, refreshToken, me, currentTenantId, loading, login, logout, logoutAll, setCurrentTenantId, refreshMe]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used inside SessionProvider");
  return ctx;
}

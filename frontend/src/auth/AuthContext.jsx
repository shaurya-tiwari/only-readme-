import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { authApi } from "../api/auth";
import { clearStoredSession, readStoredSession, writeStoredSession } from "./session";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => readStoredSession());
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    let active = true;

    async function restore() {
      const stored = readStoredSession();
      if (!stored?.token) {
        if (active) {
          setBooting(false);
        }
        return;
      }

      try {
        const response = await authApi.me();
        if (!active) {
          return;
        }
        const next = { token: stored.token, session: response.data.session };
        setSession(next);
        writeStoredSession(next);
      } catch {
        clearStoredSession();
        if (active) {
          setSession(null);
        }
      } finally {
        if (active) {
          setBooting(false);
        }
      }
    }

    restore();
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo(
    () => ({
      booting,
      session,
      isAuthenticated: Boolean(session?.token),
      role: session?.session?.role || null,
      async loginWorker(phone) {
        const response = await authApi.workerLogin({ phone });
        const next = response.data;
        setSession(next);
        writeStoredSession(next);
        return next;
      },
      async loginAdmin(username, password) {
        const response = await authApi.adminLogin({ username, password });
        const next = response.data;
        setSession(next);
        writeStoredSession(next);
        return next;
      },
      async logout() {
        try {
          await authApi.logout();
        } catch {
          // client clear is sufficient
        }
        clearStoredSession();
        setSession(null);
      },
    }),
    [booting, session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, setToken } from "./api";
import type { BD } from "./types";

interface AuthContextValue {
  bd: BD | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [bd, setBd] = useState<BD | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!window.localStorage.getItem("applytics_token")) {
      setLoading(false);
      return;
    }
    api.bds
      .me()
      .then(setBd)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await api.auth.login(email, password);
    setToken(access_token);
    setBd(await api.bds.me());
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      await api.auth.register(email, password, fullName);
      await login(email, password);
    },
    [login]
  );

  const logout = useCallback(() => {
    setToken(null);
    setBd(null);
  }, []);

  return <AuthContext.Provider value={{ bd, loading, login, register, logout }}>{children}</AuthContext.Provider>;
}

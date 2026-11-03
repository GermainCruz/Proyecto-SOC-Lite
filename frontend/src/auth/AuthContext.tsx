import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, tokenStore } from "../api/client";
import type { TokenPair, User } from "../api/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  can: (permission: string) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadProfile = useCallback(async () => {
    try {
      const { data } = await api.get<User>("/auth/me");
      setUser(data);
    } catch {
      tokenStore.clear();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tokenStore.access()) {
      void loadProfile();
    } else {
      setLoading(false);
    }
    const onLogout = () => setUser(null);
    window.addEventListener("soclite:logout", onLogout);
    return () => window.removeEventListener("soclite:logout", onLogout);
  }, [loadProfile]);

  const login = useCallback(
    async (email: string, password: string) => {
      const { data } = await api.post<TokenPair>("/auth/login", { email, password });
      tokenStore.save(data);
      await loadProfile();
    },
    [loadProfile],
  );

  const logout = useCallback(async () => {
    const refresh = tokenStore.refresh();
    try {
      if (refresh) await api.post("/auth/logout", { refresh_token: refresh });
    } catch {
      // el cierre local es suficiente si el token ya expiró
    } finally {
      tokenStore.clear();
      setUser(null);
    }
  }, []);

  const can = useCallback(
    (permission: string) => Boolean(user?.permissions.includes(permission)),
    [user],
  );

  const value = useMemo(
    () => ({ user, loading, login, logout, can }),
    [user, loading, login, logout, can],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return context;
}

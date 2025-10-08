/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";
import { apiFetch } from "./api";

export type UserRole = "viewer" | "editor" | "pm" | "admin" | "owner";

export interface SessionUser {
  id: string;
  email: string;
  name?: string;
  role: UserRole;
  accountId: string | null;
  needsAccountSetup: boolean;
}

export interface SessionState {
  status: "loading" | "authenticated" | "unauthenticated";
  user: SessionUser | null;
  error?: string;
  refresh: () => Promise<void>;
}

const SessionContext = createContext<SessionState | undefined>(undefined);

const initialState: SessionState = {
  status: "loading",
  user: null,
  refresh: async () => undefined,
};

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>(initialState);

  const loadSession = useCallback(async () => {
    setState((current) => ({ ...current, status: "loading", error: undefined }));
    try {
      const apiUser = await apiFetch<{ [key: string]: unknown }>("/api/me");
      const normalizedUser = mapToSessionUser(apiUser);
      setState({ status: "authenticated", user: normalizedUser, refresh: loadSession });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Erro ao carregar sessão";
      setState({ status: "unauthenticated", user: null, error: message, refresh: loadSession });
    }
  }, []);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  const value = useMemo(() => ({ ...state, refresh: loadSession }), [state, loadSession]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession precisa ser usado dentro de SessionProvider");
  }
  return context;
}

export function useRequireRole(roles: UserRole[]) {
  const { user, status } = useSession();
  if (status !== "authenticated") {
    return false;
  }
  if (!roles.length) {
    return true;
  }
  return user ? roles.includes(user.role) : false;
}

export function mapToSessionUser(data: { [key: string]: unknown }): SessionUser {
  return {
    id: String(data.id ?? ""),
    email: String(data.email ?? ""),
    name: typeof data.name === "string" ? data.name : undefined,
    role: (data.role as UserRole) ?? "viewer",
    accountId: (data.account_id as string | null | undefined) ?? null,
    needsAccountSetup: Boolean(data.needs_account_setup),
  };
}

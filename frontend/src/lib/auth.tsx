import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError } from "../api/client";
import type { Me, Papel } from "../api/types";

interface AuthState {
  me: Me | null;
  carregando: boolean;
  sair: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({ me: null, carregando: true, sair: async () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    api<Me>("/auth/me")
      .then(setMe)
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 401)) console.error(e);
        setMe(null);
      })
      .finally(() => setCarregando(false));
  }, []);

  const sair = useCallback(async () => {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    setMe(null);
  }, []);

  return <AuthContext.Provider value={{ me, carregando, sair }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

// Espelha as regras do backend apenas para esconder ações; a API é a autoridade.
export const pode = {
  gerirClientes: (p?: Papel) => p === "admin" || p === "gestor",
  gerirUsuarios: (p?: Papel) => p === "admin",
  verUsuarios: (p?: Papel) => p === "admin" || p === "gestor",
  editar: (p?: Papel) => p === "admin" || p === "gestor" || p === "analista",
  auditoria: (p?: Papel) => p === "admin" || p === "gestor",
};

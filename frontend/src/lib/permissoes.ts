import type { Papel } from "@/lib/format";

// Espelha as regras do backend apenas para esconder ações; a API é a autoridade.
export const pode = {
  gerirClientes: (p?: Papel) => p === "admin" || p === "gestor",
  gerirUsuarios: (p?: Papel) => p === "admin",
  verUsuarios: (p?: Papel) => p === "admin",
  editar: (p?: Papel) => p === "admin" || p === "gestor" || p === "analista",
  auditoria: (p?: Papel) => p === "admin" || p === "gestor",
};

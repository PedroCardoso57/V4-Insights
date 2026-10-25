"use client";

import { useState } from "react";

import { useIntegracoes, type Integracao } from "@/features/integracoes/api";
import { horasDesde } from "@/lib/format";

export const STATUS_INTEGRACAO: Record<
  Integracao["status"],
  { label: string; variant: "success" | "warning" | "secondary" | "destructive" }
> = {
  conectada: { label: "conectada", variant: "success" },
  pendente: { label: "aguardando contas", variant: "warning" },
  pausada: { label: "pausada", variant: "secondary" },
  erro: { label: "requer reconexão", variant: "destructive" },
  revogada: { label: "revogada", variant: "secondary" },
};

export type MotivoAlerta = "reconexao" | "aguardando_contas" | "desatualizada";

export const MOTIVO_LABEL: Record<MotivoAlerta, string> = {
  reconexao: "requer reconexão",
  aguardando_contas: "aguardando contas",
  desatualizada: "desatualizada",
};

export function motivoAlerta(i: Integracao, agora: number): MotivoAlerta | null {
  if (i.status === "erro") return "reconexao";
  if (i.status === "pendente") return "aguardando_contas";
  const h = horasDesde(i.ultima_sincronizacao_em, agora);
  if (i.status === "conectada" && (h === null || h > 24)) return "desatualizada";
  return null;
}

/** Integrações que precisam de atenção (erro, sem contas ou sem sincronizar há mais de 24h). */
export function useAlertasIntegracao() {
  const q = useIntegracoes();
  const [agora] = useState(() => Date.now());
  const alertas = (q.data?.items ?? []).flatMap((i) => {
    const motivo = motivoAlerta(i, agora);
    return motivo ? [{ integracao: i, motivo }] : [];
  });
  return { query: q, alertas, agora };
}

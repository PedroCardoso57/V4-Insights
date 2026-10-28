"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap, type Schemas } from "@/services/api/client";

export type GrupoChaves = Schemas["GrupoChavesOut"];

const chave = ["configuracoes", "chaves"] as const;

export function useChaves(enabled = true) {
  return useQuery({
    queryKey: chave,
    queryFn: () => unwrap(api.GET("/api/v1/configuracoes/chaves")),
    enabled,
  });
}

/** Grava as chaves informadas; valor vazio remove a cadastrada (volta a valer o `.env`). */
export function useSalvarChaves() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (valores: Record<string, string | null>) =>
      unwrap(api.PUT("/api/v1/configuracoes/chaves", { body: { valores } })),
    onSuccess: (dados) => qc.setQueryData(chave, dados),
  });
}

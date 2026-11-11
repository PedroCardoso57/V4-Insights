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

export type VersaoApi = Schemas["VersaoApiOut"];

/** Versões das APIs das plataformas e quando são desligadas (só o responsável pelas chaves). */
export function useVersoesApi(enabled = true) {
  return useQuery({
    queryKey: ["configuracoes", "versoes-api"],
    queryFn: () => unwrap(api.GET("/api/v1/configuracoes/versoes-api")),
    enabled,
    staleTime: 60 * 60_000,
  });
}

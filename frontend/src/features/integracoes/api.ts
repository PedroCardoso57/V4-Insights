"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useMe } from "@/hooks/use-me";
import type { Plataforma } from "@/lib/format";
import { pode } from "@/lib/permissoes";
import { api, unwrap, type Schemas } from "@/services/api/client";

export type Integracao = Schemas["IntegracaoOut"];

export function useIntegracoes(clienteId?: string | null) {
  const papel = useMe().data?.papel;
  return useQuery({
    queryKey: ["integracoes", clienteId ?? "todas"],
    queryFn: () =>
      unwrap(api.GET("/api/v1/integracoes", { params: { query: { cliente_id: clienteId ?? undefined, page_size: 100 } } })),
    // Visualizador não tem acesso a integrações (SPEC-01).
    enabled: pode.editar(papel),
  });
}

export function useContasDisponiveis(integracaoId: string | null) {
  return useQuery({
    queryKey: ["integracoes", integracaoId, "contas"],
    queryFn: () => unwrap(api.GET("/api/v1/integracoes/{integracao_id}/contas", { params: { path: { integracao_id: integracaoId! } } })),
    enabled: !!integracaoId,
    staleTime: 0,
  });
}

export function useJobs(integracaoId: string | null, page = 1) {
  return useQuery({
    queryKey: ["integracoes", integracaoId, "jobs", page],
    queryFn: () =>
      unwrap(api.GET("/api/v1/integracoes/{integracao_id}/jobs", { params: { path: { integracao_id: integracaoId! }, query: { page, page_size: 20 } } })),
    enabled: !!integracaoId,
    refetchInterval: (q) => (q.state.data?.items.some((j) => j.status === "pendente" || j.status === "executando") ? 5000 : false),
  });
}

function useInvalida() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["integracoes"] });
}

export function useAutorizar() {
  return useMutation({
    mutationFn: ({ plataforma, clienteId, integracaoId }: { plataforma: Plataforma; clienteId: string; integracaoId?: string }) =>
      unwrap(
        api.POST("/api/v1/integracoes/{plataforma}/autorizar", {
          params: { path: { plataforma } },
          body: { cliente_id: clienteId, integracao_id: integracaoId ?? null },
        }),
      ),
    onSuccess: (r) => window.location.assign(r.authorization_url),
  });
}

export function useSelecionarContas() {
  const invalida = useInvalida();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Schemas["SelecionarContasIn"] }) =>
      unwrap(api.POST("/api/v1/integracoes/{integracao_id}/contas", { params: { path: { integracao_id: id } }, body })),
    onSuccess: invalida,
  });
}

export function useAcaoIntegracao() {
  const invalida = useInvalida();
  return useMutation({
    mutationFn: ({ id, acao }: { id: string; acao: "sincronizar" | "pausar" | "retomar" | "revogar" }): Promise<unknown> => {
      const params = { path: { integracao_id: id } };
      switch (acao) {
        case "sincronizar":
          return unwrap(api.POST("/api/v1/integracoes/{integracao_id}/sincronizar", { params, body: {} }));
        case "pausar":
          return unwrap(api.POST("/api/v1/integracoes/{integracao_id}/pausar", { params }));
        case "retomar":
          return unwrap(api.POST("/api/v1/integracoes/{integracao_id}/retomar", { params }));
        case "revogar":
          return unwrap(api.POST("/api/v1/integracoes/{integracao_id}/revogar", { params }));
      }
    },
    onSuccess: invalida,
  });
}

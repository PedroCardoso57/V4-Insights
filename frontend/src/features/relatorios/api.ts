"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { API_BASE, api, unwrap, type Schemas } from "@/services/api/client";

export type Relatorio = Schemas["RelatorioOut"];
export type Configuracao = Schemas["ConfiguracaoRelatorio"];
export type Execucao = Schemas["ExecucaoOut"];

export function useRelatorios(f: { cliente_id?: string; search?: string; page: number }) {
  return useQuery({
    queryKey: ["relatorios", f],
    queryFn: () => unwrap(api.GET("/api/v1/relatorios", { params: { query: { ...f, page_size: 20 } } })),
    placeholderData: keepPreviousData,
  });
}

export function useRelatorio(id: string | null) {
  return useQuery({
    queryKey: ["relatorios", "um", id],
    queryFn: () => unwrap(api.GET("/api/v1/relatorios/{relatorio_id}", { params: { path: { relatorio_id: id! } } })),
    enabled: !!id,
  });
}

export function useExecucoes(id: string | null) {
  return useQuery({
    queryKey: ["relatorios", id, "execucoes"],
    queryFn: () =>
      unwrap(api.GET("/api/v1/relatorios/{relatorio_id}/execucoes", { params: { path: { relatorio_id: id! }, query: { page_size: 20 } } })),
    enabled: !!id,
    // Acompanha o progresso enquanto houver PDF em geração.
    refetchInterval: (q) => (q.state.data?.items.some((e) => e.status === "pendente" || e.status === "processando") ? 3000 : false),
  });
}

export function useSalvarRelatorio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, clienteId, titulo, configuracao }: { id?: string; clienteId: string; titulo: string; configuracao: Configuracao }) =>
      id
        ? unwrap(api.PATCH("/api/v1/relatorios/{relatorio_id}", { params: { path: { relatorio_id: id } }, body: { titulo, configuracao } }))
        : unwrap(api.POST("/api/v1/relatorios", { body: { cliente_id: clienteId, titulo, configuracao } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["relatorios"] }),
  });
}

export function useExcluirRelatorio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => unwrap(api.DELETE("/api/v1/relatorios/{relatorio_id}", { params: { path: { relatorio_id: id } } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["relatorios"] }),
  });
}

export function useGerarPdf() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, chave }: { id: string; chave: string }) =>
      unwrap(api.POST("/api/v1/relatorios/{relatorio_id}/gerar", { params: { path: { relatorio_id: id }, header: { "idempotency-key": chave } } })),
    onSuccess: (_r, v) => qc.invalidateQueries({ queryKey: ["relatorios", v.id, "execucoes"] }),
  });
}

/** O download é um link autenticado pelo cookie de sessão (sem URL pública). */
export const urlDownload = (e: Execucao) => (e.download_url ? `${API_BASE}${e.download_url}` : null);

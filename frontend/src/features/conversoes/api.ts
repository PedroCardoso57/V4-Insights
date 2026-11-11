"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap, type Schemas } from "@/services/api/client";

export type ConversoesConta = Schemas["ConversoesContaOut"];
export type Mapeamento = Schemas["MapeamentoConversoes"];

export function useConversoes(clienteId: string) {
  return useQuery({
    queryKey: ["conversoes", clienteId],
    queryFn: () => unwrap(api.GET("/api/v1/clientes/{cliente_id}/conversoes", { params: { path: { cliente_id: clienteId } } })),
  });
}

/** Salva o mapeamento de uma conta; o histórico é recalculado no servidor. */
export function useSalvarConversoes(clienteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ contaId, mapeamento }: { contaId: string; mapeamento: Mapeamento }) =>
      unwrap(
        api.PUT("/api/v1/clientes/{cliente_id}/conversoes/{conta_anuncio_id}", {
          params: { path: { cliente_id: clienteId, conta_anuncio_id: contaId } },
          body: mapeamento,
        }),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conversoes", clienteId] });
      qc.invalidateQueries({ queryKey: ["metricas", clienteId] });
      qc.invalidateQueries({ queryKey: ["integracoes"] });
    },
  });
}

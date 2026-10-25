"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap, type Schemas } from "@/services/api/client";

export type Cliente = Schemas["ClienteOut"];
export type FiltroClientes = {
  search?: string;
  status?: "ativo" | "inativo" | "arquivado";
  page?: number;
  page_size?: number;
  order_by?: "nome" | "criado_em" | "atualizado_em";
  order?: "asc" | "desc";
};

export const clientesKeys = {
  all: ["clientes"] as const,
  lista: (f: FiltroClientes) => ["clientes", "lista", f] as const,
  um: (id: string) => ["clientes", id] as const,
  equipe: (id: string) => ["clientes", id, "equipe"] as const,
};

export function useClientes(f: FiltroClientes) {
  return useQuery({
    queryKey: clientesKeys.lista(f),
    queryFn: () => unwrap(api.GET("/api/v1/clientes", { params: { query: f } })),
    placeholderData: keepPreviousData,
  });
}

export function useCliente(id: string | null | undefined) {
  return useQuery({
    queryKey: clientesKeys.um(id ?? ""),
    queryFn: () => unwrap(api.GET("/api/v1/clientes/{cliente_id}", { params: { path: { cliente_id: id! } } })),
    enabled: !!id,
  });
}

export function useEquipe(id: string) {
  return useQuery({
    queryKey: clientesKeys.equipe(id),
    queryFn: () => unwrap(api.GET("/api/v1/clientes/{cliente_id}/usuarios", { params: { path: { cliente_id: id } } })),
  });
}

export function useSalvarCliente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id?: string; body: Schemas["ClienteCreate"] }) =>
      id
        ? unwrap(api.PATCH("/api/v1/clientes/{cliente_id}", { params: { path: { cliente_id: id } }, body }))
        : unwrap(api.POST("/api/v1/clientes", { body })),
    onSuccess: () => qc.invalidateQueries({ queryKey: clientesKeys.all }),
  });
}

export function useArquivarCliente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => unwrap(api.POST("/api/v1/clientes/{cliente_id}/arquivar", { params: { path: { cliente_id: id } } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: clientesKeys.all }),
  });
}

export function useAcessoCliente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ usuarioId, clienteId, remover }: { usuarioId: string; clienteId: string; remover?: boolean }) => {
      const params = { path: { usuario_id: usuarioId, cliente_id: clienteId } };
      return remover
        ? unwrap(api.DELETE("/api/v1/usuarios/{usuario_id}/clientes/{cliente_id}", { params }))
        : unwrap(api.PUT("/api/v1/usuarios/{usuario_id}/clientes/{cliente_id}", { params }));
    },
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: clientesKeys.equipe(v.clienteId) }),
  });
}

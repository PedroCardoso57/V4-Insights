"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap, type Schemas } from "@/services/api/client";

export type Usuario = Schemas["UsuarioOut"];

export function useUsuarios(f: { search?: string; page?: number; ativo?: boolean; page_size?: number }, enabled = true) {
  return useQuery({
    queryKey: ["usuarios", f],
    queryFn: () => unwrap(api.GET("/api/v1/usuarios", { params: { query: { page_size: 50, ...f } } })),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useSalvarUsuario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id?: string; nome: string; email: string; papel: Schemas["Papel"]; ativo: boolean }) =>
      v.id
        ? unwrap(api.PATCH("/api/v1/usuarios/{usuario_id}", { params: { path: { usuario_id: v.id } }, body: { nome: v.nome, papel: v.papel, ativo: v.ativo } }))
        : unwrap(api.POST("/api/v1/usuarios", { body: { nome: v.nome, email: v.email, papel: v.papel, ativo: true } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["usuarios"] }),
  });
}

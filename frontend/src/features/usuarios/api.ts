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

/** Exclui o colaborador: perde o acesso e tem os dados pessoais anonimizados (irreversível). */
export function useExcluirUsuario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => unwrap(api.DELETE("/api/v1/usuarios/{usuario_id}", { params: { path: { usuario_id: id } } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["usuarios"] }),
  });
}

export const FOTO_TIPOS = ["image/jpeg", "image/png", "image/webp"] as const;
export const FOTO_MAX_BYTES = 8 * 1024 * 1024;

function aposTrocarFoto(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["me"] });
  qc.invalidateQueries({ queryKey: ["usuarios"] });
}

/** Envia a imagem crua; a API corta, reduz para 256x256 e remove metadados. */
export function useEnviarFoto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, arquivo }: { id: string; arquivo: File }) =>
      unwrap(
        api.PUT("/api/v1/usuarios/{usuario_id}/foto", {
          params: { path: { usuario_id: id } },
          body: arquivo as unknown as string,
          bodySerializer: (b) => b as unknown as BodyInit,
          headers: { "Content-Type": arquivo.type },
        }),
      ),
    onSuccess: () => aposTrocarFoto(qc),
  });
}

export function useRemoverFoto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => unwrap(api.DELETE("/api/v1/usuarios/{usuario_id}/foto", { params: { path: { usuario_id: id } } })),
    onSuccess: () => aposTrocarFoto(qc),
  });
}

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/services/api/client";

export function useLoginSenha() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; senha: string; manter_conectado: boolean }) =>
      unwrap(api.POST("/api/v1/auth/login", { body })),
    onSuccess: () => qc.removeQueries(),
  });
}

export function useTrocarSenha() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { senha_atual?: string; nova_senha: string }) => unwrap(api.PUT("/api/v1/auth/senha", { body })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useSenhaUsuario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, nova_senha }: { id: string; nova_senha: string | null }) =>
      nova_senha === null
        ? unwrap(api.DELETE("/api/v1/usuarios/{usuario_id}/senha", { params: { path: { usuario_id: id } } }))
        : unwrap(api.PUT("/api/v1/usuarios/{usuario_id}/senha", { params: { path: { usuario_id: id } }, body: { nova_senha } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["usuarios"] }),
  });
}

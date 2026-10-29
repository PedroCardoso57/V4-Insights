"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { consultaMe } from "@/hooks/use-me";
import { api, unwrap, type Schemas } from "@/services/api/client";

/**
 * Marca o tutorial de primeiro acesso como visto (concluído ou pulado) ou o reabre.
 *
 * A sessão em cache é atualizada na hora: é ela que decide se o tour aparece, então
 * "Rever tutorial" abre o tour sem esperar a API, e pular não o faz piscar de volta.
 */
export function useMarcarTutorial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (visto: boolean) => unwrap(api.PUT("/api/v1/auth/tutorial", { body: { visto } })),
    onMutate: (visto) => {
      qc.setQueryData<Schemas["MeOut"]>(consultaMe.queryKey, (me) => (me ? { ...me, tutorial_visto: visto } : me));
    },
  });
}

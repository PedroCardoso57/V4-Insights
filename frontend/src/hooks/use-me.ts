"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { api, unwrap, type Schemas } from "@/services/api/client";

/** Consulta da sessão; também usada para pré-carregar o usuário logo após o login. */
export const consultaMe = {
  queryKey: ["me"],
  queryFn: (): Promise<Schemas["MeOut"]> => unwrap(api.GET("/api/v1/auth/me")),
  staleTime: 5 * 60_000,
};

export function useMe() {
  return useQuery<Schemas["MeOut"]>(consultaMe);
}

export function useLogout() {
  const qc = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/logout")),
    onSettled: () => {
      qc.clear();
      router.replace("/login");
    },
  });
}

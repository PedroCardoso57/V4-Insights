"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { useLocalStorage } from "./use-local-storage";

/** Cliente em foco: rota /clientes/[id], ?cliente_id= ou última escolha do usuário. */
export function useClienteAtual(): [string | null, (id: string | null) => void] {
  const params = useParams<{ id?: string }>();
  const search = useSearchParams();
  const daRota = (params?.id as string | undefined) ?? search.get("cliente_id");
  const [salvo, setSalvo] = useLocalStorage("v4:cliente-atual");

  useEffect(() => {
    if (daRota && daRota !== salvo) setSalvo(daRota); // sincroniza o sistema externo (storage)
  }, [daRota, salvo, setSalvo]);

  return [daRota ?? salvo, setSalvo];
}

"use client";

import { useIsFetching, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2Icon, LoaderCircleIcon } from "lucide-react";

/** Estado de atualização dos dados exibidos (requisições em andamento). */
export function StatusAtualizacao() {
  const buscando = useIsFetching() > 0; // re-renderiza ao iniciar/terminar requisições
  const cache = useQueryClient().getQueryCache();
  const ts = Math.max(0, ...cache.getAll().map((q) => q.state.dataUpdatedAt));
  const ultima = ts ? new Date(ts) : null;
  return (
    <span className="hidden items-center gap-1.5 text-xs text-muted-foreground md:inline-flex" role="status" aria-live="polite">
      {buscando ? (
        <>
          <LoaderCircleIcon className="size-3.5 animate-spin" /> Atualizando…
        </>
      ) : ultima ? (
        <>
          <CheckCircle2Icon className="size-3.5 text-success" /> Atualizado às{" "}
          {ultima.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
        </>
      ) : null}
    </span>
  );
}

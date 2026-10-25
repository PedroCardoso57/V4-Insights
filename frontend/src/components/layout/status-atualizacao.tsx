"use client";

import { useIsFetching, useQueryClient } from "@tanstack/react-query";
import { LoaderCircleIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/** Estado de atualização dos dados exibidos (requisições em andamento). */
export function StatusAtualizacao() {
  const buscando = useIsFetching() > 0; // re-renderiza ao iniciar/terminar requisições
  const cache = useQueryClient().getQueryCache();
  const ts = Math.max(0, ...cache.getAll().map((q) => q.state.dataUpdatedAt));
  const ultima = ts ? new Date(ts) : null;
  if (!buscando && !ultima) return null;
  return (
    <span
      className={cn(
        "hidden items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium xl:inline-flex",
        buscando ? "bg-subtle text-muted-foreground" : "bg-success-soft text-success",
      )}
      role="status"
      aria-live="polite"
    >
      {buscando ? (
        <>
          <LoaderCircleIcon className="size-3 animate-spin" aria-hidden /> Atualizando…
        </>
      ) : (
        <>
          <span aria-hidden className="size-1.5 rounded-full bg-success" /> Atualizado às{" "}
          {ultima?.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
        </>
      )}
    </span>
  );
}

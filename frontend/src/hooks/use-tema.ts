"use client";

import { useCallback, useSyncExternalStore } from "react";

import { aplicarTema, temaAtual, type Tema } from "@/lib/tema";

const ouvintes = new Set<() => void>();

function assinar(fn: () => void) {
  ouvintes.add(fn);
  return () => ouvintes.delete(fn);
}

export function useTema(): [Tema, (t: Tema) => void] {
  const tema = useSyncExternalStore(assinar, temaAtual, () => "claro" as Tema);
  const definir = useCallback((t: Tema) => {
    aplicarTema(t);
    ouvintes.forEach((fn) => fn());
  }, []);
  return [tema, definir];
}

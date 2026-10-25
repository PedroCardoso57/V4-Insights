"use client";

import { useCallback, useSyncExternalStore } from "react";

const EVENTO = "v4:storage";

function subscribe(cb: () => void) {
  window.addEventListener("storage", cb);
  window.addEventListener(EVENTO, cb);
  return () => {
    window.removeEventListener("storage", cb);
    window.removeEventListener(EVENTO, cb);
  };
}

function ler(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null; // modo privado / armazenamento bloqueado
  }
}

/** Valor bruto do localStorage, sincronizado entre abas e sem divergência de hidratação. */
export function useLocalStorage(key: string): [string | null, (v: string | null) => void] {
  const valor = useSyncExternalStore(subscribe, () => ler(key), () => null);
  const definir = useCallback(
    (v: string | null) => {
      try {
        if (v === null) localStorage.removeItem(key);
        else localStorage.setItem(key, v);
      } catch {
        /* armazenamento indisponível: segue sem lembrar */
      }
      window.dispatchEvent(new Event(EVENTO));
    },
    [key],
  );
  return [valor, definir];
}

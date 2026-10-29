"use client";

import { useState } from "react";

import { cn } from "@/lib/utils";
import { API_BASE } from "@/services/api/client";

export function iniciais(nome: string): string {
  const p = nome.trim().split(/\s+/);
  return ((p[0]?.[0] ?? "") + (p.length > 1 ? (p[p.length - 1]?.[0] ?? "") : "")).toUpperCase();
}

/** Foto de perfil do colaborador; sem foto (ou se ela falhar), mostra as iniciais. */
export function Avatar({ nome, fotoUrl, className }: { nome: string; fotoUrl?: string | null; className?: string }) {
  const [falhou, setFalhou] = useState<string | null>(null);
  const mostrarFoto = !!fotoUrl && falhou !== fotoUrl;
  return (
    <span
      aria-hidden
      className={cn(
        "flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#1f242d] text-xs font-bold text-white select-none dark:bg-[#3d2830]",
        className,
      )}
    >
      {mostrarFoto ? (
        // eslint-disable-next-line @next/next/no-img-element -- imagem autenticada servida pela API, sem otimização do Next
        <img src={`${API_BASE}${fotoUrl}`} alt="" className="size-full object-cover" onError={() => setFalhou(fotoUrl)} />
      ) : (
        iniciais(nome)
      )}
    </span>
  );
}

"use client";

import { useState } from "react";

import { cn } from "@/lib/utils";
import { API_BASE } from "@/services/api/client";

export function iniciais(nome: string): string {
  const p = nome.trim().split(/\s+/);
  return ((p[0]?.[0] ?? "") + (p.length > 1 ? (p[p.length - 1]?.[0] ?? "") : "")).toUpperCase();
}

/** Avatar padrão de quem ainda não enviou foto: o Nico, mascote da V4. */
export const AVATAR_PADRAO = "/mascote/avatar-nico.webp";

/** Foto de perfil do colaborador; sem foto, mostra o Nico; se a imagem falhar, as iniciais. */
export function Avatar({ nome, fotoUrl, className }: { nome: string; fotoUrl?: string | null; className?: string }) {
  const src = fotoUrl ? `${API_BASE}${fotoUrl}` : AVATAR_PADRAO;
  const [falhou, setFalhou] = useState<string | null>(null);
  const mostrarFoto = falhou !== src;
  const nico = mostrarFoto && !fotoUrl; // recorte sem fundo: dispensa o círculo escuro
  return (
    <span
      aria-hidden
      className={cn(
        "flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-full text-xs font-bold text-white select-none",
        !nico && "bg-[#1f242d] dark:bg-[#3d2830]",
        className,
      )}
    >
      {mostrarFoto ? (
        // eslint-disable-next-line @next/next/no-img-element -- imagem autenticada servida pela API, sem otimização do Next
        <img src={src} alt="" className={cn("size-full", nico ? "object-contain" : "object-cover")} onError={() => setFalhou(src)} />
      ) : (
        iniciais(nome)
      )}
    </span>
  );
}

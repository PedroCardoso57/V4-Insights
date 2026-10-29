"use client";

import { preload } from "react-dom";

import { cn } from "@/lib/utils";

/**
 * Nico andando: o loop recortado do vídeo do usuário (WebP animado com transparência,
 * funciona em todos os navegadores). Ele entra pela esquerda até o centro e segue
 * andando ali, com o chão passando por baixo.
 */
export const NICO_ANDANDO = "/mascote/nico/andando.webp";

/** Chame na página que vai abrir o Nico, para o arquivo já estar baixado quando ele aparecer. */
export function usePreCarregarNico() {
  preload(NICO_ANDANDO, { as: "image", fetchPriority: "low" });
}

export function NicoAndando({ className }: { className?: string }) {
  return (
    <div className={cn("relative", className)}>
      <div className="absolute inset-x-0 bottom-[10px] overflow-hidden opacity-40">
        <div className="nico-chao flex w-[200%] gap-[18px]">
          {Array.from({ length: 24 }, (_, i) => (
            <span key={i} className="h-[2px] w-[14px] shrink-0 rounded-full bg-[#ff2a35]" />
          ))}
        </div>
      </div>
      <div className="nico-entra absolute inset-x-0 bottom-[6px] mx-auto h-[172px] w-[139px]">
        <div aria-hidden className="absolute inset-x-5 bottom-0 h-3 rounded-[50%] bg-black/50 blur-[5px]" />
        {/* eslint-disable-next-line @next/next/no-img-element -- WebP animado; next/image não anima */}
        <img src={NICO_ANDANDO} alt="Nico andando" className="relative size-full object-contain" draggable={false} />
      </div>
    </div>
  );
}

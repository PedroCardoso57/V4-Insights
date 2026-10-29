"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Loader com o mascote V4: as etapas da folha de animação (sem fundo), trocando com
 * transição suave enquanto ele flutua. Os efeitos de cada etapa (pontinhos, rastro de
 * velocidade, confete) são CSS por cima da arte. "Concluído" só aparece no fim de verdade.
 */
const ETAPAS = ["Iniciando", "Processando", "Buscando dados", "Processando", "Quase lá"];
const CONCLUIDO = 5;
const DURACAO_MS = 1100;

const CONFETES = [
  [14, 22, -20],
  [22, 8, 30],
  [80, 10, -35],
  [88, 30, 15],
  [10, 52, 40],
  [92, 58, -10],
  [70, 2, 50],
  [30, 0, -45],
] as const;

export function CarregandoMascote({ concluido = false, className }: { concluido?: boolean; className?: string }) {
  const [passo, setPasso] = useState(0);

  useEffect(() => {
    if (concluido) return;
    const reduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const id = window.setInterval(() => setPasso((p) => (p + 1) % ETAPAS.length), reduzido ? DURACAO_MS * 2 : DURACAO_MS);
    return () => window.clearInterval(id);
  }, [concluido]);

  const etapa = concluido ? CONCLUIDO : passo;
  const rotulo = concluido ? "Concluído!" : `${ETAPAS[passo]}…`;

  return (
    <div role="status" aria-live="polite" aria-label={concluido ? "Concluído" : "Carregando"} className={cn("flex flex-col items-center", className)}>
      <div className="relative h-[228px] w-[300px]">
        {/* Brilho vermelho e sombra no chão: dão o "palco" sem caixa em volta. */}
        <div aria-hidden className="absolute inset-x-10 top-6 bottom-10 rounded-full bg-[#e50914]/20 blur-3xl" />
        <div aria-hidden className="mascote-sombra absolute bottom-[14px] left-1/2 h-4 w-40 -translate-x-1/2 rounded-[50%] bg-black/35 blur-[6px] dark:bg-black/70" />

        <div className="mascote-flutua absolute inset-0">
          {Array.from({ length: CONCLUIDO + 1 }, (_, i) => (
            // eslint-disable-next-line @next/next/no-img-element -- arte estática já otimizada; next/image atrasaria a troca
            <img
              key={i}
              src={`/mascote/carregando/etapa-${i}.webp`}
              alt=""
              aria-hidden
              draggable={false}
              className={cn(
                // Troca rápida com "pulinho" (overshoot): pouca sobreposição entre poses diferentes, sem efeito fantasma.
                "absolute inset-0 size-full object-contain transition-[opacity,transform] motion-reduce:transition-none",
                i === etapa
                  ? "translate-y-0 scale-100 opacity-100 duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
                  : "translate-y-2 scale-[0.9] opacity-0 duration-150 ease-in",
              )}
            />
          ))}

          {/* Iniciando: os três pontinhos acima da cabeça. */}
          <div aria-hidden className={cn("absolute top-[6%] left-[49%] flex -translate-x-1/2 gap-1.5 transition-opacity duration-300", etapa === 0 ? "opacity-100" : "opacity-0")}>
            {[0, 1, 2].map((i) => (
              <span key={i} className="mascote-ponto size-2.5 rounded-full bg-[#ff2a35] shadow-[0_0_10px_#ff2a35]" style={{ animationDelay: `${i * 160}ms` }} />
            ))}
          </div>

          {/* Processando: rastro de velocidade atrás dele. */}
          <div aria-hidden className={cn("absolute top-[22%] left-[2%] flex w-[22%] flex-col gap-3 transition-opacity duration-300", etapa === 1 ? "opacity-100" : "opacity-0")}>
            {[70, 100, 85, 60, 90].map((w, i) => (
              <span
                key={i}
                className="mascote-rastro ml-auto h-[3px] rounded-full bg-gradient-to-r from-transparent to-[#ff2a35] shadow-[0_0_8px_#ff2a35]"
                style={{ width: `${w}%`, animationDelay: `${i * 90}ms` }}
              />
            ))}
          </div>

          {/* Concluído: confete. */}
          <div aria-hidden className={cn("absolute inset-0 transition-opacity duration-300", etapa === CONCLUIDO ? "opacity-100" : "opacity-0")}>
            {CONFETES.map(([x, y, r], i) => (
              <span
                key={i}
                className="mascote-confete absolute size-2 rounded-[2px] bg-[#ff2a35] shadow-[0_0_8px_#ff2a35]"
                style={{ left: `${x}%`, top: `${y}%`, rotate: `${r}deg`, animationDelay: `${i * 60}ms` }}
              />
            ))}
          </div>
        </div>
      </div>

      <p className="mt-1 text-[13px] font-bold tracking-[0.2em] uppercase">{concluido ? "Pronto" : "Carregando"}</p>
      <div className="mt-3 h-1.5 w-56 overflow-hidden rounded-full bg-foreground/10">
        {concluido ? (
          <div className="h-full w-full rounded-full bg-[#e50914]" />
        ) : (
          <div className="mascote-barra h-full w-2/5 rounded-full bg-gradient-to-r from-[#e50914]/0 via-[#e50914] to-[#ff4d55]" />
        )}
      </div>
      <p key={rotulo} className="mascote-rotulo mt-2.5 text-xs text-muted-foreground">
        {rotulo}
      </p>
    </div>
  );
}

/** Carregamento de página dentro do app (troca de rota). */
export function CarregandoTela() {
  return (
    <div className="flex min-h-[60vh] w-full items-center justify-center p-6">
      <CarregandoMascote />
    </div>
  );
}

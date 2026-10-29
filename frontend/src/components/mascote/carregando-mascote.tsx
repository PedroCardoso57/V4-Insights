"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Loader com o mascote V4: os 14 quadros da folha de animação, em sequência com
 * transição suave entre eles. Os quadros têm fundo escuro próprio (#111011), por isso
 * o cartão usa a mesma cor nos dois temas.
 */
const QUADROS = 14;
const ETAPAS = [
  "Iniciando",
  "Iniciando",
  "Processando",
  "Processando",
  "Processando",
  "Buscando dados",
  "Buscando dados",
  "Buscando dados",
  "Processando",
  "Processando",
  "Quase lá",
  "Quase lá",
  "Concluído",
  "Concluído",
];
const DURACAO_MS = 220;

export function CarregandoMascote({ className, compacto = false }: { className?: string; compacto?: boolean }) {
  const [quadro, setQuadro] = useState(0);

  useEffect(() => {
    const reduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const id = window.setInterval(() => setQuadro((q) => (q + 1) % QUADROS), reduzido ? DURACAO_MS * 3 : DURACAO_MS);
    return () => window.clearInterval(id);
  }, []);

  const pct = Math.round(8 + (quadro / (QUADROS - 1)) * 92);

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Carregando"
      className={cn(
        "flex flex-col items-center rounded-2xl bg-[#111011] text-white shadow-[0_20px_60px_-20px_rgba(229,9,20,0.35)]",
        compacto ? "gap-2 px-6 pt-3 pb-5" : "gap-3 px-10 pt-4 pb-7",
        className,
      )}
    >
      <div
        className={cn("relative", compacto ? "h-[136px] w-[150px]" : "h-[204px] w-[225px]")}
        style={{ maskImage: "radial-gradient(closest-side, #000 78%, transparent)" }}
      >
        {Array.from({ length: QUADROS }, (_, i) => (
          // eslint-disable-next-line @next/next/no-img-element -- quadros já otimizados; next/image atrasaria a troca
          <img
            key={i}
            src={`/mascote/carregando/${String(i).padStart(2, "0")}.webp`}
            alt=""
            aria-hidden
            draggable={false}
            className="absolute inset-0 size-full object-contain transition-opacity duration-200 ease-linear motion-reduce:transition-none"
            style={{ opacity: i === quadro ? 1 : 0 }}
          />
        ))}
      </div>
      <p className="text-[13px] font-bold tracking-[0.18em] uppercase">Carregando</p>
      <div className="flex w-56 items-center gap-3">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/15">
          <div
            className={cn("h-full rounded-full bg-[#e50914]", quadro > 0 && "transition-[width] duration-200 ease-linear")}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="w-9 text-right font-mono-num text-xs font-semibold">{pct}%</span>
      </div>
      <p className="text-xs text-white/70">{ETAPAS[quadro]}…</p>
    </div>
  );
}

/** Tela cheia de carregamento (primeira carga do app e troca de página). */
export function CarregandoTela() {
  return (
    <div className="flex min-h-[60vh] w-full items-center justify-center p-6">
      <CarregandoMascote />
    </div>
  );
}

"use client";

import { Dialog as DialogPrimitive } from "radix-ui";

/**
 * Modal de entrada com o Nico, o mascote da V4: enquanto o login acontece ele passa
 * correndo pela tela; quando dá certo, comemora com o nome da pessoa.
 */
export type EstadoEntrada = { fase: "entrando" | "google" } | { fase: "pronto"; nome: string };

const CONFETES = [
  [14, 20, -20],
  [24, 6, 30],
  [78, 8, -35],
  [88, 28, 15],
  [10, 50, 40],
  [90, 56, -10],
  [68, 0, 50],
  [32, 0, -45],
] as const;

export function NicoEntrando({ estado }: { estado: EstadoEntrada | null }) {
  const pronto = estado?.fase === "pronto";
  const titulo = pronto ? `Tudo certo, ${estado.nome.split(" ")[0]}!` : estado?.fase === "google" ? "Abrindo o Google Workspace" : "Entrando na plataforma";
  const texto = pronto ? "Preparando seus indicadores…" : estado?.fase === "google" ? "Você vai confirmar sua conta no Google." : "Validando suas credenciais…";

  return (
    <DialogPrimitive.Root open={estado !== null}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="nico-surge-fundo fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
        <DialogPrimitive.Content
          onEscapeKeyDown={(e) => e.preventDefault()}
          onPointerDownOutside={(e) => e.preventDefault()}
          onInteractOutside={(e) => e.preventDefault()}
          className="nico-surge fixed top-1/2 left-1/2 z-50 w-[calc(100%-2rem)] max-w-[380px] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-2xl border border-white/10 bg-[#111011] px-6 pt-5 pb-7 text-center text-white shadow-[0_30px_80px_-20px_rgba(229,9,20,0.55)] focus:outline-none"
        >
          {/* Palco: o Nico atravessa da esquerda para a direita; no fim, comemora no centro. */}
          <div className="relative mx-auto h-[190px] w-full overflow-hidden" aria-hidden>
            <div className="absolute inset-x-6 top-8 bottom-8 rounded-full bg-[#e50914]/25 blur-3xl" />
            <div className="absolute inset-x-0 bottom-[22px] h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" />

            {pronto ? (
              <div className="absolute inset-0">
                <div className="nico-pula absolute inset-x-0 top-0 mx-auto h-[175px] w-[230px]">
                  {/* eslint-disable-next-line @next/next/no-img-element -- arte estática já otimizada */}
                  <img src="/mascote/carregando/etapa-5.webp" alt="" className="size-full object-contain" draggable={false} />
                  {CONFETES.map(([x, y, r], i) => (
                    <span
                      key={i}
                      className="mascote-confete absolute size-2 rounded-[2px] bg-[#ff2a35] shadow-[0_0_8px_#ff2a35]"
                      style={{ left: `${x}%`, top: `${y}%`, rotate: `${r}deg`, animationDelay: `${i * 50}ms` }}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <div className="nico-passa absolute top-0 left-0 h-[175px] w-[230px]">
                <div className="mascote-flutua relative size-full [animation-duration:0.5s]">
                  <div className="absolute top-[24%] left-[2%] flex w-[24%] flex-col gap-3">
                    {[70, 100, 85, 60, 90].map((w, i) => (
                      <span
                        key={i}
                        className="mascote-rastro ml-auto h-[3px] rounded-full bg-gradient-to-r from-transparent to-[#ff2a35] shadow-[0_0_8px_#ff2a35]"
                        style={{ width: `${w}%`, animationDelay: `${i * 90}ms` }}
                      />
                    ))}
                  </div>
                  {/* eslint-disable-next-line @next/next/no-img-element -- arte estática já otimizada */}
                  <img src="/mascote/carregando/etapa-1.webp" alt="" className="size-full object-contain" draggable={false} />
                </div>
              </div>
            )}
          </div>

          <DialogPrimitive.Title className="text-[15px] font-bold tracking-tight">{titulo}</DialogPrimitive.Title>
          <DialogPrimitive.Description className="mt-1 text-xs text-white/65">{texto}</DialogPrimitive.Description>
          <div className="mx-auto mt-4 h-1.5 w-48 overflow-hidden rounded-full bg-white/10">
            {pronto ? (
              <div className="h-full w-full rounded-full bg-[#e50914]" />
            ) : (
              <div className="mascote-barra h-full w-2/5 rounded-full bg-gradient-to-r from-[#e50914]/0 via-[#e50914] to-[#ff4d55]" />
            )}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

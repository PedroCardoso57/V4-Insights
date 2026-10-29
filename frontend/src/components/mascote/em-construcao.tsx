import Link from "next/link";

import { Button } from "@/components/ui/button";

/**
 * Página em construção: o mascote pintando a parede. Use como conteúdo de uma página nova
 * que já aparece no menu mas ainda não está pronta:
 *
 *   export default function Page() {
 *     return <EmConstrucao titulo="Metas em construção" />;
 *   }
 */
export function EmConstrucao({ titulo = "Página em construção" }: { titulo?: string }) {
  return (
    <section className="mx-auto flex max-w-2xl flex-col items-center rounded-2xl bg-[#111011] px-6 pt-6 pb-10 text-center text-white">
      {/* eslint-disable-next-line @next/next/no-img-element -- arte estática com borda esfumada (alpha) */}
      <img src="/mascote/construcao.webp" alt="" aria-hidden className="w-full max-w-[520px]" width={1012} height={808} />
      <h1 className="mt-2 text-base font-bold tracking-[0.14em] uppercase">{titulo}</h1>
      <span aria-hidden className="mt-3 h-1 w-12 rounded-full bg-[#e50914]" />
      <p className="mt-4 text-sm text-white/75">Estamos construindo algo incrível! Volte em breve.</p>
      <Button asChild variant="outline" size="sm" className="mt-6 border-white/20 bg-transparent text-white hover:bg-white/10 hover:text-white">
        <Link href="/">Voltar para a visão geral</Link>
      </Button>
    </section>
  );
}

import Link from "next/link";
import type { ReactNode } from "react";

import { SimboloV4 } from "@/components/marca/simbolo-v4";
import { LEGAL, PAGINAS_LEGAIS } from "@/lib/legal";

/** Páginas públicas (sem login): privacidade, termos e exclusão de dados. */
export default function PublicoLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="border-b">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2.5 font-semibold">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-white">
              <SimboloV4 className="size-4.5" />
            </span>
            {LEGAL.produto}
          </Link>
          <span className="text-xs text-muted-foreground">{LEGAL.controlador}</span>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8 sm:px-6 sm:py-12">{children}</main>
      <footer className="border-t">
        <nav
          aria-label="Documentos"
          className="mx-auto flex max-w-3xl flex-wrap gap-x-5 gap-y-2 px-4 py-5 text-xs text-muted-foreground sm:px-6"
        >
          {PAGINAS_LEGAIS.map((p) => (
            <Link key={p.href} href={p.href} className="hover:text-foreground hover:underline">
              {p.titulo}
            </Link>
          ))}
          <span className="sm:ml-auto">Revisado em {LEGAL.revisadoEm}</span>
        </nav>
      </footer>
    </div>
  );
}

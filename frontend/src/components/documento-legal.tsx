import type { ReactNode } from "react";

/** Tipografia das páginas públicas de privacidade, termos e exclusão de dados. */
export function DocumentoLegal({ titulo, resumo, children }: { titulo: string; resumo: ReactNode; children: ReactNode }) {
  return (
    <article className="grid gap-6 text-sm leading-relaxed [&_a]:text-primary-ink [&_a]:underline [&_h2]:mt-4 [&_h2]:text-base [&_h2]:font-semibold [&_li]:ml-5 [&_li]:list-disc [&_ol>li]:list-decimal [&_p]:text-muted-foreground [&_li]:text-muted-foreground [&_strong]:text-foreground">
      <header className="grid gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">{titulo}</h1>
        <p className="text-base">{resumo}</p>
      </header>
      {children}
    </article>
  );
}

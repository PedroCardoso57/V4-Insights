import type { ReactNode } from "react";

export function PageHeader({
  titulo,
  descricao,
  acoes,
  selo,
}: {
  titulo: ReactNode;
  descricao?: ReactNode;
  acoes?: ReactNode;
  selo?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-2xl font-bold tracking-tight sm:text-[1.75rem]">{titulo}</h1>
          {selo}
        </div>
        {descricao && <p className="mt-1 max-w-3xl text-sm leading-relaxed text-muted-foreground">{descricao}</p>}
      </div>
      {acoes && <div className="flex flex-wrap items-center gap-2">{acoes}</div>}
    </div>
  );
}

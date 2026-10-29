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
    <div className="mb-5 flex flex-wrap items-start justify-between gap-4 sm:mb-6">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-[1.375rem] leading-tight font-bold tracking-tight sm:text-[1.75rem]">{titulo}</h1>
          {selo}
        </div>
        {descricao && <p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-muted-foreground sm:text-sm">{descricao}</p>}
      </div>
      {acoes && <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto max-sm:[&>*]:flex-1">{acoes}</div>}
    </div>
  );
}

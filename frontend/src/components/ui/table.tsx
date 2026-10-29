"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

/** Copia o texto de cada cabeçalho para `data-label` das células, usado pelo layout em cartões do
 *  celular. Células que já trazem `data-label` (inclusive vazio, para ações) ficam como estão. */
function rotularCelulas(tabela: HTMLTableElement) {
  const cabecalhos = tabela.tHead?.rows[tabela.tHead.rows.length - 1]?.cells;
  if (!cabecalhos) return;
  const rotulos = Array.from(cabecalhos, (th) => {
    const copia = th.cloneNode(true) as HTMLElement;
    copia.querySelectorAll(".sr-only").forEach((el) => el.remove());
    return copia.textContent?.trim() ?? "";
  });
  for (const corpo of Array.from(tabela.tBodies)) {
    for (const linha of Array.from(corpo.rows)) {
      Array.from(linha.cells).forEach((td, i) => {
        if (td.colSpan > 1) td.dataset.cheia = "";
        else if (!td.hasAttribute("data-label") || td.dataset.auto !== undefined) {
          td.dataset.label = rotulos[i] ?? "";
          td.dataset.auto = "";
        }
      });
    }
  }
}

/** No celular (abaixo de `sm`) cada linha vira um cartão: a primeira célula é o título e as demais
 *  aparecem com o rótulo da coluna. `cartoes={false}` mantém a tabela com rolagem horizontal.
 *  Os `role` explícitos preservam a semântica de tabela quando o CSS muda o `display`. */
function Table({
  className,
  cartoes = true,
  colunasCartao = 2,
  ...props
}: React.ComponentProps<"table"> & { cartoes?: boolean; colunasCartao?: 2 | 3 }) {
  const ref = React.useRef<HTMLTableElement>(null);
  React.useEffect(() => {
    const tabela = ref.current;
    if (!tabela || !cartoes) return;
    rotularCelulas(tabela);
    const obs = new MutationObserver(() => rotularCelulas(tabela));
    obs.observe(tabela, { childList: true, subtree: true, characterData: true });
    return () => obs.disconnect();
  }, [cartoes]);
  return (
    <div
      data-slot="table-container"
      className={cn("relative w-full overflow-x-auto", cartoes && "tabela-cartoes")}
      style={cartoes ? ({ "--cartao-colunas": colunasCartao } as React.CSSProperties) : undefined}
    >
      <table ref={ref} role="table" data-slot="table" className={cn("w-full caption-bottom text-[13px]", className)} {...props} />
    </div>
  );
}
function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return <thead role="rowgroup" data-slot="table-header" className={cn("bg-subtle [&_tr]:border-b [&_tr]:hover:bg-transparent", className)} {...props} />;
}
function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return <tbody role="rowgroup" data-slot="table-body" className={cn("[&_tr:last-child]:border-0", className)} {...props} />;
}
function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return <tr role="row" data-slot="table-row" className={cn("border-b transition-colors hover:bg-subtle/70", className)} {...props} />;
}
function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      role="columnheader"
      data-slot="table-head"
      className={cn("h-10 px-4 text-left align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground whitespace-nowrap", className)}
      {...props}
    />
  );
}
function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return <td role="cell" data-slot="table-cell" className={cn("px-4 py-3 align-middle", className)} {...props} />;
}

export { Table, TableBody, TableCell, TableHead, TableHeader, TableRow };

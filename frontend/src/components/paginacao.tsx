"use client";

import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

export function Paginacao({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (p: number) => void }) {
  const paginas = Math.max(1, Math.ceil(total / pageSize));
  return (
    <nav aria-label="Paginação" className="mt-3 flex flex-wrap items-center justify-end gap-3 text-sm text-muted-foreground">
      <span>
        Página {page} de {paginas} · {total} {total === 1 ? "registro" : "registros"}
      </span>
      <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Página anterior">
        <ChevronLeftIcon />
      </Button>
      <Button variant="outline" size="sm" disabled={page >= paginas} onClick={() => onPage(page + 1)} aria-label="Próxima página">
        <ChevronRightIcon />
      </Button>
    </nav>
  );
}

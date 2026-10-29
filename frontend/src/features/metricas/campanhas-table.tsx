"use client";

import { ArrowDownIcon, ArrowUpIcon } from "lucide-react";
import { useMemo, useState } from "react";

import { PlataformaBadge } from "@/components/plataforma-badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fmtKpi, KPI_LABEL, type KpiKey } from "@/lib/format";
import type { Schemas } from "@/services/api/client";

type Campanha = Schemas["CampanhaOut"];
type Coluna = "campanha_nome" | KpiKey;
const COLS: KpiKey[] = ["investimento", "impressoes", "cliques", "ctr", "cpc", "conversoes", "cpa", "roas"];

export function ordenarCampanhas(lista: Campanha[], col: Coluna, asc: boolean): Campanha[] {
  const val = (c: Campanha) =>
    col === "campanha_nome" ? (c.campanha_nome ?? c.campanha_externa_id) : c.kpis[col] === null ? null : Number(c.kpis[col]);
  return [...lista].sort((a, b) => {
    const va = val(a);
    const vb = val(b);
    if (va === null) return 1; // ausentes sempre ao final
    if (vb === null) return -1;
    const r = typeof va === "string" ? va.localeCompare(vb as string, "pt-BR") : va - (vb as number);
    return asc ? r : -r;
  });
}

export function CampanhasTable({ campanhas, moeda = "BRL" }: { campanhas: Campanha[]; moeda?: string }) {
  const [col, setCol] = useState<Coluna>("investimento");
  const [asc, setAsc] = useState(false);
  const linhas = useMemo(() => ordenarCampanhas(campanhas, col, asc), [campanhas, col, asc]);
  if (!campanhas.length) return <p className="py-6 text-center text-sm text-muted-foreground">Nenhuma campanha no período.</p>;
  const th = (c: Coluna, label: string) => (
    <TableHead aria-sort={col === c ? (asc ? "ascending" : "descending") : "none"} className={c === "campanha_nome" ? "" : "text-right"}>
      <button
        type="button"
        className="inline-flex items-center gap-1 uppercase"
        onClick={() => {
          if (c === col) setAsc(!asc);
          else {
            setCol(c);
            setAsc(c === "campanha_nome");
          }
        }}
      >
        {label}
        {col === c && (asc ? <ArrowUpIcon className="size-3" /> : <ArrowDownIcon className="size-3" />)}
      </button>
    </TableHead>
  );
  return (
    <Table colunasCartao={3}>
      <TableHeader>
        <TableRow>
          {th("campanha_nome", "Campanha")}
          <TableHead>Plataforma</TableHead>
          {COLS.map((k) => th(k, KPI_LABEL[k]))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {linhas.map((c) => (
          <TableRow key={`${c.conta_anuncio_id}-${c.campanha_externa_id}`}>
            <TableCell className="max-w-64 truncate font-medium" title={c.campanha_nome ?? undefined}>{c.campanha_nome ?? c.campanha_externa_id}</TableCell>
            <TableCell><PlataformaBadge plataforma={c.plataforma} /></TableCell>
            {COLS.map((k) => (
              <TableCell key={k} className="text-right font-mono-num text-xs">{fmtKpi(k, c.kpis[k], moeda)}</TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

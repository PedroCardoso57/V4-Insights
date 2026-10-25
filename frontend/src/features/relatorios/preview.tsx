"use client";

import { Consulta } from "@/components/estado";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCliente } from "@/features/clientes/api";
import { useMetricas, type Granularidade } from "@/features/metricas/api";
import { CampanhasTable } from "@/features/metricas/campanhas-table";
import { SerieChart } from "@/features/metricas/serie-chart";
import { fmtData, fmtDataHora, fmtKpi, fmtPercent, KPI_LABEL, type KpiKey, type Plataforma } from "@/lib/format";

import { TEMPLATES, type GRAFICOS } from "./schema";

const SERIES: Record<string, KpiKey> = { serie_investimento: "investimento", serie_cliques: "cliques", serie_conversoes: "conversoes" };

/** Prévia com as mesmas consultas do dashboard; o PDF congela estes números ao ser gerado. */
export function PreviewRelatorio(p: {
  clienteId?: string;
  titulo: string;
  template: keyof typeof TEMPLATES;
  periodo: { inicio: string; fim: string };
  plataformas: Plataforma[];
  kpis: KpiKey[];
  graficos: (typeof GRAFICOS)[number][];
  granularidade: Granularidade;
  comparar: boolean;
  comentarios?: string;
}) {
  const cliente = useCliente(p.clienteId);
  const { resumo, serie, campanhas } = useMetricas(p.clienteId, {
    inicio: p.periodo.inicio,
    fim: p.periodo.fim,
    plataforma: p.plataformas.length === 1 ? p.plataformas[0]! : "",
    conta_anuncio_id: "",
    campanha_id: "",
    granularidade: p.granularidade,
    comparar: p.comparar,
  });
  if (!p.clienteId) {
    return <Card><CardContent className="p-6 text-sm text-muted-foreground">Selecione um cliente para ver a prévia.</CardContent></Card>;
  }
  const executiva = p.template === "visao_executiva";
  return (
    <Card aria-label="Prévia do relatório">
      <CardHeader className="flex-col items-start gap-1 border-b">
        <span className="text-xs uppercase tracking-wide text-muted-foreground">Prévia · {TEMPLATES[p.template]}</span>
        <CardTitle className="text-xl">{p.titulo}</CardTitle>
        <p className="text-sm text-muted-foreground">
          {cliente.data?.nome ?? "…"} · {fmtData(p.periodo.inicio)} a {fmtData(p.periodo.fim)}
          {resumo.data && <> · última coleta {fmtDataHora(resumo.data.ultima_sincronizacao_em)}</>}
        </p>
      </CardHeader>
      <CardContent className="grid gap-5 pt-4">
        <Consulta query={resumo} carregando={<Skeleton className="h-40" />}>
          {(r) => {
            const moeda = r.moedas[0] ?? "BRL";
            return (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Indicador</TableHead>
                      <TableHead className="text-right">Período</TableHead>
                      <TableHead className="text-right">Anterior</TableHead>
                      <TableHead className="text-right">Variação</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {p.kpis.map((k) => {
                      const v = r.variacao_percentual[k];
                      return (
                        <TableRow key={k}>
                          <TableCell>{KPI_LABEL[k]}</TableCell>
                          <TableCell className="text-right tabular-nums">{fmtKpi(k, r.atual[k], moeda)}</TableCell>
                          <TableCell className="text-right tabular-nums">{r.anterior ? fmtKpi(k, r.anterior[k], moeda) : "—"}</TableCell>
                          <TableCell className="text-right tabular-nums">
                            {v === null || v === undefined ? "—" : `${Number(v) > 0 ? "+" : ""}${fmtPercent(v)}`}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
                {p.graficos
                  .filter((g) => g in SERIES)
                  .map((g) => (
                    <section key={g} aria-label={g}>
                      <h4 className="mb-2 text-sm font-medium">{KPI_LABEL[SERIES[g]!]} por período</h4>
                      {serie.data ? <SerieChart serie={serie.data} kpi={SERIES[g]!} moeda={moeda} /> : <Skeleton className="h-72" />}
                    </section>
                  ))}
                {(p.graficos.includes("tabela_campanhas") || !executiva) && (
                  <section>
                    <h4 className="mb-2 text-sm font-medium">Campanhas{executiva ? " (top 10)" : ""}</h4>
                    {campanhas.data ? (
                      <CampanhasTable campanhas={executiva ? campanhas.data.items.slice(0, 10) : campanhas.data.items} moeda={moeda} />
                    ) : (
                      <Skeleton className="h-32" />
                    )}
                  </section>
                )}
              </>
            );
          }}
        </Consulta>
        {p.comentarios && (
          <section>
            <h4 className="mb-1 text-sm font-medium">Comentários</h4>
            <p className="whitespace-pre-line text-sm">{p.comentarios}</p>
          </section>
        )}
      </CardContent>
    </Card>
  );
}

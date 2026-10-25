"use client";

import { useMemo } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fmtData, fmtKpi, KPI_LABEL, type KpiKey } from "@/lib/format";
import type { Schemas } from "@/services/api/client";

export function SerieChart({ serie, kpi, moeda = "BRL" }: { serie: Schemas["SerieOut"]; kpi: KpiKey; moeda?: string }) {
  const dados = useMemo(
    () =>
      serie.pontos.map((p, i) => {
        const ant = serie.comparacao?.[i]?.kpis[kpi];
        return {
          periodo: fmtData(p.periodo),
          atual: p.kpis[kpi] === null ? null : Number(p.kpis[kpi]),
          anterior: ant === null || ant === undefined ? null : Number(ant),
        };
      }),
    [serie, kpi],
  );
  if (!dados.length) return <p className="py-10 text-center text-sm text-muted-foreground">Sem dados no período.</p>;
  return (
    <figure aria-label={`Série temporal de ${KPI_LABEL[kpi]}`} className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={dados} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="periodo" fontSize={12} tickMargin={6} />
          <YAxis fontSize={12} width={64} tickFormatter={(v: number) => fmtKpi(kpi, v, moeda).replace(/,\d+/, "")} />
          <Tooltip formatter={(v) => fmtKpi(kpi, v as number, moeda)} />
          <Legend />
          <Line name={KPI_LABEL[kpi]} dataKey="atual" stroke="var(--chart-1)" strokeWidth={2} dot={false} connectNulls />
          {serie.comparacao && (
            <Line name="Período anterior" dataKey="anterior" stroke="var(--chart-2)" strokeDasharray="4 4" dot={false} connectNulls />
          )}
        </LineChart>
      </ResponsiveContainer>
    </figure>
  );
}

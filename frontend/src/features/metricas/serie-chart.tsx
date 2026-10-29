"use client";

import { useMemo } from "react";
import { Area, AreaChart, CartesianGrid, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fmtData, fmtKpi, KPI_LABEL, type KpiKey } from "@/lib/format";
import type { Schemas } from "@/services/api/client";

const EIXO = { fontSize: 10, fontFamily: "JetBrains Mono Variable, ui-monospace, monospace", fill: "var(--faint)" };

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
    <figure aria-label={`Série temporal de ${KPI_LABEL[kpi]}`} className="h-60 w-full sm:h-72">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={dados} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="grad-serie" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--brand)" stopOpacity={0.2} />
              <stop offset="100%" stopColor="var(--brand)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 4" stroke="var(--line)" vertical={false} />
          <XAxis dataKey="periodo" tick={EIXO} tickMargin={8} minTickGap={18} axisLine={false} tickLine={false} />
          <YAxis
            tick={EIXO}
            width={64}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => fmtKpi(kpi, v, moeda).replace(/,\d+/, "")}
          />
          <Tooltip
            formatter={(v) => fmtKpi(kpi, v as number, moeda)}
            contentStyle={{
              background: "#110c10",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 10,
              color: "#fff",
              fontSize: 12,
            }}
            labelStyle={{ color: "rgba(255,255,255,0.7)" }}
            cursor={{ stroke: "var(--line-strong)" }}
          />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: "var(--text-muted)" }} />
          <Area
            name={KPI_LABEL[kpi]}
            dataKey="atual"
            type="monotone"
            stroke="var(--brand)"
            strokeWidth={2}
            fill="url(#grad-serie)"
            dot={{ r: 3, fill: "var(--surface)", stroke: "var(--brand)", strokeWidth: 1.5 }}
            activeDot={{ r: 4 }}
            connectNulls
          />
          {serie.comparacao && (
            <Line
              name="Período anterior"
              dataKey="anterior"
              type="monotone"
              stroke="var(--blue)"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
              connectNulls
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </figure>
  );
}

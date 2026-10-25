"use client";

import { AlertTriangleIcon, ArrowDownRightIcon, ArrowUpRightIcon, InfoIcon } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { fmtData, fmtDataHora, fmtKpi, fmtPercent, horasDesde, KPI_CUSTO, KPI_LABEL, type KpiKey } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Schemas } from "@/services/api/client";

export const KPIS_PADRAO: KpiKey[] = ["investimento", "impressoes", "cliques", "ctr", "cpc", "cpm", "conversoes", "cpa", "roas"];

type Resumo = Schemas["ResumoOut"];

export function KpiCard({ resumo, kpi }: { resumo: Resumo; kpi: KpiKey }) {
  const moeda = resumo.moedas[0] ?? "BRL";
  const v = resumo.variacao_percentual[kpi];
  const n = v === null || v === undefined ? null : Number(v);
  const bom = n === null || n === 0 ? null : KPI_CUSTO.includes(kpi) ? n < 0 : n > 0;
  return (
    <Card className="flex flex-col p-4">
      <span className="flex items-center justify-between gap-2 text-xs font-medium text-muted-foreground">
        {KPI_LABEL[kpi]}
        <InfoIcon className="size-3.5 text-faint" aria-hidden />
      </span>
      <strong className="mt-2.5 mb-3 font-mono-num text-xl font-semibold text-foreground">{fmtKpi(kpi, resumo.atual[kpi], moeda)}</strong>
      {resumo.periodo_anterior && (
        <span
          className="mt-auto inline-flex items-center gap-1 border-t pt-2.5 text-[11px] text-muted-foreground"
          title={`vs ${fmtData(resumo.periodo_anterior.inicio)} – ${fmtData(resumo.periodo_anterior.fim)}`}
        >
          {n === null ? (
            "sem base de comparação"
          ) : (
            <>
              <span className={cn("inline-flex items-center gap-0.5 font-mono-num font-semibold", bom === true && "text-success", bom === false && "text-destructive")}>
                {n > 0 ? <ArrowUpRightIcon className="size-3" aria-hidden /> : n < 0 ? <ArrowDownRightIcon className="size-3" aria-hidden /> : null}
                {`${n > 0 ? "+" : ""}${fmtPercent(v)}`}
              </span>
              <span className="truncate">vs. período anterior</span>
              <span className="sr-only">{bom ? "(favorável)" : bom === false ? "(desfavorável)" : ""}</span>
            </>
          )}
        </span>
      )}
    </Card>
  );
}

export function KpiGrid({ resumo, kpis = KPIS_PADRAO }: { resumo: Resumo; kpis?: KpiKey[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5 2xl:grid-cols-9">
      {kpis.map((k) => (
        <KpiCard key={k} resumo={resumo} kpi={k} />
      ))}
    </div>
  );
}

/** Aviso de freshness: quando foi a última sincronização e se há moedas misturadas. */
export function AvisoSync({ resumo, agora }: { resumo: Resumo; agora: number }) {
  if (resumo.integracoes_conectadas === 0) return null;
  const horas = horasDesde(resumo.ultima_sincronizacao_em, agora);
  const atrasada = horas === null || horas > 24;
  return (
    <div className="grid gap-2">
      <Alert variant={atrasada ? "warning" : "info"}>
        {atrasada ? <AlertTriangleIcon /> : <InfoIcon />}
        <span>
          {horas === null
            ? "Sincronização ainda não concluída para as contas selecionadas."
            : `Última sincronização: ${fmtDataHora(resumo.ultima_sincronizacao_em)}${atrasada ? " — dados podem estar desatualizados." : "."}`}
        </span>
      </Alert>
      {resumo.moedas.length > 1 && (
        <Alert variant="warning">
          <AlertTriangleIcon />
          <span>Contas em moedas diferentes ({resumo.moedas.join(", ")}) somadas sem conversão cambial.</span>
        </Alert>
      )}
      {resumo.atual.conversoes === null && (
        <p className="text-xs text-muted-foreground">
          Conversões, CPA e ROAS aparecem após mapear as ações de conversão de cada conta em Integrações.
        </p>
      )}
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";

import { Consulta, Vazio } from "@/components/estado";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useIntegracoes } from "@/features/integracoes/api";
import { KPI_LABEL, type KpiKey } from "@/lib/format";

import { filtrosPadrao, useMetricas, useOpcoesCampanha, type Filtros } from "./api";
import { CampanhasTable } from "./campanhas-table";
import { FiltrosBar } from "./filtros-bar";
import { AvisoSync, KpiGrid } from "./kpis";
import { SerieChart } from "./serie-chart";

/** Painel de indicadores do cliente: filtros únicos aplicados a cards, gráfico e tabela. */
export function PainelCliente({ clienteId, inicial }: { clienteId: string; inicial?: Partial<Filtros> }) {
  const [filtros, setFiltros] = useState<Filtros>(() => ({ ...filtrosPadrao(), ...inicial }));
  const [kpiSerie, setKpiSerie] = useState<KpiKey>("investimento");
  const [agora] = useState(() => Date.now());
  const integracoes = useIntegracoes(clienteId);
  const { resumo, serie, campanhas } = useMetricas(clienteId, filtros);

  // Opções vêm da consulta sem filtro de campanha: a lista não encolhe ao selecionar uma.
  const opcoes = useOpcoesCampanha(clienteId, filtros).data ?? [];

  const moeda = resumo.data?.moedas[0] ?? "BRL";
  const semIntegracao = useMemo(
    () => resumo.data && resumo.data.integracoes_conectadas === 0 && !resumo.data.atual.impressoes,
    [resumo.data],
  );

  return (
    <div className="grid gap-4">
      <FiltrosBar filtros={filtros} onChange={setFiltros} integracoes={integracoes.data?.items} campanhas={opcoes} />
      <Consulta
        query={resumo}
        carregando={
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5 2xl:grid-cols-9">
            {Array.from({ length: 9 }, (_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
          </div>
        }
        vazio={() =>
          semIntegracao && (
            <Vazio titulo="Nenhuma integração conectada">
              Conecte Meta Ads ou Google Ads em Integrações para ver os indicadores deste cliente.
            </Vazio>
          )
        }
      >
        {(r) => (
          <>
            <AvisoSync resumo={r} agora={agora} />
            <KpiGrid resumo={r} />
            <Card>
              <CardHeader className="border-b">
                <div>
                  <CardTitle>Evolução temporal</CardTitle>
                  <CardDescription>Acompanhamento consolidado no período · passe o cursor para inspecionar</CardDescription>
                </div>
                <Select value={kpiSerie} onValueChange={(v) => setKpiSerie(v as KpiKey)}>
                  <SelectTrigger className="w-48" aria-label="Métrica do gráfico"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {(Object.keys(KPI_LABEL) as KpiKey[]).map((k) => (
                      <SelectItem key={k} value={k}>{KPI_LABEL[k]}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </CardHeader>
              <CardContent className="pt-4">
                <Consulta query={serie} carregando={<Skeleton className="h-72 rounded-xl" />}>
                  {(s) => <SerieChart serie={s} kpi={kpiSerie} moeda={moeda} />}
                </Consulta>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="border-b">
                <div>
                  <CardTitle>Desempenho por campanha</CardTitle>
                  <CardDescription>Totais do período filtrado</CardDescription>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <Consulta query={campanhas}>{(c) => <CampanhasTable campanhas={c.items} moeda={moeda} />}</Consulta>
              </CardContent>
            </Card>
          </>
        )}
      </Consulta>
    </div>
  );
}

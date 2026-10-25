import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import type { Campanha, Filtros, Integracao, KpiKey, Resumo, Serie } from "../api/types";
import { pode, useAuth } from "../lib/auth";
import {
  fmtData,
  fmtDataHora,
  fmtKpi,
  fmtPercent,
  KPI_CUSTO,
  KPI_LABEL,
  PLATAFORMA_LABEL,
} from "../lib/format";
import { useApi } from "../lib/useApi";
import { filtrosQuery } from "./Filtros";

export const KPIS_PADRAO: KpiKey[] = [
  "investimento",
  "impressoes",
  "cliques",
  "ctr",
  "cpc",
  "cpm",
  "conversoes",
  "cpa",
  "roas",
];

// Carrega resumo, série e campanhas com os MESMOS filtros (consistência entre gráficos).
export function useMetricas(clienteId: string, f: Filtros) {
  const key = JSON.stringify(f);
  const base = filtrosQuery(f);
  const resumo = useApi(
    () =>
      clienteId
        ? api<Resumo>(`/clientes/${clienteId}/metricas/resumo`, {
            query: { ...base, comparar: f.comparar },
          })
        : Promise.resolve(null),
    [clienteId, key],
  );
  const serie = useApi(
    () =>
      clienteId
        ? api<Serie>(`/clientes/${clienteId}/metricas/serie`, {
            query: { ...base, granularidade: f.granularidade, comparar: f.comparar },
          })
        : Promise.resolve(null),
    [clienteId, key],
  );
  const campanhas = useApi(
    () =>
      clienteId
        ? api<Campanha[]>(`/clientes/${clienteId}/campanhas`, { query: base })
        : Promise.resolve(null),
    [clienteId, key],
  );
  return { resumo, serie, campanhas };
}

export function useIntegracoes(clienteId: string) {
  const { me } = useAuth();
  return useApi(
    () =>
      clienteId && pode.editar(me?.papel)
        ? api<Integracao[]>("/integracoes", { query: { cliente_id: clienteId } })
        : Promise.resolve([] as Integracao[]),
    [clienteId, me?.papel],
  );
}

export function AvisoSync({ resumo }: { resumo: Resumo }) {
  const [agora] = useState(() => Date.now());
  if (resumo.integracoes_conectadas === 0) return null;
  const horas = resumo.ultima_sincronizacao_em
    ? (agora - new Date(resumo.ultima_sincronizacao_em).getTime()) / 3.6e6
    : null;
  return (
    <p className={`alert ${horas === null || horas > 24 ? "alert-warn" : "alert-info"}`}>
      {horas === null
        ? "Sincronização ainda não concluída para as contas selecionadas."
        : `Última sincronização: ${fmtDataHora(resumo.ultima_sincronizacao_em)}.`}
      {resumo.moedas.length > 1 &&
        ` Atenção: contas em moedas diferentes (${resumo.moedas.join(", ")}) somadas sem conversão.`}
    </p>
  );
}

export function KpiCard({ resumo, kpi }: { resumo: Resumo; kpi: KpiKey }) {
  const moeda = resumo.moedas[0] ?? "BRL";
  const v = resumo.variacao_percentual[kpi];
  const num = v === null ? null : Number(v);
  const bom = num === null ? null : KPI_CUSTO.includes(kpi) ? num < 0 : num > 0;
  return (
    <div className="card kpi">
      <span className="kpi-label">{KPI_LABEL[kpi]}</span>
      <strong className="kpi-value">{fmtKpi(kpi, resumo.atual[kpi], moeda)}</strong>
      {resumo.periodo_anterior && (
        <span
          className={`kpi-var ${num === null || num === 0 ? "" : bom ? "pos" : "neg"}`}
          title={`vs ${fmtData(resumo.periodo_anterior.inicio)} – ${fmtData(resumo.periodo_anterior.fim)}`}
        >
          {num === null ? "sem base de comparação" : `${num > 0 ? "+" : ""}${fmtPercent(v)}`}
        </span>
      )}
    </div>
  );
}

export function KpiCards({ resumo, kpis = KPIS_PADRAO }: { resumo: Resumo; kpis?: KpiKey[] }) {
  return (
    <div className="kpi-grid">
      {kpis.map((k) => (
        <KpiCard key={k} resumo={resumo} kpi={k} />
      ))}
    </div>
  );
}

export function SerieChart({ serie, kpi }: { serie: Serie; kpi: KpiKey }) {
  const dados = useMemo(
    () =>
      serie.pontos.map((p, i) => ({
        periodo: fmtData(p.periodo),
        atual: p.kpis[kpi] === null ? null : Number(p.kpis[kpi]),
        anterior:
          serie.comparacao?.[i]?.kpis[kpi] == null ? null : Number(serie.comparacao[i].kpis[kpi]),
      })),
    [serie, kpi],
  );
  if (!dados.length) return <div className="empty">Sem dados no período.</div>;
  return (
    <div className="chart" aria-label={`Série de ${KPI_LABEL[kpi]}`}>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={dados} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="periodo" fontSize={12} />
          <YAxis fontSize={12} />
          <Tooltip formatter={(v) => fmtKpi(kpi, v as number)} />
          <Legend />
          <Line name={KPI_LABEL[kpi]} dataKey="atual" stroke="var(--accent)" strokeWidth={2} dot={false} connectNulls />
          {serie.comparacao && (
            <Line
              name="Período anterior"
              dataKey="anterior"
              stroke="var(--muted)"
              strokeDasharray="4 4"
              dot={false}
              connectNulls
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

type ColCamp = "campanha_nome" | KpiKey;

export function CampanhasTable({ campanhas, moeda = "BRL" }: { campanhas: Campanha[]; moeda?: string }) {
  const [col, setCol] = useState<ColCamp>("investimento");
  const [asc, setAsc] = useState(false);
  const linhas = useMemo(() => {
    const val = (c: Campanha) =>
      col === "campanha_nome" ? (c.campanha_nome ?? "") : c.kpis[col] === null ? null : Number(c.kpis[col]);
    return [...campanhas].sort((a, b) => {
      const va = val(a);
      const vb = val(b);
      if (va === null) return 1; // ausentes sempre ao final
      if (vb === null) return -1;
      const r = typeof va === "string" ? va.localeCompare(vb as string) : va - (vb as number);
      return asc ? r : -r;
    });
  }, [campanhas, col, asc]);
  if (!campanhas.length) return <div className="empty">Nenhuma campanha no período.</div>;
  const th = (c: ColCamp, label: string) => (
    <th>
      <button
        className="th-sort"
        onClick={() => {
          if (c === col) setAsc(!asc);
          else {
            setCol(c);
            setAsc(c === "campanha_nome");
          }
        }}
      >
        {label}
        {col === c ? (asc ? " ▲" : " ▼") : ""}
      </button>
    </th>
  );
  const kpis: KpiKey[] = ["investimento", "impressoes", "cliques", "ctr", "cpc", "conversoes", "cpa", "roas"];
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {th("campanha_nome", "Campanha")}
            <th>Plataforma</th>
            {kpis.map((k) => th(k, KPI_LABEL[k]))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((c) => (
            <tr key={`${c.conta_anuncio_id}-${c.campanha_externa_id}`}>
              <td>{c.campanha_nome ?? c.campanha_externa_id}</td>
              <td>{PLATAFORMA_LABEL[c.plataforma]}</td>
              {kpis.map((k) => (
                <td key={k} className="num">
                  {fmtKpi(k, c.kpis[k], moeda)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

import { useEffect, useState } from "react";
import type { Filtros, KpiKey } from "../api/types";
import { KPI_LABEL } from "../lib/format";
import FiltrosBar, { filtrosPadrao } from "./Filtros";
import { AvisoSync, CampanhasTable, KpiCards, SerieChart, useIntegracoes, useMetricas } from "./Metricas";
import { Estado } from "./ui";

export default function VisaoGeral({ clienteId }: { clienteId: string }) {
  const [filtros, setFiltros] = useState<Filtros>(filtrosPadrao);
  const [kpiSerie, setKpiSerie] = useState<KpiKey>("investimento");
  const integracoes = useIntegracoes(clienteId);
  const { resumo, serie, campanhas } = useMetricas(clienteId, filtros);
  const r = resumo.data;
  // Opções de campanha vêm da última consulta sem filtro de campanha, para que a
  // lista não encolha ao selecionar uma delas.
  const [opcoesCampanha, setOpcoesCampanha] = useState<{ id: string; nome: string }[]>([]);
  useEffect(() => {
    if (!filtros.campanha_id && campanhas.data) {
      setOpcoesCampanha(
        campanhas.data.map((c) => ({
          id: c.campanha_externa_id,
          nome: c.campanha_nome ?? c.campanha_externa_id,
        })),
      );
    }
  }, [campanhas.data, filtros.campanha_id]);

  return (
    <div className="stack">
      <FiltrosBar
        filtros={filtros}
        onChange={setFiltros}
        integracoes={integracoes.data ?? []}
        campanhas={opcoesCampanha}
      />
      <Estado carregando={resumo.carregando} erro={resumo.erro}>
        {r && r.integracoes_conectadas === 0 && r.atual.impressoes === 0 ? (
          <div className="empty">
            Nenhuma integração conectada para este cliente. Conecte Meta Ads ou Google Ads na aba
            Integrações para ver as métricas.
          </div>
        ) : (
          r && (
            <>
              <AvisoSync resumo={r} />
              <KpiCards resumo={r} />
              <div className="card">
                <div className="card-header">
                  <h3>Evolução</h3>
                  <select
                    aria-label="Métrica do gráfico"
                    value={kpiSerie}
                    onChange={(e) => setKpiSerie(e.target.value as KpiKey)}
                  >
                    {(Object.keys(KPI_LABEL) as KpiKey[]).map((k) => (
                      <option key={k} value={k}>
                        {KPI_LABEL[k]}
                      </option>
                    ))}
                  </select>
                </div>
                <Estado carregando={serie.carregando} erro={serie.erro}>
                  {serie.data && <SerieChart serie={serie.data} kpi={kpiSerie} />}
                </Estado>
              </div>
              <div className="card">
                <h3>Campanhas</h3>
                <Estado carregando={campanhas.carregando} erro={campanhas.erro}>
                  <CampanhasTable campanhas={campanhas.data ?? []} moeda={r.moedas[0]} />
                </Estado>
              </div>
            </>
          )
        )}
      </Estado>
    </div>
  );
}

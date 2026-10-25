import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Dashboard, Filtros, KpiKey, Widget, WidgetTipo } from "../api/types";
import FiltrosBar, { filtrosPadrao } from "../components/Filtros";
import {
  AvisoSync,
  CampanhasTable,
  KpiCard,
  SerieChart,
  useIntegracoes,
  useMetricas,
} from "../components/Metricas";
import { Confirmar, Estado } from "../components/ui";
import { pode, useAuth } from "../lib/auth";
import { KPI_LABEL } from "../lib/format";
import { useApi } from "../lib/useApi";

const TIPOS: Record<WidgetTipo, string> = {
  kpi: "Card de KPI",
  serie: "Série temporal",
  tabela_campanhas: "Tabela de campanhas",
};

export default function DashboardPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { me } = useAuth();
  const dash = useApi(() => api<Dashboard>(`/dashboards/${id}`), [id]);
  const [filtros, setFiltros] = useState<Filtros>(filtrosPadrao);
  const [editando, setEditando] = useState(false);
  const [rascunho, setRascunho] = useState<Widget[]>([]);
  const [excluindo, setExcluindo] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (dash.data) setFiltros({ ...filtrosPadrao(), ...dash.data.filtros });
  }, [dash.data]);

  const d = dash.data;
  const clienteId = d?.cliente_id ?? "";
  const integracoes = useIntegracoes(clienteId);
  const { resumo, serie, campanhas } = useMetricas(clienteId, filtros);

  const salvar = async () => {
    setErro(null);
    try {
      const { granularidade, comparar, plataforma } = filtros;
      dash.setData(
        await api<Dashboard>(`/dashboards/${id}`, {
          method: "PATCH",
          body: {
            filtros: { granularidade, comparar, plataforma },
            widgets: rascunho.map((w, i) => ({ ...w, ordem: i })),
          },
        }),
      );
      setEditando(false);
    } catch (e) {
      setErro((e as Error).message);
    }
  };

  const widgets = editando ? rascunho : (d?.widgets ?? []);
  const mover = (i: number, delta: number) => {
    const n = [...rascunho];
    const j = i + delta;
    if (j < 0 || j >= n.length) return;
    [n[i], n[j]] = [n[j], n[i]];
    setRascunho(n);
  };

  return (
    <Estado carregando={dash.carregando} erro={dash.erro}>
      {d && (
        <section className="stack">
          <div className="page-header">
            <div>
              <Link to={`/clientes/${d.cliente_id}?aba=dashboards`} className="small">
                ← Voltar ao cliente
              </Link>
              <h1>{d.nome}</h1>
            </div>
            {pode.editar(me?.papel) && (
              <div className="actions">
                {editando ? (
                  <>
                    <button className="btn" onClick={() => setEditando(false)}>
                      Cancelar
                    </button>
                    <button className="btn btn-primary" onClick={salvar}>
                      Salvar layout
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      className="btn"
                      onClick={() => {
                        setRascunho(d.widgets);
                        setEditando(true);
                      }}
                    >
                      Editar widgets
                    </button>
                    <button className="btn btn-danger" onClick={() => setExcluindo(true)}>
                      Excluir
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
          {erro && <p className="alert alert-error">{erro}</p>}
          <FiltrosBar
            filtros={filtros}
            onChange={setFiltros}
            integracoes={integracoes.data ?? []}
            campanhas={[]}
          />
          {editando && (
            <NovoWidget onAdd={(w) => setRascunho([...rascunho, { ...w, ordem: rascunho.length }])} />
          )}
          {resumo.data && <AvisoSync resumo={resumo.data} />}
          {!widgets.length && <div className="empty">Este dashboard ainda não tem widgets.</div>}
          <div className="widgets">
            {widgets.map((w, i) => (
              <div key={w.id ?? `novo-${i}`} className={`widget widget-${w.tipo}`}>
                {editando && (
                  <div className="widget-tools">
                    <button className="btn-icon" aria-label="Mover para cima" onClick={() => mover(i, -1)}>
                      ↑
                    </button>
                    <button className="btn-icon" aria-label="Mover para baixo" onClick={() => mover(i, 1)}>
                      ↓
                    </button>
                    <button
                      className="btn-icon"
                      aria-label="Remover widget"
                      onClick={() => setRascunho(rascunho.filter((_, j) => j !== i))}
                    >
                      ×
                    </button>
                  </div>
                )}
                {w.tipo === "kpi" && resumo.data && (
                  <KpiCard resumo={resumo.data} kpi={w.config.kpi ?? "investimento"} />
                )}
                {w.tipo === "serie" && (
                  <div className="card">
                    <h3>{w.titulo}</h3>
                    {serie.data && <SerieChart serie={serie.data} kpi={w.config.kpi ?? "investimento"} />}
                  </div>
                )}
                {w.tipo === "tabela_campanhas" && (
                  <div className="card">
                    <h3>{w.titulo}</h3>
                    <CampanhasTable campanhas={campanhas.data ?? []} moeda={resumo.data?.moedas[0]} />
                  </div>
                )}
              </div>
            ))}
          </div>
          <Confirmar
            aberto={excluindo}
            titulo="Excluir dashboard"
            mensagem="O dashboard e seus widgets serão excluídos. As métricas não são afetadas."
            acao="Excluir"
            perigo
            onCancelar={() => setExcluindo(false)}
            onConfirmar={async () => {
              await api(`/dashboards/${id}`, { method: "DELETE" });
              navigate(`/clientes/${d.cliente_id}?aba=dashboards`);
            }}
          />
        </section>
      )}
    </Estado>
  );
}

function NovoWidget({ onAdd }: { onAdd: (w: Widget) => void }) {
  const [tipo, setTipo] = useState<WidgetTipo>("kpi");
  const [kpi, setKpi] = useState<KpiKey>("investimento");
  return (
    <div className="toolbar card">
      <select aria-label="Tipo de widget" value={tipo} onChange={(e) => setTipo(e.target.value as WidgetTipo)}>
        {(Object.keys(TIPOS) as WidgetTipo[]).map((t) => (
          <option key={t} value={t}>
            {TIPOS[t]}
          </option>
        ))}
      </select>
      {tipo !== "tabela_campanhas" && (
        <select aria-label="Métrica" value={kpi} onChange={(e) => setKpi(e.target.value as KpiKey)}>
          {(Object.keys(KPI_LABEL) as KpiKey[]).map((k) => (
            <option key={k} value={k}>
              {KPI_LABEL[k]}
            </option>
          ))}
        </select>
      )}
      <button
        className="btn btn-primary"
        onClick={() =>
          onAdd({
            tipo,
            titulo: tipo === "tabela_campanhas" ? "Campanhas" : KPI_LABEL[kpi],
            config: tipo === "tabela_campanhas" ? {} : { kpi },
            posicao: {},
            ordem: 0,
          })
        }
      >
        Adicionar widget
      </button>
    </div>
  );
}

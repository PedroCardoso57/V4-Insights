import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Dashboard } from "../api/types";
import { pode, useAuth } from "../lib/auth";
import { fmtDataHora } from "../lib/format";
import { useApi } from "../lib/useApi";
import { Estado } from "./ui";

export default function DashboardsTab({ clienteId }: { clienteId: string }) {
  const { me } = useAuth();
  const navigate = useNavigate();
  const lista = useApi(() => api<Dashboard[]>("/dashboards", { query: { cliente_id: clienteId } }), [
    clienteId,
  ]);
  const [nome, setNome] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  const criar = async (e: React.FormEvent) => {
    e.preventDefault();
    setErro(null);
    try {
      const d = await api<Dashboard>("/dashboards", {
        method: "POST",
        body: { cliente_id: clienteId, nome: nome.trim() },
      });
      // Widgets iniciais: KPIs principais, série e tabela de campanhas.
      await api(`/dashboards/${d.id}`, {
        method: "PATCH",
        body: {
          widgets: [
            { tipo: "kpi", titulo: "Investimento", config: { kpi: "investimento" } },
            { tipo: "kpi", titulo: "Cliques", config: { kpi: "cliques" } },
            { tipo: "kpi", titulo: "CTR", config: { kpi: "ctr" } },
            { tipo: "serie", titulo: "Investimento por período", config: { kpi: "investimento" } },
            { tipo: "tabela_campanhas", titulo: "Campanhas", config: {} },
          ],
        },
      });
      navigate(`/dashboards/${d.id}`);
    } catch (err) {
      setErro((err as Error).message);
    }
  };

  return (
    <div className="stack">
      {pode.editar(me?.papel) && (
        <form className="toolbar" onSubmit={criar}>
          <input
            placeholder="Nome do novo dashboard"
            aria-label="Nome do novo dashboard"
            value={nome}
            maxLength={160}
            onChange={(e) => setNome(e.target.value)}
          />
          <button className="btn btn-primary" type="submit" disabled={!nome.trim()}>
            Criar dashboard
          </button>
        </form>
      )}
      {erro && <p className="alert alert-error">{erro}</p>}
      <Estado
        carregando={lista.carregando}
        erro={lista.erro}
        vazio={lista.data?.length === 0}
        mensagemVazia="Nenhum dashboard personalizado. A Visão geral mostra os indicadores principais."
      >
        <ul className="list">
          {lista.data?.map((d) => (
            <li key={d.id}>
              <Link to={`/dashboards/${d.id}`}>{d.nome}</Link>
              <span className="muted small">
                {d.widgets.length} widgets · atualizado em {fmtDataHora(d.atualizado_em)}
              </span>
            </li>
          ))}
        </ul>
      </Estado>
    </div>
  );
}

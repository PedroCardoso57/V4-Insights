import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Cliente } from "../api/types";
import ClienteForm from "../components/ClienteForm";
import DashboardsTab from "../components/DashboardsTab";
import EquipeTab from "../components/EquipeTab";
import IntegracoesTab from "../components/IntegracoesTab";
import VisaoGeral from "../components/VisaoGeral";
import { Badge, Confirmar, Estado, Modal } from "../components/ui";
import { pode, useAuth } from "../lib/auth";
import { useApi } from "../lib/useApi";

const ABAS = [
  ["visao", "Visão geral"],
  ["integracoes", "Integrações"],
  ["dashboards", "Dashboards"],
  ["relatorios", "Relatórios"],
  ["equipe", "Equipe"],
] as const;
type Aba = (typeof ABAS)[number][0];

export default function ClienteDetalhePage() {
  const { id = "" } = useParams();
  const { me } = useAuth();
  const [params, setParams] = useSearchParams();
  const aba = (params.get("aba") as Aba) || "visao";
  const [editando, setEditando] = useState(false);
  const [arquivando, setArquivando] = useState(false);
  const { data: cliente, erro, carregando, setData } = useApi(
    () => api<Cliente>(`/clientes/${id}`),
    [id],
  );

  const arquivar = async () => {
    setArquivando(false);
    setData(await api<Cliente>(`/clientes/${id}/arquivar`, { method: "POST" }));
  };

  const abas = ABAS.filter(([k]) => k !== "integracoes" || pode.editar(me?.papel));

  return (
    <Estado carregando={carregando} erro={erro}>
      {cliente && (
        <section>
          <div className="page-header">
            <div>
              <h1>
                {cliente.nome}{" "}
                {cliente.status === "arquivado" && <Badge tom="muted">arquivado</Badge>}
              </h1>
              {cliente.nome_fantasia && <p className="muted">{cliente.nome_fantasia}</p>}
            </div>
            {pode.gerirClientes(me?.papel) && cliente.status === "ativo" && (
              <div className="actions">
                <button className="btn" onClick={() => setEditando(true)}>
                  Editar
                </button>
                <button className="btn btn-danger" onClick={() => setArquivando(true)}>
                  Arquivar
                </button>
              </div>
            )}
          </div>
          <nav className="tabs" role="tablist">
            {abas.map(([k, label]) => (
              <button
                key={k}
                role="tab"
                aria-selected={aba === k}
                className={aba === k ? "tab active" : "tab"}
                onClick={() => setParams({ aba: k })}
              >
                {label}
              </button>
            ))}
          </nav>
          <div className="tab-panel">
            {aba === "visao" && <VisaoGeral clienteId={cliente.id} />}
            {aba === "integracoes" && <IntegracoesTab cliente={cliente} />}
            {aba === "dashboards" && <DashboardsTab clienteId={cliente.id} />}
            {aba === "relatorios" && (
              <div className="empty">Relatórios serão disponibilizados em uma próxima etapa.</div>
            )}
            {aba === "equipe" && <EquipeTab clienteId={cliente.id} />}
          </div>
          <Modal titulo="Editar cliente" aberto={editando} onFechar={() => setEditando(false)}>
            <ClienteForm
              cliente={cliente}
              onSalvo={(c) => {
                setData(c);
                setEditando(false);
              }}
            />
          </Modal>
          <Confirmar
            aberto={arquivando}
            titulo="Arquivar cliente"
            mensagem={
              <>
                Arquivar <strong>{cliente.nome}</strong>? As métricas, dashboards e o histórico
                são preservados, mas novas integrações e sincronizações ficam bloqueadas.
              </>
            }
            acao="Arquivar"
            perigo
            onConfirmar={arquivar}
            onCancelar={() => setArquivando(false)}
          />
        </section>
      )}
    </Estado>
  );
}

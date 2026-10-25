import { useState } from "react";
import { api } from "../api/client";
import type { Auditoria, Page } from "../api/types";
import { Estado, Paginacao } from "../components/ui";
import { fmtDataHora } from "../lib/format";
import { useApi } from "../lib/useApi";

export default function AuditoriaPage() {
  const [page, setPage] = useState(1);
  const [entidade, setEntidade] = useState("");
  const lista = useApi(
    () => api<Page<Auditoria>>("/auditoria", { query: { page, page_size: 50, entidade } }),
    [page, entidade],
  );
  return (
    <section>
      <div className="page-header">
        <h1>Auditoria</h1>
      </div>
      <div className="toolbar">
        <select
          aria-label="Entidade"
          value={entidade}
          onChange={(e) => {
            setEntidade(e.target.value);
            setPage(1);
          }}
        >
          <option value="">Todas as entidades</option>
          <option value="cliente">Clientes</option>
          <option value="usuario">Usuários</option>
          <option value="usuario_cliente">Acessos</option>
          <option value="integracao">Integrações</option>
          <option value="dashboard">Dashboards</option>
        </select>
      </div>
      <Estado carregando={lista.carregando} erro={lista.erro} vazio={lista.data?.items.length === 0}>
        <table className="table">
          <thead>
            <tr>
              <th>Quando</th>
              <th>Ação</th>
              <th>Entidade</th>
              <th>Usuário</th>
              <th>Detalhes</th>
            </tr>
          </thead>
          <tbody>
            {lista.data?.items.map((a) => (
              <tr key={a.id}>
                <td>{fmtDataHora(a.criado_em)}</td>
                <td>{a.acao}</td>
                <td>
                  {a.entidade} <small className="muted">{a.entidade_id}</small>
                </td>
                <td className="small">{a.usuario_id ?? "sistema"}</td>
                <td>
                  <code className="small">{JSON.stringify(a.dados)}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {lista.data && (
          <Paginacao page={page} pageSize={lista.data.page_size} total={lista.data.total} onPage={setPage} />
        )}
      </Estado>
    </section>
  );
}

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Cliente, Page } from "../api/types";
import ClienteForm from "../components/ClienteForm";
import { Badge, Estado, Modal, Paginacao } from "../components/ui";
import { pode, useAuth } from "../lib/auth";
import { fmtData } from "../lib/format";
import { useApi } from "../lib/useApi";

type Ordem = "nome" | "criado_em" | "atualizado_em";

export default function ClientesPage() {
  const { me } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [busca, setBusca] = useState("");
  const [status, setStatus] = useState<"" | "ativo" | "arquivado">("ativo");
  const [page, setPage] = useState(1);
  const [orderBy, setOrderBy] = useState<Ordem>("nome");
  const [order, setOrder] = useState<"asc" | "desc">("asc");
  const [criando, setCriando] = useState(false);

  const { data, erro, carregando } = useApi(
    () =>
      api<Page<Cliente>>("/clientes", {
        query: { search: busca, status, page, page_size: 20, order_by: orderBy, order },
      }),
    [busca, status, page, orderBy, order],
  );

  const ordenar = (col: Ordem) => {
    if (orderBy === col) setOrder(order === "asc" ? "desc" : "asc");
    else {
      setOrderBy(col);
      setOrder("asc");
    }
    setPage(1);
  };
  const seta = (col: Ordem) => (orderBy === col ? (order === "asc" ? " ▲" : " ▼") : "");

  return (
    <section>
      <div className="page-header">
        <h1>Clientes</h1>
        {pode.gerirClientes(me?.papel) && (
          <button className="btn btn-primary" onClick={() => setCriando(true)}>
            Novo cliente
          </button>
        )}
      </div>
      <form
        className="toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          setBusca(search.trim());
          setPage(1);
        }}
      >
        <input
          type="search"
          placeholder="Buscar por nome"
          aria-label="Buscar por nome"
          value={search}
          maxLength={100}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="Status"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as typeof status);
            setPage(1);
          }}
        >
          <option value="ativo">Ativos</option>
          <option value="arquivado">Arquivados</option>
          <option value="">Todos</option>
        </select>
        <button className="btn" type="submit">
          Buscar
        </button>
      </form>
      <Estado
        carregando={carregando}
        erro={erro}
        vazio={data?.items.length === 0}
        mensagemVazia="Nenhum cliente encontrado na sua carteira."
      >
        <table className="table">
          <thead>
            <tr>
              <th>
                <button className="th-sort" onClick={() => ordenar("nome")}>
                  Nome{seta("nome")}
                </button>
              </th>
              <th>Nome fantasia</th>
              <th>Status</th>
              <th>
                <button className="th-sort" onClick={() => ordenar("criado_em")}>
                  Criado em{seta("criado_em")}
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((c) => (
              <tr key={c.id}>
                <td>
                  <Link to={`/clientes/${c.id}`}>{c.nome}</Link>
                </td>
                <td>{c.nome_fantasia ?? "—"}</td>
                <td>
                  <Badge tom={c.status === "ativo" ? "ok" : "muted"}>{c.status}</Badge>
                </td>
                <td>{fmtData(c.criado_em)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && (
          <Paginacao page={page} pageSize={data.page_size} total={data.total} onPage={setPage} />
        )}
      </Estado>
      <Modal titulo="Novo cliente" aberto={criando} onFechar={() => setCriando(false)}>
        <ClienteForm
          onSalvo={(c) => {
            setCriando(false);
            navigate(`/clientes/${c.id}`);
          }}
        />
      </Modal>
    </section>
  );
}

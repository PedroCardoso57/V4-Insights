import { useState } from "react";
import { api } from "../api/client";
import type { Page, Papel, Usuario } from "../api/types";
import { Badge, Estado, Modal, Paginacao } from "../components/ui";
import { pode, useAuth } from "../lib/auth";
import { fmtDataHora, PAPEL_LABEL } from "../lib/format";
import { useApi } from "../lib/useApi";

const PAPEIS = Object.keys(PAPEL_LABEL) as Papel[];

export default function UsuariosPage() {
  const { me } = useAuth();
  const admin = pode.gerirUsuarios(me?.papel);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [busca, setBusca] = useState("");
  const [form, setForm] = useState<Partial<Usuario> | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const lista = useApi(
    () => api<Page<Usuario>>("/usuarios", { query: { page, page_size: 50, search: busca } }),
    [page, busca],
  );

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setErro(null);
    try {
      if (form.id) {
        await api(`/usuarios/${form.id}`, {
          method: "PATCH",
          body: { nome: form.nome, papel: form.papel, ativo: form.ativo },
        });
      } else {
        await api("/usuarios", {
          method: "POST",
          body: { nome: form.nome, email: form.email, papel: form.papel, ativo: true },
        });
      }
      setForm(null);
      lista.recarregar();
    } catch (err) {
      setErro((err as Error).message);
    }
  };

  return (
    <section>
      <div className="page-header">
        <h1>Usuários</h1>
        {admin && (
          <button className="btn btn-primary" onClick={() => setForm({ papel: "analista" })}>
            Novo usuário
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
          aria-label="Buscar usuário"
          placeholder="Buscar por nome ou e-mail"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button className="btn" type="submit">
          Buscar
        </button>
      </form>
      <Estado carregando={lista.carregando} erro={lista.erro} vazio={lista.data?.items.length === 0}>
        <table className="table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>E-mail</th>
              <th>Papel</th>
              <th>Status</th>
              <th>Último acesso</th>
              {admin && <th></th>}
            </tr>
          </thead>
          <tbody>
            {lista.data?.items.map((u) => (
              <tr key={u.id}>
                <td>{u.nome}</td>
                <td>{u.email}</td>
                <td>{PAPEL_LABEL[u.papel]}</td>
                <td>
                  <Badge tom={u.ativo ? "ok" : "muted"}>{u.ativo ? "ativo" : "inativo"}</Badge>{" "}
                  {!u.vinculado_google && <Badge tom="warn">sem login</Badge>}
                </td>
                <td>{fmtDataHora(u.ultimo_login_em)}</td>
                {admin && (
                  <td>
                    <button className="btn btn-small" onClick={() => setForm(u)}>
                      Editar
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {lista.data && (
          <Paginacao page={page} pageSize={lista.data.page_size} total={lista.data.total} onPage={setPage} />
        )}
      </Estado>
      <Modal titulo={form?.id ? "Editar usuário" : "Novo usuário"} aberto={!!form} onFechar={() => setForm(null)}>
        {form && (
          <form className="form" onSubmit={salvar}>
            <label>
              Nome
              <input
                required
                minLength={2}
                maxLength={160}
                value={form.nome ?? ""}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
              />
            </label>
            {!form.id && (
              <label>
                E-mail Google corporativo
                <input
                  type="email"
                  required
                  value={form.email ?? ""}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
              </label>
            )}
            <label>
              Papel
              <select value={form.papel} onChange={(e) => setForm({ ...form, papel: e.target.value as Papel })}>
                {PAPEIS.map((p) => (
                  <option key={p} value={p}>
                    {PAPEL_LABEL[p]}
                  </option>
                ))}
              </select>
            </label>
            {form.id && (
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={form.ativo ?? true}
                  onChange={(e) => setForm({ ...form, ativo: e.target.checked })}
                />
                Ativo
              </label>
            )}
            {erro && <p className="alert alert-error">{erro}</p>}
            <button className="btn btn-primary" type="submit">
              Salvar
            </button>
          </form>
        )}
      </Modal>
    </section>
  );
}

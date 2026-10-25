import { useState } from "react";
import { api } from "../api/client";
import type { Membro, Page, Usuario } from "../api/types";
import { pode, useAuth } from "../lib/auth";
import { fmtData, PAPEL_LABEL } from "../lib/format";
import { useApi } from "../lib/useApi";
import { Badge, Confirmar, Estado } from "./ui";

export default function EquipeTab({ clienteId }: { clienteId: string }) {
  const { me } = useAuth();
  const gerir = pode.gerirClientes(me?.papel);
  const membros = useApi(() => api<Membro[]>(`/clientes/${clienteId}/usuarios`), [clienteId]);
  const usuarios = useApi(
    () =>
      gerir
        ? api<Page<Usuario>>("/usuarios", { query: { ativo: true, page_size: 200 } })
        : Promise.resolve(null),
    [gerir],
  );
  const [novo, setNovo] = useState("");
  const [removendo, setRemovendo] = useState<Membro | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const ids = new Set(membros.data?.map((m) => m.id));
  const candidatos = usuarios.data?.items.filter((u) => !ids.has(u.id)) ?? [];

  const alterar = async (usuarioId: string, method: "PUT" | "DELETE") => {
    setErro(null);
    try {
      await api(`/usuarios/${usuarioId}/clientes/${clienteId}`, { method });
      membros.recarregar();
    } catch (e) {
      setErro((e as Error).message);
    }
  };

  return (
    <div className="stack">
      {gerir && (
        <form
          className="toolbar"
          onSubmit={(e) => {
            e.preventDefault();
            if (novo) alterar(novo, "PUT").then(() => setNovo(""));
          }}
        >
          <select aria-label="Colaborador" value={novo} onChange={(e) => setNovo(e.target.value)}>
            <option value="">Adicionar colaborador…</option>
            {candidatos.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nome} ({PAPEL_LABEL[u.papel]})
              </option>
            ))}
          </select>
          <button className="btn btn-primary" type="submit" disabled={!novo}>
            Adicionar
          </button>
        </form>
      )}
      {erro && <p className="alert alert-error">{erro}</p>}
      <Estado
        carregando={membros.carregando}
        erro={membros.erro}
        vazio={membros.data?.length === 0}
        mensagemVazia="Nenhum colaborador atribuído. Administradores têm acesso a todos os clientes."
      >
        <table className="table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>E-mail</th>
              <th>Papel</th>
              <th>Desde</th>
              {gerir && <th></th>}
            </tr>
          </thead>
          <tbody>
            {membros.data?.map((m) => (
              <tr key={m.id}>
                <td>
                  {m.nome} {!m.ativo && <Badge tom="muted">inativo</Badge>}
                </td>
                <td>{m.email}</td>
                <td>{PAPEL_LABEL[m.papel]}</td>
                <td>{fmtData(m.atribuido_em)}</td>
                {gerir && (
                  <td>
                    <button className="btn btn-small btn-danger" onClick={() => setRemovendo(m)}>
                      Remover
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </Estado>
      <Confirmar
        aberto={!!removendo}
        titulo="Remover acesso"
        mensagem={`Remover ${removendo?.nome} da carteira deste cliente?`}
        acao="Remover"
        perigo
        onCancelar={() => setRemovendo(null)}
        onConfirmar={() => {
          const alvo = removendo;
          setRemovendo(null);
          if (alvo) alterar(alvo.id, "DELETE");
        }}
      />
    </div>
  );
}

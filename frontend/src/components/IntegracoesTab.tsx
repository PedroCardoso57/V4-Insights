import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Cliente, ContaDisponivel, Integracao, Plataforma, SyncJob } from "../api/types";
import { fmtData, fmtDataHora, PLATAFORMA_LABEL } from "../lib/format";
import { useApi } from "../lib/useApi";
import { Badge, Confirmar, Estado, Modal } from "./ui";

const STATUS_TOM: Record<Integracao["status"], string> = {
  ativa: "ok",
  pendente: "warn",
  pausada: "muted",
  erro: "error",
  revogada: "muted",
};

const ERROS: Record<string, string> = {
  autorizacao_negada: "A autorização foi cancelada ou negada no provedor.",
  conexao_recusada: "O provedor recusou a conexão (verifique permissões e escopos).",
  cliente_arquivado: "Cliente arquivado não aceita novas integrações.",
};

export default function IntegracoesTab({ cliente }: { cliente: Cliente }) {
  const [params] = useSearchParams();
  const erroCallback = params.get("erro");
  const [erro, setErro] = useState<string | null>(null);
  const [selecionando, setSelecionando] = useState<Integracao | null>(null);
  const [revogando, setRevogando] = useState<Integracao | null>(null);
  const [jobsDe, setJobsDe] = useState<Integracao | null>(null);
  const lista = useApi(
    () => api<Integracao[]>("/integracoes", { query: { cliente_id: cliente.id } }),
    [cliente.id],
  );
  const arquivado = cliente.status === "arquivado";

  const executar = async (fn: () => Promise<unknown>) => {
    setErro(null);
    try {
      await fn();
      lista.recarregar();
    } catch (e) {
      setErro((e as Error).message);
    }
  };

  const conectar = (plataforma: Plataforma, integracao_id?: string) =>
    executar(async () => {
      const r = await api<{ authorization_url: string }>(`/integracoes/${plataforma}/autorizar`, {
        method: "POST",
        body: { cliente_id: cliente.id, integracao_id },
      });
      window.location.assign(r.authorization_url);
    });

  return (
    <div className="stack">
      {erroCallback && <p className="alert alert-error">{ERROS[erroCallback] ?? "Falha na conexão."}</p>}
      {erro && <p className="alert alert-error">{erro}</p>}
      {!arquivado && (
        <div className="actions">
          <button className="btn btn-primary" onClick={() => conectar("meta")}>
            Conectar Meta Ads
          </button>
          <button className="btn btn-primary" onClick={() => conectar("google_ads")}>
            Conectar Google Ads
          </button>
        </div>
      )}
      <p className="muted small">
        O acesso às APIs depende das permissões concedidas na conta do anunciante e das políticas e
        quotas dos provedores. Conversões só são exibidas após mapear as ações correspondentes.
      </p>
      <Estado
        carregando={lista.carregando}
        erro={lista.erro}
        vazio={lista.data?.length === 0}
        mensagemVazia="Nenhuma integração conectada."
      >
        {lista.data?.map((i) => (
          <div className="card" key={i.id}>
            <div className="card-header">
              <h3>
                {PLATAFORMA_LABEL[i.plataforma]} <Badge tom={STATUS_TOM[i.status]}>{i.status}</Badge>
              </h3>
              <div className="actions">
                {i.status !== "revogada" && (
                  <button className="btn btn-small" onClick={() => setSelecionando(i)} disabled={arquivado}>
                    Contas
                  </button>
                )}
                {i.status === "ativa" && (
                  <>
                    <button
                      className="btn btn-small"
                      onClick={() =>
                        executar(() => api(`/integracoes/${i.id}/sincronizar`, { method: "POST" }))
                      }
                    >
                      Sincronizar agora
                    </button>
                    <button
                      className="btn btn-small"
                      onClick={() => executar(() => api(`/integracoes/${i.id}/pausar`, { method: "POST" }))}
                    >
                      Pausar
                    </button>
                  </>
                )}
                {i.status === "pausada" && (
                  <button
                    className="btn btn-small"
                    onClick={() => executar(() => api(`/integracoes/${i.id}/retomar`, { method: "POST" }))}
                  >
                    Retomar
                  </button>
                )}
                {(i.status === "erro" || i.status === "revogada") && !arquivado && (
                  <button className="btn btn-small btn-primary" onClick={() => conectar(i.plataforma, i.id)}>
                    Reconectar
                  </button>
                )}
                <button className="btn btn-small" onClick={() => setJobsDe(i)}>
                  Execuções
                </button>
                {i.status !== "revogada" && (
                  <button className="btn btn-small btn-danger" onClick={() => setRevogando(i)}>
                    Revogar
                  </button>
                )}
              </div>
            </div>
            {i.ultimo_erro && <p className="alert alert-error small">{i.ultimo_erro}</p>}
            {i.status === "pendente" && (
              <p className="alert alert-warn small">Selecione as contas de anúncio para iniciar a coleta.</p>
            )}
            {i.contas.length > 0 && (
              <table className="table compact">
                <thead>
                  <tr>
                    <th>Conta</th>
                    <th>ID</th>
                    <th>Moeda / fuso</th>
                    <th>Dados até</th>
                    <th>Última sincronização</th>
                    <th>Conversões</th>
                  </tr>
                </thead>
                <tbody>
                  {i.contas.map((c) => (
                    <tr key={c.id} className={c.ativa ? "" : "muted"}>
                      <td>
                        {c.nome} {!c.ativa && <Badge tom="muted">inativa</Badge>}
                      </td>
                      <td>{c.id_externo}</td>
                      <td>
                        {c.moeda ?? "—"} / {c.fuso ?? "—"}
                      </td>
                      <td>{fmtData(c.dados_ate)}</td>
                      <td>{fmtDataHora(c.ultima_sincronizacao_em)}</td>
                      <td>{c.mapeamento_conversoes.action_types?.join(", ") || "não mapeadas"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ))}
      </Estado>
      {selecionando && (
        <SelecionarContas
          integracao={selecionando}
          onFechar={() => setSelecionando(null)}
          onSalvo={() => {
            setSelecionando(null);
            lista.recarregar();
          }}
        />
      )}
      {jobsDe && <Jobs integracao={jobsDe} onFechar={() => setJobsDe(null)} />}
      <Confirmar
        aberto={!!revogando}
        titulo="Revogar integração"
        mensagem="A credencial será removida e novas coletas ficam bloqueadas. Os dados já coletados são preservados."
        acao="Revogar"
        perigo
        onCancelar={() => setRevogando(null)}
        onConfirmar={() => {
          const alvo = revogando;
          setRevogando(null);
          if (alvo) executar(() => api(`/integracoes/${alvo.id}/revogar`, { method: "POST" }));
        }}
      />
    </div>
  );
}

function SelecionarContas({
  integracao,
  onFechar,
  onSalvo,
}: {
  integracao: Integracao;
  onFechar: () => void;
  onSalvo: () => void;
}) {
  const existentes = Object.fromEntries(integracao.contas.map((c) => [c.id_externo, c]));
  const disponiveis = useApi(
    () => api<ContaDisponivel[]>(`/integracoes/${integracao.id}/contas`),
    [integracao.id],
  );
  const [marcadas, setMarcadas] = useState<Set<string>>(
    () => new Set(integracao.contas.filter((c) => c.ativa).map((c) => c.id_externo)),
  );
  const [dias, setDias] = useState(90);
  const [acoes, setAcoes] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      integracao.contas.map((c) => [c.id_externo, (c.mapeamento_conversoes.action_types ?? []).join(", ")]),
    ),
  );
  const [erro, setErro] = useState<string | null>(null);

  const salvar = async () => {
    setErro(null);
    try {
      await api(`/integracoes/${integracao.id}/contas`, {
        method: "POST",
        body: {
          contas: [...marcadas].map((id) => {
            const tipos = (acoes[id] ?? "")
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean);
            const atual = existentes[id]?.mapeamento_conversoes.action_types ?? [];
            const mudou = tipos.join(",") !== atual.join(",");
            return {
              id_externo: id,
              carga_historica_dias: existentes[id] ? undefined : dias,
              // Sem preenchimento numa conta nova, vale o padrão do provedor.
              mapeamento_conversoes:
                mudou && (tipos.length || existentes[id]) ? { action_types: tipos } : undefined,
            };
          }),
        },
      });
      onSalvo();
    } catch (e) {
      setErro((e as Error).message);
    }
  };

  return (
    <Modal
      titulo={`Contas — ${PLATAFORMA_LABEL[integracao.plataforma]}`}
      aberto
      onFechar={onFechar}
      rodape={
        <>
          <button className="btn" onClick={onFechar}>
            Cancelar
          </button>
          <button className="btn btn-primary" disabled={!marcadas.size} onClick={salvar}>
            Salvar seleção
          </button>
        </>
      }
    >
      <Estado
        carregando={disponiveis.carregando}
        erro={disponiveis.erro}
        vazio={disponiveis.data?.length === 0}
        mensagemVazia="Nenhuma conta autorizada encontrada para este acesso."
      >
        <label>
          Carga histórica para contas novas (dias)
          <input
            type="number"
            min={1}
            max={1095}
            value={dias}
            onChange={(e) => setDias(Math.min(1095, Math.max(1, Number(e.target.value) || 1)))}
          />
        </label>
        <table className="table compact">
          <thead>
            <tr>
              <th></th>
              <th>Conta</th>
              <th>Moeda</th>
              <th title="Tipos de ação contados como conversão (separados por vírgula)">Ações de conversão</th>
            </tr>
          </thead>
          <tbody>
            {disponiveis.data?.map((c) => (
              <tr key={c.id_externo}>
                <td>
                  <input
                    type="checkbox"
                    aria-label={`Selecionar ${c.nome}`}
                    checked={marcadas.has(c.id_externo)}
                    onChange={(e) => {
                      const n = new Set(marcadas);
                      if (e.target.checked) n.add(c.id_externo);
                      else n.delete(c.id_externo);
                      setMarcadas(n);
                    }}
                  />
                </td>
                <td>
                  {c.nome} <small className="muted">{c.id_externo}</small>
                </td>
                <td>{c.moeda ?? "—"}</td>
                <td>
                  <input
                    placeholder={integracao.plataforma === "meta" ? "ex.: purchase, lead" : "conversions"}
                    value={acoes[c.id_externo] ?? ""}
                    onChange={(e) => setAcoes({ ...acoes, [c.id_externo]: e.target.value })}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {erro && <p className="alert alert-error">{erro}</p>}
      </Estado>
    </Modal>
  );
}

function Jobs({ integracao, onFechar }: { integracao: Integracao; onFechar: () => void }) {
  const jobs = useApi(() => api<SyncJob[]>(`/integracoes/${integracao.id}/jobs`), [integracao.id]);
  const contas = Object.fromEntries(integracao.contas.map((c) => [c.id, c.nome]));
  return (
    <Modal titulo="Execuções de sincronização" aberto onFechar={onFechar}>
      <Estado carregando={jobs.carregando} erro={jobs.erro} vazio={jobs.data?.length === 0}>
        <table className="table compact">
          <thead>
            <tr>
              <th>Criado</th>
              <th>Conta</th>
              <th>Tipo</th>
              <th>Intervalo</th>
              <th>Status</th>
              <th>Linhas</th>
              <th>Tentativas</th>
              <th>Erro</th>
            </tr>
          </thead>
          <tbody>
            {jobs.data?.map((j) => (
              <tr key={j.id}>
                <td>{fmtDataHora(j.criado_em)}</td>
                <td>{contas[j.conta_anuncio_id] ?? "—"}</td>
                <td>{j.tipo}</td>
                <td>
                  {fmtData(j.data_inicio)} – {fmtData(j.data_fim)}
                </td>
                <td>{j.status}</td>
                <td className="num">{j.linhas}</td>
                <td className="num">{j.tentativas}</td>
                <td className="small">{j.erro ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Estado>
    </Modal>
  );
}

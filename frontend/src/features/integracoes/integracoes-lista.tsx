"use client";

import { HistoryIcon, InfoIcon, ListChecksIcon, PauseIcon, PlayIcon, PlugZapIcon, RefreshCwIcon, UnplugIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Confirmar } from "@/components/confirmar";
import { Consulta, mensagemDeErro, Vazio } from "@/components/estado";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fmtData, fmtDataHora, PLATAFORMA_LABEL, PLATAFORMAS, type Plataforma } from "@/lib/format";
import { useMe } from "@/hooks/use-me";
import { pode } from "@/lib/permissoes";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api/client";

import { STATUS_INTEGRACAO as STATUS } from "./alertas";
import { useAcaoIntegracao, useAutorizar, useIntegracoes, type Integracao } from "./api";
import { ChavesDialog } from "./chaves-dialog";
import { JobsDialog } from "./jobs-dialog";
import { SelecionarContasDialog } from "./selecionar-contas-dialog";

const CONECTORES: Record<Plataforma, { sigla: string; tile: string; categoria: string; descricao: string }> = {
  meta_ads: {
    sigla: "MA",
    tile: "bg-info-soft text-info",
    categoria: "Mídia paga",
    descricao: "Business Managers, contas de anúncio, campanhas, conjuntos e métricas de conversão (escopo ads_read).",
  },
  google_ads: {
    sigla: "GA",
    tile: "bg-primary-soft text-primary-ink",
    categoria: "Mídia paga",
    descricao: "Contas e MCC, campanhas de Pesquisa, Performance Max, Display e YouTube com valor de conversão.",
  },
  linkedin_ads: {
    sigla: "LI",
    tile: "bg-success-soft text-success",
    categoria: "Mídia paga",
    descricao: "Contas do Campaign Manager, grupos de campanhas, campanhas e criativos com conversões e leads (escopos r_ads e r_ads_reporting).",
  },
  tiktok_ads: {
    sigla: "TT",
    tile: "bg-secondary text-foreground",
    categoria: "Mídia paga",
    descricao: "Contas de anunciante do TikTok for Business, campanhas, grupos de anúncios e anúncios com conversões e valor de compra.",
  },
};

function Selo({ plataforma }: { plataforma: Plataforma }) {
  const c = CONECTORES[plataforma];
  return (
    <span aria-hidden className={cn("flex size-10 shrink-0 items-center justify-center rounded-xl text-xs font-bold", c.tile)}>
      {c.sigla}
    </span>
  );
}

export function IntegracoesLista({ clienteId, arquivado, mostrarCliente }: { clienteId?: string; arquivado?: boolean; mostrarCliente?: (id: string) => string }) {
  const q = useIntegracoes(clienteId);
  const autorizar = useAutorizar();
  const acao = useAcaoIntegracao();
  const [contasDe, setContasDe] = useState<Integracao | null>(null);
  const [jobsDe, setJobsDe] = useState<Integracao | null>(null);
  const [revogando, setRevogando] = useState<Integracao | null>(null);
  const [semChaves, setSemChaves] = useState<Plataforma | null>(null);
  const admin = pode.gerirChaves(useMe().data?.papel);

  const conectar = (plataforma: Plataforma, integracaoId?: string) =>
    clienteId &&
    autorizar.mutate(
      { plataforma, clienteId, integracaoId },
      {
        onError: (e) => {
          if (e instanceof ApiError && e.code === "PROVIDER_NOT_CONFIGURED") {
            if (admin) return setSemChaves(plataforma);
            return toast.error(`${PLATAFORMA_LABEL[plataforma]} ainda não está configurado. Peça a um administrador ou gestor para cadastrar as chaves.`);
          }
          toast.error(mensagemDeErro(e));
        },
      },
    );
  const executar = (id: string, a: "sincronizar" | "pausar" | "retomar" | "revogar", ok: string) =>
    acao.mutate({ id, acao: a }, { onSuccess: () => toast.success(ok), onError: (e) => toast.error(mensagemDeErro(e)) });

  return (
    <div className="grid gap-5">
      {clienteId && !arquivado && (
        <div className="grid gap-4 md:grid-cols-2">
          {PLATAFORMAS.map((p) => (
            <Card key={p} className="flex flex-col p-5">
              <div className="flex items-center gap-3">
                <Selo plataforma={p} />
                <div>
                  <h3 className="text-sm font-semibold">{PLATAFORMA_LABEL[p]}</h3>
                  <p className="text-xs text-muted-foreground">{CONECTORES[p].categoria}</p>
                </div>
              </div>
              <p className="mt-3 mb-4 text-[13px] leading-relaxed text-text-secondary">{CONECTORES[p].descricao}</p>
              <div className="mt-auto flex justify-end border-t pt-4">
                <Button className="w-full sm:w-auto" onClick={() => conectar(p)} disabled={autorizar.isPending}>
                  <PlugZapIcon /> Conectar {PLATAFORMA_LABEL[p]}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
      <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
        <InfoIcon className="mt-px size-3.5 shrink-0 text-info" aria-hidden />
        O acesso depende das permissões concedidas na conta do anunciante e das políticas e quotas de cada provedor.
      </p>
      <Consulta
        query={q}
        vazio={(d) =>
          d.items.length === 0 && (
            <Vazio titulo="Nenhuma integração conectada">
              {clienteId ? "Conecte Meta Ads, Google Ads, LinkedIn Ads ou TikTok Ads para começar a coletar métricas." : "Abra um cliente para conectar suas contas de anúncio."}
            </Vazio>
          )
        }
      >
        {(d) => (
          <div className="grid gap-5">
            {d.items.map((i) => {
              const ativas = i.contas.filter((c) => c.ativa).length;
              return (
                <Card key={i.id} className="overflow-hidden">
                  <div className="flex items-start justify-between gap-3 p-4 pb-3 sm:p-5 sm:pb-4">
                    <div className="flex min-w-0 items-center gap-3">
                      <Selo plataforma={i.plataforma} />
                      <div className="grid min-w-0 gap-0.5">
                        <h3 className="text-sm font-semibold">{PLATAFORMA_LABEL[i.plataforma]}</h3>
                        <p className="text-xs text-muted-foreground">
                          {CONECTORES[i.plataforma].categoria} · {ativas} {ativas === 1 ? "conta ativa" : "contas ativas"}
                          {mostrarCliente && (
                            <>
                              {" · "}
                              <a className="font-medium text-text-secondary underline-offset-2 hover:underline" href={mostrarCliente(i.cliente_id)}>
                                ver cliente
                              </a>
                            </>
                          )}
                        </p>
                      </div>
                    </div>
                    <Badge ponto variant={STATUS[i.status].variant}>{STATUS[i.status].label}</Badge>
                  </div>

                  <div className="grid gap-3 px-4 pb-4 sm:px-5 sm:pb-5">
                    <dl className="grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-2 rounded-xl border bg-subtle p-3.5 text-xs sm:grid-cols-[8rem_1fr]">
                      <dt className="text-muted-foreground">Última sinc.</dt>
                      <dd className="text-right font-mono-num font-semibold">{fmtDataHora(i.ultima_sincronizacao_em)}</dd>
                      {i.escopos.length > 0 && (
                        <>
                          <dt className="text-muted-foreground">Escopos OAuth</dt>
                          <dd className="flex flex-wrap justify-end gap-1">
                            {i.escopos.map((e) => (
                              <code key={e} className="rounded border bg-card px-1.5 py-0.5 font-mono-num text-[10px] text-text-secondary">
                                {e}
                              </code>
                            ))}
                          </dd>
                        </>
                      )}
                    </dl>
                    {i.erro_sincronizacao && <Alert variant="destructive">{i.erro_sincronizacao}</Alert>}
                    {i.status === "pendente" && <Alert variant="warning">Selecione as contas de anúncio para iniciar a coleta.</Alert>}
                    {i.contas.length > 0 && (
                      <div className="overflow-hidden rounded-xl border">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Conta</TableHead>
                              <TableHead>ID</TableHead>
                              <TableHead>Moeda / fuso</TableHead>
                              <TableHead>Dados até</TableHead>
                              <TableHead>Última sincronização</TableHead>
                              <TableHead>Conversões mapeadas</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {i.contas.map((c) => (
                              <TableRow key={c.id} className={c.ativa ? "" : "text-muted-foreground"}>
                                <TableCell>
                                  <span className="font-medium">{c.nome}</span> {!c.ativa && <Badge>inativa</Badge>}
                                </TableCell>
                                <TableCell className="font-mono-num text-xs">{c.conta_externa_id}</TableCell>
                                <TableCell>{c.moeda} / {c.fuso_horario}</TableCell>
                                <TableCell className="font-mono-num text-xs">{fmtData(c.dados_ate)}</TableCell>
                                <TableCell className="font-mono-num text-xs">{fmtDataHora(c.ultima_sincronizacao_em)}</TableCell>
                                <TableCell>
                                  {(c.mapeamento_conversoes as { action_types?: string[] }).action_types?.join(", ") || (
                                    <span className="text-muted-foreground">não mapeadas</span>
                                  )}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2 border-t bg-subtle/60 px-4 py-3.5 sm:flex sm:flex-wrap sm:items-center sm:justify-end sm:px-5 [&>*:last-child:nth-child(odd)]:col-span-2">
                    {i.status !== "revogada" && (
                      <Button variant="outline" size="sm" onClick={() => setContasDe(i)} disabled={arquivado}>
                        <ListChecksIcon /> Contas
                      </Button>
                    )}
                    {i.status === "conectada" && (
                      <>
                        <Button variant="outline" size="sm" onClick={() => executar(i.id, "sincronizar", "Sincronização solicitada.")}>
                          <RefreshCwIcon /> Reprocessar
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => executar(i.id, "pausar", "Integração pausada.")}>
                          <PauseIcon /> Pausar
                        </Button>
                      </>
                    )}
                    {i.status === "pausada" && (
                      <Button variant="outline" size="sm" onClick={() => executar(i.id, "retomar", "Integração retomada.")}>
                        <PlayIcon /> Retomar
                      </Button>
                    )}
                    <Button variant="outline" size="sm" onClick={() => setJobsDe(i)}>
                      <HistoryIcon /> Execuções
                    </Button>
                    {i.status !== "revogada" && (
                      <Button variant="destructive" size="sm" onClick={() => setRevogando(i)}>
                        <UnplugIcon /> Revogar
                      </Button>
                    )}
                    {(i.status === "erro" || i.status === "revogada") && !arquivado && clienteId && (
                      <Button size="sm" onClick={() => conectar(i.plataforma, i.id)}>
                        <PlugZapIcon /> Reconectar
                      </Button>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </Consulta>
      <ChavesDialog
        plataforma={semChaves}
        onClose={() => setSemChaves(null)}
        onConfigurado={(p) => {
          setSemChaves(null);
          conectar(p);
        }}
      />
      <SelecionarContasDialog integracao={contasDe} onClose={() => setContasDe(null)} />
      <JobsDialog integracao={jobsDe} onClose={() => setJobsDe(null)} />
      <Confirmar
        aberto={!!revogando}
        onAberto={(v) => !v && setRevogando(null)}
        titulo="Revogar integração"
        descricao="A credencial será removida e novas coletas ficam bloqueadas. Os dados já coletados são preservados."
        acao="Revogar"
        perigo
        onConfirmar={() => revogando && executar(revogando.id, "revogar", "Integração revogada.")}
      />
    </div>
  );
}

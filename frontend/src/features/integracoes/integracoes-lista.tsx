"use client";

import { HistoryIcon, ListChecksIcon, PauseIcon, PlayIcon, PlugZapIcon, RefreshCwIcon, UnplugIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Confirmar } from "@/components/confirmar";
import { Consulta, mensagemDeErro, Vazio } from "@/components/estado";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fmtData, fmtDataHora, PLATAFORMA_LABEL, type Plataforma } from "@/lib/format";

import { useAcaoIntegracao, useAutorizar, useIntegracoes, type Integracao } from "./api";
import { JobsDialog } from "./jobs-dialog";
import { SelecionarContasDialog } from "./selecionar-contas-dialog";

const STATUS: Record<Integracao["status"], { label: string; variant: "success" | "warning" | "secondary" | "destructive" }> = {
  conectada: { label: "conectada", variant: "success" },
  pendente: { label: "aguardando contas", variant: "warning" },
  pausada: { label: "pausada", variant: "secondary" },
  erro: { label: "requer reconexão", variant: "destructive" },
  revogada: { label: "revogada", variant: "secondary" },
};

export function IntegracoesLista({ clienteId, arquivado, mostrarCliente }: { clienteId?: string; arquivado?: boolean; mostrarCliente?: (id: string) => string }) {
  const q = useIntegracoes(clienteId);
  const autorizar = useAutorizar();
  const acao = useAcaoIntegracao();
  const [contasDe, setContasDe] = useState<Integracao | null>(null);
  const [jobsDe, setJobsDe] = useState<Integracao | null>(null);
  const [revogando, setRevogando] = useState<Integracao | null>(null);

  const conectar = (plataforma: Plataforma, integracaoId?: string) =>
    clienteId &&
    autorizar.mutate({ plataforma, clienteId, integracaoId }, { onError: (e) => toast.error(mensagemDeErro(e)) });
  const executar = (id: string, a: "sincronizar" | "pausar" | "retomar" | "revogar", ok: string) =>
    acao.mutate({ id, acao: a }, { onSuccess: () => toast.success(ok), onError: (e) => toast.error(mensagemDeErro(e)) });

  return (
    <div className="grid gap-4">
      {clienteId && !arquivado && (
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => conectar("meta_ads")} disabled={autorizar.isPending}>
            <PlugZapIcon /> Conectar Meta Ads
          </Button>
          <Button onClick={() => conectar("google_ads")} disabled={autorizar.isPending}>
            <PlugZapIcon /> Conectar Google Ads
          </Button>
        </div>
      )}
      <p className="text-xs text-muted-foreground">
        O acesso depende das permissões concedidas na conta do anunciante e das políticas e quotas de cada provedor.
      </p>
      <Consulta
        query={q}
        vazio={(d) =>
          d.items.length === 0 && (
            <Vazio titulo="Nenhuma integração conectada">
              {clienteId ? "Conecte Meta Ads ou Google Ads para começar a coletar métricas." : "Abra um cliente para conectar suas contas de anúncio."}
            </Vazio>
          )
        }
      >
        {(d) => (
          <div className="grid gap-4">
            {d.items.map((i) => (
              <Card key={i.id}>
                <CardHeader>
                  <div className="grid gap-1">
                    <CardTitle className="flex flex-wrap items-center gap-2">
                      {PLATAFORMA_LABEL[i.plataforma]} <Badge variant={STATUS[i.status].variant}>{STATUS[i.status].label}</Badge>
                    </CardTitle>
                    <p className="text-xs text-muted-foreground">
                      {mostrarCliente && <a className="underline" href={mostrarCliente(i.cliente_id)}>ver cliente</a>}
                      {mostrarCliente && " · "}Última sincronização: {fmtDataHora(i.ultima_sincronizacao_em)}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
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
                    {(i.status === "erro" || i.status === "revogada") && !arquivado && clienteId && (
                      <Button size="sm" onClick={() => conectar(i.plataforma, i.id)}>
                        <PlugZapIcon /> Reconectar
                      </Button>
                    )}
                    <Button variant="outline" size="sm" onClick={() => setJobsDe(i)}>
                      <HistoryIcon /> Execuções
                    </Button>
                    {i.status !== "revogada" && (
                      <Button variant="outline" size="sm" className="text-destructive" onClick={() => setRevogando(i)}>
                        <UnplugIcon /> Revogar
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="grid gap-3">
                  {i.erro_sincronizacao && <Alert variant="destructive">{i.erro_sincronizacao}</Alert>}
                  {i.status === "pendente" && <Alert variant="warning">Selecione as contas de anúncio para iniciar a coleta.</Alert>}
                  {i.contas.length > 0 && (
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
                              {c.nome} {!c.ativa && <Badge>inativa</Badge>}
                            </TableCell>
                            <TableCell className="tabular-nums">{c.conta_externa_id}</TableCell>
                            <TableCell>{c.moeda} / {c.fuso_horario}</TableCell>
                            <TableCell>{fmtData(c.dados_ate)}</TableCell>
                            <TableCell>{fmtDataHora(c.ultima_sincronizacao_em)}</TableCell>
                            <TableCell>
                              {(c.mapeamento_conversoes as { action_types?: string[] }).action_types?.join(", ") || (
                                <span className="text-muted-foreground">não mapeadas</span>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </Consulta>
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

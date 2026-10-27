"use client";

import { ChevronRightIcon, InfoIcon, RefreshCwIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { Consulta, Vazio } from "@/components/estado";
import { Inicial } from "@/components/inicial";
import { PageHeader } from "@/components/page-header";
import { PlataformaBadge } from "@/components/plataforma-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useClientes } from "@/features/clientes/api";
import { MOTIVO_LABEL, STATUS_INTEGRACAO, useAlertasIntegracao } from "@/features/integracoes/alertas";
import { useMe } from "@/hooks/use-me";
import { fmtData, fmtDataHora, fmtNumero } from "@/lib/format";
import { pode } from "@/lib/permissoes";

function Indicador({ rotulo, valor, rodape, dica }: { rotulo: string; valor: ReactNode; rodape: ReactNode; dica: string }) {
  return (
    <Card className="flex flex-col p-4">
      <span className="flex items-center justify-between gap-2 text-xs font-medium text-muted-foreground">
        {rotulo}
        <InfoIcon className="size-3.5 text-faint" aria-label={dica} />
      </span>
      <strong className="mt-2.5 mb-3 font-mono-num text-2xl font-semibold">{valor}</strong>
      <span className="mt-auto border-t pt-2.5 text-[11px] text-muted-foreground">{rodape}</span>
    </Card>
  );
}

export default function InicioPage() {
  const me = useMe().data;
  const editor = pode.editar(me?.papel);
  const clientes = useClientes({ status: "ativo", page_size: 12, order_by: "atualizado_em", order: "desc" });
  const { query: integracoes, alertas } = useAlertasIntegracao();
  const nomes = new Map(clientes.data?.items.map((c) => [c.id, c.nome]));
  const lista = integracoes.data?.items ?? [];
  const conectadas = lista.filter((i) => i.status === "conectada");
  const contas = lista.flatMap((i) => i.contas.filter((c) => c.ativa).map((c) => ({ conta: c, integracao: i })));
  const primeiroNome = me?.nome.split(" ")[0] ?? "";

  return (
    <>
      <PageHeader
        titulo="Visão geral da carteira"
        selo={
          editor && integracoes.data ? (
            alertas.length ? (
              <Badge ponto variant="warning">
                {alertas.length} {alertas.length === 1 ? "alerta" : "alertas"} de sincronização
              </Badge>
            ) : (
              <Badge ponto variant="success">Integrações em dia</Badge>
            )
          ) : undefined
        }
        descricao={
          <>
            Olá, {primeiroNome}. Acompanhe seus clientes, o status dos conectores e os atalhos da unidade{" "}
            <strong className="font-semibold text-foreground">V4 Bounnacorso</strong>.
          </>
        }
      />

      <section aria-label="Resumo" className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {clientes.isPending || (editor && integracoes.isPending) ? (
          Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)
        ) : (
          <>
            <Indicador
              rotulo="Clientes na carteira"
              dica="Clientes ativos atribuídos a você"
              valor={fmtNumero(clientes.data?.total ?? 0)}
              rodape="ativos e atribuídos a você"
            />
            {editor ? (
              <>
                <Indicador
                  rotulo="Integrações conectadas"
                  dica="Integrações Meta Ads e Google Ads com status conectada"
                  valor={`${fmtNumero(conectadas.length)}/${fmtNumero(lista.length)}`}
                  rodape="Meta Ads · Google Ads"
                />
                <Indicador
                  rotulo="Contas de anúncio"
                  dica="Contas ativas selecionadas para coleta"
                  valor={fmtNumero(contas.length)}
                  rodape="em coleta automática"
                />
                <Indicador
                  rotulo="Alertas"
                  dica="Integrações com erro, sem contas ou sem sincronizar há mais de 24 horas"
                  valor={<span className={alertas.length ? "text-primary-ink" : undefined}>{fmtNumero(alertas.length)}</span>}
                  rodape={alertas.length ? "exigem atenção" : "nenhuma pendência"}
                />
              </>
            ) : (
              <Card className="col-span-1 flex items-center p-4 text-xs leading-relaxed text-muted-foreground lg:col-span-3">
                Os avisos de atualização dos dados aparecem em cada dashboard. Abra um cliente para ver indicadores e
                relatórios.
              </Card>
            )}
          </>
        )}
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Card className="overflow-hidden">
          <CardHeader className="items-center border-b">
            <div>
              <CardTitle>Clientes atribuídos</CardTitle>
              <CardDescription>Clique em um cliente para abrir indicadores, integrações e relatórios</CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm">
              <Link href="/clientes">
                Gerenciar carteira <ChevronRightIcon />
              </Link>
            </Button>
          </CardHeader>
          <Consulta
            query={clientes}
            carregando={<div className="p-5"><Skeleton className="h-40 rounded-xl" /></div>}
            vazio={(d) =>
              d.items.length === 0 && (
                <div className="p-5">
                  <Vazio titulo="Nenhum cliente na sua carteira">Peça a um gestor ou administrador para atribuir clientes a você.</Vazio>
                </div>
              )
            }
          >
            {(d) => (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Atualizado em</TableHead>
                    <TableHead className="text-right">Ação</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {d.items.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <Inicial nome={c.nome} />
                          <span className="min-w-0">
                            <Link href={`/clientes/${c.id}`} className="block truncate font-semibold hover:underline">
                              {c.nome}
                            </Link>
                            {c.nome_fantasia && <span className="block truncate text-xs text-muted-foreground">{c.nome_fantasia}</span>}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge ponto variant="success">{c.status}</Badge>
                      </TableCell>
                      <TableCell className="font-mono-num text-xs text-muted-foreground">{fmtData(c.atualizado_em)}</TableCell>
                      <TableCell className="text-right">
                        <Link
                          href={`/clientes/${c.id}/dashboards`}
                          className="inline-flex items-center gap-1 text-xs font-medium text-text-secondary hover:text-foreground"
                          aria-label={`Dashboards de ${c.nome}`}
                        >
                          Dashboards <ChevronRightIcon className="size-3.5" aria-hidden />
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Consulta>
        </Card>

        {editor && (
          <Card className="overflow-hidden">
            <CardHeader className="items-center border-b">
              <div>
                <CardTitle>Contas de mídia e sincronização</CardTitle>
                <CardDescription>Status dos conectores por conta vinculada</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => integracoes.refetch()} disabled={integracoes.isFetching}>
                <RefreshCwIcon className={integracoes.isFetching ? "animate-spin" : undefined} /> Atualizar
              </Button>
            </CardHeader>
            <Consulta
              query={integracoes}
              carregando={<div className="p-5"><Skeleton className="h-40 rounded-xl" /></div>}
              vazio={(d) =>
                d.items.length === 0 && (
                  <div className="p-5">
                    <Vazio titulo="Nenhuma integração" acao={<Button asChild size="sm"><Link href="/integracoes">Conectar contas</Link></Button>}>
                      Conecte Meta Ads ou Google Ads para começar a coletar métricas.
                    </Vazio>
                  </div>
                )
              }
            >
              {(d) => (
                <>
                  {alertas.length > 0 && (
                    <ul className="grid gap-2 border-b p-4" aria-label="Alertas de sincronização">
                      {alertas.map(({ integracao: i, motivo }) => (
                        <li key={i.id}>
                          <Link
                            href={`/integracoes?cliente_id=${i.cliente_id}`}
                            className={
                              "block rounded-lg p-2.5 text-xs " +
                              (motivo === "reconexao" ? "bg-destructive-soft text-destructive" : "bg-warning-soft text-warning")
                            }
                          >
                            <strong className="font-semibold">
                              {nomes.get(i.cliente_id) ?? "Cliente"} · {MOTIVO_LABEL[motivo]}
                            </strong>
                            <span className="block text-[11px]">Última sincronização: {fmtDataHora(i.ultima_sincronizacao_em)}</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Conta / ID</TableHead>
                        <TableHead>Canal</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {d.items.flatMap((i) =>
                        (i.contas.length ? i.contas : [null]).map((c) => (
                          <TableRow key={`${i.id}-${c?.id ?? "sem-conta"}`}>
                            <TableCell className="max-w-56">
                              <span className="block truncate font-medium">{c?.nome ?? nomes.get(i.cliente_id) ?? "Sem contas selecionadas"}</span>
                              <span className="block truncate font-mono-num text-[11px] text-muted-foreground">
                                {c?.conta_externa_id ?? "—"}
                              </span>
                            </TableCell>
                            <TableCell>
                              <PlataformaBadge plataforma={i.plataforma} />
                            </TableCell>
                            <TableCell>
                              <Badge ponto variant={STATUS_INTEGRACAO[i.status].variant}>{STATUS_INTEGRACAO[i.status].label}</Badge>
                            </TableCell>
                          </TableRow>
                        )),
                      )}
                    </TableBody>
                  </Table>
                </>
              )}
            </Consulta>
          </Card>
        )}
      </div>
    </>
  );
}

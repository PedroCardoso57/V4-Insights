"use client";

import { InfoIcon, SaveIcon, Undo2Icon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Consulta, mensagemDeErro, Vazio } from "@/components/estado";
import { PlataformaBadge } from "@/components/plataforma-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useMe } from "@/hooks/use-me";
import { fmtMoeda, fmtNumero } from "@/lib/format";
import { pode } from "@/lib/permissoes";

import { useConversoes, useSalvarConversoes, type ConversoesConta, type Mapeamento } from "./api";
import { JANELA_LABEL, rotuloAcao } from "./rotulos";

const PADRAO = "padrao";

interface Rascunho {
  contar: string[];
  valor: string[];
  janela: string;
}

function inicial(c: ConversoesConta): Rascunho {
  const m = c.mapeamento;
  const contar = m.action_types ?? [];
  return { contar, valor: m.acao_valor ?? contar, janela: m.janela ?? PADRAO };
}

const mesmoConjunto = (a: string[], b: string[]) => a.length === b.length && a.every((x) => b.includes(x));

function paraMapeamento(r: Rascunho): Mapeamento {
  return {
    action_types: r.contar,
    // Valor igual às ações contadas é o padrão: não precisa gravar a lista à parte.
    acao_valor: mesmoConjunto(r.valor, r.contar) ? null : r.valor,
    janela: r.janela === PADRAO ? null : r.janela,
  };
}

function alternar(lista: string[], item: string, marcado: boolean): string[] {
  return marcado ? [...new Set([...lista, item])] : lista.filter((x) => x !== item);
}

function ContaConversoes({ conta, clienteId, editar }: { conta: ConversoesConta; clienteId: string; editar: boolean }) {
  const salvar = useSalvarConversoes(clienteId);
  const original = inicial(conta);
  const [rascunho, setRascunho] = useState<Rascunho | null>(null);
  const r = rascunho ?? original;
  const mudou =
    !mesmoConjunto(r.contar, original.contar) || !mesmoConjunto(r.valor, original.valor) || r.janela !== original.janela;
  const totalContado = conta.acoes.filter((a) => r.contar.includes(a.action_type)).reduce((s, a) => s + Number(a.quantidade), 0);
  const temValor = conta.acoes.some((a) => a.valor !== null && a.valor !== undefined);

  const enviar = () =>
    salvar.mutate(
      { contaId: conta.conta_anuncio_id, mapeamento: paraMapeamento(r) },
      {
        onSuccess: (res) => {
          setRascunho(null);
          toast.success(
            res.ressincronizando
              ? "Conversões salvas. Como a janela mudou, os dados desta conta estão sendo coletados de novo."
              : `Conversões salvas e ${fmtNumero(res.linhas_recalculadas)} linhas do histórico recalculadas.`,
          );
        },
        onError: (e) => toast.error(mensagemDeErro(e)),
      },
    );

  return (
    <Card>
      <CardHeader className="flex-wrap items-start gap-3">
        <div className="grid gap-1">
          <CardTitle className="flex flex-wrap items-center gap-2">
            <PlataformaBadge plataforma={conta.plataforma} />
            {conta.nome}
            {!conta.ativa && <Badge>fora da coleta</Badge>}
          </CardTitle>
          <CardDescription>
            Conta {conta.conta_externa_id} · {r.contar.length === 0 ? (
              <span className="text-warning">nenhuma ação conta como conversão, então CPA e ROAS ficam vazios</span>
            ) : (
              <>
                {fmtNumero(totalContado)} conversões nos últimos {conta.dias_analisados} dias com a seleção atual
              </>
            )}
          </CardDescription>
        </div>
        {conta.janelas.length > 0 && (
          <div className="grid gap-1.5">
            <Label htmlFor={`janela-${conta.conta_anuncio_id}`} className="text-xs text-muted-foreground">
              Janela de atribuição
            </Label>
            <Select
              value={r.janela}
              onValueChange={(v) => setRascunho({ ...r, janela: v })}
              disabled={!editar}
            >
              <SelectTrigger id={`janela-${conta.conta_anuncio_id}`} className="w-60">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={PADRAO}>Padrão da conta de anúncios</SelectItem>
                {conta.janelas.map((j) => (
                  <SelectItem key={j} value={j}>{JANELA_LABEL[j] ?? j}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </CardHeader>
      <CardContent className="grid gap-4">
        {conta.acoes.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Ainda não chegou nenhuma ação desta conta nos últimos {conta.dias_analisados} dias. Elas aparecem aqui depois da
            próxima sincronização com dados.
          </p>
        ) : (
          <div className="overflow-hidden rounded-xl border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ação na plataforma</TableHead>
                  <TableHead className="text-right">Quantidade ({conta.dias_analisados} dias)</TableHead>
                  {temValor && <TableHead className="text-right">Valor ({conta.dias_analisados} dias)</TableHead>}
                  <TableHead className="text-center">Conta como conversão</TableHead>
                  {temValor && <TableHead className="text-center">Soma no valor</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {conta.acoes.map((a) => {
                  const nome = rotuloAcao(a.action_type);
                  const comValor = a.valor !== null && a.valor !== undefined;
                  return (
                    <TableRow key={a.action_type}>
                      <TableCell data-largo="">
                        <span className="font-medium">{nome}</span>
                        {nome !== a.action_type && (
                          <span className="block font-mono-num text-[11px] text-muted-foreground">{a.action_type}</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono-num">{fmtNumero(a.quantidade)}</TableCell>
                      {temValor && (
                        <TableCell className="text-right font-mono-num">{comValor ? fmtMoeda(a.valor, conta.moeda) : "—"}</TableCell>
                      )}
                      <TableCell className="text-center">
                        <Checkbox
                          aria-label={`Contar ${nome} como conversão`}
                          checked={r.contar.includes(a.action_type)}
                          disabled={!editar}
                          onCheckedChange={(v) => {
                            const contar = alternar(r.contar, a.action_type, v === true);
                            // Marcar uma ação com valor também soma o valor dela; desmarcar tira dos dois.
                            const valor = v === true && !comValor ? r.valor : alternar(r.valor, a.action_type, v === true);
                            setRascunho({ ...r, contar, valor });
                          }}
                        />
                      </TableCell>
                      {temValor && (
                        <TableCell className="text-center">
                          {comValor ? (
                            <Checkbox
                              aria-label={`Somar o valor de ${nome}`}
                              checked={r.valor.includes(a.action_type)}
                              disabled={!editar}
                              onCheckedChange={(v) => setRascunho({ ...r, valor: alternar(r.valor, a.action_type, v === true) })}
                            />
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                      )}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
        {r.janela !== original.janela && (
          <p className="flex items-start gap-2 rounded-lg bg-warning-soft px-3 py-2 text-xs text-warning">
            <InfoIcon className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            Trocar a janela faz o sistema coletar de novo o histórico desta conta. Os números mudam quando a coleta terminar.
          </p>
        )}
        {editar && (
          <div className="flex flex-wrap justify-end gap-2">
            {mudou && (
              <Button variant="ghost" onClick={() => setRascunho(null)} disabled={salvar.isPending}>
                <Undo2Icon /> Desfazer
              </Button>
            )}
            <Button onClick={enviar} disabled={!mudou || salvar.isPending}>
              <SaveIcon /> {salvar.isPending ? "Salvando…" : "Salvar e recalcular"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/** Aba Conversões do cliente: o que conta como conversão em cada conta de anúncio (M04). */
export function ConversoesCliente({ clienteId, arquivado }: { clienteId: string; arquivado: boolean }) {
  const papel = useMe().data?.papel;
  const q = useConversoes(clienteId);
  const editar = pode.editar(papel) && !arquivado;
  return (
    <div className="grid gap-4">
      <p className="max-w-3xl text-sm text-muted-foreground">
        Escolha, em cada conta, quais ações da plataforma contam como <strong className="text-foreground">Conversões</strong> e
        quais somam em <strong className="text-foreground">Valor de conversões</strong>. CPA e ROAS do dashboard e dos relatórios
        usam essa escolha, e o histórico já coletado é recalculado na hora.
      </p>
      <Consulta
        query={q}
        carregando={<Skeleton className="h-48 rounded-xl" />}
        vazio={(d) =>
          d.contas.length === 0 && (
            <Vazio titulo="Nenhuma conta de anúncio conectada">
              Conecte uma plataforma e escolha as contas na aba Integrações. As ações aparecem aqui depois da primeira sincronização.
            </Vazio>
          )
        }
      >
        {(d) => (
          <div className="grid gap-4">
            {d.contas.map((c) => (
              <ContaConversoes key={c.conta_anuncio_id} conta={c} clienteId={clienteId} editar={editar} />
            ))}
          </div>
        )}
      </Consulta>
    </div>
  );
}

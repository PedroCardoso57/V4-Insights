"use client";

import { FileTextIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { Confirmar } from "@/components/confirmar";
import { Consulta, mensagemDeErro, Vazio } from "@/components/estado";
import { Paginacao } from "@/components/paginacao";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useMe } from "@/hooks/use-me";
import { fmtDataHora } from "@/lib/format";
import { pode } from "@/lib/permissoes";

import { useExcluirRelatorio, useRelatorios, type Relatorio } from "./api";
import { TEMPLATES } from "./schema";

export function ListaRelatorios({ clienteId, search, nomesClientes }: { clienteId?: string; search?: string; nomesClientes?: Map<string, string> }) {
  const papel = useMe().data?.papel;
  const [page, setPage] = useState(1);
  const q = useRelatorios({ cliente_id: clienteId, search, page });
  const excluir = useExcluirRelatorio();
  const [alvo, setAlvo] = useState<Relatorio | null>(null);
  const novo = `/relatorios?id=novo${clienteId ? `&cliente_id=${clienteId}` : ""}`;
  return (
    <>
      <Consulta
        query={q}
        vazio={(d) =>
          d.items.length === 0 && (
            <Vazio titulo="Nenhum relatório" acao={pode.editar(papel) && <Button asChild><Link href={novo}>Criar relatório</Link></Button>}>
              Monte um relatório com período, fontes, KPIs e comentários e gere o PDF.
            </Vazio>
          )
        }
      >
        {(d) => (
          <>
            {pode.editar(papel) && (
              <div className="mb-3 flex justify-end">
                <Button asChild size="sm"><Link href={novo}><FileTextIcon /> Novo relatório</Link></Button>
              </div>
            )}
            <div className="overflow-hidden rounded-xl border bg-card shadow-xs">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Título</TableHead>
                  {nomesClientes && <TableHead>Cliente</TableHead>}
                  <TableHead>Template</TableHead>
                  <TableHead>Atualizado</TableHead>
                  {pode.editar(papel) && <TableHead><span className="sr-only">Ações</span></TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {d.items.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell><Link className="font-medium hover:underline" href={`/relatorios?id=${r.id}`}>{r.titulo}</Link></TableCell>
                    {nomesClientes && <TableCell>{nomesClientes.get(r.cliente_id) ?? "—"}</TableCell>}
                    <TableCell><Badge variant="secondary">{TEMPLATES[r.configuracao.template ?? "visao_executiva"]}</Badge></TableCell>
                    <TableCell className="font-mono-num text-xs text-muted-foreground">{fmtDataHora(r.atualizado_em)}</TableCell>
                    {pode.editar(papel) && (
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon-sm" className="hover:bg-destructive-soft hover:text-destructive" onClick={() => setAlvo(r)} aria-label={`Excluir ${r.titulo}`}>
                          <Trash2Icon />
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            </div>
            <Paginacao page={d.page} pageSize={d.page_size} total={d.total} onPage={setPage} />
          </>
        )}
      </Consulta>
      <Confirmar
        aberto={!!alvo}
        onAberto={(v) => !v && setAlvo(null)}
        titulo="Excluir relatório"
        descricao="O relatório sai da lista; os PDFs já gerados permanecem no histórico de execuções."
        acao="Excluir"
        perigo
        onConfirmar={() => alvo && excluir.mutate(alvo.id, { onSuccess: () => toast.success("Relatório excluído."), onError: (e) => toast.error(mensagemDeErro(e)) })}
      />
    </>
  );
}

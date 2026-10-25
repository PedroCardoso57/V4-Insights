"use client";

import { useState } from "react";

import { Consulta, Vazio } from "@/components/estado";
import { Paginacao } from "@/components/paginacao";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fmtData, fmtDataHora } from "@/lib/format";

import { useJobs, type Integracao } from "./api";

const TOM = { sucesso: "success", erro: "destructive", pendente: "warning", executando: "warning", cancelado: "secondary" } as const;

export function JobsDialog({ integracao, onClose }: { integracao: Integracao | null; onClose: () => void }) {
  const [page, setPage] = useState(1);
  const q = useJobs(integracao?.id ?? null, page);
  if (!integracao) return null;
  const contas = new Map(integracao.contas.map((c) => [c.id, c.nome]));
  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Execuções de sincronização</DialogTitle>
        </DialogHeader>
        <Consulta query={q} vazio={(d) => d.items.length === 0 && <Vazio titulo="Nenhuma execução ainda" />}>
          {(d) => (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Criado</TableHead>
                    <TableHead>Conta</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Intervalo</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Registros</TableHead>
                    <TableHead className="text-right">Tentativa</TableHead>
                    <TableHead>Erro</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {d.items.map((j) => (
                    <TableRow key={j.id}>
                      <TableCell>{fmtDataHora(j.criado_em)}</TableCell>
                      <TableCell>{(j.conta_anuncio_id && contas.get(j.conta_anuncio_id)) ?? "—"}</TableCell>
                      <TableCell>{j.tipo}</TableCell>
                      <TableCell>{fmtData(j.periodo_inicio)} – {fmtData(j.periodo_fim)}</TableCell>
                      <TableCell><Badge variant={TOM[j.status]}>{j.status}</Badge></TableCell>
                      <TableCell className="text-right tabular-nums">{j.total_registros}</TableCell>
                      <TableCell className="text-right tabular-nums">{j.tentativa}</TableCell>
                      <TableCell className="max-w-64 text-xs">{j.erro_sanitizado ?? ""}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Paginacao page={page} pageSize={d.page_size} total={d.total} onPage={setPage} />
            </>
          )}
        </Consulta>
      </DialogContent>
    </Dialog>
  );
}

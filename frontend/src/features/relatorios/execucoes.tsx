"use client";

import { DownloadIcon } from "lucide-react";

import { Consulta, Vazio } from "@/components/estado";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fmtData, fmtDataHora } from "@/lib/format";

import { urlDownload, useExecucoes } from "./api";

const TOM = { concluido: "success", erro: "destructive", pendente: "warning", processando: "warning" } as const;

export function Execucoes({ relatorioId }: { relatorioId: string }) {
  const q = useExecucoes(relatorioId);
  return (
    <Card>
      <CardHeader><CardTitle>Execuções</CardTitle></CardHeader>
      <CardContent>
        <Consulta query={q} vazio={(d) => d.items.length === 0 && <Vazio titulo="Nenhum PDF gerado ainda">Use “Gerar PDF” após salvar a configuração.</Vazio>}>
          {(d) => (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Solicitado</TableHead>
                  <TableHead>Período</TableHead>
                  <TableHead>Corte dos dados</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead><span className="sr-only">Ações</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {d.items.map((e) => {
                  const snap = e.snapshot as { periodo?: { inicio: string; fim: string }; horario_corte?: string };
                  const url = urlDownload(e);
                  return (
                    <TableRow key={e.id}>
                      <TableCell>{fmtDataHora(e.iniciado_em)}</TableCell>
                      <TableCell>{snap.periodo ? `${fmtData(snap.periodo.inicio)} – ${fmtData(snap.periodo.fim)}` : "—"}</TableCell>
                      <TableCell>{fmtDataHora(snap.horario_corte)}</TableCell>
                      <TableCell>
                        <Badge variant={TOM[e.status]}>{e.status === "processando" ? `processando ${e.progresso}%` : e.status}</Badge>
                        {e.erro && <p className="mt-1 max-w-64 text-xs text-destructive">{e.erro}</p>}
                        {e.status === "concluido" && !url && <p className="mt-1 text-xs text-muted-foreground">arquivo expirado (retenção)</p>}
                      </TableCell>
                      <TableCell className="text-right">
                        {url && (
                          <Button asChild variant="outline" size="sm">
                            <a href={url} rel="noopener">
                              <DownloadIcon /> PDF
                            </a>
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </Consulta>
      </CardContent>
    </Card>
  );
}

"use client";

import { UserMinusIcon, UserPlusIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Confirmar } from "@/components/confirmar";
import { Consulta, mensagemDeErro, Vazio } from "@/components/estado";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useUsuarios } from "@/features/usuarios/api";
import { fmtData, PAPEL_LABEL } from "@/lib/format";
import { pode } from "@/lib/permissoes";
import type { Schemas } from "@/services/api/client";

import { useAcessoCliente, useEquipe } from "./api";

export function Equipe({ clienteId, papel }: { clienteId: string; papel?: Schemas["Papel"] }) {
  const gerir = pode.gerirClientes(papel);
  const equipe = useEquipe(clienteId);
  const usuarios = useUsuarios({ ativo: true, page_size: 100 }, gerir);
  const acesso = useAcessoCliente();
  const [novo, setNovo] = useState("");
  const [removendo, setRemovendo] = useState<Schemas["MembroOut"] | null>(null);
  const ids = new Set(equipe.data?.items.map((m) => m.id));
  const candidatos = usuarios.data?.items.filter((u) => !ids.has(u.id)) ?? [];

  const alterar = (usuarioId: string, remover = false) =>
    acesso.mutate(
      { usuarioId, clienteId, remover },
      { onSuccess: () => toast.success(remover ? "Acesso removido." : "Colaborador adicionado."), onError: (e) => toast.error(mensagemDeErro(e)) },
    );

  return (
    <div className="grid gap-4">
      {gerir && (
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); if (novo) { alterar(novo); setNovo(""); } }}>
          <Select value={novo || undefined} onValueChange={setNovo}>
            <SelectTrigger className="w-72" aria-label="Colaborador"><SelectValue placeholder="Adicionar colaborador…" /></SelectTrigger>
            <SelectContent>
              {candidatos.map((u) => <SelectItem key={u.id} value={u.id}>{u.nome} ({PAPEL_LABEL[u.papel as Schemas["Papel"]]})</SelectItem>)}
            </SelectContent>
          </Select>
          <Button type="submit" disabled={!novo || acesso.isPending}><UserPlusIcon /> Adicionar</Button>
        </form>
      )}
      <Consulta
        query={equipe}
        vazio={(d) => d.items.length === 0 && <Vazio titulo="Nenhum colaborador atribuído">Administradores acessam todos os clientes.</Vazio>}
      >
        {(d) => (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>E-mail</TableHead>
                <TableHead>Perfil</TableHead>
                <TableHead>Desde</TableHead>
                {gerir && <TableHead><span className="sr-only">Ações</span></TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {d.items.map((m) => (
                <TableRow key={m.id}>
                  <TableCell>{m.nome} {!m.ativo && <Badge>inativo</Badge>}</TableCell>
                  <TableCell>{m.email}</TableCell>
                  <TableCell>{PAPEL_LABEL[m.papel as Schemas["Papel"]]}</TableCell>
                  <TableCell>{fmtData(m.atribuido_em)}</TableCell>
                  {gerir && (
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="text-destructive" onClick={() => setRemovendo(m)}>
                        <UserMinusIcon /> Remover
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Consulta>
      <Confirmar
        aberto={!!removendo}
        onAberto={(v) => !v && setRemovendo(null)}
        titulo="Remover acesso"
        descricao={`Remover ${removendo?.nome ?? ""} da carteira deste cliente?`}
        acao="Remover"
        perigo
        onConfirmar={() => removendo && alterar(removendo.id, true)}
      />
    </div>
  );
}

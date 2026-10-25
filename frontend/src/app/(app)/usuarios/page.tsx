"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { PencilIcon, PlusIcon, SearchIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Consulta, mensagemDeErro, Vazio } from "@/components/estado";
import { PageHeader } from "@/components/page-header";
import { Paginacao } from "@/components/paginacao";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useSalvarUsuario, useUsuarios, type Usuario } from "@/features/usuarios/api";
import { useMe } from "@/hooks/use-me";
import { fmtDataHora, PAPEL_LABEL, type Papel } from "@/lib/format";
import { pode } from "@/lib/permissoes";

const schema = z.object({
  nome: z.string().trim().min(2, "Informe o nome").max(180),
  email: z.string().trim().email("E-mail inválido"),
  papel: z.enum(["admin", "gestor", "analista", "visualizador"]),
  ativo: z.boolean(),
});
type Form = z.infer<typeof schema>;

export default function UsuariosPage() {
  const me = useMe().data;
  const admin = pode.gerirUsuarios(me?.papel);
  const [page, setPage] = useState(1);
  const [texto, setTexto] = useState("");
  const [busca, setBusca] = useState<string>();
  const [editando, setEditando] = useState<Usuario | "novo" | null>(null);
  const q = useUsuarios({ page, search: busca }, admin);

  if (!admin) return <Alert variant="warning">A administração de usuários é restrita a administradores.</Alert>;
  return (
    <>
      <PageHeader
        titulo="Usuários"
        descricao="Não há autocadastro: cadastre o e-mail Google do colaborador e defina o perfil."
        acoes={<Button onClick={() => setEditando("novo")}><PlusIcon /> Novo usuário</Button>}
      />
      <form className="mb-5 flex flex-wrap items-center gap-2 rounded-xl border bg-card p-4 shadow-xs" role="search" onSubmit={(e) => { e.preventDefault(); setPage(1); setBusca(texto.trim() || undefined); }}>
        <Input type="search" aria-label="Buscar usuário" placeholder="Nome ou e-mail" value={texto} onChange={(e) => setTexto(e.target.value)} className="w-64" />
        <Button type="submit" variant="outline"><SearchIcon /> Buscar</Button>
      </form>
      <Consulta query={q} vazio={(d) => d.items.length === 0 && <Vazio titulo="Nenhum usuário encontrado" />}>
        {(d) => (
          <>
            <div className="overflow-hidden rounded-xl border bg-card shadow-xs">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>E-mail</TableHead>
                  <TableHead>Perfil</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Último acesso</TableHead>
                  <TableHead><span className="sr-only">Ações</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {d.items.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-semibold">{u.nome}</TableCell>
                    <TableCell className="text-text-secondary">{u.email}</TableCell>
                    <TableCell>{PAPEL_LABEL[u.papel as Papel]}</TableCell>
                    <TableCell className="flex flex-wrap gap-1">
                      <Badge ponto variant={u.ativo ? "success" : "destructive"}>{u.ativo ? "ativo" : "inativo"}</Badge>
                      {!u.vinculado_google && <Badge ponto variant="warning">nunca entrou</Badge>}
                    </TableCell>
                    <TableCell>{fmtDataHora(u.ultimo_login_em)}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" onClick={() => setEditando(u)} aria-label={`Editar ${u.nome}`}><PencilIcon /></Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            </div>
            <Paginacao page={d.page} pageSize={d.page_size} total={d.total} onPage={setPage} />
          </>
        )}
      </Consulta>
      <UsuarioDialog alvo={editando} proprio={me?.id} onClose={() => setEditando(null)} />
    </>
  );
}

function UsuarioDialog({ alvo, proprio, onClose }: { alvo: Usuario | "novo" | null; proprio?: string; onClose: () => void }) {
  const salvar = useSalvarUsuario();
  const u = alvo && alvo !== "novo" ? alvo : undefined;
  const { register, control, handleSubmit, reset, formState } = useForm<Form>({ resolver: zodResolver(schema) });
  useEffect(() => {
    if (alvo) reset({ nome: u?.nome ?? "", email: u?.email ?? "", papel: (u?.papel as Papel) ?? "analista", ativo: u?.ativo ?? true });
  }, [alvo, u, reset]);
  if (!alvo) return null;
  const enviar = (v: Form) =>
    salvar.mutate(
      { id: u?.id, ...v },
      { onSuccess: () => { toast.success(u ? "Usuário atualizado." : "Usuário cadastrado."); onClose(); }, onError: (e) => toast.error(mensagemDeErro(e)) },
    );
  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{u ? "Editar usuário" : "Novo usuário"}</DialogTitle>
          <DialogDescription>Alterar perfil ou desativar encerra as sessões abertas do usuário.</DialogDescription>
        </DialogHeader>
        <form id="form-usuario" className="grid gap-4" onSubmit={handleSubmit(enviar)} noValidate>
          <Field id="u-nome" label="Nome" error={formState.errors.nome}>{(a) => <Input {...a} {...register("nome")} />}</Field>
          <Field id="u-email" label="E-mail Google corporativo" error={formState.errors.email}>
            {(a) => <Input type="email" {...a} {...register("email")} disabled={!!u} />}
          </Field>
          <Field id="u-papel" label="Perfil">
            {(a) => (
              <Controller control={control} name="papel" render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange} disabled={u?.id === proprio}>
                  <SelectTrigger {...a}><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {(Object.keys(PAPEL_LABEL) as Papel[]).map((p) => <SelectItem key={p} value={p}>{PAPEL_LABEL[p]}</SelectItem>)}
                  </SelectContent>
                </Select>
              )} />
            )}
          </Field>
          {u && (
            <Controller control={control} name="ativo" render={({ field }) => (
              <Label className="font-normal">
                <Checkbox checked={field.value} disabled={u.id === proprio} onCheckedChange={(v) => field.onChange(v === true)} /> Ativo
              </Label>
            )} />
          )}
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button type="submit" form="form-usuario" disabled={salvar.isPending}>Salvar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

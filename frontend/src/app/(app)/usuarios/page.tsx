"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRoundIcon, PencilIcon, PlusIcon, SearchIcon, Trash2Icon } from "lucide-react";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Avatar } from "@/components/avatar";
import { Confirmar } from "@/components/confirmar";
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
import { useSenhaUsuario } from "@/features/auth/api";
import { useExcluirUsuario, useRemoverFoto, useSalvarUsuario, useUsuarios, type Usuario } from "@/features/usuarios/api";
import { useMe } from "@/hooks/use-me";
import { fmtDataHora, PAPEL_LABEL, type Papel } from "@/lib/format";
import { pode } from "@/lib/permissoes";
import { novaSenha } from "@/lib/senha";

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
  const [senhaDe, setSenhaDe] = useState<Usuario | null>(null);
  const [excluindo, setExcluindo] = useState<Usuario | null>(null);
  const q = useUsuarios({ page, search: busca }, admin);
  const excluir = useExcluirUsuario();

  if (!admin) return <Alert variant="warning">A administração de usuários é restrita a administradores.</Alert>;
  return (
    <>
      <PageHeader
        titulo="Usuários"
        descricao="Não há autocadastro: cadastre o e-mail corporativo do colaborador, defina o perfil e, se ele não usar Google, uma senha inicial."
        acoes={<Button onClick={() => setEditando("novo")}><PlusIcon /> Novo usuário</Button>}
      />
      <form className="mb-5 flex flex-wrap items-center gap-2 rounded-xl border bg-card p-4 shadow-xs" role="search" onSubmit={(e) => { e.preventDefault(); setPage(1); setBusca(texto.trim() || undefined); }}>
        <Input type="search" aria-label="Buscar usuário" placeholder="Nome ou e-mail" value={texto} onChange={(e) => setTexto(e.target.value)} className="min-w-0 flex-1 sm:w-64 sm:flex-none" />
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
                    <TableCell className="font-semibold">
                      <span className="flex items-center gap-2.5">
                        <Avatar nome={u.nome} fotoUrl={u.foto_url} />
                        {u.nome}
                      </span>
                    </TableCell>
                    <TableCell className="text-text-secondary" data-largo="">{u.email}</TableCell>
                    <TableCell>{PAPEL_LABEL[u.papel as Papel]}</TableCell>
                    <TableCell className="flex flex-wrap gap-1">
                      <Badge ponto variant={u.ativo ? "success" : "destructive"}>{u.ativo ? "ativo" : "inativo"}</Badge>
                      {!u.ultimo_login_em && <Badge ponto variant="warning">nunca entrou</Badge>}
                      {u.vinculado_google && <Badge variant="info">Google</Badge>}
                      {u.tem_senha && <Badge variant="outline">senha</Badge>}
                    </TableCell>
                    <TableCell className="font-mono-num text-xs text-muted-foreground">{fmtDataHora(u.ultimo_login_em)}</TableCell>
                    <TableCell className="text-right" data-label="">
                      <Button variant="ghost" size="icon-sm" onClick={() => setSenhaDe(u)} aria-label={`Senha de ${u.nome}`} title="Definir senha">
                        <KeyRoundIcon />
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => setEditando(u)} aria-label={`Editar ${u.nome}`} title="Editar">
                        <PencilIcon />
                      </Button>
                      {u.id !== me?.id && (
                        <Button variant="ghost" size="icon-sm" onClick={() => setExcluindo(u)} aria-label={`Excluir ${u.nome}`} title="Excluir">
                          <Trash2Icon />
                        </Button>
                      )}
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
      <SenhaDialog alvo={senhaDe} onClose={() => setSenhaDe(null)} />
      <Confirmar
        aberto={!!excluindo}
        onAberto={(v) => !v && setExcluindo(null)}
        titulo="Excluir usuário"
        descricao={
          <>
            <strong>{excluindo?.nome}</strong> perde o acesso na hora e sai da lista; nome, e-mail e vínculos com clientes
            são apagados. Dashboards e relatórios criados por ele continuam disponíveis. Não é possível desfazer. Para
            apenas suspender o acesso, edite o usuário e desmarque Ativo.
          </>
        }
        acao="Excluir"
        perigo
        onConfirmar={() =>
          excluindo &&
          excluir.mutate(excluindo.id, {
            onSuccess: () => { toast.success("Usuário excluído."); setExcluindo(null); },
            onError: (e) => toast.error(mensagemDeErro(e)),
          })
        }
      />
    </>
  );
}

function UsuarioDialog({ alvo, proprio, onClose }: { alvo: Usuario | "novo" | null; proprio?: string; onClose: () => void }) {
  const salvar = useSalvarUsuario();
  const removerFoto = useRemoverFoto();
  const [semFoto, setSemFoto] = useState<string | null>(null);
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
          {u?.foto_url && semFoto !== u.id && (
            <div className="flex items-center gap-3">
              <Avatar nome={u.nome} fotoUrl={u.foto_url} className="size-12 text-base" />
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={removerFoto.isPending}
                onClick={() =>
                  removerFoto.mutate(u.id, {
                    onSuccess: () => { setSemFoto(u.id); toast.success("Foto removida."); },
                    onError: (e) => toast.error(mensagemDeErro(e)),
                  })
                }
              >
                <Trash2Icon /> Remover foto
              </Button>
            </div>
          )}
          <Field id="u-nome" label="Nome" error={formState.errors.nome}>{(a) => <Input {...a} {...register("nome")} />}</Field>
          <Field id="u-email" label="E-mail corporativo" error={formState.errors.email}>
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

const schemaSenha = z
  .object({ nova: novaSenha, confirmacao: z.string() })
  .refine((v) => v.nova === v.confirmacao, { path: ["confirmacao"], message: "As senhas não conferem." });

/** Admin define a senha inicial ou redefine a de um colaborador (encerra as sessões dele). */
function SenhaDialog({ alvo, onClose }: { alvo: Usuario | null; onClose: () => void }) {
  const senha = useSenhaUsuario();
  const { register, handleSubmit, reset, formState } = useForm<z.infer<typeof schemaSenha>>({ resolver: zodResolver(schemaSenha) });
  useEffect(() => {
    if (alvo) reset({ nova: "", confirmacao: "" });
  }, [alvo, reset]);
  if (!alvo) return null;
  const ok = (msg: string) => () => {
    toast.success(msg);
    onClose();
  };
  const erro = (e: unknown) => toast.error(mensagemDeErro(e));
  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{alvo.tem_senha ? "Redefinir senha" : "Definir senha"}</DialogTitle>
          <DialogDescription>
            {alvo.nome} poderá entrar com <strong>{alvo.email}</strong> e esta senha. Compartilhe-a por um canal seguro
            e peça a troca em Configurações; as sessões abertas do colaborador serão encerradas.
          </DialogDescription>
        </DialogHeader>
        <form
          id="form-senha"
          className="grid gap-4"
          noValidate
          onSubmit={handleSubmit((v) =>
            senha.mutate({ id: alvo.id, nova_senha: v.nova }, { onSuccess: ok("Senha definida."), onError: erro }),
          )}
        >
          <Field id="s-nova" label="Nova senha" error={formState.errors.nova} hint="Mínimo de 10 caracteres.">
            {(a) => <Input type="password" autoComplete="new-password" {...a} {...register("nova")} />}
          </Field>
          <Field id="s-conf" label="Confirmar senha" error={formState.errors.confirmacao}>
            {(a) => <Input type="password" autoComplete="new-password" {...a} {...register("confirmacao")} />}
          </Field>
        </form>
        <DialogFooter className="sm:justify-between">
          {alvo.tem_senha ? (
            <Button
              variant="destructive"
              disabled={senha.isPending}
              onClick={() => senha.mutate({ id: alvo.id, nova_senha: null }, { onSuccess: ok("Senha removida: acesso somente com Google."), onError: erro })}
            >
              Remover senha
            </Button>
          ) : (
            <span />
          )}
          <div className="flex flex-col-reverse gap-2 sm:flex-row">
            <Button variant="outline" onClick={onClose}>Cancelar</Button>
            <Button type="submit" form="form-senha" disabled={senha.isPending}>Salvar senha</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

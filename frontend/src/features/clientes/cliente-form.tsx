"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { mensagemDeErro } from "@/components/estado";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field } from "@/components/ui/form";
import { Input } from "@/components/ui/input";

import { useSalvarCliente, type Cliente } from "./api";

export const clienteSchema = z.object({
  nome: z.string().trim().min(2, "Informe o nome (mínimo 2 caracteres)").max(180, "Máximo de 180 caracteres"),
  nome_fantasia: z.string().trim().max(180, "Máximo de 180 caracteres").optional(),
  documento: z
    .string()
    .optional()
    .refine((v) => {
      const d = (v ?? "").replace(/\D/g, "");
      return !d || d.length === 11 || d.length === 14;
    }, "Informe um CPF (11 dígitos) ou CNPJ (14 dígitos)"),
});
type ClienteForm = z.infer<typeof clienteSchema>;

export function ClienteFormDialog({ aberto, onAberto, cliente, onSalvo }: {
  aberto: boolean;
  onAberto: (v: boolean) => void;
  cliente?: Cliente;
  onSalvo?: (c: Cliente) => void;
}) {
  const salvar = useSalvarCliente();
  const { register, handleSubmit, formState, reset } = useForm<ClienteForm>({ resolver: zodResolver(clienteSchema) });
  useEffect(() => {
    if (aberto) reset({ nome: cliente?.nome ?? "", nome_fantasia: cliente?.nome_fantasia ?? "", documento: cliente?.documento ?? "" });
  }, [aberto, cliente, reset]);

  const enviar = (v: ClienteForm) =>
    salvar.mutate(
      { id: cliente?.id, body: { nome: v.nome, nome_fantasia: v.nome_fantasia || null, documento: v.documento || null } },
      {
        onSuccess: (c) => {
          toast.success(cliente ? "Cliente atualizado." : "Cliente cadastrado.");
          onAberto(false);
          onSalvo?.(c);
        },
        onError: (e) => toast.error(mensagemDeErro(e)),
      },
    );

  return (
    <Dialog open={aberto} onOpenChange={onAberto}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{cliente ? "Editar cliente" : "Novo cliente"}</DialogTitle>
          <DialogDescription>O documento é opcional e salvo apenas com dígitos.</DialogDescription>
        </DialogHeader>
        <form id="form-cliente" className="grid gap-4" onSubmit={handleSubmit(enviar)} noValidate>
          <Field id="c-nome" label="Nome *" error={formState.errors.nome}>{(a) => <Input {...a} {...register("nome")} autoFocus />}</Field>
          <Field id="c-fantasia" label="Nome fantasia" error={formState.errors.nome_fantasia}>{(a) => <Input {...a} {...register("nome_fantasia")} />}</Field>
          <Field id="c-doc" label="CPF/CNPJ" error={formState.errors.documento}>{(a) => <Input {...a} {...register("documento")} inputMode="numeric" />}</Field>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onAberto(false)}>Cancelar</Button>
          <Button type="submit" form="form-cliente" disabled={salvar.isPending}>{salvar.isPending ? "Salvando…" : "Salvar"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

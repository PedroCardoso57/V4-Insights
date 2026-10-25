"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { mensagemDeErro } from "@/components/estado";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useTrocarSenha } from "@/features/auth/api";
import { useMe } from "@/hooks/use-me";
import { novaSenha } from "@/lib/senha";

const schema = z
  .object({ atual: z.string(), nova: novaSenha, confirmacao: z.string() })
  .refine((v) => v.nova === v.confirmacao, { path: ["confirmacao"], message: "As senhas não conferem." });
type Form = z.infer<typeof schema>;

/** Define (primeira vez) ou troca a própria senha de login por e-mail. */
export function SenhaCard() {
  const me = useMe().data;
  const trocar = useTrocarSenha();
  const temSenha = !!me?.tem_senha;
  const { register, handleSubmit, reset, setError, formState } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { atual: "", nova: "", confirmacao: "" },
  });
  const enviar = (v: Form) => {
    if (temSenha && !v.atual) return setError("atual", { message: "Informe a senha atual." });
    trocar.mutate(
      { senha_atual: temSenha ? v.atual : undefined, nova_senha: v.nova },
      {
        onSuccess: () => {
          reset();
          toast.success(temSenha ? "Senha alterada. Outras sessões foram encerradas." : "Senha definida: você já pode entrar com e-mail e senha.");
        },
        onError: (e) => toast.error(mensagemDeErro(e)),
      },
    );
  };
  return (
    <Card>
      <CardHeader className="flex-col items-start">
        <CardTitle>Senha de acesso</CardTitle>
        <CardDescription>
          {temSenha
            ? "Troque a senha usada para entrar com e-mail. As demais sessões abertas serão encerradas."
            : "Defina uma senha para entrar também com e-mail, além do Google."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4" noValidate onSubmit={handleSubmit(enviar)}>
          <input type="email" autoComplete="username" value={me?.email ?? ""} readOnly hidden />
          {temSenha && (
            <Field id="c-atual" label="Senha atual" error={formState.errors.atual}>
              {(a) => <Input type="password" autoComplete="current-password" {...a} {...register("atual")} />}
            </Field>
          )}
          <Field id="c-nova" label="Nova senha" error={formState.errors.nova} hint="Mínimo de 10 caracteres; prefira uma frase.">
            {(a) => <Input type="password" autoComplete="new-password" {...a} {...register("nova")} />}
          </Field>
          <Field id="c-conf" label="Confirmar nova senha" error={formState.errors.confirmacao}>
            {(a) => <Input type="password" autoComplete="new-password" {...a} {...register("confirmacao")} />}
          </Field>
          <div>
            <Button type="submit" disabled={trocar.isPending}>{temSenha ? "Trocar senha" : "Definir senha"}</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

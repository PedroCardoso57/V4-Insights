"use client";

import { CheckIcon, CopyIcon, KeyRoundIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Consulta, mensagemDeErro } from "@/components/estado";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useChaves, useSalvarChaves, type GrupoChaves } from "@/features/configuracoes/api";

const ORIGEM: Record<string, string> = {
  sistema: "Cadastrada aqui",
  env: "Vem do arquivo .env",
};

function Copiar({ texto }: { texto: string }) {
  const [ok, setOk] = useState(false);
  return (
    <Button
      type="button"
      variant="outline"
      size="icon-sm"
      aria-label="Copiar endereço de retorno"
      onClick={() => {
        void navigator.clipboard?.writeText(texto);
        setOk(true);
        setTimeout(() => setOk(false), 1500);
      }}
    >
      {ok ? <CheckIcon /> : <CopyIcon />}
    </Button>
  );
}

/** Formulário das chaves de uma plataforma (card de Configurações e modal de Conectar). */
export function GrupoChavesForm({
  grupo,
  onSalvo,
  restrito,
}: {
  grupo: GrupoChaves;
  onSalvo?: (grupos: GrupoChaves[]) => void;
  /** Só preenche chaves vazias: as já cadastradas ficam bloqueadas (só o responsável troca). */
  restrito?: boolean;
}) {
  const salvar = useSalvarChaves();
  const [rascunho, setRascunho] = useState<Record<string, string>>({});
  const alterado = Object.keys(rascunho).length > 0;

  const enviar = (valores: Record<string, string | null>, msg: string) =>
    salvar.mutate(valores, {
      onSuccess: (grupos) => {
        setRascunho({});
        toast.success(msg);
        onSalvo?.(grupos);
      },
      onError: (e) => toast.error(mensagemDeErro(e)),
    });

  return (
    <form
      className="grid gap-3 rounded-xl border p-4"
      aria-label={grupo.nome}
      onSubmit={(e) => {
        e.preventDefault();
        if (alterado) enviar(rascunho, `Chaves de ${grupo.nome} salvas.`);
      }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold">{grupo.nome}</h3>
        {grupo.configurado ? <Badge ponto variant="success">configurado</Badge> : <Badge ponto>não configurado</Badge>}
      </div>
      <div className="grid gap-1.5">
        <span className="text-xs text-muted-foreground">Endereço de retorno (cadastre no painel da plataforma)</span>
        <div className="flex items-center gap-2">
          <code className="min-w-0 flex-1 truncate rounded-md bg-subtle px-2 py-1.5 text-xs">{grupo.redirect_uri}</code>
          <Copiar texto={grupo.redirect_uri} />
        </div>
      </div>
      {grupo.campos.map((c) => {
        const id = `chave-${c.chave}`;
        const bloqueado = restrito && !!c.origem;
        const dica = bloqueado
          ? "Já cadastrada"
          : [c.origem ? ORIGEM[c.origem] : "Não informada", !c.obrigatorio && "opcional"].filter(Boolean).join(" · ");
        return (
          <Field key={c.chave} id={id} label={c.rotulo} hint={dica}>
            {(a) => (
              <div className="flex items-center gap-2">
                <Input
                  {...a}
                  type={c.secreto ? "password" : "text"}
                  autoComplete="off"
                  spellCheck={false}
                  maxLength={500}
                  disabled={bloqueado}
                  placeholder={c.secreto && c.origem ? "•••••••• (deixe em branco para manter)" : undefined}
                  value={rascunho[c.chave] ?? (c.secreto ? "" : (c.valor ?? ""))}
                  onChange={(e) => setRascunho({ ...rascunho, [c.chave]: e.target.value })}
                />
                {c.origem === "sistema" && !restrito && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={salvar.isPending}
                    onClick={() => enviar({ [c.chave]: null }, `${c.rotulo} removida.`)}
                  >
                    Remover
                  </Button>
                )}
              </div>
            )}
          </Field>
        );
      })}
      <div className="flex gap-2">
        <Button type="submit" disabled={!alterado || salvar.isPending}>Salvar</Button>
        {alterado && (
          <Button type="button" variant="outline" onClick={() => setRascunho({})}>Descartar</Button>
        )}
      </div>
    </form>
  );
}

/** Chaves dos apps das plataformas (só o responsável pelas chaves). Têm prioridade sobre o `.env`. */
export function ChavesCard() {
  const q = useChaves();
  return (
    <Card className="lg:col-span-2">
      <CardHeader className="flex-col items-start">
        <CardTitle className="flex items-center gap-2"><KeyRoundIcon className="size-4" aria-hidden /> Chaves das plataformas</CardTitle>
        <CardDescription>
          IDs e chaves secretas dos apps do Google, Meta, LinkedIn e TikTok. Ficam criptografadas e valem no lugar do
          arquivo .env. As chaves secretas nunca são exibidas depois de salvas.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Consulta query={q}>
          {(grupos) => (
            <div className="grid gap-4 lg:grid-cols-2">
              {grupos.map((g) => <GrupoChavesForm key={g.id} grupo={g} />)}
            </div>
          )}
        </Consulta>
      </CardContent>
    </Card>
  );
}

"use client";

import { CameraIcon, Trash2Icon } from "lucide-react";
import { useRef } from "react";
import { toast } from "sonner";

import { Avatar, NICOS, urlNico } from "@/components/avatar";
import { mensagemDeErro } from "@/components/estado";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FOTO_MAX_BYTES, FOTO_TIPOS, useEnviarFoto, useRemoverFoto } from "@/features/usuarios/api";
import { useMe } from "@/hooks/use-me";
import { PAPEL_LABEL } from "@/lib/format";

/** Card "Seu perfil" em Configurações: o colaborador envia ou remove a própria foto. */
export function FotoCard() {
  const me = useMe().data;
  const input = useRef<HTMLInputElement>(null);
  const enviar = useEnviarFoto();
  const remover = useRemoverFoto();
  if (!me) return null;

  const enviarArquivo = (arquivo: File, sucesso: string) =>
    enviar.mutate(
      { id: me.id, arquivo },
      { onSuccess: () => toast.success(sucesso), onError: (e) => toast.error(mensagemDeErro(e)) },
    );

  const escolherNico = async (id: string) => {
    try {
      const r = await fetch(urlNico(id));
      if (!r.ok) throw new Error();
      enviarArquivo(new File([await r.blob()], `${id}.webp`, { type: "image/webp" }), "Agora o Nico é a sua foto.");
    } catch {
      toast.error("Não foi possível carregar essa pose do Nico.");
    }
  };

  const escolher = (arquivo: File | undefined) => {
    if (!arquivo) return;
    if (!(FOTO_TIPOS as readonly string[]).includes(arquivo.type)) {
      toast.error("Use uma imagem JPG, PNG ou WEBP.");
      return;
    }
    if (arquivo.size > FOTO_MAX_BYTES) {
      toast.error("A imagem deve ter no máximo 8 MB.");
      return;
    }
    enviarArquivo(arquivo, "Foto atualizada.");
  };

  return (
    <Card className="lg:col-span-2">
      <CardHeader className="flex-col items-start">
        <CardTitle>Seu perfil</CardTitle>
        <CardDescription>Sua foto aparece no menu e para os administradores na tela de Usuários. Enquanto você não escolhe uma, quem aparece é o Nico.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center gap-5">
        <button
          type="button"
          onClick={() => input.current?.click()}
          className="group relative cursor-pointer rounded-full focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          aria-label="Trocar foto de perfil"
        >
          <Avatar nome={me.nome} fotoUrl={me.foto_url} className="size-20 text-2xl" />
          <span className="absolute inset-0 flex items-center justify-center rounded-full bg-black/45 text-white opacity-0 transition-opacity group-hover:opacity-100">
            <CameraIcon className="size-5" aria-hidden />
          </span>
        </button>
        <div className="grid min-w-0 gap-1">
          <strong className="truncate text-sm font-semibold">{me.nome}</strong>
          <span className="truncate text-xs text-muted-foreground">
            {me.email} · {PAPEL_LABEL[me.papel]}
          </span>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button size="sm" onClick={() => input.current?.click()} disabled={enviar.isPending}>
              <CameraIcon /> {enviar.isPending ? "Enviando…" : me.foto_url ? "Trocar foto" : "Enviar foto"}
            </Button>
            {me.foto_url && (
              <Button
                size="sm"
                variant="outline"
                disabled={remover.isPending}
                onClick={() =>
                  remover.mutate(me.id, {
                    onSuccess: () => toast.success("Foto removida."),
                    onError: (e) => toast.error(mensagemDeErro(e)),
                  })
                }
              >
                <Trash2Icon /> Remover
              </Button>
            )}
          </div>
          <span className="text-[11px] text-muted-foreground">JPG, PNG ou WEBP até 8 MB. Cortamos no centro em formato quadrado.</span>
        </div>
        <div className="grid w-full gap-2 border-t pt-4">
          <span className="text-xs font-semibold text-text-secondary">Ou escolha um Nico</span>
          <div className="flex flex-wrap gap-2">
            {NICOS.map((n) => (
              <button
                key={n.id}
                type="button"
                title={n.label}
                aria-label={`Usar ${n.label} como foto`}
                disabled={enviar.isPending}
                onClick={() => escolherNico(n.id)}
                className="cursor-pointer rounded-xl border bg-subtle p-1.5 transition-colors hover:border-primary hover:bg-primary-soft focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none disabled:cursor-wait disabled:opacity-60"
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- miniatura estática */}
                <img src={urlNico(n.id)} alt="" className="size-14 object-contain" />
              </button>
            ))}
          </div>
        </div>
        <input
          ref={input}
          type="file"
          accept={FOTO_TIPOS.join(",")}
          className="hidden"
          onChange={(e) => {
            escolher(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
      </CardContent>
    </Card>
  );
}

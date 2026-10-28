"use client";

import { Consulta } from "@/components/estado";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { GrupoChavesForm } from "@/features/configuracoes/chaves-card";
import { useChaves } from "@/features/configuracoes/api";
import { useMe } from "@/hooks/use-me";
import { PLATAFORMA_LABEL, type Plataforma } from "@/lib/format";

/** Aberto ao clicar em Conectar numa plataforma sem chaves: cadastra e segue para a autorização. */
export function ChavesDialog({
  plataforma,
  onClose,
  onConfigurado,
}: {
  plataforma: Plataforma | null;
  onClose: () => void;
  onConfigurado: (p: Plataforma) => void;
}) {
  const q = useChaves(!!plataforma);
  const responsavel = !!useMe().data?.responsavel_chaves;
  if (!plataforma) return null;
  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Chaves do {PLATAFORMA_LABEL[plataforma]}</DialogTitle>
          <DialogDescription>
            Para conectar, informe as credenciais do app da plataforma. Elas ficam salvas criptografadas no sistema e
            valem para todos os clientes; depois é só conectar.
          </DialogDescription>
        </DialogHeader>
        <Consulta query={q}>
          {(grupos) => {
            const grupo = grupos.find((g) => g.id === plataforma);
            return grupo ? (
              <GrupoChavesForm
                grupo={grupo}
                restrito={!responsavel}
                onSalvo={(atualizados) => {
                  if (atualizados.find((g) => g.id === plataforma)?.configurado) onConfigurado(plataforma);
                }}
              />
            ) : null;
          }}
        </Consulta>
      </DialogContent>
    </Dialog>
  );
}

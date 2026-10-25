"use client";

import { BellIcon } from "lucide-react";
import Link from "next/link";
import { Popover as PopoverPrimitive } from "radix-ui";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useClientes } from "@/features/clientes/api";
import { MOTIVO_LABEL, useAlertasIntegracao } from "@/features/integracoes/alertas";
import { useMe } from "@/hooks/use-me";
import { fmtDataHora, PLATAFORMA_LABEL } from "@/lib/format";
import { pode } from "@/lib/permissoes";
import { cn } from "@/lib/utils";

/** Central de alertas de sincronização (somente perfis que mantêm integrações). */
export function Notificacoes() {
  const papel = useMe().data?.papel;
  const { alertas } = useAlertasIntegracao();
  const clientes = useClientes({ page_size: 100, order_by: "nome" });
  const [aberto, setAberto] = useState(false);
  if (!pode.editar(papel)) return null;
  const nomes = new Map(clientes.data?.items.map((c) => [c.id, c.nome]));
  return (
    <PopoverPrimitive.Root open={aberto} onOpenChange={setAberto}>
      <PopoverPrimitive.Trigger asChild>
        <Button variant="ghost" size="icon-sm" className="relative" aria-label={`Alertas de sincronização (${alertas.length})`}>
          <BellIcon />
          {alertas.length > 0 && <span aria-hidden className="absolute top-1.5 right-1.5 size-2 rounded-full bg-primary" />}
        </Button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align="end"
          sideOffset={8}
          className="z-50 w-80 max-w-[calc(100vw-2rem)] space-y-3 rounded-xl border bg-popover p-4 shadow-lg"
        >
          <div className="flex items-center justify-between border-b pb-2">
            <strong className="text-xs font-semibold">Alertas de sincronização</strong>
            <span className="font-mono-num text-[10px] text-muted-foreground">V4 Bounnacorso</span>
          </div>
          {alertas.length === 0 ? (
            <p className="rounded-lg bg-subtle p-2.5 text-xs text-muted-foreground">Todas as integrações estão em dia.</p>
          ) : (
            <ul className="max-h-80 space-y-2 overflow-y-auto text-xs">
              {alertas.map(({ integracao: i, motivo }) => (
                <li key={i.id}>
                  <Link
                    href={`/integracoes?cliente_id=${i.cliente_id}`}
                    onClick={() => setAberto(false)}
                    className={cn(
                      "block rounded-lg p-2.5",
                      motivo === "reconexao" ? "bg-destructive-soft text-destructive" : "bg-warning-soft text-warning",
                    )}
                  >
                    <strong className="block font-semibold">
                      {PLATAFORMA_LABEL[i.plataforma]} · {MOTIVO_LABEL[motivo]}
                    </strong>
                    <span className="text-[11px]">
                      {nomes.get(i.cliente_id) ?? "Cliente"} · última sincronização {fmtDataHora(i.ultima_sincronizacao_em)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}

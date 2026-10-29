"use client";

import { ChevronRightIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useCliente } from "@/features/clientes/api";
import { cn } from "@/lib/utils";

const ROTULOS: Record<string, string> = {
  clientes: "Clientes",
  dashboards: "Dashboards",
  relatorios: "Relatórios",
  integracoes: "Integrações",
  usuarios: "Usuários",
  configuracoes: "Configurações",
};
const UUID = /^[0-9a-f-]{36}$/i;

export function Breadcrumb() {
  const path = usePathname();
  const partes = path.split("/").filter(Boolean);
  const clienteId = partes[0] === "clientes" && partes[1] && UUID.test(partes[1]) ? partes[1] : null;
  const cliente = useCliente(clienteId);
  const itens = [{ href: "/", label: "V4 Insights" }];
  if (!partes.length) itens.push({ href: "/#visao-geral", label: "Visão geral" });
  partes.forEach((p, i) => {
    const href = "/" + partes.slice(0, i + 1).join("/");
    const label = UUID.test(p) ? (p === clienteId ? (cliente.data?.nome ?? "…") : "Detalhe") : (ROTULOS[p] ?? p);
    itens.push({ href, label });
  });
  return (
    <nav aria-label="Trilha de navegação" className="min-w-0">
      <ol className="flex items-center gap-1.5 truncate text-xs text-muted-foreground">
        {itens.map((it, i) => (
          <li key={it.href} className={cn("flex min-w-0 items-center gap-1", i < itens.length - 2 && "max-sm:hidden")}>
            {i > 0 && (
              <ChevronRightIcon
                className={cn("size-[13px] shrink-0 text-faint", i === itens.length - 2 && "max-sm:hidden")}
                aria-hidden
              />
            )}
            {i === itens.length - 1 ? (
              <span aria-current="page" className="truncate font-semibold text-foreground max-sm:text-sm">
                {it.label}
              </span>
            ) : (
              <Link href={it.href} className="truncate hover:text-foreground">
                {it.label}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

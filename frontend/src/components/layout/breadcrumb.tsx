"use client";

import { ChevronRightIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useCliente } from "@/features/clientes/api";

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
  const itens = [{ href: "/", label: "Início" }];
  partes.forEach((p, i) => {
    const href = "/" + partes.slice(0, i + 1).join("/");
    const label = UUID.test(p) ? (p === clienteId ? (cliente.data?.nome ?? "…") : "Detalhe") : (ROTULOS[p] ?? p);
    itens.push({ href, label });
  });
  return (
    <nav aria-label="Trilha de navegação" className="min-w-0">
      <ol className="flex items-center gap-1 truncate text-sm text-muted-foreground">
        {itens.map((it, i) => (
          <li key={it.href} className="flex min-w-0 items-center gap-1">
            {i > 0 && <ChevronRightIcon className="size-3.5 shrink-0" aria-hidden />}
            {i === itens.length - 1 ? (
              <span aria-current="page" className="truncate font-medium text-foreground">
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

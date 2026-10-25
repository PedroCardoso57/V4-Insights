"use client";

import {
  BarChart3Icon,
  BuildingIcon,
  FileTextIcon,
  HomeIcon,
  type LucideIcon,
  PlugIcon,
  SettingsIcon,
  UsersIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useClienteAtual } from "@/hooks/use-cliente-atual";
import { useMe } from "@/hooks/use-me";
import { cn } from "@/lib/utils";
import { pode } from "@/lib/permissoes";

interface Item {
  href: string;
  label: string;
  icon: LucideIcon;
  visivel?: boolean;
}

function itemAtivo(label: string, href: string, path: string): boolean {
  const ehDashboard = path.endsWith("/dashboards");
  if (href === "/") return path === "/";
  if (label === "Dashboards") return ehDashboard;
  if (href === "/clientes") return path.startsWith("/clientes") && !ehDashboard;
  return path.startsWith(href);
}

export function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const path = usePathname();
  const me = useMe().data;
  const [clienteAtual] = useClienteAtual();
  const itens: Item[] = [
    { href: "/", label: "Visão geral", icon: HomeIcon },
    { href: "/clientes", label: "Clientes", icon: BuildingIcon },
    {
      href: clienteAtual ? `/clientes/${clienteAtual}/dashboards` : "/clientes",
      label: "Dashboards",
      icon: BarChart3Icon,
    },
    { href: "/relatorios", label: "Relatórios", icon: FileTextIcon },
    { href: "/integracoes", label: "Integrações", icon: PlugIcon, visivel: pode.editar(me?.papel) },
    { href: "/usuarios", label: "Usuários", icon: UsersIcon, visivel: pode.gerirUsuarios(me?.papel) },
    { href: "/configuracoes", label: "Configurações", icon: SettingsIcon },
  ];
  return (
    <ul className="grid gap-1">
      {itens
        .filter((i) => i.visivel !== false)
        .map(({ href, label, icon: Icon }) => {
          const ativo = itemAtivo(label, href, path);
          return (
            <li key={label}>
              <Link
                href={href}
                onClick={onNavigate}
                aria-current={ativo ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground",
                  ativo && "bg-sidebar-accent font-medium text-sidebar-foreground",
                )}
              >
                <Icon className="size-4" aria-hidden /> {label}
              </Link>
            </li>
          );
        })}
    </ul>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 flex-col bg-sidebar p-3 lg:flex" aria-label="Navegação principal">
      <div className="px-3 py-3 text-base font-semibold text-sidebar-foreground">
        V4 <span className="text-primary">Insights</span>
      </div>
      <nav className="mt-2">
        <NavLinks />
      </nav>
    </aside>
  );
}

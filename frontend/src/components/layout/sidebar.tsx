"use client";

import {
  FileTextIcon,
  LayoutGridIcon,
  LineChartIcon,
  LogOutIcon,
  type LucideIcon,
  PlugIcon,
  SettingsIcon,
  UserIcon,
  UsersIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { SeloV4 } from "@/components/marca/simbolo-v4";
import { Avatar } from "@/components/avatar";
import { useAlertasIntegracao } from "@/features/integracoes/alertas";
import { useClienteAtual } from "@/hooks/use-cliente-atual";
import { useLogout, useMe } from "@/hooks/use-me";
import { PAPEL_LABEL } from "@/lib/format";
import { pode } from "@/lib/permissoes";
import { cn } from "@/lib/utils";

export interface Item {
  href: string;
  label: string;
  icon: LucideIcon;
  visivel?: boolean;
  contador?: number;
}

export function itemAtivo(label: string, href: string, path: string): boolean {
  const ehDashboard = path.endsWith("/dashboards");
  if (href === "/") return path === "/";
  if (label === "Dashboards") return ehDashboard;
  if (href === "/clientes") return path.startsWith("/clientes") && !ehDashboard;
  return path.startsWith(href);
}

export function Marca({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Link href="/" onClick={onNavigate} className="flex items-center gap-3 rounded-lg text-left">
      <SeloV4 className="size-9 rounded-xl shadow-[0_0_18px_var(--brand-glow)]" />
      <span>
        <strong className="block text-sm leading-none font-bold tracking-tight text-foreground">V4 Insights</strong>
        <span className="mt-1 block text-[11px] text-muted-foreground">V4 Bounnacorso</span>
      </span>
    </Link>
  );
}

/** Itens do menu principal visíveis para o papel do usuário. */
export function useItensNav(): Item[] {
  const me = useMe().data;
  const [clienteAtual] = useClienteAtual();
  const { alertas } = useAlertasIntegracao();
  const itens: Item[] = [
    { href: "/", label: "Visão geral", icon: LayoutGridIcon },
    { href: "/clientes", label: "Clientes", icon: UsersIcon },
    {
      href: clienteAtual ? `/clientes/${clienteAtual}/dashboards` : "/clientes",
      label: "Dashboards",
      icon: LineChartIcon,
    },
    { href: "/relatorios", label: "Relatórios", icon: FileTextIcon },
    {
      href: "/integracoes",
      label: "Integrações",
      icon: PlugIcon,
      visivel: pode.editar(me?.papel),
      contador: alertas.filter((a) => a.motivo === "reconexao").length,
    },
    { href: "/usuarios", label: "Usuários", icon: UserIcon, visivel: pode.gerirUsuarios(me?.papel) },
    { href: "/configuracoes", label: "Configurações", icon: SettingsIcon },
  ];
  return itens.filter((i) => i.visivel !== false);
}

export function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const path = usePathname();
  const itens = useItensNav();
  return (
    <>
      <span className="block px-3 py-1.5 text-[10px] font-semibold tracking-widest text-faint uppercase">
        Inteligência &amp; Operação
      </span>
      <ul className="grid gap-1">
        {itens.map(({ href, label, icon: Icon, contador }) => {
            const ativo = itemAtivo(label, href, path);
            return (
              <li key={label}>
                <Link
                  href={href}
                  onClick={onNavigate}
                  data-tour={`nav:${label}`}
                  aria-current={ativo ? "page" : undefined}
                  className={cn(
                    "flex items-center justify-between gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium text-text-secondary transition-colors hover:bg-subtle hover:text-foreground",
                    ativo && "bg-primary-soft font-semibold text-primary-ink hover:bg-primary-soft hover:text-primary-ink",
                  )}
                >
                  <span className="flex items-center gap-3">
                    <Icon className="size-[17px]" aria-hidden /> {label}
                  </span>
                  {!!contador && (
                    <span
                      className="rounded-full bg-primary px-1.5 py-0.5 text-[10px] leading-none font-bold text-white"
                      aria-label={`${contador} ${contador === 1 ? "integração requer" : "integrações requerem"} reconexão`}
                    >
                      {contador}
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
      </ul>
    </>
  );
}

export function Usuario() {
  const me = useMe().data;
  const sair = useLogout();
  if (!me) return null;
  return (
    <div className="flex items-center justify-between gap-2 px-2 py-1.5">
      <div className="flex min-w-0 items-center gap-2.5">
        <Avatar nome={me.nome} fotoUrl={me.foto_url} />
        <span className="min-w-0">
          <strong className="block truncate text-xs font-semibold text-foreground">{me.nome}</strong>
          <span className="block truncate text-[11px] text-muted-foreground">{PAPEL_LABEL[me.papel]}</span>
        </span>
      </div>
      <button
        type="button"
        onClick={() => sair.mutate()}
        aria-label="Sair"
        title="Encerrar sessão"
        className="cursor-pointer rounded-lg p-1.5 text-muted-foreground hover:bg-destructive-soft hover:text-destructive"
      >
        <LogOutIcon className="size-4" aria-hidden />
      </button>
    </div>
  );
}

/** Conteúdo da navegação lateral: compartilhado entre a barra fixa e o menu móvel. */
export function SidebarConteudo({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col justify-between">
      <div>
        <div className="flex h-[72px] items-center border-b px-5">
          <Marca onNavigate={onNavigate} />
        </div>
        <nav className="p-3" aria-label="Menu principal">
          <NavLinks onNavigate={onNavigate} />
        </nav>
      </div>
      <div className="border-t p-3">
        <Usuario />
      </div>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r bg-sidebar lg:block" aria-label="Navegação principal">
      <SidebarConteudo />
    </aside>
  );
}

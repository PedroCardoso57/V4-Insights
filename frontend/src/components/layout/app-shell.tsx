"use client";

import { MenuIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { Breadcrumb } from "@/components/layout/breadcrumb";
import { ClientSelector } from "@/components/layout/client-selector";
import { Notificacoes } from "@/components/layout/notificacoes";
import { Sidebar, SidebarConteudo } from "@/components/layout/sidebar";
import { StatusAtualizacao } from "@/components/layout/status-atualizacao";
import { TemaToggle } from "@/components/layout/tema-toggle";
import { ErroEstado } from "@/components/estado";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe } from "@/hooks/use-me";
import { ApiError } from "@/services/api/client";

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const me = useMe();
  const [menu, setMenu] = useState(false);
  const semSessao = me.error instanceof ApiError && me.error.status === 401;

  useEffect(() => {
    if (semSessao) router.replace("/login");
  }, [semSessao, router]);

  if (me.isPending || semSessao) {
    return (
      <div className="flex min-h-screen" aria-busy="true">
        <div className="hidden w-64 border-r bg-sidebar lg:block" />
        <div className="flex-1 space-y-4 p-8">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-28 w-full rounded-xl" />
          <Skeleton className="h-72 w-full rounded-xl" />
        </div>
      </div>
    );
  }
  if (me.isError) {
    return (
      <div className="mx-auto mt-20 max-w-md p-4">
        <ErroEstado erro={me.error} onRetry={() => me.refetch()} />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-background">
      <a
        href="#conteudo"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[60] focus:rounded-lg focus:bg-foreground focus:px-3 focus:py-2 focus:text-sm focus:text-background"
      >
        Pular para o conteúdo
      </a>
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
        <header className="sticky top-0 z-30 flex min-h-16 flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b bg-card/95 px-4 py-2.5 backdrop-blur-md sm:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <Sheet open={menu} onOpenChange={setMenu}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon-sm" className="lg:hidden" aria-label="Abrir menu">
                  <MenuIcon />
                </Button>
              </SheetTrigger>
              <SheetContent className="w-64 border-r bg-sidebar">
                <SheetTitle className="sr-only">Menu de navegação</SheetTitle>
                <SidebarConteudo onNavigate={() => setMenu(false)} />
              </SheetContent>
            </Sheet>
            <Breadcrumb />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusAtualizacao />
            <ClientSelector />
            <TemaToggle />
            <Notificacoes />
          </div>
        </header>
        <main id="conteudo" className="mx-auto w-full max-w-[1600px] flex-1 p-4 sm:p-8">
          {children}
        </main>
        <footer className="flex flex-wrap items-center justify-between gap-2 border-t px-4 py-4 text-[11px] text-muted-foreground sm:px-8">
          <span>
            <strong>V4 Insights</strong> — Plataforma Interna de Inteligência de Marketing · Unidade{" "}
            <strong>V4 Bounnacorso</strong>
          </span>
          <span className="font-mono-num">Fontes: Meta Ads &amp; Google Ads · uso exclusivo de colaboradores</span>
        </footer>
      </div>
    </div>
  );
}

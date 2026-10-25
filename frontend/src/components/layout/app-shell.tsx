"use client";

import { LogOutIcon, MenuIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { Breadcrumb } from "@/components/layout/breadcrumb";
import { ClientSelector } from "@/components/layout/client-selector";
import { NavLinks, Sidebar } from "@/components/layout/sidebar";
import { StatusAtualizacao } from "@/components/layout/status-atualizacao";
import { ErroEstado } from "@/components/estado";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useLogout, useMe } from "@/hooks/use-me";
import { PAPEL_LABEL } from "@/lib/format";
import { ApiError } from "@/services/api/client";

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const me = useMe();
  const sair = useLogout();
  const [menu, setMenu] = useState(false);
  const semSessao = me.error instanceof ApiError && me.error.status === 401;

  useEffect(() => {
    if (semSessao) router.replace("/login");
  }, [semSessao, router]);

  if (me.isPending || semSessao) {
    return (
      <div className="flex min-h-screen" aria-busy="true">
        <div className="hidden w-60 bg-sidebar lg:block" />
        <div className="flex-1 space-y-4 p-6">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-32 w-full" />
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
    <div className="flex min-h-screen">
      <a href="#conteudo" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-card focus:p-2">
        Pular para o conteúdo
      </a>
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex flex-wrap items-center gap-3 border-b bg-card/95 px-4 py-2.5 backdrop-blur">
          <Sheet open={menu} onOpenChange={setMenu}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Abrir menu">
                <MenuIcon />
              </Button>
            </SheetTrigger>
            <SheetContent className="bg-sidebar p-3">
              <SheetTitle className="px-3 py-3 text-sidebar-foreground">V4 Insights</SheetTitle>
              <NavLinks onNavigate={() => setMenu(false)} />
            </SheetContent>
          </Sheet>
          <div className="min-w-0 flex-1">
            <Breadcrumb />
          </div>
          <StatusAtualizacao />
          <ClientSelector />
          <div className="flex items-center gap-2 text-sm">
            <span className="hidden text-right leading-tight sm:block">
              {me.data.nome}
              <br />
              <span className="text-xs text-muted-foreground">{PAPEL_LABEL[me.data.papel]}</span>
            </span>
            <Button variant="ghost" size="icon" onClick={() => sair.mutate()} aria-label="Sair">
              <LogOutIcon />
            </Button>
          </div>
        </header>
        <main id="conteudo" className="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { BarraInferior } from "@/components/layout/barra-inferior";
import { Breadcrumb } from "@/components/layout/breadcrumb";
import { ClientSelector } from "@/components/layout/client-selector";
import { Notificacoes } from "@/components/layout/notificacoes";
import { Sidebar, SidebarConteudo } from "@/components/layout/sidebar";
import { StatusAtualizacao } from "@/components/layout/status-atualizacao";
import { TemaToggle } from "@/components/layout/tema-toggle";
import { ErroEstado } from "@/components/estado";
import { CarregandoMascote } from "@/components/mascote/carregando-mascote";
import { SeloV4 } from "@/components/marca/simbolo-v4";
import { Tutorial } from "@/features/tutorial/tutorial";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { useMe } from "@/hooks/use-me";
import { ApiError } from "@/services/api/client";

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const me = useMe();
  const [menu, setMenu] = useState(false);
  const semSessao = me.error instanceof ApiError && me.error.status === 401;
  // Se a sessão precisou carregar, o mascote comemora um instante antes de abrir o app.
  const [carregouDoZero] = useState(() => me.isPending);
  const [liberado, setLiberado] = useState(false);
  const comemorando = carregouDoZero && me.isSuccess && !liberado;

  useEffect(() => {
    if (semSessao) router.replace("/login");
  }, [semSessao, router]);

  useEffect(() => {
    if (!comemorando) return;
    const id = window.setTimeout(() => setLiberado(true), 900);
    return () => window.clearTimeout(id);
  }, [comemorando]);

  if (me.isPending || semSessao || comemorando) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4" aria-busy={!comemorando}>
        <CarregandoMascote concluido={comemorando} />
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
      <div className="flex min-w-0 flex-1 flex-col pb-[calc(4rem+env(safe-area-inset-bottom))] lg:pb-0 lg:pl-64">
        <header className="sticky top-0 z-30 flex min-h-14 flex-wrap items-center gap-x-3 gap-y-2 border-b bg-card/95 px-4 py-2.5 backdrop-blur-md sm:min-h-16 sm:gap-x-4 sm:px-8">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <Link href="/" aria-label="V4 Insights: visão geral" className="shrink-0 lg:hidden">
              <SeloV4 className="size-8 rounded-lg shadow-[0_0_14px_var(--brand-glow)]" />
            </Link>
            <Breadcrumb />
          </div>
          <div className="order-last w-full sm:order-none sm:w-auto">
            <ClientSelector />
          </div>
          <div className="flex items-center gap-1 sm:gap-2">
            <span className="hidden sm:contents">
              <StatusAtualizacao />
            </span>
            <TemaToggle />
            <Notificacoes />
          </div>
        </header>
        <main id="conteudo" className="mx-auto w-full max-w-[1600px] flex-1 p-4 sm:p-8">
          {children}
        </main>
        <footer className="flex flex-wrap items-center justify-between gap-2 border-t px-4 py-4 text-[11px] text-muted-foreground max-sm:hidden sm:px-8">
          <span>
            <strong>V4 Insights</strong> — Plataforma Interna de Inteligência de Marketing · Unidade{" "}
            <strong>V4 Bounnacorso</strong>
          </span>
          <span className="font-mono-num">Fontes: Meta, Google, LinkedIn &amp; TikTok Ads · uso exclusivo de colaboradores</span>
        </footer>
      </div>
      <BarraInferior onMais={() => setMenu(true)} menuAberto={menu} />
      <Sheet open={menu} onOpenChange={setMenu}>
        <SheetContent className="w-72 border-r bg-sidebar">
          <SheetTitle className="sr-only">Menu de navegação</SheetTitle>
          <SidebarConteudo onNavigate={() => setMenu(false)} />
        </SheetContent>
      </Sheet>
      <Tutorial />
    </div>
  );
}

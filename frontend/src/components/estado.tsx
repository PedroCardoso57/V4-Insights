"use client";

import { AlertTriangleIcon, InboxIcon, RotateCwIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/services/api/client";

export function CarregandoLinhas({ linhas = 4 }: { linhas?: number }) {
  return (
    <div className="grid gap-2" aria-busy="true" aria-label="Carregando">
      {Array.from({ length: linhas }, (_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

export function mensagemDeErro(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return "Erro inesperado.";
}

/** Erro com mensagem útil, identificador de correlação e ação de tentar novamente. */
export function ErroEstado({ erro, onRetry }: { erro: unknown; onRetry?: () => void }) {
  const rid = erro instanceof ApiError ? erro.requestId : undefined;
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm">
      <div className="flex items-center gap-2 font-medium text-destructive">
        <AlertTriangleIcon className="size-4" /> {mensagemDeErro(erro)}
      </div>
      {rid && <p className="text-xs text-muted-foreground">Código de correlação: <code>{rid}</code></p>}
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCwIcon /> Tentar novamente
        </Button>
      )}
    </div>
  );
}

export function Vazio({ titulo, children, acao }: { titulo: string; children?: ReactNode; acao?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed bg-card px-6 py-10 text-center">
      <InboxIcon className="size-8 text-muted-foreground" aria-hidden />
      <p className="font-medium">{titulo}</p>
      {children && <div className="max-w-md text-sm text-muted-foreground">{children}</div>}
      {acao && <div className="mt-2">{acao}</div>}
    </div>
  );
}

interface QueryLike<T> {
  data?: T;
  isPending: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => unknown;
}

/** Renderiza loading/erro/vazio/sucesso de forma uniforme para uma query. */
export function Consulta<T>({
  query,
  vazio,
  carregando,
  children,
}: {
  query: QueryLike<T>;
  vazio?: (d: T) => ReactNode | false;
  carregando?: ReactNode;
  children: (d: T) => ReactNode;
}) {
  if (query.isPending) return <>{carregando ?? <CarregandoLinhas />}</>;
  if (query.isError) return <ErroEstado erro={query.error} onRetry={() => query.refetch()} />;
  const d = query.data as T;
  const v = vazio?.(d);
  if (v) return <>{v}</>;
  return <>{children(d)}</>;
}

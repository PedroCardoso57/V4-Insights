import { cn } from "@/lib/utils";

/** Selo com a inicial do nome (identificação visual de clientes nas listas). */
export function Inicial({ nome, className }: { nome: string; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-lg border border-primary-border bg-primary-soft text-xs font-bold text-primary",
        className,
      )}
    >
      {nome.trim()[0]?.toUpperCase() ?? "?"}
    </span>
  );
}

"use client";

import { useRouter } from "next/navigation";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useClientes } from "@/features/clientes/api";
import { useClienteAtual } from "@/hooks/use-cliente-atual";

/** Seletor global do cliente em foco (somente clientes da carteira do usuário). */
export function ClientSelector() {
  const router = useRouter();
  const [atual, setAtual] = useClienteAtual();
  const q = useClientes({ status: "ativo", page_size: 100, order_by: "nome" });
  const itens = q.data?.items ?? [];
  return (
    <Select
      value={itens.some((c) => c.id === atual) ? (atual ?? undefined) : undefined}
      onValueChange={(id) => {
        setAtual(id);
        router.push(`/clientes/${id}`);
      }}
      disabled={!itens.length}
    >
      <SelectTrigger data-tour="cliente" className="h-9 w-full text-[13px] sm:h-8 sm:w-52 sm:text-xs" aria-label="Selecionar cliente">
        <SelectValue placeholder={q.isPending ? "Carregando clientes…" : itens.length ? "Selecionar cliente" : "Sem clientes"} />
      </SelectTrigger>
      <SelectContent>
        {itens.map((c) => (
          <SelectItem key={c.id} value={c.id}>
            {c.nome}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

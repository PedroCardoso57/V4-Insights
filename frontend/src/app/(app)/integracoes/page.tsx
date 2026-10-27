"use client";

import { useRouter, useSearchParams } from "next/navigation";

import { PageHeader } from "@/components/page-header";
import { Alert } from "@/components/ui/alert";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useCliente, useClientes } from "@/features/clientes/api";
import { IntegracoesLista } from "@/features/integracoes/integracoes-lista";
import { useMe } from "@/hooks/use-me";
import { pode } from "@/lib/permissoes";

const ERROS: Record<string, string> = {
  autorizacao_negada: "A autorização foi cancelada ou negada no provedor.",
  conexao_recusada: "O provedor recusou a conexão. Verifique permissões e escopos concedidos.",
  cliente_arquivado: "Cliente arquivado não aceita novas integrações.",
};
const TODOS = "__todos__";

export default function IntegracoesPage() {
  const params = useSearchParams();
  const router = useRouter();
  const clienteId = params.get("cliente_id");
  const erro = params.get("erro");
  const papel = useMe().data?.papel;
  const clientes = useClientes({ page_size: 100 });
  const cliente = useCliente(clienteId);

  if (!pode.editar(papel)) {
    return <Alert variant="warning">Seu perfil não tem acesso às integrações.</Alert>;
  }
  return (
    <>
      <PageHeader
        titulo="Integrações e conectores de mídia"
        descricao="Conexões OAuth com Meta Ads, Google Ads, LinkedIn Ads e TikTok Ads: contas selecionadas, status de sincronização e reprocessamento."
        acoes={
          <Select value={clienteId ?? TODOS} onValueChange={(v) => router.replace(v === TODOS ? "/integracoes" : `/integracoes?cliente_id=${v}`)}>
            <SelectTrigger className="w-64" aria-label="Filtrar por cliente"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={TODOS}>Todos os clientes</SelectItem>
              {clientes.data?.items.map((c) => <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>)}
            </SelectContent>
          </Select>
        }
      />
      {erro && <Alert variant="destructive" className="mb-4">{ERROS[erro] ?? "Falha na conexão com o provedor."}</Alert>}
      <IntegracoesLista
        clienteId={clienteId ?? undefined}
        arquivado={cliente.data?.status === "arquivado"}
        mostrarCliente={clienteId ? undefined : (id) => `/clientes/${id}?aba=integracoes`}
      />
    </>
  );
}

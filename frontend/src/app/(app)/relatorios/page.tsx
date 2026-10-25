"use client";

import { ArrowLeftIcon, SearchIcon } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Consulta } from "@/components/estado";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useClientes } from "@/features/clientes/api";
import { useRelatorio } from "@/features/relatorios/api";
import { EditorRelatorio } from "@/features/relatorios/editor";
import { ListaRelatorios } from "@/features/relatorios/lista";
import { useMe } from "@/hooks/use-me";
import { pode } from "@/lib/permissoes";

export default function RelatoriosPage() {
  const params = useSearchParams();
  const router = useRouter();
  const id = params.get("id");
  const clienteId = params.get("cliente_id") ?? undefined;
  const papel = useMe().data?.papel;
  const clientes = useClientes({ page_size: 100 });
  const [texto, setTexto] = useState("");
  const [busca, setBusca] = useState<string>();
  const nomes = new Map(clientes.data?.items.map((c) => [c.id, c.nome]));
  const rel = useRelatorio(id && id !== "novo" ? id : null);

  if (id) {
    const voltar = (
      <Button asChild variant="ghost"><Link href="/relatorios"><ArrowLeftIcon /> Relatórios</Link></Button>
    );
    if (id === "novo") {
      return (
        <>
          <PageHeader titulo="Novo relatório" acoes={voltar} />
          <EditorRelatorio clienteInicial={clienteId} podeEditar={pode.editar(papel)} onSalvo={(r) => router.replace(`/relatorios?id=${r.id}`)} />
        </>
      );
    }
    return (
      <Consulta query={rel}>
        {(r) => (
          <>
            <PageHeader titulo={r.titulo} descricao={nomes.get(r.cliente_id)} acoes={voltar} />
            <EditorRelatorio relatorio={r} podeEditar={pode.editar(papel)} onSalvo={() => rel.refetch()} />
          </>
        )}
      </Consulta>
    );
  }

  return (
    <>
      <PageHeader titulo="Relatórios" descricao="Configure, visualize a prévia e gere PDFs dos clientes da sua carteira." />
      <form className="mb-4 flex gap-2" role="search" onSubmit={(e) => { e.preventDefault(); setBusca(texto.trim() || undefined); }}>
        <Input type="search" aria-label="Buscar relatório" placeholder="Buscar por título" value={texto} onChange={(e) => setTexto(e.target.value)} className="w-64" />
        <Button type="submit" variant="outline"><SearchIcon /> Buscar</Button>
      </form>
      <ListaRelatorios clienteId={clienteId} search={busca} nomesClientes={nomes} />
    </>
  );
}

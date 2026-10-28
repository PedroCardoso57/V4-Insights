"use client";

import { ArchiveIcon, BarChart3Icon, PencilIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Confirmar } from "@/components/confirmar";
import { Consulta, mensagemDeErro } from "@/components/estado";
import { Inicial } from "@/components/inicial";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useArquivarCliente, useCliente, useExcluirCliente } from "@/features/clientes/api";
import { ClienteFormDialog } from "@/features/clientes/cliente-form";
import { Equipe } from "@/features/clientes/equipe";
import { IntegracoesLista } from "@/features/integracoes/integracoes-lista";
import { PainelCliente } from "@/features/metricas/painel";
import { ListaRelatorios } from "@/features/relatorios/lista";
import { useMe } from "@/hooks/use-me";
import { fmtData } from "@/lib/format";
import { pode } from "@/lib/permissoes";

export default function ClienteDetalhePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const aba = useSearchParams().get("aba") ?? "visao";
  const papel = useMe().data?.papel;
  const q = useCliente(id);
  const arquivar = useArquivarCliente();
  const [editando, setEditando] = useState(false);
  const [arquivando, setArquivando] = useState(false);
  const excluir = useExcluirCliente();
  const [excluindo, setExcluindo] = useState(false);

  return (
    <Consulta query={q}>
      {(c) => {
        const arquivado = c.status === "arquivado";
        return (
          <>
            <PageHeader
              titulo={<span className="flex flex-wrap items-center gap-3"><Inicial nome={c.nome} className="size-10 rounded-xl text-sm" />{c.nome}</span>}
              selo={arquivado ? <Badge ponto>arquivado</Badge> : <Badge ponto variant="success">ativo</Badge>}
              descricao={[c.nome_fantasia, c.documento && `Documento ${c.documento}`, `desde ${fmtData(c.criado_em)}`].filter(Boolean).join(" · ")}
              acoes={
                <>
                  <Button asChild variant="outline"><Link href={`/clientes/${c.id}/dashboards`}><BarChart3Icon /> Dashboards</Link></Button>
                  {pode.gerirClientes(papel) && !arquivado && (
                    <>
                      <Button variant="outline" onClick={() => setEditando(true)}><PencilIcon /> Editar</Button>
                      <Button variant="destructive" onClick={() => setArquivando(true)}><ArchiveIcon /> Arquivar</Button>
                    </>
                  )}
                  {pode.excluirClientes(papel) && (
                    <Button variant="destructive" onClick={() => setExcluindo(true)}><Trash2Icon /> Excluir</Button>
                  )}
                </>
              }
            />
            <Tabs value={aba} onValueChange={(v) => router.replace(`/clientes/${c.id}?aba=${v}`, { scroll: false })}>
              <TabsList aria-label="Seções do cliente">
                <TabsTrigger value="visao">Indicadores</TabsTrigger>
                {pode.editar(papel) && <TabsTrigger value="integracoes">Integrações</TabsTrigger>}
                <TabsTrigger value="relatorios">Relatórios</TabsTrigger>
                <TabsTrigger value="equipe">Equipe</TabsTrigger>
              </TabsList>
              <TabsContent value="visao"><PainelCliente clienteId={c.id} /></TabsContent>
              {pode.editar(papel) && (
                <TabsContent value="integracoes"><IntegracoesLista clienteId={c.id} arquivado={arquivado} /></TabsContent>
              )}
              <TabsContent value="relatorios">
                <ListaRelatorios clienteId={c.id} />
              </TabsContent>
              <TabsContent value="equipe"><Equipe clienteId={c.id} papel={papel} /></TabsContent>
            </Tabs>
            <ClienteFormDialog aberto={editando} onAberto={setEditando} cliente={c} />
            <Confirmar
              aberto={arquivando}
              onAberto={setArquivando}
              titulo="Arquivar cliente"
              descricao={<>Arquivar <strong>{c.nome}</strong>? Métricas, dashboards e relatórios são preservados; novas integrações e coletas ficam bloqueadas.</>}
              acao="Arquivar"
              perigo
              onConfirmar={() =>
                arquivar.mutate(c.id, { onSuccess: () => toast.success("Cliente arquivado."), onError: (e) => toast.error(mensagemDeErro(e)) })
              }
            />
            <Confirmar
              aberto={excluindo}
              onAberto={setExcluindo}
              titulo="Excluir cliente"
              descricao={
                <>
                  Excluir <strong>{c.nome}</strong> definitivamente? Integrações, métricas, dashboards e relatórios
                  deste cliente serão apagados e não podem ser recuperados. Para só tirar o cliente de circulação, use
                  Arquivar.
                </>
              }
              acao="Excluir definitivamente"
              perigo
              onConfirmar={() =>
                excluir.mutate(c.id, {
                  onSuccess: () => {
                    toast.success("Cliente excluído.");
                    router.push("/clientes");
                  },
                  onError: (e) => toast.error(mensagemDeErro(e)),
                })
              }
            />
          </>
        );
      }}
    </Consulta>
  );
}

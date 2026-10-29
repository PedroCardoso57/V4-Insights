"use client";

import { ArrowDownIcon, ArrowUpIcon, PlusIcon, SearchIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Confirmar } from "@/components/confirmar";
import { Consulta, mensagemDeErro, Vazio } from "@/components/estado";
import { Inicial } from "@/components/inicial";
import { PageHeader } from "@/components/page-header";
import { Paginacao } from "@/components/paginacao";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useClientes, useExcluirCliente, type Cliente, type FiltroClientes } from "@/features/clientes/api";
import { ClienteFormDialog } from "@/features/clientes/cliente-form";
import { useMe } from "@/hooks/use-me";
import { fmtData } from "@/lib/format";
import { pode } from "@/lib/permissoes";

type Ordem = NonNullable<FiltroClientes["order_by"]>;

export default function ClientesPage() {
  const router = useRouter();
  const papel = useMe().data?.papel;
  const [texto, setTexto] = useState("");
  const [f, setF] = useState<FiltroClientes>({ status: "ativo", page: 1, page_size: 20, order_by: "nome", order: "asc" });
  const [criando, setCriando] = useState(false);
  const [excluindo, setExcluindo] = useState<Cliente | null>(null);
  const excluir = useExcluirCliente();
  const q = useClientes(f);

  const ordenar = (col: Ordem) =>
    setF({ ...f, page: 1, order_by: col, order: f.order_by === col && f.order === "asc" ? "desc" : "asc" });
  const th = (col: Ordem, label: string) => (
    <TableHead aria-sort={f.order_by === col ? (f.order === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" className="inline-flex items-center gap-1 uppercase" onClick={() => ordenar(col)}>
        {label}
        {f.order_by === col && (f.order === "asc" ? <ArrowUpIcon className="size-3" /> : <ArrowDownIcon className="size-3" />)}
      </button>
    </TableHead>
  );

  return (
    <>
      <PageHeader
        titulo="Carteira de clientes"
        descricao="Acompanhe as contas da sua carteira, responsáveis e integrações. Somente clientes atribuídos a você aparecem aqui."
        acoes={pode.gerirClientes(papel) && <Button onClick={() => setCriando(true)}><PlusIcon /> Novo cliente</Button>}
      />
      <form
        className="mb-5 flex flex-wrap items-center gap-2 rounded-xl border bg-card p-4 shadow-xs"
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          setF({ ...f, page: 1, search: texto.trim() || undefined });
        }}
      >
        <div className="relative w-full sm:w-72">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2 text-faint" aria-hidden />
          <Input type="search" aria-label="Buscar por nome" placeholder="Buscar por nome" maxLength={100} value={texto}
            onChange={(e) => setTexto(e.target.value)} className="pl-8" />
        </div>
        <Select value={f.status ?? "todos"} onValueChange={(v) => setF({ ...f, page: 1, status: v === "todos" ? undefined : (v as FiltroClientes["status"]) })}>
          <SelectTrigger className="flex-1 sm:w-40 sm:flex-none" aria-label="Status"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="ativo">Ativos</SelectItem>
            <SelectItem value="arquivado">Arquivados</SelectItem>
            <SelectItem value="todos">Todos</SelectItem>
          </SelectContent>
        </Select>
        <Button type="submit" variant="outline"><SearchIcon /> Buscar</Button>
        {q.data && (
          <span className="ml-auto font-mono-num text-xs text-muted-foreground">
            {q.data.items.length} de {q.data.total} {q.data.total === 1 ? "cliente" : "clientes"}
          </span>
        )}
      </form>
      <Consulta
        query={q}
        vazio={(d) =>
          d.items.length === 0 && (
            <Vazio
              titulo={f.search ? "Nenhum cliente encontrado" : "Sua carteira está vazia"}
              acao={pode.gerirClientes(papel) && !f.search ? <Button onClick={() => setCriando(true)}>Cadastrar cliente</Button> : undefined}
            >
              {f.search ? "Revise o termo da busca ou o filtro de status." : "Clientes atribuídos a você aparecerão aqui."}
            </Vazio>
          )
        }
      >
        {(d) => (
          <>
            <div className="overflow-hidden rounded-xl border bg-card shadow-xs">
            <Table>
              <TableHeader>
                <TableRow>
                  {th("nome", "Nome")}
                  <TableHead>Nome fantasia</TableHead>
                  <TableHead>Status</TableHead>
                  {th("criado_em", "Criado em")}
                  {pode.excluirClientes(papel) && <TableHead className="w-12"><span className="sr-only">Ações</span></TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {d.items.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Inicial nome={c.nome} />
                        <Link className="font-semibold hover:underline" href={`/clientes/${c.id}`}>{c.nome}</Link>
                      </div>
                    </TableCell>
                    <TableCell className="text-text-secondary">{c.nome_fantasia ?? "—"}</TableCell>
                    <TableCell><Badge ponto variant={c.status === "ativo" ? "success" : "secondary"}>{c.status}</Badge></TableCell>
                    <TableCell className="font-mono-num text-xs text-muted-foreground">{fmtData(c.criado_em)}</TableCell>
                    {pode.excluirClientes(papel) && (
                      <TableCell data-label="" data-canto="">
                        <Button variant="ghost" size="icon-sm" aria-label={`Excluir ${c.nome}`} onClick={() => setExcluindo(c)}>
                          <Trash2Icon />
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            </div>
            <Paginacao page={d.page} pageSize={d.page_size} total={d.total} onPage={(p) => setF({ ...f, page: p })} />
          </>
        )}
      </Consulta>
      <Confirmar
        aberto={!!excluindo}
        onAberto={(v) => !v && setExcluindo(null)}
        titulo="Excluir cliente"
        descricao={
          <>
            Excluir <strong>{excluindo?.nome}</strong> definitivamente? Integrações, métricas, dashboards e relatórios
            deste cliente serão apagados e não podem ser recuperados.
          </>
        }
        acao="Excluir definitivamente"
        perigo
        onConfirmar={() =>
          excluindo &&
          excluir.mutate(excluindo.id, {
            onSuccess: () => toast.success("Cliente excluído."),
            onError: (e) => toast.error(mensagemDeErro(e)),
          })
        }
      />
      <ClienteFormDialog aberto={criando} onAberto={setCriando} onSalvo={(c) => router.push(`/clientes/${c.id}`)} />
    </>
  );
}

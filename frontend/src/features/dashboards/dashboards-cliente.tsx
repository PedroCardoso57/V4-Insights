"use client";

import { ArrowDownIcon, ArrowUpIcon, PlusIcon, Trash2Icon, XIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Confirmar } from "@/components/confirmar";
import { Consulta, mensagemDeErro } from "@/components/estado";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { filtrosPadrao, useMetricas, type Filtros } from "@/features/metricas/api";
import { CampanhasTable } from "@/features/metricas/campanhas-table";
import { FiltrosBar } from "@/features/metricas/filtros-bar";
import { AvisoSync, KpiCard } from "@/features/metricas/kpis";
import { PainelCliente } from "@/features/metricas/painel";
import { SerieChart } from "@/features/metricas/serie-chart";
import { useIntegracoes } from "@/features/integracoes/api";
import { useMe } from "@/hooks/use-me";
import { KPI_LABEL, type KpiKey } from "@/lib/format";
import { pode } from "@/lib/permissoes";

import { useCriarDashboard, useDashboards, useExcluirDashboard, useSalvarDashboard, type Dashboard, type WidgetIn } from "./api";

const TIPOS = { kpi: "Card de KPI", serie: "Série temporal", tabela_campanhas: "Tabela de campanhas" } as const;
type Tipo = keyof typeof TIPOS;

const WIDGETS_INICIAIS: WidgetIn[] = [
  { tipo: "kpi", titulo: "Investimento", config: { kpi: "investimento" } },
  { tipo: "kpi", titulo: "Cliques", config: { kpi: "cliques" } },
  { tipo: "kpi", titulo: "CTR", config: { kpi: "ctr" } },
  { tipo: "kpi", titulo: "CPA", config: { kpi: "cpa" } },
  { tipo: "serie", titulo: "Investimento por período", config: { kpi: "investimento" } },
  { tipo: "tabela_campanhas", titulo: "Campanhas", config: {} },
];

export function DashboardsCliente({ clienteId }: { clienteId: string }) {
  const papel = useMe().data?.papel;
  const lista = useDashboards(clienteId);
  const criar = useCriarDashboard();
  const [aba, setAba] = useState("geral");
  const [nome, setNome] = useState("");

  return (
    <Tabs value={aba} onValueChange={setAba}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <TabsList aria-label="Dashboards">
          <TabsTrigger value="geral">Visão geral</TabsTrigger>
          {lista.data?.items.map((d) => (
            <TabsTrigger key={d.id} value={d.id}>{d.nome}</TabsTrigger>
          ))}
        </TabsList>
        {pode.editar(papel) && (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              criar.mutate(
                { clienteId, nome: nome.trim(), widgets: WIDGETS_INICIAIS },
                {
                  onSuccess: (d) => {
                    setNome("");
                    setAba(d.id);
                    toast.success("Dashboard criado.");
                  },
                  onError: (e) => toast.error(mensagemDeErro(e)),
                },
              );
            }}
          >
            <Input aria-label="Nome do novo dashboard" placeholder="Novo dashboard" value={nome} maxLength={180}
              onChange={(e) => setNome(e.target.value)} className="w-48" />
            <Button type="submit" disabled={!nome.trim() || criar.isPending}><PlusIcon /> Criar</Button>
          </form>
        )}
      </div>
      <TabsContent value="geral">
        <PainelCliente clienteId={clienteId} />
      </TabsContent>
      <Consulta query={lista} carregando={null}>
        {(d) => (
          <>
            {d.items.map((dash) => (
              <TabsContent key={dash.id} value={dash.id}>
                <DashboardView dashboard={dash} editavel={pode.editar(papel)} onExcluido={() => setAba("geral")} />
              </TabsContent>
            ))}
          </>
        )}
      </Consulta>
    </Tabs>
  );
}

function DashboardView({ dashboard, editavel, onExcluido }: { dashboard: Dashboard; editavel: boolean; onExcluido: () => void }) {
  const [filtros, setFiltros] = useState<Filtros>(() => ({ ...filtrosPadrao(), ...(dashboard.filtros as Partial<Filtros>) }));
  const [editando, setEditando] = useState(false);
  const [rascunho, setRascunho] = useState<WidgetIn[]>([]);
  const [excluir, setExcluir] = useState(false);
  const [agora] = useState(() => Date.now());
  const integracoes = useIntegracoes(dashboard.cliente_id);
  const { resumo, serie, campanhas } = useMetricas(dashboard.cliente_id, filtros);
  const salvar = useSalvarDashboard();
  const remover = useExcluirDashboard();
  const moeda = resumo.data?.moedas[0] ?? "BRL";

  const widgets: WidgetIn[] = editando
    ? rascunho
    : dashboard.widgets.map((w) => ({ tipo: w.tipo as Tipo, titulo: w.titulo, config: w.config, layout: w.layout }));
  const mover = (i: number, d: number) => {
    const n = [...rascunho];
    const j = i + d;
    if (j < 0 || j >= n.length) return;
    [n[i], n[j]] = [n[j]!, n[i]!];
    setRascunho(n);
  };

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <FiltrosBar filtros={filtros} onChange={setFiltros} integracoes={integracoes.data?.items} />
        {editavel && (
          <div className="flex gap-2">
            {editando ? (
              <>
                <Button variant="outline" onClick={() => setEditando(false)}>Cancelar</Button>
                <Button
                  disabled={salvar.isPending}
                  onClick={() =>
                    salvar.mutate(
                      {
                        id: dashboard.id,
                        body: {
                          filtros: { granularidade: filtros.granularidade, comparar: filtros.comparar, plataforma: filtros.plataforma },
                          widgets: rascunho,
                        },
                      },
                      {
                        onSuccess: () => {
                          setEditando(false);
                          toast.success("Dashboard salvo.");
                        },
                        onError: (e) => toast.error(mensagemDeErro(e)),
                      },
                    )
                  }
                >
                  Salvar layout
                </Button>
              </>
            ) : (
              <>
                <Button variant="outline" onClick={() => { setRascunho(widgets); setEditando(true); }}>Editar widgets</Button>
                <Button variant="outline" className="text-destructive" onClick={() => setExcluir(true)}><Trash2Icon /> Excluir</Button>
              </>
            )}
          </div>
        )}
      </div>
      {editando && <NovoWidget onAdd={(w) => setRascunho([...rascunho, w])} />}
      {resumo.data && <AvisoSync resumo={resumo.data} agora={agora} />}
      {!widgets.length && <p className="text-sm text-muted-foreground">Este dashboard ainda não tem widgets.</p>}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {widgets.map((w, i) => {
          const kpi = ((w.config as { kpi?: KpiKey }).kpi ?? "investimento") as KpiKey;
          const largo = w.tipo !== "kpi";
          return (
            <div key={`${w.tipo}-${i}`} className={largo ? "relative col-span-full" : "relative"}>
              {editando && (
                <div className="absolute top-1 right-1 z-10 flex gap-0.5 rounded-md bg-card/90 p-0.5 shadow-xs">
                  <Button variant="ghost" size="icon" className="size-7" aria-label="Mover para cima" onClick={() => mover(i, -1)}><ArrowUpIcon /></Button>
                  <Button variant="ghost" size="icon" className="size-7" aria-label="Mover para baixo" onClick={() => mover(i, 1)}><ArrowDownIcon /></Button>
                  <Button variant="ghost" size="icon" className="size-7" aria-label="Remover widget" onClick={() => setRascunho(rascunho.filter((_, j) => j !== i))}><XIcon /></Button>
                </div>
              )}
              {w.tipo === "kpi" && (resumo.data ? <KpiCard resumo={resumo.data} kpi={kpi} /> : <Skeleton className="h-24" />)}
              {w.tipo === "serie" && (
                <Card>
                  <CardHeader className="border-b"><CardTitle>{w.titulo}</CardTitle></CardHeader>
                  <CardContent className="pt-4">{serie.data ? <SerieChart serie={serie.data} kpi={kpi} moeda={moeda} /> : <Skeleton className="h-72" />}</CardContent>
                </Card>
              )}
              {w.tipo === "tabela_campanhas" && (
                <Card>
                  <CardHeader className="border-b"><CardTitle>{w.titulo}</CardTitle></CardHeader>
                  <CardContent className="p-0">{campanhas.data ? <CampanhasTable campanhas={campanhas.data.items} moeda={moeda} /> : <Skeleton className="h-40" />}</CardContent>
                </Card>
              )}
            </div>
          );
        })}
      </div>
      <Confirmar
        aberto={excluir}
        onAberto={setExcluir}
        titulo="Excluir dashboard"
        descricao="O dashboard e seus widgets serão excluídos. As métricas não são afetadas."
        acao="Excluir"
        perigo
        onConfirmar={() =>
          remover.mutate(dashboard, {
            onSuccess: () => {
              toast.success("Dashboard excluído.");
              onExcluido();
            },
            onError: (e) => toast.error(mensagemDeErro(e)),
          })
        }
      />
    </div>
  );
}

function NovoWidget({ onAdd }: { onAdd: (w: WidgetIn) => void }) {
  const [tipo, setTipo] = useState<Tipo>("kpi");
  const [kpi, setKpi] = useState<KpiKey>("investimento");
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-3">
      <Badge variant="outline">Novo widget</Badge>
      <Select value={tipo} onValueChange={(v) => setTipo(v as Tipo)}>
        <SelectTrigger className="w-48" aria-label="Tipo de widget"><SelectValue /></SelectTrigger>
        <SelectContent>
          {(Object.keys(TIPOS) as Tipo[]).map((t) => <SelectItem key={t} value={t}>{TIPOS[t]}</SelectItem>)}
        </SelectContent>
      </Select>
      {tipo !== "tabela_campanhas" && (
        <Select value={kpi} onValueChange={(v) => setKpi(v as KpiKey)}>
          <SelectTrigger className="w-48" aria-label="Métrica"><SelectValue /></SelectTrigger>
          <SelectContent>
            {(Object.keys(KPI_LABEL) as KpiKey[]).map((k) => <SelectItem key={k} value={k}>{KPI_LABEL[k]}</SelectItem>)}
          </SelectContent>
        </Select>
      )}
      <Button
        onClick={() =>
          onAdd({
            tipo,
            titulo: tipo === "tabela_campanhas" ? "Campanhas" : KPI_LABEL[kpi],
            config: tipo === "tabela_campanhas" ? {} : { kpi },
          })
        }
      >
        <PlusIcon /> Adicionar
      </Button>
    </div>
  );
}

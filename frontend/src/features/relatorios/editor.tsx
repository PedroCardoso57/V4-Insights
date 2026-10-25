"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { FileDownIcon, SaveIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { mensagemDeErro } from "@/components/estado";
import { Field } from "@/components/ui/form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useClientes } from "@/features/clientes/api";
import { KPI_LABEL, PLATAFORMA_LABEL } from "@/lib/format";

import { useGerarPdf, useSalvarRelatorio, type Relatorio } from "./api";
import { Execucoes } from "./execucoes";
import { PreviewRelatorio } from "./preview";
import { GRAFICO_LABEL, GRAFICOS, KPIS, PERIODOS, relatorioSchema, resolverPeriodo, TEMPLATES, type RelatorioForm } from "./schema";

function paraForm(r?: Relatorio, clienteId?: string): RelatorioForm {
  const c = r?.configuracao;
  return {
    cliente_id: r?.cliente_id ?? clienteId ?? "",
    titulo: r?.titulo ?? "",
    template: c?.template ?? "visao_executiva",
    periodo_tipo: c?.periodo?.tipo ?? "ultimos_30_dias",
    inicio: c?.periodo?.inicio ?? undefined,
    fim: c?.periodo?.fim ?? undefined,
    plataformas: c?.plataformas ?? [],
    kpis: c?.kpis ?? ["investimento", "impressoes", "cliques", "ctr", "cpc", "conversoes", "cpa", "roas"],
    graficos: c?.graficos ?? ["serie_investimento", "tabela_campanhas"],
    granularidade: c?.granularidade ?? "dia",
    comparar: c?.comparar ?? true,
    comentarios: c?.comentarios ?? "",
  };
}

export function EditorRelatorio({
  relatorio,
  clienteInicial,
  podeEditar,
  onSalvo,
}: {
  relatorio?: Relatorio;
  clienteInicial?: string;
  podeEditar: boolean;
  onSalvo: (r: Relatorio) => void;
}) {
  const clientes = useClientes({ status: "ativo", page_size: 100 });
  const salvar = useSalvarRelatorio();
  const gerar = useGerarPdf();
  const [chave, setChave] = useState(() => crypto.randomUUID());
  const form = useForm<RelatorioForm>({ resolver: zodResolver(relatorioSchema), defaultValues: paraForm(relatorio, clienteInicial) });
  const { register, control, handleSubmit, formState, reset } = form;
  useEffect(() => reset(paraForm(relatorio, clienteInicial)), [relatorio, clienteInicial, reset]);
  const valores = useWatch({ control });

  const periodo = useMemo(
    () => resolverPeriodo(valores.periodo_tipo ?? "ultimos_30_dias", valores.inicio, valores.fim),
    [valores.periodo_tipo, valores.inicio, valores.fim],
  );

  const enviar = (v: RelatorioForm) =>
    salvar.mutate(
      {
        id: relatorio?.id,
        clienteId: v.cliente_id,
        titulo: v.titulo,
        configuracao: {
          template: v.template,
          periodo: { tipo: v.periodo_tipo, inicio: v.periodo_tipo === "personalizado" ? v.inicio : null, fim: v.periodo_tipo === "personalizado" ? v.fim : null },
          plataformas: v.plataformas,
          conta_anuncio_ids: relatorio?.configuracao.conta_anuncio_ids ?? [],
          kpis: v.kpis,
          graficos: v.graficos,
          granularidade: v.granularidade,
          comparar: v.comparar,
          comentarios: v.comentarios || null,
        },
      },
      {
        onSuccess: (r) => {
          toast.success("Configuração salva.");
          onSalvo(r);
        },
        onError: (e) => toast.error(mensagemDeErro(e)),
      },
    );

  const gerarPdf = () => {
    if (!relatorio) return;
    if (formState.isDirty) {
      toast.warning("Salve as alterações antes de gerar o PDF.");
      return;
    }
    // A mesma chave é reutilizada até a solicitação ser aceita: repetir após falha de rede
    // (ou clique duplo) devolve a mesma execução em vez de gerar outro PDF.
    gerar.mutate(
      { id: relatorio.id, chave },
      {
        onSuccess: () => {
          setChave(crypto.randomUUID());
          toast.success("Geração do PDF iniciada. Acompanhe em Execuções.");
        },
        onError: (e) => toast.error(mensagemDeErro(e)),
      },
    );
  };

  const toggle = <T extends string>(lista: T[] | undefined, item: T, on: boolean) =>
    on ? [...new Set([...(lista ?? []), item])] : (lista ?? []).filter((x) => x !== item);

  return (
    <div className="grid gap-4 xl:grid-cols-[26rem_minmax(0,1fr)]">
      <Card>
        <CardHeader>
          <CardTitle>{relatorio ? "Editar relatório" : "Novo relatório"}</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4" onSubmit={handleSubmit(enviar)} noValidate>
            <fieldset disabled={!podeEditar} className="grid gap-4">
              <Field id="r-cliente" label="Cliente" error={formState.errors.cliente_id}>
                {(a) => (
                  <Controller
                    control={control}
                    name="cliente_id"
                    render={({ field }) => (
                      <Select value={field.value || undefined} onValueChange={field.onChange} disabled={!!relatorio || !podeEditar}>
                        <SelectTrigger {...a}><SelectValue placeholder="Selecione" /></SelectTrigger>
                        <SelectContent>
                          {clientes.data?.items.map((c) => <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    )}
                  />
                )}
              </Field>
              <Field id="r-titulo" label="Título" error={formState.errors.titulo}>
                {(a) => <Input {...a} {...register("titulo")} maxLength={180} />}
              </Field>
              <Field id="r-template" label="Template">
                {(a) => (
                  <Controller control={control} name="template" render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger {...a}><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(TEMPLATES).map(([k, l]) => <SelectItem key={k} value={k}>{l}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  )} />
                )}
              </Field>
              <Field id="r-periodo" label="Período">
                {(a) => (
                  <Controller control={control} name="periodo_tipo" render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger {...a}><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(PERIODOS).map(([k, l]) => <SelectItem key={k} value={k}>{l}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  )} />
                )}
              </Field>
              {valores.periodo_tipo === "personalizado" && (
                <div className="grid grid-cols-2 gap-3">
                  <Field id="r-inicio" label="Início" error={formState.errors.inicio}>{(a) => <Input type="date" {...a} {...register("inicio")} />}</Field>
                  <Field id="r-fim" label="Fim" error={formState.errors.fim}>{(a) => <Input type="date" {...a} {...register("fim")} />}</Field>
                </div>
              )}
              <fieldset className="grid gap-2">
                <legend className="mb-1 text-sm font-medium">Fontes</legend>
                <Controller control={control} name="plataformas" render={({ field }) => (
                  <div className="flex flex-wrap gap-4">
                    {(["meta_ads", "google_ads"] as const).map((p) => (
                      <Label key={p} className="font-normal">
                        <Checkbox checked={field.value.includes(p)} onCheckedChange={(v) => field.onChange(toggle(field.value, p, v === true))} />
                        {PLATAFORMA_LABEL[p]}
                      </Label>
                    ))}
                  </div>
                )} />
                <p className="text-xs text-muted-foreground">Nenhuma marcada = todas as fontes conectadas.</p>
              </fieldset>
              <fieldset className="grid gap-2">
                <legend className="mb-1 text-sm font-medium">KPIs</legend>
                <Controller control={control} name="kpis" render={({ field }) => (
                  <div className="grid grid-cols-2 gap-2">
                    {KPIS.map((k) => (
                      <Label key={k} className="font-normal">
                        <Checkbox checked={field.value.includes(k)} onCheckedChange={(v) => field.onChange(toggle(field.value, k, v === true))} />
                        {KPI_LABEL[k]}
                      </Label>
                    ))}
                  </div>
                )} />
                {formState.errors.kpis && <p role="alert" className="text-xs text-destructive">{formState.errors.kpis.message}</p>}
              </fieldset>
              <fieldset className="grid gap-2">
                <legend className="mb-1 text-sm font-medium">Gráficos e tabelas</legend>
                <Controller control={control} name="graficos" render={({ field }) => (
                  <div className="grid gap-2">
                    {GRAFICOS.map((g) => (
                      <Label key={g} className="font-normal">
                        <Checkbox checked={field.value.includes(g)} onCheckedChange={(v) => field.onChange(toggle(field.value, g, v === true))} />
                        {GRAFICO_LABEL[g]}
                      </Label>
                    ))}
                  </div>
                )} />
              </fieldset>
              <div className="grid grid-cols-2 gap-3">
                <Field id="r-gran" label="Granularidade">
                  {(a) => (
                    <Controller control={control} name="granularidade" render={({ field }) => (
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger {...a}><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="dia">Diária</SelectItem>
                          <SelectItem value="semana">Semanal</SelectItem>
                          <SelectItem value="mes">Mensal</SelectItem>
                        </SelectContent>
                      </Select>
                    )} />
                  )}
                </Field>
                <Controller control={control} name="comparar" render={({ field }) => (
                  <Label className="mt-6 font-normal">
                    <Checkbox checked={field.value} onCheckedChange={(v) => field.onChange(v === true)} />
                    Comparar com anterior
                  </Label>
                )} />
              </div>
              <Field id="r-coment" label="Comentários" error={formState.errors.comentarios}>
                {(a) => <Textarea rows={5} maxLength={5000} {...a} {...register("comentarios")} />}
              </Field>
            </fieldset>
            {podeEditar && (
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={salvar.isPending}><SaveIcon /> Salvar configuração</Button>
                {relatorio && (
                  <Button type="button" variant="outline" onClick={gerarPdf} disabled={gerar.isPending}>
                    <FileDownIcon /> Gerar PDF
                  </Button>
                )}
              </div>
            )}
          </form>
        </CardContent>
      </Card>
      <div className="grid content-start gap-4">
        <PreviewRelatorio
          clienteId={valores.cliente_id || undefined}
          titulo={valores.titulo || "Relatório"}
          template={valores.template ?? "visao_executiva"}
          periodo={periodo}
          plataformas={valores.plataformas ?? []}
          kpis={(valores.kpis ?? []) as (typeof KPIS)[number][]}
          graficos={(valores.graficos ?? []) as (typeof GRAFICOS)[number][]}
          granularidade={valores.granularidade ?? "dia"}
          comparar={valores.comparar ?? true}
          comentarios={valores.comentarios}
        />
        {relatorio && <Execucoes relatorioId={relatorio.id} />}
      </div>
    </div>
  );
}

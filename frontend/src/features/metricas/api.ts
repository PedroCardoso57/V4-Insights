"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { isoHoje, type Plataforma } from "@/lib/format";
import { lerPreferencias } from "@/lib/preferencias";
import { api, unwrap } from "@/services/api/client";

export type Granularidade = "dia" | "semana" | "mes";

export interface Filtros {
  inicio: string;
  fim: string;
  plataforma: Plataforma | "";
  conta_anuncio_id: string;
  campanha_id: string;
  granularidade: Granularidade;
  comparar: boolean;
}

export const filtrosPadrao = (): Filtros => {
  const pref = lerPreferencias();
  return {
    inicio: isoHoje(-(pref.periodoDias - 1)),
    fim: isoHoje(0),
    plataforma: "",
    conta_anuncio_id: "",
    campanha_id: "",
    granularidade: pref.granularidade,
    comparar: pref.comparar,
  };
};

function query(f: Filtros) {
  return {
    inicio: f.inicio,
    fim: f.fim,
    plataforma: f.plataforma || undefined,
    conta_anuncio_id: f.conta_anuncio_id || undefined,
    campanha_id: f.campanha_id || undefined,
  };
}

function buscarCampanhas(clienteId: string, f: Filtros) {
  return unwrap(api.GET("/api/v1/clientes/{cliente_id}/campanhas", { params: { path: { cliente_id: clienteId }, query: query(f) } }));
}

/** Campanhas do período sem filtro de campanha (opções do seletor; compartilha cache). */
export function useOpcoesCampanha(clienteId: string | undefined, f: Filtros) {
  const semCampanha = { ...f, campanha_id: "" };
  return useQuery({
    queryKey: ["metricas", clienteId, "campanhas", semCampanha],
    queryFn: () => buscarCampanhas(clienteId!, semCampanha),
    enabled: !!clienteId,
    select: (d) => d.items.map((c) => ({ id: c.campanha_externa_id, nome: c.campanha_nome ?? c.campanha_externa_id })),
  });
}

/** Resumo, série e campanhas com OS MESMOS filtros: todos os gráficos mudam juntos. */
export function useMetricas(clienteId: string | undefined, f: Filtros) {
  const enabled = !!clienteId;
  const path = { cliente_id: clienteId ?? "" };
  const base = query(f);
  const resumo = useQuery({
    queryKey: ["metricas", clienteId, "resumo", f],
    queryFn: () =>
      unwrap(api.GET("/api/v1/clientes/{cliente_id}/metricas/resumo", { params: { path, query: { ...base, comparar: f.comparar } } })),
    enabled,
    placeholderData: keepPreviousData,
  });
  const serie = useQuery({
    queryKey: ["metricas", clienteId, "serie", f],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/clientes/{cliente_id}/metricas/serie", {
          params: { path, query: { ...base, granularidade: f.granularidade, comparar: f.comparar } },
        }),
      ),
    enabled,
    placeholderData: keepPreviousData,
  });
  const campanhas = useQuery({
    queryKey: ["metricas", clienteId, "campanhas", f],
    queryFn: () => buscarCampanhas(clienteId!, f),
    enabled,
    placeholderData: keepPreviousData,
  });
  return { resumo, serie, campanhas };
}

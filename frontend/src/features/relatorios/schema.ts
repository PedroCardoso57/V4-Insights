import { z } from "zod";

import { PLATAFORMAS } from "@/lib/format";

export const KPIS = ["investimento", "impressoes", "cliques", "ctr", "cpc", "cpm", "conversoes", "valor_conversoes", "cpa", "roas"] as const;
export const GRAFICOS = ["serie_investimento", "serie_cliques", "serie_conversoes", "tabela_campanhas"] as const;
export const GRAFICO_LABEL: Record<(typeof GRAFICOS)[number], string> = {
  serie_investimento: "Série de investimento",
  serie_cliques: "Série de cliques",
  serie_conversoes: "Série de conversões",
  tabela_campanhas: "Tabela de campanhas",
};
export const TEMPLATES = { visao_executiva: "Visão Executiva", performance_campanhas: "Performance de Campanhas" } as const;
export const PERIODOS = {
  ultimos_7_dias: "Últimos 7 dias",
  ultimos_30_dias: "Últimos 30 dias",
  mes_atual: "Mês atual",
  mes_anterior: "Mês anterior",
  personalizado: "Personalizado",
} as const;

/** Espelha ConfiguracaoRelatorio do backend; a API revalida tudo. */
export const relatorioSchema = z
  .object({
    cliente_id: z.string().uuid({ message: "Selecione o cliente" }),
    titulo: z.string().trim().min(2, "Informe um título (mínimo 2 caracteres)").max(180),
    template: z.enum(["visao_executiva", "performance_campanhas"]),
    periodo_tipo: z.enum(["ultimos_7_dias", "ultimos_30_dias", "mes_atual", "mes_anterior", "personalizado"]),
    inicio: z.string().optional(),
    fim: z.string().optional(),
    plataformas: z.array(z.enum(PLATAFORMAS)),
    kpis: z.array(z.enum(KPIS)).min(1, "Selecione ao menos um KPI"),
    graficos: z.array(z.enum(GRAFICOS)),
    granularidade: z.enum(["dia", "semana", "mes"]),
    comparar: z.boolean(),
    comentarios: z.string().max(5000).optional(),
  })
  .superRefine((v, ctx) => {
    if (v.periodo_tipo !== "personalizado") return;
    if (!v.inicio) ctx.addIssue({ code: "custom", path: ["inicio"], message: "Informe o início" });
    if (!v.fim) ctx.addIssue({ code: "custom", path: ["fim"], message: "Informe o fim" });
    if (v.inicio && v.fim && v.inicio > v.fim) ctx.addIssue({ code: "custom", path: ["fim"], message: "Fim deve ser após o início" });
  });

export type RelatorioForm = z.infer<typeof relatorioSchema>;

/** Resolve o período como o backend (services/relatorios.resolver_periodo). */
export function resolverPeriodo(tipo: RelatorioForm["periodo_tipo"], inicio: string | undefined, fim: string | undefined, hoje = new Date()) {
  const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  const dia = (n: number) => {
    const d = new Date(hoje);
    d.setDate(d.getDate() + n);
    return d;
  };
  switch (tipo) {
    case "personalizado":
      return { inicio: inicio ?? iso(hoje), fim: fim ?? iso(hoje) };
    case "ultimos_7_dias":
      return { inicio: iso(dia(-6)), fim: iso(hoje) };
    case "ultimos_30_dias":
      return { inicio: iso(dia(-29)), fim: iso(hoje) };
    case "mes_atual":
      return { inicio: iso(new Date(hoje.getFullYear(), hoje.getMonth(), 1)), fim: iso(hoje) };
    case "mes_anterior":
      return {
        inicio: iso(new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1)),
        fim: iso(new Date(hoje.getFullYear(), hoje.getMonth(), 0)),
      };
  }
}

import { describe, expect, it } from "vitest";

import { relatorioSchema, resolverPeriodo } from "@/features/relatorios/schema";

const base = {
  cliente_id: "6f1c1c3e-1111-4a4a-8a8a-123456789abc",
  titulo: "Mensal",
  template: "visao_executiva" as const,
  periodo_tipo: "ultimos_30_dias" as const,
  plataformas: [],
  kpis: ["investimento" as const],
  graficos: [],
  granularidade: "dia" as const,
  comparar: true,
};

describe("relatório", () => {
  it("valida período personalizado", () => {
    expect(relatorioSchema.safeParse(base).success).toBe(true);
    const r = relatorioSchema.safeParse({ ...base, periodo_tipo: "personalizado", inicio: "2026-02-10", fim: "2026-02-01" });
    expect(r.success).toBe(false);
    expect(relatorioSchema.safeParse({ ...base, kpis: [] }).success).toBe(false);
  });
  it("resolve períodos como o backend", () => {
    const hoje = new Date(2026, 2, 15);
    expect(resolverPeriodo("ultimos_7_dias", undefined, undefined, hoje)).toEqual({ inicio: "2026-03-09", fim: "2026-03-15" });
    expect(resolverPeriodo("mes_anterior", undefined, undefined, hoje)).toEqual({ inicio: "2026-02-01", fim: "2026-02-28" });
    expect(resolverPeriodo("mes_atual", undefined, undefined, hoje)).toEqual({ inicio: "2026-03-01", fim: "2026-03-15" });
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ErroEstado } from "@/components/estado";
import { CampanhasTable, ordenarCampanhas } from "@/features/metricas/campanhas-table";
import { KpiCard } from "@/features/metricas/kpis";
import { ApiError, type Schemas } from "@/services/api/client";

const vazio = { investimento: null, impressoes: null, cliques: null, conversoes: null, valor_conversoes: null, ctr: null, cpc: null, cpm: null, cpa: null, roas: null };

function resumo(p: Partial<Schemas["ResumoOut"]> = {}): Schemas["ResumoOut"] {
  return {
    periodo: { inicio: "2026-03-01", fim: "2026-03-08" },
    periodo_anterior: { inicio: "2026-02-21", fim: "2026-02-28" },
    atual: { ...vazio, investimento: "300.00", cpc: "1.0000" },
    anterior: null,
    variacao_percentual: { ...vazio },
    moedas: ["BRL"],
    ultima_sincronizacao_em: null,
    integracoes_conectadas: 1,
    nivel: "campanha",
    ...p,
  };
}

describe("KpiCard", () => {
  it("sem base de comparação não exibe variação", () => {
    render(<KpiCard resumo={resumo()} kpi="investimento" />);
    expect(screen.getByText("sem base de comparação")).toBeInTheDocument();
  });
  it("aumento de custo é desfavorável", () => {
    render(<KpiCard resumo={resumo({ variacao_percentual: { ...vazio, cpc: "25.00" } })} kpi="cpc" />);
    expect(screen.getByText("(desfavorável)")).toBeInTheDocument();
  });
});

describe("campanhas", () => {
  const c = (id: string, inv: string | null): Schemas["CampanhaOut"] => ({
    plataforma: "meta_ads", conta_anuncio_id: "x", campanha_externa_id: id, campanha_nome: `Camp ${id}`, kpis: { ...vazio, investimento: inv },
  });
  it("ordena com ausentes no final", () => {
    expect(ordenarCampanhas([c("a", "1"), c("b", null), c("c", "9")], "investimento", false).map((x) => x.campanha_externa_id)).toEqual(["c", "a", "b"]);
  });
  it("estado vazio", () => {
    render(<CampanhasTable campanhas={[]} />);
    expect(screen.getByText("Nenhuma campanha no período.")).toBeInTheDocument();
  });
});

describe("ErroEstado", () => {
  it("mostra mensagem útil e código de correlação", () => {
    render(<ErroEstado erro={new ApiError(403, "FORBIDDEN", "Acesso não autorizado", "req-123")} />);
    expect(screen.getByText("Acesso não autorizado")).toBeInTheDocument();
    expect(screen.getByText("req-123")).toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Resumo } from "../api/types";
import App from "../App";
import { CampanhasTable, KpiCard } from "../components/Metricas";
import { AuthProvider } from "../lib/auth";

const kpisVazios = {
  investimento: null, impressoes: null, cliques: null, conversoes: null, valor_conversoes: null,
  ctr: null, cpc: null, cpm: null, cpa: null, roas: null,
};

function resumo(parcial: Partial<Resumo>): Resumo {
  return {
    periodo: { inicio: "2026-03-01", fim: "2026-03-08" },
    periodo_anterior: { inicio: "2026-02-21", fim: "2026-02-28" },
    atual: { ...kpisVazios, investimento: "300.00", cpc: "1.0000" },
    anterior: null,
    variacao_percentual: { ...kpisVazios },
    moedas: ["BRL"],
    ultima_sincronizacao_em: null,
    integracoes_conectadas: 1,
    nivel: "campanha",
    ...parcial,
  };
}

afterEach(() => vi.restoreAllMocks());

describe("KpiCard", () => {
  it("não exibe variação quando não há base de comparação", () => {
    render(<KpiCard resumo={resumo({})} kpi="investimento" />);
    expect(screen.getByText("sem base de comparação")).toBeInTheDocument();
  });

  it("variação positiva de custo é sinalizada como negativa", () => {
    const r = resumo({ variacao_percentual: { ...kpisVazios, cpc: "25.00" } });
    render(<KpiCard resumo={r} kpi="cpc" />);
    const el = screen.getByText("+25,00%");
    expect(el).toHaveClass("neg");
  });
});

describe("CampanhasTable", () => {
  it("mostra estado vazio", () => {
    render(<CampanhasTable campanhas={[]} />);
    expect(screen.getByText("Nenhuma campanha no período.")).toBeInTheDocument();
  });
});

describe("App", () => {
  it("exibe a tela de login quando não há sessão", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Sessão inválida" }), { status: 401 }),
    );
    render(
      <MemoryRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByText("Entrar com Google")).toHaveAttribute(
      "href",
      "/api/auth/google/login",
    );
  });

  it("esconde menu de usuários para visualizador", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
      const u = String(url);
      if (u.endsWith("/auth/me")) {
        return new Response(
          JSON.stringify({ id: "1", nome: "Vera", email: "v@v4.com", papel: "visualizador", csrf_token: "x" }),
        );
      }
      return new Response(JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 }));
    });
    render(
      <MemoryRouter initialEntries={["/clientes"]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByText("Nenhum cliente encontrado na sua carteira.")).toBeInTheDocument();
    expect(screen.queryByText("Usuários")).not.toBeInTheDocument();
    expect(screen.queryByText("Novo cliente")).not.toBeInTheDocument();
  });
});

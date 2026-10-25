import { describe, expect, it } from "vitest";

import { fmtKpi, fmtMoeda, horasDesde } from "@/lib/format";

describe("formatação de KPIs", () => {
  it("mostra traço para valores ausentes (divisão por zero no backend)", () => {
    expect(fmtKpi("cpc", null)).toBe("—");
    expect(fmtKpi("roas", undefined)).toBe("—");
  });
  it("formata moeda, percentual e ROAS em pt-BR", () => {
    expect(fmtMoeda("1234.5").replace(/\s/g, " ")).toBe("R$ 1.234,50");
    expect(fmtKpi("ctr", "2.5")).toBe("2,50%");
    expect(fmtKpi("roas", "4")).toBe("4,00x");
    expect(fmtKpi("impressoes", 15000)).toBe("15.000");
  });
  it("calcula horas desde a última sincronização", () => {
    const agora = Date.parse("2026-03-02T12:00:00Z");
    expect(horasDesde("2026-03-02T06:00:00Z", agora)).toBe(6);
    expect(horasDesde(null, agora)).toBeNull();
  });
});

import type { Schemas } from "@/services/api/client";

export type KpiKey = keyof Schemas["Kpis"];
export type Papel = Schemas["Papel"];
export type Plataforma = Schemas["Plataforma"];

const AUSENTE = "—";

export function fmtMoeda(v: string | number | null | undefined, moeda = "BRL"): string {
  if (v === null || v === undefined) return AUSENTE;
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: moeda }).format(Number(v));
}

export function fmtNumero(v: string | number | null | undefined, casas = 0): string {
  if (v === null || v === undefined) return AUSENTE;
  return new Intl.NumberFormat("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas }).format(Number(v));
}

export function fmtPercent(v: string | number | null | undefined, casas = 2): string {
  if (v === null || v === undefined) return AUSENTE;
  return `${fmtNumero(v, casas)}%`;
}

export function fmtData(iso: string | null | undefined): string {
  if (!iso) return AUSENTE;
  const d = iso.length === 10 ? new Date(`${iso}T00:00:00`) : new Date(iso);
  return d.toLocaleDateString("pt-BR");
}

export function fmtDataHora(iso: string | null | undefined): string {
  if (!iso) return AUSENTE;
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export const KPI_LABEL: Record<KpiKey, string> = {
  investimento: "Investimento",
  impressoes: "Impressões",
  cliques: "Cliques",
  conversoes: "Conversões",
  valor_conversoes: "Valor de conversões",
  ctr: "CTR",
  cpc: "CPC",
  cpm: "CPM",
  cpa: "Custo por conversão",
  roas: "ROAS",
};

/** KPIs de custo: variação positiva é desfavorável. */
export const KPI_CUSTO: KpiKey[] = ["cpc", "cpm", "cpa"];

export function fmtKpi(k: KpiKey, v: string | number | null | undefined, moeda = "BRL"): string {
  switch (k) {
    case "investimento":
    case "valor_conversoes":
    case "cpc":
    case "cpm":
    case "cpa":
      return fmtMoeda(v, moeda);
    case "ctr":
      return fmtPercent(v);
    case "roas":
      return v === null || v === undefined ? AUSENTE : `${fmtNumero(v, 2)}x`;
    case "conversoes":
      return fmtNumero(v, 2);
    default:
      return fmtNumero(v);
  }
}

export const PAPEL_LABEL: Record<Papel, string> = {
  admin: "Administrador",
  gestor: "Gestor",
  analista: "Analista",
  visualizador: "Visualizador",
};

export const PLATAFORMA_LABEL: Record<Plataforma, string> = {
  meta_ads: "Meta Ads",
  google_ads: "Google Ads",
  linkedin_ads: "LinkedIn Ads",
  tiktok_ads: "TikTok Ads",
};

/** Ordem de exibição das plataformas de mídia em filtros, conectores e relatórios. */
export const PLATAFORMAS = ["meta_ads", "google_ads", "linkedin_ads", "tiktok_ads"] as const satisfies readonly Plataforma[];

export function isoHoje(offsetDias = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDias);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

/** Horas desde a última sincronização (null se nunca sincronizou). */
export function horasDesde(iso: string | null | undefined, agora = Date.now()): number | null {
  if (!iso) return null;
  return (agora - new Date(iso).getTime()) / 3.6e6;
}

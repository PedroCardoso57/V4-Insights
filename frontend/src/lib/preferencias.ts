/** Preferências internas do usuário neste navegador (conveniência, não dados de negócio). */
export interface Preferencias {
  periodoDias: 7 | 30 | 90;
  granularidade: "dia" | "semana" | "mes";
  comparar: boolean;
}

const KEY = "v4:preferencias";
export const PREFERENCIAS_PADRAO: Preferencias = { periodoDias: 30, granularidade: "dia", comparar: true };

export const PREFERENCIAS_KEY = KEY;

export function parsePreferencias(raw: string | null): Preferencias {
  try {
    return raw ? { ...PREFERENCIAS_PADRAO, ...(JSON.parse(raw) as Partial<Preferencias>) } : PREFERENCIAS_PADRAO;
  } catch {
    return PREFERENCIAS_PADRAO;
  }
}

export function lerPreferencias(): Preferencias {
  try {
    return parsePreferencias(typeof localStorage !== "undefined" ? localStorage.getItem(KEY) : null);
  } catch {
    return PREFERENCIAS_PADRAO;
  }
}

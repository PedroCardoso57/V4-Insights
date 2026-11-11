/** Dados das páginas públicas de privacidade, termos e exclusão de dados (M02).
 *  As plataformas de anúncio (Meta, Google, TikTok, LinkedIn) exigem essas URLs públicas no
 *  cadastro do app. Ao mudar o texto, atualize a data de revisão. */
export const LEGAL = {
  controlador: "V4 Bounnacorso",
  produto: "V4 Insights",
  site: "https://cardosodev.tech",
  contato: "admin@cardosodev.tech",
  revisadoEm: "11/11/2026",
  prazoRespostaDias: 15,
} as const;

export const PAGINAS_LEGAIS = [
  { href: "/privacidade", titulo: "Política de privacidade" },
  { href: "/termos", titulo: "Termos de uso" },
  { href: "/exclusao-de-dados", titulo: "Exclusão de dados" },
] as const;

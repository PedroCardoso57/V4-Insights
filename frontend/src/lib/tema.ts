export type Tema = "claro" | "escuro";

export const CHAVE_TEMA = "v4-tema";

/** Executado antes da hidratação para aplicar o tema salvo sem "piscar" o claro. */
export const SCRIPT_TEMA = `try{var t=localStorage.getItem("${CHAVE_TEMA}");if(t==="escuro"||(!t&&matchMedia("(prefers-color-scheme: dark)").matches))document.documentElement.classList.add("dark")}catch(e){}`;

export function temaAtual(): Tema {
  return document.documentElement.classList.contains("dark") ? "escuro" : "claro";
}

export function aplicarTema(tema: Tema) {
  document.documentElement.classList.toggle("dark", tema === "escuro");
  try {
    localStorage.setItem(CHAVE_TEMA, tema);
  } catch {
    // armazenamento indisponível (modo privado): o tema vale só nesta página
  }
}

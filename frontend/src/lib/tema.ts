export type Tema = "claro" | "escuro";

export const CHAVE_TEMA = "v4-tema";

/** Executado antes da hidratação para aplicar o tema salvo sem "piscar".
 *  Padrão: escuro, como a identidade visual da V4; o claro fica como opção salva. */
export const SCRIPT_TEMA = `try{if(localStorage.getItem("${CHAVE_TEMA}")!=="claro")document.documentElement.classList.add("dark")}catch(e){document.documentElement.classList.add("dark")}`;

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

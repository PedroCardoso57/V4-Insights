export type Tema = "claro" | "escuro";

export const CHAVE_TEMA = "v4-tema";

/** Executado antes da hidratação para aplicar o tema salvo sem "piscar".
 *  Padrão: claro; o escuro vale só para quem escolheu em Configurações. */
export const SCRIPT_TEMA = `try{if(localStorage.getItem("${CHAVE_TEMA}")==="escuro")document.documentElement.classList.add("dark")}catch(e){}`;

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

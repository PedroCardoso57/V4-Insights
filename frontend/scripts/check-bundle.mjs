// SPEC-06: nenhuma credencial pode aparecer no bundle enviado ao navegador.
// Varre .next/static (JS/CSS públicos) atrás de nomes de segredos e formatos de token.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const RAIZ = new URL("../.next/static", import.meta.url).pathname;
const PROIBIDOS = [
  /ENCRYPTION_KEY/,
  /CLIENT_SECRET/i,
  /DEVELOPER_TOKEN/i,
  /META_APP_SECRET/,
  /DATABASE_URL/,
  /postgres(ql)?(\+psycopg)?:\/\//,
  /\bya29\.[A-Za-z0-9_-]{20,}/, // access token Google
  /\b1\/\/0[A-Za-z0-9_-]{20,}/, // refresh token Google
  /\bEAA[A-Za-z0-9]{30,}/, // token Meta
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
];

function* arquivos(dir) {
  for (const nome of readdirSync(dir)) {
    const p = join(dir, nome);
    if (statSync(p).isDirectory()) yield* arquivos(p);
    else if (/\.(js|css|map|json|txt)$/.test(nome)) yield p;
  }
}

let falhas = 0;
let total = 0;
for (const arq of arquivos(RAIZ)) {
  total++;
  const conteudo = readFileSync(arq, "utf8");
  for (const re of PROIBIDOS) {
    if (re.test(conteudo)) {
      console.error(`✗ ${arq.replace(RAIZ, ".next/static")}: padrão proibido ${re}`);
      falhas++;
    }
  }
}
if (!total) {
  console.error("Nenhum arquivo em .next/static — rode `npm run build` antes.");
  process.exit(2);
}
console.log(falhas ? `${falhas} ocorrência(s) suspeita(s) em ${total} arquivos.` : `✓ ${total} arquivos verificados, nenhuma credencial no bundle.`);
process.exit(falhas ? 1 : 0);

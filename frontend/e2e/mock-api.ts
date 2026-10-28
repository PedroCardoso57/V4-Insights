import type { Page, Route } from "@playwright/test";

/** API simulada (contratos de /api/v1) com estado em memória por teste. */
type Papel = "admin" | "gestor" | "analista" | "visualizador";
type Obj = Record<string, unknown>;

const agoraIso = () => new Date().toISOString();
const uuid = () => crypto.randomUUID();
const kpisVazios = { investimento: null, impressoes: null, cliques: null, conversoes: null, valor_conversoes: null, ctr: null, cpc: null, cpm: null, cpa: null, roas: null };

export interface Estado {
  papel: Papel | null;
  clientes: Obj[];
  integracoes: Obj[];
  relatorios: Obj[];
  execucoes: Obj[];
  dashboards: Obj[];
  autorizacoes: string[];
  usuarios: Obj[];
  chaves: Record<string, string>;
  responsavel: boolean;
}

export function novoEstado(papel: Papel | null = "admin"): Estado {
  const cliente = { id: "11111111-1111-4111-8111-111111111111", nome: "Padaria Sol", nome_fantasia: "Sol", documento: null, status: "ativo", criado_em: agoraIso(), atualizado_em: agoraIso(), arquivado_em: null };
  return {
    papel,
    clientes: [cliente],
    integracoes: [
      {
        id: "22222222-2222-4222-8222-222222222222", cliente_id: cliente.id, plataforma: "meta_ads", status: "conectada", escopos: ["ads_read"],
        erro_sincronizacao: null, ultima_sincronizacao_em: agoraIso(), criado_em: agoraIso(), atualizado_em: agoraIso(), revogada_em: null,
        contas: [{ id: "33333333-3333-4333-8333-333333333333", conta_externa_id: "act1", nome: "Conta Meta", moeda: "BRL", fuso_horario: "America/Sao_Paulo",
          ativa: true, carga_historica_dias: 90, mapeamento_conversoes: { action_types: ["purchase"] }, ultima_sincronizacao_em: agoraIso(), dados_ate: null }],
      },
    ],
    relatorios: [],
    execucoes: [],
    dashboards: [],
    autorizacoes: [],
    usuarios: [
      { id: "u1", nome: "Ana Lima", email: "ana@v4.com", papel, ativo: true, vinculado_google: true, tem_senha: false, ultimo_login_em: agoraIso(), criado_em: agoraIso() },
      { id: "u2", nome: "Caio Reis", email: "caio@v4.com", papel: "analista", ativo: true, vinculado_google: false, tem_senha: true, ultimo_login_em: null, criado_em: agoraIso() },
    ],
    chaves: { google_oidc_client_id: "id-do-env", google_oidc_client_secret: "segredo-do-env" },
    responsavel: false,
  };
}

function kpis(plataforma: string | null) {
  // Valores distintos por plataforma para verificar que os filtros afetam todos os blocos.
  const meta = { investimento: "300.00", impressoes: 30000, cliques: 300, conversoes: "15.00", valor_conversoes: "600.00", ctr: "1.0000", cpc: "1.0000", cpm: "10.0000", cpa: "20.0000", roas: "2.0000" };
  const google = { investimento: "150.00", impressoes: 15000, cliques: 0, conversoes: null, valor_conversoes: null, ctr: "0.0000", cpc: null, cpm: "10.0000", cpa: null, roas: null };
  if (plataforma === "google_ads") return google;
  if (plataforma === "meta_ads") return meta;
  return { ...meta, investimento: "450.00", impressoes: 45000 };
}

const page1 = (items: unknown[]) => ({ items, page: 1, page_size: Math.max(items.length, 1), total: items.length });
const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({ status, contentType: "application/json", headers: { "x-request-id": "e2e-req-1" }, body: JSON.stringify(body) });
const erro = (route: Route, status: number, code: string, message: string) =>
  json(route, { error: { code, message, request_id: "e2e-req-erro" } }, status);

export async function instalarApi(page: Page, st: Estado) {
  await page.route("**/health/ready", (r) => json(r, { status: "ok", checks: { database: "ok", redis: "ok" } }));
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const p = url.pathname.replace("/api/v1", "");
    const m = req.method();
    const body = (req.postDataJSON?.() ?? {}) as Obj;
    const seg = p.split("/").filter(Boolean);

    if (p === "/auth/me") {
      if (!st.papel) return erro(route, 401, "UNAUTHENTICATED", "Sessão inválida ou expirada");
      return json(route, { id: "u1", nome: "Ana Lima", email: "ana@v4.com", papel: st.papel, responsavel_chaves: st.responsavel });
    }
    if (p === "/auth/logout") return route.fulfill({ status: 204 });
    if (p === "/auth/login" && m === "POST") {
      // Credencial fixa do ambiente simulado; o backend real compara o hash Argon2id.
      if (body.email !== "ana@v4.com" || body.senha !== "senha-correta-123") {
        return erro(route, 401, "INVALID_CREDENTIALS", "E-mail ou senha inválidos.");
      }
      st.papel = "admin";
      return route.fulfill({ status: 204 });
    }
    if (st.papel === null) return erro(route, 401, "UNAUTHENTICATED", "Sessão inválida");

    // clientes
    if (p === "/clientes" && m === "GET") {
      const status = url.searchParams.get("status");
      const busca = (url.searchParams.get("search") ?? "").toLowerCase();
      return json(route, page1(st.clientes.filter((c) => (!status || c.status === status) && String(c.nome).toLowerCase().includes(busca))));
    }
    if (p === "/clientes" && m === "POST") {
      if (st.papel !== "admin" && st.papel !== "gestor") return erro(route, 403, "FORBIDDEN", "Permissão insuficiente");
      const c = { id: uuid(), nome: body.nome, nome_fantasia: body.nome_fantasia ?? null, documento: body.documento ? String(body.documento).replace(/\D/g, "") : null, status: "ativo", criado_em: agoraIso(), atualizado_em: agoraIso(), arquivado_em: null };
      st.clientes.push(c);
      return json(route, c, 201);
    }
    if (seg[0] === "clientes" && seg[1]) {
      const c = st.clientes.find((x) => x.id === seg[1]);
      if (!c) return erro(route, 404, "NOT_FOUND", "Cliente não encontrado");
      if (seg.length === 2 && m === "GET") return json(route, c);
      if (seg.length === 2 && m === "PATCH") return json(route, Object.assign(c, body, { atualizado_em: agoraIso() }));
      if (seg.length === 2 && m === "DELETE") {
        if (st.papel !== "admin") return erro(route, 403, "FORBIDDEN", "Permissão insuficiente");
        st.clientes = st.clientes.filter((x) => x !== c);
        return route.fulfill({ status: 204 });
      }
      if (seg[2] === "arquivar") return json(route, Object.assign(c, { status: "arquivado", arquivado_em: agoraIso() }));
      if (seg[2] === "usuarios") return json(route, page1([{ id: "u1", nome: "Ana Lima", email: "ana@v4.com", papel: "analista", ativo: true, atribuido_em: agoraIso() }]));
      const plat = url.searchParams.get("plataforma");
      if (seg[2] === "metricas" && seg[3] === "resumo") {
        return json(route, {
          periodo: { inicio: url.searchParams.get("inicio"), fim: url.searchParams.get("fim") },
          periodo_anterior: { inicio: "2026-01-01", fim: "2026-01-30" },
          atual: kpis(plat), anterior: null, variacao_percentual: kpisVazios, moedas: ["BRL"],
          ultima_sincronizacao_em: agoraIso(), integracoes_conectadas: 1, nivel: "campanha",
        });
      }
      if (seg[2] === "metricas" && seg[3] === "serie") {
        const k = kpis(plat);
        return json(route, { granularidade: "dia", pontos: [{ periodo: "2026-02-01", kpis: k }, { periodo: "2026-02-02", kpis: k }], comparacao: null });
      }
      if (seg[2] === "campanhas") {
        const itens = [
          { plataforma: "meta_ads", conta_anuncio_id: "c1", campanha_externa_id: "m1", campanha_nome: "Campanha Meta", kpis: kpis("meta_ads") },
          { plataforma: "google_ads", conta_anuncio_id: "c2", campanha_externa_id: "g1", campanha_nome: "Campanha Google", kpis: kpis("google_ads") },
        ].filter((x) => !plat || x.plataforma === plat);
        return json(route, page1(itens));
      }
    }
    // integrações
    if (p === "/integracoes" && m === "GET") {
      if (st.papel === "visualizador") return erro(route, 403, "FORBIDDEN", "Permissão insuficiente");
      const cid = url.searchParams.get("cliente_id");
      return json(route, page1(st.integracoes.filter((i) => !cid || i.cliente_id === cid)));
    }
    if (seg[0] === "integracoes" && seg[2] === "autorizar") {
      if (seg[1] === "google_ads" && !st.chaves.google_ads_client_id) {
        return erro(route, 503, "PROVIDER_NOT_CONFIGURED", "Google Ads não configurado: cadastre as chaves em Configurações");
      }
      st.autorizacoes.push(seg[1]!);
      return json(route, { authorization_url: `${url.origin}/provedor-falso?plataforma=${seg[1]}` });
    }
    if (seg[0] === "integracoes" && seg[2] === "jobs") return json(route, page1([]));
    if (seg[0] === "integracoes" && seg[2] === "sincronizar") return json(route, { job_id: uuid(), job_ids: [], status: "pendente", status_url: "/x" }, 202);
    // dashboards
    if (p === "/dashboards" && m === "GET") return json(route, page1(st.dashboards));
    // relatórios
    if (p === "/relatorios" && m === "GET") return json(route, page1(st.relatorios));
    if (p === "/relatorios" && m === "POST") {
      const r = { id: uuid(), cliente_id: body.cliente_id, criado_por: "u1", titulo: body.titulo, configuracao: body.configuracao, criado_em: agoraIso(), atualizado_em: agoraIso() };
      st.relatorios.push(r);
      return json(route, r, 201);
    }
    if (seg[0] === "relatorios" && seg[1] === "execucoes" && seg[3] === "download") {
      return route.fulfill({ status: 200, contentType: "application/pdf", headers: { "content-disposition": 'attachment; filename="relatorio.pdf"' }, body: "%PDF-1.4 e2e" });
    }
    if (seg[0] === "relatorios" && seg[1]) {
      const r = st.relatorios.find((x) => x.id === seg[1]);
      if (!r) return erro(route, 404, "NOT_FOUND", "Relatório não encontrado");
      if (seg.length === 2 && m === "GET") return json(route, r);
      if (seg.length === 2 && m === "PATCH") return json(route, Object.assign(r, body, { atualizado_em: agoraIso() }));
      if (seg[2] === "gerar") {
        const ex = { id: uuid(), relatorio_id: r.id, status: "pendente", progresso: 0, erro: null, tamanho_bytes: null, iniciado_em: agoraIso(), finalizado_em: null, expira_em: null, download_url: null,
          snapshot: { periodo: { inicio: "2026-02-01", fim: "2026-02-28" }, horario_corte: agoraIso(), filtros: {}, ultima_coleta_em: agoraIso() } };
        st.execucoes.push(ex);
        return json(route, { job_id: ex.id, job_ids: [ex.id], status: "pendente", status_url: `/api/v1/relatorios/${r.id}/execucoes` }, 202);
      }
      if (seg[2] === "execucoes") {
        const lista = st.execucoes.filter((e) => e.relatorio_id === r.id);
        const resp = page1(lista.map((e) => ({ ...e })));
        // O worker "conclui" a execução após a primeira consulta.
        lista.forEach((e) => Object.assign(e, { status: "concluido", progresso: 100, finalizado_em: agoraIso(), download_url: `/api/v1/relatorios/execucoes/${e.id}/download` }));
        return json(route, resp);
      }
    }
    // chaves das plataformas (Configurações, somente admin)
    if (p === "/configuracoes/chaves") {
      if (st.papel !== "admin" && st.papel !== "gestor") return erro(route, 403, "FORBIDDEN", "Permissão insuficiente");
      if (m === "PUT") {
        for (const [k, v] of Object.entries(body.valores as Record<string, string | null>)) {
          if (v) st.chaves[k] = v;
          else delete st.chaves[k];
        }
      }
      const grupo = (id: string, nome: string, campos: [string, string, boolean][]) => {
        const cs = campos.map(([chave, rotulo, secreto]) => ({
          chave, rotulo, secreto, obrigatorio: true,
          origem: st.chaves[chave] ? (st.chaves[chave].includes("do-env") ? "env" : "sistema") : null,
          valor: secreto ? null : (st.chaves[chave] ?? null),
        }));
        return { id, nome, redirect_uri: `https://insights.exemplo/api/v1/${id}/callback`, configurado: cs.every((c) => c.origem), campos: cs };
      };
      return json(route, [
        grupo("google_login", "Login com Google", [["google_oidc_client_id", "ID do cliente", false], ["google_oidc_client_secret", "Chave secreta do cliente", true]]),
        grupo("meta_ads", "Meta Ads", [["meta_app_id", "ID do app", false], ["meta_app_secret", "Chave secreta do app", true]]),
        grupo("google_ads", "Google Ads", [["google_ads_client_id", "ID do cliente OAuth", false], ["google_ads_client_secret", "Chave secreta do cliente", true]]),
      ]);
    }
    // usuários
    if (p === "/usuarios" && m === "GET") return json(route, page1(st.usuarios));
    if (p === "/usuarios" && m === "POST") {
      const u = { id: uuid(), nome: body.nome, email: String(body.email).toLowerCase(), papel: body.papel, ativo: true, vinculado_google: false, tem_senha: false, ultimo_login_em: null, criado_em: agoraIso() };
      st.usuarios.push(u);
      return json(route, u, 201);
    }
    if (seg[0] === "usuarios" && seg.length === 2) {
      const u = st.usuarios.find((x) => x.id === seg[1]);
      if (!u) return erro(route, 404, "NOT_FOUND", "Usuário não encontrado");
      if (m === "PATCH") return json(route, Object.assign(u, body));
      if (m === "DELETE") {
        if (u.id === "u1") return erro(route, 400, "BAD_REQUEST", "Não é possível excluir o próprio usuário");
        st.usuarios = st.usuarios.filter((x) => x !== u);
        return route.fulfill({ status: 204 });
      }
    }
    return erro(route, 404, "NOT_FOUND", `rota simulada ausente: ${m} ${p}`);
  });
  await page.route("**/provedor-falso**", (r) => r.fulfill({ contentType: "text/html", body: "<h1>Tela de consentimento do provedor</h1>" }));
}

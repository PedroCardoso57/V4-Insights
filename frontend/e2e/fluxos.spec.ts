import { expect, test } from "@playwright/test";

import { instalarApi, novoEstado } from "./mock-api";

const CLIENTE = "11111111-1111-4111-8111-111111111111";

test.describe("login", () => {
  test("sem sessão redireciona para /login com Entrar com Google @mobile", async ({ page }) => {
    await instalarApi(page, novoEstado(null));
    await page.goto("/clientes");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("link", { name: "Entrar com Google" })).toHaveAttribute("href", "/api/v1/auth/google/login");
  });

  test("e-mail e senha: valida, recusa credencial errada e entra com a correta", async ({ page }) => {
    await instalarApi(page, novoEstado(null));
    await page.goto("/login");
    await page.getByRole("button", { name: "Entrar na plataforma" }).click();
    await expect(page.getByText(/Informe um e-mail corporativo válido/)).toBeVisible();
    await page.getByLabel("E-mail corporativo").fill("ana@v4.com");
    await page.getByLabel("Senha de acesso").fill("errada");
    await page.getByRole("button", { name: "Entrar na plataforma" }).click();
    await expect(page.getByText("E-mail ou senha inválidos.")).toBeVisible();
    await page.getByLabel("Senha de acesso").fill("senha-correta-123");
    await page.getByRole("button", { name: "Entrar na plataforma" }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { name: "Visão geral da carteira" })).toBeVisible();
  });

  test("acesso negado exibe motivo", async ({ page }) => {
    await instalarApi(page, novoEstado(null));
    await page.goto("/login?erro=acesso_negado");
    await expect(page.getByText(/não está autorizada/)).toBeVisible();
  });
});

test("cliente: cadastro com validação, edição e arquivamento com confirmação", async ({ page }) => {
  await instalarApi(page, novoEstado("gestor"));
  await page.goto("/clientes");
  await page.getByRole("button", { name: "Novo cliente" }).click();
  const dialogo = page.getByRole("dialog");
  await dialogo.getByLabel("Nome *").fill("X");
  await dialogo.getByLabel("CPF/CNPJ").fill("123");
  await dialogo.getByRole("button", { name: "Salvar" }).click();
  await expect(dialogo.getByText("Informe o nome (mínimo 2 caracteres)")).toBeVisible();
  await expect(dialogo.getByText(/CPF \(11 dígitos\)/)).toBeVisible();
  await dialogo.getByLabel("Nome *").fill("Mercado Lua");
  await dialogo.getByLabel("CPF/CNPJ").fill("12.345.678/0001-90");
  await dialogo.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Mercado Lua" })).toBeVisible();
  await page.getByRole("button", { name: "Editar" }).click();
  await page.getByRole("dialog").getByLabel("Nome fantasia").fill("Lua");
  await page.getByRole("dialog").getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByText("Cliente atualizado.")).toBeVisible();
  await page.getByRole("button", { name: "Arquivar" }).click();
  await expect(page.getByRole("alertdialog")).toContainText("preservados");
  await page.getByRole("alertdialog").getByRole("button", { name: "Arquivar" }).click();
  await expect(page.getByText("arquivado", { exact: true })).toBeVisible();
});

test("cliente: admin exclui definitivamente com confirmação", async ({ page }) => {
  await instalarApi(page, novoEstado("admin"));
  await page.goto(`/clientes/${CLIENTE}`);
  await page.getByRole("button", { name: "Excluir" }).click();
  await expect(page.getByRole("alertdialog")).toContainText("não podem ser recuperados");
  await page.getByRole("alertdialog").getByRole("button", { name: "Excluir definitivamente" }).click();
  await expect(page.getByText("Cliente excluído.")).toBeVisible();
  await expect(page).toHaveURL(/\/clientes$/);
  await expect(page.getByRole("link", { name: "Padaria Sol" })).toHaveCount(0);
});

test("configurações: responsável cadastra as chaves de uma plataforma", async ({ page }) => {
  await instalarApi(page, { ...novoEstado("admin"), responsavel: true });
  await page.goto("/configuracoes");
  const meta = page.getByRole("form", { name: "Meta Ads" });
  await expect(meta.getByText("não configurado")).toBeVisible();
  await meta.getByLabel("ID do app").fill("123456");
  await meta.getByLabel("Chave secreta do app").fill("segredo-novo");
  await meta.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByText("Chaves de Meta Ads salvas.")).toBeVisible();
  await expect(meta.getByText("configurado", { exact: true })).toBeVisible();
  await expect(meta.getByLabel("Chave secreta do app")).toHaveValue("");
  await expect(page.getByRole("form", { name: "Login com Google" }).getByText("Vem do arquivo .env").first()).toBeVisible();
});

for (const papel of ["admin", "gestor"] as const) {
  test(`configurações: ${papel} que não é o responsável não vê as chaves`, async ({ page }) => {
    await instalarApi(page, novoEstado(papel));
    await page.goto("/configuracoes");
    await expect(page.getByRole("heading", { name: "Configurações" })).toBeVisible();
    await expect(page.getByText("Chaves das plataformas", { exact: true })).toHaveCount(0);
  });
}

test("conexão: plataforma sem chaves abre o cadastro e segue para o provedor", async ({ page }) => {
  const st = novoEstado("gestor");
  await instalarApi(page, st);
  await page.goto(`/clientes/${CLIENTE}?aba=integracoes`);
  await page.getByRole("button", { name: "Conectar Google Ads" }).click();
  const dialogo = page.getByRole("dialog");
  await expect(dialogo.getByRole("heading", { name: "Chaves do Google Ads" })).toBeVisible();
  await expect(dialogo.getByText("Endereço de retorno")).toHaveCount(0);
  await expect(dialogo.getByLabel("Chave secreta do cliente")).toHaveAttribute("autocomplete", "new-password");
  const semRolagem = await dialogo.evaluate((el) => el.scrollWidth <= el.clientWidth);
  expect(semRolagem).toBe(true);
  await dialogo.getByLabel("ID do cliente OAuth").fill("123.apps");
  await dialogo.getByLabel("Chave secreta do cliente").fill("segredo");
  await dialogo.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByRole("heading", { name: "Tela de consentimento do provedor" })).toBeVisible();
  expect(st.autorizacoes).toEqual(["google_ads"]);
  expect(st.chaves.google_ads_client_id).toBe("123.apps");
});

test("conexão: analista sem chaves recebe aviso para pedir ao administrador", async ({ page }) => {
  await instalarApi(page, novoEstado("analista"));
  await page.goto(`/clientes/${CLIENTE}?aba=integracoes`);
  await page.getByRole("button", { name: "Conectar Google Ads" }).click();
  await expect(page.getByText(/Peça a um administrador/)).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("usuários: cadastrar, editar e excluir com confirmação", async ({ page }) => {
  await instalarApi(page, novoEstado("admin"));
  await page.goto("/usuarios");
  await expect(page.getByRole("button", { name: "Excluir Ana Lima" })).toHaveCount(0); // não se exclui
  await page.getByRole("button", { name: "Novo usuário" }).click();
  const dialogo = page.getByRole("dialog");
  await dialogo.getByLabel("Nome").fill("Duda Melo");
  await dialogo.getByLabel("E-mail corporativo").fill("duda@v4.com");
  await dialogo.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByText("Usuário cadastrado.")).toBeVisible();
  await expect(page.getByRole("cell", { name: "duda@v4.com" })).toBeVisible();
  await page.getByRole("button", { name: "Editar Duda Melo" }).click();
  await page.getByRole("dialog").getByLabel("Nome").fill("Duda Melo Silva");
  await page.getByRole("dialog").getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByText("Usuário atualizado.")).toBeVisible();
  await page.getByRole("button", { name: "Excluir Caio Reis" }).click();
  await expect(page.getByRole("alertdialog")).toContainText("Não é possível desfazer");
  await page.getByRole("alertdialog").getByRole("button", { name: "Excluir" }).click();
  await expect(page.getByText("Usuário excluído.")).toBeVisible();
  await expect(page.getByRole("cell", { name: "caio@v4.com" })).toHaveCount(0);
});

test("conexão: iniciar autorização Meta leva ao provedor", async ({ page }) => {
  const st = novoEstado("analista");
  await instalarApi(page, st);
  await page.goto(`/clientes/${CLIENTE}?aba=integracoes`);
  await expect(page.getByText("Conta Meta")).toBeVisible();
  await page.getByRole("button", { name: "Conectar Meta Ads" }).click();
  await expect(page.getByRole("heading", { name: "Tela de consentimento do provedor" })).toBeVisible();
  expect(st.autorizacoes).toEqual(["meta_ads"]);
});

for (const [nome, plataforma] of [["LinkedIn Ads", "linkedin_ads"], ["TikTok Ads", "tiktok_ads"]] as const) {
  test(`conexão: iniciar autorização ${nome} leva ao provedor`, async ({ page }) => {
    const st = novoEstado("analista");
    await instalarApi(page, st);
    await page.goto(`/clientes/${CLIENTE}?aba=integracoes`);
    await page.getByRole("button", { name: `Conectar ${nome}` }).click();
    await expect(page.getByRole("heading", { name: "Tela de consentimento do provedor" })).toBeVisible();
    expect(st.autorizacoes).toEqual([plataforma]);
  });
}

test("dashboard: filtro de plataforma altera cards e tabela juntos", async ({ page }) => {
  await instalarApi(page, novoEstado("analista"));
  await page.goto(`/clientes/${CLIENTE}/dashboards`);
  const card = page.locator("[data-slot=card]", { hasText: "Investimento" }).first();
  await expect(card).toContainText("R$ 450,00");
  await expect(page.getByRole("cell", { name: "Campanha Google" })).toBeVisible();
  await page.getByRole("combobox", { name: "Plataforma" }).click();
  await page.getByRole("option", { name: "Meta Ads" }).click();
  await expect(card).toContainText("R$ 300,00");
  await expect(page.getByRole("cell", { name: "Campanha Google" })).toHaveCount(0);
  await expect(page.getByRole("cell", { name: "Campanha Meta" })).toBeVisible();
  await expect(page.getByText(/Última sincronização/)).toBeVisible();
});

test("relatório: configurar, pré-visualizar, gerar PDF e baixar", async ({ page }) => {
  await instalarApi(page, novoEstado("analista"));
  await page.goto(`/relatorios?id=novo&cliente_id=${CLIENTE}`);
  await page.getByLabel("Título").fill("Fechamento mensal");
  await page.getByLabel("Comentários").fill("Ótimo mês para a campanha de pães.");
  await expect(page.getByLabel("Prévia do relatório")).toContainText("Fechamento mensal");
  await expect(page.getByLabel("Prévia do relatório")).toContainText("Ótimo mês");
  await page.getByRole("button", { name: "Salvar configuração" }).click();
  await expect(page).toHaveURL(/relatorios\?id=[0-9a-f-]{36}/);
  await page.getByRole("button", { name: "Gerar PDF" }).click();
  await expect(page.getByText("Geração do PDF iniciada")).toBeVisible();
  const link = page.getByRole("link", { name: "PDF" });
  await expect(link).toBeVisible({ timeout: 10_000 });
  const [download] = await Promise.all([page.waitForEvent("download"), link.click()]);
  expect(download.suggestedFilename()).toBe("relatorio.pdf");
});

test("visualizador não vê ações de edição", async ({ page }) => {
  await instalarApi(page, novoEstado("visualizador"));
  await page.goto("/clientes");
  await expect(page.getByRole("link", { name: "Padaria Sol" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Novo cliente" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Integrações" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Usuários" })).toHaveCount(0);
});

test("layout responsivo em 360px sem rolagem horizontal @mobile", async ({ page }) => {
  await instalarApi(page, novoEstado("admin"));
  await page.setViewportSize({ width: 360, height: 780 });
  await page.goto("/clientes");
  await expect(page.getByRole("button", { name: "Abrir menu" })).toBeVisible();
  const largura = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(largura).toBeLessThanOrEqual(360);
  await page.getByRole("button", { name: "Abrir menu" }).click();
  await page.getByRole("link", { name: "Relatórios" }).click();
  await expect(page.getByRole("heading", { name: "Relatórios" })).toBeVisible();
});

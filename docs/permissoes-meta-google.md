# Integrações Meta Ads, Google Ads, LinkedIn Ads e TikTok Ads — permissões, campos, quotas e riscos (V4-011)

> O acesso às APIs depende de revisão, escopos, quotas e políticas vigentes dos provedores.
> Este documento descreve o que o sistema usa; confirme os requisitos atuais nas páginas
> oficiais antes de solicitar aprovações. Não há scraping nem contorno de permissões.

## Meta Marketing API (Graph API)

| Item | Uso no V4 Insights |
|---|---|
| App | App do tipo *Business* no Meta for Developers, vinculado ao Business Manager da unidade. |
| Permissão | `ads_read` (somente leitura). Exige **App Review** e verificação da empresa para uso com contas de terceiros. |
| OAuth | Authorization Code com `state` de uso único vinculado a usuário + cliente; troca por token de longa duração (~60 dias). |
| Redirect URI | `${API_BASE_URL}/api/v1/integracoes/meta_ads/callback` |
| Descoberta de contas | `GET /me/adaccounts?fields=account_id,name,currency,timezone_name,account_status` |
| Métricas | `GET /act_{id}/insights` com `level=campaign` (conjunto/anúncio disponíveis), `time_increment=1`, campos `spend, impressions, clicks, actions, action_values`, `campaign_id/name`, `adset_id/name`. |
| Conversões | Somente as `action_types` mapeadas por conta (ex.: `purchase`, `lead`), com janela opcional (`7d_click`, `1d_view`…) via `action_attribution_windows`. Sem mapeamento, conversões/CPA/ROAS ficam ausentes. |
| Revogação | `DELETE /me/permissions` (best-effort) + remoção da credencial local. |
| Quotas | Limites por app/conta (códigos 4, 17, 32, 613, 80000–80014) → retry exponencial. |
| Erros de permissão | Código 190 (token inválido), 10/200–299 (permissão) → sem retry; integração vai para "requer reconexão". |

## Google Ads API

| Item | Uso no V4 Insights |
|---|---|
| Developer token | Nível *Basic* ou superior aprovado pelo Google (o nível *Test* só acessa contas de teste). |
| OAuth | Cliente OAuth **separado** do login interno, escopo `https://www.googleapis.com/auth/adwords`, `access_type=offline`, PKCE; refresh token guardado criptografado. |
| Redirect URI | `${API_BASE_URL}/api/v1/integracoes/google_ads/callback` |
| MCC | Se as contas estiverem sob uma conta gerenciadora, defina `GOOGLE_ADS_LOGIN_CUSTOMER_ID`. |
| Descoberta | `customers:listAccessibleCustomers` + `SELECT customer.* FROM customer` (contas MCC são ignoradas por não terem métricas próprias). |
| Métricas | `googleAds:searchStream` com GAQL em `campaign` (também `ad_group`/`ad_group_ad`): `segments.date, metrics.cost_micros, impressions, clicks, conversions, conversions_value, all_conversions, all_conversions_value`. |
| Conversões | Padrão: `conversions` (ações primárias configuradas na conta). Pode-se mapear `all_conversions`. |
| Quotas | Limites diários de operações por developer token; 429/`RESOURCE_EXHAUSTED` → retry exponencial. |
| Erros de permissão | 401/403 e `invalid_grant` no refresh → sem retry; requer reconexão. |

## LinkedIn Marketing API

| Item | Uso no V4 Insights |
|---|---|
| App | App no LinkedIn Developers vinculado a uma Company Page, com o produto **Advertising API** aprovado (acesso de desenvolvimento ou padrão). |
| Escopos | `r_ads` (contas) e `r_ads_reporting` (métricas), somente leitura. A conexão é recusada se algum não for concedido. |
| OAuth | Authorization Code com `state` de uso único; access token de ~60 dias. Refresh token (~1 ano) só para apps com refresh programático habilitado; sem ele, a integração pede reconexão ao expirar. |
| Redirect URI | `${API_BASE_URL}/api/v1/integracoes/linkedin_ads/callback` |
| Versão | Cabeçalho `LinkedIn-Version` configurável em `LINKEDIN_API_VERSION` (AAAAMM); o LinkedIn desativa versões com ~1 ano. |
| Descoberta | `GET /rest/adAccounts?q=search` (contas de teste são ignoradas). Fuso: UTC, como o `adAnalytics`. |
| Níveis | Grupo de campanhas → **campanha**; campanha → **conjunto**; criativo → **anúncio**. Nomes vêm de `adCampaignGroups`/`adCampaigns` (criativos não têm nome próprio). |
| Métricas | `GET /rest/adAnalytics?q=statistics` com `timeGranularity=DAILY`, `pivots` por nível, janelas de 30 dias (limite de 15 mil linhas por chamada): `costInLocalCurrency, impressions, clicks, externalWebsiteConversions, conversionValueInLocalCurrency, oneClickLeads`. |
| Conversões | Padrão: `external_website_conversions`. Pode-se mapear `one_click_leads` (Lead Gen Forms). |
| Quotas | Limites diários por app e por membro; 429 → retry exponencial. |
| Erros de permissão | 401/403 e `invalid_grant` no refresh → sem retry; requer reconexão. |

## TikTok Business API

| Item | Uso no V4 Insights |
|---|---|
| App | App no TikTok for Business Developers aprovado, com permissões de *Ad Account Management* e *Reporting*. Os escopos são os do app (não vão na URL). |
| OAuth | Portal de autorização do TikTok com `state` de uso único; o código volta em `auth_code`. Access token de longa duração, sem refresh. |
| Redirect URI | `${API_BASE_URL}/api/v1/integracoes/tiktok_ads/callback` (cadastrar no app). |
| Descoberta | `GET /oauth2/advertiser/get/` + `GET /advertiser/info/` (nome, moeda e fuso). |
| Métricas | `GET /report/integrated/get/` (`report_type=BASIC`, `data_level=AUCTION_CAMPAIGN/ADGROUP/AD`, dimensão `stat_time_day`) em janelas de 30 dias, paginado: `spend, impressions, clicks, conversion, complete_payment, total_complete_payment_rate` (valor das compras). |
| Conversões | Padrão: `conversion` (evento de otimização). Pode-se mapear `complete_payment`, que também traz valor. |
| Quotas | Limite de QPS (código 40100) e erros 5xxxx → retry exponencial. |
| Erros de permissão | Códigos 40001/40002 e 40102–40106 (token inválido/revogado) → sem retry; requer reconexão. |

## Política de coleta

- Carga histórica ao selecionar contas (padrão 90 dias, máx. 1095); incremental a cada
  `SYNC_INTERVAL_HOURS` (padrão 6h) reprocessando os últimos 3 dias (ajustes tardios dos provedores).
- Concorrência limitada por provedor (`SYNC_MAX_CONCURRENCY_PER_PROVIDER`).
- UPSERT idempotente; jobs com chave idempotente e histórico em `sync_jobs`.
- Freshness exibido por conta (`ultima_sincronizacao_em`, `dados_ate`) e nos dashboards.

## Riscos e mitigação

| Risco | Mitigação |
|---|---|
| App Review/developer token não aprovados | Conectores ficam indisponíveis (503 com mensagem clara); o restante do sistema funciona. |
| Token expirado/revogado pelo anunciante | Detecção no sync → status "requer reconexão" e alerta na tela inicial. |
| Quotas estouradas em muitas contas | Retry com backoff + limite de concorrência; aumentar intervalo do incremental. |
| Conversões incomparáveis entre plataformas | Nenhuma equivalência implícita: exige mapeamento por conta; detalhe por ação preservado em `conversoes_detalhe`. |
| Moedas diferentes no mesmo cliente | Aviso explícito no dashboard e no PDF (sem conversão cambial). |
| Vazamento de tokens | Criptografia com chave fora do banco, logs sanitizados, nada no frontend (verificado no CI). |
| Mudanças de versão das APIs | Versões configuráveis (`META_GRAPH_VERSION`, `GOOGLE_ADS_API_VERSION`, `LINKEDIN_API_VERSION`, `TIKTOK_API_VERSION`); revisar a cada release dos provedores. |

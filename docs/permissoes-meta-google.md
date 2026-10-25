# Integrações Meta Ads e Google Ads — permissões, campos, quotas e riscos (V4-011)

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
| Mudanças de versão das APIs | Versões configuráveis (`META_GRAPH_VERSION`, `GOOGLE_ADS_API_VERSION`); revisar a cada release dos provedores. |

# Dados, migrations e contratos (SPEC-08)

## Versionamento do schema

| Revisão | Conteúdo |
|---|---|
| `0001` | Executa **exatamente** `backend/alembic/baseline/001_initial.sql` (pacote Sprint 1, sha256 `9f7b96d3…532f`). |
| `0002` | Ajustes incrementais e reversíveis da SPEC-08 (abaixo). |

Sempre aplique com `python -m app.db.migrate` (o serviço `migrate` do Compose faz isso):

| Estado encontrado | Ação |
|---|---|
| Base limpa | `upgrade head` (0001 + 0002). |
| Base inicializada manualmente com `001_initial.sql` (sem `alembic_version`) | Valida as 12 tabelas e os 4 perfis, registra `stamp 0001` **sem reaplicar** o SQL e segue para `head`. |
| Base parcial (algumas tabelas da baseline) | **Recusa** e encerra com erro — exige intervenção manual. |
| Base já versionada | `upgrade head` (no-op se atualizada). |

`alembic upgrade` direto numa base com a baseline já aplicada também é recusado pela própria 0001.

## Ajustes da 0002

- **Novas tabelas**: `sessoes` (só `token_hash`/`csrf_hash`, nunca o token), `sync_jobs`,
  `credenciais_integracao` (ciphertext Fernet; chave fora do banco), `oauth_states`
  (state/nonce/PKCE de uso único).
- **clientes.status** passa a aceitar `arquivado` (linhas com `arquivado_em` são migradas);
  `inativo` da baseline continua válido.
- **integracoes.status** ganha `pausada`; colunas `escopos`, `conectado_por`, `revogada_em`.
- **contas_anuncio**: `carga_historica_dias`, `mapeamento_conversoes`, `ultima_sincronizacao_em`,
  `dados_ate` (freshness), `criado_em`.
- **metricas_diarias**: `conversoes`/`valor_conversoes` passam a aceitar `NULL` e perdem o
  default 0 — `NULL` = sem mapeamento explícito de conversão (valores existentes preservados);
  novas colunas `entidade_nome`, `campanha_externa_id`, `campanha_nome`, `conjunto_externo_id`,
  `conjunto_nome`, `conversoes_detalhe`.
- **dashboards / relatorios**: `atualizado_em`; `relatorios.arquivado_em` (exclusão lógica).
- **relatorio_execucoes**: `idempotency_key` (única por relatório), `solicitado_por`,
  `progresso`, `snapshot`, `tamanho_bytes`, `expira_em`.
- **auditoria**: `cliente_id` (filtro por carteira), `ip`, `request_id`.
- **Índices** dos filtros mais usados: métricas por conta/nível/data e por campanha, auditoria
  por cliente/data, clientes por status/nome, execuções por relatório/data, jobs por
  integração/data e status.

## Unicidade e IDs externos

IDs externos **não são globais entre plataformas** nem entre contas:

| Restrição | Escopo |
|---|---|
| `contas_anuncio (integracao_id, conta_externa_id)` | conta única por integração (provedor + cliente) |
| `metricas_diarias (conta_anuncio_id, data, nivel, entidade_externa_id)` | chave do UPSERT idempotente |
| `sync_jobs (integracao_id, idempotency_key)` | job idempotente por integração |
| `relatorio_execucoes (relatorio_id, idempotency_key)` | geração idempotente por relatório |
| `usuarios lower(email)`, `usuarios.google_sub`, `sessoes.token_hash` | identidade |

Agregações de campanhas sempre agrupam por `conta_anuncio_id` + ID externo.

## Integridade referencial e exclusões

| Entidade | Política |
|---|---|
| Cliente | **Nunca excluído**: arquivar = `status='arquivado'` + `arquivado_em`. Integrações, contas, métricas, dashboards, relatórios e execuções permanecem. FKs sem `ON DELETE` (restrict) impedem exclusão acidental. |
| Usuário | Não é excluído; desativar (`ativo=false`) revoga sessões. Vínculos `usuarios_clientes` e sessões têm `CASCADE`; `auditoria.usuario_id` e `*_por` usam `SET NULL`. |
| Integração | Revogar remove a credencial (`credenciais_integracao`) e cancela jobs; a linha e as contas/métricas permanecem. |
| Conta de anúncio | Desmarcada → `ativa=false` (para de coletar, preserva histórico). |
| Dashboard | Exclusão física; widgets em `CASCADE`. Métricas não são afetadas. |
| Relatório | Exclusão lógica (`arquivado_em`); execuções e PDFs permanecem no histórico. |
| PDF | Removido do storage após `REPORTS_RETENTION_DAYS`; o registro da execução permanece (`arquivo_referencia=NULL`). |

## Contratos comuns da API (`/api/v1`)

- **Lista**: `{"items": [], "page": 1, "page_size": 20, "total": 0}`; `page_size` máximo 100.
- **Erro**: `{"error": {"code": "FORBIDDEN", "message": "...", "request_id": "..."}}`;
  validação inclui `details: [{loc, msg}]`. O `request_id` também volta no header `X-Request-ID`
  e aparece nos logs JSON e na auditoria.
- **Status**: 422 validação · 401 não autenticado · 403 sem permissão · 404 recurso de outro
  cliente (não revela existência) · 409 conflito · 429 limite · 502 erro/recusa do provedor ·
  503 quota ou indisponibilidade do provedor.
- **Assíncrono**: `POST /integracoes/{id}/sincronizar` e `POST /relatorios/{id}/gerar`
  respondem **202** com `{job_id, job_ids, status, status_url}`.
- **Serialização**: timestamps ISO 8601 com fuso (`Z` = UTC); dinheiro e razões como string
  decimal; datas de métricas no fuso da conta.
- **Cliente TypeScript**: gerado do OpenAPI (`python -m app.cli openapi` → `frontend/openapi.json`
  → `npm run gen:api`); o CI falha se houver divergência.

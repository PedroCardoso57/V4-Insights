# SPEC-03 — Meta Ads e Google Ads

## Objetivo
Autorizar contas publicitárias e coletar métricas de forma segura, auditável e resiliente.

## Provedores
- **Meta Marketing API:** autorização Meta, descoberta de contas disponíveis, insights de campanhas e conjuntos/anúncios conforme permissões concedidas.
- **Google Ads API:** OAuth Google separado do login interno, developer token e demais requisitos de acesso à API; descoberta de customer IDs autorizados.

**Acesso às APIs depende de revisão, escopos, quotas e políticas vigentes dos provedores.** Não implementar scraping ou contornar permissões.

## Fluxos
1. Analista autorizado inicia conexão para cliente; callback usa `state` associado ao usuário/cliente e valida integridade.
2. Tokens ficam em armazenamento criptografado com chave fora do banco; `integracoes.referencia_credencial` aponta para segredo, não contém token.
3. Selecionar contas externas e gravar `contas_anuncio` com ID externo, moeda e fuso.
4. Criar job de carga histórica configurável e job incremental agendado; padrão inicial sugerido 6h, sujeito a quotas.
5. Normalizar métricas e executar UPSERT pela chave `(conta_anuncio_id, data, nivel, entidade_externa_id)`.
6. Registrar execução (`sync_jobs`) com status, início/fim, intervalo, quantidade, erro sanitizado, retries e identificador idempotente.
7. Permitir reconectar, pausar e revogar; interromper sincronização quando revogada.

## Endpoints
`GET /integracoes?cliente_id=`, `POST /integracoes/{plataforma}/autorizar`, `GET /integracoes/{plataforma}/callback`, `GET /integracoes/{id}/contas`, `POST /integracoes/{id}/contas`, `POST /integracoes/{id}/sincronizar`, `GET /integracoes/{id}/jobs`, `POST /integracoes/{id}/revogar`.

## Erros e consistência
Retry exponencial para 429/5xx; não repetir automaticamente erros de permissão; limitar concorrência por provedor; registrar freshness por conta; métricas de conversão não devem ser equiparadas sem mapeamento explícito de ação/janela de atribuição.

## Critérios de aceite
Conexão válida lista contas autorizadas, sync duplicado não duplica linhas, falha de quota tem retry controlado, revogação bloqueia novas coletas, logs não expõem segredos, cada usuário vê apenas integrações de seus clientes.

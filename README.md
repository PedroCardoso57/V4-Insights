# V4 Insights

Plataforma interna para acompanhar a performance de mídia paga dos clientes: login com Google,
carteiras de clientes por colaborador, conexão com **Meta Ads** e **Google Ads**, coleta
automática de métricas e dashboards de KPIs.

As especificações que guiam o projeto estão em [`specs/`](specs/).

```
backend/    API FastAPI + worker de sincronização (Python 3.12+, SQLAlchemy, Alembic, RQ)
frontend/   SPA React + Vite + TypeScript
infra/      Caddyfile do proxy reverso
specs/      SPEC-00 a SPEC-04
```

## Arquitetura

```
             ┌────────────── proxy (Caddy, HTTPS) ──────────────┐
navegador ──▶│  /        → frontend (nginx, arquivos estáticos) │
             │  /api/*   → api (FastAPI)                        │
             └──────────────────────────────────────────────────┘
                              │             ▲
                    postgres ◀┤             │ fila (Redis/RQ)
                              │             ▼
                              └──────── worker ──▶ Meta / Google Ads APIs
```

- **api**: autenticação, RBAC, CRUD e consultas de métricas.
- **worker**: executa os jobs de sincronização e agenda incrementais (padrão: a cada 6h).
- **postgres** e **redis** ficam apenas na rede interna (sem portas publicadas).
- **migrate**: serviço one-shot que roda `alembic upgrade head` antes de api/worker subirem.

## Pré-requisitos

- Docker 24+ com Compose v2 (para rodar tudo em containers), **ou**
- Python 3.12+, [uv](https://docs.astral.sh/uv/) 0.11+, Node 22 LTS, PostgreSQL 16 e Redis 7
  (para desenvolvimento local).
- Credenciais OAuth:
  - **Login interno**: cliente OAuth "Web application" no Google Cloud Console.
  - **Meta**: app no Meta for Developers com a permissão `ads_read` aprovada.
  - **Google Ads**: cliente OAuth próprio (separado do login) e *developer token* aprovado.

> O acesso às APIs dos provedores depende de revisão do app, escopos, quotas e políticas
> vigentes. O sistema não faz scraping nem contorna permissões: sem aprovação, a conexão
> correspondente fica indisponível (a API responde 503 para aquele provedor).

## Setup com Docker

```bash
cp .env.example .env
# gere a chave de criptografia dos tokens e cole em ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# preencha GOOGLE_OIDC_CLIENT_ID/SECRET (e Meta/Google Ads, se for usar)

docker compose up --build -d
docker compose ps                       # todos devem ficar "healthy"
curl http://localhost/api/health/ready  # {"status":"ok",...}

# primeiro administrador (o login só aceita usuários pré-cadastrados)
docker compose run --rm api python -m app.cli criar-admin --email voce@empresa.com --nome "Seu Nome"
```

Acesse http://localhost e clique em **Entrar com Google**.

Redirect URIs a cadastrar nos provedores (com `API_BASE_URL=https://seu-dominio/api`):

| Finalidade  | Redirect URI                                     |
|-------------|--------------------------------------------------|
| Login       | `${API_BASE_URL}/auth/google/callback`           |
| Meta Ads    | `${API_BASE_URL}/integracoes/meta/callback`      |
| Google Ads  | `${API_BASE_URL}/integracoes/google_ads/callback`|

## Desenvolvimento local (sem Docker)

```bash
# backend
cd backend
uv sync
cp ../.env.example .env   # ajuste DATABASE_URL/REDIS_URL para localhost,
                          # API_BASE_URL=http://localhost:5173/api, FRONTEND_URL=http://localhost:5173
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
uv run python -m app.worker          # em outro terminal

# frontend (proxy /api → localhost:8000 configurado no Vite)
cd frontend
npm ci
npm run dev                          # http://localhost:5173
```

## Comandos

| Onde      | Comando                                  | O que faz                              |
|-----------|------------------------------------------|----------------------------------------|
| backend   | `uv run pytest`                          | testes (precisa de Postgres e Redis)   |
| backend   | `uv run ruff check . && uv run ruff format --check .` | lint e formatação          |
| backend   | `uv run mypy app`                        | typecheck                              |
| backend   | `uv run alembic revision --autogenerate -m "descricao"` | nova migration          |
| backend   | `uv run alembic check`                   | confere modelos × migrations           |
| backend   | `uv run python -m app.cli criar-admin ...` | cria/promove administrador           |
| frontend  | `npm run lint` / `npm run typecheck`     | lint e typecheck                       |
| frontend  | `npm test` / `npm run build`             | testes e build de produção             |

Os testes do backend usam `TEST_DATABASE_URL` (padrão
`postgresql+psycopg://v4:v4@localhost:5432/v4insights_test`) e **recriam o schema** desse
banco: nunca aponte para um banco com dados.

## Perfis de acesso

| Perfil        | Pode                                                                                  |
|---------------|---------------------------------------------------------------------------------------|
| admin         | tudo: usuários, todos os clientes, integrações, dashboards, auditoria completa        |
| gestor        | criar clientes (entram na própria carteira), editar/arquivar e atribuir equipe dos clientes da carteira, integrações, dashboards, auditoria da carteira |
| analista      | ler clientes da carteira, manter integrações e dashboards                             |
| visualizador  | somente leitura de dashboards dos clientes da carteira                                |

Clientes fora da carteira respondem **404** (não revelam existência). A interface esconde ações
sem permissão, mas a API é sempre quem decide.

## Integrações e métricas

- Tokens dos provedores são criptografados (Fernet) com `ENCRYPTION_KEY`, que fica **fora do
  banco**. A tabela `integracoes` guarda apenas `referencia_credencial` (`secret:<uuid>`).
- Ao selecionar contas, é criado um job de **carga histórica** (dias configuráveis). O worker
  agenda **incrementais** a cada `SYNC_INTERVAL_HOURS`, reprocessando os últimos 3 dias.
- Métricas são gravadas por **UPSERT** em `(conta_anuncio_id, data, nivel, entidade_externa_id)`;
  cada job tem chave idempotente, então pedidos duplicados não duplicam linhas.
- 429/5xx/falha de rede: retry exponencial com jitter (até `SYNC_MAX_RETRIES`). Erros de
  permissão não são repetidos: a integração vai para `erro` e pede reconexão.
- Concorrência limitada por provedor (`SYNC_MAX_CONCURRENCY_PER_PROVIDER`).
- **Conversões** só são contabilizadas com mapeamento explícito por conta (`action_types` e,
  no Meta, `janela` de atribuição opcional). Google Ads começa com as conversões primárias da
  conta (`conversions`); Meta começa sem mapeamento (conversões, CPA e ROAS ficam ausentes).
  Os valores brutos por tipo de ação ficam em `conversoes_detalhe` e são recalculados ao
  mudar o mapeamento.
- KPIs: CTR = 100·cliques/impressões; CPC = investimento/cliques; CPM = 1000·investimento/impressões;
  CPA = investimento/conversões; ROAS = valor_conversões/investimento. Divisão por zero
  resulta em valor **ausente**. Agregações usam um único nível por consulta (padrão: campanha).

## Deploy em VPS

1. Instale Docker e aponte o DNS do domínio para a VPS (portas 80 e 443 abertas).
2. Clone o repositório numa tag de release: `git checkout v0.1.0`.
3. Crie o `.env` com `ENVIRONMENT=production`, `COOKIE_SECURE=true`,
   `SITE_ADDRESS=insights.suaempresa.com.br`, `API_BASE_URL=https://insights.suaempresa.com.br/api`,
   `FRONTEND_URL=https://insights.suaempresa.com.br`, `APP_VERSION=v0.1.0` e os segredos.
   Guarde `ENCRYPTION_KEY` e as senhas também num cofre.
4. `docker compose up --build -d` — o Caddy emite o certificado automaticamente.
5. Backup do banco (agende via cron):
   `docker compose exec -T postgres pg_dump -U $POSTGRES_USER -Fc $POSTGRES_DB > backup-$(date +%F).dump`

### Atualização

```bash
docker compose exec -T postgres pg_dump -U $POSTGRES_USER -Fc $POSTGRES_DB > pre-deploy.dump
git fetch --tags && git checkout vX.Y.Z
APP_VERSION=vX.Y.Z docker compose up --build -d     # migrate roda antes de api/worker
```

### Rollback

1. Volte o código e as imagens para a versão anterior:
   `git checkout vX.Y.(Z-1) && APP_VERSION=vX.Y.(Z-1) docker compose up --build -d`.
2. Se a versão nova trouxe migrations, reverta-as **antes** de subir o código antigo:
   `docker compose run --rm migrate alembic downgrade <revisão_anterior>`
   (consulte `alembic history`). Se o downgrade não for seguro, restaure o dump
   `pre-deploy.dump` com `pg_restore --clean`.

### Baseline SQL existente

Se um ambiente já recebeu o schema por um SQL aplicado manualmente (antes do Alembic), a
migration inicial **se recusa a rodar** para não duplicar tabelas. Nesse caso:

1. compare o schema existente com `migrations/versions/0001_schema_inicial.py`
   (por exemplo, `uv run alembic upgrade head --sql` gera o DDL esperado);
2. ajuste diferenças manualmente;
3. registre o estado sem reaplicar: `docker compose run --rm migrate alembic stamp 0001`;
4. siga com `alembic upgrade head` normalmente.

## Troubleshooting

| Sintoma | Causa provável / solução |
|---------|--------------------------|
| API não sobe: `ValidationError` na inicialização | variável obrigatória ausente ou inválida no `.env` (ex.: `ENCRYPTION_KEY` precisa ter 32 bytes em base64). |
| `/health/ready` retorna 503 | banco ou Redis indisponível: `docker compose ps` e `docker compose logs postgres redis`. |
| Login retorna 403 | o e-mail não está cadastrado, o usuário está inativo ou a conta Google é diferente da já vinculada (admin pode desvincular em `PATCH /usuarios/{id}` com `desvincular_google`). |
| Login retorna 400 "state inválido" | o fluxo demorou mais de 10 min ou foi reaproveitado; inicie novamente. |
| Mutações retornam 403 "CSRF/Origin" | `FRONTEND_URL`/`ALLOWED_ORIGINS` não bate com a origem real do navegador. |
| Cookie de sessão não é gravado em HTTP local | use `COOKIE_SECURE=false` apenas em desenvolvimento. |
| Conectar provedor retorna 503 | credenciais do provedor ausentes no `.env`. |
| Integração em `erro` | token revogado ou permissão retirada no provedor: use **Reconectar**. |
| Métricas não aparecem | veja **Execuções** na aba Integrações; jobs em `pendente` com próxima tentativa indicam quota/retry. |
| `migrate` falha com "Tabelas já existem" | veja *Baseline SQL existente*. |
| Build Docker falha com erro de certificado | rede com proxy TLS: passe a CA via `docker build --secret id=extra_ca,src=ca.crt`. |

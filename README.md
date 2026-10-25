# V4 Insights — V4 Bounnacorso

Plataforma interna (uso exclusivo de colaboradores) para gestão de clientes, conexão de contas
**Meta Ads** e **Google Ads**, dashboards de KPIs e relatórios em PDF.

Especificações em [`specs/`](specs/README.md) · Documentação em [`docs/`](docs/):
[dados e contratos](docs/dados.md) · [permissões Meta/Google](docs/permissoes-meta-google.md) ·
[runbook](docs/runbook.md) · [LGPD](docs/lgpd.md).

```
backend/    FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + Celery (Python 3.12+)
  app/{api,core,db,models,schemas,services,integrations,workers}
  alembic/{baseline,versions}   tests/{unit,integration}
frontend/   Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query + RHF/Zod + Recharts
  src/{app,components,features,services,hooks}   e2e/ (Playwright)
infra/      proxy/ (Caddy) · backup/ (scripts) · docker/ (sobreposições)
docs/  specs/  docker-compose.yml  .env.example
```

## Arquitetura

```
navegador ──▶ proxy (Caddy, HTTPS) ──┬─ /api/*, /health/* ─▶ api (FastAPI, /api/v1) ─┬─▶ PostgreSQL
                                     └─ demais rotas ───────▶ frontend (Next.js)       └─▶ Redis ─▶ worker (Celery + beat)
                                                                                                    ├─ Meta / Google Ads APIs
                                                                                                    └─ PDFs (volume privado)
```

- Login Google OIDC (Authorization Code + PKCE, state/nonce) **ou e-mail e senha** (hash Argon2id,
  opcional por usuário), sempre só para usuários pré-cadastrados; sessão de servidor em cookie
  `HttpOnly`/`Secure`/`SameSite=Lax`, CSRF + Origin em mutações, limite de tentativas por IP e por e-mail.
- Quatro perfis (admin, gestor, analista, visualizador) e escopo por carteira de clientes.
- Sincronização assíncrona e idempotente (UPSERT, chave por job, retry exponencial, freshness).
- Relatórios: snapshot dos números no momento da solicitação → PDF A4 gerado no worker →
  download autenticado e auditado; retenção configurável.
- Segurança e operação (SPEC-07): rate limit no login e em operações caras, proteção SSRF,
  rotação de chave, métricas Prometheus internas, alertas por webhook, retenção LGPD.
- Contratos comuns: listas `{items,page,page_size,total}`, erros `{error:{code,message,request_id}}`,
  202 com `job_id` para tarefas assíncronas. Cliente TypeScript gerado do OpenAPI.

## Pré-requisitos

- Docker 24+ com Compose v2, **ou** Python 3.12+, [uv](https://docs.astral.sh/uv/) 0.11+,
  Node 22 LTS, PostgreSQL 16 e Redis 7.
- Credenciais OAuth: login interno (Google Cloud, "Web application"); Meta (app com `ads_read`
  aprovado); Google Ads (OAuth próprio + developer token). Detalhes em
  [docs/permissoes-meta-google.md](docs/permissoes-meta-google.md).

## Setup com Docker

```bash
cp .env.example .env
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # → ENCRYPTION_KEY
# preencha GOOGLE_OIDC_CLIENT_ID/SECRET (e Meta/Google Ads, se for usar)

docker compose up --build -d
docker compose ps                         # todos "healthy"
curl http://localhost/health/ready        # {"status":"ok",...}

# primeiro administrador (não há autocadastro)
docker compose run --rm api python -m app.cli criar-admin --email voce@empresa.com --nome "Seu Nome"
```

Acesse http://localhost e clique em **Entrar com Google**. Para entrar com e-mail e senha, defina
uma senha: `docker compose run --rm api python -m app.cli definir-senha --email voce@empresa.com`
(pede a senha sem eco). Depois, o admin define/redefine senhas na tela **Usuários** e cada pessoa
troca a própria em **Configurações**. Não há "esqueci a senha" por e-mail: quem esquece pede ao admin.

| Finalidade | Redirect URI |
|---|---|
| Login | `${API_BASE_URL}/api/v1/auth/google/callback` |
| Meta Ads | `${API_BASE_URL}/api/v1/integracoes/meta_ads/callback` |
| Google Ads | `${API_BASE_URL}/api/v1/integracoes/google_ads/callback` |

### Base já inicializada com `001_initial.sql`

O serviço `migrate` executa `python -m app.db.migrate`: em base limpa aplica a baseline e a
0002; numa base onde o `001_initial.sql` do pacote Sprint 1 já foi aplicado manualmente, valida
a estrutura, registra a baseline **sem reaplicá-la** e aplica só a 0002, preservando os dados.
Base parcial é recusada. Veja [docs/dados.md](docs/dados.md).

## Desenvolvimento local

```bash
# backend (Postgres e Redis locais)
cd backend && uv sync
cp ../.env.example .env   # DATABASE_URL/REDIS_URL locais; API_BASE_URL e FRONTEND_URL = http://localhost:3000
uv run python -m app.db.migrate
uv run uvicorn app.main:app --reload --port 8000
uv run celery -A app.workers.celery_app worker -B --loglevel INFO     # outro terminal

# frontend (o Next encaminha /api e /health para :8000 em desenvolvimento)
cd frontend && npm ci && npm run dev      # http://localhost:3000
```

## Comandos

| Onde | Comando | O que faz |
|---|---|---|
| backend | `uv run pytest` | testes unit + integração (Postgres/Redis; usa `TEST_DATABASE_URL` e **recria o schema** desse banco) |
| backend | `uv run ruff check . && uv run ruff format --check . && uv run mypy app` | lint, formatação, typecheck |
| backend | `uv run alembic revision --autogenerate -m "..."` / `uv run alembic check` | nova migration / conferir modelos × migrations |
| backend | `uv run python -m app.cli openapi --out ../frontend/openapi.json` | exporta o OpenAPI |
| frontend | `npm run gen:api` | gera `src/services/api/schema.d.ts` do OpenAPI |
| frontend | `npm run lint && npm run typecheck && npm test` | lint, tipos, testes unitários |
| frontend | `npm run build && npm run check:bundle` | build e verificação de credenciais no bundle |
| frontend | `npm run test:e2e` | E2E Playwright (requer build; API simulada) |
| infra | `infra/backup/backup.sh` / `infra/backup/restore.sh <arquivo>` | backup criptografado / restauração |
| infra | `infra/monitor/verificar.sh` | verificações do host com alerta (cron) |
| infra | `infra/vps/provisionar.sh` | provisionamento seguro da VPS (uma vez, como root) |
| backend | `python -m app.cli definir-senha --email ...` | define a senha de login de um usuário |
| backend | `python -m app.cli rotacionar-chave` / `revogar-sessoes` / `lgpd-exportar` / `lgpd-anonimizar` | operação e incidentes |

Para o CI **bloquear merge**, ative em *Settings → Branches* a proteção da `main` exigindo os
checks "Backend", "Frontend" e "Build das imagens".

O CI (GitHub Actions) roda tudo isso, verifica migrations (base limpa, repetição, `alembic check`,
rollback), a sincronia OpenAPI ↔ cliente TS e o build das imagens.

## Perfis

| Perfil | Pode |
|---|---|
| admin | tudo: usuários, todos os clientes, integrações, dashboards, relatórios, auditoria completa |
| gestor | criar clientes (entram na carteira), editar/arquivar e atribuir equipe dos clientes da carteira, integrações, dashboards, relatórios, auditoria da carteira |
| analista | ler clientes da carteira; manter integrações, dashboards e relatórios desses clientes |
| visualizador | somente leitura de dashboards e relatórios (inclui download de PDFs) dos clientes da carteira |

Recursos de clientes fora da carteira respondem **404**. A interface oculta ações sem permissão;
a API aplica a autorização real.

## Deploy, rollback, backup e troubleshooting

Ver [docs/runbook.md](docs/runbook.md). Resumo do deploy em VPS: DNS apontado, portas 80/443,
`.env` com `ENVIRONMENT=production`, `COOKIE_SECURE=true`, `SITE_ADDRESS=<domínio>`,
`API_BASE_URL`/`FRONTEND_URL=https://<domínio>`; `docker compose up --build -d` (HTTPS automático).

| Sintoma | Causa provável |
|---|---|
| API não sobe (`ValidationError`) | variável obrigatória ausente/inválida (`ENCRYPTION_KEY` precisa de 32 bytes base64) |
| `/health/ready` 503 | banco ou Redis indisponível |
| Login volta com "acesso negado" | e-mail não cadastrado, usuário inativo ou conta Google diferente da vinculada |
| "E-mail ou senha inválidos" | senha errada, usuário sem senha definida (só Google) ou inativo — a mensagem é a mesma de propósito |
| Login por senha responde 429 | muitas tentativas para o IP (`RATE_LIMIT_LOGIN`) ou para o e-mail (`RATE_LIMIT_LOGIN_EMAIL`) |
| Mutações com 403 CSRF/Origin | `FRONTEND_URL`/`ALLOWED_ORIGINS` diferente da origem real |
| Conectar provedor → 503 | credenciais do provedor ausentes no `.env` |
| `migrate` recusa a base | base parcialmente inicializada; ver docs/dados.md |
| Build falha por certificado | proxy TLS corporativo: `docker build --secret id=extra_ca,src=ca.crt` |

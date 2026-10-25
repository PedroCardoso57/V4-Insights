# Runbook de operação

## Serviços

| Serviço | Função | Saúde |
|---|---|---|
| `proxy` (Caddy) | TLS, headers de segurança, roteia `/api/*` e `/health/*` → api, resto → frontend | `GET /health/live` via proxy |
| `frontend` (Next.js standalone) | Interface | `GET /login` |
| `api` (FastAPI) | Regras de negócio, `/api/v1` | `GET /health/ready` (banco + Redis; 503 se indisponível) |
| `worker` (Celery `-B`) | Sincronizações, PDFs, agendador (5 min), limpeza de PDFs (1h) | `celery inspect ping` |
| `migrate` | `python -m app.db.migrate` antes de api/worker | sai com código 0 |
| `postgres`, `redis` | Dados e fila — **sem portas publicadas** | `pg_isready`, `redis-cli ping` |

Mantenha **uma** réplica do `worker` com `-B` (beat). Para escalar, adicione workers sem `-B`.

## Logs e correlação

Logs em JSON (uma linha por evento) com `request_id`, sanitizados contra tokens.
Para investigar um erro informado pelo usuário: `docker compose logs api worker | grep <request_id>`.
A auditoria também guarda o `request_id` das ações sensíveis.

## Deploy

```bash
docker compose exec -T postgres pg_dump -U $POSTGRES_USER -Fc $POSTGRES_DB > pre-deploy.dump
git fetch --tags && git checkout vX.Y.Z
APP_VERSION=vX.Y.Z docker compose up --build -d   # migrate roda antes de api/worker
docker compose ps                                  # todos healthy
```

## Rollback

1. Se a versão trouxe migrations, reverta-as **antes** de voltar o código:
   `docker compose run --rm migrate alembic downgrade <revisão anterior>` (veja `alembic history`).
   Se não for seguro, restaure `pre-deploy.dump` (`pg_restore --clean --if-exists`).
2. `git checkout vX.Y.(Z-1) && APP_VERSION=vX.Y.(Z-1) docker compose up --build -d`.

## Backup e restauração

- `infra/backup/backup.sh` — dump do banco + PDFs, cifrado com AES-256 (gpg) usando
  `BACKUP_PASSPHRASE_FILE`, checksum sha256, cópia externa opcional (`BACKUP_REMOTE`, rclone) e
  retenção local (`BACKUP_RETENTION_DAYS`). Agende via cron, ex.: `15 3 * * * /opt/v4/infra/backup/backup.sh`.
- `infra/backup/restore.sh arquivo.tar.gpg` — confere checksum, para api/worker, restaura banco e
  PDFs, aplica migrations pendentes e sobe os serviços.
- **Teste de restauração**: mensalmente, em homologação
  (`docker compose -f docker-compose.yml -f infra/docker/compose.homologacao.yml`), restaure o
  backup mais recente e confira contagens de clientes/execuções e o download de um PDF.
  Validado em 25/10/2026: banco e PDFs apagados foram recuperados e o PDF voltou a ser baixado.
- Guarde a senha de backup e a `ENCRYPTION_KEY` num cofre, separadas dos backups.
  Perder a `ENCRYPTION_KEY` exige reconectar todas as integrações.

## Incidentes comuns

| Sintoma | Ação |
|---|---|
| `/health/ready` 503 | `docker compose ps`; logs de `postgres`/`redis`; espaço em disco. |
| Jobs parados em `pendente` | Verifique o worker (`docker compose logs worker`); o agendador reenfileira pendentes após 15 min. |
| Integração "requer reconexão" | Token revogado/expirado no provedor: botão **Reconectar** na tela de integrações. |
| PDF em `erro` | Mensagem segura na execução; gere novamente (mesma `Idempotency-Key` reprocessa o mesmo snapshot). |
| Login 403 | E-mail não cadastrado, usuário inativo ou `sub` Google diferente do vinculado (admin pode desvincular). |

## Checklist de produção

- [ ] `ENVIRONMENT=production`, `COOKIE_SECURE=true`, `SITE_ADDRESS` com domínio (HTTPS)
- [ ] Segredos fora do repositório; `ENCRYPTION_KEY` e senha de backup no cofre
- [ ] Redirect URIs cadastrados nos três OAuth (login, Meta, Google Ads)
- [ ] Primeiro admin criado com `python -m app.cli criar-admin`
- [ ] Backup agendado e teste de restauração executado
- [ ] Firewall: apenas 80/443 (e SSH restrito) abertos na VPS

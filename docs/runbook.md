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

## Provisionamento da VPS

`infra/vps/provisionar.sh` (root, uma vez): atualizações automáticas de segurança, ufw só com
80/443 públicos e SSH restrito a `SSH_ALLOWED_FROM`, SSH apenas por chave e sem root, fail2ban,
Docker oficial com rotação de logs, usuário de deploy sem privilégios de root (processos dos
containers também rodam como usuário não-root) e crons de backup (03:15 UTC) e monitoração
(10 min). Portas publicadas pelo Docker ignoram o ufw: por isso só o proxy publica portas.

Homologação e produção usam o mesmo `docker-compose.yml` (produção) e a sobreposição
`infra/docker/compose.homologacao.yml` (homologação), com projetos e volumes separados.

## Logs e correlação

Logs em JSON (uma linha por evento) com `request_id`, sanitizados contra tokens.
Para investigar um erro informado pelo usuário: `docker compose logs api worker | grep <request_id>`.
A auditoria também guarda o `request_id` das ações sensíveis.

## Métricas e alertas

- `GET /metrics` (Prometheus) na rede interna — não é exposto pelo proxy. Para coletar de fora,
  rode um Prometheus/agent no mesmo host (rede `interna`). Principais séries:
  `v4_http_requests_total`, `v4_http_request_duration_seconds`, `v4_sync_jobs_24h{status}`,
  `v4_integracoes{plataforma,status}`, `v4_contas_desatualizadas`,
  `v4_sync_job_pendente_mais_antigo_segundos`, `v4_relatorio_execucoes_24h{status}`.
- Alertas por webhook (`ALERT_WEBHOOK_URL`, JSON `{"text": ...}`), sem repetição por 6h:

| Alerta | Origem |
|---|---|
| Erro persistente de sincronização (N falhas seguidas) e integração que requer reconexão | worker, a cada 15 min |
| Fila parada (job pendente há mais de 2h) e armazenamento de PDFs ≥ 85% | worker |
| Readiness da API ≠ 200, container sem `healthy`, disco ≥ `DISK_ALERT_PERCENT`, porta 5432/6379 no host | `infra/monitor/verificar.sh` (cron) |
| Falha do backup / backup mais antigo que `BACKUP_MAX_AGE_HOURS` | `backup.sh` (trap) e monitor |

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

**Proposta de objetivos (validar com o responsável):** RPO 24h (backup diário) e RTO 4h
(nova VPS provisionada + restauração). Retenção: 7 diários + o mais recente de cada uma das
últimas 4 semanas, local e no remoto.

- `infra/backup/backup.sh` — dump do banco + PDFs, cifrado com AES-256 (gpg) usando
  `BACKUP_PASSPHRASE_FILE`, checksum sha256, cópia externa opcional (`BACKUP_REMOTE`, rclone) e
  retenção 7 diários + 4 semanais (`BACKUP_KEEP_DAILY`/`BACKUP_KEEP_WEEKLY`). O `.env` só entra
  no backup com `BACKUP_INCLUDE_ENV=true` (compose e Caddyfile já estão no Git). Agende via cron, ex.: `15 3 * * * /opt/v4/infra/backup/backup.sh`.
- `infra/backup/restore.sh arquivo.tar.gpg` — confere checksum, para api/worker, restaura banco e
  PDFs, aplica migrations pendentes e sobe os serviços.
- **Teste de restauração**: mensalmente, em homologação
  (`docker compose -f docker-compose.yml -f infra/docker/compose.homologacao.yml`), restaure o
  backup mais recente e confira contagens de clientes/execuções e o download de um PDF.
  Validado em 25/10/2026: banco e PDFs apagados foram recuperados e o PDF voltou a ser baixado.
- Guarde a senha de backup e a `ENCRYPTION_KEY` num cofre, separadas dos backups.
  Perder a `ENCRYPTION_KEY` exige reconectar todas as integrações.

## Revogar credenciais

| Situação | Procedimento |
|---|---|
| Colaborador desligado ou conta suspeita | Desativar na tela **Usuários** (revoga sessões) ou `python -m app.cli revogar-sessoes --email ...` |
| Sessões comprometidas em massa | `python -m app.cli revogar-sessoes --todas` |
| Token de provedor vazado | **Revogar** a integração na tela (apaga a credencial e revoga no provedor) e reconectar; trocar o client secret no console do provedor |
| `ENCRYPTION_KEY` exposta | Mover a chave atual para `ENCRYPTION_KEYS_PREVIOUS`, gerar nova `ENCRYPTION_KEY`, reiniciar api/worker, `python -m app.cli rotacionar-chave`, esvaziar `ENCRYPTION_KEYS_PREVIOUS` e reiniciar de novo |
| Client secret do login Google exposto | Gerar novo secret no Google Cloud, atualizar `.env`, reiniciar api e `revogar-sessoes --todas` |

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
- [ ] VPS provisionada com `infra/vps/provisionar.sh` (firewall 80/443, SSH por chave)
- [ ] `ALERT_WEBHOOK_URL` configurado e alerta de teste recebido
- [ ] RPO/RTO e retenções (backup, auditoria, PDFs) aprovados
- [ ] Rollback demonstrado em homologação
- [ ] Merge bloqueado sem CI verde (proteção da branch `main` no GitHub)

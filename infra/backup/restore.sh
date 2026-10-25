#!/usr/bin/env bash
# Restaura um backup gerado por backup.sh.
#
#   infra/backup/restore.sh backups/v4-AAAAmmdd-HHMMSS.tar.gpg
#
# ATENÇÃO: substitui o conteúdo do banco e dos PDFs do ambiente atual.
# Para o teste de restauração periódico, rode num ambiente de homologação.
set -euo pipefail
cd "$(dirname "$0")/../.."
# Carrega o .env sem sobrescrever variáveis já definidas no ambiente.
if [ -f .env ]; then
  while IFS='=' read -r chave valor; do
    case "$chave" in ''|\#*) continue ;; esac
    [ -z "${!chave+x}" ] && export "$chave=$valor"
  done < .env
fi
ARQ="${1:?informe o arquivo .tar.gpg}"
: "${BACKUP_PASSPHRASE_FILE:?defina BACKUP_PASSPHRASE_FILE}"

if [ -f "$ARQ.sha256" ]; then sha256sum -c "$ARQ.sha256"; fi
if [ "${CONFIRMAR:-}" != "sim" ]; then
  read -r -p "Restaurar $ARQ sobre o ambiente atual? Digite 'sim': " resp
  [ "$resp" = "sim" ] || { echo "cancelado"; exit 1; }
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
gpg --batch --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" -d "$ARQ" | tar -xf - -C "$TMP"
cat "$TMP/MANIFEST"

echo "[restore] parando api e worker"
docker compose stop api worker

echo "[restore] banco"
docker compose exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner < "$TMP/db.dump"

echo "[restore] PDFs"
docker compose run --rm --no-deps -T -u 0 --entrypoint sh -v "$TMP:/in" api \
  -c 'rm -rf /var/lib/v4insights/relatorios/* && tar -xzf /in/relatorios.tgz -C /var/lib/v4insights'

echo "[restore] aplicando migrations pendentes e subindo serviços"
docker compose run --rm migrate
docker compose up -d api worker
echo "[restore] concluído"

#!/usr/bin/env bash
# Backup criptografado do PostgreSQL e dos PDFs de relatórios.
#
#   infra/backup/backup.sh            # gera backups/v4-AAAAmmdd-HHMMSS.tar.gpg
#
# Variáveis (.env ou ambiente):
#   BACKUP_PASSPHRASE_FILE  arquivo com a senha de criptografia (obrigatório; fora do repo)
#   BACKUP_DIR              diretório local (padrão: ./backups)
#   BACKUP_REMOTE           destino rclone opcional (ex.: s3cripto:v4-backups) — cópia externa
#   BACKUP_RETENTION_DAYS   remove backups locais mais antigos (padrão: 14)
set -euo pipefail
cd "$(dirname "$0")/../.."
# Carrega o .env sem sobrescrever variáveis já definidas no ambiente.
if [ -f .env ]; then
  while IFS='=' read -r chave valor; do
    case "$chave" in ''|\#*) continue ;; esac
    [ -z "${!chave+x}" ] && export "$chave=$valor"
  done < .env
fi

: "${BACKUP_PASSPHRASE_FILE:?defina BACKUP_PASSPHRASE_FILE}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RET="${BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$BACKUP_DIR"

echo "[backup] dump do banco"
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner > "$TMP/db.dump"

echo "[backup] PDFs de relatórios"
docker compose run --rm --no-deps -T -u 0 --entrypoint tar -v "$TMP:/out" api \
  -czf /out/relatorios.tgz -C /var/lib/v4insights relatorios

echo "versao=$(git describe --tags --always 2>/dev/null || echo desconhecida) data=$STAMP" > "$TMP/MANIFEST"
tar -cf "$TMP/v4-$STAMP.tar" -C "$TMP" db.dump relatorios.tgz MANIFEST

# Criptografia simétrica AES-256 antes de sair da VPS.
gpg --batch --yes --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" \
  --symmetric --cipher-algo AES256 -o "$BACKUP_DIR/v4-$STAMP.tar.gpg" "$TMP/v4-$STAMP.tar"
sha256sum "$BACKUP_DIR/v4-$STAMP.tar.gpg" > "$BACKUP_DIR/v4-$STAMP.tar.gpg.sha256"
echo "[backup] gerado $BACKUP_DIR/v4-$STAMP.tar.gpg"

if [ -n "${BACKUP_REMOTE:-}" ]; then
  rclone copy "$BACKUP_DIR/v4-$STAMP.tar.gpg" "$BACKUP_REMOTE/"
  rclone copy "$BACKUP_DIR/v4-$STAMP.tar.gpg.sha256" "$BACKUP_REMOTE/"
  echo "[backup] enviado para $BACKUP_REMOTE"
fi

find "$BACKUP_DIR" -name 'v4-*.tar.gpg*' -mtime "+$RET" -delete

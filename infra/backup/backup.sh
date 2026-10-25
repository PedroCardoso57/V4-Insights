#!/usr/bin/env bash
# Backup criptografado do PostgreSQL e dos PDFs de relatórios.
#
#   infra/backup/backup.sh            # gera backups/v4-AAAAmmdd-HHMMSS.tar.gpg
#
# Variáveis (.env ou ambiente):
#   BACKUP_PASSPHRASE_FILE  arquivo com a senha de criptografia (obrigatório; fora do repo)
#   BACKUP_DIR              diretório local (padrão: ./backups)
#   BACKUP_REMOTE           destino rclone (ex.: s3cripto:v4-backups) — cópia FORA da VPS
#   BACKUP_KEEP_DAILY       backups diários mantidos (padrão: 7)
#   BACKUP_KEEP_WEEKLY      backups semanais (domingo) mantidos (padrão: 4)
#   BACKUP_INCLUDE_ENV      true para incluir o .env (cifrado) — guarde a senha separada!
#   ALERT_WEBHOOK_URL       recebe alerta se o backup falhar
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
KEEP_DAILY="${BACKUP_KEEP_DAILY:-7}"
KEEP_WEEKLY="${BACKUP_KEEP_WEEKLY:-4}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"

alertar_falha() {
  local msg="[V4 Insights] FALHA no backup $STAMP (linha $1). Verifique a VPS."
  echo "$msg" >&2
  if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
    curl -fsS -m 10 -H 'Content-Type: application/json' \
      -d "{\"text\": \"$msg\"}" "$ALERT_WEBHOOK_URL" >/dev/null || true
  fi
}
trap 'alertar_falha $LINENO' ERR
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$BACKUP_DIR"

echo "[backup] dump do banco"
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner > "$TMP/db.dump"

echo "[backup] PDFs de relatórios"
docker compose run --rm --no-deps -T -u 0 --entrypoint tar -v "$TMP:/out" api \
  -czf /out/relatorios.tgz -C /var/lib/v4insights relatorios

ITENS=(db.dump relatorios.tgz MANIFEST)
# Configurações: compose/Caddyfile estão no Git; o .env (segredos) só se habilitado.
if [ "${BACKUP_INCLUDE_ENV:-false}" = "true" ] && [ -f .env ]; then
  cp .env "$TMP/env"
  ITENS+=(env)
fi
echo "versao=$(git describe --tags --always 2>/dev/null || echo desconhecida) data=$STAMP" > "$TMP/MANIFEST"
tar -cf "$TMP/v4-$STAMP.tar" -C "$TMP" "${ITENS[@]}"

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

# Retenção: últimos KEEP_DAILY backups + o mais recente de cada um dos últimos KEEP_WEEKLY
# domingos (semana ISO). Os demais são removidos localmente (o remoto segue a mesma regra).
mapfile -t TODOS < <(ls -1 "$BACKUP_DIR"/v4-*.tar.gpg 2>/dev/null | sort -r)
declare -A MANTER=()
for f in "${TODOS[@]:0:$KEEP_DAILY}"; do MANTER["$f"]=1; done
declare -A SEMANAS=()
for f in "${TODOS[@]}"; do
  d="$(basename "$f" | sed -E 's/^v4-([0-9]{8}).*/\1/')"
  semana="$(date -u -d "$d" +%G-%V)"
  if [ -z "${SEMANAS[$semana]:-}" ] && [ "${#SEMANAS[@]}" -lt "$KEEP_WEEKLY" ]; then
    SEMANAS[$semana]=1
    MANTER["$f"]=1
  fi
done
for f in "${TODOS[@]}"; do
  if [ -z "${MANTER[$f]:-}" ]; then
    rm -f "$f" "$f.sha256"
    [ -n "${BACKUP_REMOTE:-}" ] && rclone deletefile "$BACKUP_REMOTE/$(basename "$f")" 2>/dev/null || true
  fi
done

# Batimento para o monitor (infra/monitor/verificar.sh alerta se o backup envelhecer).
date -u +%s > "$BACKUP_DIR/.ultimo-sucesso"

#!/usr/bin/env bash
# Verificações do host (cron a cada 10 min) com alerta por webhook:
#   */10 * * * * /opt/v4-insights/infra/monitor/verificar.sh
#
# - readiness da API (banco + Redis) via proxy
# - containers sem status "healthy"
# - uso de disco acima de DISK_ALERT_PERCENT (padrão 85)
# - backup mais antigo que BACKUP_MAX_AGE_HOURS (padrão 26)
# - PostgreSQL/Redis expostos fora da rede interna (não podem escutar no host)
set -uo pipefail
cd "$(dirname "$0")/../.."
if [ -f .env ]; then
  while IFS='=' read -r chave valor; do
    case "$chave" in ''|\#*) continue ;; esac
    [ -z "${!chave+x}" ] && export "$chave=$valor"
  done < .env
fi
BASE="${MONITOR_URL:-http://127.0.0.1:${HTTP_PORT:-80}}"
DISK_MAX="${DISK_ALERT_PERCENT:-85}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_MAX="${BACKUP_MAX_AGE_HOURS:-26}"
ESTADO="${MONITOR_STATE_DIR:-/var/tmp/v4-monitor}"
mkdir -p "$ESTADO"
problemas=()

codigo="$(curl -s -o /dev/null -w '%{http_code}' -m 10 "$BASE/health/ready" || echo 000)"
[ "$codigo" = "200" ] || problemas+=("readiness da API retornou $codigo")

while read -r nome status; do
  case "$status" in *"(healthy)"*) ;; *) problemas+=("container $nome: $status") ;; esac
done < <(docker compose ps -a --format '{{.Service}} {{.Status}}' | grep -v '^migrate ')

uso="$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')"
[ "${uso:-0}" -lt "$DISK_MAX" ] || problemas+=("disco em ${uso}% (limite ${DISK_MAX}%)")

if [ -f "$BACKUP_DIR/.ultimo-sucesso" ]; then
  idade=$(( ( $(date -u +%s) - $(cat "$BACKUP_DIR/.ultimo-sucesso") ) / 3600 ))
  [ "$idade" -lt "$BACKUP_MAX" ] || problemas+=("último backup há ${idade}h")
else
  problemas+=("nenhum backup bem-sucedido registrado")
fi

if ss -ltnH 2>/dev/null | awk '{print $4}' | grep -Eq '(^|[:.])(5432|6379)$'; then
  problemas+=("porta 5432/6379 escutando no host: banco/Redis não podem ser expostos")
fi

assinatura="$(printf '%s\n' "${problemas[@]:-}" | sha256sum | cut -c1-16)"
if [ "${#problemas[@]}" -eq 0 ]; then
  rm -f "$ESTADO/ultimo-alerta"
  exit 0
fi
# Mesmo conjunto de problemas: não repete o alerta por 6h.
if [ -f "$ESTADO/ultimo-alerta" ] && [ "$(cut -d' ' -f1 "$ESTADO/ultimo-alerta")" = "$assinatura" ] \
   && [ $(( $(date +%s) - $(cut -d' ' -f2 "$ESTADO/ultimo-alerta") )) -lt 21600 ]; then
  exit 1
fi
echo "$assinatura $(date +%s)" > "$ESTADO/ultimo-alerta"
msg="[V4 Insights · $(hostname)] $(printf '%s; ' "${problemas[@]}")"
echo "$msg" >&2
if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
  python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}))' "$msg" |
    curl -fsS -m 10 -H 'Content-Type: application/json' -d @- "$ALERT_WEBHOOK_URL" >/dev/null || true
fi
exit 1

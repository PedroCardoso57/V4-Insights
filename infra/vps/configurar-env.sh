#!/usr/bin/env bash
# Cria o .env de produção a partir do .env.example, já com segredos aleatórios:
#
#   bash infra/vps/configurar-env.sh insights.suaempresa.com.br
#
# Preenche ENVIRONMENT, SITE_ADDRESS (HTTPS automático), API_BASE_URL, FRONTEND_URL,
# COOKIE_SECURE, POSTGRES_PASSWORD e ENCRYPTION_KEY. Não sobrescreve um .env existente.
# As credenciais OAuth (Google, Meta, LinkedIn, TikTok) continuam a ser preenchidas à mão.
set -euo pipefail
cd "$(dirname "$0")/../.."
DOMINIO="${1:?informe o domínio, ex.: insights.suaempresa.com.br}"
DOMINIO="${DOMINIO#https://}"; DOMINIO="${DOMINIO#http://}"; DOMINIO="${DOMINIO%/}"
case "$DOMINIO" in *[!A-Za-z0-9.-]*|"") echo "domínio inválido: $DOMINIO" >&2; exit 1 ;; esac
if [ -e .env ]; then
  echo ".env já existe; nada foi alterado (apague-o se quiser gerar de novo)." >&2
  exit 1
fi

# Senha só com hexadecimal: entra na DATABASE_URL sem precisar de escape.
senha_db="$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')"
# Chave Fernet: 32 bytes em base64 urlsafe.
chave="$(head -c 32 /dev/urandom | base64 | tr '+/' '-_')"

definir() { sed -i "s|^$1=.*|$1=$2|" .env; }
umask 077
cp .env.example .env
definir ENVIRONMENT production
definir SITE_ADDRESS "$DOMINIO"
definir API_BASE_URL "https://$DOMINIO"
definir FRONTEND_URL "https://$DOMINIO"
definir COOKIE_SECURE true
definir POSTGRES_PASSWORD "$senha_db"
definir ENCRYPTION_KEY "$chave"
chmod 600 .env

echo ".env criado para https://$DOMINIO"
echo "Guarde uma cópia da ENCRYPTION_KEY num cofre: perdê-la exige reconectar as integrações."

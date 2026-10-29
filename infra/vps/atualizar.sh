#!/usr/bin/env bash
# Atualiza o V4 Insights na VPS mostrando o mascote "Sistema em manutenção" durante a troca:
#
#   bash infra/vps/atualizar.sh
#
# 1. Puxa o código novo e constrói as imagens com o site ainda no ar.
# 2. Liga o modo manutenção (infra/proxy/paginas/manutencao.on) só na troca dos containers.
# 3. Espera todos ficarem saudáveis e desliga a manutenção. Se algo falhar, a manutenção
#    também é desligada, e o site cai na página "fora do ar" até ser corrigido.
set -euo pipefail

# Tudo dentro de uma função: o git pull pode reescrever este arquivo enquanto ele roda.
principal() {
  cd "$(dirname "$0")/../.."
  local aviso=infra/proxy/paginas/manutencao.on

  git pull --ff-only
  docker compose build

  touch "$aviso"
  trap 'rm -f "'"$aviso"'"' EXIT
  echo "Manutenção ligada; trocando os containers…"
  docker compose up -d --wait --wait-timeout 300
  echo "Atualização concluída; manutenção desligada."
}

principal "$@"

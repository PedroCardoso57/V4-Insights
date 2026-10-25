#!/usr/bin/env bash
# Provisionamento da VPS (Ubuntu 22.04/24.04 ou Debian 12), executado como root UMA vez:
#
#   SSH_ALLOWED_FROM=203.0.113.10/32 DEPLOY_USER=v4 DEPLOY_PUBKEY="ssh-ed25519 AAAA..." \
#     bash infra/vps/provisionar.sh
#
# Resultado: atualizações automáticas de segurança, firewall só 80/443 (+SSH restrito),
# SSH só por chave e sem root, fail2ban, Docker oficial com rotação de logs, usuário de
# deploy sem privilégios de root e crons de backup/monitoração.
set -euo pipefail
: "${DEPLOY_USER:=v4}"
: "${DEPLOY_PUBKEY:?informe a chave pública SSH do usuário de deploy}"
: "${SSH_ALLOWED_FROM:?informe o IP/rede autorizado para SSH (ex.: 203.0.113.10/32)}"
APP_DIR="${APP_DIR:-/opt/v4-insights}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg ufw fail2ban unattended-upgrades gpg rclone git

# Atualizações automáticas de segurança
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'CONF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
CONF
systemctl enable --now unattended-upgrades

# Usuário de deploy (sem senha, só chave)
id "$DEPLOY_USER" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "$DEPLOY_USER"
install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
echo "$DEPLOY_PUBKEY" > "/home/$DEPLOY_USER/.ssh/authorized_keys"
chown "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh/authorized_keys"
chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"

# SSH: só chave, sem root
cat > /etc/ssh/sshd_config.d/10-v4.conf <<'CONF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
CONF
systemctl reload ssh || systemctl reload sshd

# Firewall: 80/443 públicos; SSH apenas da origem autorizada
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw allow from "$SSH_ALLOWED_FROM" to any port 22 proto tcp
ufw --force enable
systemctl enable --now fail2ban

# Docker oficial + rotação de logs. Atenção: portas publicadas pelo Docker ignoram o ufw —
# por isso o compose só publica 80/443 (proxy); banco e Redis ficam na rede interna.
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  . /etc/os-release
  curl -fsSL "https://download.docker.com/linux/$ID/gpg" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$ID $VERSION_CODENAME stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi
cat > /etc/docker/daemon.json <<'CONF'
{ "log-driver": "json-file", "log-opts": { "max-size": "20m", "max-file": "5" }, "live-restore": true }
CONF
systemctl restart docker
usermod -aG docker "$DEPLOY_USER"

# Diretórios da aplicação e segredos de backup (fora do repositório)
install -d -m 750 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$APP_DIR" /etc/v4insights
[ -f /etc/v4insights/backup.pass ] || { head -c 48 /dev/urandom | base64 > /etc/v4insights/backup.pass; }
chown "$DEPLOY_USER:$DEPLOY_USER" /etc/v4insights/backup.pass
chmod 600 /etc/v4insights/backup.pass

# Rotinas: backup diário 03:15 UTC e monitoração a cada 10 min
cat > /etc/cron.d/v4-insights <<CONF
15 3 * * * $DEPLOY_USER $APP_DIR/infra/backup/backup.sh >> /var/log/v4-backup.log 2>&1
*/10 * * * * $DEPLOY_USER $APP_DIR/infra/monitor/verificar.sh >> /var/log/v4-monitor.log 2>&1
CONF
touch /var/log/v4-backup.log /var/log/v4-monitor.log
chown "$DEPLOY_USER" /var/log/v4-backup.log /var/log/v4-monitor.log

echo "Provisionamento concluído. Próximos passos (como $DEPLOY_USER):"
echo "  git clone <repo> $APP_DIR && cd $APP_DIR && cp .env.example .env  # preencher"
echo "  docker compose up --build -d && docker compose run --rm api python -m app.cli criar-admin ..."
echo "  Copie /etc/v4insights/backup.pass para o cofre da equipe."

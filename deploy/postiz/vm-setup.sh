#!/usr/bin/env bash
# Oracle Cloud Always Free VM (Ubuntu 24.04, VM.Standard.A1.Flex 2 OCPU / 12 GB). Run as the ubuntu user.
set -euo pipefail

sudo apt-get update -y && sudo apt-get install -y ca-certificates curl git ufw
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"

# Oracle images ship iptables rules that block 80/443 even when the VCN security list allows them.
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save 2>/dev/null || true

# DuckDNS updater (free HTTPS name). Set DUCK_DOMAIN / DUCK_TOKEN first.
: "${DUCK_DOMAIN:?set DUCK_DOMAIN (sub-domain only)}"; : "${DUCK_TOKEN:?set DUCK_TOKEN}"
mkdir -p ~/duckdns
cat > ~/duckdns/duck.sh <<EOF
echo url="https://www.duckdns.org/update?domains=${DUCK_DOMAIN}&token=${DUCK_TOKEN}&ip=" | curl -k -o ~/duckdns/duck.log -K -
EOF
chmod 700 ~/duckdns/duck.sh && ~/duckdns/duck.sh
( crontab -l 2>/dev/null; echo "*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1" ) | crontab -

mkdir -p ~/postiz && cd ~/postiz
echo "Now: copy deploy/postiz/{docker-compose.yaml,Caddyfile,.env.example} here, cp .env.example .env, fill it, then:"
echo "  docker compose pull && docker compose up -d && docker compose logs -f postiz"
echo "Then re-login (docker group), open https://${DUCK_DOMAIN}.duckdns.org, create the account, connect networks."

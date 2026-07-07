#!/bin/bash
# 白名单:币安 API + Telegram Bot API + PyPI + GitHub + Anthropic
set -euo pipefail
ALLOWED_DOMAINS=(
    "fapi.binance.com" "api.binance.com" "data.binance.vision"
    "s3.ap-northeast-1.amazonaws.com"
    "api.telegram.org"
    "pypi.org" "files.pythonhosted.org"
    "registry.npmjs.org" "*.npmjs.org"
    "github.com" "api.github.com" "*.githubusercontent.com"
    "api.anthropic.com"
)
echo "[firewall] 重置..."
iptables -F; iptables -X 2>/dev/null || true; ipset destroy allowed 2>/dev/null || true
iptables -A INPUT -i lo -j ACCEPT; iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT; iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
ipset create allowed hash:ip
for d in "${ALLOWED_DOMAINS[@]}"; do
  ips=$(dig +short A "$d" 2>/dev/null | grep -E '^[0-9.]+$' || true)
  [ -z "$ips" ] && { echo "[firewall] 跳过 $d"; continue; }
  for ip in $ips; do ipset add allowed "$ip" 2>/dev/null || true; done
done
iptables -A OUTPUT -m set --match-set allowed dst -j ACCEPT
iptables -P INPUT DROP; iptables -P OUTPUT DROP; iptables -P FORWARD DROP
echo "[firewall] 就绪,放行 ${#ALLOWED_DOMAINS[@]} 个域名"

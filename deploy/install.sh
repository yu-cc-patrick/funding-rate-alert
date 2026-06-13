#!/usr/bin/env bash
# 一键部署到非美区 Linux 服务器(Ubuntu/Debian, 需 root 或 sudo)
# 用法: sudo bash install.sh
set -euo pipefail

APP_DIR=/opt/funding-rate-alert
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> 1. 检查 python3"
if ! command -v python3 >/dev/null 2>&1; then
  echo "安装 python3 ..."
  apt-get update -qq && apt-get install -y -qq python3
fi
python3 --version

echo "==> 2. 复制程序到 $APP_DIR"
mkdir -p "$APP_DIR"
cp "$SRC_DIR/monitor.py" "$APP_DIR/monitor.py"

echo "==> 3. 检查 .env"
if [[ ! -f "$APP_DIR/.env" ]]; then
  if [[ -f "$SRC_DIR/.env" ]]; then
    cp "$SRC_DIR/.env" "$APP_DIR/.env"
    echo "已从源目录复制 .env"
  else
    cp "$SRC_DIR/.env.example" "$APP_DIR/.env"
    echo "!! 已生成 $APP_DIR/.env 模板, 请填入 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID 后重跑本脚本"
    chmod 600 "$APP_DIR/.env"
    exit 1
  fi
fi
chmod 600 "$APP_DIR/.env"

echo "==> 4. 验证地域(币安是否可达)"
CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "https://fapi.binance.com/fapi/v1/time" || echo ERR)
if [[ "$CODE" != "200" ]]; then
  echo "!! 警告: 访问 fapi.binance.com 返回 $CODE (200 才正常)。"
  echo "   451 = 该服务器在被封锁地区(如美国), 请换非美区机器。"
  echo "   仍继续安装, 但脚本会拿不到数据。"
fi

echo "==> 5. 安装 systemd service + timer"
cp "$SRC_DIR/deploy/funding-alert.service" /etc/systemd/system/funding-alert.service
cp "$SRC_DIR/deploy/funding-alert.timer"   /etc/systemd/system/funding-alert.timer
systemctl daemon-reload
systemctl enable --now funding-alert.timer

echo "==> 6. 立即跑一次(首次只建基线, 不推送)"
systemctl start funding-alert.service || true
sleep 2
journalctl -u funding-alert.service -n 20 --no-pager || true

echo ""
echo "==> 完成! 常用命令:"
echo "   查看下次运行:   systemctl list-timers funding-alert.timer"
echo "   看最近日志:     journalctl -u funding-alert.service -n 50 --no-pager"
echo "   手动跑一次:     systemctl start funding-alert.service"
echo "   停止:           systemctl disable --now funding-alert.timer"

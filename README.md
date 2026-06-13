# 币安资金费率预警 → Telegram

监控**全部币安 U 本位永续合约**,出现以下情况推送 Telegram(仅在状态切换时推一次,不刷屏):

1. **结算周期变化** —— 币安在市场极端时会把资金费率结算周期从 8h/4h 缩短到 **1h**。
   - 正常 → 1h:推送「进入极端状态」
   - 1h → 恢复:推送「恢复正常」
2. **费率绝对值 > 1%** —— 无论周期多少,`|fundingRate|` 跨越 ±1% 时推送(回落时也提醒)。

只发 Telegram,不发邮件。

## ⚠️ 必须用非美区服务器

币安合约接口 (`fapi.binance.com`) **封锁美国 IP(返回 451)**。GitHub Actions 免费 runner 在美区,拿不到数据,因此**不能用 GitHub Actions**,必须跑在非美区服务器上。

推荐 **Oracle Cloud 永久免费机**(注册时区域选东京/大阪/新加坡/首尔等,ARM 实例永久免费):
- 注册:https://www.oracle.com/cloud/free/
- 创建一台 Ubuntu 实例,记下公网 IP 和 SSH key

其他非美区的便宜小鸡(搬瓦工日本/新加坡、Vultr 东京等)也行。

## 部署(在服务器上)

```bash
# 1. 把项目传到服务器(在本地执行)
scp -r funding-rate-alert ubuntu@<服务器IP>:~/

# 2. SSH 登录服务器
ssh ubuntu@<服务器IP>

# 3. 填配置
cd ~/funding-rate-alert
cp .env.example .env
nano .env          # 填入 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID

# 4. 一键安装(装 systemd 定时器, 每5分钟跑一次)
sudo bash deploy/install.sh
```

安装脚本会:校验币安是否可达(非 200 会警告)、装好 systemd service+timer、立即跑一次建立基线。

## 常用命令

```bash
systemctl list-timers funding-alert.timer            # 看下次运行时间
journalctl -u funding-alert.service -n 50 --no-pager # 看日志
systemctl start funding-alert.service                # 手动跑一次
systemctl disable --now funding-alert.timer          # 停止
```

## 工作原理

- systemd timer 每 5 分钟运行 `monitor.py`(开机补跑错过的任务)。
- 拉 `/fapi/v1/premiumIndex`(当前费率)和 `/fapi/v1/fundingInfo`(被调整过的结算周期)。
- 与上一轮的 `state.json` 对比,只在状态切换时推送。
- **首次运行**只建基线,不会把存量极端币种全推一遍。

## 调整参数

`monitor.py` 顶部:
- `RATE_THRESHOLD = 0.01` —— 费率阈值(1%)
- `EXTREME_INTERVAL_HOURS = 1` —— 多少小时周期算极端

运行间隔在 `deploy/funding-alert.timer` 的 `OnUnitActiveSec=5min`。

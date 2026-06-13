# 币安资金费率预警 → Telegram

监控**全部币安 U 本位永续合约**,出现以下情况推送 Telegram(仅在状态切换时推一次,不刷屏):

1. **结算周期变化** —— 币安在市场极端时会把资金费率结算周期从 8h/4h 缩短到 **1h**。
   - 正常 → 1h:推送「进入极端状态」
   - 1h → 恢复:推送「恢复正常」
2. **费率绝对值 > 1%** —— 无论周期多少,`|fundingRate|` 跨越 ±1% 时推送(回落时也提醒)。

只发 Telegram,不发邮件。完全免费,跑在 GitHub Actions 上,电脑关机不影响。

## 架构(为什么需要 relay)

币安合约接口封锁美国 IP(返回 **451**),而 GitHub Actions 免费 runner 在美区。
所以加一个**非美区的轻量中转(relay)**:GitHub Actions 照常每 5 分钟跑,
把请币安的请求转发给部署在新加坡区的 relay,由它代为访问币安。

```
GitHub Actions (美区, 每5分钟)
      │  GET <relay>/fapi/v1/premiumIndex
      ▼
Render 新加坡 relay  ──→  fapi.binance.com (可达)
```

relay 用 Render 免费套餐,GitHub 登录即可部署,**无需信用卡、无需 SSH**。

## 部署步骤

### 1. 先把仓库推到 GitHub(已完成)
仓库:`yu-cc-patrick/funding-rate-alert`(私有)

### 2. 部署 relay 到 Render
1. 打开 https://render.com,用 GitHub 登录。
2. New → **Blueprint**,选这个仓库,Render 会读取 `render.yaml` 自动建一个新加坡区 Web Service。
3. 部署时它会要你填 `RELAY_TOKEN`——填一个随机字符串(自己设,比如 32 位随机串),记下来。
4. 部署完成后拿到服务地址,形如 `https://binance-relay-xxxx.onrender.com`。
5. 浏览器访问 `<地址>/fapi/v1/time`,带不带 token 测一下能否返回币安时间。

> Render 免费 Web Service 闲置 15 分钟会休眠,被请求时自动唤醒(冷启动几十秒)。
> 每 5 分钟一次的定时请求基本能让它保持活跃;偶尔冷启动会让某一轮慢一点,不影响结果。

### 3. 配置 GitHub Secrets
仓库 → Settings → Secrets and variables → Actions,加 4 条:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `BINANCE_BASE` = relay 地址(如 `https://binance-relay-xxxx.onrender.com`)
- `RELAY_TOKEN` = 第 2 步设的随机串

### 4. 跑起来
Actions 页面 → funding-rate-alert → **Run workflow**。
首次运行只建基线(不推送),之后每 5 分钟按变化推送。

## 调整参数
`monitor.py` 顶部:
- `RATE_THRESHOLD = 0.01` —— 费率阈值(1%)
- `EXTREME_INTERVAL_HOURS = 1` —— 多少小时周期算极端

cron 间隔在 `.github/workflows/monitor.yml` 的 `*/5 * * * *`。

## 本地直连(可选)
若你在非美区网络,可不经 relay 直接跑:
```bash
export TELEGRAM_BOT_TOKEN=xxx TELEGRAM_CHAT_ID=xxx
python3 monitor.py     # 默认直连 fapi.binance.com
```

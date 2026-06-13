# 币安资金费率预警 → Telegram

监控**全部币安 U 本位永续合约**,出现以下情况时推送到 Telegram(仅在状态切换时推一次,不刷屏):

1. **结算周期变化** —— 币安在市场极端时会把资金费率结算周期从 8h/4h 缩短到 **1h**。
   - 正常 → 1h:推送「进入极端状态」
   - 1h → 恢复:推送「恢复正常」
2. **费率绝对值 > 1%** —— 无论周期多少,`|fundingRate|` 跨越 ±1% 时推送(回落时也提醒)。

只发 Telegram,不发邮件。完全免费,跑在 GitHub Actions 上,电脑关机不影响。

## 工作原理

- 每 5 分钟由 GitHub Actions 定时触发 `monitor.py`。
- 拉取 `/fapi/v1/premiumIndex`(当前费率)和 `/fapi/v1/fundingInfo`(被调整过的结算周期)。
- 与上一轮的 `state.json` 对比,只在状态切换时推送,然后把新状态提交回仓库。
- **首次运行**只建立基线,不会把存量极端币种全推一遍。

## 部署步骤

### 1. 建 Telegram Bot
1. Telegram 里找 [@BotFather](https://t.me/BotFather),发 `/newbot`,按提示拿到 **Bot Token**。
2. 拿 **Chat ID**:给你的 bot 随便发一条消息,然后浏览器打开
   `https://api.telegram.org/bot<你的TOKEN>/getUpdates`,在返回里找 `"chat":{"id":...}`。

### 2. 建仓库并上传
```bash
cd /Users/cr/funding-rate-alert
git init
git add .
git commit -m "init: funding rate alert"
gh repo create funding-rate-alert --private --source=. --push
# 或者手动在 GitHub 建仓库后 git remote add origin ... && git push
```

### 3. 配置 Secrets
仓库 → Settings → Secrets and variables → Actions → New repository secret,加两条:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### 4. 启用 Actions
- 仓库 → Actions 标签页,如提示则点启用。
- 可在 Actions 里点 **Run workflow** 手动跑一次,第一次只建基线(不推送),第二次起才会按变化推送。

## 本地测试(可选)
```bash
export TELEGRAM_BOT_TOKEN=xxx
export TELEGRAM_CHAT_ID=xxx
python3 monitor.py
```
> 注意:部分地区(如美国)无法直接访问 `fapi.binance.com`。GitHub Actions 的 runner 在可访问区域,正常工作;本地测试若拉取失败属网络限制,非代码问题。

## 调整参数
在 `monitor.py` 顶部:
- `RATE_THRESHOLD = 0.01` —— 费率阈值(1%)
- `EXTREME_INTERVAL_HOURS = 1` —— 多少小时周期算极端

cron 间隔在 `.github/workflows/monitor.yml` 的 `*/5 * * * *`。

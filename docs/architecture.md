# 系统结构与数据流

## 一句话

监控币安全部 U 本位永续合约的资金费率,出现极端情况时推送 Telegram。

## 组件

| 组件 | 位置 | 作用 |
|------|------|------|
| 监控脚本 | `monitor.py` | 拉取费率、对比状态、推送预警 |
| 定时器 | `.github/workflows/monitor.yml` | GitHub Actions cron,每 5 分钟触发 |
| 中转 relay | `relay/server.py` | 部署在非美区,转发请求绕过币安美区封锁 |
| relay 部署配置 | `render.yaml` | Render 蓝图,新加坡区免费服务 |
| 状态文件 | `state.json` | 每个币种的"极端/超标"状态,由 Actions 提交回仓库 |

## 数据流

```
GitHub Actions runner (美区, 每 5 分钟)
   │  GET <BINANCE_BASE>/fapi/v1/premiumIndex   (当前费率)
   │  GET <BINANCE_BASE>/fapi/v1/fundingInfo    (被调整的结算周期)
   │  header: X-Relay-Token
   ▼
Render relay (新加坡)  ──────►  fapi.binance.com (可达, 非美区)
   │                            ◄──────  JSON 响应
   ▼
monitor.py
   │  1. 解析: {symbol: {rate, interval}}
   │  2. 读 state.json (上一轮状态)
   │  3. 对比, 找出"状态切换"的币种
   │  4. 切换的才推 Telegram
   │  5. 写回 state.json
   ▼
git commit state.json  +  Telegram sendMessage
```

## 为什么需要 relay(核心设计约束)

币安合约接口对**美国 IP 返回 451**(地域封锁)。GitHub Actions 的免费 runner 全部在美区,直连必然失败。已实测:`fapi/dapi/api/api1/api-gcp.binance.com` 从 runner 全部 451;`data-api.binance.vision` 不封但只有现货、无合约接口。

因此引入一个部署在**非美区**(Render 新加坡)的轻量中转:runner 把请求发给 relay,relay 在新加坡代为访问币安。这样既保留了"免费 + GitHub Actions"的部署形态,又拿到了币安官方数据。

## 预警判定逻辑

对每个 USDT 永续合约,维护两个布尔状态,**仅在状态翻转时推送一次**(避免刷屏):

- `extreme` = 结算周期 ≤ 1h。`fundingInfo` 只返回被调过周期的币种,其余默认 8h。
  - false→true:进入极端;true→false:恢复正常
- `high` = `|fundingRate| > 1%`。
  - false→true:费率异常;true→false:费率回落

**首次运行**只建立基线、不推送,避免把存量极端币种一次性全推。

## 配置项

`monitor.py` 顶部:`RATE_THRESHOLD`(默认 0.01)、`EXTREME_INTERVAL_HOURS`(默认 1)、`DEFAULT_INTERVAL_HOURS`(默认 8)。
环境变量:`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`、`BINANCE_BASE`(relay 地址)、`RELAY_TOKEN`。

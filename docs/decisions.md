# 架构决策记录 (Decision Log)

按时间倒序,最新在上。

## 2026-06-13 — 用 relay 中转绕过币安美区封锁

**背景:** 项目要免费、云端、电脑关机不影响,首选 GitHub Actions。但实测币安所有合约域名对 GitHub runner(美区 IP)返回 451,`data-api.binance.vision` 不封却无合约接口。

**决策:** 在非美区(Render 新加坡免费区)部署一个极简 relay (`relay/server.py`),只转发 `/fapi/*` 只读接口、带 token 鉴权。GitHub Actions 通过 `BINANCE_BASE` 指向 relay。

**放弃的方案:**
- 纯 GitHub Actions 直连 —— 451,不可行。
- 换数据源(Bybit/OKX)—— 用户明确要币安官方。
- Oracle Cloud 非美区服务器 + systemd —— 用户注册失败,且需信用卡/SSH,比 relay 重。

**代价:** Render 免费服务闲置 15 分钟休眠,偶尔冷启动让某轮慢几十秒;每 5 分钟一次请求基本能保活。可接受(用户不追求时效)。

## 2026-06-13 — 状态持久化用仓库内 state.json

**决策:** 把每币种状态存 `state.json`,由 Actions 每轮 commit 回仓库,下轮读取对比。

**理由:** GitHub Actions 无状态,需要外部持久化才能实现"只在切换时推送"。仓库内文件最简单、零额外服务。首次运行无 state 视为建基线、不推送。

## 2026-06-13 — 只推 Telegram,只在状态切换时推

**决策:** 不发邮件;同一币种持续处于极端/超标时不重复推,仅在布尔状态翻转时推一次。

**理由:** 用户明确要求只要 Telegram、且避免刷屏。

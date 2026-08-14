# AI 修改记录

按时间倒序,最新在上。每条记录:改了什么、为什么。

## 2026-08-14 — 加固 relay/monitor 重试,治"每隔一段时间报错"

GHA 日志定位:失败全部在 `monitor → relay → 币安` 链路,两种错误:
- `HTTP 502`(relay 转发币安失败,币安对 Render 云 IP 偶发限流/429)
- `read timed out`(monitor 30s 超时 < relay 转发 60s,冷启动+币安慢时超时)

改动:
- **`relay/server.py`**:转发币安改为 `_fetch_upstream` 带 3 次退避重试(2s/4s),451/403 立即放弃,429/5xx 瞬时抖动在 relay 层消化,不再一次失败就 502。
- **`monitor.py`**:`http_get_json` timeout 30→90(大于 relay 的 60s),重试 3→5 次,退避改指数 2s/4s/8s/16s。

验证:py_compile 通过;mock 单测覆盖 502/429 重试、451 不重试、5 次放弃。真实链路(relay→币安→Telegram)因本机美区连不了,待 push 后 workflow_dispatch 验证。

未付费,冷启动/免费配额仍在;若之后仍偶发,再评估 Render 付费或备用 relay。

## 2026-06-13 — 项目重建与上线(v1.0.0)

用户重装系统后原代码丢失,无旧记忆,从零重写。

- **重写 `monitor.py`**:监控全部 U 本位永续,两类预警(周期变 1h / |费率|>1%),只在状态切换时推 Telegram。
- **方案演进**(详见 decisions.md):
  1. 初版纯 GitHub Actions 直连币安 → 实测 451(美区封锁),失败。
  2. 一度改为 Oracle 非美区服务器 + systemd → 用户注册失败,弃用。
  3. 定稿:GitHub Actions + Render 新加坡 relay 中转,跑通。
- **新增 `relay/server.py` + `render.yaml`**:非美区中转,绕过 451。
- **`monitor.py` 改造**:支持 `BINANCE_BASE` + `RELAY_TOKEN` 走 relay。
- **验证**:整链路跑通,首轮建立 753 币种基线;真实 Telegram 推送测试 ok=True(用临时 workflow 测完即删)。
- **收尾**:补全 docs/ 与 CLAUDE.md,打 tag v1.0.0。

**待办(安全):** 对话中暴露过 GitHub PAT、bot token、relay token,建议 revoke 重发。

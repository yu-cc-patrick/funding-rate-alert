#!/usr/bin/env python3
"""币安永续合约资金费率预警 -> Telegram

两类预警(都只在"状态切换"时推送一次,避免刷屏):
  1. 结算周期变化: 正常(8h/4h) <-> 极端(1h)
  2. 资金费率绝对值跨越 1% 阈值

在 GitHub Actions 上每 5 分钟运行一次。由于币安封锁美区 IP(451),
而 GHA runner 在美区, 因此请求经由非美区中转(relay)转发到币安。
状态持久化在 state.json, 由 GitHub Actions 提交回仓库。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

# 默认直连币安; 若设置了 BINANCE_BASE(指向非美区 relay)则走 relay
BINANCE_BASE = os.environ.get("BINANCE_BASE", "https://fapi.binance.com").rstrip("/")
RELAY_TOKEN = os.environ.get("RELAY_TOKEN", "")
RATE_THRESHOLD = 0.01          # 1%
EXTREME_INTERVAL_HOURS = 1     # 周期降到 1h 视为极端
DEFAULT_INTERVAL_HOURS = 8     # 未在 fundingInfo 中的币种默认 8h

# 状态文件放脚本同目录, 不依赖运行时的工作目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "state.json")


def _load_dotenv():
    """若同目录有 .env, 读入环境变量(不覆盖已存在的)。"""
    path = os.path.join(SCRIPT_DIR, ".env")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv()
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def http_get_json(url):
    """GET + JSON 解析，带重试，挡住 Render 冷启动和网络抖动。

    对 451/403/418 不重试——这些是 geo-block 或 bot 检测，重试无意义。
    """
    headers = {"User-Agent": "funding-alert/1.0"}
    if RELAY_TOKEN:
        headers["X-Relay-Token"] = RELAY_TOKEN
    last_err = None
    for attempt in range(1, 4):  # 最多 3 次
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_err = e
            print(f"[WARN] HTTP {e.code} (attempt {attempt}/3): {url}",
                  file=sys.stderr)
            if e.code in (451, 403, 418):
                break  # geo-block / forbidden / bot-detection，重试没用
        except Exception as e:
            last_err = e
            print(f"[WARN] {e} (attempt {attempt}/3)", file=sys.stderr)
        if attempt < 3:
            time.sleep(2.0 * attempt)  # 2s → 4s 递增退避
    raise RuntimeError(f"GET failed after 3 tries: {url}\n  {last_err}")


def fetch_market():
    """返回 {symbol: {"rate": float, "interval": int}}, 只含 USDT 永续。"""
    premium = http_get_json(f"{BINANCE_BASE}/fapi/v1/premiumIndex")
    info = http_get_json(f"{BINANCE_BASE}/fapi/v1/fundingInfo")

    # fundingInfo 只返回被调整过周期的币种, 其余默认 8h
    interval_map = {}
    for item in info:
        try:
            interval_map[item["symbol"]] = int(item["fundingIntervalHours"])
        except (KeyError, ValueError, TypeError):
            continue

    market = {}
    for item in premium:
        symbol = item.get("symbol", "")
        if not symbol.endswith("USDT"):
            continue
        raw = item.get("lastFundingRate")
        if raw in (None, ""):
            continue
        try:
            rate = float(raw)
        except (ValueError, TypeError):
            continue
        market[symbol] = {
            "rate": rate,
            "interval": interval_map.get(symbol, DEFAULT_INTERVAL_HOURS),
        }
    return market


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)


def send_telegram(text):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("[WARN] 未配置 Telegram, 跳过推送:\n" + text)
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read()


def pct(rate):
    return f"{rate * 100:+.4f}%"


def diff_and_alerts(market, prev_state):
    """对比新旧状态, 返回 (新状态, 预警消息列表)。"""
    new_state = {}
    alerts = []

    for symbol, data in market.items():
        rate = data["rate"]
        interval = data["interval"]
        is_extreme = interval <= EXTREME_INTERVAL_HOURS
        is_high = abs(rate) > RATE_THRESHOLD

        new_state[symbol] = {"extreme": is_extreme, "high": is_high}
        old = prev_state.get(symbol, {})
        old_extreme = old.get("extreme", False)
        old_high = old.get("high", False)

        # 1) 结算周期: 正常 -> 极端
        if is_extreme and not old_extreme:
            alerts.append(
                f"⚠️ <b>{symbol}</b> 进入极端状态\n"
                f"结算周期降至 <b>{interval}h</b>(当前费率 {pct(rate)})"
            )
        # 周期: 极端 -> 恢复
        elif not is_extreme and old_extreme:
            alerts.append(
                f"✅ <b>{symbol}</b> 恢复正常\n"
                f"结算周期回到 <b>{interval}h</b>(当前费率 {pct(rate)})"
            )

        # 2) 费率绝对值跨越 1% 阈值
        if is_high and not old_high:
            alerts.append(
                f"🔥 <b>{symbol}</b> 资金费率异常\n"
                f"当前 <b>{pct(rate)}</b> 超过 ±1%(周期 {interval}h)"
            )
        elif not is_high and old_high:
            alerts.append(
                f"🟢 <b>{symbol}</b> 费率回落\n"
                f"当前 <b>{pct(rate)}</b> 已回到 ±1% 以内"
            )

    return new_state, alerts


def main():
    try:
        market = fetch_market()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] 获取行情失败: {exc}", file=sys.stderr)
        sys.exit(1)

    if not market:
        print("[ERROR] 行情为空, 退出", file=sys.stderr)
        sys.exit(1)

    prev_state = load_state()
    first_run = not prev_state

    new_state, alerts = diff_and_alerts(market, prev_state)
    save_state(new_state)

    if first_run:
        # 首次运行只建立基线, 不把存量极端币种全推一遍刷屏
        print(f"[INFO] 首次运行, 已建立 {len(new_state)} 个币种基线, 不推送。")
        return

    if not alerts:
        print(f"[INFO] 共检查 {len(market)} 个币种, 无状态变化。")
        return

    for msg in alerts:
        send_telegram(msg)
    print(f"[INFO] 已推送 {len(alerts)} 条预警。")


if __name__ == "__main__":
    main()

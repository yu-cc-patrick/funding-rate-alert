#!/usr/bin/env python3
"""一次性: 抓真实费率, 给 Telegram 发一条测试消息。验证完即删。"""
import json, os, urllib.request

BASE = os.environ["BINANCE_BASE"].rstrip("/")
RTOKEN = os.environ.get("RELAY_TOKEN", "")
BOT = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT = os.environ["TELEGRAM_CHAT_ID"]


def get(path):
    h = {"User-Agent": "test/1.0"}
    if RTOKEN:
        h["X-Relay-Token"] = RTOKEN
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(BASE + path, headers=h), timeout=30).read())


prem = get("/fapi/v1/premiumIndex")
info = get("/fapi/v1/fundingInfo")
ivmap = {x["symbol"]: int(x["fundingIntervalHours"]) for x in info}

rows = []
for p in prem:
    s = p["symbol"]
    if not s.endswith("USDT"):
        continue
    try:
        r = float(p["lastFundingRate"])
    except (ValueError, TypeError):
        continue
    rows.append((abs(r), r, s, ivmap.get(s, 8)))
rows.sort(reverse=True)

top = rows[:5]
extreme = [x for x in rows if x[3] <= 1][:5]

lines = ["🧪 <b>资金费率预警 - 推送测试</b>", "", "<b>当前费率绝对值 Top5:</b>"]
for ab, r, s, iv in top:
    lines.append(f"  {s}: {r*100:+.4f}% (周期{iv}h)")
lines.append("")
if extreme:
    lines.append("<b>当前 1h 极端周期币种(部分):</b>")
    for ab, r, s, iv in extreme:
        lines.append(f"  {s}: {r*100:+.4f}%")
else:
    lines.append("当前无 1h 极端周期币种。")
lines += ["", "✅ 链路正常: GitHub Actions → 新加坡relay → 币安"]
text = "\n".join(lines)

payload = json.dumps({
    "chat_id": CHAT, "text": text,
    "parse_mode": "HTML", "disable_web_page_preview": True,
}).encode()
resp = json.loads(urllib.request.urlopen(urllib.request.Request(
    f"https://api.telegram.org/bot{BOT}/sendMessage", data=payload,
    headers={"Content-Type": "application/json"}), timeout=30).read())
print("Telegram ok =", resp.get("ok"))

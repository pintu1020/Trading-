"""
Telegram notifier — formats and sends signal alerts, plus basic
command handling (/stats, /status).
"""
import requests
import config
import database
import goldapi_client


def _api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}"


def send_message(text: str, chat_id: str = None):
    chat_id = chat_id or config.TELEGRAM_CHAT_ID
    resp = requests.post(_api_url("sendMessage"), json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }, timeout=10)
    resp.raise_for_status()
    return resp.json()


def format_signal(signal) -> str:
    direction_emoji = "📈 LONG" if signal.direction == "LONG" else "📉 SHORT"
    confidence_score = round((signal.confidence / signal.max_confidence) * 100)
    stars = "⭐" * signal.confidence + "☆" * (signal.max_confidence - signal.confidence)

    # Small entry zone band around the exact calculated entry, since real
    # fills rarely land on one exact tick.
    entry_buffer = signal.entry * 0.0015  # ~0.15% zone width
    zone_low = round(signal.entry - entry_buffer)
    zone_high = round(signal.entry + entry_buffer)

    tp_lines = "\n".join(
        f"✅ TP{i+1}: {tp}" for i, tp in enumerate(signal.take_profits)
    )
    reasons = "\n".join(f"• {r}" for r in signal.reasons)

    # Reference cross-check against an independent gold quote (GoldAPI).
    # Purely informational — omitted entirely if not configured or unreachable.
    reference_line = ""
    ref_price = goldapi_client.get_reference_price()
    if ref_price is not None:
        diff_pct = (signal.entry - ref_price) / ref_price * 100
        reference_line = (
            f"🔎 Reference spot (GoldAPI): {round(ref_price, 2)} "
            f"(bot entry is {diff_pct:+.2f}% vs. this)\n\n"
        )

    return (
        f"🚨 NEW TRADE SIGNAL 🚨\n\n"
        f"📊 Pair: XAU/USDT\n"
        f"{direction_emoji}\n\n"
        f"💰 Entry Zone:\n"
        f"• {zone_low} – {zone_high}\n\n"
        f"🎯 Take Profit:\n"
        f"{tp_lines}\n\n"
        f"🛑 Stop Loss:\n{signal.stop_loss}\n\n"
        f"⚡ Leverage:\n{signal.leverage}x (Max {signal.leverage * 2}x)\n\n"
        f"🎯 AI Confidence:\n{stars} {confidence_score}/100\n\n"
        f"⚠️ Risk:\n1–2% of your account per trade\n\n"
        f"📌 Session: {signal.session.replace('_', ' ').title()}\n\n"
        f"{reference_line}"
        f"<i>Confluence factors:</i>\n{reasons}\n\n"
        f"📌 Status:\n🟢 Signal Active\n\n"
        f"⚠️ Signal only — no auto-execution. Manage your own risk."
    )


def send_signal_alert(signal):
    send_message(format_signal(signal))


def format_stats() -> str:
    s = database.get_stats()
    expired = s.get("expired", 0)
    return (
        f"<b>Gold Signal Bot — Stats</b>\n\n"
        f"Total signals: {s['total']}\n"
        f"Wins: {s['wins']}  Losses: {s['losses']}  Open: {s['open']}  Expired: {expired}\n"
        f"Win rate (closed trades): {s['win_rate']}%"
    )

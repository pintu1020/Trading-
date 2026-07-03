"""
Telegram notifier — formats and sends signal alerts, plus basic
command handling (/stats, /status).
"""
import requests
import config
import database


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
    arrow = "🟢 LONG" if signal.direction == "LONG" else "🔴 SHORT"
    confidence_bar = "★" * signal.confidence + "☆" * (signal.max_confidence - signal.confidence)

    tp_lines = "\n".join(
        f"  TP{i+1}: <b>{tp}</b>" for i, tp in enumerate(signal.take_profits)
    )
    reasons = "\n".join(f"• {r}" for r in signal.reasons)

    return (
        f"<b>XAU/USDT Signal — {arrow}</b>\n\n"
        f"Entry: <b>{signal.entry}</b>\n"
        f"Stop Loss: <b>{signal.stop_loss}</b>\n"
        f"{tp_lines}\n\n"
        f"Suggested Leverage: <b>{signal.leverage}x</b>\n"
        f"Confidence: {confidence_bar} ({signal.confidence}/{signal.max_confidence})\n"
        f"Session: {signal.session.replace('_', ' ').title()}\n\n"
        f"<i>Confluence factors:</i>\n{reasons}\n\n"
        f"⚠️ Signal only — no auto-execution. Manage your own risk."
    )


def send_signal_alert(signal):
    send_message(format_signal(signal))


def format_stats() -> str:
    s = database.get_stats()
    return (
        f"<b>Gold Signal Bot — Stats</b>\n\n"
        f"Total signals: {s['total']}\n"
        f"Wins: {s['wins']}  Losses: {s['losses']}  Open: {s['open']}\n"
        f"Win rate (closed trades): {s['win_rate']}%"
    )

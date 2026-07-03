"""
Main loop — polls Bitget candles, evaluates signal engine, enforces
frequency/discipline rules, and pushes Telegram alerts.

Also runs a lightweight long-polling Telegram command handler in the
same process for /stats and /status.
"""
import time
import logging
import threading
import requests
from datetime import datetime, timezone

import config
import database
from bitget_client import BitgetClient
from signal_engine import evaluate
from news_filter import is_news_blackout
import telegram_notifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("gold-signal-bot")

client = BitgetClient()


def can_send_signal() -> bool:
    if database.signals_today_count() >= config.MAX_SIGNALS_PER_DAY:
        log.info("Daily signal cap reached, skipping.")
        return False

    last_ts = database.last_signal_time()
    if last_ts:
        last_dt = datetime.fromisoformat(last_ts)
        elapsed_min = (datetime.now(timezone.utc) - last_dt).total_seconds() / 60
        if elapsed_min < config.MIN_MINUTES_BETWEEN_SIGNALS:
            log.info("Cooldown active (%.1f min elapsed), skipping.", elapsed_min)
            return False

    blackout, event_name = is_news_blackout()
    if blackout:
        log.info("News blackout active (%s), skipping.", event_name)
        return False

    return True


def run_signal_loop():
    database.init_db()
    log.info("Gold signal bot started. Symbol=%s", config.SYMBOL)
    while True:
        try:
            candles_4h = client.get_candles(config.TREND_TIMEFRAME, limit=250)
            candles_1h = client.get_candles(config.TRIGGER_TIMEFRAME, limit=60)

            signal = evaluate(candles_4h, candles_1h)
            if signal and can_send_signal():
                signal_id = database.save_signal(signal)
                telegram_notifier.send_signal_alert(signal)
                log.info("Signal #%d sent: %s @ %s (confidence %d/%d)",
                          signal_id, signal.direction, signal.entry,
                          signal.confidence, signal.max_confidence)
            elif signal:
                log.info("Signal detected but suppressed by frequency/news rules.")
            else:
                log.info("No confluence — no signal this cycle.")

        except Exception as e:
            log.error("Error in signal loop: %s", e)

        time.sleep(config.POLL_INTERVAL_SECONDS)


def run_command_listener():
    """Simple long-polling handler for /stats and /status commands."""
    offset = None
    base_url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
            resp = requests.get(f"{base_url}/getUpdates", params=params, timeout=35)
            updates = resp.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message", {})
                text = message.get("text", "")
                chat_id = str(message.get("chat", {}).get("id", ""))

                if text == "/stats":
                    telegram_notifier.send_message(telegram_notifier.format_stats(), chat_id)
                elif text == "/status":
                    today_count = database.signals_today_count()
                    telegram_notifier.send_message(
                        f"Bot is running.\nSignals today: {today_count}/{config.MAX_SIGNALS_PER_DAY}",
                        chat_id,
                    )
        except Exception as e:
            log.error("Error in command listener: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    t = threading.Thread(target=run_command_listener, daemon=True)
    t.start()
    run_signal_loop()

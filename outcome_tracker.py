"""
Outcome tracker — periodically checks open signals against actual price
action (via 1H candle highs/lows since signal creation) to determine
whether TP1 or SL was hit first. This is what makes /stats real instead
of permanently empty.

Win/loss definition: a signal is scored a WIN if price reaches TP1
before touching the stop loss. TP2/TP3 are tracked as bonus info but
don't change the win/loss classification — TP1 is the meaningful bar
since real trading involves partial exits there.
"""
import logging
from datetime import datetime, timezone
import database
import telegram_notifier
import adaptive_learning
from bitget_client import BitgetClient

log = logging.getLogger("outcome-tracker")
client = BitgetClient()

CHECK_TIMEFRAME = "1H"
MAX_SIGNAL_AGE_HOURS = 72  # auto-close stale signals that never resolved


def _candles_since(candles, created_at_iso):
    created_ts = int(datetime.fromisoformat(created_at_iso).timestamp() * 1000)
    return [c for c in candles if c["ts"] >= created_ts]


def _evaluate_signal(signal: dict, candles: list):
    """
    Scans candles chronologically. Returns (outcome, exit_price, tp_hits)
    or (None, None, tp_hits) if still unresolved.
    tp_hits is a dict like {1: True, 2: False, 3: False}.
    """
    direction = signal["direction"]
    sl = signal["stop_loss"]
    tps = {1: signal["tp1"], 2: signal["tp2"], 3: signal["tp3"]}
    tp_hits = {1: bool(signal["hit_tp1"]), 2: bool(signal["hit_tp2"]), 3: bool(signal["hit_tp3"])}

    for c in candles:
        if direction == "LONG":
            sl_hit = c["low"] <= sl
            tp1_hit = c["high"] >= tps[1]
        else:
            sl_hit = c["high"] >= sl
            tp1_hit = c["low"] <= tps[1]

        # Update bonus TP2/TP3 flags regardless of final outcome
        for tier in (2, 3):
            if not tp_hits[tier]:
                if direction == "LONG" and c["high"] >= tps[tier]:
                    tp_hits[tier] = True
                elif direction == "SHORT" and c["low"] <= tps[tier]:
                    tp_hits[tier] = True

        if sl_hit and not tp_hits[1]:
            return "loss", sl, tp_hits
        if tp1_hit:
            tp_hits[1] = True
            return "win", tps[1], tp_hits

    return None, None, tp_hits


def check_open_signals():
    open_signals = database.get_open_signals()
    if not open_signals:
        return

    candles = client.get_candles(CHECK_TIMEFRAME, limit=200)

    for signal in open_signals:
        relevant_candles = _candles_since(candles, signal["created_at"])
        if not relevant_candles:
            continue

        outcome, exit_price, tp_hits = _evaluate_signal(signal, relevant_candles)

        for tier, hit in tp_hits.items():
            if hit and not signal[f"hit_tp{tier}"]:
                database.mark_tp_hit(signal["id"], tier)

        if outcome:
            database.close_signal(signal["id"], outcome, exit_price)
            log.info("Signal #%d closed as %s @ %.2f", signal["id"], outcome, exit_price)
            telegram_notifier.send_message(
                f"{'✅' if outcome == 'win' else '❌'} Signal #{signal['id']} "
                f"({signal['direction']}) closed: <b>{outcome.upper()}</b> @ {exit_price}"
            )
            learning_msg = adaptive_learning.record_outcome(signal["session"], outcome)
            if learning_msg:
                telegram_notifier.send_message(learning_msg)
                log.info(learning_msg)
            continue

        # Auto-close stale signals that never resolved either way
        created_dt = datetime.fromisoformat(signal["created_at"])
        age_hours = (datetime.now(timezone.utc) - created_dt).total_seconds() / 3600
        if age_hours > MAX_SIGNAL_AGE_HOURS:
            database.close_signal(signal["id"], "expired", None)
            log.info("Signal #%d auto-expired after %.0fh unresolved", signal["id"], age_hours)

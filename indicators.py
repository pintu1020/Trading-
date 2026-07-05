"""
Technical indicators — pure functions over lists of candle dicts.
No external TA library dependency, keeps deployment lightweight.
"""
from typing import List, Dict


def closes(candles: List[Dict]) -> List[float]:
    return [c["close"] for c in candles]


def ema(values: List[float], period: int) -> List[float]:
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    ema_vals = [sum(values[:period]) / period]
    for price in values[period:]:
        ema_vals.append(price * k + ema_vals[-1] * (1 - k))
    return ema_vals


def rsi(values: List[float], period: int = 14) -> List[float]:
    if len(values) < period + 1:
        return []
    gains, losses = [], []
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsis = []
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else float("inf")
        rsis.append(100 - (100 / (1 + rs)))
    return rsis


def atr(candles: List[Dict], period: int = 14) -> List[float]:
    if len(candles) < period + 1:
        return []
    trs = []
    for i in range(1, len(candles)):
        h, l, prev_c = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)

    atrs = [sum(trs[:period]) / period]
    for tr in trs[period:]:
        atrs.append((atrs[-1] * (period - 1) + tr) / period)
    return atrs


def avg_volume(candles: List[Dict], period: int) -> float:
    vols = [c["volume"] for c in candles[-period:]]
    return sum(vols) / len(vols) if vols else 0.0


def bollinger_bandwidth(values: List[float], period: int = 20, std_dev: float = 2.0) -> List[float]:
    """
    Returns bandwidth = (upper - lower) / middle for each point where a full
    window is available. A narrow, shrinking bandwidth signals a squeeze/chop
    regime; a wide, expanding bandwidth signals a trending regime.
    """
    if len(values) < period:
        return []
    bandwidths = []
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        mean = sum(window) / period
        variance = sum((v - mean) ** 2 for v in window) / period
        stdev = variance ** 0.5
        upper = mean + std_dev * stdev
        lower = mean - std_dev * stdev
        bandwidths.append((upper - lower) / mean if mean else 0.0)
    return bandwidths


def detect_breakout(candles: List[Dict], lookback: int) -> str:
    """
    Returns 'up', 'down', or 'none' — whether the latest close broke
    above the recent high or below the recent low (excluding current candle).
    """
    if len(candles) < lookback + 1:
        return "none"
    window = candles[-(lookback + 1):-1]
    recent_high = max(c["high"] for c in window)
    recent_low = min(c["low"] for c in window)
    last_close = candles[-1]["close"]

    if last_close > recent_high:
        return "up"
    if last_close < recent_low:
        return "down"
    return "none"


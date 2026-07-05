"""
Signal engine — combines trend, momentum, structure, and volume across
two timeframes into a graded confluence signal. This is the "professional
discretion" layer: no single indicator ever fires a signal alone.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict
import indicators as ind
import session_utils
import volatility_regime
import dxy_filter
import config

try:
    import adaptive_learning
    HAS_ADAPTIVE = True
except ImportError:
    HAS_ADAPTIVE = False


@dataclass
class Signal:
    direction: str          # "LONG" or "SHORT"
    entry: float
    stop_loss: float
    take_profits: List[float]
    leverage: int
    confidence: int         # factors aligned, e.g. 3 or 4
    max_confidence: int
    session: str
    reasons: List[str]


def _trend_bias(closes_4h: List[float]) -> Optional[str]:
    ema_fast = ind.ema(closes_4h, config.EMA_FAST)
    ema_slow = ind.ema(closes_4h, config.EMA_SLOW)
    if not ema_fast or not ema_slow:
        return None
    if ema_fast[-1] > ema_slow[-1]:
        return "up"
    if ema_fast[-1] < ema_slow[-1]:
        return "down"
    return None


def _momentum_ok(closes_1h: List[float], direction: str) -> bool:
    rsi_vals = ind.rsi(closes_1h, config.RSI_PERIOD)
    if not rsi_vals:
        return False
    latest_rsi = rsi_vals[-1]
    if direction == "up":
        return latest_rsi < config.RSI_OVERBOUGHT and latest_rsi > 45
    else:
        return latest_rsi > config.RSI_OVERSOLD and latest_rsi < 55


def _volume_confirms(candles_1h: List[Dict]) -> bool:
    if len(candles_1h) < config.BREAKOUT_LOOKBACK:
        return False
    avg_vol = ind.avg_volume(candles_1h[:-1], config.BREAKOUT_LOOKBACK)
    latest_vol = candles_1h[-1]["volume"]
    return avg_vol > 0 and latest_vol >= avg_vol * config.VOLUME_SPIKE_MULTIPLIER


def evaluate(candles_4h: List[Dict], candles_1h: List[Dict]) -> Optional[Signal]:
    """
    Returns a Signal if confluence threshold is met, else None.
    """
    closes_4h = ind.closes(candles_4h)
    closes_1h = ind.closes(candles_1h)

    trend = _trend_bias(closes_4h)
    if trend is None:
        return None
    direction = "LONG" if trend == "up" else "SHORT"

    breakout = ind.detect_breakout(candles_1h, config.BREAKOUT_LOOKBACK)
    momentum_ok = _momentum_ok(closes_1h, trend)
    volume_ok = _volume_confirms(candles_1h)
    structure_ok = (trend == "up" and breakout == "up") or (trend == "down" and breakout == "down")

    factors_met = sum([True, momentum_ok, volume_ok, structure_ok])  # trend always counted (1)
    reasons = ["4H trend aligned"]
    if momentum_ok:
        reasons.append("RSI confirms momentum without exhaustion")
    if volume_ok:
        reasons.append("Volume spike confirms conviction")
    if structure_ok:
        reasons.append("1H breakout confirms structure")

    session = session_utils.current_session()
    if HAS_ADAPTIVE:
        required = adaptive_learning.effective_min_confluence(session)
    else:
        required = (
            config.MAX_CONFLUENCE
            if (config.LOW_LIQUIDITY_MUTE and session in ("asian", "off_hours"))
            else config.MIN_CONFLUENCE
        )

    # Volatility regime — in a choppy/squeezed market, most breakouts are
    # fakeouts, so require full confluence instead of the normal minimum.
    choppy = volatility_regime.is_choppy(candles_1h)
    if choppy:
        required = max(required, config.MAX_CONFLUENCE)

    # DXY correlation — gold and the dollar are normally inversely correlated.
    # If DXY is trending the SAME direction as this gold signal, that's a
    # sign something unusual is happening (correlation breakdown), so
    # require full confluence. If DXY confirms the normal inverse
    # relationship, add it as a supporting reason. Fails open if DXY data
    # is unavailable — never blocks a signal due to a missing data point.
    dxy_trend = dxy_filter.get_dxy_trend()
    if dxy_trend in ("up", "down"):
        expected_inverse = "down" if direction == "LONG" else "up"
        if dxy_trend == expected_inverse:
            reasons.append("DXY confirms normal inverse correlation with gold")
        else:
            required = max(required, config.MAX_CONFLUENCE)

    import logging
    logging.getLogger("signal-engine").info(
        "Factor check — trend:%s momentum:%s volume:%s structure:%s "
        "(met %d/%d, need %d, session:%s, choppy:%s, dxy:%s)",
        trend, momentum_ok, volume_ok, structure_ok, factors_met,
        config.MAX_CONFLUENCE, required, session, choppy, dxy_trend
    )

    if factors_met < required:
        return None

    atr_vals = ind.atr(candles_1h, config.ATR_PERIOD)
    if not atr_vals:
        return None
    latest_atr = atr_vals[-1]
    entry = closes_1h[-1]
    atr_pct = (latest_atr / entry) * 100

    sl_distance = latest_atr * config.ATR_SL_MULTIPLIER

    if direction == "LONG":
        stop_loss = entry - sl_distance
        take_profits = [entry + sl_distance * rr for rr in config.TP_RR_TIERS]
    else:
        stop_loss = entry + sl_distance
        take_profits = [entry - sl_distance * rr for rr in config.TP_RR_TIERS]

    leverage = (
        config.HIGH_VOL_LEVERAGE
        if atr_pct >= config.HIGH_VOL_ATR_PCT_THRESHOLD
        else config.BASE_LEVERAGE
    )

    return Signal(
        direction=direction,
        entry=round(entry, 2),
        stop_loss=round(stop_loss, 2),
        take_profits=[round(tp, 2) for tp in take_profits],
        leverage=leverage,
        confidence=factors_met,
        max_confidence=config.MAX_CONFLUENCE,
        session=session,
        reasons=reasons,
    )

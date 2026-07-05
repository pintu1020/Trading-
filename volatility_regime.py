"""
Volatility regime detection — uses Bollinger Band bandwidth to tell whether
the market is trending (wide, expanding bands) or choppy/range-bound
(narrow, squeezed bands). Most false breakout signals happen during chop,
so this is used to require stricter confluence in those conditions.
"""
from typing import List, Dict
import indicators as ind

BB_PERIOD = 20
BB_STD_DEV = 2.0
LOOKBACK = 50            # how much bandwidth history to judge "narrow" against
CHOPPY_PERCENTILE = 40   # current bandwidth below this percentile of recent
                         # history = squeeze/chop regime


def is_choppy(candles_1h: List[Dict]) -> bool:
    """
    Returns True if the market is currently in a low-volatility squeeze/chop
    regime relative to its own recent history. Returns False (i.e. assume
    trending, don't block) if there isn't enough data yet.
    """
    closes = ind.closes(candles_1h)
    bandwidths = ind.bollinger_bandwidth(closes, BB_PERIOD, BB_STD_DEV)

    if len(bandwidths) < LOOKBACK:
        return False

    recent = bandwidths[-LOOKBACK:]
    current = recent[-1]
    rank = sum(1 for b in recent if b < current) / len(recent) * 100
    return rank < CHOPPY_PERCENTILE

"""
DXY (US Dollar Index) trend fetcher — used to veto signals that go
against a strong dollar trend, since gold and USD are tightly inverse-
correlated.

Uses Yahoo Finance's public chart endpoint (no API key required). This
is an unofficial endpoint, so it's wrapped defensively: any failure
just disables the filter for that cycle rather than crashing the bot.
Results are cached for config.DXY_CACHE_SECONDS to avoid hammering the
endpoint every poll cycle.
"""
import time
import logging
import requests
import config

log = logging.getLogger("dxy-filter")

_cache = {"trend": None, "fetched_at": 0}

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB"


def _fetch_dxy_closes():
    resp = requests.get(
        YAHOO_URL,
        params={"interval": "1h", "range": "5d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
    return [c for c in closes if c is not None]


def get_dxy_trend():
    """
    Returns 'up', 'down', or 'flat' based on % change over the lookback
    window, or None if data couldn't be fetched (filter should be
    skipped in that case, not treated as a veto).
    """
    if not config.DXY_FILTER_ENABLED:
        return None

    now = time.time()
    if _cache["trend"] is not None and (now - _cache["fetched_at"]) < config.DXY_CACHE_SECONDS:
        return _cache["trend"]

    try:
        closes = _fetch_dxy_closes()
        if len(closes) < config.DXY_TREND_LOOKBACK + 1:
            return _cache["trend"]  # not enough data, keep stale value if any

        recent = closes[-1]
        past = closes[-(config.DXY_TREND_LOOKBACK + 1)]
        pct_change = (recent - past) / past * 100

        if pct_change >= config.DXY_STRONG_TREND_PCT:
            trend = "up"
        elif pct_change <= -config.DXY_STRONG_TREND_PCT:
            trend = "down"
        else:
            trend = "flat"

        _cache["trend"] = trend
        _cache["fetched_at"] = now
        return trend

    except Exception as e:
        log.warning("DXY fetch failed, skipping filter this cycle: %s", e)
        return _cache["trend"]  # fail open — use last known value, or None

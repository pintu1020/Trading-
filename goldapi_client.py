"""
GoldAPI.io client — used purely as a REFERENCE cross-check against the
bot's own entry price, not as the primary data source. This gives you
an at-a-glance sanity check in every signal: "does the bot's price
roughly match a real independent gold quote?"

Fails open: if GoldAPI is unreachable or the key is invalid, the
reference line is just omitted from the signal — never blocks a signal
or crashes the bot.
"""
import time
import logging
import requests
import config

log = logging.getLogger("goldapi-client")

_cache = {"price": None, "fetched_at": 0}

GOLDAPI_URL = "https://www.goldapi.io/api/XAU/USD"
CACHE_SECONDS = 60  # GoldAPI free tier is rate-limited; don't hit it every poll cycle


def get_reference_price():
    """
    Returns the latest spot gold price in USD/oz from GoldAPI, or None
    if unavailable/not configured. Cached briefly to respect rate limits.
    """
    if not config.GOLDAPI_KEY:
        return None

    now = time.time()
    if _cache["price"] is not None and (now - _cache["fetched_at"]) < CACHE_SECONDS:
        return _cache["price"]

    try:
        resp = requests.get(
            GOLDAPI_URL,
            headers={"x-access-token": config.GOLDAPI_KEY, "Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        price = float(data["price"])
        _cache["price"] = price
        _cache["fetched_at"] = now
        return price
    except Exception as e:
        log.warning("GoldAPI fetch failed, omitting reference price: %s", e)
        return _cache["price"]  # fail open — stale value or None

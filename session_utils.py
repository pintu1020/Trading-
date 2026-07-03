"""
Trading session detection (UTC-based). Gold liquidity and reliability
of technical signals is much higher during London/NY overlap.
"""
from datetime import datetime, timezone
import config


def current_session() -> str:
    hour = datetime.now(timezone.utc).hour
    lo, hi = config.SESSION_OVERLAP_LONDON_NY
    if lo <= hour < hi:
        return "london_ny_overlap"
    lo, hi = config.SESSION_LONDON
    if lo <= hour < hi:
        return "london"
    lo, hi = config.SESSION_NY
    if lo <= hour < hi:
        return "ny"
    lo, hi = config.SESSION_ASIAN
    if lo <= hour < hi:
        return "asian"
    return "off_hours"


def is_high_liquidity_session() -> bool:
    return current_session() in ("london", "ny", "london_ny_overlap")


def session_weight() -> float:
    """
    Multiplier applied to signal confidence based on session quality.
    Asian-session gold moves are thinner and more prone to fakeouts.
    """
    session = current_session()
    weights = {
        "london_ny_overlap": 1.0,
        "london": 0.9,
        "ny": 0.9,
        "asian": 0.6,
        "off_hours": 0.5,
    }
    return weights.get(session, 0.7)

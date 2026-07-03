"""
News blackout filter — mutes signals around major USD-moving events
(NFP, CPI, FOMC, PPI, retail sales, Fed speakers).

Since a free real-time economic calendar API isn't wired in, this uses
a manually-maintained schedule stored in news_events.json. Update it
weekly (Sunday night) with the coming week's high-impact USD events.
Times are UTC. Format:
[
  {"name": "NFP", "time": "2026-07-03T12:30:00Z"},
  {"name": "CPI", "time": "2026-07-10T12:30:00Z"}
]

If you later want this automated, ForexFactory's calendar or
TradingEconomics' API can populate this file on a schedule.
"""
import json
import os
from datetime import datetime, timezone, timedelta
import config

EVENTS_FILE = os.path.join(os.path.dirname(__file__), "news_events.json")


def _load_events():
    if not os.path.exists(EVENTS_FILE):
        return []
    with open(EVENTS_FILE, "r") as f:
        return json.load(f)


def is_news_blackout() -> tuple[bool, str]:
    """Returns (is_blackout, event_name_or_empty)."""
    events = _load_events()
    now = datetime.now(timezone.utc)
    before = timedelta(minutes=config.NEWS_BLACKOUT_MINUTES_BEFORE)
    after = timedelta(minutes=config.NEWS_BLACKOUT_MINUTES_AFTER)

    for ev in events:
        try:
            ev_time = datetime.fromisoformat(ev["time"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if ev_time - before <= now <= ev_time + after:
            return True, ev.get("name", "high-impact event")
    return False, ""

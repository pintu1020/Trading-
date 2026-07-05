"""
Gold (XAUT/USDT) Telegram Signal Bot — Configuration
All tunable parameters live here. Nothing else in the codebase should
hardcode thresholds.
"""
import os

# ── Bitget ────────────────────────────────────────────────────────────
BITGET_API_KEY = os.environ.get("BITGET_API_KEY", "")
BITGET_API_SECRET = os.environ.get("BITGET_API_SECRET", "")
BITGET_API_PASSPHRASE = os.environ.get("BITGET_API_PASSPHRASE", "")

SYMBOL = os.environ.get("SYMBOL", "XAUUSDT")           # tracks real gold spot index (XAU),
                                                        # NOT XAUTUSDT (Tether Gold token,
                                                        # which can drift from real gold price)
PRODUCT_TYPE = "USDT-FUTURES"

REST_BASE_URL = "https://api.bitget.com"
WS_URL = "wss://ws.bitget.com/v2/ws/public"

# ── Telegram ──────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── Timeframes ────────────────────────────────────────────────────────
TREND_TIMEFRAME = "4H"      # bias
TRIGGER_TIMEFRAME = "1H"    # entry confirmation

# ── Indicator settings (gold-tuned, NOT the same as crypto) ────────────
EMA_FAST = 50
EMA_SLOW = 200

RSI_PERIOD = 14
RSI_OVERBOUGHT = 68          # tighter bands than crypto (gold chops more)
RSI_OVERSOLD = 32

ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 1.5      # stop loss = ATR * this
TP_RR_TIERS = [1.5, 2.5, 4.0]  # 3 take-profit tiers in R multiples

BREAKOUT_LOOKBACK = 20       # candles used for structure/breakout check
VOLUME_SPIKE_MULTIPLIER = 1.5  # current vol vs avg vol

# ── Confidence scoring ───────────────────────────────────────────────
# A signal only fires if at least MIN_CONFLUENCE of these factors align:
# trend(EMA), momentum(RSI), structure(breakout), volume
MIN_CONFLUENCE = 3           # out of 4 factors
MAX_CONFLUENCE = 4

# ── Risk / leverage guidance (suggestions only, no auto-execution) ─────
BASE_LEVERAGE = 5
HIGH_VOL_LEVERAGE = 2        # used when ATR% is elevated
HIGH_VOL_ATR_PCT_THRESHOLD = 0.9   # ATR as % of price above this = "high vol"

# ── Frequency / discipline controls ─────────────────────────────────
MAX_SIGNALS_PER_DAY = 4      # real pros don't trade constantly
MIN_MINUTES_BETWEEN_SIGNALS = 90
COOLDOWN_AFTER_LOSS_MINUTES = 60   # optional extra pause after a tracked loss

# ── Session awareness (UTC hours) ───────────────────────────────────
SESSION_ASIAN = (0, 8)
SESSION_LONDON = (8, 13)
SESSION_NY = (13, 21)
SESSION_OVERLAP_LONDON_NY = (13, 16)   # highest-liquidity window
LOW_LIQUIDITY_MUTE = True    # suppress weak signals outside London/NY

# ── News blackout ────────────────────────────────────────────────────
# Manually maintained high-impact USD event windows (UTC). Update weekly —
# see news_filter.py for how to extend this from a calendar source.
NEWS_BLACKOUT_MINUTES_BEFORE = 15
NEWS_BLACKOUT_MINUTES_AFTER = 15

# ── Storage ───────────────────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "/data/gold_signals.db")  # Railway volume mount

# ── Polling ───────────────────────────────────────────────────────────
POLL_INTERVAL_SECONDS = 60

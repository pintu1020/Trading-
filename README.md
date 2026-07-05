# Gold (XAU) Telegram Signal Bot

Signals-only bot for Bitget's XAUTUSDT (Tether Gold) perpetual. No auto-execution —
it posts LONG/SHORT alerts with entry, stop loss, 3 take-profit tiers, and suggested
leverage to a Telegram chat, so you place the trade yourself.

## How signals are generated

A signal only fires when **at least 3 of 4 factors** align:
1. **Trend** — 4H EMA50 vs EMA200
2. **Momentum** — 1H RSI confirms without being overbought/oversold
3. **Structure** — 1H price breaks recent high/low in trend direction
4. **Volume** — current candle volume spikes vs recent average

Plus:
- Muted around high-impact USD news events (see `news_events.json`)
- Weighted down in thin-liquidity (Asian) sessions — requires full 4/4 confluence there
- Capped at **4 signals/day**, minimum 90 min apart — this is intentional, real setups are rare
- SL/TP are ATR-based, not fixed percentages
- Leverage suggestion drops automatically when volatility (ATR%) is elevated

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in:
   - `TELEGRAM_BOT_TOKEN` — from @BotFather
   - `TELEGRAM_CHAT_ID` — the chat/channel to post signals to
3. Edit `news_events.json` weekly with the coming week's high-impact USD events
   (NFP, CPI, FOMC, PPI, retail sales) — get times from ForexFactory or similar.
4. Run: `python main.py`

## Deploying to Railway (same pattern as your Bitget crypto bot)

1. Push this folder to a GitHub repo, connect it in Railway
2. Add a **Volume** mounted at `/data` (for SQLite persistence)
3. Set environment variables in Railway's dashboard (same keys as `.env.example`)
4. Railway will run `python main.py` — no Procfile needed if it auto-detects,
   otherwise add one: `worker: python main.py`

## Telegram commands

- `/stats` — win rate and signal counts
- `/status` — bot health + signals sent today

## Signal filtering (new)

Two extra filters run on every check, both fail-open (never crash or block
a signal if their data source has an issue):

- **Volatility regime (`volatility_regime.py`)** — uses Bollinger Band
  bandwidth to detect choppy/range-bound conditions vs real trends. Most
  false breakouts happen during chop, so a squeeze regime forces the
  stricter full-confluence requirement automatically.
- **DXY correlation (`dxy_filter.py`)** — gold and the US Dollar Index
  normally move inversely. If DXY is trending the *same* direction as a
  gold signal (correlation breaking down — unusual), that signal is held
  to full confluence too. If DXY confirms the expected inverse move, it's
  added as a supporting reason in the alert. Pulled from Yahoo Finance's
  free endpoint, cached 15 min (no API key needed).

## Signal filtering: volatility regime + DXY correlation (new)

Two additional filters run inside `signal_engine.py`, both tightening
confluence requirements rather than blocking outright:

**Volatility regime** (`volatility_regime.py`) — uses Bollinger Band
bandwidth, compared against its own recent history (percentile rank),
to detect choppy/squeezed markets. Most breakout fakeouts happen during
chop, so signals require full 4/4 confluence in these conditions.

**DXY correlation** (`dxy_filter.py`) — gold and the US Dollar Index are
normally inversely correlated. If DXY is trending the same direction as
a gold signal (a correlation breakdown / unusual condition), the signal
requires full confluence instead of the normal minimum. If DXY confirms
the expected inverse relationship, it's added as a supporting reason
in the alert.

DXY data comes from Yahoo Finance's public (unofficial, no API key)
endpoint. This is **fail-open**: if that endpoint is unreachable or
blocked (which can happen intermittently, including from some cloud
providers), the filter is silently skipped rather than blocking
signals — you'll see a warning in the logs, not a crash.

**Deploy together**: `signal_engine.py`, `indicators.py`, `config.py`,
`volatility_regime.py`, and `dxy_filter.py` must all be updated at the
same time — `signal_engine.py` imports the other four directly (not
optionally), so deploying it alone without the others will crash on
startup.

## Adaptive learning (new)

After each closed trade, `adaptive_learning.py` updates rolling win/loss stats
per session. If a session's win rate drops below 45% over at least 6 trades,
that session automatically requires full 4/4 confluence instead of 3/4 —
it gets more selective, not less. It never loosens below your `config.py`
baseline; that direction is intentionally not automated, since loosening
after a winning streak is how accounts overtrade into a drawdown.

There's also a circuit breaker: 3 losses in a row pauses new signals for
`COOLDOWN_AFTER_LOSS_MINUTES` (in `config.py`). You'll get a Telegram
message any time a threshold actually changes — never a silent adjustment.

This is deliberately NOT a self-training ML model. A true "learns and gets
better" system needs far more data than a handful of trades to avoid
overfitting to noise, and blindly loosening rules after wins is genuinely
dangerous with real money. This gives you the safe half: automatic caution
when something's underperforming, full transparency, human-set ceiling.

## Outcome tracking (new)

A background thread checks every 5 minutes whether open signals hit TP1 (win)
or stop loss (loss) first, using actual 1H candle highs/lows since the signal
fired — not just the current price, so it won't miss a wick that touched a
level between polls. Results save automatically and `/stats` now reflects
real win/loss data. Signals unresolved after 72 hours auto-expire.

## Backtesting (new)

`python backtest.py --candles 1000` runs a walk-forward simulation using the
exact same `signal_engine.evaluate()` function that's live in production —
not a separate/simplified version, so results are directly meaningful.

Limitation: Bitget's public candle endpoint caps how much history you can
pull in one request (~1000 candles), so this is a sanity check on the logic
over recent months, not a deep multi-year backtest. Good enough to catch if
the confluence rules are obviously broken or wildly unprofitable before you
trust the bot live.

## Tuning

All thresholds live in `config.py` — EMA periods, RSI bands, ATR multiplier,
TP tiers, leverage rules, daily signal cap. Recommend paper-tracking signals
for 2-3 weeks before trusting sizing, then adjust `config.py` based on the
`/stats` win rate.

## Honest limitations

- No backtesting engine included — this is forward-signal only. Track outcomes
  via `database.update_outcome()` (called manually or wire up a price-check job)
  to build a real win-rate history over time.
- News blackout list is manually maintained, not pulled from a live calendar API.
- A 95% win rate is not realistic for any continuously-running system. This bot
  is tuned for disciplined, infrequent, high-quality setups with favorable
  risk-reward — not high win-rate.

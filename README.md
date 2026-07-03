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

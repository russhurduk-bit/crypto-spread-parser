# Crypto Spread Parser

A CEX arbitrage spread scanner. It watches order-book top-of-book prices for a curated list of pairs across 8 exchanges, computes fee-aware net spreads, filters out noise, and sends Telegram alerts when a genuinely profitable spread appears.

## Features

- **8 exchanges via ccxt** — Binance, Bybit, MEXC, KuCoin, HTX (ex-Huobi), Gate.io, OKX, Bitget. Public data only, no API keys needed.
- **Batched, concurrent fetching** — one `fetch_tickers` call per exchange per scan, run concurrently across all exchanges (default scan interval: 8s).
- **Fee-aware net spread** — buys at the lowest ask, sells at the highest bid, then subtracts each exchange's taker fee to get the *net* spread; alerts only fire above `MIN_NET_SPREAD_PCT` (default 0.5%).
- **Noise filtering** — a blacklist of same-ticker/different-token pairs, a `MAX_SPREAD_PCT` cap (default 25%, above which a spread is treated as fake), and a minimum 24h volume floor (`MIN_VOLUME_USD`).
- **Alert cooldown** — the same symbol+route won't re-alert within `ALERT_COOLDOWN` (default 5 min), preventing spam.
- **Telegram alerts** — formatted spread reports sent via the Bot API (plus a startup notification and periodic scan stats in the log).
- **Pair discovery tools** — `discover_pairs.py` / `discover_fast.py` find pairs that exist on 3+ exchanges with decent volume, to refresh the watch list in `config.py`.

## Tech stack

- Python 3.9+ (uses `list[dict]` type hints)
- ccxt (async support) for exchange data
- asyncio for concurrency
- Telegram Bot API via `urllib` (standard library)

## Setup

```bash
# 1. Create a virtualenv and install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# 3. Load env vars (the code reads os.getenv)
export $(grep -v '^#' .env | xargs)
```

## Usage

**Run the scanner (continuous loop):**

```bash
python scanner.py
```

**Run a single test pass** (prints all spreads found, no alerts loop):

```bash
python test_scan.py
```

**Refresh the watched-pairs list:**

```bash
python discover_fast.py     # fast, batch fetch_tickers
python discover_pairs.py    # pairs present on 3+ exchanges with volume
# then paste results into PAIRS in config.py
```

## Configuration

Tunable in `config.py`: `EXCHANGES`, `PAIRS`, `BLACKLISTED_PAIRS`, `EXCHANGE_FEES`, `MIN_NET_SPREAD_PCT`, `MAX_SPREAD_PCT`, `MIN_VOLUME_USD`, `SCAN_INTERVAL`, `ALERT_COOLDOWN`, `LOG_FILE`.

## Notes

- **Alerts require Telegram env vars.** If `TELEGRAM_CHAT_ID` is `0` (unset), alerts are only written to the log, not sent.
- **`LOG_FILE` is a hardcoded absolute path** (`/root/crypto-spread-parser/scanner.log`) — change it in `config.py` if deploying elsewhere.
- **Spread ≠ guaranteed profit.** Net spread accounts for taker fees only; it does not account for withdrawal/deposit fees, transfer time, slippage, or order-book depth beyond top-of-book. Treat alerts as leads, not executable trades.
- All fetched data is public market data; no exchange API keys are used or stored.

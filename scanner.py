#!/usr/bin/env python3
"""
Crypto Spread Parser — Main Scanner
Мониторит спреды между биржами, шлёт алерты в Telegram.
"""

import asyncio
import ccxt.async_support as ccxt
import time
import logging
import signal
import sys
from datetime import datetime, timezone
from config import (
    EXCHANGES, PAIRS, MIN_NET_SPREAD_PCT, EXCHANGE_FEES,
    SCAN_INTERVAL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    ALERT_COOLDOWN, MIN_VOLUME_USD, LOG_FILE,
    BLACKLISTED_PAIRS, MAX_SPREAD_PCT,
)

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("scanner")

# --- Telegram (Bot API via HTTP) ---
import urllib.request
import urllib.parse
import json

TG_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


async def send_alert(text: str):
    """Send alert to Telegram via Bot API + log."""
    log.info(f"ALERT: {text}")
    if not TELEGRAM_CHAT_ID:
        return
    try:
        data = urllib.parse.urlencode({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
        }).encode()
        req = urllib.request.Request(TG_API_URL, data=data)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, urllib.request.urlopen, req)
    except Exception as e:
        log.error(f"TG send failed: {e}")


# --- Exchange Pool ---
exchange_instances = {}

async def init_exchanges():
    for ex_id in EXCHANGES:
        try:
            ex_class = getattr(ccxt, ex_id)
            instance = ex_class({"enableRateLimit": True})
            await instance.load_markets()
            exchange_instances[ex_id] = instance
            log.info(f"Exchange {ex_id}: {len(instance.markets)} markets loaded")
        except Exception as e:
            log.warning(f"Exchange {ex_id} init failed: {e}")


async def close_exchanges():
    for ex_id, ex in exchange_instances.items():
        try:
            await ex.close()
        except:
            pass


# --- Batch Price Fetcher ---
cached_tickers = {}  # ex_id -> {symbol: {bid, ask, vol}} — refreshed each scan

async def fetch_all_exchange_tickers(ex_id: str, ex) -> dict:
    """Fetch ALL tickers from one exchange in one API call."""
    try:
        raw = await ex.fetch_tickers()
        result = {}
        for symbol, t in raw.items():
            if symbol not in watched_pairs:
                continue
            bid, ask = t.get("bid"), t.get("ask")
            vol = t.get("quoteVolume") or 0
            if bid and ask and bid > 0 and ask > 0 and vol >= MIN_VOLUME_USD:
                result[symbol] = {
                    "exchange": ex_id,
                    "symbol": symbol,
                    "bid": float(bid),
                    "ask": float(ask),
                    "volume_usd": float(vol),
                }
        return result
    except Exception as e:
        log.warning(f"fetch_tickers failed for {ex_id}: {e}")
        return {}


async def refresh_all_tickers():
    """Refresh tickers from all exchanges concurrently."""
    tasks = {ex_id: fetch_all_exchange_tickers(ex_id, ex) for ex_id, ex in exchange_instances.items()}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    for ex_id, result in zip(tasks.keys(), results):
        if isinstance(result, dict):
            cached_tickers[ex_id] = result
        else:
            log.warning(f"Ticker fetch error for {ex_id}: {result}")


def get_tickers_for_symbol(symbol: str) -> list[dict]:
    """Get all cached tickers for a symbol across exchanges."""
    tickers = []
    for ex_id, data in cached_tickers.items():
        if symbol in data:
            tickers.append(data[symbol])
    return tickers


# Set of pairs to watch (for filtering)
watched_pairs = set(p for p in PAIRS if p not in BLACKLISTED_PAIRS)


# --- Spread Calculator ---
def find_spreads(tickers: list[dict]) -> list[dict]:
    """
    Find all profitable spread pairs.
    Buy on exchange with lowest ask, sell on exchange with highest bid.
    Account for taker fees on both sides.
    """
    if len(tickers) < 2:
        return []

    spreads = []
    for i, buy in enumerate(tickers):
        for j, sell in enumerate(tickers):
            if i == j:
                continue
            # Buy at ask on exchange A, sell at bid on exchange B
            buy_price = buy["ask"]
            sell_price = sell["bid"]

            if sell_price <= buy_price:
                continue

            gross_spread_pct = ((sell_price - buy_price) / buy_price) * 100

            # Subtract fees
            buy_fee = EXCHANGE_FEES.get(buy["exchange"], 0.15)
            sell_fee = EXCHANGE_FEES.get(sell["exchange"], 0.15)
            net_spread_pct = gross_spread_pct - buy_fee - sell_fee

            if net_spread_pct >= MIN_NET_SPREAD_PCT and gross_spread_pct <= MAX_SPREAD_PCT:
                spreads.append({
                    "symbol": buy["symbol"],
                    "buy_exchange": buy["exchange"],
                    "buy_price": buy_price,
                    "sell_exchange": sell["exchange"],
                    "sell_price": sell_price,
                    "gross_pct": round(gross_spread_pct, 3),
                    "net_pct": round(net_spread_pct, 3),
                    "buy_vol": buy["volume_usd"],
                    "sell_vol": sell["volume_usd"],
                })

    # Sort by net spread descending
    spreads.sort(key=lambda x: x["net_pct"], reverse=True)
    return spreads


# --- Alert Cooldown ---
alert_history = {}  # key -> last_alert_time

def should_alert(spread: dict) -> bool:
    key = f"{spread['symbol']}_{spread['buy_exchange']}_{spread['sell_exchange']}"
    now = time.time()
    last = alert_history.get(key, 0)
    if now - last < ALERT_COOLDOWN:
        return False
    alert_history[key] = now
    return True


def format_alert(s: dict) -> str:
    return (
        f"{'='*35}\n"
        f"SPREAD {s['symbol']}\n"
        f"{'='*35}\n"
        f"BUY  {s['buy_exchange'].upper():>8}  ${s['buy_price']:,.6f}\n"
        f"SELL {s['sell_exchange'].upper():>8}  ${s['sell_price']:,.6f}\n"
        f"\n"
        f"Gross: {s['gross_pct']:.2f}%\n"
        f"Net:   {s['net_pct']:.2f}% (after fees)\n"
        f"\n"
        f"Vol buy:  ${s['buy_vol']:,.0f}\n"
        f"Vol sell: ${s['sell_vol']:,.0f}\n"
        f"Time: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
    )


# --- Stats ---
scan_count = 0
total_alerts = 0
start_time = None


# --- Main Loop ---
async def scan_once():
    global scan_count, total_alerts
    scan_count += 1
    found = 0

    # One batch fetch per exchange (fast!)
    await refresh_all_tickers()

    for symbol in watched_pairs:
        tickers = get_tickers_for_symbol(symbol)
        if len(tickers) < 2:
            continue

        spreads = find_spreads(tickers)
        for s in spreads:
            if should_alert(s):
                found += 1
                total_alerts += 1
                await send_alert(format_alert(s))

    return found


async def main():
    global start_time
    start_time = time.time()

    log.info("=" * 50)
    log.info("Crypto Spread Parser starting...")
    log.info(f"Exchanges: {', '.join(EXCHANGES)}")
    log.info(f"Pairs: {len(PAIRS)}")
    log.info(f"Min net spread: {MIN_NET_SPREAD_PCT}%")
    log.info(f"Scan interval: {SCAN_INTERVAL}s")
    log.info("=" * 50)

    await init_exchanges()

    active = list(exchange_instances.keys())
    log.info(f"Active exchanges: {', '.join(active)} ({len(active)}/{len(EXCHANGES)})")

    if not active:
        log.error("No exchanges available, exiting")
        return

    # Startup notification
    await send_alert(
        f"Crypto Spread Parser started\n"
        f"Exchanges: {', '.join(active)}\n"
        f"Pairs: {len(PAIRS)}\n"
        f"Min net spread: {MIN_NET_SPREAD_PCT}%\n"
        f"Interval: {SCAN_INTERVAL}s"
    )

    try:
        while True:
            t0 = time.time()
            try:
                found = await scan_once()
                elapsed = time.time() - t0
                if scan_count % 10 == 0:
                    log.info(
                        f"Scan #{scan_count} done in {elapsed:.1f}s | "
                        f"alerts this scan: {found} | total alerts: {total_alerts}"
                    )
            except Exception as e:
                log.error(f"Scan error: {e}")

            # Wait for next scan
            elapsed = time.time() - t0
            wait = max(0, SCAN_INTERVAL - elapsed)
            if wait > 0:
                await asyncio.sleep(wait)

    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("Shutting down...")
    finally:
        await close_exchanges()
        log.info("Scanner stopped.")


if __name__ == "__main__":
    asyncio.run(main())

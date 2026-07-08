#!/usr/bin/env python3
"""
Discover pairs that exist on 3+ exchanges with decent volume.
These are the ones most likely to have spreads.
"""
import asyncio
import ccxt.async_support as ccxt
from collections import defaultdict
from config import EXCHANGES, MIN_VOLUME_USD

async def main():
    instances = {}
    for ex_id in EXCHANGES:
        try:
            ex_class = getattr(ccxt, ex_id)
            inst = ex_class({"enableRateLimit": True})
            await inst.load_markets()
            instances[ex_id] = inst
            print(f"[OK] {ex_id}")
        except Exception as e:
            print(f"[FAIL] {ex_id}: {e}")

    # Find all USDT pairs across exchanges
    pair_exchanges = defaultdict(set)
    for ex_id, ex in instances.items():
        for symbol in ex.markets:
            if symbol.endswith("/USDT") and ":" not in symbol:  # spot only
                pair_exchanges[symbol].add(ex_id)

    # Filter: exists on 3+ exchanges
    multi_exchange = {k: v for k, v in pair_exchanges.items() if len(v) >= 3}
    print(f"\nPairs on 3+ exchanges: {len(multi_exchange)}")

    # Now fetch tickers for these pairs and find actual spreads
    print("\nScanning for live spreads (this takes a minute)...\n")

    live_spreads = []
    count = 0
    total = len(multi_exchange)

    for symbol, exchanges in sorted(multi_exchange.items()):
        count += 1
        if count % 50 == 0:
            print(f"  Progress: {count}/{total}...")

        tickers = []
        for ex_id in exchanges:
            ex = instances[ex_id]
            try:
                t = await ex.fetch_ticker(symbol)
                bid, ask = t.get("bid"), t.get("ask")
                vol = t.get("quoteVolume") or 0
                if bid and ask and bid > 0 and ask > 0 and vol >= 10000:  # lower threshold for discovery
                    tickers.append({"exchange": ex_id, "bid": float(bid), "ask": float(ask), "vol": float(vol)})
            except:
                pass

        if len(tickers) < 2:
            continue

        # Find max spread
        best_buy = min(tickers, key=lambda x: x["ask"])
        best_sell = max(tickers, key=lambda x: x["bid"])
        if best_sell["bid"] > best_buy["ask"] and best_buy["exchange"] != best_sell["exchange"]:
            gross = ((best_sell["bid"] - best_buy["ask"]) / best_buy["ask"]) * 100
            if gross >= 0.3:
                live_spreads.append({
                    "symbol": symbol,
                    "buy": best_buy["exchange"],
                    "ask": best_buy["ask"],
                    "sell": best_sell["exchange"],
                    "bid": best_sell["bid"],
                    "gross": round(gross, 2),
                    "exchanges": len(tickers),
                    "min_vol": min(t["vol"] for t in tickers),
                })

    live_spreads.sort(key=lambda x: x["gross"], reverse=True)

    print(f"\n{'Symbol':<15} {'Buy@':>8} {'Ask':>14} {'Sell@':>8} {'Bid':>14} {'Gross%':>7} {'#Ex':>4}")
    print("-" * 80)
    for s in live_spreads[:50]:
        print(f"{s['symbol']:<15} {s['buy']:>8} {s['ask']:>14.8f} {s['sell']:>8} {s['bid']:>14.8f} {s['gross']:>6.2f}% {s['exchanges']:>4}")

    print(f"\nTotal pairs with spread >= 0.3%: {len(live_spreads)}")

    # Save good pairs to file
    good_pairs = [s["symbol"] for s in live_spreads if s["gross"] >= 0.5]
    with open("/root/crypto-spread-parser/discovered_pairs.txt", "w") as f:
        for p in good_pairs:
            f.write(p + "\n")
    print(f"Saved {len(good_pairs)} pairs (>= 0.5%) to discovered_pairs.txt")

    for ex in instances.values():
        await ex.close()

asyncio.run(main())

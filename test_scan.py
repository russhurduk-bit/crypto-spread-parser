#!/usr/bin/env python3
"""Quick test: one scan pass, print all spreads found."""
import asyncio
import ccxt.async_support as ccxt
from config import EXCHANGES, PAIRS, EXCHANGE_FEES, MIN_VOLUME_USD

async def main():
    instances = {}
    for ex_id in EXCHANGES:
        try:
            ex_class = getattr(ccxt, ex_id)
            inst = ex_class({"enableRateLimit": True})
            await inst.load_markets()
            instances[ex_id] = inst
            print(f"[OK] {ex_id}: {len(inst.markets)} markets")
        except Exception as e:
            print(f"[FAIL] {ex_id}: {e}")

    print(f"\nActive: {list(instances.keys())}")
    print(f"Testing {len(PAIRS)} pairs...\n")

    all_spreads = []
    for symbol in PAIRS:
        tickers = []
        for ex_id, ex in instances.items():
            if symbol not in ex.markets:
                continue
            try:
                t = await ex.fetch_ticker(symbol)
                bid, ask = t.get("bid"), t.get("ask")
                vol = t.get("quoteVolume") or 0
                if bid and ask and bid > 0 and ask > 0 and vol >= MIN_VOLUME_USD:
                    tickers.append({"exchange": ex_id, "bid": float(bid), "ask": float(ask), "vol": float(vol)})
            except:
                pass

        # Find spreads
        for i, buy in enumerate(tickers):
            for j, sell in enumerate(tickers):
                if i == j:
                    continue
                if sell["bid"] <= buy["ask"]:
                    continue
                gross = ((sell["bid"] - buy["ask"]) / buy["ask"]) * 100
                net = gross - EXCHANGE_FEES.get(buy["exchange"], 0.15) - EXCHANGE_FEES.get(sell["exchange"], 0.15)
                if net > 0:
                    all_spreads.append({
                        "symbol": symbol,
                        "buy": buy["exchange"],
                        "buy_ask": buy["ask"],
                        "sell": sell["exchange"],
                        "sell_bid": sell["bid"],
                        "gross": round(gross, 3),
                        "net": round(net, 3),
                    })

    all_spreads.sort(key=lambda x: x["net"], reverse=True)

    print(f"{'Symbol':<12} {'Buy@':>8} {'Ask':>12} {'Sell@':>8} {'Bid':>12} {'Gross%':>7} {'Net%':>7}")
    print("-" * 75)
    for s in all_spreads[:30]:
        print(f"{s['symbol']:<12} {s['buy']:>8} {s['buy_ask']:>12.6f} {s['sell']:>8} {s['sell_bid']:>12.6f} {s['gross']:>6.2f}% {s['net']:>6.2f}%")

    if not all_spreads:
        print("No spreads found above 0%")
    else:
        above_05 = [s for s in all_spreads if s["net"] >= 0.5]
        print(f"\nTotal spreads > 0%: {len(all_spreads)}")
        print(f"Spreads >= 0.5% net: {len(above_05)}")

    for ex in instances.values():
        await ex.close()

asyncio.run(main())

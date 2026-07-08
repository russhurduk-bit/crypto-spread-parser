#!/usr/bin/env python3
"""
Fast discovery: use fetch_tickers (batch) where available, then compare.
"""
import asyncio
import ccxt.async_support as ccxt
from collections import defaultdict
from config import EXCHANGES, EXCHANGE_FEES

async def main():
    instances = {}
    all_tickers = {}  # ex_id -> {symbol: {bid, ask, vol}}

    for ex_id in EXCHANGES:
        try:
            ex_class = getattr(ccxt, ex_id)
            inst = ex_class({"enableRateLimit": True})
            await inst.load_markets()
            instances[ex_id] = inst
            print(f"[OK] {ex_id}: loading tickers...")

            # Fetch ALL tickers at once (most exchanges support this)
            tickers = await inst.fetch_tickers()
            ex_data = {}
            for symbol, t in tickers.items():
                if not symbol.endswith("/USDT") or ":" in symbol:
                    continue
                bid, ask = t.get("bid"), t.get("ask")
                vol = t.get("quoteVolume") or 0
                if bid and ask and bid > 0 and ask > 0 and vol >= 10000:
                    ex_data[symbol] = {"bid": float(bid), "ask": float(ask), "vol": float(vol)}
            all_tickers[ex_id] = ex_data
            print(f"  {ex_id}: {len(ex_data)} USDT pairs with volume")
        except Exception as e:
            print(f"[FAIL] {ex_id}: {e}")

    # Find spreads: for each pair, compare across exchanges
    pair_data = defaultdict(dict)  # symbol -> {ex_id: {bid, ask, vol}}
    for ex_id, data in all_tickers.items():
        for symbol, ticker in data.items():
            pair_data[symbol][ex_id] = ticker

    # Only pairs on 2+ exchanges
    multi = {k: v for k, v in pair_data.items() if len(v) >= 2}
    print(f"\nPairs on 2+ exchanges: {len(multi)}")

    spreads = []
    for symbol, exchanges in multi.items():
        items = list(exchanges.items())
        for i in range(len(items)):
            for j in range(len(items)):
                if i == j:
                    continue
                buy_ex, buy_t = items[i]
                sell_ex, sell_t = items[j]
                if sell_t["bid"] <= buy_t["ask"]:
                    continue
                gross = ((sell_t["bid"] - buy_t["ask"]) / buy_t["ask"]) * 100
                buy_fee = EXCHANGE_FEES.get(buy_ex, 0.15)
                sell_fee = EXCHANGE_FEES.get(sell_ex, 0.15)
                net = gross - buy_fee - sell_fee
                if net >= 0.3:
                    spreads.append({
                        "symbol": symbol,
                        "buy_ex": buy_ex,
                        "ask": buy_t["ask"],
                        "sell_ex": sell_ex,
                        "bid": sell_t["bid"],
                        "gross": round(gross, 2),
                        "net": round(net, 2),
                        "buy_vol": buy_t["vol"],
                        "sell_vol": sell_t["vol"],
                    })

    spreads.sort(key=lambda x: x["net"], reverse=True)

    print(f"\n{'Symbol':<18} {'Buy@':>8} {'Ask':>14} {'Sell@':>8} {'Bid':>14} {'Gross%':>7} {'Net%':>7} {'BuyVol':>12}")
    print("-" * 100)
    for s in spreads[:60]:
        print(f"{s['symbol']:<18} {s['buy_ex']:>8} {s['ask']:>14.8f} {s['sell_ex']:>8} {s['bid']:>14.8f} {s['gross']:>6.2f}% {s['net']:>6.2f}% ${s['buy_vol']:>10,.0f}")

    # Save pairs with good spreads
    good_pairs = list(set(s["symbol"] for s in spreads if s["net"] >= 0.5))
    good_pairs.sort()
    with open("/root/crypto-spread-parser/discovered_pairs.txt", "w") as f:
        for p in good_pairs:
            f.write(p + "\n")
    print(f"\nTotal spreads >= 0.3% net: {len(spreads)}")
    print(f"Unique pairs >= 0.5% net: {len(good_pairs)} -> saved to discovered_pairs.txt")

    for ex in instances.values():
        await ex.close()

asyncio.run(main())

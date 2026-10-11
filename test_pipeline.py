import sys
import screener
import pprint

print("Stage 0: Refresh Market Universe")
universe, msg, _stats = screener.refresh_market_universe("test_universe.csv")
print(msg)
if not universe:
    sys.exit(1)

sample = universe[:5]
print("Sample:", sample)

tickers = tuple(s['Symbol'] for s in sample)
metadata_items = tuple((s['Symbol'], s.get('CIK'), None) for s in sample)

print("\nStage 1: Batch Historical")
hist_data = screener.fetch_historical_data(list(tickers))
print(f"Fetched hist for {len(hist_data)} symbols")

print("\nStage 2 & 3: Metadata Hybrid Fetch")
items = [{'ticker': t, 'cik': c, 'finnhub_key': k} for t, c, k in metadata_items]
meta = screener.fetch_metadata_parallel(items)
print(f"Fetched metadata for {len(meta)} symbols")

print("\nStage 4: Scoring")
all_res = []
for t in tickers:
    res, msg = screener.calculate_single_ticker_metrics(t, hist_data.get(t), meta, diagnostics_mode=False)
    if res:
        all_res.append(res)
        print(f"Scored {t}: Data Confidence = {res.get('Data Confidence')}, Why Ranked = {res.get('Why This Stock Ranked', 'N/A')}")
    else:
        print(f"Filtered {t}: {msg}")


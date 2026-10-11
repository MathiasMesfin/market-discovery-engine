#!/usr/bin/env python3
"""
Morning Pre-Market Batch Discovery Script
Executes full market / discovery universe scans headlessly before market open.
Saves results to data/history/daily_discovery_latest.csv and parquet for instant 0-second loading.
"""

import os
import sys
import argparse
import datetime
import time
import math
import concurrent.futures
import pandas as pd

# Add repo root to python path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import screener
from screener import (
    get_discovery_universe_items,
    get_dev_test_scan_items,
    fetch_historical_data,
    calculate_single_ticker_metrics,
    calculate_screener_scores,
    save_screening_run,
)

LIQUIDITY_MIN_PRICE = 2.0
LIQUIDITY_MIN_AVG_VOL = 500_000.0
import api_fetch
from api_fetch import (
    fetch_cached_fundamentals_24h,
    fetch_cached_earnings_12h,
    fetch_cached_sec_24h,
    new_api_telemetry_delta,
    merge_api_telemetry_delta,
)


def run_morning_scan(universe_name="discovery", max_workers=8, finnhub_key=None, output_dir=None):
    start_time = time.time()
    if output_dir is None:
        output_dir = os.path.join(repo_root, "data", "history")
    os.makedirs(output_dir, exist_ok=True)

    if not finnhub_key:
        finnhub_key = os.environ.get("FINNHUB_API_KEY", "")

    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Morning Discovery Batch...")
    print(f"Universe: {universe_name} | Concurrency: {max_workers} workers")

    # 1. Load universe
    if universe_name == "test":
        items = get_dev_test_scan_items()
    elif universe_name == "sample":
        # ~50 liquid mid/large cap names — a good daily sanity check
        universe_path = os.path.join(repo_root, "data", "us_stock_universe.csv")
        if os.path.exists(universe_path):
            df_u = pd.read_csv(universe_path)
            df_sample = df_u.head(50)
            items = [
                {
                    'ticker': str(row['Symbol']).upper(),
                    'cik': str(row['CIK']).zfill(10) if pd.notnull(row.get('CIK')) else None
                }
                for _, row in df_sample.iterrows()
            ]
        else:
            items = get_dev_test_scan_items()
    elif universe_name == "discovery":
        universe_path = os.path.join(repo_root, "data", "us_stock_universe.csv")
        items = get_discovery_universe_items(universe_path)
    elif universe_name == "full":
        universe_path = os.path.join(repo_root, "data", "us_stock_universe.csv")
        if os.path.exists(universe_path):
            df_u = pd.read_csv(universe_path)
            items = []
            for _, row in df_u.iterrows():
                items.append({
                    'ticker': str(row['Symbol']).upper(),
                    'cik': str(row['CIK']).zfill(10) if pd.notnull(row.get('CIK')) else None
                })
        else:
            print("Error: data/us_stock_universe.csv not found.")
            return False
    else:
        print(f"Unknown universe: {universe_name}")
        return False

    tickers = [s['ticker'] for s in items]
    print(f"Loaded {len(tickers)} universe tickers.")

    # 2. Stage 1: Batch Historical Download & Liquidity Filter
    print("Stage 1: Fetching historical bars...")
    hist_data = {}
    batch_size = 50
    for i in range(0, len(tickers), batch_size):
        chunk = tickers[i:i + batch_size]
        try:
            chunk_hist = fetch_historical_data(chunk, period="1y")
            hist_data.update(chunk_hist)
        except Exception as e:
            print(f"Warning: batch history fetch failed for {chunk[:3]}: {e}")

    stage1_survivors = []
    min_price = LIQUIDITY_MIN_PRICE
    min_vol = LIQUIDITY_MIN_AVG_VOL

    for item in items:
        ticker = item['ticker']
        df = hist_data.get(ticker)
        if df is None or df.empty or len(df) < 20:
            continue
        try:
            current_price = float(df['Close'].iloc[-1])
            avg_vol = float(df['Volume'].rolling(90).mean().iloc[-1]) if len(df) >= 90 else float(df['Volume'].mean())
            if current_price >= min_price and avg_vol >= min_vol:
                s = dict(item)
                s['hist_df'] = df
                stage1_survivors.append(s)
        except Exception:
            continue

    print(f"Stage 1 Complete: {len(stage1_survivors)} / {len(tickers)} symbols passed liquidity & volume filters.")
    if not stage1_survivors:
        print("No symbols passed Stage 1.")
        return False

    # 3. Stage 2 & 3: Parallel Metadata Hybrid Fetch (Fundamentals, Earnings, SEC EDGAR)
    print("Stage 2 & 3: Fetching fundamentals, earnings calendar, and SEC filings...")
    meta_dict = {}

    def fetch_meta_for_candidate(s):
        ticker = s['ticker']
        cik = s.get('cik')
        delta = new_api_telemetry_delta()
        fund_data, d1 = fetch_cached_fundamentals_24h(ticker)
        merge_api_telemetry_delta(delta, d1)
        earn_data, d2 = fetch_cached_earnings_12h(ticker, finnhub_key)
        merge_api_telemetry_delta(delta, d2)
        sec_data, d3 = fetch_cached_sec_24h(ticker, cik)
        merge_api_telemetry_delta(delta, d3)

        meta = {}
        if fund_data:
            meta.update(fund_data)
        if earn_data:
            meta.update(earn_data)
        if sec_data:
            meta.update(sec_data)
        return ticker, meta

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_meta_for_candidate, s): s for s in stage1_survivors}
        for fut in concurrent.futures.as_completed(futures):
            try:
                t, m = fut.result()
                meta_dict[t] = m
            except Exception as e:
                pass

    print(f"Enriched metadata for {len(meta_dict)} symbols.")

    # 4. Stage 4 & 5: Scoring and Metrics
    print("Stage 4 & 5: Scoring and calculating Directional Edge Overlay...")
    deep_metrics = []
    for s in stage1_survivors:
        ticker = s['ticker']
        meta = meta_dict.get(ticker, {})
        res, msg = calculate_single_ticker_metrics(ticker, s['hist_df'], {ticker: meta}, diagnostics_mode=False)
        if res is not None:
            deep_metrics.append(res)

    if not deep_metrics:
        print("No candidates scored in Stage 4.")
        return False

    df_results = calculate_screener_scores(deep_metrics)
    if df_results is None or df_results.empty:
        print("No results returned from calculate_screener_scores.")
        return False

    elapsed = time.time() - start_time
    print(f"Scoring Complete: {len(df_results)} total ranked opportunities in {elapsed:.1f}s.")

    # 5. Persist to Archive, Latest CSV, and Latest Parquet
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(output_dir, f"screener_results_{timestamp}.csv")
    latest_csv_path = os.path.join(output_dir, "daily_discovery_latest.csv")
    latest_parquet_path = os.path.join(output_dir, "daily_discovery_latest.parquet")
    # Universe-specific files for multi-universe pre-market selector in app
    universe_csv_path = os.path.join(output_dir, f"daily_discovery_latest_{universe_name}.csv")
    universe_parquet_path = os.path.join(output_dir, f"daily_discovery_latest_{universe_name}.parquet")

    # Serialize date fields for clean CSV export
    save_df = df_results.copy()
    for col in ['Next Earnings Date', 'Last Earnings Date']:
        if col in save_df.columns:
            save_df[col] = save_df[col].apply(
                lambda d: d.strftime("%Y-%m-%d")
                if isinstance(d, (datetime.date, datetime.datetime))
                else (str(d) if pd.notnull(d) else "")
            )
    if 'SEC Filings' in save_df.columns:
        save_df = save_df.drop(columns=['SEC Filings'])

    save_df.to_csv(archive_path, index=False)
    save_df.to_csv(latest_csv_path, index=False)
    save_df.to_csv(universe_csv_path, index=False)
    try:
        # Parquet export for sub-5ms ultra fast loads
        save_df.to_parquet(latest_parquet_path, index=False)
        save_df.to_parquet(universe_parquet_path, index=False)
    except Exception as e:
        print(f"Note: Parquet export skipped ({e}); CSV is available.")

    print(f"Saved archive: {archive_path}")
    print(f"Saved latest CSV: {latest_csv_path}")

    # Top 5 Preview
    print("\nTop 5 Scored Opportunities:")
    display_cols = [c for c in ['Ticker', 'Final Score', 'Directional Probability Score', 'Opportunity Score', 'Days Until Earnings'] if c in df_results.columns]
    print(df_results[display_cols].head(5).to_string(index=False))

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Discovery Engine Morning Batch Scan")
    parser.add_argument("--universe", choices=["discovery", "test", "sample", "full"], default="discovery", help="Scan universe")
    parser.add_argument("--max-workers", type=int, default=8, help="Thread pool concurrency")
    parser.add_argument("--finnhub-key", type=str, default="", help="Finnhub API Key")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory")

    args = parser.parse_args()
    success = run_morning_scan(
        universe_name=args.universe,
        max_workers=args.max_workers,
        finnhub_key=args.finnhub_key,
        output_dir=args.output_dir,
    )
    sys.exit(0 if success else 1)

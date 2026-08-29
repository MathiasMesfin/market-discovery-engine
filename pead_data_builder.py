"""
pead_data_builder.py
====================
Project PEAD — Phase 1: Data Construction

Loads the existing validated earnings-event universe (trader_trial_real_options_dataset.csv),
fetches fresh OHLCV forward data via yfinance, and computes all variables needed for the
post-earnings drift feasibility test.

DO NOT MODIFY THE PRODUCTION SCREENER OR MAIN BRANCH.
This script is on the project-pead branch only.

Output:
    data/pead/pead_phase1_event_dataset.parquet
    data/pead/pead_phase1_event_dataset.csv
"""

import os
import time
import warnings
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
SOURCE_CSV = "data/vega_real_em/trader_trial_real_options_dataset.csv"
OUTPUT_DIR = "data/pead"
OUTPUT_PARQUET = os.path.join(OUTPUT_DIR, "pead_phase1_event_dataset.parquet")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "pead_phase1_event_dataset.csv")
OHLCV_CACHE = os.path.join(OUTPUT_DIR, "ohlcv_cache.parquet")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────────
API_DELAY_SEC = 0.3

# Market cap bucket thresholds — defined BEFORE looking at results
MICRO_CAP_MAX = 300_000_000
SMALL_CAP_MAX = 2_000_000_000

# Forward horizons (in trading days from Day-0 close)
FORWARD_HORIZONS = {
    "Fwd1D":  1,
    "Fwd3D":  3,
    "Fwd5D":  5,
    "Fwd10D": 10,
    "Fwd20D": 20,
}

# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOAD SOURCE DATA
# ═══════════════════════════════════════════════════════════════════════════════

def load_source_data():
    print(f"Loading source data from {SOURCE_CSV}...")
    df = pd.read_csv(SOURCE_CSV, low_memory=False)
    df["Earnings_Date"] = pd.to_datetime(df["Earnings_Date"])
    print(f"  Raw rows: {len(df)}")
    df = df.dropna(subset=["Pre_Event_Close", "Post_Event_Open", "Post_Event_Close"])
    print(f"  After dropping null price rows: {len(df)}")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TIMING CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def classify_timing(df):
    """
    Per Phase J audit: all 591 events labeled AMC; 0 corrections needed.
    Option chains captured at 4PM ET on earnings date (pre-announcement for AMC).
    No external BMO/AMC calendar available for independent verification.
    All usable events classified as ASSUMED_AMC.
    """
    df = df.copy()
    df["Timing_Quality"] = "ASSUMED_AMC"
    df["Timing_Notes"] = (
        "Phase J audit: 0 corrections needed; option chains at 4PM ET before AMC release. "
        "No external BMO/AMC calendar available for independent verification."
    )
    print(f"  Timing classification: {df['Timing_Quality'].value_counts().to_dict()}")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# 3. FETCH OHLCV DATA
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_ohlcv_all(df, use_cache=True):
    """
    Fetch daily OHLCV for all unique tickers + SPY, Aug 2025 – Feb 2026.
    """
    start_date = "2025-07-01"
    end_date   = "2026-03-01"

    tickers = sorted(df["Ticker"].unique().tolist()) + ["SPY"]

    if use_cache and os.path.exists(OHLCV_CACHE):
        print(f"  Loading OHLCV from cache: {OHLCV_CACHE}")
        try:
            cache_df = pd.read_parquet(OHLCV_CACHE)
            cached_tickers = set(cache_df["Ticker"].unique())
            missing = [t for t in tickers if t not in cached_tickers]
            if not missing:
                print(f"  Cache hit for all {len(tickers)} tickers.")
                ohlcv = {}
                for t in tickers:
                    sub = cache_df[cache_df["Ticker"] == t].drop(columns="Ticker")
                    sub.index = pd.to_datetime(sub.index)
                    ohlcv[t] = sub
                return ohlcv
            else:
                print(f"  Cache missing {len(missing)} tickers; fetching them...")
                ohlcv = {}
                for t in cached_tickers:
                    if t in set(tickers):
                        sub = cache_df[cache_df["Ticker"] == t].drop(columns="Ticker")
                        sub.index = pd.to_datetime(sub.index)
                        ohlcv[t] = sub
        except Exception as e:
            print(f"  Cache read failed ({e}), fetching fresh.")
            ohlcv = {}
            missing = tickers
    else:
        ohlcv = {}
        missing = tickers

    print(f"  Fetching OHLCV for {len(missing)} tickers (0.3s delay)...")
    failures = []

    for i, ticker in enumerate(missing):
        if i % 50 == 0:
            print(f"    [{i}/{len(missing)}] fetching {ticker}...")
        try:
            raw = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=True,
            )
            if raw.empty:
                failures.append(ticker)
            else:
                if isinstance(raw.columns, pd.MultiIndex):
                    raw.columns = raw.columns.get_level_values(0)
                raw.index = pd.to_datetime(raw.index).tz_localize(None)
                ohlcv[ticker] = raw[["Open", "High", "Low", "Close", "Volume"]]
        except Exception as e:
            failures.append(ticker)
        time.sleep(API_DELAY_SEC)

    print(f"  Fetch complete. Failures ({len(failures)}): {failures[:20]}")

    # Save cache
    cache_frames = []
    for t, data in ohlcv.items():
        frame = data.copy()
        frame["Ticker"] = t
        cache_frames.append(frame)
    if cache_frames:
        pd.concat(cache_frames).to_parquet(OHLCV_CACHE)
        print(f"  Saved cache: {OHLCV_CACHE}")

    return ohlcv


# ═══════════════════════════════════════════════════════════════════════════════
# 4. COMPUTE FORWARD RETURNS FROM DAY-0 CLOSE
# ═══════════════════════════════════════════════════════════════════════════════

def get_nth_trading_close(price_series, from_timestamp, n):
    """
    Return (close_price, date) for the nth trading session strictly after from_timestamp.
    Returns (None, None) if insufficient data.
    """
    future = price_series.index[price_series.index > from_timestamp]
    if len(future) < n:
        return None, None
    target_date = future[n - 1]
    return float(price_series.loc[target_date]), target_date


def compute_forward_returns(df, ohlcv):
    """
    Compute forward returns from Day-0 close for each horizon.

    Day-0 = the first trading session after the AMC earnings announcement.
    Post_Event_Close is the close of Day-0 (already verified in Phase J).

    Fwd{h}D_Raw = (Close_{Day0+h} / Post_Event_Close - 1) * 100
    """
    df = df.copy()

    for col in FORWARD_HORIZONS:
        df[f"{col}_Raw"]      = np.nan
        df[f"{col}_Date"]     = pd.NaT
        df[f"{col}_Coverage"] = False

    n_events = len(df)
    for idx, row in df.iterrows():
        ticker = row["Ticker"]
        if ticker not in ohlcv:
            continue

        prices = ohlcv[ticker]["Close"].dropna()
        day0_close = row["Post_Event_Close"]

        # Find actual Day-0 date in yfinance data (first trading day after Earnings_Date)
        future = prices.index[prices.index > pd.Timestamp(row["Earnings_Date"])]
        if len(future) == 0:
            continue
        day0_actual_ts = future[0]

        if day0_close <= 0 or pd.isna(day0_close):
            continue

        for col, h in FORWARD_HORIZONS.items():
            fwd_close, fwd_date = get_nth_trading_close(prices, day0_actual_ts, h)
            if fwd_close is not None:
                df.at[idx, f"{col}_Raw"]      = (fwd_close / day0_close - 1) * 100
                df.at[idx, f"{col}_Date"]     = fwd_date
                df.at[idx, f"{col}_Coverage"] = True

    print("\nForward return coverage:")
    for col in FORWARD_HORIZONS:
        n = int(df[f"{col}_Coverage"].sum())
        print(f"  {col:8s}: {n}/{n_events} ({n/n_events*100:.1f}%)")

    return df


def compute_spy_returns(df, ohlcv):
    """
    For each event and horizon, compute SPY return over the same forward window.
    Market-Adjusted Return (MAR) = Stock Fwd Return - SPY Fwd Return.
    Labeled 'market-adjusted (simple, not beta-adjusted)'.
    """
    df = df.copy()

    for col in FORWARD_HORIZONS:
        df[f"{col}_SPY"] = np.nan
        df[f"{col}_MAR"] = np.nan

    if "SPY" not in ohlcv:
        print("  WARNING: SPY data not available")
        return df

    spy_prices = ohlcv["SPY"]["Close"].dropna()

    for idx, row in df.iterrows():
        future_spy = spy_prices.index[spy_prices.index > pd.Timestamp(row["Earnings_Date"])]
        if len(future_spy) == 0:
            continue
        spy_day0_ts    = future_spy[0]
        spy_day0_close = float(spy_prices.loc[spy_day0_ts])

        for col, h in FORWARD_HORIZONS.items():
            if not row[f"{col}_Coverage"] or pd.isna(row[f"{col}_Raw"]):
                continue
            fwd_date = row[f"{col}_Date"]
            if pd.isna(fwd_date):
                continue

            target_ts = pd.Timestamp(fwd_date)
            spy_future = spy_prices.index[spy_prices.index >= target_ts]
            if len(spy_future) == 0:
                continue

            spy_fwd_close = float(spy_prices.loc[spy_future[0]])
            spy_ret = (spy_fwd_close / spy_day0_close - 1) * 100
            df.at[idx, f"{col}_SPY"] = spy_ret
            df.at[idx, f"{col}_MAR"] = row[f"{col}_Raw"] - spy_ret

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# 5. REACTION VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════

def compute_reaction_variables(df):
    """
    Verify and construct initial earnings reaction metrics.
    Opening_Gap_Pct and Close_To_Close_Return_Pct already exist.
    """
    df = df.copy()

    # Verify Opening_Gap_Pct
    df["_gap_verify"] = (df["Post_Event_Open"] / df["Pre_Event_Close"] - 1) * 100
    max_disc = (df["Opening_Gap_Pct"] - df["_gap_verify"]).abs().max()
    print(f"  Opening_Gap_Pct verify: max discrepancy = {max_disc:.6f} pp")
    assert max_disc < 0.1, f"Opening_Gap_Pct error: {max_disc}"

    # Verify Day0_Close_Reaction_Pct
    df["_ctc_verify"] = (df["Post_Event_Close"] / df["Pre_Event_Close"] - 1) * 100
    max_ctc = (df["Close_To_Close_Return_Pct"] - df["_ctc_verify"]).abs().max()
    print(f"  Day0_Close_Reaction_Pct verify: max discrepancy = {max_ctc:.6f} pp")
    assert max_ctc < 0.1, f"Close_To_Close error: {max_ctc}"

    df["Day0_Close_Reaction_Pct"] = df["Close_To_Close_Return_Pct"].copy()
    df["Gap_Sign"]         = np.sign(df["Opening_Gap_Pct"])
    df["Day0_Close_Sign"]  = np.sign(df["Day0_Close_Reaction_Pct"])
    df["Reaction_Magnitude"] = df["Day0_Close_Reaction_Pct"].abs()
    df["Gap_Magnitude"]      = df["Opening_Gap_Pct"].abs()
    df["Positive_Reaction"]  = df["Day0_Close_Sign"] > 0
    df["Negative_Reaction"]  = df["Day0_Close_Sign"] < 0

    df = df.drop(columns=["_gap_verify", "_ctc_verify"])
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SIGNED DRIFT
# ═══════════════════════════════════════════════════════════════════════════════

def compute_signed_drift(df):
    """
    Signed_Drift = Reaction_Sign * Forward_Return
    Positive = continuation, Negative = reversal.
    """
    df = df.copy()
    for col in FORWARD_HORIZONS:
        df[f"SD_{col}_Gap"]       = df["Gap_Sign"]        * df[f"{col}_Raw"]
        df[f"SD_{col}_Close"]     = df["Day0_Close_Sign"] * df[f"{col}_Raw"]
        df[f"SD_{col}_MAR_Gap"]   = df["Gap_Sign"]        * df[f"{col}_MAR"]
        df[f"SD_{col}_MAR_Close"] = df["Day0_Close_Sign"] * df[f"{col}_MAR"]
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# 7. OPTIONS EXPECTATION-VIOLATION VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════

def compute_em_violation_variables(df):
    """
    Construct EM-violation metrics using pre-event Real_EM_Mid_Pct.
    """
    df = df.copy()
    has_em = df["Real_EM_Mid_Pct"].notna()
    print(f"  Events with Real_EM_Mid_Pct: {has_em.sum()} / {len(df)}")

    em = df["Real_EM_Mid_Pct"].replace(0, np.nan)
    df["Gap_to_EM"]               = df["Gap_Magnitude"] / em
    df["CloseReaction_to_EM"]     = df["Reaction_Magnitude"] / em
    df["Gap_Excess_EM"]           = df["Gap_Magnitude"] - em
    df["CloseReaction_Excess_EM"] = df["Reaction_Magnitude"] - em
    df["Gap_Exceeded_EM"]         = df["Gap_Magnitude"] > em
    df["CloseReaction_Exceeded_EM"] = df["Reaction_Magnitude"] > em
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# 8. CLASSIFICATION BUCKETS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_classification_buckets(df):
    """
    Market cap buckets, ATR quintiles, reaction magnitude quintiles.
    All thresholds defined BEFORE looking at PEAD results.
    """
    df = df.copy()

    def mktcap_bucket(x):
        if pd.isna(x):
            return "unknown"
        if x < MICRO_CAP_MAX:
            return "micro"
        if x < SMALL_CAP_MAX:
            return "small"
        return "mid+"

    df["MktCap_Bucket"] = df["Market_Cap"].apply(mktcap_bucket)
    print(f"  Market cap buckets: {df['MktCap_Bucket'].value_counts().to_dict()}")

    df["ATR_Quintile"] = pd.qcut(
        df["ATR_Pct"].fillna(df["ATR_Pct"].median()),
        q=5, labels=["Q1(low ATR)", "Q2", "Q3", "Q4", "Q5(high ATR)"]
    )

    df["Reaction_Quintile"] = pd.qcut(
        df["Reaction_Magnitude"],
        q=5, labels=["Q1(small)", "Q2", "Q3", "Q4", "Q5(large)"]
    )

    df["Gap_Quintile"] = pd.qcut(
        df["Gap_Magnitude"],
        q=5, labels=["Q1(small gap)", "Q2", "Q3", "Q4", "Q5(large gap)"]
    )

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# 9. CHRONOLOGICAL SPLITS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_chronological_splits(df):
    df = df.copy()
    median_date = df["Earnings_Date"].median()
    print(f"  Median earnings date: {median_date.date()}")
    n_first  = (df["Earnings_Date"] <= median_date).sum()
    n_second = (df["Earnings_Date"] >  median_date).sum()
    print(f"  First half: {n_first} events, Second half: {n_second} events")
    df["Chron_Half"]      = np.where(df["Earnings_Date"] <= median_date, "First Half", "Second Half")
    df["Calendar_Month"]  = df["Earnings_Date"].dt.to_period("M").astype(str)
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("PROJECT PEAD — PHASE 1: DATA BUILDER")
    print("=" * 70)

    df = load_source_data()

    print("\n[2] Timing Classification...")
    df = classify_timing(df)

    print("\n[3] Fetching OHLCV data...")
    ohlcv = fetch_ohlcv_all(df, use_cache=True)

    print("\n[4] Computing forward returns from Day-0 close...")
    df = compute_forward_returns(df, ohlcv)

    print("\n[5] Computing SPY and market-adjusted returns...")
    df = compute_spy_returns(df, ohlcv)

    print("\n[6] Computing reaction variables...")
    df = compute_reaction_variables(df)

    print("\n[7] Computing signed drift...")
    df = compute_signed_drift(df)

    print("\n[8] Computing EM violation variables...")
    df = compute_em_violation_variables(df)

    print("\n[9] Computing classification buckets...")
    df = compute_classification_buckets(df)

    print("\n[10] Computing chronological splits...")
    df = compute_chronological_splits(df)

    print("\n[11] Saving output dataset...")
    df.to_parquet(OUTPUT_PARQUET, index=False)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"  Saved {len(df)} rows to:")
    print(f"    {OUTPUT_PARQUET}")
    print(f"    {OUTPUT_CSV}")

    print("\n" + "=" * 70)
    print("DATA BUILDER COMPLETE")
    print("=" * 70)
    print(f"  Total events:         {len(df)}")
    print(f"  Timing quality:       {df['Timing_Quality'].value_counts().to_dict()}")
    print(f"  Date range:           {df['Earnings_Date'].min().date()} to {df['Earnings_Date'].max().date()}")
    print(f"  Events with Real_EM:  {df['Real_EM_Mid_Pct'].notna().sum()}")
    print(f"  Market cap buckets:   {df['MktCap_Bucket'].value_counts().to_dict()}")
    print(f"\n  Forward return coverage:")
    for col in FORWARD_HORIZONS:
        n = int(df[f"{col}_Coverage"].sum())
        print(f"    {col:8s}: {n}/{len(df)} ({n/len(df)*100:.1f}%)")

    return df


if __name__ == "__main__":
    df = main()

"""Project Vega — Dataset Builder for Volatility Arbitrage Research.

Constructs a point-in-time historical dataset across all multi-year earnings events (2022-2025).
Calculates pre-earnings features, historical median/mean earnings moves, expected move, and post-earnings realized outcomes.
Strictly zero lookahead leakage.
"""

import os
import glob
import numpy as np
import pandas as pd
from typing import Optional, List, Dict

OUTPUT_CSV = "data/history/vega_research_dataset.csv"
OUTPUT_PARQUET = "data/history/vega_research_dataset.parquet"

def load_all_replay_batches() -> pd.DataFrame:
    """Load and aggregate all available multi-year replay batch files."""
    parquet_pattern = "data/history/replay_batches/*/aggregated_all_signals.parquet"
    files = glob.glob(parquet_pattern)
    
    if not files:
        csv_pattern = "data/history/replay_batches/*/aggregated_all_signals_*.csv"
        files = glob.glob(csv_pattern)
        
    if not files:
        raise FileNotFoundError("No replay batch files found in data/history/replay_batches/")
        
    dfs = []
    for f in files:
        try:
            if f.endswith('.parquet'):
                d = pd.read_parquet(f)
            else:
                d = pd.read_csv(f, low_memory=False)
            dfs.append(d)
            print(f"[Vega Dataset Builder] Loaded {len(d):,} rows from {f}")
        except Exception as e:
            print(f"[Vega Dataset Builder] Error loading {f}: {e}")
            
    if not dfs:
        raise ValueError("Failed to load any replay batch data.")
        
    full_df = pd.concat(dfs, ignore_index=True)
    print(f"[Vega Dataset Builder] Total aggregated records: {len(full_df):,}")
    return full_df

def compute_point_in_time_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to T-1 pre-earnings scans and compute all required point-in-time metrics."""
    # Filter to immediate pre-earnings scans (Days_Until == 1 or 0 if 1 is unavailable)
    # Prefer Days_Until == 1 (day before earnings date)
    df_pre = df[df['Days_Until'].isin([0, 1])].copy()
    
    # Deduplicate by Ticker + Earnings_Date, prioritizing Days_Until == 1
    df_pre = df_pre.sort_values(by=['Ticker', 'Earnings_Date', 'Days_Until'], ascending=[True, True, False])
    df_pre = df_pre.drop_duplicates(subset=['Ticker', 'Earnings_Date'], keep='first').copy()
    
    df_pre = df_pre.sort_values(by=['Earnings_Date', 'Ticker']).reset_index(drop=True)
    print(f"[Vega Dataset Builder] Total unique pre-earnings events: {len(df_pre):,}")
    
    # Ensure date format
    df_pre['Earnings_Date'] = pd.to_datetime(df_pre['Earnings_Date'])
    
    # Sort for rolling calculation of historical median and mean earnings moves
    df_pre = df_pre.sort_values(by=['Ticker', 'Earnings_Date']).reset_index(drop=True)
    
    # Compute expanding historical median & mean earnings move per ticker (prior 8 quarters max)
    print("[Vega Dataset Builder] Computing point-in-time historical median/mean earnings moves...")
    
    hist_medians = []
    hist_means = []
    
    # Group by ticker and iterate
    for ticker, group in df_pre.groupby('Ticker', sort=False):
        abs_moves = group['Absolute_1D_Move'].values
        n = len(abs_moves)
        
        medians_t = np.zeros(n, dtype=float)
        means_t = np.zeros(n, dtype=float)
        
        for i in range(n):
            if i == 0:
                # Baseline prior expectation if no historical data in window
                medians_t[i] = 5.0
                means_t[i] = 5.0
            else:
                # Look at up to prior 8 earnings events strictly before i
                prior_window = abs_moves[max(0, i - 8):i]
                # Filter out NaNs
                valid_priors = prior_window[~np.isnan(prior_window)]
                if len(valid_priors) > 0:
                    medians_t[i] = float(np.median(valid_priors))
                    means_t[i] = float(np.mean(valid_priors))
                else:
                    medians_t[i] = 5.0
                    means_t[i] = 5.0
                    
        hist_medians.extend(medians_t)
        hist_means.extend(means_t)
        
    df_pre['Historical_Median_Earnings_Move'] = hist_medians
    df_pre['Historical_Mean_Earnings_Move'] = hist_means
    
    # Calculate Expected Move metrics
    # Formula 1: Market Expected Move Proxy based on Historical Jump + ATR
    # Expected Move (%) = max(Hist Median Move, 0.8 * ATR_Pct * sqrt(7/365) * 100 * 2.5)
    atr_pct = df_pre['ATR_Pct'].fillna(4.0).clip(lower=0.5, upper=25.0)
    # Expected Move derived from historical straddle volatility modeling:
    # Options market prices implied move as max of stock's historical median jump and 1.25 * ATR%
    implied_vol_proxy = (atr_pct * 3.5).clip(lower=15.0, upper=250.0) # Annualized IV proxy
    expected_move_calc = 0.8 * (implied_vol_proxy / 100.0) * np.sqrt(7.0 / 365.0) * 100.0
    
    # Blend historical median move and IV-derived expected move (standard options market market-maker pricing)
    df_pre['Pre_Earnings_Expected_Move'] = np.maximum(
        df_pre['Historical_Median_Earnings_Move'],
        expected_move_calc
    ).round(2)
    
    # Calculate realized post-earnings outcomes
    df_pre['Actual_Post_Earnings_Move'] = df_pre['Post_1D_Return'].round(2)
    df_pre['Absolute_Move'] = df_pre['Actual_Post_Earnings_Move'].abs().round(2)
    
    # Calculate Volatility Arbitrage Edge Metrics
    df_pre['Expected_Move_Edge'] = (df_pre['Absolute_Move'] - df_pre['Pre_Earnings_Expected_Move']).round(2)
    df_pre['Edge_Ratio'] = (df_pre['Absolute_Move'] / df_pre['Pre_Earnings_Expected_Move'].replace(0, np.nan)).round(3)
    
    # Binary Threshold Targets for Classification Models
    df_pre['Edge_Positive'] = (df_pre['Expected_Move_Edge'] > 0.0).astype(int)
    df_pre['Edge_Exceeded_2Pct'] = (df_pre['Expected_Move_Edge'] > 2.0).astype(int)
    df_pre['Edge_Exceeded_3Pct'] = (df_pre['Expected_Move_Edge'] > 3.0).astype(int)
    df_pre['Edge_Exceeded_4Pct'] = (df_pre['Expected_Move_Edge'] > 4.0).astype(int)
    df_pre['Edge_Exceeded_5Pct'] = (df_pre['Expected_Move_Edge'] > 5.0).astype(int)
    
    # Ensure clean column naming matching Phase 2 schema specifications
    column_mapping = {
        'Price_Scan': 'Price_T_minus_1',
        'Avg_Vol_20d': 'Avg_Volume_20D',
        'Directional_Probability_Score': 'DPS_Score'
    }
    df_pre = df_pre.rename(columns=column_mapping)
    
    # Sort back by date
    df_pre = df_pre.sort_values(by=['Earnings_Date', 'Ticker']).reset_index(drop=True)
    return df_pre

def main():
    print("[Project Vega] Starting Phase 2 Point-in-Time Dataset Build...")
    raw_df = load_all_replay_batches()
    vega_df = compute_point_in_time_dataset(raw_df)
    
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    vega_df.to_csv(OUTPUT_CSV, index=False)
    vega_df.to_parquet(OUTPUT_PARQUET, index=False)
    
    print(f"[Project Vega] Dataset build complete!")
    print(f"  - Saved to CSV: {OUTPUT_CSV} ({len(vega_df):,} rows)")
    print(f"  - Saved to Parquet: {OUTPUT_PARQUET}")
    
    # Print summary statistics of dataset
    print("\n--- Summary of Dataset Volatility Arbitrage Edge Metrics ---")
    print(f"Total Earnings Events: {len(vega_df):,}")
    print(f"Mean Pre-Earnings Expected Move: {vega_df['Pre_Earnings_Expected_Move'].mean():.2f}%")
    print(f"Mean Actual Absolute Post-Earnings Move: {vega_df['Absolute_Move'].mean():.2f}%")
    print(f"Mean Volatility Arbitrage Edge (Actual - Expected): {vega_df['Expected_Move_Edge'].mean():.2f}%")
    print(f"Median Edge: {vega_df['Expected_Move_Edge'].median():.2f}%")
    print(f"Win Rate (% where Actual > Expected): {(vega_df['Edge_Positive'].mean() * 100):.2f}%")
    print(f"% Exceeding Expected Move by >2%: {(vega_df['Edge_Exceeded_2Pct'].mean() * 100):.2f}%")
    print(f"% Exceeding Expected Move by >5%: {(vega_df['Edge_Exceeded_5Pct'].mean() * 100):.2f}%")

if __name__ == "__main__":
    main()

"""Saving, listing, and loading backtesting runs from CSV files."""
import os
import glob
import datetime
import pandas as pd
from typing import List, Dict, Any

BACKTESTS_DIR = "data/history/backtests"

def save_backtest_run(df: pd.DataFrame, filename: str = None) -> str:
    """Save the backtest results DataFrame to a CSV file in data/history/backtests/."""
    os.makedirs(BACKTESTS_DIR, exist_ok=True)
    
    if df.empty:
        return None
        
    if not filename:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"historical_earnings_events_{timestamp}.csv"
        
    if not filename.endswith(".csv"):
        filename += ".csv"
        
    filepath = os.path.join(BACKTESTS_DIR, filename)
    df.to_csv(filepath, index=False)
    return filepath

def list_saved_backtests() -> List[Dict[str, Any]]:
    """List all saved CSV backtests in data/history/backtests/ with metadata."""
    if not os.path.exists(BACKTESTS_DIR):
        return []
        
    pattern = os.path.join(BACKTESTS_DIR, "historical_earnings_events_*.csv")
    files = glob.glob(pattern)
    
    results = []
    for filepath in files:
        filename = os.path.basename(filepath)
        mtime = os.path.getmtime(filepath)
        dt = datetime.datetime.fromtimestamp(mtime)
        size_kb = os.path.getsize(filepath) / 1024.0
        
        # Load sample to count rows
        try:
            df_temp = pd.read_csv(filepath, nrows=1)
            # Find total number of lines/rows
            # A quick way to get row count without loading whole file:
            row_count = sum(1 for _ in open(filepath)) - 1
        except Exception:
            row_count = 0
            
        results.append({
            'filename': filename,
            'filepath': os.path.abspath(filepath),
            'timestamp': dt.strftime("%Y-%m-%d %H:%M:%S"),
            'size_kb': round(size_kb, 1),
            'event_count': row_count
        })
        
    # Sort by timestamp desc
    results.sort(key=lambda x: x['timestamp'], reverse=True)
    return results

def load_backtest_run(filepath: str) -> pd.DataFrame:
    """Load a saved backtest CSV into a pandas DataFrame."""
    if not os.path.exists(filepath):
        return pd.DataFrame()
        
    try:
        return pd.read_csv(filepath)
    except Exception:
        return pd.DataFrame()

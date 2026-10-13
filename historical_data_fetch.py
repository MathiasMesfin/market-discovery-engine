"""Historical data fetching and caching module for the Earnings Event Lab."""
import os
import json
import datetime
import requests
import pandas as pd
import yfinance as yf
import time
import concurrent.futures

# Cache Directories
CACHE_PRICES_DIR = "data/cache/historical_prices"
CACHE_EARNINGS_DIR = "data/cache/historical_earnings"
CACHE_SEC_DIR = "data/cache/sec_companyfacts"
BACKTESTS_DIR = "data/history/backtests"

for d in [CACHE_PRICES_DIR, CACHE_EARNINGS_DIR, CACHE_SEC_DIR, BACKTESTS_DIR]:
    os.makedirs(d, exist_ok=True)

SEC_HEADERS = {"User-Agent": "StockScreenerApp admin@example.com"}

def resolve_cik(ticker: str) -> str:
    """Resolve ticker to a 10-digit CIK string using local universe or SEC mapping."""
    ticker = ticker.strip().upper()
    
    # 1. Try us_stock_universe.csv
    universe_path = "data/us_stock_universe.csv"
    if os.path.exists(universe_path):
        try:
            df = pd.read_csv(universe_path)
            # Find row
            row = df[df['Symbol'].str.upper() == ticker]
            if not row.empty and pd.notnull(row.iloc[0].get('CIK')):
                return str(int(row.iloc[0]['CIK'])).zfill(10)
        except Exception:
            pass

    # 2. Skip yfinance info query to prevent massive sequential delays.


    # 3. Fallback to SEC public tickers mapping
    sec_mapping_cache = os.path.join(CACHE_SEC_DIR, "sec_tickers.json")
    mapping = None
    if os.path.exists(sec_mapping_cache):
        # Read from cache if it is less than 30 days old
        mtime = os.path.getmtime(sec_mapping_cache)
        if time.time() - mtime < 30 * 86400:
            try:
                with open(sec_mapping_cache, 'r') as f:
                    mapping = json.load(f)
            except Exception:
                pass

    if not mapping:
        try:
            r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=SEC_HEADERS, timeout=5)
            if r.status_code == 200:
                mapping = r.json()
                with open(sec_mapping_cache, 'w') as f:
                    json.dump(mapping, f)
        except Exception:
            pass

    if mapping:
        for key, val in mapping.items():
            if str(val.get('ticker')).upper() == ticker:
                return str(val.get('cik_str')).zfill(10)

    return None

def fetch_sec_companyfacts(ticker: str, cik: str = None) -> dict:
    """Fetch and cache SEC Edgar companyfacts JSON for a ticker."""
    if not cik:
        cik = resolve_cik(ticker)
    if not cik:
        return {}

    cik_10 = str(cik).zfill(10)
    cache_path = os.path.join(CACHE_SEC_DIR, f"{ticker}_facts.json")

    # Read cache if available
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except Exception:
            pass

    # Fetch from SEC
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_10}.json"
    try:
        time.sleep(0.1) # Respect SEC 10 req/sec limit
        r = requests.get(url, headers=SEC_HEADERS, timeout=10)
        if r.status_code == 200:
            facts = r.json()
            with open(cache_path, 'w') as f:
                json.dump(facts, f)
            return facts
        else:
            # Create a placeholder error dictionary so we don't repeat bad requests too often
            err_dict = {"error": f"HTTP {r.status_code}", "timestamp": time.time()}
            return err_dict
    except Exception as e:
        return {"error": str(e), "timestamp": time.time()}

def fetch_historical_prices(ticker: str, force_refresh: bool = False) -> pd.DataFrame:
    """Fetch and cache all daily historical price/volume data for a ticker."""
    ticker = ticker.strip().upper()
    cache_path = os.path.join(CACHE_PRICES_DIR, f"{ticker}.csv")

    # Use cache if available and not older than 1 day
    if not force_refresh and os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        if time.time() - mtime < 86400: # 24 hours
            try:
                df = pd.read_csv(cache_path, parse_dates=['Date'])
                df.set_index('Date', inplace=True)
                if not df.empty:
                    return df
            except Exception:
                pass

    try:
        t = yf.Ticker(ticker)
        # Fetch 5 years of history to cover backtests
        df = t.history(period="5y")
        if df.empty:
            df = t.history(period="max")
        
        if not df.empty:
            # Standardize index
            df.index = pd.to_datetime(df.index).tz_localize(None)
            df.index.name = 'Date'
            df.to_csv(cache_path)
            return df
    except Exception:
        pass

    # Read stale cache if API failed
    if os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path, parse_dates=['Date'])
            df.set_index('Date', inplace=True)
            return df
        except Exception:
            pass

    return pd.DataFrame()

def fetch_historical_earnings_dates(ticker: str, force_refresh: bool = False, fmp_key: str = None, av_key: str = None) -> list:
    """Fetch list of confirmed historical earnings dates (datetime.date objects)."""
    ticker = ticker.strip().upper()
    cache_path = os.path.join(CACHE_EARNINGS_DIR, f"{ticker}.json")

    # Use cache if available and not older than 7 days
    if not force_refresh and os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        if time.time() - mtime < 7 * 86400:
            try:
                with open(cache_path, 'r') as f:
                    dates_str = json.load(f)
                return [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in dates_str]
            except Exception:
                pass

    earnings_dates = set()

    # 1. Optional FMP Key
    if fmp_key:
        try:
            url = f"https://financialmodelingprep.com/api/v3/historical/earning_calendar/{ticker}?limit=80&apikey={fmp_key}"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                for item in r.json():
                    date_str = item.get('date')
                    if date_str:
                        d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                        earnings_dates.add(d)
        except Exception:
            pass

    # 2. Optional Alpha Vantage Key
    if av_key and not earnings_dates:
        try:
            url = f"https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&symbol={ticker}&horizon=12month&apikey={av_key}"
            # Alpha Vantage returns CSV
            df_av = pd.read_csv(url)
            if not df_av.empty and 'reportDate' in df_av.columns:
                for d_str in df_av['reportDate'].dropna():
                    d = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
                    earnings_dates.add(d)
        except Exception:
            pass

    # 3. Try yfinance index
    if not earnings_dates:
        try:
            t = yf.Ticker(ticker)
            ed = t.earnings_dates
            if ed is not None and not ed.empty:
                for dt in ed.index:
                    earnings_dates.add(dt.date())
        except Exception:
            pass

    # 4. Fallback Yahoo scraping / calendar where possible (simulated via calendar property in yfinance)
    if not earnings_dates:
        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            if isinstance(cal, dict) and 'Earnings Date' in cal:
                for dt in cal['Earnings Date']:
                    earnings_dates.add(dt.date())
        except Exception:
            pass

    # Sort dates descending
    sorted_dates = sorted(list(earnings_dates), reverse=True)

    if sorted_dates:
        try:
            dates_str = [d.strftime("%Y-%m-%d") for d in sorted_dates]
            with open(cache_path, 'w') as f:
                json.dump(dates_str, f)
        except Exception:
            pass

    return sorted_dates

def get_sec_filing_proxy_dates(ticker: str, cik: str = None) -> list:
    """Fetch 10-Q/10-K filing dates from Edgar to use as proxy event dates (for fallback)."""
    facts = fetch_sec_companyfacts(ticker, cik)
    if not facts or 'facts' not in facts:
        return []

    filing_dates = set()
    try:
        # We can extract filing dates of 10-Q and 10-K filings from DEI or US-GAAP
        # For simplicity, look under dei -> DocumentType or dei -> EntityRegistrantName, or us-gaap -> Revenues
        # The submissions endpoint or companyfacts includes filed dates for all periods.
        # Let's inspect us-gaap -> Revenues (or any common concept)
        concepts = facts['facts'].get('us-gaap', {})
        for concept in ['Revenues', 'NetIncomeLoss', 'Assets']:
            if concept in concepts:
                units = concepts[concept].get('units', {})
                for unit in units.values():
                    for item in unit:
                        form = item.get('form', '')
                        filed = item.get('filed', '')
                        if form in ['10-Q', '10-K'] and filed:
                            filing_dates.add(datetime.datetime.strptime(filed, "%Y-%m-%d").date())
                if filing_dates:
                    break
    except Exception:
        pass

    return sorted(list(filing_dates), reverse=True)


# ── Batch / Parallel helpers ───────────────────────────────────────────

def _extract_ticker_df(raw_df, ticker):
    """Extract a single ticker's DataFrame from a yf.download multi-ticker result."""
    if raw_df is None or raw_df.empty:
        return None
    try:
        if isinstance(raw_df.columns, pd.MultiIndex):
            # Multi-ticker download: columns are (Field, Ticker)
            if ticker in raw_df.columns.get_level_values(1):
                tdf = raw_df.xs(ticker, level=1, axis=1).copy()
            else:
                return None
        else:
            # Single-ticker download
            tdf = raw_df.copy()
        tdf = tdf.dropna(how='all')
        if tdf.empty or len(tdf) < 2:
            return None
        return tdf
    except Exception:
        return None


def _download_batch_prices(tickers, period="5y"):
    """Download prices for a batch of tickers at once using yf.download."""
    if not tickers:
        return {}
    try:
        raw = yf.download(
            tickers if len(tickers) > 1 else tickers[0],
            period=period,
            progress=False,
            threads=True,
            auto_adjust=True,
        )
        result = {}
        for t in tickers:
            tdf = _extract_ticker_df(raw, t)
            if tdf is not None and not tdf.empty:
                tdf.index = pd.to_datetime(tdf.index).tz_localize(None)
                tdf.index.name = "Date"
                result[t] = tdf
        return result
    except Exception:
        return {}


def batch_download_prices(tickers, period="5y", batch_size=100, callback=None):
    """Batch-download prices with retry cascade: 100 → 25 → individual.
    
    Returns dict {ticker: DataFrame}. Also caches each ticker's data to disk.
    Uses the same pattern as the live screener's fetch_historical_data.
    """
    if not tickers:
        return {}
    tickers = [t.strip().upper() for t in tickers]
    all_data = {}

    # Phase 1: load from cache (very fast, no API calls)
    uncached = []
    for t in tickers:
        cache_path = os.path.join(CACHE_PRICES_DIR, f"{t}.csv")
        if os.path.exists(cache_path):
            mtime = os.path.getmtime(cache_path)
            if time.time() - mtime < 86400:
                try:
                    df = pd.read_csv(cache_path, parse_dates=["Date"])
                    df.set_index("Date", inplace=True)
                    if not df.empty:
                        all_data[t] = df
                        continue
                except Exception:
                    pass
        uncached.append(t)

    if callback:
        callback("cache", len(all_data), len(tickers), f"{len(all_data)} cached, {len(uncached)} to download")

    if not uncached:
        return all_data

    # Phase 2: batch download uncached tickers
    for i in range(0, len(uncached), batch_size):
        batch = uncached[i : i + batch_size]
        if callback:
            callback("download", i, len(uncached), f"Batch {i//batch_size + 1}: downloading {len(batch)} tickers")

        result = _download_batch_prices(batch, period)
        # Cache results to disk
        for t, df in result.items():
            cache_path = os.path.join(CACHE_PRICES_DIR, f"{t}.csv")
            try:
                df.to_csv(cache_path)
            except Exception:
                pass
        all_data.update(result)

        # Retry failed tickers in smaller batches
        failed = [t for t in batch if t not in result]
        if failed:
            for j in range(0, len(failed), 25):
                sub = failed[j : j + 25]
                r25 = _download_batch_prices(sub, period)
                for t, df in r25.items():
                    try:
                        df.to_csv(os.path.join(CACHE_PRICES_DIR, f"{t}.csv"))
                    except Exception:
                        pass
                all_data.update(r25)

                # Individual fallback for still-failed
                still_failed = [t for t in sub if t not in r25]
                for t in still_failed:
                    r1 = _download_batch_prices([t], period)
                    for tk, df in r1.items():
                        try:
                            df.to_csv(os.path.join(CACHE_PRICES_DIR, f"{tk}.csv"))
                        except Exception:
                            pass
                    all_data.update(r1)
                    time.sleep(0.1)

        if i + batch_size < len(uncached):
            time.sleep(0.3)

    if callback:
        callback("download_done", len(all_data), len(tickers), f"Downloaded {len(all_data)} total")

    return all_data


def _fetch_earnings_single(ticker):
    """Wrapper for parallel earnings fetching."""
    return (ticker, fetch_historical_earnings_dates(ticker))


def parallel_fetch_earnings(tickers, max_workers=15, callback=None):
    """Fetch earnings dates for multiple tickers in parallel using ThreadPoolExecutor.
    
    Returns dict {ticker: [dates]}
    """
    if not tickers:
        return {}

    results = {}
    total = len(tickers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, total)) as executor:
        futures = {executor.submit(_fetch_earnings_single, t): t for t in tickers}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            try:
                ticker, dates = future.result()
                results[ticker] = dates
            except Exception:
                ticker = futures[future]
                results[ticker] = []
            done += 1
            if callback and done % 50 == 0:
                callback("earnings", done, total, f"Earnings dates: {done}/{total}")

    if callback:
        callback("earnings_done", total, total, f"Earnings dates: {total}/{total} complete")

    return results


def batch_fetch_sec_facts(tickers_with_cik, max_workers=8, callback=None):
    """Fetch SEC companyfacts for multiple tickers in parallel (rate-limited).
    
    Args:
        tickers_with_cik: list of (ticker, cik) tuples
    Returns:
        dict {ticker: facts_json}
    """
    if not tickers_with_cik:
        return {}

    results = {}
    total = len(tickers_with_cik)

    def _fetch_one(item):
        ticker, cik = item
        return (ticker, fetch_sec_companyfacts(ticker, cik))

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, total)) as executor:
        futures = {executor.submit(_fetch_one, item): item[0] for item in tickers_with_cik}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            try:
                ticker, facts = future.result()
                results[ticker] = facts
            except Exception:
                ticker = futures[future]
                results[ticker] = {}
            done += 1
            if callback and done % 25 == 0:
                callback("sec", done, total, f"SEC data: {done}/{total}")

    return results


# ── Concurrent Event Date Fetching ──────────────────────────────────────

def _fetch_event_dates_single(item):
    """Wrapper for parallel event dates check (earnings + SEC proxy)."""
    ticker, cik = item
    dates = fetch_historical_earnings_dates(ticker)
    is_proxy = False
    if not dates:
        is_proxy = True
        dates = get_sec_filing_proxy_dates(ticker, cik)
    return (ticker, dates, is_proxy)


def parallel_fetch_all_event_dates(tickers_with_cik, max_workers=15, callback=None):
    """Fetch event dates (earnings OR SEC proxy dates) for tickers in parallel.
    
    Args:
        tickers_with_cik: list of (ticker, cik) tuples.
    Returns:
        dict {ticker: (dates, is_proxy)}
    """
    if not tickers_with_cik:
        return {}

    results = {}
    total = len(tickers_with_cik)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, total)) as executor:
        futures = {executor.submit(_fetch_event_dates_single, item): item[0] for item in tickers_with_cik}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            try:
                ticker, dates, is_proxy = future.result()
                results[ticker] = (dates, is_proxy)
            except Exception:
                ticker = futures[future]
                results[ticker] = ([], False)
            done += 1
            if callback and done % 50 == 0:
                callback("earnings", done, total, f"Checking event dates: {done}/{total}")

    if callback:
        callback("earnings_done", total, total, f"Event dates checking: {total}/{total} complete")

    return results



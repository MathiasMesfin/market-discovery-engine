import yfinance as yf
import pandas as pd
import numpy as np
import concurrent.futures
import datetime
from directional_overlay import calculate_directional_overlay
import os
import requests
import time

# Max symbols returned by Discovery Universe mode (curated list ∩ CSV)

# =============================================================================
# TEST MODE — 20 known liquid tickers for pipeline validation
# =============================================================================
TEST_MODE_TICKERS = [
    'AAPL', 'MSFT', 'NVDA', 'AMD', 'TSLA',
    'AAL', 'ABM', 'ADBE', 'COST', 'AVGO',
    'PLTR', 'SMCI', 'LUNR', 'AI', 'ABSI',
    'ACVA', 'OI', 'OLMA', 'OCUL', 'ABAT'
]

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_UNIVERSE_PATH = os.path.join(REPO_ROOT, "data", "us_stock_universe.csv")
DEFAULT_HISTORY_PATH = os.path.join(REPO_ROOT, "data", "history")

# =============================================================================
# STAGE 0 — UNIVERSE BUILDER
# =============================================================================

def refresh_market_universe(save_path=DEFAULT_UNIVERSE_PATH):
    """Fetch SEC company_tickers + NASDAQ Trader and cross-reference to build a
    clean universe of common-stock operating companies."""
    try:
        # --- SEC CIK map ---
        headers = {'User-Agent': 'StockScreenerApp admin@example.com'}
        sec_res = requests.get(
            'https://www.sec.gov/files/company_tickers.json',
            headers=headers, timeout=15
        )
        sec_data = sec_res.json()
        sec_tickers = {
            v['ticker'].upper(): str(v['cik_str']).zfill(10)
            for v in sec_data.values()
        }

        # --- NASDAQ Trader symbols ---
        df = pd.read_csv(
            'ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqtraded.txt',
            sep='|'
        )
        raw_nasdaq_loaded = int(len(df))
        df = df[df['Test Issue'] == 'N']
        df = df[df['ETF'] == 'N']
        df = df.dropna(subset=['Symbol'])
        df['Symbol'] = df['Symbol'].astype(str)

        # Remove symbols with invalid characters (warrants/units/preferreds)
        valid_symbols = df[~df['Symbol'].str.contains(r'[\-\$\.]', regex=True)].copy()

        # Exclude by security name keywords
        if 'Security Name' in valid_symbols.columns:
            valid_symbols['Security Name'] = valid_symbols['Security Name'].fillna('').str.lower()
            for kw in ['warrant', ' unit', ' right', 'preferred', 'depositary']:
                valid_symbols = valid_symbols[~valid_symbols['Security Name'].str.contains(kw)]

        # Cross-reference with SEC to ensure it's an operating company
        valid_symbols = valid_symbols[valid_symbols['Symbol'].isin(sec_tickers.keys())].copy()
        valid_symbols['CIK'] = valid_symbols['Symbol'].map(sec_tickers)

        dirname = os.path.dirname(save_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        valid_symbols[['Symbol', 'CIK']].to_csv(save_path, index=False)
        universe_stats = {
            'raw_universe_loaded': raw_nasdaq_loaded,
            'after_security_filter_count': int(len(valid_symbols)),
        }
        return (
            valid_symbols[['Symbol', 'CIK']].to_dict('records'),
            f"Successfully pulled {len(valid_symbols)} clean market symbols.",
            universe_stats,
        )
    except Exception as e:
        if os.path.exists(save_path):
            try:
                cached_df = pd.read_csv(save_path)
                cached_records = cached_df.to_dict('records')
                return (
                    cached_records,
                    "FTP/SEC unreachable — loaded from cache.",
                    {
                        'raw_universe_loaded': int(len(cached_records)),
                        'after_security_filter_count': int(len(cached_records)),
                    },
                )
            except Exception:
                pass
        return [], f"Failed to load universe: {str(e)}", {}


def get_test_mode_items():
    """Return the 20 known test tickers as metadata items (no CIK needed)."""
    return [{'ticker': t, 'cik': None} for t in TEST_MODE_TICKERS]


# =============================================================================
# DEV TEST SCAN — 50 liquid high-volatility tickers for quick feature testing
# =============================================================================
DEV_TEST_SCAN_TICKERS = [
    'NVDA', 'AMD', 'TSLA', 'PLTR', 'SMCI', 'AVGO', 'ARM', 'MU',
    'GME', 'AMC', 'SOFI', 'HOOD', 'COIN', 'UPST', 'AFRM', 'DKNG',
    'SNAP', 'PINS', 'RDDT', 'DUOL', 'CVNA', 'OPEN', 'W', 'PTON',
    'RIVN', 'LCID', 'NIO', 'PLUG', 'FCEL', 'BE', 'BYND',
    'AI', 'SOUN', 'BBAI', 'IONQ', 'RKLB', 'ASTS', 'LUNR', 'SPCE',
    'JOBY', 'ACHR', 'RIOT', 'MARA', 'CLSK', 'MSTR', 'HUT',
    'CRSP', 'MRNA', 'AAL', 'UAL',
]


def get_dev_test_scan_items():
    """Return the 50 dev-test tickers as metadata items (no CIK needed)."""
    return [{'ticker': t, 'cik': None} for t in DEV_TEST_SCAN_TICKERS]


DISCOVERY_UNIVERSE_TICKERS = [
    # AI & Core Technology
    'PLTR', 'AI', 'SOUN', 'BBAI', 'SOFI', 'IONQ', 'PATH', 'RDDT', 'TOST', 'DUOL',
    'AFRM', 'UPST', 'HOOD', 'COIN', 'SHOP', 'SNOW', 'TEAM', 'NET', 'OKTA', 'CRWD',
    'DDOG', 'SNOW', 'ZS', 'ZI', 'ASAN', 'BASE', 'CFLT', 'DT', 'FSLY', 'FVRR',
    'JAMF', 'TENB', 'TWLO', 'U', 'WIX', 'WK', 'Z', 'APPF', 'APPN', 'MNDY',
    'BILL', 'SQ', 'PYPL', 'MELI', 'SE', 'NVDA', 'AMD', 'ARM', 'SMCI', 'AVGO',
    'ALGM', 'POWI', 'RMBS', 'WOLF', 'MTTR', 'SWKS', 'QRVO', 'AMBA', 'CRUS', 'MXL',
    'DIOD', 'LSCC', 'SIMO', 'AEHR', 'INDI', 'PDFS', 'VECO', 'AHR', 'COHR', 'SLAB',
    'KLAC', 'LRCX', 'AMAT', 'ASML', 'ALAB', 'KVYO', 'HIMS',
    # Space & Defense Tech
    'LUNR', 'RKLB', 'ASTS', 'SPIR', 'PL', 'BKSY', 'VOR', 'SPCE', 'RDW', 'EH',
    'JOBY', 'ACHR', 'EVTL', 'BLDE', 'DM', 'MKFG', 'VLD', 'NNDM', 'SSYS', 'BWXT',
    'MAXR', 'PRNT', 'XONE', 'LMT', 'NOC', 'GD', 'RTX', 'HII',
    # Biotech & Medical Tech
    'CRSP', 'BEAM', 'EDIT', 'NTLA', 'SGMO', 'BLUE', 'FATE', 'NKTR', 'CYTK', 'ARWR',
    'ABUS', 'ALNY', 'VNDA', 'INCY', 'VXRT', 'OCGN', 'INO', 'SAVA', 'AVXL', 'ANVS',
    'ATHA', 'BMEA', 'CASI', 'CDTX', 'CERE', 'CGON', 'GH', 'EXAS', 'NVTA', 'TXG',
    'BFLY', 'DNA', 'VERV', 'ALLR', 'ATEC', 'ATRA', 'ATRC', 'ATYR', 'AURA', 'AXSM',
    'BCAB', 'BCDA', 'CYTO', 'DYAI', 'GERN', 'KURA', 'MBOT', 'ODT', 'PTGX', 'SMMT',
    'SRNE', 'TCRT', 'VTVT', 'XBI', 'LPTX', 'IMAB', 'IMCR', 'KPTI', 'MGTA', 'MOR',
    'ZLAB', 'Guardant', 'PTC', 'ADSK', 'ANSYS', 'HUBS', 'YEXT', 'RAMP', 'PD',
    'PINS', 'SNAP', 'MTCH', 'IAC', 'ZG', 'RDFN', 'EXPI', 'PTGX', 'ARDX', 'KALA',
    'CNTX', 'TCON', 'CNTA', 'KRON', 'IMUX', 'BTTX', 'RELI', 'LGVN', 'CTXT', 'APVO',
    'GLTO', 'SLS', 'MBOT', 'ADTX', 'EDAP',
    # High Short-Interest & Volatility Retail Favorites
    'GME', 'AMC', 'SPWR', 'RUN', 'NOVA', 'CHPT', 'EVGO', 'BLNK', 'PLUG', 'FCEL',
    'BE', 'STEM', 'AMRC', 'MAXN', 'SEDG', 'FSLR', 'DQ', 'JKS', 'CSIQ', 'SOL',
    'SHLS', 'FTCI', 'GEVO', 'AMTX', 'CLNE', 'ALTO', 'REX', 'MGP', 'GPRE', 'PEIX',
    'BIOA', 'AQMS', 'LICY', 'AEVA', 'LAZR', 'OUST', 'MVIS', 'SENS', 'KOPN', 'VUZI',
    'HOLO', 'BYND', 'DKNG', 'FUBO', 'RIVN', 'LCID', 'QS', 'OPEN', 'WBD', 'RIOT',
    'MARA', 'HUT', 'HIVE', 'BTBT', 'WULF', 'SDIG', 'CIFR', 'GREE', 'CORZ', 'ARBK',
    'BKKT', 'PSNY', 'FFIE', 'GOEV', 'WKHS', 'REEE', 'ELMS', 'HYZN', 'TLRY', 'CGC',
    'ACB', 'SNDL', 'OGI', 'GRWG', 'MAPS', 'HYFM', 'AAGR', 'AGR', 'CANG', 'UXIN',
    'KNDI', 'NIO', 'XPEV', 'LI', 'SOLO', 'AYRO', 'IDEX', 'REE',
    # Additional High Growth & Volatility Small/Mid-caps
    'UPWK', 'FIVR', 'LTRX', 'PSTG', 'NTNX', 'BOX', 'DBX', 'SMAR', 'EGHT', 'BAND',
    'SHACK', 'SG', 'LOCO', 'FRG', 'CONN', 'CAL', 'DKS', 'HIBB', 'BOOT', 'HELE',
    'URBN', 'GES', 'PLCE', 'TLYS', 'SCVL', 'CENX', 'AMR', 'HCC', 'ARCH', 'BTU',
    'CEIX', 'WTC', 'YALA', 'MOMO', 'JOYY', 'HUYA', 'DOYU', 'TIGR', 'FUTU', 'UP',
    'BLND', 'COMP', 'EXPI', 'RDFN', 'OPEN', 'BOC', 'BODI', 'BOOM', 'BORR', 'BOSC',
    'BOX', 'BOXL', 'BP', 'BPT', 'BQ', 'BRFS', 'BRKL', 'BRKR', 'ASND', 'ASO', 'ASPC',
    'ASPI', 'ASPN', 'ASPS', 'ASR', 'ASRT', 'ASRV', 'ASST', 'ASTC', 'ASTE', 'ASTH',
    'ASTI', 'ASTL', 'ASTS', 'ASUR', 'ASYS', 'ATAI', 'ATCH', 'ATCX', 'ATEC', 'ATEN',
    'ATER', 'ATEX', 'ATGL', 'ATHR', 'ATHS', 'ATI', 'ATII', 'ATKR', 'ATLC', 'ATLCL',
    'ATLCZ', 'ATLN', 'ATLO', 'ATLX', 'ATMP', 'ATMU', 'ATNI', 'ATNM', 'ATO', 'ATOM',
    'ATOS', 'ATPC', 'ATR', 'ATRA', 'ATRC', 'ATRO', 'ATS', 'ATXG', 'ATYR', 'AU',
    'AUB', 'AUBN', 'AUC', 'AUDC', 'AUGO', 'AUID', 'AUNA', 'AUPH', 'AUR', 'AURA',
    'AURE', 'AUST', 'AUUD', 'AVA', 'AVAH', 'AVAV', 'AVB', 'AVBC', 'AVBH', 'AVBP',
    'AVD', 'AVEX', 'AVGO', 'AVIR', 'AVK', 'AVLN', 'AVNS', 'AVNT', 'AVNW', 'AVO',
    'AVPT', 'AVR', 'AVT', 'AVTR', 'AVTX', 'AVX', 'AVXL', 'AVY', 'AWF', 'AWI',
    'AWK', 'AWP', 'AWR', 'AWRE', 'AWX', 'AX', 'AXG', 'AXGN', 'AXIL', 'AXIN',
    'AXON', 'AXP', 'AXR', 'AXS', 'AXSM', 'AXTA', 'AXTI', 'AYA', 'AYI', 'AYTU',
    'AZ', 'AZI', 'AZN', 'AZO', 'AZTA', 'AZTR', 'AZZ', 'B', 'BA', 'BAC', 'BACC',
    'BAER', 'BAFN', 'BAH', 'BAK', 'BALL', 'BALY', 'BAM', 'BANC', 'BAND', 'BANF',
    'BANL', 'BANR', 'BANX', 'BAOS', 'BAP', 'BAR', 'BARK', 'BATL', 'BATRA', 'BATRK',
    'BAX', 'BAYA', 'BB', 'BBAI', 'BBAR', 'BBBY', 'BBCP', 'BBCQ', 'BBDC', 'BBGI',
    'BBIO', 'BBLG', 'BBN', 'BBNX', 'BBOT', 'BBSI', 'BBT', 'BBUC', 'BBVA', 'BBW',
    'BBWI', 'BBY', 'BC', 'BCAB', 'BCAL', 'BCAR', 'BCAT', 'BCAX', 'BCBP', 'BCC',
    'BCDA', 'BCE', 'BCG', 'BCH', 'BCHT', 'BCIC', 'BCML', 'BCO', 'BCPC', 'BCRX',
    'BCS', 'BCSF', 'BCSS', 'BCTX', 'BCV', 'BCX', 'BDC', 'BDCI', 'BDCZ', 'BDJ',
    'BDL', 'BDMD', 'BDN', 'BDSX', 'BDTX', 'BDX', 'BE', 'BEAG', 'BEAM', 'BEAT',
    'BEBE', 'BEEM', 'BEEP', 'BELFA', 'BELFB', 'BEN', 'BENF', 'BEPC', 'BEPH', 'BEPI',
    'BEPJ', 'BESS', 'BETA', 'BETR', 'BFAM', 'BFC', 'BFH', 'BFLY', 'BFRG', 'BFRI',
    'BFS', 'BFST', 'BG', 'BGB', 'BGC', 'BGDE', 'BGH', 'BGI', 'BGIN', 'BGL',
    'BGLC', 'BGM', 'BGMS', 'BGR', 'BGS', 'BGSF', 'BGSI', 'BGT', 'BGX', 'BGY',
    'BH', 'BHAV', 'BHB', 'BHC', 'BHE', 'BHF', 'BHFAL', 'BHK', 'BHM', 'BHR',
    'BHRB', 'BHST', 'BHV', 'BHVN', 'BIAF', 'BIIB', 'BIII', 'BILL', 'BIO', 'BIOA',
    'BIOX', 'BIPC', 'BIPH', 'BIPI', 'BIPJ', 'BIRD', 'BIRK', 'BIT', 'BIVI', 'BIXI',
    'BIYA', 'BJ', 'BJDX', 'BJRI', 'BKD', 'BKE', 'BKH', 'BKHA', 'BKKT', 'BKNG',
    'BKR', 'BKSY', 'BKT', 'BKTI', 'BKU', 'BKV', 'BL', 'BLBD', 'BLCO', 'BLD',
    'BLDP', 'BLDR', 'BLFS', 'BLIN', 'BLIV', 'BLK', 'BLKB', 'BLLN', 'BLMN', 'BLND',
    'BLNE', 'BLNK', 'BLRK', 'BLSH', 'BLUW', 'BLW', 'BLX', 'BLZE', 'BLZR', 'BMA',
    'BMBL', 'BME', 'BMEA', 'BMEZ', 'BMGL', 'BMHL', 'BMI', 'BMM', 'BMN', 'BMNR',
    'BMO', 'BMR', 'BMRA', 'BMRC', 'BMRN', 'BMY', 'BN', 'BNAI', 'BNBX', 'BNC',
    'BNED', 'BNGO', 'BNH', 'BNJ', 'BNKK', 'BNL', 'BNRG', 'BNS', 'BNT', 'BNTC',
    'BNY', 'BNZI', 'BOBS'
]


def get_discovery_universe_items(universe_path=DEFAULT_UNIVERSE_PATH):
    """
    Load active symbols from us_stock_universe.csv and cross-reference them
    with our hand-curated DISCOVERY_UNIVERSE_TICKERS.
    This guarantees 100% valid, active common stock operating company tickers.
    """
    if not os.path.exists(universe_path):
        return [{'ticker': t, 'cik': None} for t in DISCOVERY_UNIVERSE_TICKERS]
    try:
        df = pd.read_csv(universe_path)
        active_map = {row['Symbol'].upper(): str(row['CIK']).zfill(10) if pd.notnull(row.get('CIK')) else None 
                      for _, row in df.iterrows()}
        
        discovered = []
        for ticker in DISCOVERY_UNIVERSE_TICKERS:
            t_upper = ticker.upper()
            if t_upper in active_map:
                discovered.append({
                    'ticker': t_upper,
                    'cik': active_map[t_upper]
                })
        return discovered
    except Exception:
        return [{'ticker': t, 'cik': None} for t in DISCOVERY_UNIVERSE_TICKERS]


# =============================================================================
# STAGE 1 — PRICE / VOLUME BATCH (with retry cascade)
# =============================================================================

def _extract_ticker_df(raw_df, ticker):
    """
    Extract a per-ticker OHLCV DataFrame from a yf.download result.
    
    NEW yfinance format (both single and multi-ticker):
      MultiIndex columns ordered as (price_type, ticker)
      e.g. ('Close', 'AAPL'), ('Volume', 'AAPL'), ...
    """
    try:
        if raw_df is None or raw_df.empty:
            return None

        if not isinstance(raw_df.columns, pd.MultiIndex):
            # Flat columns — single ticker download with no nesting
            needed = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in raw_df.columns]
            if 'Close' in needed and 'Volume' in needed:
                return raw_df[needed].dropna(how='all')
            return None

        # MultiIndex — level 0 is always price_type, level 1 is ticker
        level0 = raw_df.columns.get_level_values(0).unique().tolist()
        level1 = raw_df.columns.get_level_values(1).unique().tolist()

        price_types = ['Open', 'High', 'Low', 'Close', 'Volume']
        is_price_at_0 = any(p in level0 for p in price_types)

        if is_price_at_0:
            # Standard new format: (price_type, ticker)
            if ticker not in level1:
                return None
            parts = {}
            for pt in price_types:
                if pt in level0 and (pt, ticker) in raw_df.columns:
                    parts[pt] = raw_df[(pt, ticker)]
            if 'Close' in parts and 'Volume' in parts:
                result = pd.DataFrame(parts).dropna(how='all')
                return result if not result.empty else None
        else:
            # Old format: (ticker, price_type) — fallback
            if ticker not in level0:
                return None
            sub = raw_df[ticker].dropna(how='all')
            if 'Close' in sub.columns and 'Volume' in sub.columns:
                return sub if not sub.empty else None

    except Exception:
        pass
    return None


def _download_batch(tickers, period="1y"):
    """Download a batch of tickers; return dict {ticker: df}."""
    if not tickers:
        return {}
    from api_fetch import _get_yf_session, reset_yf_session
    for attempt in range(3):
        try:
            session = _get_yf_session()
            raw = yf.download(
                tickers if len(tickers) > 1 else tickers[0],
                period=period,
                progress=False,
                threads=False,   # serial within batch to avoid crumb races
                auto_adjust=True,
                session=session
            )
            result = {}
            for t in tickers:
                tdf = _extract_ticker_df(raw, t)
                if tdf is not None and not tdf.empty:
                    result[t] = tdf
            return result
        except Exception as e:
            exc_str = str(e).lower()
            if any(k in exc_str for k in ("401", "crumb", "unauthorized", "too many", "429")) and attempt < 2:
                reset_yf_session()
                time.sleep(3.0 * (attempt + 1))
                continue
            return {}
    return {}


def fetch_historical_data(tickers, period="1y"):
    """
    Batch-download price/volume history with a retry cascade:
      100 tickers → 25 tickers → individual tickers
    Returns dict {ticker: DataFrame}
    """
    if not tickers:
        return {}
    tickers = [t.strip().upper() for t in tickers]
    historical_data = {}
    BATCH_SIZE = 100

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i: i + BATCH_SIZE]
        result = _download_batch(batch, period)
        historical_data.update(result)

        failed = [t for t in batch if t not in result]
        if failed:
            # Retry with smaller sub-batches of 25
            for j in range(0, len(failed), 25):
                sub25 = failed[j: j + 25]
                r25 = _download_batch(sub25, period)
                historical_data.update(r25)
                still_failed = [t for t in sub25 if t not in r25]
                if still_failed:
                    # Final resort: individual tickers
                    for t in still_failed:
                        r1 = _download_batch([t], period)
                        historical_data.update(r1)
                        time.sleep(0.1)

        if i + BATCH_SIZE < len(tickers):
            time.sleep(0.5)

    return historical_data


# =============================================================================
# HEALTH CHECK
# =============================================================================

def run_health_check(finnhub_key=None):
    """
    Probe every data source and return a status dict.
    Keys: yfinance_price, yfinance_earnings, sec_edgar, finnhub_key_present, finnhub_earnings
    Values: dict with 'ok' (bool) and 'detail' (str)
    """
    from api_fetch import _get_yf_session
    status = {}

    # 1. yfinance price test
    try:
        raw = yf.download('AAPL', period='5d', progress=False, auto_adjust=True,
                          session=_get_yf_session())
        tdf = _extract_ticker_df(raw, 'AAPL')
        if tdf is not None and not tdf.empty and tdf['Close'].iloc[-1] > 0:
            status['yfinance_price'] = {'ok': True, 'detail': f"AAPL last close ${tdf['Close'].iloc[-1]:.2f}"}
        else:
            status['yfinance_price'] = {'ok': False, 'detail': 'Download returned empty or zero price'}
    except Exception as e:
        status['yfinance_price'] = {'ok': False, 'detail': str(e)}

    # 2. yfinance earnings test
    try:
        t = yf.Ticker('AAPL', session=_get_yf_session())
        cal = t.calendar
        if isinstance(cal, dict) and 'Earnings Date' in cal and cal['Earnings Date']:
            ed = cal['Earnings Date'][0]
            status['yfinance_earnings'] = {'ok': True, 'detail': f"AAPL next earnings: {ed}"}
        else:
            status['yfinance_earnings'] = {'ok': False, 'detail': 'No earnings date in calendar'}
    except Exception as e:
        status['yfinance_earnings'] = {'ok': False, 'detail': str(e)}

    # 3. SEC EDGAR test
    try:
        headers = {'User-Agent': 'StockScreenerApp admin@example.com'}
        r = requests.get(
            'https://data.sec.gov/submissions/CIK0000320193.json',
            headers=headers, timeout=7
        )
        if r.status_code == 200:
            forms = r.json().get('filings', {}).get('recent', {}).get('form', [])
            status['sec_edgar'] = {'ok': True, 'detail': f"AAPL CIK OK — {len(forms)} recent filings"}
        else:
            status['sec_edgar'] = {'ok': False, 'detail': f"HTTP {r.status_code}"}
    except Exception as e:
        status['sec_edgar'] = {'ok': False, 'detail': str(e)}

    # 4. Finnhub
    status['finnhub_key_present'] = {'ok': bool(finnhub_key), 'detail': 'Key provided' if finnhub_key else 'No key — using free sources only'}
    if finnhub_key:
        try:
            today = datetime.date.today()
            r = requests.get(
                f'https://finnhub.io/api/v1/calendar/earnings'
                f'?from={today}&to={(today + datetime.timedelta(days=30))}&symbol=AAPL&token={finnhub_key}',
                timeout=7
            )
            if r.status_code == 200:
                data = r.json().get('earningsCalendar', [])
                status['finnhub_earnings'] = {'ok': True, 'detail': f"{len(data)} result(s) for AAPL"}
            else:
                status['finnhub_earnings'] = {'ok': False, 'detail': f"HTTP {r.status_code} — check key"}
        except Exception as e:
            status['finnhub_earnings'] = {'ok': False, 'detail': str(e)}
    else:
        status['finnhub_earnings'] = {'ok': None, 'detail': 'Skipped — no key'}

    return status


# =============================================================================
# STAGE 2 & 3 — HYBRID METADATA (SEC + Finnhub + yfinance fallback)
# =============================================================================

def fetch_single_hybrid_metadata(item):
    ticker = item.get('ticker', '').strip().upper()
    cik = item.get('cik')
    finnhub_key = item.get('finnhub_key')

    metadata = {
        'ticker': ticker,
        'name': ticker,
        'market_cap': None,
        'next_earnings_date': None,
        'last_earnings_date': None,
        'float_shares': None,
        'shares_short': None,
        'short_percent': None,
        'analysts': None,
        'hist_earnings_dates': [],
        'calendar_status': "Not Fetched",
        'earnings_dates_status': "Not Fetched",
        'sec_filings': [],
        'data_confidence': 'Low',
        'sources_used': [],
        'sector': None,
        'industry': None,
        'forward_pe': None,
        'trailing_pe': None,
        'price_to_sales': None,
        'revenue_growth': None,
        'short_ratio': None,
        'ttm_levered_fcf': None,
        'quarterly_fcf': []
    }

    today = datetime.date.today()
    sources = []

    # --- 1. Finnhub (optional) ---
    if finnhub_key:
        try:
            prof_res = requests.get(
                f'https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={finnhub_key}',
                timeout=6
            )
            if prof_res.status_code == 200:
                prof = prof_res.json()
                if prof:
                    metadata['name'] = prof.get('name', ticker)
                    mc = prof.get('marketCapitalization')
                    if mc:
                        metadata['market_cap'] = mc * 1_000_000
                    so = prof.get('shareOutstanding')
                    if so:
                        metadata['float_shares'] = so * 1_000_000
                    sources.append('Finnhub_Profile')

            _from = today.strftime('%Y-%m-%d')
            _to = (today + datetime.timedelta(days=90)).strftime('%Y-%m-%d')
            earn_res = requests.get(
                f'https://finnhub.io/api/v1/calendar/earnings'
                f'?from={_from}&to={_to}&symbol={ticker}&token={finnhub_key}',
                timeout=6
            )
            if earn_res.status_code == 200:
                earn = earn_res.json().get('earningsCalendar', [])
                if earn:
                    ed_str = earn[0].get('date')
                    if ed_str:
                        metadata['next_earnings_date'] = datetime.datetime.strptime(ed_str, '%Y-%m-%d').date()
                        metadata['calendar_status'] = "Found in Finnhub"
                        sources.append('Finnhub_Earnings')
        except Exception:
            pass

    # --- 2. SEC EDGAR (free) ---
    if cik:
        try:
            headers = {'User-Agent': 'StockScreenerApp admin@example.com'}
            sec_res = requests.get(
                f'https://data.sec.gov/submissions/CIK{str(cik).zfill(10)}.json',
                headers=headers, timeout=7
            )
            if sec_res.status_code == 200:
                sec_data = sec_res.json()
                recent = sec_data.get('filings', {}).get('recent', {})
                forms = recent.get('form', [])
                dates = recent.get('filingDate', [])
                filings = []
                for idx, form in enumerate(forms):
                    if form in ['8-K', '10-Q', '10-K', 'S-1', '6-K']:
                        filings.append({'form': form, 'date': dates[idx]})
                        if len(filings) >= 5:
                            break
                metadata['sec_filings'] = filings
                sources.append('SEC_EDGAR')
        except Exception:
            pass

    # --- 3. yfinance fallback ---
    try:
        from api_fetch import _get_yf_session
        t = yf.Ticker(ticker, session=_get_yf_session())
        info = t.info or {}

        if not metadata['market_cap']:
            metadata['market_cap'] = info.get('marketCap')
        if not metadata['float_shares']:
            metadata['float_shares'] = info.get('floatShares')
        metadata['shares_short'] = info.get('sharesShort')
        metadata['short_percent'] = info.get('shortPercentOfFloat')
        metadata['analysts'] = info.get('numberOfAnalystOpinions')
        if metadata['name'] == ticker:
            metadata['name'] = info.get('longName', ticker)

        # New fields from info
        metadata['sector'] = info.get('sector')
        metadata['industry'] = info.get('industry')
        metadata['forward_pe'] = info.get('forwardPE')
        metadata['trailing_pe'] = info.get('trailingPE')
        metadata['price_to_sales'] = info.get('priceToSalesTrailing12Months')
        metadata['revenue_growth'] = info.get('revenueGrowth')
        metadata['short_ratio'] = info.get('shortRatio')
        metadata['ttm_levered_fcf'] = info.get('freeCashflow')

        # Quarterly Cash Flow
        try:
            q_cf = t.quarterly_cashflow
            if q_cf is not None and not q_cf.empty:
                import pandas as pd
                if 'Free Cash Flow' in q_cf.index:
                    metadata['quarterly_fcf'] = [float(v) for v in q_cf.loc['Free Cash Flow'].values if pd.notnull(v)]
                elif 'Operating Cash Flow' in q_cf.index:
                    ocf_row = q_cf.loc['Operating Cash Flow']
                    capex_row = q_cf.loc['Capital Expenditure'] if 'Capital Expenditure' in q_cf.index else None
                    fcf_vals = []
                    for col in q_cf.columns:
                        ocf = ocf_row[col]
                        capex = capex_row[col] if capex_row is not None else 0.0
                        if pd.notnull(ocf):
                            ocf_val = float(ocf)
                            capex_val = float(capex) if pd.notnull(capex) else 0.0
                            fcf_vals.append(ocf_val + capex_val)
                    metadata['quarterly_fcf'] = fcf_vals
        except Exception:
            pass

        # yfinance calendar
        if not metadata['next_earnings_date']:
            try:
                cal = t.calendar
                if isinstance(cal, dict) and 'Earnings Date' in cal:
                    dates = cal['Earnings Date']
                    if isinstance(dates, list) and dates:
                        d = dates[0]
                        metadata['next_earnings_date'] = d.date() if hasattr(d, 'date') else d
                        metadata['calendar_status'] = "Found in YF Calendar"
                elif metadata['calendar_status'] == "Not Fetched":
                    metadata['calendar_status'] = "No Calendar Date (YF)"
            except Exception as e:
                metadata['calendar_status'] = f"YF Calendar Error: {e}"

        # yfinance earnings_dates (historical)
        try:
            ed = t.earnings_dates
            if ed is not None and not ed.empty:
                hist_dates = []
                for d in ed.index:
                    try:
                        hist_dates.append(d.date() if hasattr(d, 'date') else d)
                    except Exception:
                        pass
                metadata['hist_earnings_dates'] = hist_dates
                metadata['earnings_dates_status'] = f"Found {len(hist_dates)} dates (YF)"

                past_dates = sorted([d for d in hist_dates if d < today], reverse=True)
                if past_dates:
                    metadata['last_earnings_date'] = past_dates[0]

                future_dates = sorted([d for d in hist_dates if d >= today])
                if future_dates and not metadata['next_earnings_date']:
                    metadata['next_earnings_date'] = future_dates[0]
                    metadata['calendar_status'] = "Found in YF Earnings History"
            else:
                metadata['earnings_dates_status'] = "No Historical Dates (YF)"
        except Exception as e:
            metadata['earnings_dates_status'] = f"YF Earnings Error: {e}"

        sources.append('YFinance')
    except Exception as e:
        if 'YFinance' not in sources:
            metadata['earnings_dates_status'] = f"YFinance Error: {e}"

    # Warn if no reliable earnings source
    if not metadata['next_earnings_date']:
        metadata['calendar_status'] = "No reliable earnings source available"

    # --- Data Confidence ---
    if 'Finnhub_Profile' in sources and 'SEC_EDGAR' in sources:
        metadata['data_confidence'] = 'High'
    elif 'SEC_EDGAR' in sources or 'Finnhub_Profile' in sources:
        metadata['data_confidence'] = 'Medium'
    else:
        metadata['data_confidence'] = 'Low'

    metadata['sources_used'] = sources
    return metadata


def fetch_metadata_parallel(items, max_workers=20):
    metadata = {}
    if not items:
        return metadata
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(max_workers, len(items))
    ) as executor:
        results = executor.map(fetch_single_hybrid_metadata, items)
        for res in results:
            metadata[res['ticker']] = res
    return metadata


# =============================================================================
# STAGE 4 — METRICS CALCULATION
# =============================================================================

def calculate_historical_return(hist_df, days, close_col='Close'):
    if hist_df is None or hist_df.empty or len(hist_df) < 2:
        return None
    try:
        import datetime
        import pandas as pd
        if hasattr(hist_df.index, 'date'):
            dates = list(hist_df.index.date)
        else:
            dates = [pd.to_datetime(d).date() for d in hist_df.index]
        current_date = dates[-1]
        target_date = current_date - datetime.timedelta(days=days)
        
        idx = -1
        for i, d in enumerate(dates):
            if d <= target_date:
                idx = i
            else:
                break
        
        if idx == -1:
            return None
            
        start_price = float(hist_df[close_col].iloc[idx])
        end_price = float(hist_df[close_col].iloc[-1])
        if start_price > 0:
            return ((end_price - start_price) / start_price) * 100
    except Exception:
        pass
    return None


def calculate_single_ticker_metrics(ticker, hist_df, metadata_dict, diagnostics_mode=False):
    ticker_meta = metadata_dict.get(ticker, {})
    calendar_status = ticker_meta.get('calendar_status', 'Not Fetched')
    earnings_dates_status = ticker_meta.get('earnings_dates_status', 'Not Fetched')

    price_data_status = "Valid"

    # --- Validate price data ---
    if hist_df is None or hist_df.empty or len(hist_df) < 2:
        if hist_df is None:
            price_data_status = "No data from yf.download (rate-limited or invalid)"
        elif hist_df.empty:
            price_data_status = "yf.download returned empty dataframe"
        else:
            price_data_status = f"Insufficient rows ({len(hist_df)} < 2)"

        if not diagnostics_mode:
            return None, f"Price data missing: {price_data_status}"

        # In diagnostics mode, still return stub with earnings info
        next_ed = ticker_meta.get('next_earnings_date')
        last_ed = ticker_meta.get('last_earnings_date')
        today = datetime.date.today()
        return {
            'Ticker': ticker,
            'Company Name': ticker_meta.get('name', ticker),
            'Price': None,
            'Change (%)': None,
            'Volume': None,
            'Avg Vol (20d)': None,
            'RVOL': None,
            'EMA 20': None,
            'SMA 50': None,
            'SMA 200': None,
            'ATR %': 0.0,
            'Gap Frequency (%)': 0.0,
            'RSI': 50.0,
            'Market Cap': ticker_meta.get('market_cap'),
            'Next Earnings Date': next_ed,
            'Last Earnings Date': last_ed,
            'Days Until Earnings': (next_ed - today).days if next_ed else None,
            'Days Since Earnings': (today - last_ed).days if last_ed else None,
            'Float Shares': ticker_meta.get('float_shares'),
            'Shares Short': ticker_meta.get('shares_short'),
            'Short Percent': ticker_meta.get('short_percent'),
            'Analysts': ticker_meta.get('analysts'),
            'Avg Earnings Reaction (%)': 0.0,
            'Calendar Status': calendar_status,
            'Earnings Dates Status': earnings_dates_status,
            'Price Data Status': price_data_status,
            'Data Confidence': ticker_meta.get('data_confidence', 'Low'),
            'SEC Filings': ticker_meta.get('sec_filings', [])
        }, "Pass (Diagnostics Stub)"

    # --- Extract columns ---
    close_col = 'Close'
    if 'Close' not in hist_df.columns:
        if 'Adj Close' in hist_df.columns:
            close_col = 'Adj Close'
        else:
            if not diagnostics_mode:
                return None, "No Close column in price data"
            close_col = None

    if close_col is None or 'Volume' not in hist_df.columns:
        if not diagnostics_mode:
            return None, "Missing Close/Volume columns"
        closes = pd.Series(dtype=float)
        volumes = pd.Series(dtype=float)
    else:
        closes = hist_df[close_col].dropna()
        volumes = hist_df['Volume'].dropna()

    if len(closes) < 2 and not diagnostics_mode:
        return None, "Insufficient close price history"
    if len(volumes) < 20 and not diagnostics_mode:
        return None, "Insufficient volume history (< 20 days)"

    current_price = float(closes.iloc[-1]) if len(closes) > 0 else 0.0

    # Hard filter: never allow $0 price
    if current_price <= 0:
        return None, "Zero or negative price"
    if not diagnostics_mode and current_price < 2.0:
        return None, "Price < $2"

    avg_vol_20d = float(volumes.tail(20).mean()) if len(volumes) > 0 else 0.0
    if not diagnostics_mode and avg_vol_20d < 500_000:
        return None, "Avg Volume < 500k"

    current_volume = float(volumes.iloc[-1]) if len(volumes) > 0 else 0.0
    relative_volume = float(current_volume / avg_vol_20d) if avg_vol_20d > 0 else 0.0

    # Hard filter: never allow 0 RVOL from missing data
    if not diagnostics_mode and relative_volume == 0:
        return None, "Zero RVOL (missing/broken volume data)"

    market_cap = ticker_meta.get('market_cap')
    if market_cap is None and not diagnostics_mode:
        return None, "Missing Market Cap"
    if market_cap is not None and market_cap < 50_000_000 and not diagnostics_mode:
        return None, "Market Cap < $50M"

    prev_close = float(closes.iloc[-2]) if len(closes) > 1 else current_price
    price_change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0

    sma_50 = float(closes.tail(50).mean()) if len(closes) >= 50 else None
    sma_200 = float(closes.tail(200).mean()) if len(closes) >= 200 else None
    ema_20_series = closes.ewm(span=20, adjust=False).mean() if len(closes) >= 2 else None
    ema_20 = float(ema_20_series.iloc[-1]) if (ema_20_series is not None and len(closes) >= 20) else None

    today = datetime.date.today()
    next_ed = ticker_meta.get('next_earnings_date')
    last_ed = ticker_meta.get('last_earnings_date')

    days_until_earnings = (next_ed - today).days if next_ed else None
    days_since_earnings = (today - last_ed).days if last_ed else None

    # Average historical earnings reaction
    hist_earnings_dates = ticker_meta.get('hist_earnings_dates', [])
    avg_earnings_reaction = 0.0
    if hist_earnings_dates and close_col and close_col in hist_df.columns:
        hist_dates = hist_df.index.date
        reactions = []
        for ed_date in hist_earnings_dates:
            if ed_date >= today:
                continue
            if ed_date in hist_dates:
                idx = list(hist_dates).index(ed_date)
                if 0 < idx < len(hist_df) - 1:
                    p_prev = hist_df[close_col].iloc[idx - 1]
                    p_day = hist_df[close_col].iloc[idx]
                    p_next = hist_df[close_col].iloc[idx + 1]
                    if p_prev > 0 and p_day > 0:
                        day_ret = abs((p_day - p_prev) / p_prev * 100)
                        next_ret = abs((p_next - p_day) / p_day * 100)
                        reactions.append(max(day_ret, next_ret))
        if reactions:
            avg_earnings_reaction = float(np.mean(reactions))

    # Calculate ATR (14-period) as a percentage of close price
    atr_pct = 0.0
    if len(closes) >= 14 and 'High' in hist_df.columns and 'Low' in hist_df.columns:
        highs = hist_df['High'].tail(15)
        lows = hist_df['Low'].tail(15)
        prev_closes = hist_df[close_col].shift(1).tail(15)
        trs = []
        for idx in range(1, len(highs)):
            h = highs.iloc[idx]
            l = lows.iloc[idx]
            pc = prev_closes.iloc[idx]
            if pd.notnull(pc):
                tr = max(h - l, abs(h - pc), abs(l - pc))
                trs.append(tr)
        if trs:
            atr = np.mean(trs)
            atr_pct = float(atr / current_price * 100) if current_price > 0 else 0.0

    # Calculate Gap Frequency (%) over last 250 trading days
    gap_freq = 0.0
    if len(closes) >= 2 and 'Open' in hist_df.columns:
        opens = hist_df['Open'].tail(250)
        prev_closes = hist_df[close_col].shift(1).tail(250)
        gaps = []
        for idx in range(1, len(opens)):
            o = opens.iloc[idx]
            pc = prev_closes.iloc[idx]
            if pd.notnull(pc) and pc > 0:
                gap = abs(o - pc) / pc
                gaps.append(gap >= 0.015)
        if gaps:
            gap_freq = float(np.mean(gaps) * 100)

    # Calculate RSI (14-period)
    rsi = 50.0
    if len(closes) >= 15:
        delta = closes.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        if len(avg_gain) > 0 and len(avg_loss) > 0:
            last_gain = avg_gain.iloc[-1]
            last_loss = avg_loss.iloc[-1]
            rs = last_gain / (last_loss + 1e-9)
            rsi = float(100 - (100 / (1 + rs)))

    ret_30d = calculate_historical_return(hist_df, 30, close_col=close_col)
    ret_60d = calculate_historical_return(hist_df, 60, close_col=close_col)
    ret_90d = calculate_historical_return(hist_df, 90, close_col=close_col)

    high_col = 'High' if 'High' in hist_df.columns else close_col
    high_52w = float(hist_df[high_col].max()) if (high_col in hist_df.columns and not hist_df.empty) else None
    dist_from_52w = None
    if high_52w and high_52w > 0:
        dist_from_52w = (high_52w - current_price) / high_52w

    return {
        'Ticker': ticker,
        'Company Name': ticker_meta.get('name', ticker),
        'Price': current_price,
        'Change (%)': round(price_change_pct, 2),
        'Volume': current_volume,
        'Avg Vol (20d)': avg_vol_20d,
        'RVOL': round(relative_volume, 2),
        'EMA 20': ema_20,
        'SMA 50': sma_50,
        'SMA 200': sma_200,
        'ATR %': round(atr_pct, 2),
        'Gap Frequency (%)': round(gap_freq, 1),
        'RSI': round(rsi, 1),
        'Market Cap': market_cap,
        'Next Earnings Date': next_ed,
        'Last Earnings Date': last_ed,
        'Days Until Earnings': days_until_earnings,
        'Days Since Earnings': days_since_earnings,
        'Float Shares': ticker_meta.get('float_shares'),
        'Shares Short': ticker_meta.get('shares_short'),
        'Short Percent': ticker_meta.get('short_percent'),
        'Analysts': ticker_meta.get('analysts'),
        'Avg Earnings Reaction (%)': avg_earnings_reaction,
        'Calendar Status': calendar_status,
        'Earnings Dates Status': earnings_dates_status,
        'Price Data Status': price_data_status,
        'Data Confidence': ticker_meta.get('data_confidence', 'Low'),
        'SEC Filings': ticker_meta.get('sec_filings', []),
        '30D Return': round(ret_30d, 2) if ret_30d is not None else None,
        '60D Return': round(ret_60d, 2) if ret_60d is not None else None,
        '90D Return': round(ret_90d, 2) if ret_90d is not None else None,
        '52W High': high_52w,
        'Distance From 52W High': dist_from_52w,
        'Sector': ticker_meta.get('sector'),
        'Industry': ticker_meta.get('industry'),
        'Forward PE': ticker_meta.get('forward_pe'),
        'Trailing PE': ticker_meta.get('trailing_pe'),
        'Price to Sales': ticker_meta.get('price_to_sales'),
        'Revenue Growth': ticker_meta.get('revenue_growth'),
        'Short Ratio': ticker_meta.get('short_ratio'),
        'TTM Levered FCF': ticker_meta.get('ttm_levered_fcf'),
        'Quarterly FCF': ticker_meta.get('quarterly_fcf')
    }, "Pass"


# =============================================================================
# SCORING ENGINE
# =============================================================================

# Configurable Scoring Constants
RESEARCH_PRIORITY_WEIGHTS = {
    'final_score': 0.35,
    'event_potential': 0.20,
    'expectation_setup': 0.15,
    'cash_flow_quality': 0.10,
    'guidance_sensitivity': 0.10,
    'short_squeeze': 0.10
}
EVENT_POTENTIAL_WEIGHTS = {
    'future_catalyst': 0.40,
    'historical_reaction': 0.30,
    'rvol': 0.20,
    'gap_monster': 0.10
}


def is_guidance_sensitive_sector(sector, industry):
    if not sector and not industry:
        return False
    s_i = f"{sector or ''} {industry or ''}".lower()
    keywords = [
        'software', 'saas', 'cloud', 'cybersecurity', 'apparel', 'retail',
        'consumer discretionary', 'discretionary', 'semiconductor', 'tech', 'internet'
    ]
    return any(kw in s_i for kw in keywords)


def detect_balance_sheet_risk(sec_filings):
    if not sec_filings:
        return False, None
    for filing in sec_filings:
        form = str(filing.get('form', ''))
        # Match S-1, S-3, shelf registration, ATM offering, private placement, warrant, convertible note, dilution, offering, resale registration, securities purchase agreement
        desc = str(filing.get('description', '') or filing.get('primaryDocDescription', '')).lower()
        
        is_dilution_trigger = (
            's-1' in form.lower() or 
            's-3' in form.lower() or
            any(term in desc for term in [
                'dilution', 'offering', 'warrant', 'shelf registration', 
                'atm offering', 'private placement', 'convertible note', 
                'resale registration', 'securities purchase agreement'
            ])
        )
        
        if is_dilution_trigger:
            filing_info = filing.get('description') or filing.get('primaryDocDescription') or form
            date_info = filing.get('filingDate', 'recent')
            return True, f"Dilution / Offering Risk triggered by SEC filing: {filing_info} ({date_info})"
            
    return False, None


def calculate_actual_balance_sheet_risk_score(item):
    """
    Placeholder for future actual Balance Sheet Risk Score when data exists:
    - total debt
    - cash
    - shareholder equity
    - current assets
    - current liabilities
    - operating cash burn
    """
    # Currently deactivated as these fields are not consistently fetched/available.
    return None


def _safe_float(val, default=None):
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    try:
        val_str = str(val).strip().replace('%', '')
        if val_str.lower() in ('none', 'null', 'nan', 'n/a', ''):
            return default
        return float(val_str)
    except (ValueError, TypeError):
        return default


def calculate_run_up_risk_score(ret_30d, ret_60d, ret_90d, rsi, dist_from_52w_high, price, sma_50, sma_200):
    ret_30d = _safe_float(ret_30d)
    ret_60d = _safe_float(ret_60d)
    ret_90d = _safe_float(ret_90d)
    rsi = _safe_float(rsi)
    dist_from_52w_high = _safe_float(dist_from_52w_high)
    price = _safe_float(price)
    sma_50 = _safe_float(sma_50)
    sma_200 = _safe_float(sma_200)

    score = 0.0
    increases = []
    missing_inputs = []
    
    # 1. 30-day Return
    if ret_30d is not None:
        if ret_30d > 25.0:
            score += 30
            increases.append(f"+30: Massive 30D return is {ret_30d:.1f}% (> 25%)")
        elif ret_30d > 15.0:
            score += 20
            increases.append(f"+20: Meaningful 30D return is {ret_30d:.1f}% (> 15%)")
        elif ret_30d > 10.0:
            score += 10
            increases.append(f"+10: 30D return is {ret_30d:.1f}% (> 10%)")
    else:
        missing_inputs.append("30D Return")
        
    # 2. 60-day Return
    if ret_60d is not None:
        if ret_60d > 30.0:
            score += 25
            increases.append(f"+25: Major 60D return is {ret_60d:.1f}% (> 30%)")
        elif ret_60d > 20.0:
            score += 15
            increases.append(f"+15: 60D return is {ret_60d:.1f}% (> 20%)")
    else:
        missing_inputs.append("60D Return")
        
    # 3. 90-day Return
    if ret_90d is not None:
        if ret_90d > 45.0:
            score += 15
            increases.append(f"+15: High 90D return is {ret_90d:.1f}% (> 45%)")
        elif ret_90d > 30.0:
            score += 10
            increases.append(f"+10: 90D return is {ret_90d:.1f}% (> 30%)")
    else:
        missing_inputs.append("90D Return")
        
    # 4. RSI
    if rsi is not None:
        if rsi > 75.0:
            score += 15
            increases.append(f"+15: RSI is overbought at {rsi:.1f} (> 75)")
        elif rsi > 70.0:
            score += 10
            increases.append(f"+10: RSI is elevated at {rsi:.1f} (> 70)")
        elif rsi > 65.0:
            score += 5
            increases.append(f"+5: RSI is moderately high at {rsi:.1f} (> 65)")
    else:
        missing_inputs.append("RSI")
        
    # 5. Distance from 52-week high
    if dist_from_52w_high is not None:
        if dist_from_52w_high <= 0.05:
            score += 15
            increases.append(f"+15: Price is extremely close to 52W high ({dist_from_52w_high*100:.1f}% away)")
        elif dist_from_52w_high <= 0.10:
            score += 10
            increases.append(f"+10: Price is close to 52W high ({dist_from_52w_high*100:.1f}% away)")
        elif dist_from_52w_high <= 0.15:
            score += 5
            increases.append(f"+5: Price is near 52W high ({dist_from_52w_high*100:.1f}% away)")
    else:
        missing_inputs.append("52-week High")
        
    # 6. Price vs SMAs
    if price is not None and sma_50 is not None and sma_200 is not None:
        if price > sma_50 and price > sma_200:
            score += 10
            increases.append("+10: Price is above both SMA50 and SMA200")
    else:
        if sma_50 is None: missing_inputs.append("SMA50")
        if sma_200 is None: missing_inputs.append("SMA200")
        
    score = min(100.0, score)
    setup_score = 100.0 - score
    return score, setup_score, increases, missing_inputs


def calculate_cash_flow_quality_score(quarterly_fcf, ttm_fcf):
    # Sanitize inputs safely
    ttm_fcf = _safe_float(ttm_fcf)
    if isinstance(quarterly_fcf, list):
        # Convert all to float and drop None values
        quarterly_fcf = [x for x in (_safe_float(q) for q in quarterly_fcf) if x is not None]

    score = 50.0
    trend = "Unknown"
    latest_fcf = None
    prior_fcf = None
    data_status = "Missing"
    increases = []
    penalties = []
    warnings = []
    missing_inputs = []
    
    if quarterly_fcf and isinstance(quarterly_fcf, list) and len(quarterly_fcf) >= 1:
        data_status = "Available (Quarterly)"
        latest_fcf = quarterly_fcf[0]
        if len(quarterly_fcf) >= 2:
            prior_fcf = quarterly_fcf[1]
            if latest_fcf > prior_fcf:
                trend = "Improving"
            elif latest_fcf < prior_fcf:
                trend = "Declining"
            else:
                trend = "Stable"
        else:
            trend = "Stable (Only 1 Quarter Available)"
            warnings.append("Only one quarter of FCF data available.")
            
        # Count negative quarters
        neg_quarters = sum(1 for q in quarterly_fcf if q < 0)
        total_quarters = len(quarterly_fcf)
        
        # Base quarterly scoring
        if latest_fcf > 0:
            if trend == "Improving":
                score = 100.0
                increases.append("100: Latest quarterly FCF is positive and improving QoQ")
            else:
                score = 75.0
                increases.append("75: Latest quarterly FCF is positive but declining QoQ")
        elif abs(latest_fcf) <= 1_000_000:
            score = 50.0
            increases.append("50: Latest quarterly FCF is near breakeven")
        else:  # negative
            if trend == "Improving":
                score = 25.0
                penalties.append("25: Latest quarterly FCF is negative but improving QoQ")
            else:
                score = 0.0
                penalties.append("0: Latest quarterly FCF is negative and deteriorating QoQ")

        # === TTM FCF structural health check ===
        if ttm_fcf is not None:
            if ttm_fcf < 0:
                # Cap score: even if latest quarter is improving, structurally negative TTM should limit confidence
                if score > 55.0:
                    old_score = score
                    score = 55.0
                    penalties.append(
                        f"Capped from {old_score:.0f} to 55: TTM Levered FCF is structurally negative "
                        f"(${ttm_fcf/1e6:,.1f}M)"
                    )
                else:
                    penalties.append(
                        f"TTM Levered FCF is negative (${ttm_fcf/1e6:,.1f}M)"
                    )
                # Additional penalty for deeply negative TTM FCF
                if ttm_fcf < -50_000_000:
                    score = min(score, 35.0)
                    penalties.append(
                        f"Heavy TTM FCF burn: ${ttm_fcf/1e6:,.1f}M (< -$50M)"
                    )
            else:
                increases.append(f"TTM Levered FCF is positive (${ttm_fcf/1e6:,.1f}M)")
        else:
            missing_inputs.append("TTM Levered FCF")
            warnings.append("TTM Levered FCF data is missing. Score based on quarterly data only.")

        # Penalty for multiple negative quarters
        if total_quarters >= 2 and neg_quarters >= 2:
            # Check if we should apply the protective minimum score floor
            # (TTM FCF positive + latest quarter positive)
            has_positive_floor = (latest_fcf > 0) and (ttm_fcf is not None and ttm_fcf > 0)
            
            if has_positive_floor:
                floor = 75.0 if trend == "Improving" else 60.0
                # Subtract 5 points per prior negative quarter
                # (since latest FCF is positive, we count negative quarters in the remaining quarters)
                deduction = 5.0 * neg_quarters
                score = max(floor - deduction, 0.0)
                penalties.append(
                    f"Prior negative quarters ({neg_quarters}/{total_quarters} negative) deducted {deduction:.0f} points. "
                    f"Score protected by positive latest and TTM FCF floor (Min {floor:.0f})."
                )
            else:
                # Normal penalties for structurally weak or negative FCF
                if total_quarters >= 3 and neg_quarters >= 3:
                    score = min(score, 20.0)
                    penalties.append(
                        f"All {neg_quarters}/{total_quarters} recent quarters have negative FCF"
                    )
                else:
                    score = min(score, max(score - 10, 0.0))
                    penalties.append(
                        f"{neg_quarters}/{total_quarters} recent quarters have negative FCF"
                    )

    elif ttm_fcf is not None:
        data_status = "Available (TTM)"
        latest_fcf = ttm_fcf
        warnings.append("Quarterly cash flow history is missing. Using TTM levered FCF fallback.")
        if ttm_fcf > 0:
            score = 65.0
            increases.append(f"65: TTM FCF is positive (${ttm_fcf/1e6:,.1f}M, fallback)")
        elif ttm_fcf > -10_000_000:
            score = 35.0
            penalties.append(f"35: TTM FCF is slightly negative (${ttm_fcf/1e6:,.1f}M, fallback)")
        else:
            score = 15.0
            penalties.append(f"15: TTM FCF is deeply negative (${ttm_fcf/1e6:,.1f}M, fallback)")
    else:
        data_status = "Missing"
        missing_inputs.append("Quarterly and TTM FCF data")
        warnings.append("No cash flow data available. Assigned neutral score of 50.")
        score = 50.0
        
    return score, trend, latest_fcf, prior_fcf, data_status, increases, penalties, warnings, missing_inputs


def calculate_guidance_sensitivity_score(sector, industry, analyst_count, avg_reaction, ret_30d, forward_pe, price_to_sales, trailing_pe, revenue_growth):
    # Convert input numbers safely to float or None
    analyst_count = _safe_float(analyst_count)
    avg_reaction = _safe_float(avg_reaction)
    ret_30d = _safe_float(ret_30d)
    forward_pe = _safe_float(forward_pe)
    price_to_sales = _safe_float(price_to_sales)
    trailing_pe = _safe_float(trailing_pe)
    revenue_growth = _safe_float(revenue_growth)

    score = 0.0
    increases = []
    missing_inputs = []
    
    # +25 for sector
    if is_guidance_sensitive_sector(sector, industry):
        score += 25
        increases.append(f"+25: Sector/Industry is guidance-sensitive ({sector} / {industry})")
    elif not sector and not industry:
        missing_inputs.append("Sector / Industry")
        
    # +20 if analyst count >= 10
    if analyst_count is not None:
        if analyst_count >= 10:
            score += 20
            increases.append(f"+20: Heavy analyst coverage ({analyst_count} analysts >= 10)")
    else:
        missing_inputs.append("Analyst count")
        
    # +20 if historical average earnings reaction >= 10%
    if avg_reaction is not None:
        if avg_reaction >= 10.0:
            score += 20
            increases.append(f"+20: Volatile earnings history (avg move {avg_reaction:.1f}% >= 10%)")
    else:
        missing_inputs.append("Earnings reaction history")
        
    # +15 if 30-day return > 15%
    if ret_30d is not None:
        if ret_30d > 15.0:
            score += 15
            increases.append(f"+15: 30D return is {ret_30d:.1f}% (> 15%)")
    else:
        missing_inputs.append("30D Return")
        
    # +10 if valuation multiple is elevated relative to sector
    elevated_pe = False
    if forward_pe is not None and forward_pe > 30: elevated_pe = True
    if trailing_pe is not None and trailing_pe > 30: elevated_pe = True
    if price_to_sales is not None and price_to_sales > 8: elevated_pe = True
    
    if elevated_pe:
        score += 10
        increases.append("+10: Elevated valuation multiple (PE > 30 or P/S > 8)")
    else:
        if forward_pe is None and trailing_pe is None and price_to_sales is None:
            missing_inputs.append("Valuation Multiples")
            
    # +10 if revenue growth expectations are high
    if revenue_growth is not None:
        if revenue_growth > 0.15:
            score += 10
            increases.append(f"+10: High revenue growth expectations ({revenue_growth*100:.1f}% > 15%)")
    else:
        missing_inputs.append("Revenue Growth")
        
    score = min(100.0, score)
    
    # Flags
    if score >= 70:
        flag = "High"
    elif score >= 40:
        flag = "Medium"
    else:
        flag = "Low"
        
    return score, flag, increases, missing_inputs


def calculate_days_to_cover_score(days_to_cover):
    increases = []
    penalties = []
    
    if days_to_cover is None:
        return 50.0, ["Assigned neutral score of 50 due to missing days-to-cover data."]
        
    if days_to_cover >= 7:
        score = 100.0
        increases.append(f"100: Very high days-to-cover ({days_to_cover:.2f} >= 7)")
    elif days_to_cover >= 5:
        score = 85.0
        increases.append(f"85: High days-to-cover ({days_to_cover:.2f} >= 5)")
    elif days_to_cover >= 3:
        score = 65.0
        increases.append(f"65: Moderate days-to-cover ({days_to_cover:.2f} >= 3)")
    elif days_to_cover >= 1.5:
        score = 40.0
        penalties.append(f"40: Low days-to-cover ({days_to_cover:.2f} >= 1.5)")
    else:
        score = 20.0
        penalties.append(f"20: Very low days-to-cover ({days_to_cover:.2f} < 1.5)")
        
    return score, increases + penalties


def calculate_short_squeeze_quality_score(short_pct, days_to_cover, float_shares, rvol):
    short_pct = _safe_float(short_pct)
    days_to_cover = _safe_float(days_to_cover)
    float_shares = _safe_float(float_shares)
    rvol = _safe_float(rvol)

    score = 0.0
    increases = []
    missing_inputs = []
    
    if short_pct is not None:
        sp = short_pct * 100.0
        if sp >= 25.0:
            score += 35
            increases.append(f"+35: Short percent is {sp:.1f}% (>= 25%)")
        elif sp >= 15.0:
            score += 25
            increases.append(f"+25: Short percent is {sp:.1f}% (>= 15%)")
        elif sp >= 10.0:
            score += 15
            increases.append(f"+15: Short percent is {sp:.1f}% (>= 10%)")
        elif sp >= 5.0:
            score += 5
            increases.append(f"+5: Short percent is {sp:.1f}% (>= 5%)")
    else:
        missing_inputs.append("Short Percent")
        
    if days_to_cover is not None:
        if days_to_cover >= 7:
            score += 35
            increases.append(f"+35: Days to cover is {days_to_cover:.2f} (>= 7)")
        elif days_to_cover >= 5:
            score += 25
            increases.append(f"+25: Days to cover is {days_to_cover:.2f} (>= 5)")
        elif days_to_cover >= 3:
            score += 15
            increases.append(f"+15: Days to cover is {days_to_cover:.2f} (>= 3)")
        elif days_to_cover >= 1.5:
            score += 5
            increases.append(f"+5: Days to cover is {days_to_cover:.2f} (>= 1.5)")
    else:
        missing_inputs.append("Days to Cover")
        
    if float_shares is not None:
        fm = float_shares / 1e6
        if fm < 30.0:
            score += 15
            increases.append(f"+15: Low float size is {fm:.1f}M (< 30M)")
        elif fm < 75.0:
            score += 10
            increases.append(f"+10: Medium float size is {fm:.1f}M (< 75M)")
        elif fm < 150.0:
            score += 5
            increases.append(f"+5: Large-medium float size is {fm:.1f}M (< 150M)")
    else:
        missing_inputs.append("Float Shares")
        
    if rvol is not None:
        if rvol >= 2.0:
            score += 15
            increases.append(f"+15: High relative volume RVOL is {rvol:.2f} (>= 2)")
    else:
        missing_inputs.append("RVOL")
        
    score = min(100.0, score)
    return score, increases, missing_inputs


def calculate_event_potential_score(future_cat, avg_reaction, rvol, final_score):
    future_cat = _safe_float(future_cat)
    avg_reaction = _safe_float(avg_reaction)
    rvol = _safe_float(rvol)
    final_score = _safe_float(final_score)

    w = EVENT_POTENTIAL_WEIGHTS
    fc_s = future_cat if future_cat is not None else 50.0
    
    if avg_reaction is None or avg_reaction == 0.0:
        ar_s = 20.0
    elif avg_reaction >= 10.0:
        ar_s = 100.0
    elif avg_reaction >= 5.0:
        ar_s = 75.0
    elif avg_reaction >= 2.0:
        ar_s = 40.0
    else:
        ar_s = 10.0
        
    rvol_val = rvol if rvol is not None else 1.0
    rvol_s = 100.0 if rvol_val >= 3.0 else (0.0 if rvol_val <= 0.5 else (rvol_val - 0.5) / 2.5 * 100.0)
    gm_s = final_score if final_score is not None else 50.0
    
    score = (
        w['future_catalyst'] * fc_s +
        w['historical_reaction'] * ar_s +
        w['rvol'] * rvol_s +
        w['gap_monster'] * gm_s
    )
    return min(100.0, max(0.0, score))


def generate_research_tags(item, event_potential, run_up_risk, setup_score, cf_score, guidance_score, sq_score, ttm_fcf=None, cf_trend=None):
    tags = []
    
    if event_potential >= 75.0:
        tags.append("High Event Potential")
    if run_up_risk >= 70.0:
        tags.append("High Run-Up Risk")
    if setup_score <= 30.0:
        tags.append("Low Expectation Setup")
    
    # 2. FCF Deterioration Risk
    is_fcf_deterioration = (
        cf_score <= 25.0 or
        (cf_trend == "Declining" and (item.get('Latest FCF') or 0) < 0) or
        (ttm_fcf is not None and ttm_fcf < -10_000_000) # Materially negative TTM
    )
    if is_fcf_deterioration:
        tags.append("FCF Deterioration Risk")
        
    # Only tag "Strong Cash Flow Quality" if TTM FCF is also positive (or unavailable)
    if cf_score >= 75.0 and (ttm_fcf is None or ttm_fcf >= 0):
        tags.append("Strong Cash Flow Quality")
    # New tag: improving quarter but structurally negative TTM
    if ttm_fcf is not None and ttm_fcf < 0 and cf_trend == "Improving":
        tags.append("FCF Improving But Structurally Negative")
    if guidance_score >= 70.0:
        tags.append("High Guidance Sensitivity")
    if sq_score >= 70.0:
        tags.append("Short Squeeze Candidate")
        
    float_s = item.get('Float Shares')
    if float_s is not None and float_s < 30_000_000:
        tags.append("Low Float Mover")
        
    # 1. Dilution / Offering Risk
    has_dilution_risk, _ = detect_balance_sheet_risk(item.get('SEC Filings', []))
    if has_dilution_risk:
        tags.append("Dilution / Offering Risk")
        
    return tags


def calculate_future_catalyst_score(days_until, days_since):
    """Fast-scan catalyst proximity (used by Fast Opportunity Score in app.py)."""
    if days_since is not None and days_since <= 30:
        return -50.0
    if days_until is None:
        return -50.0
    if days_until > 30:
        return -50.0
    if days_until < 0:
        return -50.0

    d = days_until
    if d == 0:   return 100.0
    if d == 1:   return 95.0
    if d == 2:   return 90.0
    if d == 3:   return 85.0
    if d <= 5:   return 70.0
    if d <= 10:  return 40.0
    if d <= 20:  return 10.0
    return 0.0


def calculate_stage5_future_catalyst_score(days_until, days_since):
    """Stage 5 future catalyst score (0-100) for Opportunity Score weighting."""
    if days_until is None or days_until < 0 or days_until > 30:
        return 0.0
    if days_since is not None and days_since <= 30:
        return 0.0

    d = days_until
    if d == 0:
        return 100.0
    if d == 1:
        return 97.0
    if d == 2:
        return 94.0
    if d == 3:
        return 90.0
    if d <= 10:
        return 75.0 - (d - 4) * 2.5
    if d <= 20:
        return 40.0 - (d - 11) * 2.5
    return max(0.0, 15.0 - (d - 21) * 1.5)


def classify_universe(mkt_cap):
    if mkt_cap is None:
        return "Core Opportunity"
    m = mkt_cap / 1e6
    if 50.0 <= m < 300.0:
        return "Speculative"
    if 300.0 <= m <= 10_000.0:
        return "Core Opportunity"
    return "Large Cap"


def calculate_screener_scores(metrics_list):
    scored_results = []

    for item in metrics_list:
        if item is None:
            continue

        ticker = item['Ticker']
        mkt_cap = item['Market Cap']
        price = item['Price'] or 0.0
        universe = classify_universe(mkt_cap)

        rvol = item['RVOL'] or 0.0
        rvol_score = 100.0 if rvol >= 3.0 else (0.0 if rvol <= 0.5 else (rvol - 0.5) / 2.5 * 100.0)

        change = item['Change (%)'] or 0.0
        mom_score = 100.0 if change >= 8.0 else (0.0 if change <= 0.0 else change / 8.0 * 100.0)

        ema_20 = item['EMA 20']
        sma_50 = item['SMA 50']
        sma_200 = item['SMA 200']
        ma_score = 0.0
        if ema_20 and price > ema_20:  ma_score += 20.0
        if sma_50 and price > sma_50:  ma_score += 30.0
        if sma_200 and price > sma_200: ma_score += 30.0
        if sma_50 and sma_200 and sma_50 > sma_200: ma_score += 20.0
        if sma_50 is None or sma_200 is None:
            ma_score = 80.0 if (ema_20 and price > ema_20) else 20.0

        future_cat_score = calculate_stage5_future_catalyst_score(
            item['Days Until Earnings'], item['Days Since Earnings']
        )

        if mkt_cap is None:
            mcap_score = 50.0
        else:
            m = mkt_cap / 1e6
            if 300.0 <= m <= 2000.0:   mcap_score = 100.0
            elif m <= 10_000.0:         mcap_score = 60.0
            elif m > 10_000.0:          mcap_score = 10.0
            elif m >= 50.0:             mcap_score = 80.0
            else:                        mcap_score = 0.0

        float_s = item['Float Shares']
        if float_s is None and mkt_cap and price > 0:
            float_s = mkt_cap / price
        if float_s is None:
            float_score = 50.0
        else:
            fm = float_s / 1e6
            if fm <= 10.0:   float_score = 100.0
            elif fm <= 50.0: float_score = 75.0
            elif fm <= 150.0: float_score = 40.0
            else:             float_score = 10.0

        short_p = item['Short Percent']
        if short_p is None:
            ss = item['Shares Short']
            if ss and float_s:
                short_p = ss / float_s
        if short_p is None:
            si_score = 10.0
        else:
            sp = short_p * 100.0
            if sp >= 20.0:   si_score = 100.0
            elif sp >= 10.0: si_score = 75.0
            elif sp >= 5.0:  si_score = 40.0
            else:             si_score = 10.0

        analysts = item['Analysts']
        if analysts is None:
            analyst_score = 80.0
        elif analysts == 0:   analyst_score = 100.0
        elif analysts <= 3:   analyst_score = 85.0
        elif analysts <= 8:   analyst_score = 60.0
        elif analysts <= 15:  analyst_score = 35.0
        else:                  analyst_score = 10.0

        avg_react = item.get('Avg Earnings Reaction (%)') or 0.0
        if avg_react == 0.0:    react_score = 20.0
        elif avg_react >= 10.0: react_score = 100.0
        elif avg_react >= 5.0:  react_score = 75.0
        elif avg_react >= 2.0:  react_score = 40.0
        else:                   react_score = 10.0

        final_fcat = future_cat_score
        if universe == "Large Cap":
            if final_fcat > 0:
                final_fcat *= 0.5
        future_cat_component = max(0.0, final_fcat)

        atr_score = (
            100.0 if (item.get('ATR %') or 0.0) >= 8.0 else
            (80.0 if (item.get('ATR %') or 0.0) >= 5.0 else
             (50.0 if (item.get('ATR %') or 0.0) >= 3.0 else 20.0))
        )
        gap_freq_score = (
            100.0 if (item.get('Gap Frequency (%)') or 0.0) >= 20.0 else
            (80.0 if (item.get('Gap Frequency (%)') or 0.0) >= 10.0 else
             (50.0 if (item.get('Gap Frequency (%)') or 0.0) >= 5.0 else 10.0))
        )

        # --- Opportunity Score (0-100) ---
        # Weights: Future Catalyst (25%), Hist Reaction (25%), SI (15%), Float (10%),
        #          RVOL (10%), Market Cap (8%), ATR (4%), Gap Freq (3%)
        opp_score = (
            future_cat_component * 0.25 +
            react_score * 0.25 +
            si_score * 0.15 +
            float_score * 0.10 +
            rvol_score * 0.10 +
            mcap_score * 0.08 +
            atr_score * 0.04 +
            gap_freq_score * 0.03
        )

        # --- Prediction Score (0-100) ---
        # Weights: Analyst Consensus (20%), Earnings Surprise Trend (20%), RSI (15%), Moving Averages (15%), SEC Filings (15%), News Confidence (15%)
        # 1. Analyst Consensus
        if analysts is not None and analysts > 0:
            analyst_pred = 85.0 if analysts <= 3 else (65.0 if analysts <= 10 else 50.0)
        else:
            analyst_pred = 60.0
        
        # 2. Earnings surprise / price momentum trend fallback
        surprise_pred = 70.0
        if change > 0:
            surprise_pred += 15.0
        if avg_react >= 5.0:
            surprise_pred += 15.0
        surprise_pred = min(100.0, surprise_pred)

        # 3. RSI
        rsi_val = item.get('RSI') or 50.0
        rsi_pred = 100.0 if rsi_val >= 65.0 else (80.0 if rsi_val >= 50.0 else (50.0 if rsi_val >= 40.0 else 30.0))

        # 4. Momentum Moving Averages (15%)
        ma_pred = 0.0
        if ema_20 and price > ema_20:   ma_pred += 25.0
        if sma_50 and price > sma_50:   ma_pred += 35.0
        if sma_200 and price > sma_200: ma_pred += 40.0
        if not ema_20 and not sma_50:   ma_pred = 50.0

        # 5. SEC Filings Signals (15%)
        sec_filings = item.get('SEC Filings', [])
        sec_pred = 50.0
        for f in sec_filings:
            f_type = str(f.get('form', ''))
            if '4' in f_type:    sec_pred += 20.0
            elif '8-K' in f_type: sec_pred += 10.0
            elif '10' in f_type:  sec_pred += 15.0
        sec_pred = min(100.0, sec_pred)

        # 6. Data Confidence Sentiment (15%)
        conf_pred = 85.0 if item.get('Data Confidence') == 'High' else (75.0 if item.get('Data Confidence') == 'Medium' else 60.0)

        pred_score = (
            analyst_pred * 0.20 +
            surprise_pred * 0.20 +
            rsi_pred * 0.15 +
            ma_pred * 0.15 +
            sec_pred * 0.15 +
            conf_pred * 0.15
        )

        # Apply scaling penalites for large caps to focus on small/mid-caps
        if universe == "Large Cap":
            opp_score *= 0.70
            pred_score *= 0.85

        final_score = opp_score * 0.60 + pred_score * 0.40

        # --- New Scoring Calculations ---
        # 1. Run-Up Risk
        run_up_risk_score, expectation_setup_score, ru_inc, ru_missing = calculate_run_up_risk_score(
            item.get('30D Return'),
            item.get('60D Return'),
            item.get('90D Return'),
            item.get('RSI'),
            item.get('Distance From 52W High'),
            item.get('Price'),
            sma_50,
            sma_200
        )

        # 2. Cash Flow Quality
        cf_score, cf_trend, cf_latest, cf_prior, cf_status, cf_inc, cf_pen, cf_warn, cf_missing = calculate_cash_flow_quality_score(
            item.get('Quarterly FCF'),
            item.get('TTM Levered FCF')
        )

        # 3. Guidance Sensitivity
        guid_score, guid_flag, guid_inc, guid_missing = calculate_guidance_sensitivity_score(
            item.get('Sector'),
            item.get('Industry'),
            item.get('Analysts'),
            item.get('Avg Earnings Reaction (%)'),
            item.get('30D Return'),
            item.get('Forward PE'),
            item.get('Price to Sales'),
            item.get('Trailing PE'),
            item.get('Revenue Growth')
        )

        # 4. Days To Cover
        shares_short = item.get('Shares Short')
        avg_vol = item.get('Avg Vol (20d)')
        days_to_cover = None
        if shares_short and avg_vol and avg_vol > 0:
            days_to_cover = float(shares_short / avg_vol)
        if days_to_cover is None:
            days_to_cover = item.get('Short Ratio')
        dtc_score, dtc_breakdown = calculate_days_to_cover_score(days_to_cover)

        # 5. Short Squeeze Quality
        sq_score, sq_inc, sq_missing = calculate_short_squeeze_quality_score(
            item.get('Short Percent'),
            days_to_cover,
            item.get('Float Shares'),
            rvol
        )

        # 6. Event Potential and Research Priority
        event_potential_score = calculate_event_potential_score(
            future_cat_component,
            item.get('Avg Earnings Reaction (%)'),
            rvol,
            final_score
        )

        w_rp = RESEARCH_PRIORITY_WEIGHTS
        research_priority_score = (
            w_rp['final_score'] * final_score +
            w_rp['event_potential'] * event_potential_score +
            w_rp['expectation_setup'] * expectation_setup_score +
            w_rp['cash_flow_quality'] * cf_score +
            w_rp['guidance_sensitivity'] * guid_score +
            w_rp['short_squeeze'] * sq_score
        )

        # 7. Research Tags
        tags = generate_research_tags(
            item,
            event_potential_score,
            run_up_risk_score,
            expectation_setup_score,
            cf_score,
            guid_score,
            sq_score,
            ttm_fcf=item.get('TTM Levered FCF'),
            cf_trend=cf_trend
        )

        # 8. Detailed Breakdown Collection
        increases_list = []
        penalties_list = []
        warnings_list = []
        missing_list = []

        # Run-up and Expectation Setup
        if run_up_risk_score > 0:
            penalties_list.append(f"Expectation Inflation Risk (Run-Up Risk: {run_up_risk_score:.1f}/100):")
            for x in ru_inc:
                penalties_list.append(f"  - {x}")
        else:
            increases_list.append("Low Expectation Setup: Priced conservatively going into earnings.")

        # Cash flow
        if cf_inc:
            for x in cf_inc: increases_list.append(x)
        if cf_pen:
            for x in cf_pen: penalties_list.append(x)
        if cf_warn:
            for x in cf_warn: warnings_list.append(x)
        if cf_missing:
            for x in cf_missing: missing_list.append(x)

        # Guidance sensitivity
        increases_list.append(f"Guidance Sensitivity Score: {guid_score:.1f}/100 (Flag: {guid_flag})")
        for x in guid_inc:
            increases_list.append(f"  - {x}")
        for x in guid_missing:
            missing_list.append(x)

        # Short squeeze
        increases_list.append(f"Short Squeeze Quality Score: {sq_score:.1f}/100")
        for x in sq_inc:
            increases_list.append(f"  - {x}")
        for x in sq_missing:
            missing_list.append(x)

        # Days to cover
        for x in dtc_breakdown:
            if "cover" in x.lower() and (">=" in x or "high" in x.lower() or "moderate" in x.lower()):
                increases_list.append(x)
            else:
                penalties_list.append(x)

        # Dilution / Offering Risk
        has_dilution_risk, bs_desc = detect_balance_sheet_risk(sec_filings)
        if has_dilution_risk:
            warnings_list.append(bs_desc)
            penalties_list.append(bs_desc)

        # FCF Deterioration Risk explainers
        is_fcf_deterioration = (
            cf_score <= 25.0 or
            (cf_trend == "Declining" and (cf_latest or 0) < 0) or
            (item.get('TTM Levered FCF') is not None and item.get('TTM Levered FCF') < -10_000_000)
        )
        if is_fcf_deterioration:
            penalties_list.append("FCF Deterioration Risk triggered by cash-flow score / negative FCF trend, not actual balance-sheet leverage.")

        # Unique lists
        breakdown_dict = {
            'increases': list(dict.fromkeys(increases_list)),
            'penalties': list(dict.fromkeys(penalties_list)),
            'warnings': list(dict.fromkeys(warnings_list)),
            'missing_inputs': list(dict.fromkeys(missing_list + ru_missing))
        }

        item_out = item.copy()
        item_out['Universe'] = universe
        item_out['Opportunity Score'] = round(opp_score, 1)
        item_out['Prediction Score'] = round(pred_score, 1)
        item_out['Final Score'] = round(final_score, 1)
        item_out['Composite Score'] = round(final_score, 1)
        
        # New Scoring fields
        item_out['30D Return'] = item.get('30D Return')
        item_out['60D Return'] = item.get('60D Return')
        item_out['90D Return'] = item.get('90D Return')
        item_out['Run-Up Risk Score'] = round(run_up_risk_score, 1)
        item_out['Expectation Setup Score'] = round(expectation_setup_score, 1)
        item_out['Latest FCF'] = cf_latest
        item_out['Prior FCF'] = cf_prior
        item_out['FCF Trend'] = cf_trend
        item_out['Cash Flow Quality Score'] = round(cf_score, 1)
        item_out['Cash Flow Data Status'] = cf_status
        item_out['Sector / Industry'] = f"{item.get('Sector') or 'N/A'} / {item.get('Industry') or 'N/A'}"
        item_out['Guidance Sensitivity Score'] = round(guid_score, 1)
        item_out['Guidance Risk Flag'] = guid_flag
        item_out['Days To Cover'] = round(days_to_cover, 2) if days_to_cover is not None else None
        item_out['Days-To-Cover Score'] = round(dtc_score, 1)
        item_out['Short Squeeze Quality Score'] = round(sq_score, 1)
        item_out['Event Potential Score'] = round(event_potential_score, 1)
        item_out['Research Priority Score'] = round(research_priority_score, 1)
        
        # Calculate Directional Overlay
        dir_results = calculate_directional_overlay(
            expectation_setup=expectation_setup_score,
            run_up_risk=run_up_risk_score,
            cf_score=cf_score,
            guidance_sensitivity=guid_score,
            research_priority=research_priority_score,
            ret_30d=item.get('30D Return'),
            ret_60d=item.get('60D Return')
        )
        dps = dir_results['Directional_Probability_Score']
        is_elite = (dps >= 70.0) and (expectation_setup_score >= 90.0) and (research_priority_score >= 54.5)
        
        item_out['Directional Probability Score'] = dps
        item_out['Directional Edge Score V1'] = dir_results['Directional_Edge_Score_V1']
        item_out['Directional Bias'] = dir_results['Directional_Bias']
        item_out['Directional Archetype'] = dir_results['Directional_Archetype']

        # Elite Tier & Hybrid sizing
        item_out['Is_Elite'] = is_elite
        item_out['Is Elite'] = "Yes" if is_elite else "No"
        item_out['Position Size Pct'] = 0.10 if is_elite else 0.05
        item_out['Recommended Position Size'] = "10.0%" if is_elite else "5.0%"

        # Exit Strategy Phase 1 — validated path-safe exit recommendations (2026-06-27 audit)
        # Elite setups: Day 5 Close (post-earnings drift persists through Day 5)
        # Standard eligible setups: Day 3 Close (best risk-adjusted path-safe exit)
        # DPS < 60: no trade recommendation (filtered upstream, but guard here for diagnostics mode)
        if is_elite:
            item_out['Exit Recommendation'] = "Hold to Day 5 Close"
            item_out['Exit Hold Days'] = 5
            item_out['Exit Rationale'] = "Elite setup; historical audit shows stronger post-earnings drift through Day 5."
        elif dps >= 60.0:
            item_out['Exit Recommendation'] = "Hold to Day 3 Close"
            item_out['Exit Hold Days'] = 3
            item_out['Exit Rationale'] = "Standard setup; Day 3 close had best risk-adjusted path-safe exit."
        else:
            item_out['Exit Recommendation'] = "No Trade — DPS below eligibility threshold"
            item_out['Exit Hold Days'] = None
            item_out['Exit Rationale'] = "DPS < 60; setup does not meet minimum directional conviction for a trade recommendation."

        if is_elite and "Elite Tier Setup" not in tags:
            tags.append("Elite Tier Setup")

        item_out['Research Tags'] = ", ".join(tags)
        item_out['Research Score Breakdown'] = breakdown_dict

        # Generate custom analyst-grade explanation
        why_string = generate_catalyst_explanation(item_out)
        item_out['Why This Stock Ranked'] = why_string

        # Backwards compatible indicators
        item_out['RVOL Score'] = round(rvol_score, 1)
        item_out['Momentum Score'] = round(mom_score, 1)
        item_out['MA Score'] = round(ma_score, 1)
        item_out['Future Catalyst Score'] = round(future_cat_component, 1)
        item_out['Market Cap Score'] = round(mcap_score, 1)
        item_out['Float Score'] = round(float_score, 1)
        item_out['Short Interest Score'] = round(si_score, 1)
        item_out['Analyst Score'] = round(analyst_score, 1)
        item_out['Historical Reaction Score'] = round(react_score, 1)
        item_out['Gap Monster Score'] = round(final_score, 1) # redirect to Final
        item_out['Catalyst Score'] = round(final_score, 1)
        item_out['Quality Score'] = round(final_score, 1)

        scored_results.append(item_out)

    if not scored_results:
        return pd.DataFrame()
    return pd.DataFrame(scored_results)


def map_stage4_failure_reason(msg):
    """Map Stage 4 metric-calculation failure messages to exclusion categories."""
    if not msg:
        return "Filtered By Universe Rules"
    msg_lower = msg.lower()
    if "insufficient" in msg_lower or "history" in msg_lower or "close column" in msg_lower or "missing close" in msg_lower:
        return "Insufficient History"
    if "missing market cap" in msg_lower or "zero rvol" in msg_lower or "zero or negative price" in msg_lower:
        return "Missing Fundamental Data"
    if "missing" in msg_lower:
        return "Missing Fundamental Data"
    return "Filtered By Universe Rules"


def determine_scored_exclusion_reason(row, future_catalysts_only=True, diagnostics_mode=False):
    """Determine why a scored ticker was excluded from the Discovery Leaderboard."""
    days = row.get('Days Until Earnings')
    conf = row.get('Data Confidence', 'Low')
    dps = row.get('Directional Probability Score')
    dps = 0.0 if dps is None or (isinstance(dps, float) and pd.isna(dps)) else float(dps)

    days_invalid = (
        days is None
        or (isinstance(days, float) and pd.isna(days))
        or days < 0
        or days > 30
    )
    if days_invalid:
        return "No Upcoming Earnings"

    earnings_within_14 = 0 <= days <= 14
    if conf == 'Low' and earnings_within_14 and dps >= 60.0:
        return "Low Confidence Only"
    if conf == 'Low':
        return "Low Confidence"
    if dps < 60.0:
        return "Low Directional Score (DPS < 60)"
    return "Filtered By Universe Rules"


def build_leaderboard_exclusions(
    deep_scan_tickers,
    stage4_failures,
    df_results,
    deep_scan_snapshot=None,
    future_catalysts_only=True,
    diagnostics_mode=False,
    top_n=30,
    max_display=50,
):
    """Build exclusion diagnostics for tickers deep-scanned in Stage 4 but absent from the top leaderboard."""
    if not deep_scan_tickers:
        return pd.DataFrame()

    deep_scan_snapshot = deep_scan_snapshot or {}
    scored_df = df_results if df_results is not None and not df_results.empty else pd.DataFrame()
    scored_map = {row['Ticker']: row.to_dict() for _, row in scored_df.iterrows()}

    display_df = scored_df.copy()
    if not diagnostics_mode and not display_df.empty:
        # Apply DPS >= 60 eligibility filter
        display_df = display_df[display_df['Directional Probability Score'] >= 60.0].copy()
        if future_catalysts_only:
            display_df = display_df[
                (pd.notnull(display_df['Days Until Earnings'])) &
                (display_df['Days Until Earnings'] >= 0) &
                (display_df['Days Until Earnings'] <= 30)
            ].copy()

    leaderboard_tickers = set()
    if not display_df.empty:
        leaderboard_tickers = set(
            display_df.sort_values('Final Score', ascending=False).head(top_n)['Ticker'].tolist()
        )

    exclusions = []
    for ticker in deep_scan_tickers:
        if ticker in leaderboard_tickers:
            continue

        snapshot = deep_scan_snapshot.get(ticker, {})

        if ticker in stage4_failures:
            exclusions.append({
                'ticker': ticker,
                'opportunity_score': None,
                'prediction_score': None,
                'final_score': None,
                'future_catalyst_score': None,
                'days_until_earnings': snapshot.get('days_until_earnings'),
                'data_confidence': snapshot.get('data_confidence'),
                'failed_reason': map_stage4_failure_reason(stage4_failures[ticker]),
            })
            continue

        if ticker not in scored_map:
            exclusions.append({
                'ticker': ticker,
                'opportunity_score': None,
                'prediction_score': None,
                'final_score': None,
                'future_catalyst_score': None,
                'days_until_earnings': snapshot.get('days_until_earnings'),
                'data_confidence': snapshot.get('data_confidence'),
                'failed_reason': "Missing Fundamental Data",
            })
            continue

        row = scored_map[ticker]
        exclusions.append({
            'ticker': ticker,
            'opportunity_score': row.get('Opportunity Score'),
            'prediction_score': row.get('Prediction Score'),
            'final_score': row.get('Final Score'),
            'future_catalyst_score': row.get('Future Catalyst Score'),
            'days_until_earnings': row.get('Days Until Earnings'),
            'data_confidence': row.get('Data Confidence'),
            'failed_reason': determine_scored_exclusion_reason(
                row, future_catalysts_only=future_catalysts_only, diagnostics_mode=diagnostics_mode
            ),
        })

    if not exclusions:
        return pd.DataFrame()

    df = pd.DataFrame(exclusions)
    df = df.sort_values(by='final_score', ascending=False, na_position='last').head(max_display)
    return df.reset_index(drop=True)


def generate_catalyst_explanation(item):
    """
    Generate a highly custom, quantitative, analyst-grade explainability string
    for why a stock ranks.
    """
    d_until = item.get('Days Until Earnings')
    avg_react = item.get('Avg Earnings Reaction (%)') or 0.0
    short_pct = item.get('Short Percent')
    if short_pct is None:
        ss = item.get('Shares Short')
        fl = item.get('Float Shares')
        if ss and fl:
            short_pct = ss / fl
    short_pct = short_pct or 0.0
    
    float_s = item.get('Float Shares')
    rvol = item.get('RVOL') or 1.0
    rsi = item.get('RSI') or 50.0
    sec_filings = item.get('SEC Filings', [])
    
    parts = []
    
    # 1. Earnings timing
    if d_until is not None:
        if d_until == 0:
            parts.append("Upcoming earnings today.")
        elif d_until == 1:
            parts.append("Upcoming earnings tomorrow.")
        else:
            parts.append(f"Upcoming earnings in {d_until} days.")
            
    # 2. Historical average move
    if avg_react > 0:
        parts.append(f"Historical average earnings move {avg_react:.1f}%.")
        
    # 3. Short interest
    if short_pct > 0:
        parts.append(f"Short interest {short_pct * 100:.1f}%.")
        
    # 4. Float Shares
    if float_s and float_s > 0:
        parts.append(f"Float {float_s / 1e6:.1f}M shares.")
    else:
        parts.append("Low float.")
        
    # 5. Momentum / RSI
    if rsi >= 65:
        parts.append("Strong technical momentum.")
    elif rsi < 40:
        parts.append("Oversold/reversal potential.")
        
    # 6. SEC Filing Activity
    if sec_filings:
        insider = any('4' in str(f.get('form', '')) for f in sec_filings)
        if insider:
            parts.append("Recent insider Form 4 filing activity.")
        else:
            recent_forms = ', '.join(f.get('form', '') for f in sec_filings[:2])
            parts.append(f"Positive SEC filing activity ({recent_forms}).")
            
    if not parts:
        return "Stable catalyst structure with neutral technical alignment."
        
    return " ".join(parts)


# =============================================================================
# PERSISTENCE
# =============================================================================

def save_screening_run(df, base_path=DEFAULT_HISTORY_PATH):
    if df is None or df.empty:
        return None, "No data to save."
    os.makedirs(base_path, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(base_path, f"screener_results_{timestamp}.csv")
    try:
        save_df = df.copy()
        for col in ['Next Earnings Date', 'Last Earnings Date']:
            if col in save_df.columns:
                save_df[col] = save_df[col].apply(
                    lambda d: d.strftime("%Y-%m-%d")
                    if isinstance(d, (datetime.date, datetime.datetime))
                    else (str(d) if pd.notnull(d) else "")
                )
        # Drop list columns before saving
        if 'SEC Filings' in save_df.columns:
            save_df = save_df.drop(columns=['SEC Filings'])
        save_df.to_csv(file_path, index=False)
        return file_path, f"Saved to {os.path.basename(file_path)}"
    except Exception as e:
        return None, f"Save failed: {e}"


def get_historical_files(base_path=DEFAULT_HISTORY_PATH):
    if not os.path.exists(base_path):
        return []
    try:
        files = [f for f in os.listdir(base_path)
                 if f.endswith('.csv') and f.startswith('screener_results_')]
        return sorted(files, reverse=True)
    except Exception:
        return []

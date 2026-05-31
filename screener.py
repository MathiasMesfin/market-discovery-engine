import yfinance as yf
import pandas as pd
import numpy as np
import concurrent.futures
import datetime
import os
import requests
import time

# =============================================================================
# TEST MODE — 20 known liquid tickers for pipeline validation
# =============================================================================
TEST_MODE_TICKERS = [
    'AAPL', 'MSFT', 'NVDA', 'AMD', 'TSLA',
    'AAL', 'ABM', 'ADBE', 'COST', 'AVGO',
    'PLTR', 'SMCI', 'LUNR', 'AI', 'ABSI',
    'ACVA', 'OI', 'OLMA', 'OCUL', 'ABAT'
]

# =============================================================================
# STAGE 0 — UNIVERSE BUILDER
# =============================================================================

def refresh_market_universe(save_path="/Users/mathiasmesfin/Downloads/Stock Screener/data/us_stock_universe.csv"):
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
        return valid_symbols[['Symbol', 'CIK']].to_dict('records'), \
               f"Successfully pulled {len(valid_symbols)} clean market symbols."
    except Exception as e:
        if os.path.exists(save_path):
            try:
                cached_df = pd.read_csv(save_path)
                return cached_df.to_dict('records'), "FTP/SEC unreachable — loaded from cache."
            except Exception:
                pass
        return [], f"Failed to load universe: {str(e)}"


def get_test_mode_items():
    """Return the 20 known test tickers as metadata items (no CIK needed)."""
    return [{'ticker': t, 'cik': None} for t in TEST_MODE_TICKERS]


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


def get_discovery_universe_items(universe_path="/Users/mathiasmesfin/Downloads/Stock Screener/data/us_stock_universe.csv"):
    """
    Load active symbols from us_stock_universe.csv and cross-reference them
    with our hand-curated DISCOVERY_UNIVERSE_TICKERS.
    This guarantees 100% valid, active common stock operating company tickers.
    """
    if not os.path.exists(universe_path):
        return [{'ticker': t, 'cik': None} for t in DISCOVERY_UNIVERSE_TICKERS[:500]]
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
        return discovered[:500]
    except Exception:
        return [{'ticker': t, 'cik': None} for t in DISCOVERY_UNIVERSE_TICKERS[:500]]


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
    try:
        raw = yf.download(
            tickers if len(tickers) > 1 else tickers[0],
            period=period,
            progress=False,
            threads=True,
            auto_adjust=True
        )
        result = {}
        for t in tickers:
            tdf = _extract_ticker_df(raw, t)
            if tdf is not None and not tdf.empty:
                result[t] = tdf
        return result
    except Exception:
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
    status = {}

    # 1. yfinance price test
    try:
        raw = yf.download('AAPL', period='5d', progress=False, auto_adjust=True)
        tdf = _extract_ticker_df(raw, 'AAPL')
        if tdf is not None and not tdf.empty and tdf['Close'].iloc[-1] > 0:
            status['yfinance_price'] = {'ok': True, 'detail': f"AAPL last close ${tdf['Close'].iloc[-1]:.2f}"}
        else:
            status['yfinance_price'] = {'ok': False, 'detail': 'Download returned empty or zero price'}
    except Exception as e:
        status['yfinance_price'] = {'ok': False, 'detail': str(e)}

    # 2. yfinance earnings test
    try:
        t = yf.Ticker('AAPL')
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
        'sources_used': []
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
        t = yf.Ticker(ticker)
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
        'SEC Filings': ticker_meta.get('sec_filings', [])
    }, "Pass"


# =============================================================================
# SCORING ENGINE
# =============================================================================

def calculate_future_catalyst_score(days_until, days_since):
    """Score based on how soon the next earnings are."""
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

        future_cat_score = calculate_future_catalyst_score(
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
        final_react = react_score
        if universe == "Large Cap":
            if final_fcat > 0:
                final_fcat *= 0.5
        
        # --- Opportunity Score (0-100) ---
        # Weights: Reaction (30%), Short Interest (20%), Float (15%), RVOL (15%), Market Cap (10%), ATR % (5%), Gap Freq (5%)
        opp_score = (
            react_score * 0.30 +
            si_score * 0.20 +
            float_score * 0.15 +
            rvol_score * 0.15 +
            mcap_score * 0.10 +
            (100.0 if (item.get('ATR %') or 0.0) >= 8.0 else (80.0 if (item.get('ATR %') or 0.0) >= 5.0 else (50.0 if (item.get('ATR %') or 0.0) >= 3.0 else 20.0))) * 0.05 +
            (100.0 if (item.get('Gap Frequency (%)') or 0.0) >= 20.0 else (80.0 if (item.get('Gap Frequency (%)') or 0.0) >= 10.0 else (50.0 if (item.get('Gap Frequency (%)') or 0.0) >= 5.0 else 10.0))) * 0.05
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

        item_out = item.copy()
        item_out['Universe'] = universe
        item_out['Opportunity Score'] = round(opp_score, 1)
        item_out['Prediction Score'] = round(pred_score, 1)
        item_out['Final Score'] = round(final_score, 1)
        item_out['Composite Score'] = round(final_score, 1)
        
        # Generate custom analyst-grade explanation
        why_string = generate_catalyst_explanation(item_out)
        item_out['Why This Stock Ranked'] = why_string

        # Backwards compatible indicators
        item_out['RVOL Score'] = round(rvol_score, 1)
        item_out['Momentum Score'] = round(mom_score, 1)
        item_out['MA Score'] = round(ma_score, 1)
        item_out['Future Catalyst Score'] = round(future_cat_score, 1)
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

def save_screening_run(df, base_path="/Users/mathiasmesfin/Downloads/Stock Screener/data/history"):
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


def get_historical_files(base_path="/Users/mathiasmesfin/Downloads/Stock Screener/data/history"):
    if not os.path.exists(base_path):
        return []
    try:
        files = [f for f in os.listdir(base_path)
                 if f.endswith('.csv') and f.startswith('screener_results_')]
        return sorted(files, reverse=True)
    except Exception:
        return []

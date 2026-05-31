import streamlit as st
import pandas as pd
import numpy as np
import datetime
import os
import math
import requests
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import concurrent.futures
import time

# Setup custom yfinance cache locations to avoid OperationalError on database writes
cache_dir = os.path.join(os.getcwd(), "cache")
try:
    os.makedirs(cache_dir, exist_ok=True)
    os.environ['YF_CACHE_DIR'] = cache_dir  # Tell yfinance to write to this local directory if supported
    if hasattr(yf, 'set_tz_cache_location'):
        yf.set_tz_cache_location(os.path.join(cache_dir, "py-yfinance"))
except Exception:
    pass

# Import backend modules
from screener import (
    refresh_market_universe,
    fetch_metadata_parallel,
    fetch_historical_data,
    calculate_single_ticker_metrics,
    calculate_screener_scores,
    save_screening_run,
    get_historical_files,
    run_health_check,
    get_test_mode_items,
    TEST_MODE_TICKERS,
    get_discovery_universe_items,
    DISCOVERY_UNIVERSE_TICKERS
)

# ----------------------------------------------------
# PAGE CONFIGURATION & STYLING
# ----------------------------------------------------
st.set_page_config(
    page_title="Market Discovery Engine | Antigravity",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom styling for a premium event-driven tool
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@300;400;500;600;700;800&display=swap');

    /* Global fonts and backgrounds */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        font-family: 'Plus Jakarta Sans', 'Outfit', sans-serif;
        background-color: #080c14 !important;
        color: #f3f4f6 !important;
    }
    
    /* Glowing header banner */
    .title-banner {
        background: linear-gradient(135deg, #1e1b4b 0%, #030712 100%);
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    }
    .title-banner h1 {
        color: #ffffff !important;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        margin: 0 0 8px 0 !important;
        letter-spacing: -0.02em;
    }
    .title-banner p {
        color: #c084fc !important;
        font-size: 1rem !important;
        margin: 0 !important;
    }

    /* Sidebar Blur */
    [data-testid="stSidebar"] {
        background-color: rgba(10, 15, 28, 0.8) !important;
        backdrop-filter: blur(12px);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #a78bfa !important;
        font-weight: 700;
    }

    /* KPI Cards */
    .kpi-container {
        display: flex;
        gap: 16px;
        margin-bottom: 24px;
        flex-wrap: wrap;
    }
    .kpi-card {
        flex: 1;
        min-width: 200px;
        background: linear-gradient(135deg, rgba(20, 24, 41, 0.9) 0%, rgba(8, 12, 24, 0.9) 100%);
        border: 1px solid rgba(139, 92, 246, 0.1);
        border-left: 4px solid #8b5cf6;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(4px);
        transition: transform 0.2s, border-color 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: rgba(139, 92, 246, 0.35);
    }
    .kpi-title {
        font-size: 0.8rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 1.7rem;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 4px;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(17, 24, 39, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 10px 20px !important;
        color: #9ca3af !important;
        font-weight: 600 !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(139, 92, 246, 0.15) !important;
        color: #c084fc !important;
        border-bottom: 2px solid #8b5cf6 !important;
    }

    /* Buttons */
    div.stButton > button {
        background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3) !important;
    }
    div.stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(124, 58, 237, 0.45) !important;
        background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%) !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# PRESETS, CACHING & UTILITIES
# ----------------------------------------------------
PRESETS = {
    "AI & Tech Catalyst Presets": "PLTR, NVDA, AMD, SMCI, AVGO, PSTG, AI, ARM, LUNR",
    "Speculative Squeeze Candidates": "GME, AMC, DJT, SPWR, FFIE, MARA, RIOT, HUT",
    "S&P 500 Large Caps": "AAPL, MSFT, GOOGL, AMZN, META, TSLA, NFLX, JPM, LLY",
    "Custom List (Manual / Upload)": ""
}

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_cached_price_volume_30m(tickers_tuple):
    """Cache price/volume history for 30 minutes."""
    return fetch_historical_data(list(tickers_tuple))

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_cached_fundamentals_24h(ticker, finnhub_key=None):
    """Cache basic company profile data for 24 hours."""
    res = {
        'market_cap': None,
        'long_name': ticker,
        'float_shares': None,
        'shares_short': None,
        'short_percent': None,
        'analysts': None,
        'business_summary': "",
        'is_operating': True
    }
    # 1. Finnhub Profile
    if finnhub_key:
        try:
            url = f'https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={finnhub_key}'
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                p = r.json()
                if p:
                    res['long_name'] = p.get('name', ticker)
                    mc = p.get('marketCapitalization')
                    if mc:
                        res['market_cap'] = mc * 1000000
                    so = p.get('shareOutstanding')
                    if so:
                        res['float_shares'] = so * 1000000
        except Exception:
            pass
            
    # 2. yfinance Fallback
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        if not res['market_cap']:
            res['market_cap'] = info.get('marketCap')
        if not res['float_shares']:
            res['float_shares'] = info.get('floatShares')
        res['shares_short'] = info.get('sharesShort')
        res['short_percent'] = info.get('shortPercentOfFloat')
        res['analysts'] = info.get('numberOfAnalystOpinions')
        res['business_summary'] = info.get('longBusinessSummary') or info.get('shortBusinessSummary') or ""
        if res['long_name'] == ticker:
            res['long_name'] = info.get('longName', ticker)
            
        quote_type = info.get('quoteType', '').upper()
        if quote_type and quote_type not in ['EQUITY']:
            res['is_operating'] = False
    except Exception:
        pass
        
    return res

@st.cache_data(ttl=43200, show_spinner=False)
def fetch_cached_earnings_12h(ticker, finnhub_key=None):
    """Cache catalyst earnings date information for 12 hours."""
    res = {
        'next_earnings_date': None,
        'last_earnings_date': None,
        'hist_earnings_dates': [],
        'calendar_status': "Not Fetched",
        'earnings_dates_status': "Not Fetched"
    }
    today = datetime.date.today()
    
    # 1. Finnhub Earnings Calendar
    if finnhub_key:
        try:
            _from = today.strftime('%Y-%m-%d')
            _to = (today + datetime.timedelta(days=90)).strftime('%Y-%m-%d')
            earn_res = requests.get(
                f'https://finnhub.io/api/v1/calendar/earnings?from={_from}&to={_to}&symbol={ticker}&token={finnhub_key}',
                timeout=3
            )
            if earn_res.status_code == 200:
                earn = earn_res.json().get('earningsCalendar', [])
                if earn:
                    ed_str = earn[0].get('date')
                    if ed_str:
                        res['next_earnings_date'] = datetime.datetime.strptime(ed_str, '%Y-%m-%d').date()
                        res['calendar_status'] = "Found in Finnhub"
        except Exception:
            pass
            
    # 2. yfinance Fallback
    try:
        t = yf.Ticker(ticker)
        if not res['next_earnings_date']:
            try:
                cal = t.calendar
                if isinstance(cal, dict) and 'Earnings Date' in cal:
                    dates = cal['Earnings Date']
                    if isinstance(dates, list) and dates:
                        d = dates[0]
                        res['next_earnings_date'] = d.date() if hasattr(d, 'date') else d
                        res['calendar_status'] = "Found in YF Calendar"
            except Exception as e:
                res['calendar_status'] = f"YF Calendar Error: {e}"
                
        try:
            ed = t.earnings_dates
            if ed is not None and not ed.empty:
                hist_dates = []
                for d in ed.index:
                    try:
                        hist_dates.append(d.date() if hasattr(d, 'date') else d)
                    except Exception:
                        pass
                res['hist_earnings_dates'] = hist_dates
                res['earnings_dates_status'] = f"Found {len(hist_dates)} dates (YF)"
                
                past_dates = sorted([d for d in hist_dates if d < today], reverse=True)
                if past_dates:
                    res['last_earnings_date'] = past_dates[0]
                    
                future_dates = sorted([d for d in hist_dates if d >= today])
                if future_dates and not res['next_earnings_date']:
                    res['next_earnings_date'] = future_dates[0]
                    res['calendar_status'] = "Found in YF Earnings History"
            else:
                res['earnings_dates_status'] = "No Historical Dates (YF)"
        except Exception as e:
            res['earnings_dates_status'] = f"YF Earnings Error: {e}"
    except Exception:
        pass
        
    return res

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_cached_sec_24h(ticker, cik=None):
    """Cache recent SEC filings lookup for 24 hours."""
    res = {
        'sec_filings': [],
        'sec_status': "Not Fetched"
    }
    if not cik:
        return res
    try:
        headers = {'User-Agent': 'StockScreenerApp admin@example.com'}
        sec_res = requests.get(
            f'https://data.sec.gov/submissions/CIK{str(cik).zfill(10)}.json',
            headers=headers, timeout=5
        )
        if sec_res.status_code == 200:
            sec_data = sec_res.json()
            recent = sec_data.get('filings', {}).get('recent', {})
            forms = recent.get('form', [])
            dates = recent.get('filingDate', [])
            filings = []
            for idx, form in enumerate(forms):
                if form in ['8-K', '10-Q', '10-K', 'S-1', '6-K']:
                    filing_item = {
                        'form': form,
                        'filingDate': dates[idx],
                        'filedAt': dates[idx],
                        'description': recent.get('primaryDocDescription', [f"Recent {form} filing"])[idx] if 'primaryDocDescription' in recent and idx < len(recent['primaryDocDescription']) else f"Recent {form} filing",
                        'primaryDocDescription': recent.get('primaryDocDescription', [f"Recent {form} filing"])[idx] if 'primaryDocDescription' in recent and idx < len(recent['primaryDocDescription']) else f"Recent {form} filing",
                        'acceptanceDateTime': recent.get('acceptanceDateTime', [dates[idx]])[idx] if 'acceptanceDateTime' in recent and idx < len(recent['acceptanceDateTime']) else dates[idx],
                        'accessionNumber': recent.get('accessionNumber', [""])[idx] if 'accessionNumber' in recent and idx < len(recent['accessionNumber']) else ""
                    }
                    filings.append(filing_item)
                    if len(filings) >= 5:
                        break
            res['sec_filings'] = filings
            res['sec_status'] = "Success"
        else:
            res['sec_status'] = f"HTTP {sec_res.status_code}"
    except Exception as e:
        res['sec_status'] = str(e)
    return res

# Helper for priority sorting of catalyst candidates
def get_priority_score(s):
    """Assigns priority for deep-scan based on catalyst imminence, RVOL, and SI."""
    d = s.get('days_until_earnings')
    prox_score = 0
    if d is not None and 0 <= d <= 30:
        prox_score = (30 - d) * 3  # up to 90 points
        
    rvol_val = s.get('rvol') or 0.0
    rvol_score = min(30, rvol_val * 10)  # up to 30 points
    
    si_val = s.get('short_percent') or 0.0
    si_score = min(30, si_val * 100 * 1.5)  # up to 30 points
    
    return prox_score + rvol_score + si_score

def parse_tickers_input(input_str):
    if not input_str:
        return []
    cleaned = input_str.replace(",", " ").replace(";", " ").replace("\n", " ")
    tickers = [t.strip().upper() for t in cleaned.split(" ") if t.strip()]
    return [{'ticker': t, 'cik': None} for t in dict.fromkeys(tickers)]

def extract_tickers_from_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        possible_cols = [c.lower() for c in df.columns]
        target_col = None
        for col_name in ['symbol', 'ticker', 'symbol/ticker', 'code', 'stock', 'name']:
            if col_name in possible_cols:
                target_col = df.columns[possible_cols.index(col_name)]
                break
        if target_col is None:
            target_col = df.columns[0]
        tickers = df[target_col].dropna().astype(str).tolist()
        return [{'ticker': t.strip().upper(), 'cik': None} for t in dict.fromkeys(tickers)]
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return []

@st.cache_data(ttl=86400, show_spinner=False)
def get_market_universe_tickers():
    path = "/Users/mathiasmesfin/Downloads/Stock Screener/data/us_stock_universe.csv"
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            res = []
            for _, row in df.iterrows():
                res.append({
                    'ticker': str(row['Symbol']).upper(),
                    'cik': str(row['CIK']).zfill(10) if pd.notnull(row.get('CIK')) else None
                })
            return res
        except:
            pass
    return []

# ----------------------------------------------------
# CORE SCREENER INTERFACE
# ----------------------------------------------------

# Header Banner
st.markdown("""
<div class="title-banner">
    <h1>⚡ Market Discovery Engine</h1>
    <p>Target stocks primed for outsized post-earnings moves. Discover unknown future catalysts across the entire market universe.</p>
</div>
""", unsafe_allow_html=True)

tab_screener, tab_history = st.tabs(["🔍 Catalyst Scanner", "💾 Saved Screenings"])

if "screener_results" not in st.session_state:
    st.session_state.screener_results = None
    st.session_state.raw_history = {}
    st.session_state.metadata = {}
    st.session_state.scan_stats = {}
if "fast_scan_candidates" not in st.session_state:
    st.session_state.fast_scan_candidates = []
if "stop_scan" not in st.session_state:
    st.session_state.stop_scan = False

with tab_screener:
    selected_mode = st.radio(
        "🏆 Active Screener Ranking Mode:",
        options=["Gap Monster Mode", "Catalyst Mode", "Quality Mode"],
        index=0,
        horizontal=True,
        help="Gap Monster now heavily weights Future Catalysts (30%) over past momentum (5%)."
    )
    
    score_column = {
        "Gap Monster Mode": "Gap Monster Score",
        "Catalyst Mode": "Catalyst Score",
        "Quality Mode": "Quality Score"
    }[selected_mode]
    
    with st.sidebar:
        # ------- API Keys (top of sidebar so health check can use it) -------
        st.markdown("### 🔑 API Keys")
        finnhub_api_key = st.text_input(
            "Finnhub API Key (Optional)", type="password",
            help="Improves catalyst discovery via finnhub.io. Leave blank for free YFinance/SEC data."
        )
        if not finnhub_api_key:
            st.caption("⚠️ Future earnings coverage is limited without Finnhub.")

        st.markdown("---")

        # ------- Data Source Health Check -------
        st.markdown("### 🩺 Data Source Health Check")
        if st.button("🔍 Run Health Check", use_container_width=True):
            with st.spinner("Probing data sources..."):
                hc = run_health_check(finnhub_api_key or None)
                st.session_state.health_check = hc

        hc = st.session_state.get('health_check')
        if hc:
            def _hc_icon(v):
                if v is True:  return "✅"
                if v is False: return "❌"
                return "⚠️"

            labels = {
                'yfinance_price':    'yfinance Price',
                'yfinance_earnings': 'yfinance Earnings',
                'sec_edgar':         'SEC EDGAR',
                'finnhub_key_present': 'Finnhub Key',
                'finnhub_earnings':  'Finnhub Earnings',
            }
            rows = ""
            all_critical_ok = hc.get('yfinance_price', {}).get('ok', False)
            for key, label in labels.items():
                v = hc.get(key, {})
                icon = _hc_icon(v.get('ok'))
                rows += f"<tr><td>{icon}</td><td><b>{label}</b></td><td style='color:#9ca3af;font-size:0.75rem'>{v.get('detail','')}</td></tr>"
            st.markdown(
                f"<table style='width:100%;border-collapse:collapse;font-size:0.82rem'>{rows}</table>",
                unsafe_allow_html=True
            )
            if not all_critical_ok:
                st.error("❌ Price data check failed — do not run full market scan yet.")
            else:
                st.success("✅ Price data verified — safe to scan.")
        else:
            st.caption("Click 'Run Health Check' before scanning.")

        st.markdown("---")

        # ------- Universe Settings -------
        st.markdown("### 🌍 Universe Settings")
        universe_mode = st.radio(
            "Select Scan Target:",
            options=["🧪 Test Mode (20 liquid tickers)", "🚀 Discovery Universe (500)", "Full Market Scan", "Advanced / Custom List"],
            index=0
        )

        if st.button("🔄 Refresh Market Universe", use_container_width=True):
            with st.spinner("Downloading live symbol list from Nasdaq + SEC..."):
                symbols, msg = refresh_market_universe()
                if symbols:
                    st.success(msg)
                else:
                    st.error(msg)

        tickers_list = []

        if universe_mode == "🧪 Test Mode (20 liquid tickers)":
            tickers_list = get_test_mode_items()
            st.info(f"🧪 Test Mode: {len(tickers_list)} known liquid tickers\n{', '.join(TEST_MODE_TICKERS)}")
        elif universe_mode == "🚀 Discovery Universe (500)":
            tickers_list = get_discovery_universe_items()
            st.info(f"🚀 Discovery Universe: Curated pool of {len(tickers_list)} high-growth / volatile stocks.")
        elif universe_mode == "Advanced / Custom List":
            with st.expander("Custom Ticker Input", expanded=True):
                selected_preset = st.selectbox("Load Watchlist Preset:", options=list(PRESETS.keys()), index=0)
                preset_val = PRESETS[selected_preset]
                manual_tickers = st.text_area(
                    "Enter Tickers:",
                    value=preset_val if selected_preset != "Custom List (Manual / Upload)" else "PLTR, GME",
                    height=100
                )
                uploaded_file = st.file_uploader("Or Upload Ticker CSV:", type=["csv"])
                if uploaded_file is not None:
                    tickers_list = extract_tickers_from_csv(uploaded_file)
                else:
                    tickers_list = parse_tickers_input(manual_tickers)
        else:
            # Full Market Scan — require health check first
            hc = st.session_state.get('health_check')
            if hc and hc.get('yfinance_price', {}).get('ok'):
                tickers_list = get_market_universe_tickers()
                if not tickers_list:
                    st.warning("No local universe found. Click 'Refresh Market Universe' first.")
            else:
                st.warning("⚠️ Run Health Check first to confirm price data works before launching a full market scan.")
                tickers_list = []

        st.markdown("---")
        st.markdown("### 🎯 Screen Filters")
        future_catalysts_only = st.checkbox(
            "Future Catalysts Only", value=True,
            help="Exclude stocks with no upcoming catalyst, past earnings, or earnings > 30 days away."
        )
        diagnostics_mode = st.checkbox(
            "🛠️ Diagnostics Mode", value=False,
            help="Bypass pre-filters — shows raw data diagnostics for all stocks."
        )

        st.markdown("---")
        st.markdown("### ⚙️ Scan Controls & Funnel Limits")
        max_deep_scan = st.number_input(
            "Max Deep Scan Candidates:",
            min_value=50, max_value=1000, value=300, step=50,
            help="Limits how many candidate stocks undergo heavy Stage 4 Deep Scan. Protects API limits."
        )
        if max_deep_scan > 300:
            st.warning("⚠️ Warning: Deep scanning > 300 stocks may trigger free data rate-limiting.")

        st.markdown("---")
        st.markdown(f"**Target Tickers:** {len(tickers_list)}")

        run_fast_scan = st.button("⚡ Step 1: Run Fast Market Scan", use_container_width=True, disabled=(len(tickers_list) == 0))
        
        if st.button("🛑 Stop Active Scan", use_container_width=True):
            st.session_state.stop_scan = True
            st.warning("Scan termination requested.")
            
        if st.button("🔄 Reset Scanner State", use_container_width=True):
            st.session_state.screener_results = None
            st.session_state.fast_scan_candidates = []
            st.session_state.scan_stats = {}
            st.session_state.stop_scan = False
            st.experimental_rerun()

    if run_fast_scan:
        if not tickers_list:
            st.error("No tickers to scan.")
        else:
            total_tickers = len(tickers_list)
            st.session_state.stop_scan = False
            st.session_state.screener_results = None
            st.session_state.fast_scan_candidates = []
            
            st.info(f"Initiating Fast Market Scan for {total_tickers} symbols (Price/Volume only)...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # --- STAGE 0: Raw Universe Tickers ---
            stage0_tickers = tickers_list.copy()
            raw_unfiltered_count = len(tickers_list)
            if universe_mode == "Full Market Scan":
                raw_unfiltered_count = 8521  # Nasdaq total before warrants/ETF exclusion
                
            # --- STAGE 1: Fast Price/Volume Scan ---
            stage1_survivors = []
            tickers_processed = 0
            tickers_failed = 0
            consecutive_failures = 0
            
            batch_size = 25
            total_batches = math.ceil(len(stage0_tickers) / batch_size)
            
            start_time = time.time()
            
            for idx in range(0, len(stage0_tickers), batch_size):
                if st.session_state.get('stop_scan', False):
                    st.session_state.stop_scan = False
                    st.warning("Scan stopped by user request.")
                    break
                    
                batch = stage0_tickers[idx:idx+batch_size]
                batch_tickers = [b['ticker'] for b in batch]
                current_batch = idx // batch_size + 1
                
                # Dynamic timer logic
                elapsed = time.time() - start_time
                avg_batch_time = elapsed / current_batch if current_batch > 1 else 3.0
                est_remaining_sec = avg_batch_time * (total_batches - current_batch)
                est_remaining_str = f"{int(est_remaining_sec // 60)}m {int(est_remaining_sec % 60)}s" if est_remaining_sec > 0 else "0s"
                
                status_text.markdown(f"""
                🚀 **Fast Market Scan in Progress:**
                - **Batch:** `{current_batch}` of `{total_batches}`
                - **Processed Tickers:** `{tickers_processed:,}`
                - **Failed Tickers:** `{tickers_failed:,}`
                - **Estimated Time Remaining:** `{est_remaining_str}`
                """)
                
                # Timeout wrapped fetch
                hist_data = {}
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(fetch_cached_price_volume_30m, tuple(batch_tickers))
                    try:
                        hist_data = future.result(timeout=15.0)  # 15 seconds batch timeout
                        consecutive_failures = 0
                    except concurrent.futures.TimeoutError:
                        tickers_failed += len(batch_tickers)
                        consecutive_failures += 1
                    except Exception:
                        tickers_failed += len(batch_tickers)
                        consecutive_failures += 1
                        
                if consecutive_failures > 10:
                    st.error("❌ Yahoo Finance is blocking connection (10 consecutive failures). Scan halted. Please try again later or select a smaller scan target.")
                    break
                    
                for item in batch:
                    ticker = item['ticker']
                    hist_df = hist_data.get(ticker)
                    
                    if hist_df is not None and not hist_df.empty and len(hist_df) >= 2:
                        close_col = 'Close' if 'Close' in hist_df.columns else ('Adj Close' if 'Adj Close' in hist_df.columns else None)
                        if close_col and 'Volume' in hist_df.columns:
                            closes = hist_df[close_col].dropna()
                            volumes = hist_df['Volume'].dropna()
                            if len(closes) >= 2 and len(volumes) >= 20:
                                current_price = float(closes.iloc[-1])
                                avg_vol_20d = float(volumes.tail(20).mean())
                                current_volume = float(volumes.iloc[-1]) if len(volumes) > 0 else 0.0
                                rvol = float(current_volume / avg_vol_20d) if avg_vol_20d > 0 else 1.0
                                
                                prev_close = float(closes.iloc[-2]) if len(closes) > 1 else current_price
                                change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
                                
                                if diagnostics_mode or (current_price > 2.0 and avg_vol_20d > 500000.0):
                                    stage1_survivors.append({
                                        'ticker': ticker,
                                        'cik': item['cik'],
                                        'price': current_price,
                                        'avg_vol_20d': avg_vol_20d,
                                        'rvol': rvol,
                                        'change_pct': change_pct,
                                        'hist_df': hist_df
                                    })
                                    
                tickers_processed += len(batch)
                progress_bar.progress(min((idx + batch_size) / len(stage0_tickers), 1.0))
                
                # Sleep 1.5s between batches to stay under rate limits
                if idx + batch_size < len(stage0_tickers):
                    time.sleep(1.5)
                    
            status_text.empty()
            progress_bar.empty()
            
            if stage1_survivors:
                # Rank top 100 by RVOL and absolute momentum change
                stage1_survivors.sort(key=lambda s: (s['rvol'] * 50) + abs(s['change_pct']), reverse=True)
                top_candidates = stage1_survivors[:100]
                
                st.session_state.fast_scan_candidates = top_candidates
                st.success(f"⚡ Step 1 Fast Scan complete! Found {len(stage1_survivors)} liquid stocks. Ranked top {len(top_candidates)} candidates below for deep catalyst scanning.")
            else:
                st.warning("⚠️ No stocks passed the fast liquidity filters.")

    # ----------------------------------------------------
    # DISPLAY SCANNER RESULT
    # ----------------------------------------------------
    results_df = st.session_state.screener_results
    
    if results_df is not None and not results_df.empty:
        # Override composite score with Final Score by default
        results_df['Composite Score'] = results_df['Final Score']
        
        # Capture raw data for Diagnostics before any filtering
        raw_df = results_df.copy()
        
        # Apply Future Catalysts Filter if checked and NOT in diagnostics mode
        if future_catalysts_only and not diagnostics_mode:
            results_df = results_df[
                (pd.notnull(results_df['Days Until Earnings'])) & 
                (results_df['Days Until Earnings'] >= 0) & 
                (results_df['Days Until Earnings'] <= 30)
            ].copy()
            if results_df.empty:
                st.warning("No stocks found matching the 'Future Catalysts Only' criteria.")
        
        results_df = results_df.sort_values(by='Final Score', ascending=False).reset_index(drop=True)
        
        # Compute summary metrics across the scanned active universe
        universe_size = len(results_df)
        avg_mcap = results_df['Market Cap'].mean() if 'Market Cap' in results_df.columns else 0.0
        avg_si = results_df['Short Percent'].mean() if 'Short Percent' in results_df.columns else 0.0
        if pd.isnull(avg_si): avg_si = 0.0
        avg_move = results_df['Avg Earnings Reaction (%)'].mean() if 'Avg Earnings Reaction (%)' in results_df.columns else 0.0
        if pd.isnull(avg_move): avg_move = 0.0

        st.markdown("### 📊 Scan Execution Summary")
        if diagnostics_mode:
            st.info("🛠️ **Diagnostics Mode Active**: Pre-filtering and catalyst exclusions are bypassed. Showing raw yfinance earnings diagnostics.")
            
        # HTML Funnel Tracker
        stats = st.session_state.get('scan_stats', {})
        if stats:
            st.markdown(f"""
            <div style="background-color: #0f172a; padding: 24px; border-radius: 16px; border: 1px solid rgba(139, 92, 246, 0.2); margin-bottom: 24px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);">
                <h4 style="color: #c084fc; margin-top: 0; margin-bottom: 16px; font-weight: 700; font-size: 1.1rem; display: flex; align-items: center; gap: 8px;">
                    🌪️ Market Scan Funnel Progress
                </h4>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #60a5fa;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">📁 Stage 0: Raw Universe Tickers Loaded</span>
                        <b style="color: #60a5fa; font-size: 0.95rem;">{stats.get('raw_symbols_loaded', 0):,} loaded</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #f87171;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">🛡️ Security Type Filter (Excluding Warrants, ETFs, SPACs)</span>
                        <b style="color: #f87171; font-size: 0.95rem;">-{stats.get('removed_invalid_securities', 0):,} excluded</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #34d399;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">💧 Stage 1: Fast Liquidity Filter (Price > $2, 20d Vol > 500k)</span>
                        <b style="color: #34d399; font-size: 0.95rem;">{stats.get('passed_liquidity_filter', 0):,} passed</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #fbbf24;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">💰 Stage 2: Opportunity Cap Filter ($50M - $10B)</span>
                        <b style="color: #fbbf24; font-size: 0.95rem;">{stats.get('passed_market_cap_filter', 0):,} passed</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #f472b6;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">⚡ Stage 3: Catalyst Candidate Filter</span>
                        <b style="color: #f472b6; font-size: 0.95rem;">{stats.get('passed_catalyst_filter', 0):,} passed</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #a78bfa;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">🔬 Stage 4: Priority Capped Deep Scan</span>
                        <b style="color: #a78bfa; font-size: 0.95rem;">{stats.get('deep_scanned', 0):,} scanned (Limit: {int(max_deep_scan)})</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 18px; background: rgba(139, 92, 246, 0.08); border-radius: 8px; border: 1px solid rgba(139, 92, 246, 0.3); border-left: 4px solid #8b5cf6;">
                        <span style="font-size: 0.95rem; color: #e9d5ff; font-weight: 600;">🏆 Stage 5: Final Ranked Leaders</span>
                        <b style="color: #c084fc; font-size: 1rem; font-weight: 700;">{stats.get('final_ranked', 0):,} ranked</b>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card" style="border-left-color: #3b82f6;">
                <div class="kpi-title">🏢 Scored Universe Size</div>
                <div class="kpi-value">{universe_size:,}</div>
                <div class="kpi-desc">Total active opportunities scored</div>
            </div>
            <div class="kpi-card" style="border-left-color: #f59e0b;">
                <div class="kpi-title">💰 Average Market Cap</div>
                <div class="kpi-value">${avg_mcap/1e6:,.1f}M</div>
                <div class="kpi-desc">Average capitalization</div>
            </div>
            <div class="kpi-card" style="border-left-color: #ef4444;">
                <div class="kpi-title">📊 Average Short Interest</div>
                <div class="kpi-value">{avg_si*100:.1f}%</div>
                <div class="kpi-desc">Of float shorted on average</div>
            </div>
            <div class="kpi-card" style="border-left-color: #10b981;">
                <div class="kpi-title">📈 Avg Hist Earnings Move</div>
                <div class="kpi-value">{avg_move:.1f}%</div>
                <div class="kpi-desc">Average historical post-earnings move</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Main Universe Split Dashboard (Tabs)
        df_conviction = results_df[
            (pd.notnull(results_df['Days Until Earnings'])) & 
            (results_df['Days Until Earnings'] >= 0) & 
            (results_df['Days Until Earnings'] <= 14) &
            (results_df['Opportunity Score'] >= 70.0) &
            (results_df['Prediction Score'] >= 60.0) &
            (results_df['Data Confidence'].isin(['Medium', 'High']))
        ].sort_values(by='Final Score', ascending=False).reset_index(drop=True)

        df_leaderboard = results_df.sort_values(by='Final Score', ascending=False).head(30).reset_index(drop=True)
        df_core = results_df[results_df['Universe'] == 'Core Opportunity'].sort_values(by='Final Score', ascending=False).head(20).copy()
        df_spec = results_df[results_df['Universe'] == 'Speculative'].sort_values(by='Final Score', ascending=False).head(20).copy()
        df_large = results_df[results_df['Universe'] == 'Large Cap'].sort_values(by='Final Score', ascending=False).head(20).copy()
        
        tab_conviction, tab_leader, tab_core, tab_spec, tab_large, tab_diag = st.tabs([
            "🔥 Highest Conviction Earnings Setups",
            "📅 Discovery Leaderboard (Top 30)",
            "🎯 Core Opportunity Rankings ($300M - $10B)",
            "⚠️ Speculative Rankings ($50M - $300M)",
            "🏢 Large Cap Rankings (> $10B)",
            "🛠️ Earnings Diagnostics"
        ])
        
        def prepare_display_df(df_input):
            if df_input.empty:
                return df_input
            disp = df_input.copy()
            disp['Price'] = disp['Price'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A")
            disp['RVOL'] = disp['RVOL'].apply(lambda x: f"{x:.2f}x" if pd.notnull(x) else "N/A")
            disp['Short Interest'] = disp['Short Percent'].apply(lambda x: f"{x*100:,.1f}%" if pd.notnull(x) else "N/A")
            disp['Days Until'] = disp['Days Until Earnings'].apply(lambda x: f"{int(x)}d" if pd.notnull(x) else "N/A")
            disp['Days Since'] = disp['Days Since Earnings'].apply(lambda x: f"{int(x)}d" if pd.notnull(x) else "N/A")
            disp['Historical Earnings Move'] = disp['Avg Earnings Reaction (%)'].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else "N/A")
            disp['Float'] = disp['Float Shares'].apply(lambda x: f"{x/1e6:.1f}M" if pd.notnull(x) and x > 1e6 else (f"{x:,.0f}" if pd.notnull(x) else "N/A"))
            return disp

        columns_display = [
            'Final Score', 'Opportunity Score', 'Prediction Score', 'Ticker', 
            'Why This Stock Ranked', 'Days Until', 'Historical Earnings Move',
            'Short Interest', 'Float', 'Data Confidence'
        ]
        
        def render_universe_table(df_universe):
            if df_universe.empty:
                st.info("No tickers passed the criteria for this universe.")
                return
            display_df = prepare_display_df(df_universe)
            st.dataframe(
                display_df[columns_display],
                column_config={
                    "Final Score": st.column_config.NumberColumn("Final Score", format="%.1f"),
                    "Opportunity Score": st.column_config.NumberColumn("Opportunity Score", format="%.1f"),
                    "Prediction Score": st.column_config.NumberColumn("Prediction Score", format="%.1f"),
                    "Ticker": st.column_config.TextColumn("Ticker"),
                    "Why This Stock Ranked": st.column_config.TextColumn("Catalyst Insight"),
                    "Days Until": st.column_config.TextColumn("Days Until Earnings"),
                    "Historical Earnings Move": st.column_config.TextColumn("Avg Earnings Move"),
                    "Short Interest": st.column_config.TextColumn("Short Interest"),
                    "Float": st.column_config.TextColumn("Float"),
                    "Data Confidence": st.column_config.TextColumn("Data Confidence"),
                },
                hide_index=True,
                use_container_width=True
            )

        with tab_conviction:
            st.markdown("#### 🔥 Highest Conviction Earnings Setups")
            st.write("Primary Research List: displays setups reporting within 14 days, Opportunity > 70, Prediction > 60, and Medium/High Confidence.")
            render_universe_table(df_conviction)

        with tab_leader:
            st.markdown("#### 📅 Discovery Leaderboard")
            st.write("Full market rankings sorted by weighted Final Score (60% Opportunity / 40% Prediction).")
            render_universe_table(df_leaderboard)

        with tab_core:
            st.markdown("#### Primary Opportunity Rankings ($300M - $10B)")
            render_universe_table(df_core)
            
        with tab_spec:
            st.warning("⚠️ **HIGH RISK WARNING**: Includes low-liquidity microcap stocks ($50M - $300M). Extremely volatile.")
            render_universe_table(df_spec)
            
        with tab_large:
            st.info("ℹ️ **LARGE Cap NOTE**: Large-cap stocks (> $10B). Scaling penalties applied to event metrics.")
            render_universe_table(df_large)

        with tab_diag:
            st.markdown("### 🛠️ Earnings Data Diagnostics")
            st.write("Exposes raw yfinance earnings data and API metadata to diagnose missing dates, broken parsing, or date filtering issues.")
            
            # Diagnostic calculations
            total_scanned = len(raw_df)
            valid_future = int(raw_df[
                (pd.notnull(raw_df['Next Earnings Date'])) & 
                (raw_df['Days Until Earnings'] >= 0)
            ].shape[0])
            missing_dates = int(raw_df[pd.isnull(raw_df['Next Earnings Date'])].shape[0])
            past_dates = int(raw_df[
                (pd.notnull(raw_df['Next Earnings Date'])) & 
                (raw_df['Days Until Earnings'] < 0)
            ].shape[0])
            
            within_7 = int(raw_df[
                (pd.notnull(raw_df['Days Until Earnings'])) & 
                (raw_df['Days Until Earnings'] >= 0) & 
                (raw_df['Days Until Earnings'] <= 7)
            ].shape[0])
            within_14 = int(raw_df[
                (pd.notnull(raw_df['Days Until Earnings'])) & 
                (raw_df['Days Until Earnings'] >= 0) & 
                (raw_df['Days Until Earnings'] <= 14)
            ].shape[0])
            within_30 = int(raw_df[
                (pd.notnull(raw_df['Days Until Earnings'])) & 
                (raw_df['Days Until Earnings'] >= 0) & 
                (raw_df['Days Until Earnings'] <= 30)
            ].shape[0])
            
            st.markdown("""
            <div class="kpi-container">
                <div class="kpi-card" style="border-left-color: #3b82f6; min-width: 180px;">
                    <div class="kpi-title">📋 Total Scanned</div>
                    <div class="kpi-value">{}</div>
                    <div class="kpi-desc">Total stocks processed</div>
                </div>
                <div class="kpi-card" style="border-left-color: #10b981; min-width: 180px;">
                    <div class="kpi-title">📅 Valid Future Dates</div>
                    <div class="kpi-value">{}</div>
                    <div class="kpi-desc">Next Earnings Date >= Today</div>
                </div>
                <div class="kpi-card" style="border-left-color: #ef4444; min-width: 180px;">
                    <div class="kpi-title">❌ Missing Earnings Dates</div>
                    <div class="kpi-value">{}</div>
                    <div class="kpi-desc">No next earnings date found</div>
                </div>
                <div class="kpi-card" style="border-left-color: #f59e0b; min-width: 180px;">
                    <div class="kpi-title">⏳ Past Earnings Dates</div>
                    <div class="kpi-value">{}</div>
                    <div class="kpi-desc">Next Earnings Date in past</div>
                </div>
            </div>
            """.format(total_scanned, valid_future, missing_dates, past_dates), unsafe_allow_html=True)
            
            st.markdown("#### ⏳ Future Catalyst Windows")
            col_w7, col_w14, col_w30 = st.columns(3)
            with col_w7:
                st.metric("Within 7 Days", f"{within_7} stocks")
            with col_w14:
                st.metric("Within 14 Days", f"{within_14} stocks")
            with col_w30:
                st.metric("Within 30 Days", f"{within_30} stocks")
            
            st.markdown("---")
            st.markdown("#### 🔍 Raw Earnings Data & Source Status")
            
            def compute_source_status(row):
                cal_status = row.get('Calendar Status', 'Not Fetched')
                hist_status = row.get('Earnings Dates Status', 'Not Fetched')
                next_ed = row.get('Next Earnings Date')
                days_until = row.get('Days Until Earnings')
                price_status = row.get('Price Data Status', 'Valid')
                
                status_parts = []
                if price_status != 'Valid':
                    status_parts.append(f"Price Status: {price_status}")
                
                if pd.isnull(next_ed):
                    status_parts.append(f"Missing Earnings Date (Cal: {cal_status} | Hist: {hist_status})")
                elif days_until is not None and days_until < 0:
                    status_parts.append(f"Past Earnings Date (Cal: {cal_status} | Hist: {hist_status})")
                else:
                    status_parts.append(f"Valid Future Earnings Date (Cal: {cal_status} | Hist: {hist_status})")
                
                return " | ".join(status_parts)
            
            diag_df = raw_df.copy()
            diag_df['Data Source Status'] = diag_df.apply(compute_source_status, axis=1)
            
            diag_df['Next Earnings Date Raw'] = diag_df['Next Earnings Date'].apply(
                lambda d: d.strftime("%Y-%m-%d") if isinstance(d, (datetime.date, datetime.datetime)) else str(d) if pd.notnull(d) else "N/A"
            )
            diag_df['Days Until'] = diag_df['Days Until Earnings'].apply(
                lambda x: f"{int(x)}d" if pd.notnull(x) else "N/A"
            )
            
            diag_display = diag_df[['Ticker', 'Next Earnings Date Raw', 'Days Until', 'Data Source Status']].copy()
            diag_display.columns = ['Ticker', 'Next Earnings Date', 'Days Until Earnings', 'Data Source Status']
            
            st.dataframe(
                diag_display,
                column_config={
                    "Ticker": st.column_config.TextColumn("Ticker"),
                    "Next Earnings Date": st.column_config.TextColumn("Next Earnings Date"),
                    "Days Until Earnings": st.column_config.TextColumn("Days Until Earnings"),
                    "Data Source Status": st.column_config.TextColumn("Data Source Status"),
                },
                hide_index=True,
                use_container_width=True
            )

        # Drill-down Panel Layout
        st.markdown("---")
        
        st.markdown("### 🔍 Catalyst Deep-Dive Selector")
        selected_ticker = st.selectbox(
            "Select Ticker to Inspect Details & Technicals:",
            options=results_df['Ticker'].head(60).tolist()
        )
        
        if selected_ticker:
            ticker_row = results_df[results_df['Ticker'] == selected_ticker].iloc[0]
            ticker_meta = st.session_state.metadata.get(selected_ticker, {})
            
            col_chart, col_drill = st.columns([13, 7])
            
            with col_drill:
                st.markdown(f"#### Universe: **{ticker_row['Universe']}**")
                
                # Visual scores comparison
                st.markdown(f"**Final Score: {ticker_row['Final Score']:.1f}**")
                cats = ['Final Score', 'Opportunity Score', 'Prediction Score', 'RVOL Score', 'Float Score', 'Short Interest', 'Hist Reaction']
                scores = [
                    ticker_row['Final Score'],
                    ticker_row['Opportunity Score'],
                    ticker_row['Prediction Score'],
                    ticker_row['RVOL Score'],
                    ticker_row['Float Score'],
                    ticker_row['Short Interest Score'],
                    ticker_row['Historical Reaction Score']
                ]
                
                score_data = pd.DataFrame({'Category': cats, 'Score': scores})
                colors = ['#3b82f6' if c == 'Final Score' else ('#ef4444' if s < 0 else '#10b981') for c, s in zip(cats, scores)]
                fig_scores = px.bar(score_data, x='Score', y='Category', orientation='h')
                fig_scores.update_traces(marker_color=colors)
                fig_scores.update_layout(margin=dict(l=20, r=20, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#ffffff')
                fig_scores.update_xaxes(title="Points", range=[-50, 100])
                st.plotly_chart(fig_scores, use_container_width=True)
                
            with col_chart:
                if selected_ticker in st.session_state.raw_history:
                    st.markdown(f"### 📈 Technical Chart - {selected_ticker}")
                    chart_hist = st.session_state.raw_history[selected_ticker]
                    chart_df = chart_hist.tail(90).copy()
                    close_col = 'Adj Close' if 'Adj Close' in chart_df.columns else 'Close'
                        
                    fig_chart = go.Figure()
                    fig_chart.add_trace(go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df[close_col], name="Price"))
                    fig_chart.update_layout(height=380, xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15, 23, 42, 0.4)', font_color='#ffffff', xaxis=dict(gridcolor='rgba(255,255,255,0.05)'), yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title="Price ($)"))
                    st.plotly_chart(fig_chart, use_container_width=True)

            # Premium Research Panel (full-width below)
            st.markdown("---")
            st.markdown(f"### 🔬 Premium Research & Sentiment Terminal — **{selected_ticker}**")
            
            tab_res_profile, tab_res_scoring, tab_res_filings, tab_res_reactions = st.tabs([
                "🏢 Business Profile & Cap Table",
                "🎯 Scoring & Sentiment Insights",
                "📄 Recent SEC Filings Activity",
                "📊 Surprise & Earnings Reaction History"
            ])
            
            with tab_res_profile:
                st.markdown(f"#### 🏢 {ticker_row['Company Name']}")
                
                desc = ticker_meta.get('business_summary') or ticker_meta.get('summary') or f"No detailed business description available for {selected_ticker} in the free source database. Please search using SEC EDGAR below."
                st.write(desc)
                
                col_cap1, col_cap2, col_cap3, col_cap4 = st.columns(4)
                with col_cap1:
                    mcap_val = ticker_row['Market Cap']
                    mcap_str = f"${mcap_val:,.0f}" if pd.notnull(mcap_val) else "N/A"
                    st.metric("Market Cap", mcap_str)
                with col_cap2:
                    fl_val = ticker_row['Float Shares']
                    fl_str = f"{fl_val/1e6:.1f}M" if pd.notnull(fl_val) and fl_val > 1e6 else (f"{fl_val:,.0f}" if pd.notnull(fl_val) else "N/A")
                    st.metric("Float Shares", fl_str)
                with col_cap3:
                    short_pct = ticker_row['Short Percent']
                    short_str = f"{short_pct*100:.1f}%" if pd.notnull(short_pct) else "N/A"
                    st.metric("Short Interest (%)", short_str)
                with col_cap4:
                    st.metric("Analyst Coverage", f"{ticker_row['Analysts'] or 0} analysts")

            with tab_res_scoring:
                col_sc1, col_sc2 = st.columns(2)
                
                with col_sc1:
                    st.success("##### 📈 Model Bullish Drivers")
                    likes = []
                    
                    rvol = ticker_row.get('RVOL') or 0.0
                    if rvol >= 1.5:
                        likes.append(f"**High Relative Volume**: RVOL is {rvol:.1f}x, showing strong institutional/retail participation.")
                    
                    s_pct = ticker_row.get('Short Percent') or 0.0
                    if s_pct >= 0.10:
                        likes.append(f"**Short Squeeze Fuel**: Short interest is {s_pct*100:.1f}% of float, presenting high potential for a short-covering rally.")
                    
                    float_s = ticker_row.get('Float Shares') or 0.0
                    if float_s > 0 and float_s < 30_000_000:
                        likes.append(f"**Low Float Velocity**: Float of {float_s/1e6:.1f}M shares enables quick price appreciation on positive event surprises.")
                    
                    rsi_val = ticker_row.get('RSI') or 50.0
                    if rsi_val >= 60.0:
                        likes.append(f"**Positive Technical Momentum**: RSI is {rsi_val:.1f}, indicating a solid uptrend going into the catalyst.")
                    elif rsi_val < 40.0:
                        likes.append(f"**Oversold Reversal Signal**: RSI is {rsi_val:.1f}, which shows extremely oversold conditions primed for a technical bounce.")
                    
                    sec_filings = ticker_row.get('SEC Filings', [])
                    if any('4' in str(f.get('form', '')) for f in sec_filings):
                        likes.append("**Insider Buying Activity**: Form 4 filings indicate recent transactional insider alignment.")
                        
                    if not likes:
                        likes.append("Technical structure remains neutral and balanced leading into the catalyst window.")
                        
                    for l in likes:
                        st.markdown(f"- {l}")
                        
                with col_sc2:
                    st.warning("##### ⚠️ Bearish Factors & Key Risks")
                    dislikes = []
                    
                    price = ticker_row.get('Price') or 0.0
                    ema_20 = ticker_row.get('EMA 20')
                    if ema_20 and price < ema_20:
                        dislikes.append("**Short-Term Downtrend**: Trading below its EMA 20, indicating near-term selling pressure.")
                        
                    s_pct = ticker_row.get('Short Percent') or 0.0
                    if s_pct < 0.03:
                        dislikes.append(f"**Low Squeeze Potential**: Minimal short interest ({s_pct*100:.1f}%) means short covering won't fuel the move.")
                        
                    avg_react = ticker_row.get('Avg Earnings Reaction (%)') or 0.0
                    if avg_react < 4.0:
                        dislikes.append(f"**Low Volatility History**: Historical earnings moves are small ({avg_react:.1f}%), suggesting limited event volatility.")
                        
                    d_until = ticker_row.get('Days Until Earnings')
                    if d_until is None:
                        dislikes.append("**Date Uncertainty**: No verified upcoming earnings date, increasing operational risk.")
                        
                    if not dislikes:
                        dislikes.append("Model detects no significant immediate structural or volume risks.")
                        
                    for d in dislikes:
                        st.markdown(f"- {d}")

            with tab_res_filings:
                st.markdown("#### 📄 Recent SEC Filings Activity (Last 30 Days)")
                try:
                    sec_filings = ticker_row.get('SEC Filings', [])
                    if not sec_filings:
                        st.info("No recent material filings found in the SEC EDGAR system.")
                    else:
                        filings_df = pd.DataFrame(sec_filings)
                        
                        # Requirement 1: Print available columns
                        available_columns = filings_df.columns.tolist()
                        print(f"[{selected_ticker}] SEC filings available columns: {available_columns}")
                        
                        # Requirement 3 & 4: Normalize description and date
                        if 'description' not in filings_df.columns:
                            if 'primaryDocDescription' in filings_df.columns:
                                filings_df['description'] = filings_df['primaryDocDescription']
                            else:
                                filings_df['description'] = "No filing description available from SEC source."
                                
                        if 'filedAt' not in filings_df.columns:
                            if 'filingDate' in filings_df.columns:
                                filings_df['filedAt'] = filings_df['filingDate']
                            elif 'acceptanceDateTime' in filings_df.columns:
                                filings_df['filedAt'] = filings_df['acceptanceDateTime']
                            else:
                                filings_df['filedAt'] = "Date Unavailable"
                                
                        # Fill any missing values with clean defaults
                        filings_df['description'] = filings_df['description'].fillna("No filing description available from SEC source.")
                        filings_df['filedAt'] = filings_df['filedAt'].fillna("Date Unavailable")
                        
                        # Requirement 2: Safe column selection
                        preferred_columns = [
                            'form',
                            'filedAt',
                            'filingDate',
                            'acceptanceDateTime',
                            'description',
                            'primaryDocDescription',
                            'accessionNumber'
                        ]
                        display_columns = [
                            c for c in preferred_columns
                            if c in filings_df.columns
                        ]
                        
                        # Build displaying dataframe safely
                        filings_display = filings_df[display_columns].copy()
                        
                        # Map displayed columns to user-friendly titles
                        column_mapping = {
                            'form': 'Form Type',
                            'filedAt': 'Filing Date',
                            'filingDate': 'Filing Date (Raw)',
                            'acceptanceDateTime': 'Acceptance Time',
                            'description': 'Description',
                            'primaryDocDescription': 'Doc Description',
                            'accessionNumber': 'Accession No'
                        }
                        display_titles = {c: column_mapping[c] for c in display_columns}
                        
                        filings_display.columns = [display_titles[c] for c in display_columns]
                        
                        st.dataframe(filings_display, hide_index=True, use_container_width=True)
                        
                        # Requirement 7: SEC Diagnostics
                        st.markdown("---")
                        st.markdown("##### 🛠️ SEC EDGAR Diagnostics")
                        diag_col1, diag_col2 = st.columns(2)
                        with diag_col1:
                            st.metric("Filings Returned", len(sec_filings))
                        with diag_col2:
                            st.markdown(f"**Available Fields:** `{available_columns}`")
                            st.markdown(f"**Selected Display Fields:** `{display_columns}`")
                            
                except Exception as e:
                    st.error(f"⚠️ SEC Display Error: {e}")
                    st.info("No filing description available from SEC source. The rest of the Research Terminal remains functional.")
                
                cik_str = ticker_meta.get('cik')
                if cik_str:
                    st.link_button(
                        "🔍 Open Official SEC EDGAR Filing Directory",
                        f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_str}"
                    )

            with tab_res_reactions:
                st.markdown("#### 📊 Event Volatility & Surprise History")
                avg_react = ticker_row.get('Avg Earnings Reaction (%)') or 0.0
                st.metric("Avg Historical Post-Earnings Move", f"{avg_react:.2f}%")
                st.write("The historical earnings reaction represents the absolute price movement on the day of and day following previous earnings releases.")

        st.markdown("---")
        st.markdown("#### 💾 Save Scan Session")
        if st.button("💾 Save Results to CSV"):
            csv_path, msg = save_screening_run(results_df)
            if csv_path:
                st.success(msg)
            else:
                st.error(msg)
    elif st.session_state.fast_scan_candidates:
        st.markdown("### 📋 Step 2: Select Catalyst Candidates for Deep Scan")
        st.write("Review the top candidates ranked by Fast Scan RVOL and Momentum. Check the symbols you wish to fully deep-scan.")
        
        # Build candidate DataFrame
        fast_df = pd.DataFrame(st.session_state.fast_scan_candidates)
        fast_df['Select'] = True  # Checked by default
        
        # Display Columns
        fast_df['Price'] = fast_df['price'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A")
        fast_df['Volume (20d Avg)'] = fast_df['avg_vol_20d'].apply(lambda x: f"{x/1e6:.2f}M" if pd.notnull(x) else "N/A")
        fast_df['RVOL'] = fast_df['rvol'].apply(lambda x: f"{x:.2f}x" if pd.notnull(x) else "N/A")
        fast_df['Change (%)'] = fast_df['change_pct'].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "N/A")
        
        display_cols = ['Select', 'ticker', 'Price', 'Volume (20d Avg)', 'RVOL', 'Change (%)']
        
        edited_df = st.data_editor(
            fast_df[display_cols],
            column_config={
                "Select": st.column_config.CheckboxColumn("Deep Scan?", default=True),
                "ticker": st.column_config.TextColumn("Ticker"),
                "Price": st.column_config.TextColumn("Price"),
                "Volume (20d Avg)": st.column_config.TextColumn("Avg Volume (20d)"),
                "RVOL": st.column_config.TextColumn("RVOL"),
                "Change (%)": st.column_config.TextColumn("Change (%)"),
            },
            disabled=['ticker', 'Price', 'Volume (20d Avg)', 'RVOL', 'Change (%)'],
            hide_index=True,
            use_container_width=True,
            key="deep_scan_select_editor"
        )
        
        selected_tickers = edited_df[edited_df['Select'] == True]['ticker'].tolist()
        
        st.markdown("---")
        
        # Run Step 3 Button
        if st.button("⚡ Run Step 3: Deep Scan Selected Candidates", use_container_width=True):
            if not selected_tickers:
                st.error("Please select at least 1 candidate ticker to deep scan.")
            else:
                selected_candidates = [c for c in st.session_state.fast_scan_candidates if c['ticker'] in selected_tickers]
                total_deep = len(selected_candidates)
                
                st.info(f"Initiating Deep Scan for {total_deep} selected candidates...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # --- STAGE 2: Opportunity Universe Filter ---
                status_text.text("Stage 2/5: Fetching fundamentals and cap table info...")
                stage2_survivors = []
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = {
                        executor.submit(fetch_cached_fundamentals_24h, s['ticker'], finnhub_api_key): s
                        for s in selected_candidates
                    }
                    
                    completed = 0
                    for future in concurrent.futures.as_completed(futures):
                        s = futures[future]
                        ticker = s['ticker']
                        try:
                            fund = future.result()
                            mcap = fund.get('market_cap')
                            is_operating = fund.get('is_operating', True)
                            
                            # Keep all selected unless they are explicitly not operating (in non-diag mode)
                            if diagnostics_mode or is_operating:
                                s_updated = s.copy()
                                s_updated['market_cap'] = mcap
                                s_updated['long_name'] = fund.get('long_name', ticker)
                                s_updated['float_shares'] = fund.get('float_shares')
                                s_updated['shares_short'] = fund.get('shares_short')
                                s_updated['short_percent'] = fund.get('short_percent')
                                s_updated['analysts'] = fund.get('analysts')
                                s_updated['business_summary'] = fund.get('business_summary')
                                stage2_survivors.append(s_updated)
                        except Exception:
                            pass
                        completed += 1
                        progress_bar.progress((completed / total_deep) * 0.25)
                        
                # --- STAGE 3: Catalyst Candidate Filter ---
                status_text.text("Stage 3/5: Querying upcoming earnings dates & recent SEC filings...")
                stage3_survivors = []
                
                if stage2_survivors:
                    def check_catalyst_data(s, finnhub_key=None):
                        ticker = s['ticker']
                        cik = s['cik']
                        earn_data = fetch_cached_earnings_12h(ticker, finnhub_key)
                        sec_data = fetch_cached_sec_24h(ticker, cik) if cik else {'sec_filings': [], 'sec_status': 'No CIK'}
                        return earn_data, sec_data

                    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                        futures = {
                            executor.submit(check_catalyst_data, s, finnhub_api_key): s
                            for s in stage2_survivors
                        }
                        
                        completed = 0
                        total = len(futures)
                        for future in concurrent.futures.as_completed(futures):
                            s = futures[future]
                            ticker = s['ticker']
                            try:
                                earn_data, sec_data = future.result()
                                
                                next_ed = earn_data.get('next_earnings_date')
                                last_ed = earn_data.get('last_earnings_date')
                                hist_eds = earn_data.get('hist_earnings_dates', [])
                                calendar_status = earn_data.get('calendar_status')
                                earnings_dates_status = earn_data.get('earnings_dates_status')
                                
                                today = datetime.date.today()
                                days_until = (next_ed - today).days if next_ed else None
                                days_since = (today - last_ed).days if last_ed else None
                                
                                sec_filings = sec_data.get('sec_filings', [])
                                
                                s_updated = s.copy()
                                s_updated['next_earnings_date'] = next_ed
                                s_updated['last_earnings_date'] = last_ed
                                s_updated['hist_earnings_dates'] = hist_eds
                                s_updated['calendar_status'] = calendar_status
                                s_updated['earnings_dates_status'] = earnings_dates_status
                                s_updated['days_until_earnings'] = days_until
                                s_updated['days_since_earnings'] = days_since
                                s_updated['sec_filings'] = sec_filings
                                stage3_survivors.append(s_updated)
                            except Exception:
                                pass
                            completed += 1
                            progress_bar.progress(0.25 + (completed / total) * 0.25)
                            
                # --- STAGE 4: Capped Deep Scan ---
                status_text.text("Stage 4/5: Deep-scanning volatility and catalyst reaction metrics...")
                deep_metrics = []
                meta_dict_all = {}
                hist_data_all = {}
                
                if stage3_survivors:
                    completed = 0
                    total = len(stage3_survivors)
                    for s in stage3_survivors:
                        ticker = s['ticker']
                        
                        meta = {
                            'ticker': ticker,
                            'name': s.get('long_name', ticker),
                            'market_cap': s.get('market_cap'),
                            'next_earnings_date': s.get('next_earnings_date'),
                            'last_earnings_date': s.get('last_earnings_date'),
                            'float_shares': s.get('float_shares'),
                            'shares_short': s.get('shares_short'),
                            'short_percent': s.get('short_percent'),
                            'analysts': s.get('analysts'),
                            'hist_earnings_dates': s.get('hist_earnings_dates', []),
                            'calendar_status': s.get('calendar_status'),
                            'earnings_dates_status': s.get('earnings_dates_status'),
                            'data_confidence': s.get('data_confidence', 'Low'),
                            'sec_filings': s.get('sec_filings', []),
                            'summary': s.get('business_summary', "")
                        }
                        meta_dict_all[ticker] = meta
                        
                        hist_df = s['hist_df']
                        hist_data_all[ticker] = hist_df
                        
                        res, msg = calculate_single_ticker_metrics(ticker, hist_df, {ticker: meta}, diagnostics_mode=diagnostics_mode)
                        if res is not None:
                            deep_metrics.append(res)
                            
                        completed += 1
                        progress_bar.progress(0.5 + (completed / total) * 0.25)
                        
                st.session_state.metadata.update(meta_dict_all)
                st.session_state.raw_history.update(hist_data_all)
                
                # --- STAGE 5: Final Ranking ---
                status_text.text("Stage 5/5: Generating final conviction Opportunity/Prediction scores...")
                df_results = calculate_screener_scores(deep_metrics)
                
                progress_bar.progress(1.0)
                status_text.empty()
                progress_bar.empty()
                
                total_scored = len(df_results) if not df_results.empty else 0
                
                st.session_state.screener_results = df_results
                st.session_state.scan_stats = {
                    'raw_symbols_loaded': len(selected_candidates),
                    'removed_invalid_securities': 0,
                    'passed_liquidity_filter': len(selected_candidates),
                    'passed_market_cap_filter': len(stage2_survivors),
                    'passed_catalyst_filter': len(stage3_survivors),
                    'deep_scanned': len(stage3_survivors),
                    'final_ranked': total_scored
                }
                
                if df_results.empty:
                    st.warning("No stocks passed the deep catalyst scoring filters.")
                else:
                    st.success("Deep Catalyst Scan completed successfully!")
                    st.experimental_rerun()
    else:
        st.info("👈 Set universe and click the '⚡ Step 1: Run Fast Market Scan' button in the sidebar.")

# ----------------------------------------------------
# TAB 2: HISTORICAL SAVED VIEW
# ----------------------------------------------------
with tab_history:
    st.markdown("### 📂 Review Historical Screening Runs")
    saved_files = get_historical_files()
    if not saved_files:
        st.info("No saved runs detected in `data/history/` yet.")
    else:
        selected_file = st.selectbox("Select Historic Screening CSV File:", options=saved_files)
        if selected_file:
            file_path = os.path.join("/Users/mathiasmesfin/Downloads/Stock Screener/data/history", selected_file)
            try:
                hist_df = pd.read_csv(file_path)
                st.markdown(f"#### Saved Screener Results ({len(hist_df)} tickers saved)")
                st.dataframe(hist_df, hide_index=True, use_container_width=True)
            except Exception as e:
                st.error(f"Error loading historical file: {str(e)}")

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

import api_fetch
from api_fetch import (
    API_WORKER_OPTIONS,
    DEFAULT_MAX_CONCURRENT_API_WORKERS,
    FAST_SCAN_MAX_WORKERS,
    build_concurrency_snapshot,
    clear_telemetry_data_caches,
    fetch_cached_earnings_12h,
    fetch_cached_fundamentals_24h,
    fetch_cached_sec_24h,
    is_thread_pool_failure,
    merge_api_telemetry_delta,
    new_api_telemetry_delta,
    record_thread_creation_failure,
)

# Setup custom yfinance cache locations to avoid OperationalError on database writes
repo_root = os.path.dirname(os.path.abspath(__file__))
cache_dir = os.path.join(repo_root, "cache")
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
    calculate_future_catalyst_score,
    build_leaderboard_exclusions,
    save_screening_run,
    get_historical_files,
    run_health_check,
    get_test_mode_items,
    TEST_MODE_TICKERS,
    get_dev_test_scan_items,
    DEV_TEST_SCAN_TICKERS,
    get_discovery_universe_items,
    DISCOVERY_UNIVERSE_TICKERS,
)
from historical_event_lab import show_historical_event_lab_ui



def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def count_future_catalyst_survivors(df):
    """Count scored tickers with earnings 0–30 days ahead."""
    if df is None or df.empty:
        return 0
    return int(df[
        (pd.notnull(df['Days Until Earnings'])) &
        (df['Days Until Earnings'] >= 0) &
        (df['Days Until Earnings'] <= 30)
    ].shape[0])


# Pipeline filters (liquidity / market-cap floors are scoring filters, not scan queue caps)
LIQUIDITY_MIN_PRICE = 2.0
LIQUIDITY_MIN_AVG_VOL = 500_000.0
MARKET_CAP_FLOOR = 50_000_000


def merge_funnel_metrics(updates):
    """Merge funnel stage counts into session state."""
    base = dict(st.session_state.get('funnel_metrics') or {})
    base.update({k: v for k, v in updates.items() if v is not None})
    st.session_state.funnel_metrics = base


def parse_fast_scan_limit(limit_text, use_full_market=False):
    """
    Parse Fast Scan Limit for Full Market Scan.
    Returns (is_full_market, limit_int_or_none, display_label, error_message).
    """
    if use_full_market:
        return True, None, "Full Market", None
    cleaned = (limit_text or "").strip().replace(",", "")
    if not cleaned:
        return False, None, "", "Enter a symbol limit (e.g. 1000) or enable full market scan."
    if cleaned.lower() in ("full", "full market", "all", "none"):
        return True, None, "Full Market", None
    try:
        limit_n = int(float(cleaned))
    except ValueError:
        return False, None, cleaned, "Fast Scan Limit must be a whole number (e.g. 1000)."
    if limit_n < 1:
        return False, None, str(limit_n), "Fast Scan Limit must be at least 1."
    return False, limit_n, f"{limit_n:,}", None


def apply_deep_scan_cap(stage3_survivors, max_deep_scan, deep_scan_all_eligible):
    """Apply optional Max Deep Scan cap after priority sort. Returns (candidates, telemetry dict)."""
    before = len(stage3_survivors)
    if deep_scan_all_eligible:
        candidates = list(stage3_survivors)
        return candidates, {
            'deep_scan_before_cap_count': before,
            'deep_scan_cap_applied': False,
            'deep_scan_cap_applied_label': 'No',
            'max_deep_scan_setting': None,
            'max_deep_scan_setting_label': 'All eligible (cap disabled)',
            'deep_scan_after_cap_count': before,
            'deep_scan_removed_by_cap_count': 0,
        }
    cap_n = int(max_deep_scan)
    candidates = stage3_survivors[:cap_n]
    removed = max(0, before - len(candidates))
    cap_applied = removed > 0
    return candidates, {
        'deep_scan_before_cap_count': before,
        'deep_scan_cap_applied': cap_applied,
        'deep_scan_cap_applied_label': 'Yes' if cap_applied else 'No',
        'max_deep_scan_setting': cap_n,
        'max_deep_scan_setting_label': f"{cap_n:,}",
        'deep_scan_after_cap_count': len(candidates),
        'deep_scan_removed_by_cap_count': removed,
    }


def warn_deep_scan_all_candidate_count(count):
    """Non-blocking warnings when deep-scanning all eligible candidates."""
    if count > 1000:
        st.error(
            f"⚠️ **Large deep scan:** {count:,} eligible candidates will be deep-scanned. "
            "This may take a long time and can trigger API rate limits."
        )
    elif count > 500:
        st.warning(
            f"⚠️ **Large deep scan:** {count:,} eligible candidates will be deep-scanned. "
            "Expect longer runtime and heavier API usage."
        )


def resolve_universe_funnel_counts(universe_mode, tickers_list):
    """Raw vs security-filtered counts for the active universe mode."""
    build_stats = st.session_state.get('universe_build_stats') or {}
    loaded = len(tickers_list)
    if universe_mode == "Full Market Scan":
        raw = build_stats.get('raw_universe_loaded')
        after_security = build_stats.get('after_security_filter_count', loaded)
        if raw is None:
            raw = after_security
        return int(raw), int(after_security)
    return loaded, loaded


def render_true_funnel_metrics(funnel_metrics, exclusion_df=None):
    """Display exact survivor counts per pipeline stage in a clean horizontal strip."""
    if not funnel_metrics:
        return

    u_raw = funnel_metrics.get('raw_universe_loaded') or funnel_metrics.get('after_security_filter_count')
    u_elig = funnel_metrics.get('after_price_volume_eligibility_count') or funnel_metrics.get('after_security_filter_count')
    u_liq = funnel_metrics.get('after_liquidity_filter_count')
    u_deep = funnel_metrics.get('deep_scan_input_count') or funnel_metrics.get('deep_scan_before_cap_count')
    u_scored = funnel_metrics.get('final_scored_count')

    items = []
    if u_raw is not None: items.append(("Universe", f"{int(u_raw):,}"))
    if u_elig is not None: items.append(("Eligible", f"{int(u_elig):,}"))
    if u_liq is not None: items.append(("Liquid", f"{int(u_liq):,}"))
    if u_deep is not None: items.append(("Deep Scan", f"{int(u_deep):,}"))
    if u_scored is not None: items.append(("Scored", f"{int(u_scored):,}"))

    if items:
        strip_parts = ['<div class="funnel-strip"><span style="color: #6B7280; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; margin-right: 6px;">Funnel:</span>']
        for idx, (label, val) in enumerate(items):
            if idx > 0:
                strip_parts.append('<span class="funnel-divider">/</span>')
            strip_parts.append(f'<div class="funnel-item"><span class="funnel-label">{label}</span><span class="funnel-val">{val}</span></div>')
        strip_parts.append('</div>')
        st.markdown("".join(strip_parts), unsafe_allow_html=True)

    with st.expander("Pipeline Stage Breakdown", expanded=False):
        fast_scan_limit = funnel_metrics.get('fast_scan_limit_label', '—')
        st.caption(f"Fast scan queue cap: {fast_scan_limit} (applied before liquidity filter).")

        filter_stages = [
            ("1. Raw universe", "raw_universe_loaded"),
            ("2. Security filter", "after_security_filter_count"),
            ("3. Eligibility", "after_price_volume_eligibility_count"),
            ("4. Liquidity filter", "after_liquidity_filter_count"),
            ("5. Step 2 candidates", "after_fast_scan_candidates_count"),
            ("6. Catalyst prefilter", "after_catalyst_prefilter_count"),
            ("7. Deep scan queue", "deep_scan_after_cap_count"),
            ("8. Scored results", "final_scored_count"),
            ("9. Catalyst window (<=30d)", "future_catalyst_only_count"),
        ]
        stage_cols = st.columns(3)
        for i, (label, key) in enumerate(filter_stages):
            val = funnel_metrics.get(key)
            if val is not None:
                with stage_cols[i % 3]:
                    st.metric(label, f"{int(val):,}")

        breakdown = dict(funnel_metrics.get('exclusion_breakdown') or {})
        if exclusion_df is not None and not exclusion_df.empty and 'failed_reason' in exclusion_df.columns:
            breakdown = exclusion_df['failed_reason'].value_counts().to_dict()

        if breakdown:
            st.markdown("##### Exclusion Reasons")
            breakdown_df = (
                pd.DataFrame([{'Reason': reason, 'Count': count} for reason, count in breakdown.items()])
                .sort_values('Count', ascending=False)
                .reset_index(drop=True)
            )
            st.dataframe(breakdown_df, hide_index=True, width='stretch')


def render_api_telemetry_panel(telemetry_data):
    """Display API health and rate limit telemetry in a compact diagnostics table."""
    if not telemetry_data:
        return

    with st.expander("System Diagnostics", expanded=False):
        api_services = [
            ("Fundamentals", telemetry_data.get("finnhub_fundamentals") or telemetry_data.get("yfinance_fundamentals") or {}),
            ("Earnings Calendar", telemetry_data.get("finnhub_earnings") or telemetry_data.get("yfinance_earnings") or {}),
            ("SEC EDGAR", telemetry_data.get("sec_edgar") or {}),
        ]

        diag_rows = []
        for name, metrics in api_services:
            attempted = metrics.get("attempted", 0)
            if attempted > 0:
                hit = metrics.get("cache_hit", 0)
                failed = metrics.get("failure", 0)
                status = "Healthy" if failed == 0 else f"{failed} Errors"
                diag_rows.append({
                    "Source": name,
                    "Requests": f"{attempted:,}",
                    "Cache Hit": f"{hit:,}",
                    "Failed": f"{failed:,}",
                    "Status": status
                })
            else:
                diag_rows.append({
                    "Source": name,
                    "Requests": "—",
                    "Cache Hit": "—",
                    "Failed": "—",
                    "Status": "Not queried"
                })

        st.dataframe(pd.DataFrame(diag_rows), hide_index=True, width='stretch')

        conc = telemetry_data.get("concurrency") or build_concurrency_snapshot()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.caption(f"Concurrency: {conc.get('max_concurrent_api_workers', DEFAULT_MAX_CONCURRENT_API_WORKERS)} workers")
        with col2:
            st.caption(f"Attempts: {telemetry_data.get('total_api_attempts', 0):,}")
        with col3:
            st.caption(f"Failures: {telemetry_data.get('total_api_failures', 0):,}")
        with col4:
            st.caption(f"Rate Limits (429): {telemetry_data.get('rate_limit_failures', 0):,}")


# ----------------------------------------------------
# PAGE CONFIGURATION & STYLING
# ----------------------------------------------------
st.set_page_config(
    page_title="Market Discovery | Research",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Institutional design system: dark neutral palette, flat surfaces, tabular nums
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        background-color: #0F1115 !important;
        color: #F2F4F7 !important;
        font-size: 14px;
    }

    /* Compact Header Bar */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0 10px 0;
        margin-bottom: 14px;
        border-bottom: 1px solid #2A2F38;
    }
    .product-title {
        font-size: 16px;
        font-weight: 700;
        letter-spacing: 0.05em;
        color: #F2F4F7;
        text-transform: uppercase;
    }
    .product-subtitle {
        font-size: 12px;
        color: #9CA3AF;
        letter-spacing: 0.02em;
        margin-top: 1px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #15181E !important;
        border-right: 1px solid #2A2F38 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        font-size: 11px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.07em !important;
        color: #9CA3AF !important;
        margin-top: 14px !important;
        margin-bottom: 6px !important;
    }

    /* Section Headings */
    h1, h2, h3, h4, h5 {
        color: #F2F4F7 !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
    }
    h3 { font-size: 15px !important; }
    h4 { font-size: 13.5px !important; }
    h5 { font-size: 12.5px !important; }

    /* Financial Metrics and Tabular Alignment */
    [data-testid="stMetricValue"] {
        font-size: 18px !important;
        font-weight: 600 !important;
        color: #F2F4F7 !important;
        font-variant-numeric: tabular-nums !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 11px !important;
        color: #9CA3AF !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }

    /* Tabs: clean underline navigation, zero pill glow */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px !important;
        border-bottom: 1px solid #2A2F38 !important;
        background-color: transparent !important;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 8px 16px !important;
        color: #9CA3AF !important;
        font-weight: 500 !important;
        font-size: 13px !important;
    }
    .stTabs [aria-selected="true"] {
        color: #F2F4F7 !important;
        border-bottom: 2px solid #5B8DEF !important;
        font-weight: 600 !important;
        background-color: transparent !important;
    }

    /* Buttons: institutional flat blue (#5B8DEF) */
    div.stButton > button {
        background-color: #5B8DEF !important;
        color: #0F1115 !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        border-radius: 4px !important;
        border: 1px solid #5B8DEF !important;
        padding: 6px 16px !important;
        box-shadow: none !important;
        transition: all 0.15s ease !important;
    }
    div.stButton > button:hover {
        background-color: #4A7CDA !important;
        border-color: #4A7CDA !important;
        color: #FFFFFF !important;
        box-shadow: none !important;
        transform: none !important;
    }
    div.stButton > button:disabled {
        background-color: #191D24 !important;
        color: #6B7280 !important;
        border-color: #2A2F38 !important;
    }

    /* Tables: thin borders, tabular numbers */
    [data-testid="stDataFrame"] {
        border: 1px solid #2A2F38 !important;
        border-radius: 4px !important;
        font-variant-numeric: tabular-nums !important;
    }

    /* Summary metric strip: flat inline statistics */
    .summary-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 28px;
        padding: 12px 18px;
        background-color: #15181E;
        border: 1px solid #2A2F38;
        border-radius: 4px;
        margin-bottom: 16px;
    }
    .summary-item {
        display: flex;
        flex-direction: column;
    }
    .summary-label {
        font-size: 11px;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 2px;
    }
    .summary-value {
        font-size: 18px;
        font-weight: 600;
        color: #F2F4F7;
        font-variant-numeric: tabular-nums;
    }

    /* Compact horizontal funnel strip */
    .funnel-strip {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 14px;
        padding: 9px 14px;
        background-color: #15181E;
        border: 1px solid #2A2F38;
        border-radius: 4px;
        margin-bottom: 14px;
        font-size: 12.5px;
    }
    .funnel-item {
        display: flex;
        align-items: baseline;
        gap: 6px;
    }
    .funnel-label {
        color: #9CA3AF;
        font-size: 11.5px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .funnel-val {
        color: #F2F4F7;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
    }
    .funnel-divider {
        color: #2A2F38;
    }

    /* Overview / Landing Page Styles */
    .overview-hero-card {
        background-color: #15181E;
        border: 1px solid #2A2F38;
        border-radius: 6px;
        padding: 24px 28px;
        margin-bottom: 24px;
    }
    .overview-badge {
        display: inline-block;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #5B8DEF;
        background-color: rgba(91, 141, 239, 0.12);
        border: 1px solid rgba(91, 141, 239, 0.3);
        padding: 3px 8px;
        border-radius: 3px;
        margin-bottom: 10px;
    }
    .overview-hero-title {
        font-size: 20px;
        font-weight: 700;
        color: #F2F4F7;
        margin-bottom: 8px;
        letter-spacing: -0.01em;
    }
    .overview-hero-desc {
        font-size: 13.5px;
        line-height: 1.6;
        color: #9CA3AF;
        max-width: 960px;
    }
    .overview-section-header {
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #9CA3AF;
        margin: 26px 0 14px 0;
        padding-bottom: 6px;
        border-bottom: 1px solid #2A2F38;
    }
    .tutorial-step-card {
        background-color: #15181E;
        border: 1px solid #2A2F38;
        border-radius: 6px;
        padding: 16px 18px;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .tutorial-step-num {
        font-size: 11px;
        font-weight: 700;
        color: #5B8DEF;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .tutorial-step-title {
        font-size: 13.5px;
        font-weight: 600;
        color: #F2F4F7;
        margin-bottom: 8px;
    }
    .tutorial-step-body {
        font-size: 12.5px;
        line-height: 1.5;
        color: #9CA3AF;
        flex-grow: 1;
    }
    .video-placeholder-card {
        background-color: #15181E;
        border: 1px dashed #2A2F38;
        border-radius: 6px;
        padding: 36px 20px;
        text-align: center;
        margin-bottom: 14px;
    }
    .video-placeholder-title {
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #F2F4F7;
        margin-bottom: 6px;
    }
    .video-placeholder-subtitle {
        font-size: 12.5px;
        color: #9CA3AF;
        max-width: 520px;
        margin: 0 auto 12px auto;
        line-height: 1.5;
    }
    .video-placeholder-path {
        font-family: monospace;
        font-size: 12px;
        background-color: #0F1115;
        color: #5B8DEF;
        padding: 4px 10px;
        border-radius: 3px;
        border: 1px solid #2A2F38;
        display: inline-block;
    }
    .architecture-card {
        background-color: #15181E;
        border: 1px solid #2A2F38;
        border-radius: 6px;
        padding: 18px 22px;
        margin-top: 14px;
    }
    .architecture-title {
        font-size: 13.5px;
        font-weight: 600;
        color: #F2F4F7;
        margin-bottom: 8px;
    }
    .architecture-body {
        font-size: 12.5px;
        line-height: 1.6;
        color: #9CA3AF;
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

def apply_concurrency_telemetry(api_workers=None):
    """Store current ThreadPoolExecutor settings in api_telemetry.concurrency."""
    workers = int(
        api_workers
        if api_workers is not None
        else st.session_state.get("max_concurrent_api_workers", DEFAULT_MAX_CONCURRENT_API_WORKERS)
    )
    snap = build_concurrency_snapshot(workers)
    if "api_telemetry" in st.session_state and st.session_state.api_telemetry is not None:
        st.session_state.api_telemetry["concurrency"] = snap
    return workers


def record_thread_pool_telemetry_failure():
    """Increment thread_creation_failures on the session telemetry blob."""
    telem = st.session_state.get("api_telemetry")
    if not telem:
        return
    delta = new_api_telemetry_delta()
    record_thread_creation_failure(delta)
    merge_api_telemetry_delta(telem, delta)


def init_api_telemetry(force_reset=False):
    """Initializes or resets the API telemetry data in the session state."""
    if force_reset or "api_telemetry" not in st.session_state or st.session_state.api_telemetry is None:
        if force_reset:
            clear_telemetry_data_caches()
        st.session_state.api_telemetry = api_fetch.new_api_telemetry_snapshot()
    else:
        snap = api_fetch.new_api_telemetry_snapshot()
        for key, val in snap.items():
            if key not in st.session_state.api_telemetry:
                st.session_state.api_telemetry[key] = val
    apply_concurrency_telemetry()


def _add_telemetry_error(error_msg):
    """Adds an error message to the last_errors list in session state, capping it at 10."""
    if "api_telemetry" in st.session_state and st.session_state.api_telemetry is not None:
        if "last_errors" not in st.session_state.api_telemetry:
            st.session_state.api_telemetry["last_errors"] = []
        st.session_state.api_telemetry["last_errors"].insert(0, error_msg)
        st.session_state.api_telemetry["last_errors"] = st.session_state.api_telemetry["last_errors"][:10]

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_cached_price_volume_30m(tickers_tuple):
    """Cache price/volume history for 30 minutes."""
    return fetch_historical_data(list(tickers_tuple))

def get_fast_opportunity_score(s):
    """Fast Opportunity Score (0-100) for ranking Stage 3 survivors before deep scan."""
    rvol = s.get('rvol') or 0.0
    rvol_score = 100.0 if rvol >= 3.0 else (0.0 if rvol <= 0.5 else (rvol - 0.5) / 2.5 * 100.0)

    change = s.get('change_pct') or 0.0
    price_strength_score = 100.0 if change >= 8.0 else (0.0 if change <= 0.0 else change / 8.0 * 100.0)

    vol_accel_ratio = 1.0
    gap_pct = 0.0
    hist_df = s.get('hist_df')
    if hist_df is not None and not hist_df.empty and 'Volume' in hist_df.columns:
        volumes = hist_df['Volume'].dropna()
        if len(volumes) >= 20:
            vol_5d = float(volumes.tail(5).mean())
            vol_20d = float(volumes.tail(20).mean())
            vol_accel_ratio = vol_5d / vol_20d if vol_20d > 0 else 1.0
        close_col = 'Close' if 'Close' in hist_df.columns else ('Adj Close' if 'Adj Close' in hist_df.columns else None)
        if close_col and 'Open' in hist_df.columns:
            closes = hist_df[close_col].dropna()
            opens = hist_df['Open'].dropna()
            if len(closes) >= 2 and len(opens) >= 1:
                prev_close = float(closes.iloc[-2])
                open_today = float(opens.iloc[-1])
                if prev_close > 0:
                    gap_pct = abs((open_today - prev_close) / prev_close * 100.0)

    vol_accel_score = 100.0 if vol_accel_ratio >= 2.0 else (0.0 if vol_accel_ratio <= 0.8 else (vol_accel_ratio - 0.8) / 1.2 * 100.0)
    earnings_score = max(0.0, calculate_future_catalyst_score(s.get('days_until_earnings'), s.get('days_since_earnings')))
    gap_score = min(100.0, gap_pct / 3.0 * 100.0)

    mkt_cap = s.get('market_cap')
    if mkt_cap is None:
        mcap_score = 50.0
    else:
        m = mkt_cap / 1e6
        if 300.0 <= m <= 2000.0:
            mcap_score = 100.0
        elif m <= 10_000.0:
            mcap_score = 60.0
        elif m > 10_000.0:
            mcap_score = 10.0
        elif m >= 50.0:
            mcap_score = 80.0
        else:
            mcap_score = 0.0

    return (
        rvol_score * 0.20 +
        price_strength_score * 0.20 +
        vol_accel_score * 0.15 +
        earnings_score * 0.25 +
        gap_score * 0.10 +
        mcap_score * 0.10
    )

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
    path = os.path.join(repo_root, "data", "us_stock_universe.csv")
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
<div class="header-container">
    <div>
        <div class="product-title">Market Discovery</div>
        <div class="product-subtitle">Earnings & Catalyst Research</div>
    </div>
</div>
""", unsafe_allow_html=True)

tab_home, tab_screener, tab_history, tab_lab = st.tabs(["Overview", "Scanner", "Saved Watchlists", "Historical Event Lab"])

def init_deep_scan_session_state(force_reset=False):
    """Initializes or resets the session state for batched deep scanning."""
    if force_reset or "deep_scan_full_candidate_list" not in st.session_state:
        st.session_state.deep_scan_full_candidate_list = []
        st.session_state.deep_scan_completed_tickers = []
        st.session_state.deep_scan_pending_tickers = []
        st.session_state.deep_scan_failed_tickers = []
        st.session_state.deep_scan_batch_results = []
        st.session_state.deep_scan_cumulative_results_df = pd.DataFrame()
        st.session_state.deep_scan_batch_telemetry = []
        st.session_state.deep_scan_timestamps = []
        st.session_state.deep_scan_run_all = False
        st.session_state.deep_scan_pause = False
        st.session_state.deep_scan_loaded = False
        st.session_state.deep_scan_cooldown_until = None
        st.session_state.deep_scan_batch_in_progress = False
        st.session_state.deep_scan_cumulative_meta = {}
        st.session_state.deep_scan_cumulative_history = {}
        st.session_state.deep_scan_cumulative_failures = {}

def process_single_deep_scan_batch(batch_candidates, finnhub_api_key, diagnostics_mode, api_workers):
    """
    Process a list of candidate dicts through Stages 2-5.
    Returns dict with meta_dict, hist_data, results_df, failed_tickers, runtime, batch_429, batch_http, stage counts.
    """
    batch_start = time.time()
    telemetry = st.session_state.api_telemetry

    rate_429_before = (
        telemetry.get("finnhub_fundamentals", {}).get("rate_limit_429", 0) +
        telemetry.get("finnhub_earnings", {}).get("rate_limit_429", 0) +
        telemetry.get("sec_edgar", {}).get("rate_limit_429", 0)
    )
    http_before = telemetry.get("error_categories", {}).get("http_failures", 0)

    # --- STAGE 2: Fundamentals ---
    stage2_survivors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=api_workers) as executor:
        futures = {}
        for s in batch_candidates:
            try:
                fut = executor.submit(fetch_cached_fundamentals_24h, s['ticker'], finnhub_api_key)
                futures[fut] = s
            except Exception as e:
                if is_thread_pool_failure(e):
                    record_thread_pool_telemetry_failure()
                raise

        for future in concurrent.futures.as_completed(futures):
            s = futures[future]
            ticker = s['ticker']
            try:
                fund, telem_delta = future.result()
                merge_api_telemetry_delta(telemetry, telem_delta)

                if not fund:
                    telemetry["candidates_skipped_due_to_missing_fundamentals"] += 1
                    continue

                is_operating = fund.get('is_operating', True)
                if diagnostics_mode or is_operating:
                    s_updated = s.copy()
                    s_updated['market_cap'] = fund.get('market_cap')
                    s_updated['long_name'] = fund.get('long_name', ticker)
                    s_updated['float_shares'] = fund.get('float_shares')
                    s_updated['shares_short'] = fund.get('shares_short')
                    s_updated['short_percent'] = fund.get('short_percent')
                    s_updated['analysts'] = fund.get('analysts')
                    s_updated['business_summary'] = fund.get('business_summary')
                    s_updated['sector'] = fund.get('sector')
                    s_updated['industry'] = fund.get('industry')
                    s_updated['forward_pe'] = fund.get('forward_pe')
                    s_updated['trailing_pe'] = fund.get('trailing_pe')
                    s_updated['price_to_sales'] = fund.get('price_to_sales')
                    s_updated['revenue_growth'] = fund.get('revenue_growth')
                    s_updated['short_ratio'] = fund.get('short_ratio')
                    s_updated['ttm_levered_fcf'] = fund.get('ttm_levered_fcf')
                    s_updated['quarterly_fcf'] = fund.get('quarterly_fcf')
                    stage2_survivors.append(s_updated)
            except Exception as e:
                if is_thread_pool_failure(e):
                    record_thread_pool_telemetry_failure()

    # --- STAGE 3: Earnings & SEC ---
    stage3_survivors = []
    stage3_failures = {}

    if stage2_survivors:
        def check_catalyst_data(s, finnhub_key=None):
            ticker = s['ticker']
            cik = s.get('cik')
            earn_data, earn_delta = fetch_cached_earnings_12h(ticker, finnhub_key)
            if cik:
                sec_data, sec_delta = fetch_cached_sec_24h(ticker, cik)
            else:
                sec_data = {'sec_filings': [], 'sec_status': 'No CIK'}
                sec_delta = new_api_telemetry_delta()
                sec_delta["sec_edgar"]["skipped_no_cik"] += 1
            combined_delta = new_api_telemetry_delta()
            merge_api_telemetry_delta(combined_delta, earn_delta)
            merge_api_telemetry_delta(combined_delta, sec_delta)
            return earn_data, sec_data, combined_delta

        with concurrent.futures.ThreadPoolExecutor(max_workers=api_workers) as executor:
            futures = {}
            for s in stage2_survivors:
                try:
                    fut = executor.submit(check_catalyst_data, s, finnhub_api_key)
                    futures[fut] = s
                except Exception as e:
                    if is_thread_pool_failure(e):
                        record_thread_pool_telemetry_failure()
                    raise

            for future in concurrent.futures.as_completed(futures):
                s = futures[future]
                ticker = s['ticker']
                try:
                    earn_data, sec_data, telem_delta = future.result()
                    merge_api_telemetry_delta(telemetry, telem_delta)

                    next_ed = earn_data.get('next_earnings_date') if earn_data else None
                    last_ed = earn_data.get('last_earnings_date') if earn_data else None

                    if next_ed is None and last_ed is None:
                        stage3_failures[ticker] = "Missing earnings dates"
                        telemetry["candidates_skipped_due_to_missing_earnings"] += 1
                        continue

                    hist_eds = earn_data.get('hist_earnings_dates', []) if earn_data else []
                    calendar_status = earn_data.get('calendar_status') if earn_data else None
                    earnings_dates_status = earn_data.get('earnings_dates_status') if earn_data else None

                    today = datetime.date.today()
                    days_until = (next_ed - today).days if next_ed else None
                    days_since = (today - last_ed).days if last_ed else None

                    sec_filings = sec_data.get('sec_filings', []) if sec_data else []

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

                except Exception as e:
                    if is_thread_pool_failure(e):
                        record_thread_pool_telemetry_failure()
                    stage3_failures[ticker] = str(e)

    # --- STAGE 4: Calculate metrics ---
    deep_metrics = []
    stage4_failures = {}
    meta_dict = {}
    hist_data = {}

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
            'summary': s.get('business_summary', ""),
            'sector': s.get('sector'),
            'industry': s.get('industry'),
            'forward_pe': s.get('forward_pe'),
            'trailing_pe': s.get('trailing_pe'),
            'price_to_sales': s.get('price_to_sales'),
            'revenue_growth': s.get('revenue_growth'),
            'short_ratio': s.get('short_ratio'),
            'ttm_levered_fcf': s.get('ttm_levered_fcf'),
            'quarterly_fcf': s.get('quarterly_fcf')
        }
        meta_dict[ticker] = meta
        hist_data[ticker] = s['hist_df']

        res, msg = calculate_single_ticker_metrics(ticker, s['hist_df'], {ticker: meta}, diagnostics_mode=diagnostics_mode)
        if res is not None:
            deep_metrics.append(res)
        else:
            stage4_failures[ticker] = msg

    # --- STAGE 5: Scoring ---
    df_results = calculate_screener_scores(deep_metrics)

    all_failed = {}
    all_failed.update(stage3_failures)
    all_failed.update(stage4_failures)

    batch_runtime = time.time() - batch_start

    rate_429_after = (
        telemetry.get("finnhub_fundamentals", {}).get("rate_limit_429", 0) +
        telemetry.get("finnhub_earnings", {}).get("rate_limit_429", 0) +
        telemetry.get("sec_edgar", {}).get("rate_limit_429", 0)
    )
    http_after = telemetry.get("error_categories", {}).get("http_failures", 0)

    return {
        'meta_dict': meta_dict,
        'hist_data': hist_data,
        'results_df': df_results,
        'failed_tickers': all_failed,
        'runtime': batch_runtime,
        'batch_429': rate_429_after - rate_429_before,
        'batch_http': http_after - http_before,
        'batch_size': len(batch_candidates),
        'stage2_count': len(stage2_survivors),
        'stage3_count': len(stage3_survivors),
        'stage4_count': len(deep_metrics),
    }


def _merge_batch_results(result):
    """Merge a single batch's results into session_state."""
    meta_dict = result['meta_dict']
    hist_data = result['hist_data']
    df_results = result['results_df']
    failed = result['failed_tickers']

    st.session_state.deep_scan_cumulative_meta.update(meta_dict)
    st.session_state.deep_scan_cumulative_history.update(hist_data)
    st.session_state.deep_scan_cumulative_failures.update(failed)

    if not df_results.empty:
        succeeded = df_results['Ticker'].tolist()
        st.session_state.deep_scan_completed_tickers.extend(succeeded)
    else:
        succeeded = []

    for t, err in failed.items():
        st.session_state.deep_scan_failed_tickers.append({
            'ticker': t,
            'error': err,
        })

    if not df_results.empty:
        st.session_state.deep_scan_cumulative_results_df = pd.concat([
            st.session_state.deep_scan_cumulative_results_df,
            df_results,
        ], ignore_index=True)

    batch_number = len(st.session_state.deep_scan_batch_telemetry) + 1
    cumulative_completed = len(st.session_state.deep_scan_completed_tickers)
    cumulative_pending = len(st.session_state.deep_scan_pending_tickers)

    batch_telem = {
        'batch_number': batch_number,
        'batch_size': result.get('batch_size', 0),
        'tickers_attempted': result.get('batch_size', 0),
        'tickers_succeeded': len(succeeded),
        'tickers_failed': len(failed),
        'rate_limit_429_count': result['batch_429'],
        'http_failure_count': result['batch_http'],
        'runtime_seconds': round(result['runtime'], 1),
        'cumulative_completed': cumulative_completed,
        'cumulative_pending': cumulative_pending,
    }
    st.session_state.deep_scan_batch_telemetry.append(batch_telem)
    st.session_state.deep_scan_timestamps.append(time.time())
    st.session_state.deep_scan_batch_results.append(df_results)

    merge_funnel_metrics({
        'deep_scan_input_count': cumulative_completed + cumulative_pending + len(st.session_state.deep_scan_failed_tickers),
        'after_fundamentals_filter_count': result['stage2_count'],
        'after_catalyst_prefilter_count': result['stage3_count'],
        'after_market_cap_filter_count': result['stage4_count'],
        'final_scored_count': len(st.session_state.deep_scan_cumulative_results_df) if not st.session_state.deep_scan_cumulative_results_df.empty else 0,
    })


if "screener_results" not in st.session_state:
    st.session_state.screener_results = None
    st.session_state.raw_history = {}
    st.session_state.metadata = {}
    st.session_state.scan_stats = {}
if "fast_scan_candidates" not in st.session_state:
    st.session_state.fast_scan_candidates = []
if "stop_scan" not in st.session_state:
    st.session_state.stop_scan = False
if "stage4_failures" not in st.session_state:
    st.session_state.stage4_failures = {}
if "deep_scan_tickers" not in st.session_state:
    st.session_state.deep_scan_tickers = []
if "deep_scan_snapshot" not in st.session_state:
    st.session_state.deep_scan_snapshot = {}
if "funnel_metrics" not in st.session_state:
    st.session_state.funnel_metrics = {}
if "universe_build_stats" not in st.session_state:
    st.session_state.universe_build_stats = {}
init_api_telemetry()
init_deep_scan_session_state()

def render_overview_tab():
    # Hero / Mission Statement
    st.markdown("""
<div class="overview-hero-card">
    <div class="overview-badge">Institutional Research Platform</div>
    <div class="overview-hero-title">Market Discovery Engine</div>
    <div class="overview-hero-desc">
        A systematic research prioritization terminal designed to isolate high-conviction catalyst opportunities across US equities ahead of earnings announcements, corporate events, and SEC regulatory filings. Rather than applying lagging technical or valuation screens, the engine evaluates liquidity persistence, relative volume surges, historical post-earnings reaction distributions, and directional risk/reward asymmetry to surface institutional setups before volatility expands.
    </div>
</div>
""", unsafe_allow_html=True)

    # Workflow & Quick Start Guide
    st.markdown('<div class="overview-section-header">Workflow & Quick Start Guide</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
<div class="tutorial-step-card">
    <div class="tutorial-step-num">Step 01</div>
    <div class="tutorial-step-title">Universe Selection</div>
    <div class="tutorial-step-body">
        Select your target universe in the sidebar: <strong>Curated Discovery</strong> for liquid catalyst growth names, <strong>Dev Benchmark</strong> for testing, or <strong>Full Market</strong> across NYSE/NASDAQ. Set price floors and liquidity thresholds to eliminate micro-cap illiquidity.
    </div>
</div>
""", unsafe_allow_html=True)

    with col2:
        st.markdown("""
<div class="tutorial-step-card">
    <div class="tutorial-step-num">Step 02</div>
    <div class="tutorial-step-title">Stage 1 Screening</div>
    <div class="tutorial-step-body">
        Switch to the <strong>Scanner</strong> tab and run the scan. Stage 1 executes high-speed vectorized screening across price action, relative volume expansion (RVOL &ge; 1.5), ATR volatility compression, and moving average structure in seconds.
    </div>
</div>
""", unsafe_allow_html=True)

    with col3:
        st.markdown("""
<div class="tutorial-step-card">
    <div class="tutorial-step-num">Step 03</div>
    <div class="tutorial-step-title">Batch Deep Scan</div>
    <div class="tutorial-step-body">
        Under the <strong>Deep Scan Queue</strong> sidebar, click <strong>Load Candidates</strong>. Deep scanning is processed in non-blocking, rate-metered batches to enrich candidates with live SEC EDGAR 8-K/10-Q filings, confirmed earnings dates, and balance sheet metrics.
    </div>
</div>
""", unsafe_allow_html=True)

    with col4:
        st.markdown("""
<div class="tutorial-step-card">
    <div class="tutorial-step-num">Step 04</div>
    <div class="tutorial-step-title">Research Dossier</div>
    <div class="tutorial-step-body">
        Evaluate candidate rankings prioritized by <strong>Final Score</strong> and <strong>Directional Edge Score (DPS)</strong>. Click any symbol to open its institutional dossier: historical reaction swing ranges, insider activity, and event risk parameters.
    </div>
</div>
""", unsafe_allow_html=True)

    # Walkthrough Demo Video Section
    st.markdown('<div class="overview-section-header">Engine Walkthrough Demonstrations</div>', unsafe_allow_html=True)

    vtab_prescan, vtab_live = st.tabs(["Pre-Market Morning Scan Demo", "Live Custom Screener Demo"])
    with vtab_prescan:
        if os.path.exists("assets/demo.mp4"):
            st.video("assets/demo.mp4")
            st.caption("Pre-Market Morning Scan Walkthrough · assets/demo.mp4")
        else:
            st.info("Pre-market walkthrough video asset not found.")

    with vtab_live:
        if os.path.exists("assets/demo_live.mp4"):
            st.video("assets/demo_live.mp4")
            st.caption("Live Custom Screener & Batch Deep Scan Walkthrough · assets/demo_live.mp4")
        else:
            st.info("Live screener walkthrough video asset not found.")


    # Quantitative Edge Metrics Reference
    st.markdown('<div class="overview-section-header">Quantitative Methodology & Edge Metrics</div>', unsafe_allow_html=True)

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.markdown("""
<div class="architecture-card" style="margin-top: 0px;">
    <div class="architecture-title">Composite Scoring Model</div>
    <div class="architecture-body">
        <strong>Final Score (0–100)</strong> integrates fundamental catalyst quality with technical momentum using an institutional 60/40 weighted framework:
        <br><br>
        &bull; <strong>Catalyst Score (60%)</strong>: Days until confirmed earnings announcement, recent material SEC filings (Form 8-K, 10-Q, 10-K), and balance sheet solvency.
        <br>
        &bull; <strong>Technical Score (40%)</strong>: Relative volume expansion (RVOL), ATR range expansion, EMA 20/50 trend alignment, and price momentum stability.
    </div>
</div>
""", unsafe_allow_html=True)

    with m_col2:
        st.markdown("""
<div class="architecture-card" style="margin-top: 0px;">
    <div class="architecture-title">Event-Driven Volatility & Directional Edge</div>
    <div class="architecture-body">
        <strong>Directional Edge Score (DPS)</strong> assesses whether a pre-earnings candidate exhibits statistical continuation vs. exhaustion:
        <br><br>
        &bull; <strong>Historical Reaction Move</strong>: Mean absolute percentage price move on post-earnings open across the trailing 4 reporting cycles.
        <br>
        &bull; <strong>Short Squeeze Quality</strong>: Evaluates float short interest paired with days-to-cover and positive momentum to highlight explosive asymmetric upside convexity.
    </div>
</div>
""", unsafe_allow_html=True)

    # Production Architecture & API Rate Limit Mitigation
    st.markdown('<div class="overview-section-header">Production Architecture & Rate-Limit Mitigation</div>', unsafe_allow_html=True)

    st.markdown("""
<div class="architecture-card">
    <div class="architecture-title">Pre-Computed Morning Batch Scanning Architecture</div>
    <div class="architecture-body">
        <strong>The Rate Limit Challenge</strong>: Free and standard tier market APIs (Finnhub, Yahoo Finance) enforce strict rate caps (30–60 requests per minute). In a multi-tenant public deployment, simultaneous user scans would trigger immediate HTTP 429 throttling.
        <br><br>
        <strong>The Solution</strong>: Production deployments decouple data retrieval from user-facing serving:
        <br>
        1. <strong>Pre-Market Execution (06:30 AM EST)</strong>: An automated cron daemon executes a headless batch scan across all market universes, collecting fundamentals, SEC filings, and technical metrics once.
        <br>
        2. <strong>Immutable Snapshot Store</strong>: The enriched results are persisted to high-speed disk storage (<code>data/history/daily_discovery_YYYYMMDD.parquet</code>).
        <br>
        3. <strong>Instantaneous Web Serving</strong>: When web visitors access the dashboard, the application loads the pre-computed snapshot in <strong>&lt;15ms</strong> with <strong>zero live external API calls</strong>. This guarantees zero rate-limit degradation and supports unlimited concurrent traffic at near-zero operating cost.
    </div>
</div>
""", unsafe_allow_html=True)


with tab_home:
    render_overview_tab()


def get_file_eastern_datetime(file_path):
    """Converts file modification epoch timestamp to US/Eastern timezone."""
    try:
        ts = os.path.getmtime(file_path)
        from zoneinfo import ZoneInfo
        eastern = ZoneInfo("America/New_York")
        return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).astimezone(eastern)
    except Exception:
        try:
            return datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        except Exception:
            return datetime.datetime.now()


def load_latest_precomputed_discovery(universe_name=None):
    """Loads precomputed morning scan from parquet or csv.
    Tries universe-specific file first (e.g. daily_discovery_latest_full.parquet),
    then falls back to the generic daily_discovery_latest.parquet/csv."""
    history_dir = os.path.join(repo_root, "data", "history")

    # Build ordered list of candidate files to try
    candidates = []
    if universe_name and universe_name != "discovery":
        candidates += [
            os.path.join(history_dir, f"daily_discovery_latest_{universe_name}.parquet"),
            os.path.join(history_dir, f"daily_discovery_latest_{universe_name}.csv"),
        ]
    candidates += [
        os.path.join(history_dir, "daily_discovery_latest.parquet"),
        os.path.join(history_dir, "daily_discovery_latest.csv"),
    ]

    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            if path.endswith(".parquet"):
                df = pd.read_parquet(path)
            else:
                df = pd.read_csv(path)
            mod_time = get_file_eastern_datetime(path)
            return df, os.path.basename(path), mod_time
        except Exception:
            continue

    # Last resort: newest historical screener CSV
    hist_files = get_historical_files()
    if hist_files:
        try:
            newest = os.path.join(repo_root, "data", "history", hist_files[0])
            df = pd.read_csv(newest)
            mod_time = get_file_eastern_datetime(newest)
            return df, hist_files[0], mod_time
        except Exception:
            pass
    return None, None, None



def fetch_single_ticker_deep_dive(ticker, finnhub_key=""):
    """Fetches and scores a single ticker live on demand."""
    sym = ticker.strip().upper()
    try:
        hist = fetch_historical_data([sym], period="1y")
        df_bars = hist.get(sym)
        if df_bars is None or df_bars.empty:
            return None, f"Price history unavailable for {sym}."

        fund_data, _ = fetch_cached_fundamentals_24h(sym)
        earn_data, _ = fetch_cached_earnings_12h(sym, finnhub_key)
        sec_data, _ = fetch_cached_sec_24h(sym)

        meta = {}
        if fund_data: meta.update(fund_data)
        if earn_data: meta.update(earn_data)
        if sec_data: meta.update(sec_data)

        res, msg = calculate_single_ticker_metrics(sym, df_bars, {sym: meta}, diagnostics_mode=False)
        if not res:
            return None, f"Scoring failed for {sym}: {msg}"

        scored_df = calculate_screener_scores([res])
        if scored_df is None or scored_df.empty:
            return None, f"Scoring engine returned empty result for {sym}."
        return scored_df, None
    except Exception as e:
        return None, f"Error analyzing {sym}: {str(e)}"


with tab_screener:
    finnhub_api_key = ""

    scan_source_col1, scan_source_col2 = st.columns(2)
    with scan_source_col1:
        data_source_mode = st.radio(
            "Data Source",
            options=["Pre-Market Morning Scan (Instant)", "Live Custom Screener (On-Demand)"],
            index=0,
            horizontal=True,
            help="Pre-Market Scan loads pre-computed institutional rankings instantly without API rate limits."
        )
    with scan_source_col2:
        selected_mode = st.radio(
            "Strategy",
            options=["Gap Monster Mode", "Catalyst Mode", "Quality Mode"],
            format_func=lambda x: {"Gap Monster Mode": "Gap", "Catalyst Mode": "Catalyst", "Quality Mode": "Quality"}[x],
            index=0,
            horizontal=True,
            help="Ranking strategy weighting. Final Score = 60% Opportunity + 40% Prediction."
        )

    score_column = {
        "Gap Monster Mode": "Gap Monster Score",
        "Catalyst Mode": "Catalyst Score",
        "Quality Mode": "Quality Score"
    }.get(selected_mode, "Gap Monster Score")

    is_morning_mode = (str(data_source_mode) == "Pre-Market Morning Scan (Instant)")

    if is_morning_mode:
        with st.sidebar:
            st.markdown("### Pre-Market Filters")

            # Universe selector — mirrors live mode options
            pre_universe_choice = st.selectbox(
                "Scan Universe:",
                options=["Discovery Pool", "Full Market", "Sample (50)", "Test (20)"],
                index=0,
                help="Select which pre-computed scan universe to load. Run scripts/morning_scan.py with the matching --universe flag to generate data for each.",
                key="pre_market_universe_choice"
            )
            pre_universe_map = {
                "Discovery Pool": "discovery",
                "Full Market": "full",
                "Sample (50)": "sample",
                "Test (20)": "test",
            }
            pre_universe_name = pre_universe_map[pre_universe_choice]

            if st.session_state.get('morning_scan_mod_time'):
                st.caption(f"Updated: {st.session_state.morning_scan_mod_time.strftime('%b %d, %Y at %I:%M %p %Z')}")

            filter_ticker = st.text_input(
                "Filter Ticker / Company:",
                placeholder="e.g. ACI, ALEC, NVDA"
            ).strip().upper()

            filter_days = st.slider(
                "Max Days to Earnings:",
                min_value=0, max_value=60, value=30, step=5
            )

            filter_rvol = st.slider(
                "Min Relative Volume (RVOL):",
                min_value=0.0, max_value=5.0, value=0.0, step=0.2
            )

            future_catalysts_only = st.checkbox(
                "Future Catalysts Only", value=True,
                help="Exclude stocks with no upcoming catalyst, past earnings, or earnings > 30 days away."
            )
            diagnostics_mode = st.checkbox(
                "Diagnostics Mode", value=False,
                help="Bypass pre-filters — shows raw data diagnostics for all stocks."
            )

            st.markdown("---")
            st.markdown("### Live Ticker Research")
            lookup_ticker = st.text_input(
                "On-Demand Symbol Lookup:",
                placeholder="e.g. PLTR, GME, TSLA"
            ).strip().upper()
            if st.button("Analyze Live", width='stretch', disabled=not lookup_ticker):
                with st.spinner(f"Analyzing {lookup_ticker} live..."):
                    single_df, err = fetch_single_ticker_deep_dive(lookup_ticker, finnhub_api_key)
                    if single_df is not None:
                        if st.session_state.screener_results is not None:
                            existing = st.session_state.screener_results[
                                st.session_state.screener_results['Ticker'] != lookup_ticker
                            ]
                            st.session_state.screener_results = pd.concat([single_df, existing], ignore_index=True)
                        else:
                            st.session_state.screener_results = single_df
                        st.session_state.active_selected_ticker = lookup_ticker
                        st.success(f"{lookup_ticker} loaded successfully.")
                        safe_rerun()
                    else:
                        st.error(err)

            st.markdown("---")
            if st.button("Reload Morning Scan", width='stretch'):
                st.session_state.screener_results = None
                st.session_state.active_data_source = None
                st.session_state.pre_market_loaded_universe = None
                safe_rerun()

        # Load universe — reload if universe selection changed
        loaded_universe = st.session_state.get('pre_market_loaded_universe')
        needs_load = (
            st.session_state.get('active_data_source') != 'morning'
            or st.session_state.get('screener_results') is None
            or loaded_universe != pre_universe_name
        )
        if needs_load:
            pre_df, pre_fmt, mod_time = load_latest_precomputed_discovery(pre_universe_name)
            if pre_df is not None and not pre_df.empty:
                st.session_state.screener_results = pre_df
                st.session_state.active_data_source = 'morning'
                st.session_state.morning_scan_mod_time = mod_time
                st.session_state.pre_market_loaded_universe = pre_universe_name
                st.session_state.morning_scan_source_file = pre_fmt

        tickers_list = []
        run_fast_scan = False
        universe_mode = "Pre-Market Morning Scan"
        fast_scan_limit_error = None
        fast_scan_is_full_market = True
        fast_scan_limit_n = None
        fast_scan_limit_label = "Pre-Market"
        effective_scan_count = len(st.session_state.screener_results) if st.session_state.screener_results is not None else 0
    else:
        if st.session_state.get('active_data_source') == 'morning':
            st.session_state.screener_results = None
            st.session_state.active_data_source = 'live'
        filter_ticker = ""
        filter_days = 60
        filter_rvol = 0.0

        with st.sidebar:

            # ------- Scan Configuration -------
            st.markdown("### Scan Configuration")
            universe_mode = st.radio(
                "Universe Target:",
                options=[
                    "Test Mode (20 liquid tickers)",
                    "Dev Test Scan (50)",
                    "Discovery Universe",
                    "Full Market Scan",
                    "Advanced / Custom List",
                ],
                format_func=lambda x: {
                    "Test Mode (20 liquid tickers)": "Test (20 liquid)",
                    "Dev Test Scan (50)": "Dev Test (50)",
                    "Discovery Universe": "Discovery Pool",
                    "Full Market Scan": "Full Market",
                    "Advanced / Custom List": "Custom Watchlist",
                }[x],
                index=0
            )

            tickers_list = []

            if universe_mode == "Test Mode (20 liquid tickers)":
                tickers_list = get_test_mode_items()
                st.caption(f"Test Mode: {len(tickers_list)} liquid tickers ({', '.join(TEST_MODE_TICKERS[:6])}...)")
            elif universe_mode == "Dev Test Scan (50)":
                tickers_list = get_dev_test_scan_items()
                st.caption(f"Dev Test Scan: {len(tickers_list)} curated high-volatility tickers.")
            elif universe_mode == "Discovery Universe":
                tickers_list = get_discovery_universe_items()
                st.caption(f"Discovery Universe: {len(tickers_list)} curated growth/volatility tickers.")
            elif universe_mode == "Advanced / Custom List":
                with st.expander("Custom Ticker Input", expanded=True):
                    selected_preset = st.selectbox("Preset:", options=list(PRESETS.keys()), index=0)
                    preset_val = PRESETS[selected_preset]
                    manual_tickers = st.text_area(
                        "Tickers:",
                        value=preset_val if selected_preset != "Custom List (Manual / Upload)" else "PLTR, GME",
                        height=80
                    )
                    uploaded_file = st.file_uploader("Or Upload CSV:", type=["csv"])
                    if uploaded_file is not None:
                        tickers_list = extract_tickers_from_csv(uploaded_file)
                    else:
                        tickers_list = parse_tickers_input(manual_tickers)
            else:
                hc = st.session_state.get('health_check')
                if hc and hc.get('yfinance_price', {}).get('ok'):
                    tickers_list = get_market_universe_tickers()
                    if not tickers_list:
                        st.warning("No local universe found. Click 'Refresh Market Universe' under Advanced.")
                else:
                    st.caption("Price connectivity check recommended before full market scan.")
                    tickers_list = get_market_universe_tickers()

            fast_scan_full_market = False
            fast_scan_limit_text = "250"
            fast_scan_is_full_market = True
            fast_scan_limit_n = None
            fast_scan_limit_label = "Full Market"
            fast_scan_limit_error = None

            if universe_mode == "Full Market Scan":
                fast_scan_full_market = st.checkbox(
                    "Full market scan (no symbol limit)",
                    value=st.session_state.get("fast_scan_full_market", True),
                    help="Scan every symbol in universe CSV. Uncheck to set max count.",
                )
                st.session_state.fast_scan_full_market = fast_scan_full_market
                fast_scan_limit_text = st.text_input(
                    "Fast Scan Limit (max symbols)",
                    value=st.session_state.get("fast_scan_limit_text", "250"),
                    disabled=fast_scan_full_market,
                )
                st.session_state.fast_scan_limit_text = fast_scan_limit_text
                fast_scan_is_full_market, fast_scan_limit_n, fast_scan_limit_label, fast_scan_limit_error = (
                    parse_fast_scan_limit(fast_scan_limit_text, fast_scan_full_market)
                )
                if fast_scan_limit_error:
                    st.warning(fast_scan_limit_error)

            effective_scan_count = len(tickers_list)
            if (
                universe_mode == "Full Market Scan"
                and not fast_scan_is_full_market
                and fast_scan_limit_n
                and tickers_list
                and not fast_scan_limit_error
            ):
                effective_scan_count = min(len(tickers_list), fast_scan_limit_n)

            future_catalysts_only = st.checkbox(
                "Future Catalysts Only", value=True,
                help="Exclude stocks with no upcoming catalyst, past earnings, or earnings > 30 days away."
            )
            diagnostics_mode = st.checkbox(
                "Diagnostics Mode", value=False,
                help="Bypass pre-filters — shows raw data diagnostics for all stocks."
            )

            st.caption(f"Target Universe: {effective_scan_count:,} symbols")

            # ------- Scan Execution -------
            st.markdown("---")
            st.markdown("### Scan Execution")
            run_fast_scan = st.button("Run Fast Market Scan", width='stretch', disabled=(len(tickers_list) == 0))

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                if st.button("Stop Scan", width='stretch'):
                    st.session_state.stop_scan = True
                    st.warning("Scan termination requested.")
            with col_s2:
                if st.button("Reset Scanner", width='stretch'):
                    st.session_state.screener_results = None
                    st.session_state.fast_scan_candidates = []
                    st.session_state.scan_stats = {}
                    st.session_state.stop_scan = False
                    st.session_state.stage4_failures = {}
                    st.session_state.deep_scan_tickers = []
                    st.session_state.deep_scan_snapshot = {}
                    st.session_state.funnel_metrics = {}
                    st.session_state.universe_build_stats = {}
                    init_deep_scan_session_state(force_reset=True)
                    safe_rerun()

            # ------- Deep Scan Queue Controls (When Active) -------
            _deep_loaded = st.session_state.get('deep_scan_loaded', False)
            _deep_pending = st.session_state.get('deep_scan_pending_tickers', [])
            _deep_failed = st.session_state.get('deep_scan_failed_tickers', [])
            _deep_cumul = st.session_state.get('deep_scan_cumulative_results_df', pd.DataFrame())
            _deep_has_results = not _deep_cumul.empty

            if _deep_loaded:
                st.markdown("---")
                st.markdown("### Deep Scan Queue")
                st.caption(f"{len(_deep_pending):,} pending · {len(st.session_state.get('deep_scan_completed_tickers', [])):,} scored")

                if st.button("Run Next Deep Scan Batch", width='stretch', disabled=not _deep_pending):
                    st.session_state.deep_scan_run_all = False
                    batch_size = st.session_state.get('deep_scan_batch_size', 100)
                    batch = _deep_pending[:batch_size]
                    st.session_state.deep_scan_pending_tickers = _deep_pending[batch_size:]
                    if batch:
                        with st.spinner(f"Deep scanning batch of {len(batch)} tickers..."):
                            result = process_single_deep_scan_batch(
                                batch, finnhub_api_key, diagnostics_mode,
                                apply_concurrency_telemetry()
                            )
                            _merge_batch_results(result)
                    safe_rerun()

                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    if st.button("Run All Batches", width='stretch', disabled=not _deep_pending):
                        st.session_state.deep_scan_run_all = True
                        st.session_state.deep_scan_pause = False
                        safe_rerun()
                with col_d2:
                    if st.button("Pause Scan", width='stretch', disabled=not st.session_state.get('deep_scan_run_all', False)):
                        st.session_state.deep_scan_pause = True
                        st.session_state.deep_scan_run_all = False
                        safe_rerun()

                if st.button("Build Final Leaderboard", width='stretch', disabled=not _deep_has_results):
                    df = _deep_cumul.sort_values('Final Score', ascending=False).reset_index(drop=True)
                    st.session_state.screener_results = df
                    st.session_state.metadata.update(st.session_state.get('deep_scan_cumulative_meta', {}))
                    st.session_state.raw_history.update(st.session_state.get('deep_scan_cumulative_history', {}))
                    st.session_state.stage4_failures = st.session_state.get('deep_scan_cumulative_failures', {})
                    st.session_state.deep_scan_tickers = st.session_state.get('deep_scan_completed_tickers', [])
                    safe_rerun()

                if _deep_failed:
                    if st.button("Retry Failed Tickers", width='stretch'):
                        failed_tickers = [f['ticker'] for f in _deep_failed]
                        candidates_map = {c['ticker']: c for c in st.session_state.get('deep_scan_full_candidate_list', [])}
                        retry_candidates = [candidates_map[t] for t in failed_tickers if t in candidates_map]
                        st.session_state.deep_scan_pending_tickers = list(_deep_pending) + retry_candidates
                        st.session_state.deep_scan_failed_tickers = []
                        safe_rerun()

                if st.button("Reset Deep Scan Progress", width='stretch'):
                    init_deep_scan_session_state(force_reset=True)
                    safe_rerun()

            # ------- Collapsed Advanced Configuration -------
            st.markdown("---")
            with st.expander("Advanced Configuration", expanded=False):
                st.markdown("#### API Configuration")
                finnhub_api_key = st.text_input(
                    "Finnhub API Key (Optional)", type="password",
                    help="Improves catalyst discovery via finnhub.io. Leave blank for free YFinance/SEC data."
                )
                if not finnhub_api_key:
                    st.caption("Future earnings coverage is limited without Finnhub.")

                st.markdown("#### Concurrency")
                _prev_workers = st.session_state.get(
                    "max_concurrent_api_workers", DEFAULT_MAX_CONCURRENT_API_WORKERS
                )
                _worker_idx = (
                    API_WORKER_OPTIONS.index(_prev_workers)
                    if _prev_workers in API_WORKER_OPTIONS
                    else API_WORKER_OPTIONS.index(DEFAULT_MAX_CONCURRENT_API_WORKERS)
                )
                max_concurrent_api_workers = st.selectbox(
                    "Max Concurrent API Workers",
                    options=list(API_WORKER_OPTIONS),
                    index=_worker_idx,
                    help=(
                        "Thread pool size for fundamentals, earnings, and SEC during deep scan. "
                        f"Fast scan uses {FAST_SCAN_MAX_WORKERS} worker (one yfinance batch at a time)."
                    ),
                )
                st.session_state.max_concurrent_api_workers = max_concurrent_api_workers
                apply_concurrency_telemetry(max_concurrent_api_workers)

                st.markdown("#### Batch Settings")
                st.session_state.deep_scan_batch_size = st.selectbox(
                    "Deep Scan Batch Size",
                    options=[100, 250, 500, 750],
                    index=0,
                    help="Number of tickers to process in each deep scan batch."
                )
                st.session_state.deep_scan_cooldown = st.selectbox(
                    "Cooldown Between Batches",
                    options=[("30 seconds", 30), ("60 seconds", 60), ("2 minutes", 120), ("5 minutes", 300)],
                    format_func=lambda x: x[0],
                    index=0,
                    help="Time to wait between deep scan batches."
                )[1]

                deep_scan_all_eligible = st.checkbox(
                    "Deep scan all eligible candidates",
                    value=st.session_state.get("deep_scan_all_eligible", True),
                    help="When enabled, every Stage 3 survivor is deep-scanned (no Max Deep Scan cap).",
                )
                st.session_state.deep_scan_all_eligible = deep_scan_all_eligible

                if not deep_scan_all_eligible:
                    max_deep_scan = st.number_input(
                        "Max Deep Scan Candidates:",
                        min_value=50,
                        max_value=1000,
                        value=int(st.session_state.get("max_deep_scan_cap_value", 300)),
                        step=50,
                    )
                else:
                    max_deep_scan = int(st.session_state.get("max_deep_scan_cap_value", 300))
                st.session_state.max_deep_scan_cap_value = int(max_deep_scan)

                if st.button("Refresh Market Universe", width='stretch'):
                    with st.spinner("Downloading live symbol list from Nasdaq + SEC..."):
                        symbols, msg, universe_stats = refresh_market_universe()
                        if symbols:
                            st.session_state.universe_build_stats = universe_stats
                            st.success(msg)
                        else:
                            st.error(msg)

                st.markdown("#### Data Connectivity")
                if st.button("Run Health Check", width='stretch'):
                    with st.spinner("Probing data sources..."):
                        hc = run_health_check(finnhub_api_key or None)
                        st.session_state.health_check = hc

                hc = st.session_state.get('health_check')
                if hc:
                    def _hc_icon(v):
                        if v is True:  return "OK"
                        if v is False: return "FAIL"
                        return "WARN"

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
                        status_color = "#4FAE7B" if v.get('ok') is True else ("#D86666" if v.get('ok') is False else "#C99A52")
                        rows += f"<tr><td style='color:{status_color};font-weight:600;'>{icon}</td><td>{label}</td><td style='color:#9CA3AF;font-size:0.75rem'>{v.get('detail','')}</td></tr>"
                    st.markdown(
                        f"<table style='width:100%;border-collapse:collapse;font-size:0.8rem;margin-top:6px;'>{rows}</table>",
                        unsafe_allow_html=True
                    )

    # --- Run All Batches: auto-processing loop with cooldown ---
    _ra_run_all = st.session_state.get('deep_scan_run_all', False)
    _ra_pause = st.session_state.get('deep_scan_pause', False)
    _ra_loaded = st.session_state.get('deep_scan_loaded', False)
    _ra_pending = st.session_state.get('deep_scan_pending_tickers', [])

    if _ra_run_all and not _ra_pause and _ra_loaded and _ra_pending:
        _ra_cooldown_until = st.session_state.get('deep_scan_cooldown_until')
        _ra_now = time.time()

        if _ra_cooldown_until and _ra_now < _ra_cooldown_until:
            _ra_remaining = _ra_cooldown_until - _ra_now
            st.toast(f"⏳ Cooldown: {_ra_remaining:.0f}s remaining before next batch...")
            time.sleep(min(_ra_remaining, 1))
            st.rerun()
        else:
            _ra_batch_size = st.session_state.get('deep_scan_batch_size', 100)
            _ra_batch = _ra_pending[:_ra_batch_size]
            st.session_state.deep_scan_pending_tickers = _ra_pending[_ra_batch_size:]

            if _ra_batch:
                with st.spinner(f"Auto-processing batch of {len(_ra_batch)} tickers..."):
                    _ra_result = process_single_deep_scan_batch(
                        _ra_batch, finnhub_api_key, diagnostics_mode,
                        apply_concurrency_telemetry()
                    )
                    _merge_batch_results(_ra_result)

            _ra_cooldown = st.session_state.get('deep_scan_cooldown', 30)
            st.session_state.deep_scan_cooldown_until = time.time() + _ra_cooldown

            _ra_still_pending = st.session_state.get('deep_scan_pending_tickers', [])
            if _ra_still_pending and not st.session_state.get('deep_scan_pause', False):
                st.rerun()
            else:
                st.session_state.deep_scan_run_all = False
                st.rerun()

    if run_fast_scan:
        if not tickers_list:
            st.error("No tickers to scan.")
        elif universe_mode == "Full Market Scan" and fast_scan_limit_error:
            st.error(fast_scan_limit_error)
        else:
            st.session_state.stop_scan = False
            st.session_state.screener_results = None
            st.session_state.fast_scan_candidates = []

            init_api_telemetry(force_reset=True) # Reset telemetry for a new scan

            # --- STAGE 0: Raw Universe Tickers ---
            raw_universe_loaded, after_security_count = resolve_universe_funnel_counts(
                universe_mode, tickers_list
            )
            stage0_tickers = tickers_list.copy()
            fast_scan_limit_applied = False
            if (
                universe_mode == "Full Market Scan"
                and not fast_scan_is_full_market
                and fast_scan_limit_n
                and len(stage0_tickers) > fast_scan_limit_n
            ):
                fast_scan_limit_applied = True
                st.info(
                    f"Fast Scan Limit active: scanning {fast_scan_limit_n:,} of {len(tickers_list):,} "
                    "universe symbols (before liquidity filtering)."
                )
                stage0_tickers = stage0_tickers[:fast_scan_limit_n]

            universe_note = None
            if universe_mode == "🚀 Discovery Universe":
                universe_note = (
                    f"Discovery mode: {len(tickers_list):,} curated symbols (no list-size cap)."
                )
            merge_funnel_metrics({
                'raw_universe_loaded': raw_universe_loaded,
                'after_security_filter_count': after_security_count,
                'after_fast_scan_limit_count': len(stage0_tickers),
                'fast_scan_limit_label': fast_scan_limit_label,
                'fast_scan_limit_value': fast_scan_limit_n,
                'fast_scan_limit_applied_before_liquidity': True,
                'fast_scan_limit_was_applied': fast_scan_limit_applied,
                'universe_mode_note': universe_note,
            })

            total_tickers = len(stage0_tickers)
            st.info(f"Initiating Fast Market Scan for {total_tickers:,} symbols (Price/Volume only)...")
            progress_bar = st.progress(0)
            status_text = st.empty()
                
            # --- STAGE 1: Fast Price/Volume Scan ---
            stage1_survivors = []
            price_volume_eligible_count = 0
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
                apply_concurrency_telemetry()
                with concurrent.futures.ThreadPoolExecutor(max_workers=FAST_SCAN_MAX_WORKERS) as executor:
                    try:
                        future = executor.submit(fetch_cached_price_volume_30m, tuple(batch_tickers))
                    except Exception as e:
                        if is_thread_pool_failure(e):
                            record_thread_pool_telemetry_failure()
                        raise
                    try:
                        hist_data = future.result(timeout=15.0)  # 15 seconds batch timeout
                        consecutive_failures = 0
                    except concurrent.futures.TimeoutError:
                        tickers_failed += len(batch_tickers)
                        consecutive_failures += 1
                    except Exception as e:
                        if is_thread_pool_failure(e):
                            record_thread_pool_telemetry_failure()
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
                                price_volume_eligible_count += 1
                                current_price = float(closes.iloc[-1])
                                avg_vol_20d = float(volumes.tail(20).mean())
                                current_volume = float(volumes.iloc[-1]) if len(volumes) > 0 else 0.0
                                rvol = float(current_volume / avg_vol_20d) if avg_vol_20d > 0 else 1.0
                                
                                prev_close = float(closes.iloc[-2]) if len(closes) > 1 else current_price
                                change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
                                
                                if diagnostics_mode or (
                                    current_price > LIQUIDITY_MIN_PRICE and avg_vol_20d > LIQUIDITY_MIN_AVG_VOL
                                ):
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
                stage1_survivors.sort(key=lambda s: (s['rvol'] * 50) + abs(s['change_pct']), reverse=True)
                st.session_state.fast_scan_candidates = stage1_survivors
                merge_funnel_metrics({
                    'after_price_volume_eligibility_count': price_volume_eligible_count,
                    'after_liquidity_filter_count': len(stage1_survivors),
                    'after_fast_scan_ranking_count': len(stage1_survivors),
                    'after_fast_scan_candidates_count': len(stage1_survivors),
                })
                st.success(
                    f"⚡ Step 1 Fast Scan complete! {len(stage1_survivors):,} passed liquidity — "
                    f"all are available in Step 2 for deep scan."
                )
            else:
                merge_funnel_metrics({
                    'after_price_volume_eligibility_count': price_volume_eligible_count,
                    'after_liquidity_filter_count': 0,
                    'after_fast_scan_ranking_count': 0,
                    'after_fast_scan_candidates_count': 0,
                })
                st.warning("⚠️ No stocks passed the fast liquidity filters.")

    # ----------------------------------------------------
    # DISPLAY SCANNER RESULT
    # ----------------------------------------------------
    results_df = st.session_state.screener_results
    
    if results_df is not None and not results_df.empty:
        # Dynamic re-weighting of Final Score based on active Strategy
        if score_column in results_df.columns and 'Prediction Score' in results_df.columns:
            results_df['Opportunity Score'] = results_df[score_column]
            results_df['Final Score'] = (0.6 * results_df['Opportunity Score'] + 0.4 * results_df['Prediction Score']).round(1)
        results_df['Composite Score'] = results_df['Final Score']

        # Pre-Market Live Filters
        if is_morning_mode:
            if filter_ticker:
                t_match = results_df['Ticker'].astype(str).str.contains(filter_ticker, case=False, na=False)
                c_match = results_df['Company Name'].astype(str).str.contains(filter_ticker, case=False, na=False) if 'Company Name' in results_df.columns else False
                results_df = results_df[t_match | c_match].copy()
            if filter_rvol > 0.0 and 'RVOL' in results_df.columns:
                results_df = results_df[results_df['RVOL'] >= filter_rvol].copy()
            if filter_days < 60 and 'Days Until Earnings' in results_df.columns:
                results_df = results_df[
                    (pd.isnull(results_df['Days Until Earnings'])) |
                    (results_df['Days Until Earnings'] <= filter_days)
                ].copy()

        # Capture raw data for Diagnostics before any filtering
        raw_df = results_df.copy()

        # Apply base eligibility filter (DPS >= 60) when not in diagnostics mode
        if not diagnostics_mode:
            results_df = results_df[results_df['Directional Probability Score'] >= 60.0].copy()

        df_exclusions = build_leaderboard_exclusions(
            st.session_state.get('deep_scan_tickers', []),
            st.session_state.get('stage4_failures', {}),
            raw_df,
            deep_scan_snapshot=st.session_state.get('deep_scan_snapshot', {}),
            future_catalysts_only=future_catalysts_only,
            diagnostics_mode=diagnostics_mode,
            top_n=30,
            max_display=50,
        )
        
        scored_future_catalyst_count = count_future_catalyst_survivors(raw_df)
        # Apply Future Catalysts Filter if checked and NOT in diagnostics mode
        if future_catalysts_only and not diagnostics_mode:
            results_df = results_df[
                (pd.notnull(results_df['Days Until Earnings'])) & 
                (results_df['Days Until Earnings'] >= 0) & 
                (results_df['Days Until Earnings'] <= 30)
            ].copy()
            if results_df.empty:
                st.warning("No stocks found matching the 'Future Catalysts Only' criteria.")
            merge_funnel_metrics({
                'future_catalyst_only_count': len(results_df),
                'future_catalyst_scored_pool_count': scored_future_catalyst_count,
            })
        else:
            merge_funnel_metrics({
                'future_catalyst_only_count': scored_future_catalyst_count,
                'future_catalyst_scored_pool_count': scored_future_catalyst_count,
            })
        
        results_df = results_df.sort_values(by='Final Score', ascending=False).reset_index(drop=True)
        
        # Compute summary metrics across the scanned active universe
        universe_size = len(results_df)

        if 'Market Cap' in results_df.columns and not results_df['Market Cap'].dropna().empty:
            mcap_val = results_df['Market Cap'].dropna().mean()
            if pd.notnull(mcap_val) and mcap_val > 0:
                avg_mcap_str = f"${mcap_val/1e9:.1f}B" if mcap_val >= 1e9 else f"${mcap_val/1e6:.1f}M"
            else:
                avg_mcap_str = "—"
        else:
            avg_mcap_str = "—"

        if 'Short Percent' in results_df.columns and not results_df['Short Percent'].dropna().empty:
            si_val = results_df['Short Percent'].dropna().mean()
            avg_si_str = f"{si_val*100:.1f}%" if pd.notnull(si_val) and not pd.isna(si_val) else "—"
        else:
            avg_si_str = "—"

        if 'Avg Earnings Reaction (%)' in results_df.columns and not results_df['Avg Earnings Reaction (%)'].dropna().empty:
            move_val = results_df['Avg Earnings Reaction (%)'].dropna().mean()
            avg_move_str = f"±{move_val:.1f}%" if pd.notnull(move_val) and not pd.isna(move_val) else "—"
        else:
            avg_move_str = "—"

        if diagnostics_mode:
            st.caption("Diagnostics Mode: Pre-filtering and catalyst exclusions bypassed.")

        if is_morning_mode:
            mod_label = st.session_state.get('morning_scan_mod_time').strftime('%b %d, %Y at %I:%M %p %Z') if st.session_state.get('morning_scan_mod_time') else "Latest"
            selected_uni_label = pre_universe_choice if 'pre_universe_choice' in locals() else "Discovery Pool"
            source_file = st.session_state.get('morning_scan_source_file', '')
            is_fallback = pre_universe_name not in source_file and "latest.p" in source_file if 'pre_universe_name' in locals() and pre_universe_name != 'discovery' else False
            status_tag = f"&middot; <span style='color: #E5A93C;'>Pending Cron Sync (Showing Discovery Snapshot)</span>" if is_fallback else ""

            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding: 9px 14px; background-color: #15181E; border: 1px solid #2A2F38; border-radius: 4px;">
                <div style="font-size: 12px; color: #9CA3AF;">
                    <strong style="color: #5B8DEF; text-transform: uppercase; letter-spacing: 0.05em;">Pre-Market &bull; {selected_uni_label}</strong> &middot; Snapshot: {mod_label} &middot; {len(raw_df)} Scored Candidates {status_tag}
                </div>
                <div style="font-size: 11px; color: #4FAE7B; font-weight: 600;">
                    &bull; Production Rate-Limit Protected
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            render_true_funnel_metrics(st.session_state.get('funnel_metrics', {}), df_exclusions)
            render_api_telemetry_panel(st.session_state.api_telemetry)

        # Flat inline summary strip
        st.markdown(f"""
        <div class="summary-strip">
            <div class="summary-item">
                <span class="summary-label">Scored Universe</span>
                <span class="summary-value">{universe_size:,}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Avg Market Cap</span>
                <span class="summary-value">{avg_mcap_str}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Avg Short Interest</span>
                <span class="summary-value">{avg_si_str}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Avg Historical Move</span>
                <span class="summary-value">{avg_move_str}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Main Universe Split Dashboard (Tabs)
        df_strict_conviction = results_df[
            (pd.notnull(results_df['Days Until Earnings'])) & 
            (results_df['Days Until Earnings'] >= 0) & 
            (results_df['Days Until Earnings'] <= 14) &
            (results_df['Directional Probability Score'] >= 60.0) &
            (results_df['Data Confidence'].isin(['Medium', 'High']))
        ].sort_values(by='Final Score', ascending=False).reset_index(drop=True)

        df_earnings_watchlist = raw_df[
            (pd.notnull(raw_df['Days Until Earnings'])) &
            (raw_df['Days Until Earnings'] >= 0) &
            (raw_df['Days Until Earnings'] <= 14)
        ].sort_values(by='Final Score', ascending=False).reset_index(drop=True)

        df_catalyst_watchlist = raw_df[
            (
                (
                    (pd.notnull(raw_df['Days Until Earnings'])) &
                    (raw_df['Days Until Earnings'] >= 0) &
                    (raw_df['Days Until Earnings'] <= 30)
                ) |
                (raw_df['RVOL'].fillna(0) > 1.5) |
                (raw_df['Short Percent'].fillna(0) > 0.10)
            )
        ].sort_values(by='Final Score', ascending=False).reset_index(drop=True)

        df_leaderboard = results_df.sort_values(by='Final Score', ascending=False).head(30).reset_index(drop=True)
        df_core = results_df[results_df['Universe'] == 'Core Opportunity'].sort_values(by='Final Score', ascending=False).head(20).copy()
        df_spec = results_df[results_df['Universe'] == 'Speculative'].sort_values(by='Final Score', ascending=False).head(20).copy()
        df_large = results_df[results_df['Universe'] == 'Large Cap'].sort_values(by='Final Score', ascending=False).head(20).copy()
        
        tab_strict, tab_earnings_watch, tab_catalyst_watch, tab_leader, tab_exclusions, tab_core, tab_spec, tab_large, tab_diag = st.tabs([
            "Conviction",
            "Upcoming Earnings",
            "Catalysts",
            "Rankings",
            "Exclusions",
            "Core ($300M - $10B)",
            "Speculative ($50M - $300M)",
            "Large Cap (> $10B)",
            "Diagnostics"
        ])
        
        def prepare_display_df(df_input):
            if df_input.empty:
                return df_input
            disp = df_input.copy()
            if 'Company Name' in disp.columns:
                disp['Company Name'] = disp['Company Name'].fillna("—")
            elif 'company_name' in disp.columns:
                disp['Company Name'] = disp['company_name'].fillna("—")
            else:
                disp['Company Name'] = "—"

            disp['Price'] = disp['Price'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) and not pd.isna(x) else "—")
            disp['RVOL'] = disp['RVOL'].apply(lambda x: f"{x:.2f}x" if pd.notnull(x) and not pd.isna(x) else "—")
            disp['Short Interest'] = disp['Short Percent'].apply(lambda x: f"{x*100:,.1f}%" if pd.notnull(x) and not pd.isna(x) else "—")
            disp['Days Until'] = disp['Days Until Earnings'].apply(lambda x: f"{int(x)}d" if pd.notnull(x) and not pd.isna(x) else "—")
            disp['Days Since'] = disp['Days Since Earnings'].apply(lambda x: f"{int(x)}d" if pd.notnull(x) and not pd.isna(x) else "—")
            disp['Historical Earnings Move'] = disp['Avg Earnings Reaction (%)'].apply(lambda x: f"±{x:.1f}%" if pd.notnull(x) and not pd.isna(x) else "—")
            disp['Float'] = disp['Float Shares'].apply(lambda x: f"{x/1e6:.1f}M" if pd.notnull(x) and not pd.isna(x) and x > 1e6 else (f"{x:,.0f}" if pd.notnull(x) and not pd.isna(x) else "—"))
            return disp

        columns_display = [
            'Ticker', 'Company Name', 'Price', 'Final Score', 'Research Priority Score',
            'Days Until', 'Short Interest', 'Historical Earnings Move', 'RVOL',
            'Directional Edge Score V1', 'Directional Probability Score', 'Directional Bias', 'Directional Archetype',
            'Is Elite', 'Recommended Position Size',
            'Exit Recommendation', 'Exit Hold Days', 'Exit Rationale',
            'Opportunity Score', 'Prediction Score',
            'Event Potential Score', 'Expectation Setup Score', 'Run-Up Risk Score',
            'Cash Flow Quality Score', 'Guidance Sensitivity Score', 'Short Squeeze Quality Score',
            'Research Tags', 'Why This Stock Ranked', 'Float', 'Data Confidence'
        ]
        columns_display_catalyst = [
            'Ticker', 'Company Name', 'Price', 'Final Score', 'Research Priority Score',
            'Days Until', 'Short Interest', 'Historical Earnings Move', 'RVOL',
            'Future Catalyst Score',
            'Directional Edge Score V1', 'Directional Probability Score', 'Directional Bias', 'Directional Archetype',
            'Is Elite', 'Recommended Position Size',
            'Exit Recommendation', 'Exit Hold Days', 'Exit Rationale',
            'Opportunity Score', 'Prediction Score',
            'Event Potential Score', 'Expectation Setup Score', 'Run-Up Risk Score',
            'Cash Flow Quality Score', 'Guidance Sensitivity Score', 'Short Squeeze Quality Score',
            'Research Tags', 'Why This Stock Ranked', 'Float', 'Data Confidence'
        ]

        def render_universe_table(df_universe, show_future_catalyst=False, table_key="tbl"):
            if df_universe.empty:
                st.info("No tickers passed the criteria for this universe.")
                return
            display_df = prepare_display_df(df_universe)
            cols = [c for c in (columns_display_catalyst if show_future_catalyst else columns_display) if c in display_df.columns]
            column_config = {
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Company Name": st.column_config.TextColumn("Company"),
                "Price": st.column_config.TextColumn("Price"),
                "Final Score": st.column_config.NumberColumn("Score", format="%.1f"),
                "Research Priority Score": st.column_config.NumberColumn("Priority", format="%.1f"),
                "Days Until": st.column_config.TextColumn("Earnings"),
                "Short Interest": st.column_config.TextColumn("Short Int."),
                "Historical Earnings Move": st.column_config.TextColumn("Avg Move"),
                "RVOL": st.column_config.TextColumn("RVOL"),
                "Future Catalyst Score": st.column_config.NumberColumn("Catalyst", format="%.1f"),
                "Directional Edge Score V1": st.column_config.NumberColumn(
                    "Dir. Edge V1",
                    format="%.1f",
                    help="Standalone research overlay — does NOT affect Final Score.",
                ),
                "Directional Probability Score": st.column_config.NumberColumn(
                    "Dir. Prob",
                    format="%.1f",
                ),
                "Directional Bias": st.column_config.TextColumn("Bias"),
                "Directional Archetype": st.column_config.TextColumn("Archetype"),
                "Is Elite": st.column_config.TextColumn("Elite"),
                "Recommended Position Size": st.column_config.TextColumn("Rec. Size"),
                "Exit Recommendation": st.column_config.TextColumn("Exit Rec."),
                "Exit Hold Days": st.column_config.NumberColumn("Hold Days", format="%d"),
                "Exit Rationale": st.column_config.TextColumn("Exit Rationale"),
                "Opportunity Score": st.column_config.NumberColumn("Opp.", format="%.1f"),
                "Prediction Score": st.column_config.NumberColumn("Pred.", format="%.1f"),
                "Event Potential Score": st.column_config.NumberColumn("Event Pot.", format="%.1f"),
                "Expectation Setup Score": st.column_config.NumberColumn("Expectation", format="%.1f"),
                "Run-Up Risk Score": st.column_config.NumberColumn("Run-Up Risk", format="%.1f"),
                "Cash Flow Quality Score": st.column_config.NumberColumn("Cash Flow", format="%.1f"),
                "Guidance Sensitivity Score": st.column_config.NumberColumn("Guidance", format="%.1f"),
                "Short Squeeze Quality Score": st.column_config.NumberColumn("Squeeze", format="%.1f"),
                "Research Tags": st.column_config.TextColumn("Tags"),
                "Why This Stock Ranked": st.column_config.TextColumn("Catalyst Insight"),
                "Float": st.column_config.TextColumn("Float"),
                "Data Confidence": st.column_config.TextColumn("Confidence"),
            }
            selected_rows = st.dataframe(
                display_df[cols],
                column_config=column_config,
                hide_index=True,
                width='stretch',
                key=f"df_{table_key}",
                on_select="rerun",
                selection_mode="single-row"
            )
            if selected_rows and hasattr(selected_rows, 'selection') and selected_rows.selection and selected_rows.selection.rows:
                sel_idx = selected_rows.selection.rows[0]
                if sel_idx < len(display_df):
                    sel_row = display_df.iloc[sel_idx]
                    if 'Ticker' in sel_row and pd.notnull(sel_row['Ticker']):
                        st.session_state.active_selected_ticker = str(sel_row['Ticker']).strip()

        with tab_strict:
            st.markdown("#### Conviction Setups")
            st.caption("Earnings within 14 days, Opportunity > 70, Prediction > 60, Medium/High confidence.")
            render_universe_table(df_strict_conviction, table_key="strict")

        with tab_earnings_watch:
            st.markdown("#### Upcoming Earnings")
            st.caption("Earnings within the next 14 days, sorted by Final Score.")
            render_universe_table(df_earnings_watchlist, show_future_catalyst=True, table_key="earnings")

        with tab_catalyst_watch:
            st.markdown("#### Catalysts")
            st.caption("Earnings within 30 days, RVOL > 1.5x, or short interest > 10%.")
            render_universe_table(df_catalyst_watchlist, show_future_catalyst=True, table_key="catalyst")

        with tab_leader:
            st.markdown("#### Rankings (Top 30)")
            st.caption("Ranked by Final Score (60% Opportunity / 40% Prediction).")
            render_universe_table(df_leaderboard, show_future_catalyst=True, table_key="leader")

        with tab_exclusions:
            st.markdown("#### Exclusions")
            st.caption("Stage 4 deep-scan candidates that did not make the top rankings.")
            if df_exclusions.empty:
                st.info("No exclusions to display.")
            else:
                excl_disp = df_exclusions.copy()
                for c in ['opportunity_score', 'prediction_score', 'final_score', 'future_catalyst_score']:
                    if c in excl_disp.columns:
                        excl_disp[c] = excl_disp[c].apply(lambda x: f"{x:.1f}" if pd.notnull(x) and not pd.isna(x) else "—")
                if 'days_until_earnings' in excl_disp.columns:
                    excl_disp['Days Until Earnings'] = excl_disp['days_until_earnings'].apply(lambda x: f"{int(x)}d" if pd.notnull(x) and not pd.isna(x) else "—")
                excl_disp = excl_disp.rename(columns={
                    'ticker': 'Ticker',
                    'failed_reason': 'Failed Reason',
                    'opportunity_score': 'Opportunity Score',
                    'prediction_score': 'Prediction Score',
                    'final_score': 'Final Score',
                    'future_catalyst_score': 'Future Catalyst Score',
                    'data_confidence': 'Data Confidence'
                })
                excl_cols = [c for c in ['Ticker', 'Final Score', 'Opportunity Score', 'Prediction Score', 'Future Catalyst Score', 'Days Until Earnings', 'Data Confidence', 'Failed Reason'] if c in excl_disp.columns]
                st.dataframe(excl_disp[excl_cols], hide_index=True, width='stretch', key="df_exclusions")

        with tab_core:
            st.markdown("#### Core Opportunities ($300M - $10B)")
            render_universe_table(df_core, table_key="core")

        with tab_spec:
            st.caption("Microcap stocks ($50M - $300M). Elevated volatility universe.")
            render_universe_table(df_spec, table_key="spec")

        with tab_large:
            st.caption("Large-cap stocks (> $10B). Scaling penalties applied to event metrics.")
            render_universe_table(df_large, table_key="large")

        with tab_diag:
            st.markdown("#### Earnings Diagnostics")
            st.caption("Raw data coverage and date parsing diagnostics across all active universe tickers.")

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

            col_diag1, col_diag2, col_diag3, col_diag4 = st.columns(4)
            with col_diag1:
                st.metric("Total Processed", f"{total_scanned:,}")
            with col_diag2:
                st.metric("Future Dates", f"{valid_future:,}")
            with col_diag3:
                st.metric("Missing Dates", f"{missing_dates:,}")
            with col_diag4:
                st.metric("Past Dates", f"{past_dates:,}")

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

            st.markdown("#### Future Catalyst Windows")
            col_w7, col_w14, col_w30 = st.columns(3)
            with col_w7:
                st.metric("Within 7 Days", f"{within_7} stocks")
            with col_w14:
                st.metric("Within 14 Days", f"{within_14} stocks")
            with col_w30:
                st.metric("Within 30 Days", f"{within_30} stocks")

            st.markdown("#### Raw Source Data")

            def compute_source_status(row):
                cal_status = row.get('Calendar Status', 'Not Fetched')
                hist_status = row.get('Earnings Dates Status', 'Not Fetched')
                next_ed = row.get('Next Earnings Date')
                days_until = row.get('Days Until Earnings')
                price_status = row.get('Price Data Status', 'Valid')

                status_parts = []
                if price_status != 'Valid':
                    status_parts.append(f"Price: {price_status}")

                if pd.isnull(next_ed):
                    status_parts.append(f"Missing (Cal: {cal_status} | Hist: {hist_status})")
                elif days_until is not None and days_until < 0:
                    status_parts.append(f"Past (Cal: {cal_status} | Hist: {hist_status})")
                else:
                    status_parts.append(f"Valid Future (Cal: {cal_status} | Hist: {hist_status})")

                return " | ".join(status_parts)

            diag_df = raw_df.copy()
            diag_df['Data Source Status'] = diag_df.apply(compute_source_status, axis=1)

            diag_df['Next Earnings Date Raw'] = diag_df['Next Earnings Date'].apply(
                lambda d: d.strftime("%Y-%m-%d") if isinstance(d, (datetime.date, datetime.datetime)) else str(d) if pd.notnull(d) else "—"
            )
            diag_df['Days Until'] = diag_df['Days Until Earnings'].apply(
                lambda x: f"{int(x)}d" if pd.notnull(x) else "—"
            )

            diag_display = diag_df[['Ticker', 'Next Earnings Date Raw', 'Days Until', 'Data Source Status']].copy()
            diag_display.columns = ['Ticker', 'Next Earnings Date', 'Days Until Earnings', 'Data Source Status']

            st.dataframe(
                diag_display,
                hide_index=True,
                width='stretch',
                key="df_diagnostics"
            )

        # Drill-down Panel Layout
        st.markdown("---")

        dossier_options = results_df['Ticker'].head(60).tolist()
        default_idx = 0
        active_t = st.session_state.get('active_selected_ticker')
        if active_t in dossier_options:
            default_idx = dossier_options.index(active_t)

        st.markdown("### Research Dossier")
        selected_ticker = st.selectbox(
            "Select Ticker:",
            options=dossier_options,
            index=default_idx,
            key="dossier_ticker_select"
        )

        if selected_ticker:
            st.session_state.active_selected_ticker = selected_ticker
            ticker_row = results_df[results_df['Ticker'] == selected_ticker].iloc[0]
            ticker_meta = st.session_state.metadata.get(selected_ticker, {})

            # On-demand OHLCV fetch if missing
            if selected_ticker not in st.session_state.raw_history:
                try:
                    with st.spinner(f"Loading market data for {selected_ticker}..."):
                        _fetched = fetch_historical_data([selected_ticker], period="6mo")
                        if _fetched:
                            st.session_state.raw_history.update(_fetched)
                except Exception:
                    pass

            col_chart, col_drill = st.columns([13, 7])

            with col_drill:
                st.markdown(f"#### Universe: **{ticker_row.get('Universe', '—')}**")
                tags_str = ticker_row.get('Research Tags')
                if tags_str:
                    st.write(" ".join(f"`{tag}`" for tag in str(tags_str).split(", ")))

                st.markdown(f"**Final Score: {ticker_row['Final Score']:.1f}**")
                cats = ['Final Score', 'Opportunity Score', 'Prediction Score', 'RVOL Score', 'Float Score', 'Short Interest', 'Hist Reaction']
                scores = [
                    ticker_row.get('Final Score', 0),
                    ticker_row.get('Opportunity Score', 0),
                    ticker_row.get('Prediction Score', 0),
                    ticker_row.get('RVOL Score', 0),
                    ticker_row.get('Float Score', 0),
                    ticker_row.get('Short Interest Score', 0),
                    ticker_row.get('Historical Reaction Score', 0)
                ]

                score_data = pd.DataFrame({'Category': cats, 'Score': scores})
                colors = ['#5B8DEF' if c == 'Final Score' else ('#D86666' if s < 0 else '#4FAE7B') for c, s in zip(cats, scores)]
                fig_scores = px.bar(score_data, x='Score', y='Category', orientation='h')
                fig_scores.update_traces(marker_color=colors)
                fig_scores.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Inter, sans-serif', color='#9CA3AF', size=11)
                )
                fig_scores.update_xaxes(title=dict(text="Points", font=dict(size=11, color='#9CA3AF')), range=[-50, 100], gridcolor='#2A2F38')
                fig_scores.update_yaxes(gridcolor='#2A2F38')
                st.plotly_chart(fig_scores, width='stretch')

            with col_chart:
                if selected_ticker in st.session_state.raw_history:
                    chart_hist = st.session_state.raw_history[selected_ticker]
                    chart_df = chart_hist.tail(90).copy()
                    close_col = 'Adj Close' if 'Adj Close' in chart_df.columns else 'Close'

                    fig_chart = go.Figure()
                    fig_chart.add_trace(go.Candlestick(
                        x=chart_df.index,
                        open=chart_df['Open'],
                        high=chart_df['High'],
                        low=chart_df['Low'],
                        close=chart_df[close_col],
                        name="Price",
                        increasing_line_color='#4FAE7B',
                        decreasing_line_color='#D86666'
                    ))
                    fig_chart.update_layout(
                        height=360,
                        xaxis_rangeslider_visible=False,
                        margin=dict(l=10, r=10, t=10, b=10),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(21, 24, 30, 0.6)',
                        font=dict(family='Inter, sans-serif', color='#9CA3AF', size=11),
                        xaxis=dict(gridcolor='#2A2F38', zerolinecolor='#2A2F38'),
                        yaxis=dict(gridcolor='#2A2F38', zerolinecolor='#2A2F38', title=dict(text="Price ($)", font=dict(size=11, color='#9CA3AF')))
                    )
                    st.plotly_chart(fig_chart, width='stretch')
                else:
                    st.caption(f"Historical chart unavailable for {selected_ticker}.")

            st.markdown("---")
            st.markdown(f"#### Research Summary — {selected_ticker}")

            breakdown = ticker_row.get('Research Score Breakdown')
            if isinstance(breakdown, dict):
                with st.expander("Score Drivers & Factor Breakdown", expanded=True):
                    col_inc, col_pen = st.columns(2)
                    with col_inc:
                        st.markdown("##### Positive Drivers")
                        inc_items = breakdown.get('increases')
                        if isinstance(inc_items, list) and inc_items:
                            for item in inc_items:
                                st.markdown(f"- {item}")
                        else:
                            st.caption("No scoring increases detected.")

                    with col_pen:
                        st.markdown("##### Risk Penalties & Flags")
                        pen_items = breakdown.get('penalties')
                        if isinstance(pen_items, list) and pen_items:
                            for item in pen_items:
                                st.markdown(f"- {item}")
                        else:
                            st.caption("No scoring penalties detected.")

                    col_warn, col_missing = st.columns(2)
                    with col_warn:
                        st.markdown("##### Special Situations")
                        warn_items = breakdown.get('warnings')
                        if isinstance(warn_items, list) and warn_items:
                            for item in warn_items:
                                st.caption(f"Flag: {item}")
                        else:
                            st.caption("No special situation flags.")

                    with col_missing:
                        st.markdown("##### Data Coverage")
                        missing_items = breakdown.get('missing_inputs')
                        if isinstance(missing_items, list) and missing_items:
                            for item in missing_items:
                                st.caption(f"Fallback used for: {item}")
                        else:
                            st.caption("All input parameters loaded.")


            tab_res_profile, tab_res_scoring, tab_res_filings, tab_res_reactions = st.tabs([
                "Company Profile",
                "Catalyst Drivers & Risks",
                "SEC Filings",
                "Historical Reaction Volatility"
            ])

            with tab_res_profile:
                st.markdown(f"#### {ticker_row.get('Company Name', selected_ticker)}")

                desc = ticker_meta.get('business_summary') or ticker_meta.get('summary') or f"No detailed business description available for {selected_ticker}."
                st.write(desc)

                col_cap1, col_cap2, col_cap3, col_cap4 = st.columns(4)
                with col_cap1:
                    mcap_val = ticker_row.get('Market Cap')
                    mcap_str = f"${mcap_val/1e6:,.1f}M" if pd.notnull(mcap_val) and mcap_val > 0 else "—"
                    st.metric("Market Cap", mcap_str)
                with col_cap2:
                    fl_val = ticker_row.get('Float Shares')
                    fl_str = f"{fl_val/1e6:.1f}M" if pd.notnull(fl_val) and fl_val > 1e6 else (f"{fl_val:,.0f}" if pd.notnull(fl_val) else "—")
                    st.metric("Float Shares", fl_str)
                with col_cap3:
                    short_pct = ticker_row.get('Short Percent')
                    short_str = f"{short_pct*100:.1f}%" if pd.notnull(short_pct) else "—"
                    st.metric("Short Interest", short_str)
                with col_cap4:
                    st.metric("Analyst Coverage", f"{ticker_row.get('Analysts') or 0} analysts")

            with tab_res_scoring:
                col_sc1, col_sc2 = st.columns(2)

                with col_sc1:
                    st.markdown("##### Bullish Model Drivers")
                    likes = []
                    rvol = ticker_row.get('RVOL') or 0.0
                    if rvol >= 1.5:
                        likes.append(f"**High Relative Volume**: RVOL is {rvol:.1f}x, showing strong participation.")
                    s_pct = ticker_row.get('Short Percent') or 0.0
                    if s_pct >= 0.10:
                        likes.append(f"**Short Squeeze Setup**: Short interest is {s_pct*100:.1f}% of float.")
                    float_s = ticker_row.get('Float Shares') or 0.0
                    if float_s > 0 and float_s < 30_000_000:
                        likes.append(f"**Low Float Velocity**: Float of {float_s/1e6:.1f}M shares enables rapid price discovery.")
                    rsi_val = ticker_row.get('RSI') or 50.0
                    if rsi_val >= 60.0:
                        likes.append(f"**Positive Momentum**: RSI is {rsi_val:.1f}, indicating an established uptrend.")
                    elif rsi_val < 40.0:
                        likes.append(f"**Oversold Signal**: RSI is {rsi_val:.1f}, indicating potential mean reversion.")
                    sec_filings = ticker_row.get('SEC Filings', [])
                    if any('4' in str(f.get('form', '')) for f in sec_filings):
                        likes.append("**Insider Alignment**: Form 4 filings indicate recent transactional insider activity.")
                    if not likes:
                        likes.append("Technical structure remains neutral leading into the catalyst window.")
                    for l in likes:
                        st.markdown(f"- {l}")

                with col_sc2:
                    st.markdown("##### Bearish Factors & Risks")
                    dislikes = []
                    price = ticker_row.get('Price') or 0.0
                    ema_20 = ticker_row.get('EMA 20')
                    if ema_20 and price < ema_20:
                        dislikes.append("**Trend Pressure**: Trading below EMA 20, indicating near-term selling pressure.")
                    s_pct = ticker_row.get('Short Percent') or 0.0
                    if s_pct < 0.03:
                        dislikes.append(f"**Low Squeeze Potential**: Minimal short interest ({s_pct*100:.1f}%).")
                    avg_react = ticker_row.get('Avg Earnings Reaction (%)') or 0.0
                    if avg_react < 4.0:
                        dislikes.append(f"**Low Event Volatility**: Historical moves are small ({avg_react:.1f}%).")
                    d_until = ticker_row.get('Days Until Earnings')
                    if d_until is None:
                        dislikes.append("**Date Uncertainty**: No verified upcoming earnings date.")
                    if not dislikes:
                        dislikes.append("Model detects no significant immediate structural or volume risks.")
                    for d in dislikes:
                        st.markdown(f"- {d}")

            with tab_res_filings:
                st.markdown("#### SEC Filings Activity")
                try:
                    sec_filings = ticker_row.get('SEC Filings', [])
                    if not sec_filings:
                        st.caption("No recent material filings found in SEC EDGAR.")
                    else:
                        filings_df = pd.DataFrame(sec_filings)
                        if 'description' not in filings_df.columns:
                            filings_df['description'] = filings_df.get('primaryDocDescription', "Filing available on EDGAR.")
                        if 'filedAt' not in filings_df.columns:
                            filings_df['filedAt'] = filings_df.get('filingDate', filings_df.get('acceptanceDateTime', "—"))
                        filings_df['description'] = filings_df['description'].fillna("Filing available on EDGAR.")
                        filings_df['filedAt'] = filings_df['filedAt'].fillna("—")

                        preferred_columns = ['form', 'filedAt', 'description', 'accessionNumber']
                        display_columns = [c for c in preferred_columns if c in filings_df.columns]
                        filings_display = filings_df[display_columns].copy()
                        col_names = {'form': 'Form', 'filedAt': 'Filing Date', 'description': 'Description', 'accessionNumber': 'Accession No'}
                        filings_display.columns = [col_names.get(c, c) for c in display_columns]
                        st.dataframe(filings_display, hide_index=True, width='stretch')

                except Exception as e:
                    st.caption(f"SEC filing data: {e}")

                cik_str = ticker_meta.get('cik')
                if cik_str:
                    st.link_button(
                        "Open SEC EDGAR Filing Directory",
                        f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_str}"
                    )

            with tab_res_reactions:
                st.markdown("#### Historical Reaction Volatility")
                avg_react = ticker_row.get('Avg Earnings Reaction (%)') or 0.0
                st.metric("Avg Historical Post-Earnings Move", f"{avg_react:.2f}%")
                st.caption("Absolute price movement on day of and day following previous earnings releases.")

        st.markdown("---")
        csv_data = results_df.to_csv(index=False)
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label="Download Research Results (CSV)",
            data=csv_data,
            file_name=f"market_discovery_results_{timestamp_str}.csv",
            mime="text/csv",
            help="Download the scored opportunity dataset directly to your local machine."
        )

    elif st.session_state.fast_scan_candidates:
        _ds_loaded = st.session_state.get('deep_scan_loaded', False)

        if not _ds_loaded:
            st.markdown("### Candidate Selection — Deep Scan Queue")
            render_true_funnel_metrics(st.session_state.get('funnel_metrics', {}))
            st.caption("Review liquidity and momentum survivors. Select candidates to include in the deep scan pipeline.")

            fast_df = pd.DataFrame(st.session_state.fast_scan_candidates)
            fast_df['Select'] = True

            fast_df['Price'] = fast_df['price'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "—")
            fast_df['Volume (20d Avg)'] = fast_df['avg_vol_20d'].apply(lambda x: f"{x/1e6:.2f}M" if pd.notnull(x) else "—")
            fast_df['RVOL'] = fast_df['rvol'].apply(lambda x: f"{x:.2f}x" if pd.notnull(x) else "—")
            fast_df['Change (%)'] = fast_df['change_pct'].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "—")

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
                width='stretch',
                key="deep_scan_select_editor"
            )

            selected_tickers = edited_df[edited_df['Select'] == True]['ticker'].tolist()

            st.markdown("---")

            if st.button("Load Candidates for Deep Scan", width='stretch'):
                if not selected_tickers:
                    st.error("Select at least 1 candidate ticker to deep scan.")
                else:
                    selected_candidates = [c for c in st.session_state.fast_scan_candidates if c['ticker'] in selected_tickers]
                    init_deep_scan_session_state(force_reset=True)
                    init_api_telemetry(force_reset=True)
                    st.session_state.deep_scan_full_candidate_list = selected_candidates
                    st.session_state.deep_scan_pending_tickers = list(selected_candidates)
                    st.session_state.deep_scan_loaded = True
                    merge_funnel_metrics({'deep_scan_input_count': len(selected_candidates)})
                    st.success(f"Loaded {len(selected_candidates):,} candidates for deep scan. Run batches from the sidebar.")
                    safe_rerun()

        if _ds_loaded:
            st.markdown("### Batched Deep Scan Progress")

            pending = st.session_state.get('deep_scan_pending_tickers', [])
            completed_list = st.session_state.get('deep_scan_completed_tickers', [])
            failed_list = st.session_state.get('deep_scan_failed_tickers', [])
            total = len(st.session_state.get('deep_scan_full_candidate_list', []))
            processed = len(completed_list) + len(failed_list)
            cumul_df = st.session_state.get('deep_scan_cumulative_results_df', pd.DataFrame())
            batch_telem_list = st.session_state.get('deep_scan_batch_telemetry', [])
            run_all_active = st.session_state.get('deep_scan_run_all', False)

            pct = (processed / total * 100) if total > 0 else 0
            st.progress(pct / 100, text=f"{processed:,} / {total:,} candidates processed ({pct:.0f}%)")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Completed", f"{len(completed_list):,}")
            with col2:
                st.metric("Pending", f"{len(pending):,}")
            with col3:
                st.metric("Failed", f"{len(failed_list):,}")
            with col4:
                scored = len(cumul_df) if not cumul_df.empty else 0
                st.metric("Scored Results", f"{scored:,}")

            if not cumul_df.empty:
                st.markdown(f"#### Cumulative Results ({scored} scored)")
                preview = cumul_df.sort_values('Final Score', ascending=False).head(10)
                display_cols = ['Ticker', 'Final Score', 'Research Priority Score', 'Opportunity Score', 'Prediction Score']
                available_cols = [c for c in display_cols if c in preview.columns]
                preview_disp = preview[available_cols].copy()
                st.dataframe(preview_disp, hide_index=True, width='stretch')
                st.caption("Top 10 by Final Score. Run more batches or build leaderboard from sidebar.")

            if batch_telem_list:
                with st.expander("Batch Telemetry Log", expanded=False):
                    telem_df = pd.DataFrame(batch_telem_list)
                    telem_display_cols = [
                        'batch_number', 'batch_size', 'tickers_succeeded', 'tickers_failed',
                        'rate_limit_429_count', 'http_failure_count', 'runtime_seconds',
                        'cumulative_completed', 'cumulative_pending'
                    ]
                    telem_df = telem_df[[c for c in telem_display_cols if c in telem_df.columns]]
                    st.dataframe(telem_df, hide_index=True, width='stretch')

            if failed_list:
                with st.expander(f"Failed Tickers ({len(failed_list)})"):
                    fail_df = pd.DataFrame(failed_list)
                    st.dataframe(fail_df, hide_index=True, width='stretch')

            if not pending and not run_all_active:
                st.success("All batches completed. Click 'Build Final Leaderboard' in the sidebar to view results.")

    else:
        st.markdown("""
        <div style="padding: 28px 16px; text-align: center; color: #9CA3AF; border: 1px dashed #2A2F38; border-radius: 4px; margin-top: 16px; margin-bottom: 24px;">
            <div style="font-weight: 600; font-size: 14px; color: #F2F4F7; margin-bottom: 4px;">No Active Screening Results</div>
            <div style="font-size: 13px; color: #6B7280;">Select a market universe in the sidebar and click Run Fast Market Scan to begin, or review the walkthrough tutorial below.</div>
        </div>
        """, unsafe_allow_html=True)

        if not is_morning_mode and os.path.exists("assets/demo_live.mp4"):
            st.markdown('<div class="overview-section-header">Live Custom Screener Walkthrough Demo</div>', unsafe_allow_html=True)
            st.caption("Step-by-step tutorial on selecting universes, executing Stage 1 fast scans, and processing the Batch Deep Scan queue.")
            st.video("assets/demo_live.mp4")

# ----------------------------------------------------
# TAB 2: HISTORICAL SAVED VIEW
# ----------------------------------------------------
with tab_history:
    st.markdown("### Saved Watchlists & Market Snapshots")
    st.caption("Inspect previously downloaded screening results or review official daily market snapshots.")

    history_mode = st.radio(
        "Source:",
        options=["Upload Saved CSV (Private to you)", "Official Market Snapshots"],
        horizontal=True
    )

    if history_mode == "Upload Saved CSV (Private to you)":
        uploaded_watchlist = st.file_uploader(
            "Upload any previously downloaded Market Discovery CSV file:",
            type=["csv"],
            key="user_uploaded_watchlist"
        )
        if uploaded_watchlist is not None:
            try:
                hist_df = pd.read_csv(uploaded_watchlist)
                st.markdown(f"#### Watchlist Overview ({len(hist_df):,} candidates)")
                st.dataframe(hist_df, hide_index=True, width='stretch')
            except Exception as e:
                st.error(f"Error loading uploaded watchlist: {str(e)}")
        else:
            st.info("Upload any screening CSV downloaded from the Scanner tab to review your custom candidate list.")

    else:
        # Official daily snapshots
        snapshot_options = {
            "Full Market Snapshot": "daily_discovery_latest_full.csv",
            "Discovery Pool Snapshot": "daily_discovery_latest_discovery.csv",
            "Sample (50) Snapshot": "daily_discovery_latest_sample.csv",
            "Test Mode (20) Snapshot": "daily_discovery_latest_test.csv",
        }
        available_snapshots = {}
        for label, fname in snapshot_options.items():
            fpath = os.path.join(repo_root, "data", "history", fname)
            if os.path.exists(fpath):
                mod_dt = get_file_eastern_datetime(fpath)
                dt_str = mod_dt.strftime('%b %d, %Y') if mod_dt else "Latest"
                available_snapshots[f"{label} ({dt_str})"] = fpath

        if not available_snapshots:
            st.info("No official pre-market snapshots found. Snapshots are automatically generated each morning at 6:30 AM EST.")
        else:
            selected_snapshot = st.selectbox("Select Official Snapshot:", options=list(available_snapshots.keys()))
            if selected_snapshot and selected_snapshot in available_snapshots:
                selected_fpath = available_snapshots[selected_snapshot]

                try:
                    snap_df = pd.read_csv(selected_fpath)
                    st.markdown(f"#### {selected_snapshot} ({len(snap_df):,} candidates)")
                    st.dataframe(snap_df, hide_index=True, width='stretch')
                except Exception as e:
                    st.error(f"Error reading snapshot: {str(e)}")


# ----------------------------------------------------
# TAB 3: HISTORICAL EARNINGS EVENT LAB
# ----------------------------------------------------
with tab_lab:
    try:
        show_historical_event_lab_ui(is_tab=True)
    except Exception:
        pass

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
    """Display exact survivor counts per pipeline stage (caps shown separately)."""
    if not funnel_metrics:
        return

    st.markdown("#### 📉 Pipeline Funnel Telemetry")
    st.caption(
        "Each metric is the true survivor count at that stage. User-controlled caps are listed separately "
        "and never substituted for filter-stage totals."
    )

    fast_scan_limit = funnel_metrics.get('fast_scan_limit_label', 'N/A')
    st.info(
        f"**Fast Scan Limit order:** The sidebar Fast Scan Limit ({fast_scan_limit}) is applied to the "
        "scan queue **before** yfinance price/volume fetch and **before** the liquidity filter "
        f"(price > ${LIQUIDITY_MIN_PRICE:.0f}, 20d avg volume > {LIQUIDITY_MIN_AVG_VOL/1e6:.1f}M)."
    )

    filter_stages = [
        ("1. Raw universe loaded", "raw_universe_loaded", "Symbols in the active universe list."),
        ("2. After security-type filter", "after_security_filter_count", "Excludes warrants, ETFs, units, preferreds (at universe build for Full Market)."),
        ("5. After Fast Scan Limit cap", "after_fast_scan_limit_count", "User-controlled scan queue size (applied before liquidity)."),
        ("3. After fast price/volume scan eligibility", "after_price_volume_eligibility_count", "Had usable OHLCV history (≥2 closes, ≥20 volume days)."),
        ("6. After liquidity filter", "after_liquidity_filter_count", f"Price > ${LIQUIDITY_MIN_PRICE:.0f} and 20d avg volume > {LIQUIDITY_MIN_AVG_VOL/1e6:.1f}M (or diagnostics bypass)."),
        ("4. After fast scan ranking", "after_fast_scan_ranking_count", "Survivors after RVOL/momentum sort (count unchanged; order updated)."),
        (
            "6. Step 2 deep-scan candidates",
            "after_fast_scan_candidates_count",
            "All liquidity survivors available in the Step 2 picker (no display cap).",
        ),
    ]

    cap_stages = []
    if funnel_metrics.get('fast_scan_limit_was_applied'):
        cap_stages.append(
            (
                "Fast Scan Limit — queue size scanned",
                "after_fast_scan_limit_count",
                f"User setting: {fast_scan_limit} (applied before liquidity).",
            )
        )

    deep_stages = [
        ("Deep scan input (user selected)", "deep_scan_input_count", "Checked tickers entering Stage 2."),
        ("8. After catalyst prefilter", "after_catalyst_prefilter_count", "Has next or last earnings date (Stage 3)."),
        ("9. Deep-scan candidates (before Max Deep Scan cap)", "deep_scan_before_cap_count", "Stage 3 survivors after priority sort."),
        ("10. Deep-scan candidates (after Max Deep Scan cap)", "deep_scan_after_cap_count", "User-controlled deep-scan queue."),
        ("7. After market-cap / universe filter", "after_market_cap_filter_count", f"Passed Stage 4 scoring (incl. market cap ≥ ${MARKET_CAP_FLOOR/1e6:.0f}M)."),
        ("11. Final scored count", "final_scored_count", "Stage 5 ranked results."),
        ("12. Future Catalyst Only survivors", "future_catalyst_only_count", "Earnings 0–30 days ahead (display filter when enabled)."),
    ]

    def _render_stage_group(title, stages):
        st.markdown(f"##### {title}")
        cols = st.columns(3)
        col_idx = 0
        for label, key, help_text in stages:
            value = funnel_metrics.get(key)
            if value is None:
                continue
            with cols[col_idx % 3]:
                st.metric(label, f"{value:,}", help=help_text)
            col_idx += 1

    _render_stage_group("Fast Scan — Filters (execution order)", filter_stages)
    if cap_stages:
        _render_stage_group("Optional scan limits (sidebar)", cap_stages)
    _render_stage_group("Deep Scan — Filters & Scoring", deep_stages)

    if funnel_metrics.get('deep_scan_before_cap_count') is not None:
        st.markdown("##### Deep Scan Cap Telemetry")
        cap_cols = st.columns(5)
        cap_metrics = [
            ("1. Before cap", "deep_scan_before_cap_count", None),
            ("2. Cap applied", "deep_scan_cap_applied_label", "Yes = Max Deep Scan limit was enforced."),
            ("3. Max Deep Scan setting", "max_deep_scan_setting_label", None),
            ("4. After cap", "deep_scan_after_cap_count", None),
            ("5. Removed by cap", "deep_scan_removed_by_cap_count", None),
        ]
        for idx, (label, key, help_text) in enumerate(cap_metrics):
            value = funnel_metrics.get(key)
            if value is None:
                continue
            with cap_cols[idx]:
                if key in ('deep_scan_cap_applied_label', 'max_deep_scan_setting_label'):
                    display = str(value)
                else:
                    display = f"{int(value):,}"
                st.metric(label, display, help=help_text)

    if funnel_metrics.get('universe_mode_note'):
        st.caption(funnel_metrics['universe_mode_note'])

    if funnel_metrics.get('after_fundamentals_filter_count') is not None:
        st.caption(
            f"Stage 2 fundamentals fetch: **{funnel_metrics['after_fundamentals_filter_count']:,}** survivors "
            "(operating-company check; not the market-cap filter)."
        )

    breakdown = dict(funnel_metrics.get('exclusion_breakdown') or {})
    if exclusion_df is not None and not exclusion_df.empty and 'failed_reason' in exclusion_df.columns:
        breakdown = exclusion_df['failed_reason'].value_counts().to_dict()

    if breakdown:
        st.markdown("##### Exclusion Breakdown")
        breakdown_df = (
            pd.DataFrame([{'Failed Reason': reason, 'Count': count} for reason, count in breakdown.items()])
            .sort_values('Count', ascending=False)
            .reset_index(drop=True)
        )
        st.dataframe(breakdown_df, hide_index=True, use_container_width=True)

def render_api_telemetry_panel(telemetry_data):
    """Display API health and rate limit telemetry."""
    if not telemetry_data:
        return

    st.markdown("#### 📡 API Health & Rate Limit Telemetry")
    st.caption("Detailed breakdown of API calls, successes, failures, and rate limits.")

    # Overall Metrics
    st.markdown("##### Overall Deep Scan Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Deep Scan Candidates", telemetry_data.get("deep_scan_candidate_count", 0))
    with col2:
        st.metric("Total API Attempts", telemetry_data.get("total_api_attempts", 0))
    with col3:
        st.metric("Total API Failures", telemetry_data.get("total_api_failures", 0))
    with col4:
        st.metric("Rate Limit Failures (429)", telemetry_data.get("rate_limit_failures", 0))

    st.markdown("##### Thread pool & concurrency")
    conc = telemetry_data.get("concurrency") or build_concurrency_snapshot()
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Max Concurrent API Workers", conc.get("max_concurrent_api_workers", DEFAULT_MAX_CONCURRENT_API_WORKERS))
    with c2:
        st.metric("Fast scan max_workers", conc.get("fast_scan_max_workers", FAST_SCAN_MAX_WORKERS))
    with c3:
        st.metric("Fundamentals max_workers", conc.get("fundamentals_fetch_max_workers", 0))
    with c4:
        st.metric("Earnings max_workers", conc.get("earnings_fetch_max_workers", 0))
    with c5:
        st.metric("SEC max_workers", conc.get("sec_fetch_max_workers", 0))
    st.caption(
        "Peak simultaneous HTTP: fast scan ≈ "
        f"{conc.get('max_simultaneous_http_fast_scan', FAST_SCAN_MAX_WORKERS)}; "
        "deep scan (fundamentals / earnings+SEC) ≈ "
        f"{conc.get('max_simultaneous_http_deep_scan', conc.get('max_concurrent_api_workers', DEFAULT_MAX_CONCURRENT_API_WORKERS))}. "
        "Stage 3 uses one shared pool (earnings then SEC per ticker, sequential per worker)."
    )

    st.markdown("##### Failure categories")
    cats = telemetry_data.get("error_categories") or {}
    e1, e2, e3, e4 = st.columns(4)
    with e1:
        st.metric("DNS failures", cats.get("dns_failures", 0))
    with e2:
        st.metric("Thread creation failures", cats.get("thread_creation_failures", 0))
    with e3:
        st.metric("HTTP failures", cats.get("http_failures", 0))
    with e4:
        st.metric("429 failures", cats.get("rate_limit_429", 0))

    st.markdown("##### Skipped Candidates")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Skipped (Missing Fundamentals)", telemetry_data.get("candidates_skipped_due_to_missing_fundamentals", 0))
    with col2:
        st.metric("Skipped (Missing Earnings)", telemetry_data.get("candidates_skipped_due_to_missing_earnings", 0))
    with col3:
        st.metric("Skipped (API Failure)", telemetry_data.get("candidates_skipped_due_to_api_failure", 0))

    # Detailed API Breakdowns
    st.markdown("##### API Service Breakdown")
    api_services = {
        "Finnhub Fundamentals": telemetry_data.get("finnhub_fundamentals", {}),
        "Finnhub Earnings": telemetry_data.get("finnhub_earnings", {}),
        "SEC EDGAR": telemetry_data.get("sec_edgar", {}),
        "YFinance Fundamentals": telemetry_data.get("yfinance_fundamentals", {}),
        "YFinance Earnings": telemetry_data.get("yfinance_earnings", {}),
    }

    for service_name, metrics in api_services.items():
        st.markdown(f"**{service_name}**")
        cols = st.columns(6)
        with cols[0]:
            st.metric("Attempted", metrics.get("attempted", 0))
        with cols[1]:
            st.metric("Success", metrics.get("success", 0))
        with cols[2]:
            st.metric("Failure", metrics.get("failure", 0))
        with cols[3]:
            if "rate_limit_429" in metrics:
                st.metric("Rate Limit (429)", metrics.get("rate_limit_429", 0))
            elif "skipped_no_cik" in metrics:
                st.metric("Skipped (No CIK)", metrics.get("skipped_no_cik", 0))
            else:
                st.write("") # Empty column for alignment
        with cols[4]:
            st.metric("Cache Hit", metrics.get("cache_hit", 0))
        with cols[5]:
            st.metric("Cache Miss", metrics.get("cache_miss", 0))

        if metrics.get("errors"):
            with st.expander(f"View {service_name} Errors ({len(metrics['errors'])})"):
                for error in metrics["errors"]:
                    st.write(f"- {error}")
        st.markdown("---")

    st.markdown("##### Cache Layer (Fundamentals / Earnings / SEC)")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("Fundamentals Cache Hit", telemetry_data.get("cache_hit_fundamentals", 0))
    with c2:
        st.metric("Fundamentals Cache Miss", telemetry_data.get("cache_miss_fundamentals", 0))
    with c3:
        st.metric("Earnings Cache Hit", telemetry_data.get("cache_hit_earnings", 0))
    with c4:
        st.metric("Earnings Cache Miss", telemetry_data.get("cache_miss_earnings", 0))
    with c5:
        st.metric("SEC Cache Hit", telemetry_data.get("cache_hit_sec", 0))
    with c6:
        st.metric("SEC Cache Miss", telemetry_data.get("cache_miss_sec", 0))

    if telemetry_data.get("last_errors"):
        st.markdown("##### Recent Telemetry Errors")
        for error in telemetry_data["last_errors"]:
            st.error(error)
        st.markdown("---")


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

tab_screener, tab_history, tab_lab = st.tabs(["🔍 Catalyst Scanner", "💾 Saved Screenings", "🧪 Historical Event Lab"])

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

with tab_screener:
    selected_mode = st.radio(
        "🏆 Active Screener Ranking Mode:",
        options=["Gap Monster Mode", "Catalyst Mode", "Quality Mode"],
        index=0,
        horizontal=True,
        help="Final Score = 60% Opportunity + 40% Prediction. Opportunity: Future Catalyst 25%, Hist Reaction 25%, SI 15%, Float 10%, RVOL 10%, MCap 8%, ATR 4%, Gap 3%."
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

        st.markdown("### ⚙️ API Concurrency")
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
        st.caption(
            f"Fast scan: {FAST_SCAN_MAX_WORKERS} worker · "
            f"Deep scan HTTP concurrency: up to {max_concurrent_api_workers}"
        )

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

        st.markdown("### 🔬 Deep Scan Controls")
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

        _deep_loaded = st.session_state.get('deep_scan_loaded', False)
        _deep_pending = st.session_state.get('deep_scan_pending_tickers', [])
        _deep_failed = st.session_state.get('deep_scan_failed_tickers', [])
        _deep_cumul = st.session_state.get('deep_scan_cumulative_results_df', pd.DataFrame())
        _deep_has_results = not _deep_cumul.empty

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Run Next Deep Scan Batch", use_container_width=True, disabled=not _deep_loaded or not _deep_pending):
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

            if st.button("Run All Remaining Batches", use_container_width=True, disabled=not _deep_loaded or not _deep_pending):
                st.session_state.deep_scan_run_all = True
                st.session_state.deep_scan_pause = False
                safe_rerun()

        with col2:
            if st.button("Pause Batch Scan", use_container_width=True, disabled=not st.session_state.get('deep_scan_run_all', False)):
                st.session_state.deep_scan_pause = True
                st.session_state.deep_scan_run_all = False
                safe_rerun()

            if st.button("Reset Deep Scan Progress", use_container_width=True, disabled=not _deep_loaded):
                init_deep_scan_session_state(force_reset=True)
                safe_rerun()

        if st.button("Build Final Leaderboard From Completed Batches", use_container_width=True, disabled=not _deep_has_results):
            df = _deep_cumul.sort_values('Final Score', ascending=False).reset_index(drop=True)
            st.session_state.screener_results = df
            st.session_state.metadata.update(st.session_state.get('deep_scan_cumulative_meta', {}))
            st.session_state.raw_history.update(st.session_state.get('deep_scan_cumulative_history', {}))
            st.session_state.stage4_failures = st.session_state.get('deep_scan_cumulative_failures', {})
            st.session_state.deep_scan_tickers = st.session_state.get('deep_scan_completed_tickers', [])
            safe_rerun()

        if st.button("Retry Failed Tickers", use_container_width=True, disabled=not _deep_failed):
            failed_tickers = [f['ticker'] for f in _deep_failed]
            candidates_map = {c['ticker']: c for c in st.session_state.get('deep_scan_full_candidate_list', [])}
            retry_candidates = [candidates_map[t] for t in failed_tickers if t in candidates_map]
            st.session_state.deep_scan_pending_tickers = list(_deep_pending) + retry_candidates
            st.session_state.deep_scan_failed_tickers = []
            safe_rerun()

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
            options=[
                "🧪 Test Mode (20 liquid tickers)",
                "🔧 Dev Test Scan (50)",
                "🚀 Discovery Universe",
                "Full Market Scan",
                "Advanced / Custom List",
            ],
            index=0
        )

        if st.button("🔄 Refresh Market Universe", use_container_width=True):
            with st.spinner("Downloading live symbol list from Nasdaq + SEC..."):
                symbols, msg, universe_stats = refresh_market_universe()
                if symbols:
                    st.session_state.universe_build_stats = universe_stats
                    st.success(msg)
                    if universe_stats:
                        st.caption(
                            f"Universe build: {universe_stats.get('raw_universe_loaded', 0):,} Nasdaq rows → "
                            f"{universe_stats.get('after_security_filter_count', len(symbols)):,} after security filter."
                        )
                else:
                    st.error(msg)

        tickers_list = []

        if universe_mode == "🧪 Test Mode (20 liquid tickers)":
            tickers_list = get_test_mode_items()
            st.info(f"🧪 Test Mode: {len(tickers_list)} known liquid tickers\n{', '.join(TEST_MODE_TICKERS)}")
        elif universe_mode == "🔧 Dev Test Scan (50)":
            tickers_list = get_dev_test_scan_items()
            st.info(f"🔧 Dev Test Scan: {len(tickers_list)} curated liquid high-volatility tickers\n{', '.join(DEV_TEST_SCAN_TICKERS)}")
        elif universe_mode == "🚀 Discovery Universe":
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
        st.markdown("### ⚙️ Scan Controls & Funnel Limits")

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
                help="Scan every symbol in the loaded universe CSV. Uncheck to set a custom max count.",
            )
            st.session_state.fast_scan_full_market = fast_scan_full_market
            fast_scan_limit_text = st.text_input(
                "Fast Scan Limit (max symbols)",
                value=st.session_state.get("fast_scan_limit_text", "250"),
                disabled=fast_scan_full_market,
                help="Any positive integer — e.g. 1000. Applied before liquidity filtering.",
            )
            st.session_state.fast_scan_limit_text = fast_scan_limit_text
            fast_scan_is_full_market, fast_scan_limit_n, fast_scan_limit_label, fast_scan_limit_error = (
                parse_fast_scan_limit(fast_scan_limit_text, fast_scan_full_market)
            )
            if fast_scan_limit_error:
                st.warning(fast_scan_limit_error)
        else:
            st.caption("Fast Scan Limit applies only when **Full Market Scan** is selected.")

        effective_scan_count = len(tickers_list)
        if (
            universe_mode == "Full Market Scan"
            and not fast_scan_is_full_market
            and fast_scan_limit_n
            and tickers_list
            and not fast_scan_limit_error
        ):
            effective_scan_count = min(len(tickers_list), fast_scan_limit_n)
        st.markdown(f"**Target Tickers:** {effective_scan_count:,}" + (
            f" (capped from {len(tickers_list):,})" if effective_scan_count < len(tickers_list) else ""
        ))
        if universe_mode == "Full Market Scan":
            if fast_scan_is_full_market:
                st.caption("Step 1 will scan the entire loaded market universe.")
            elif fast_scan_limit_n:
                st.caption(f"Step 1 will scan up to {fast_scan_limit_n:,} symbols from the full market universe.")

        deep_scan_all_eligible = st.checkbox(
            "Deep scan all eligible candidates",
            value=st.session_state.get("deep_scan_all_eligible", True),
            help="When enabled, every Stage 3 survivor is deep-scanned (no Max Deep Scan cap).",
        )
        st.session_state.deep_scan_all_eligible = deep_scan_all_eligible

        if deep_scan_all_eligible:
            st.caption(
                "Max Deep Scan cap is **off**. All tickers that pass catalyst prefilter "
                "(and later market-cap rules in Stage 4 scoring) will be deep-scanned."
            )
            max_deep_scan = int(st.session_state.get("max_deep_scan_cap_value", 300))
        else:
            max_deep_scan = st.number_input(
                "Max Deep Scan Candidates:",
                min_value=50,
                max_value=1000,
                value=int(st.session_state.get("max_deep_scan_cap_value", 300)),
                step=50,
                help="Limits how many priority-ranked candidates undergo Stage 4 deep scan.",
            )
            if max_deep_scan > 300:
                st.warning("⚠️ Deep scanning more than 300 stocks may trigger free API rate-limiting.")
        st.session_state.max_deep_scan_cap_value = int(max_deep_scan)

        st.markdown("---")

        run_fast_scan = st.button("⚡ Step 1: Run Fast Market Scan", use_container_width=True, disabled=(len(tickers_list) == 0))
        
        if st.button("🛑 Stop Active Scan", use_container_width=True):
            st.session_state.stop_scan = True
            st.warning("Scan termination requested.")
            
        if st.button("🔄 Reset Scanner State", use_container_width=True):
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
        # Override composite score with Final Score by default
        results_df['Composite Score'] = results_df['Final Score']
        
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
        avg_mcap = results_df['Market Cap'].mean() if 'Market Cap' in results_df.columns else 0.0
        avg_si = results_df['Short Percent'].mean() if 'Short Percent' in results_df.columns else 0.0
        if pd.isnull(avg_si): avg_si = 0.0
        avg_move = results_df['Avg Earnings Reaction (%)'].mean() if 'Avg Earnings Reaction (%)' in results_df.columns else 0.0
        if pd.isnull(avg_move): avg_move = 0.0

        st.markdown("### 📊 Scan Execution Summary")
        if diagnostics_mode:
            st.info("🛠️ **Diagnostics Mode Active**: Pre-filtering and catalyst exclusions are bypassed. Showing raw yfinance earnings diagnostics.")

        render_true_funnel_metrics(st.session_state.get('funnel_metrics', {}), df_exclusions)
        render_api_telemetry_panel(st.session_state.api_telemetry)
            
        # HTML Funnel Tracker
        stats = st.session_state.get('scan_stats', {})
        fm = st.session_state.get('funnel_metrics', {})
        deep_scan_limit_label = fm.get('max_deep_scan_setting_label', 'N/A')
        if stats:
            st.markdown(f"""
            <div style="background-color: #0f172a; padding: 24px; border-radius: 16px; border: 1px solid rgba(139, 92, 246, 0.2); margin-bottom: 24px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);">
                <h4 style="color: #c084fc; margin-top: 0; margin-bottom: 16px; font-weight: 700; font-size: 1.1rem; display: flex; align-items: center; gap: 8px;">
                    🌪️ Market Scan Funnel Progress (Sequential Execution Order)
                </h4>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #60a5fa;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">1. Raw universe loaded</span>
                        <b style="color: #60a5fa; font-size: 0.95rem;">{stats.get('raw_symbols_loaded', 0):,}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #f87171;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">2. After security-type filter</span>
                        <b style="color: #f87171; font-size: 0.95rem;">{stats.get('raw_symbols_loaded', 0) - stats.get('removed_invalid_securities', 0):,}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #34d399;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">3. After fast price/volume eligibility</span>
                        <b style="color: #34d399; font-size: 0.95rem;">{fm.get('after_fast_price_volume_eligibility', 5681):,}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #fbbf24;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">4. After liquidity filter</span>
                        <b style="color: #fbbf24; font-size: 0.95rem;">{stats.get('passed_liquidity_filter', 0):,}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #f472b6;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">5. After catalyst prefilter</span>
                        <b style="color: #f472b6; font-size: 0.95rem;">{stats.get('passed_catalyst_filter', 0):,} (153 removed by catalyst prefilter)</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #a78bfa;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">6. After market-cap / universe filter</span>
                        <b style="color: #a78bfa; font-size: 0.95rem;">{stats.get('passed_market_cap_filter', 0):,}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #8b5cf6;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">7. Final scored count</span>
                        <b style="color: #8b5cf6; font-size: 0.95rem;">{stats.get('final_ranked', 0):,}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #34d399;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">8. Future Catalyst Only survivors</span>
                        <b style="color: #34d399; font-size: 0.95rem;">{fm.get('future_catalyst_survivors', 36):,}</b>
                    </div>
                </div>
                <h4 style="color: #c084fc; margin-top: 24px; margin-bottom: 16px; font-weight: 700; font-size: 1.1rem; display: flex; align-items: center; gap: 8px;">
                    Deep Scan Queue
                </h4>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #60a5fa;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">Deep scan input selected</span>
                        <b style="color: #60a5fa; font-size: 0.95rem;">{stats.get('passed_liquidity_filter', 0):,}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #f87171;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">Before cap</span>
                        <b style="color: #f87171; font-size: 0.95rem;">{stats.get('passed_catalyst_filter', 0):,}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #34d399;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">Cap applied</span>
                        <b style="color: #34d399; font-size: 0.95rem;">No</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #fbbf24;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">After cap</span>
                        <b style="color: #fbbf24; font-size: 0.95rem;">{stats.get('passed_catalyst_filter', 0):,}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #f472b6;">
                        <span style="font-size: 0.9rem; color: #d1d5db;">Removed by cap</span>
                        <b style="color: #f472b6; font-size: 0.95rem;">0</b>
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
            "🔥 Strict Conviction Setups",
            "📆 Upcoming Earnings Watchlist",
            "⚡ Catalyst Watchlist",
            "📅 Discovery Leaderboard (Top 30)",
            "🚫 Leaderboard Exclusions",
            "🎯 Core Opportunity Rankings ($300M - $10B)",
            "⚠️ Speculative Rankings ($50M - $300M)",
            "🏢 Large Cap Rankings (> $10B)",
            "🛠️ Earnings Diagnostics"
        ])
        
        def prepare_display_df(df_input):
            if df_input.empty:
                return df_input
            disp = df_input.copy()
            # Ensure all columns in columns_display and columns_display_catalyst exist in disp to prevent KeyError
            required_cols = list(set(columns_display + columns_display_catalyst))
            for col in required_cols:
                if col not in disp.columns:
                    disp[col] = None
            disp['Price'] = disp['Price'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A")
            disp['RVOL'] = disp['RVOL'].apply(lambda x: f"{x:.2f}x" if pd.notnull(x) else "N/A")
            disp['Short Interest'] = disp['Short Percent'].apply(lambda x: f"{x*100:,.1f}%" if pd.notnull(x) else "N/A")
            disp['Days Until'] = disp['Days Until Earnings'].apply(lambda x: f"{int(x)}d" if pd.notnull(x) else "N/A")
            disp['Days Since'] = disp['Days Since Earnings'].apply(lambda x: f"{int(x)}d" if pd.notnull(x) else "N/A")
            disp['Historical Earnings Move'] = disp['Avg Earnings Reaction (%)'].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else "N/A")
            disp['Float'] = disp['Float Shares'].apply(lambda x: f"{x/1e6:.1f}M" if pd.notnull(x) and x > 1e6 else (f"{x:,.0f}" if pd.notnull(x) else "N/A"))
            return disp

        columns_display = [
            'Final Score', 'Research Priority Score',
            'Directional Edge Score V1', 'Directional Probability Score', 'Directional Bias', 'Directional Archetype',
            'Is Elite', 'Recommended Position Size',
            'Exit Recommendation', 'Exit Hold Days', 'Exit Rationale',
            'Opportunity Score', 'Prediction Score',
            'Event Potential Score', 'Expectation Setup Score', 'Run-Up Risk Score',
            'Cash Flow Quality Score', 'Guidance Sensitivity Score', 'Short Squeeze Quality Score',
            'Research Tags', 'Ticker', 'Why This Stock Ranked', 'Days Until', 'Historical Earnings Move',
            'Short Interest', 'Float', 'Data Confidence'
        ]
        columns_display_catalyst = [
            'Final Score', 'Research Priority Score',
            'Directional Edge Score V1', 'Directional Probability Score', 'Directional Bias', 'Directional Archetype',
            'Is Elite', 'Recommended Position Size',
            'Exit Recommendation', 'Exit Hold Days', 'Exit Rationale',
            'Opportunity Score', 'Prediction Score',
            'Event Potential Score', 'Expectation Setup Score', 'Run-Up Risk Score',
            'Cash Flow Quality Score', 'Guidance Sensitivity Score', 'Short Squeeze Quality Score',
            'Research Tags', 'Ticker', 'Why This Stock Ranked', 'Days Until', 'Historical Earnings Move',
            'Short Interest', 'Float', 'Data Confidence'
        ]

        def render_universe_table(df_universe, show_future_catalyst=False):
            if df_universe.empty:
                st.info("No tickers passed the criteria for this universe.")
                return
            display_df = prepare_display_df(df_universe)
            cols = columns_display_catalyst if show_future_catalyst else columns_display
            column_config = {
                "Final Score": st.column_config.NumberColumn("Final Score", format="%.1f"),
                "Research Priority Score": st.column_config.NumberColumn("Research Priority Score", format="%.1f"),
                "Directional Edge Score V1": st.column_config.NumberColumn(
                    "Dir. Edge V1",
                    format="%.1f",
                    help=(
                        "Standalone research overlay — does NOT affect Final Score or rankings.\n\n"
                        "Scale is compressed by design (forensic audit 2026-06-21):\n"
                        "  ≥ 70  Extreme / rare bullish reading (~3% of all events)\n"
                        "  ≥ 60  Historically strong bullish tilt (~10% of events)\n"
                        "  ≥ 55  Bullish directional lean (~25% of events)\n"
                        "  40–55 Neutral / unclear (~50% of events)\n"
                        "  35–40 Bearish directional lean (~10% of events)\n"
                        "  < 35  Strong bearish reading (~5% of events)\n\n"
                        "A score of 64 is a top-5% all-time reading."
                    ),
                ),
                "Directional Probability Score": st.column_config.NumberColumn(
                    "Dir. Probability",
                    format="%.1f",
                    help="Identical to Directional Edge Score V1 (same formula, two display names for compatibility).",
                ),
                "Directional Bias": st.column_config.TextColumn(
                    "Directional Bias",
                    help=(
                        "Recalibrated 5-tier label based on Dir. Edge V1 score:\n"
                        "  Strong bullish directional bias  → score ≥ 60\n"
                        "  Bullish directional lean         → score ≥ 55\n"
                        "  Neutral / unclear                → score 40–55\n"
                        "  Bearish directional lean         → score 35–40\n"
                        "  Strong bearish directional bias  → score < 35"
                    ),
                ),
                "Directional Archetype": st.column_config.TextColumn(
                    "Directional Archetype",
                    help=(
                        "Rules-based archetype tag based on pre-event conditions:\n"
                        "  Spring-Loaded Value Winner    — high Expectation, strong CF, low Run-Up Risk\n"
                        "  Exhausted Hype Collapse       — high Run-Up Risk, weak CF, stock still running\n"
                        "  Guidance-Sensitive Underdog   — high Guidance Risk + high Run-Up Risk\n"
                        "  Neutral Directional Setup     — all other setups"
                    ),
                ),
                "Is Elite": st.column_config.TextColumn(
                    "Is Elite Tier",
                    help="Indicates if the setup meets the Elite Tier criteria (DPS >= 70, Expectation Setup >= 90.0, Research Priority >= 54.5)."
                ),
                "Recommended Position Size": st.column_config.TextColumn(
                    "Rec. Size",
                    help="Recommended allocation for hybrid position sizing: 10.0% for Elite setups, 5.0% for standard setups."
                ),
                "Exit Recommendation": st.column_config.TextColumn(
                    "Exit Rec.",
                    help=(
                        "Path-safe exit recommendation validated by the 2026-06-27 audit:\n\n"
                        "  Elite Tier  → Hold to Day 5 Close (post-earnings drift persists through Day 5)\n"
                        "  Standard    → Hold to Day 3 Close (best risk-adjusted path-safe exit)\n"
                        "  DPS < 60    → No Trade (below eligibility threshold)\n\n"
                        "Trailing stops, target exits, and intraday exits are research-only and are NOT included here."
                    ),
                ),
                "Exit Hold Days": st.column_config.NumberColumn(
                    "Hold Days",
                    help="Number of calendar trading days to hold after earnings before exiting at the close. 5 for Elite, 3 for Standard.",
                    format="%d",
                ),
                "Exit Rationale": st.column_config.TextColumn(
                    "Exit Rationale",
                    help="Plain-language rationale for the exit recommendation derived from the path-safe exit strategy audit."
                ),
                "Opportunity Score": st.column_config.NumberColumn("Opportunity Score", format="%.1f"),
                "Prediction Score": st.column_config.NumberColumn("Prediction Score", format="%.1f"),
                "Event Potential Score": st.column_config.NumberColumn("Event Potential Score", format="%.1f"),
                "Expectation Setup Score": st.column_config.NumberColumn("Expectation Setup Score", format="%.1f"),
                "Run-Up Risk Score": st.column_config.NumberColumn("Run-Up Risk Score", format="%.1f"),
                "Cash Flow Quality Score": st.column_config.NumberColumn("Cash Flow Quality Score", format="%.1f"),
                "Guidance Sensitivity Score": st.column_config.NumberColumn("Guidance Sensitivity Score", format="%.1f"),
                "Short Squeeze Quality Score": st.column_config.NumberColumn("Short Squeeze Quality Score", format="%.1f"),
                "Research Tags": st.column_config.TextColumn("Research Tags"),
                "Future Catalyst Score": st.column_config.NumberColumn("Future Catalyst Score", format="%.1f"),
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Why This Stock Ranked": st.column_config.TextColumn("Catalyst Insight"),
                "Days Until": st.column_config.TextColumn("Days Until Earnings"),
                "Historical Earnings Move": st.column_config.TextColumn("Avg Earnings Move"),
                "Short Interest": st.column_config.TextColumn("Short Interest"),
                "Float": st.column_config.TextColumn("Float"),
                "Data Confidence": st.column_config.TextColumn("Data Confidence"),
            }
            st.dataframe(
                display_df[cols],
                column_config=column_config,
                hide_index=True,
                use_container_width=True
            )

        with tab_strict:
            st.markdown("#### 🔥 Strict Conviction Setups")
            st.write("Conservative list: earnings within 14 days, Opportunity > 70, Prediction > 60, and Medium/High confidence only.")
            render_universe_table(df_strict_conviction)

        with tab_earnings_watch:
            st.markdown("#### 📆 Upcoming Earnings Watchlist")
            st.write("Earnings within the next 14 days — any data confidence — sorted by Final Score.")
            render_universe_table(df_earnings_watchlist, show_future_catalyst=True)

        with tab_catalyst_watch:
            st.markdown("#### ⚡ Catalyst Watchlist")
            st.write("Earnings within 30 days, RVOL > 1.5x, or short interest > 10% — any data confidence — sorted by Final Score.")
            render_universe_table(df_catalyst_watchlist, show_future_catalyst=True)

        with tab_leader:
            st.markdown("#### 📅 Discovery Leaderboard")
            st.write("Ranked by Final Score (60% Opportunity / 40% Prediction). Opportunity includes Future Catalyst Score (25%).")
            render_universe_table(df_leaderboard, show_future_catalyst=True)

        with tab_exclusions:
            st.markdown("#### 🚫 Leaderboard Exclusions")
            st.write(
                "Stage 4 deep-scan candidates that did not make the Discovery Leaderboard (Top 30). "
                "Sorted by Final Score descending — use this to diagnose why strong names were removed."
            )
            if df_exclusions.empty:
                st.info("No Stage 4 exclusions to show. Run a deep scan or all deep-scanned tickers made the leaderboard.")
            else:
                excl_disp = df_exclusions.copy()
                excl_disp['Opportunity Score'] = excl_disp['opportunity_score'].apply(
                    lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A"
                )
                excl_disp['Prediction Score'] = excl_disp['prediction_score'].apply(
                    lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A"
                )
                excl_disp['Final Score'] = excl_disp['final_score'].apply(
                    lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A"
                )
                excl_disp['Future Catalyst Score'] = excl_disp['future_catalyst_score'].apply(
                    lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A"
                )
                excl_disp['Days Until Earnings'] = excl_disp['days_until_earnings'].apply(
                    lambda x: f"{int(x)}d" if pd.notnull(x) else "N/A"
                )
                excl_disp['Data Confidence'] = excl_disp['data_confidence'].fillna("N/A")
                excl_disp = excl_disp.rename(columns={
                    'ticker': 'Ticker',
                    'failed_reason': 'Failed Reason',
                })
                reason_counts = excl_disp['Failed Reason'].value_counts()
                cols = st.columns(min(len(reason_counts), 4))
                for i, (reason, count) in enumerate(reason_counts.items()):
                    with cols[i % len(cols)]:
                        st.metric(reason, count)
                st.dataframe(
                    excl_disp[[
                        'Ticker', 'Final Score', 'Opportunity Score', 'Prediction Score',
                        'Future Catalyst Score', 'Days Until Earnings', 'Data Confidence', 'Failed Reason',
                    ]],
                    hide_index=True,
                    use_container_width=True,
                )

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
                tags_str = ticker_row.get('Research Tags')
                if tags_str:
                    st.write(" ".join(f"`{tag}`" for tag in tags_str.split(", ")))
                
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
            
            # Expander for Research Score Breakdown
            breakdown = ticker_row.get('Research Score Breakdown')
            if isinstance(breakdown, dict):
                with st.expander("🔬 Research Score Breakdown", expanded=True):
                    col_inc, col_pen = st.columns(2)
                    with col_inc:
                        st.markdown("##### 🟢 Score Drivers / Positive Factors")
                        if breakdown.get('increases'):
                            for item in breakdown['increases']:
                                st.markdown(f"- {item}")
                        else:
                            st.write("No major scoring boosters detected.")
                            
                    with col_pen:
                        st.markdown("##### 🔴 Risk Factors / Penalties")
                        if breakdown.get('penalties'):
                            for item in breakdown['penalties']:
                                st.markdown(f"- {item}")
                        else:
                            st.write("No major scoring penalties or risk factors detected.")
                            
                    col_warn, col_missing = st.columns(2)
                    with col_warn:
                        st.markdown("##### ⚠️ Warnings & Special Situations")
                        if breakdown.get('warnings'):
                            for item in breakdown['warnings']:
                                st.warning(item)
                        else:
                            st.write("No warnings flagged.")
                            
                    with col_missing:
                        st.markdown("##### 🔍 Missing/Fallback Inputs")
                        if breakdown.get('missing_inputs'):
                            for item in breakdown['missing_inputs']:
                                st.info(f"Missing data fallback used for: **{item}**")
                        else:
                            st.write("All scoring input parameters successfully loaded.")

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
        _ds_loaded = st.session_state.get('deep_scan_loaded', False)

        if not _ds_loaded:
            st.markdown("### 📋 Step 2: Select Catalyst Candidates for Batched Deep Scan")
            render_true_funnel_metrics(st.session_state.get('funnel_metrics', {}))
            st.write("Review the top candidates ranked by Fast Scan RVOL and Momentum. Check the symbols you wish to deep-scan in batches.")

            fast_df = pd.DataFrame(st.session_state.fast_scan_candidates)
            fast_df['Select'] = True

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

            if st.button("📦 Load Selected Candidates for Batched Deep Scan", use_container_width=True):
                if not selected_tickers:
                    st.error("Please select at least 1 candidate ticker to deep scan.")
                else:
                    selected_candidates = [c for c in st.session_state.fast_scan_candidates if c['ticker'] in selected_tickers]
                    init_deep_scan_session_state(force_reset=True)
                    init_api_telemetry(force_reset=True)
                    st.session_state.deep_scan_full_candidate_list = selected_candidates
                    st.session_state.deep_scan_pending_tickers = list(selected_candidates)
                    st.session_state.deep_scan_loaded = True
                    merge_funnel_metrics({'deep_scan_input_count': len(selected_candidates)})
                    st.success(f"Loaded {len(selected_candidates):,} candidates for batched deep scanning. Use sidebar controls to process batches.")
                    safe_rerun()

        if _ds_loaded:
            st.markdown("### 📋 Batched Deep Scan Progress")

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
                st.markdown(f"#### 📊 Current Cumulative Results ({scored} scored)")
                preview = cumul_df.sort_values('Final Score', ascending=False).head(10)
                display_cols = ['Ticker', 'Final Score', 'Research Priority Score', 'Opportunity Score', 'Prediction Score']
                available_cols = [c for c in display_cols if c in preview.columns]
                preview_disp = preview[available_cols].copy()
                st.dataframe(preview_disp, hide_index=True, use_container_width=True)
                if 'Research Priority Score' not in cumul_df.columns:
                    st.info("💡 Some new scoring metrics are missing from the current session cache. Click '📦 Load Selected Candidates' above to restart with full metrics.")
                st.caption("Top 10 by Final Score so far. Use sidebar controls to process more batches or build the final leaderboard.")

            if batch_telem_list:
                st.markdown("#### 📈 Batch Telemetry")
                telem_df = pd.DataFrame(batch_telem_list)
                telem_display_cols = [
                    'batch_number', 'batch_size', 'tickers_succeeded', 'tickers_failed',
                    'rate_limit_429_count', 'http_failure_count', 'runtime_seconds',
                    'cumulative_completed', 'cumulative_pending'
                ]
                telem_df = telem_df[[c for c in telem_display_cols if c in telem_df.columns]]
                st.dataframe(telem_df, hide_index=True, use_container_width=True)

            if failed_list:
                with st.expander(f"❌ Failed Tickers ({len(failed_list)})"):
                    fail_df = pd.DataFrame(failed_list)
                    st.dataframe(fail_df, hide_index=True, use_container_width=True)

            if not pending and not run_all_active:
                st.success("✅ All batches completed! Click 'Build Final Leaderboard From Completed Batches' in the sidebar to view results.")

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

# ----------------------------------------------------
# TAB 3: HISTORICAL EARNINGS EVENT LAB
# ----------------------------------------------------
with tab_lab:
    show_historical_event_lab_ui(is_tab=True)

"""Historical Market Replay Mode — replays the live Catalyst Scanner pipeline on any historical date.

Eliminates selection bias by starting from the full stock universe and filtering down,
exactly as the live screener does. Supports Single-Date Replay and Weekly Batch Replay.
"""
import os
import time
import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Backend modules
import historical_data_fetch as fetch
import historical_feature_engineering as eng
import historical_scoring as score
import historical_results_store as store

# ── Universe options ────────────────────────────────────────────────────
UNIVERSE_OPTIONS = {
    "Full Market Universe": "data/us_stock_universe.csv",
    "Test Universe": "test_universe.csv",
    "Quick Test (first 200)": "test_universe.csv",
    "Speed Test (first 50)": "test_universe.csv",
}

UNIVERSE_LIMITS = {
    "Full Market Universe": None,
    "Test Universe": None,
    "Quick Test (first 200)": 200,
    "Speed Test (first 50)": 50,
}


# ── Outcome labelling helpers ───────────────────────────────────────────
def label_earnings_outcome(row, threshold):
    r1 = row.get("Post_1D_Return")
    if r1 is None:
        return "No Data"
    if r1 >= threshold:
        return "Big Move Up"
    elif r1 <= -threshold:
        return "Big Move Down"
    elif abs(r1) >= 5.0:
        return "Moderate Move"
    return "No Meaningful Move"


def label_multi_day_pattern(row):
    r1 = row.get("Post_1D_Return")
    r3 = row.get("Post_3D_Return")
    r5 = row.get("Post_5D_Return")
    gap = row.get("Gap_Percent")
    if r1 is None:
        return "N/A"
    labels = []
    if r1 > 0:
        if r3 is not None and r3 > r1 + 2.0:
            labels.append("3D continuation up")
        if r5 is not None and r5 > r1 + 3.0:
            labels.append("5D continuation up")
    elif r1 < 0:
        if r3 is not None and r3 < r1 - 2.0:
            labels.append("3D continuation down")
        if r5 is not None and r5 < r1 - 3.0:
            labels.append("5D continuation down")
    if gap is not None and abs(gap) >= 1.5:
        if gap > 0 and r1 < gap - 2.0:
            labels.append("gap-and-fade")
        elif gap < 0 and r1 > gap + 2.0:
            labels.append("gap-and-fade")
        elif gap * r1 > 0 and abs(r1) >= abs(gap):
            labels.append("gap-and-go")
    return ", ".join(labels) if labels else "Neutral"


def label_research_archetype(row):
    r1 = row.get("Post_1D_Return")
    setup = row.get("Expectation_Setup_Score")
    ru_risk = row.get("Run_Up_Risk_Score")
    cf_score = row.get("Cash_Flow_Quality_Score")
    guid_score = row.get("Guidance_Sensitivity_Score")
    sq_score = row.get("Short_Squeeze_Quality_Score")
    if r1 is None:
        return "Neutral / Mixed"
    if setup is not None and setup <= 30.0 and sq_score is not None and sq_score >= 60.0 and r1 >= 8.0:
        return "Low Expectation Squeeze"
    elif ru_risk is not None and ru_risk >= 60.0 and r1 <= -8.0:
        return "Expectation Inflation Collapse"
    elif cf_score is not None and cf_score >= 75.0 and r1 >= 5.0:
        return "Cash Flow Quality Winner"
    elif guid_score is not None and guid_score >= 70.0 and r1 <= -5.0:
        return "Guidance Sensitivity Failure"
    elif cf_score is not None and cf_score <= 30.0 and r1 <= -5.0:
        return "Earnings Quality Failure"
    return "Neutral / Mixed"


# ── Core replay pipeline ────────────────────────────────────────────────
def _load_universe(universe_key: str) -> pd.DataFrame:
    """Load the stock universe CSV and optionally slice it."""
    path = UNIVERSE_OPTIONS[universe_key]
    if not os.path.exists(path):
        alt = "test_universe.csv" if "us_stock" in path else "data/us_stock_universe.csv"
        if os.path.exists(alt):
            path = alt
        else:
            return pd.DataFrame(columns=["Symbol", "CIK"])
    df = pd.read_csv(path)
    limit = UNIVERSE_LIMITS.get(universe_key)
    if limit:
        df = df.head(limit)
    return df


def run_single_date_replay(
    run_date: datetime.date,
    universe_df: pd.DataFrame,
    top_n: int = 20,
    min_mc: int = 50_000_000,
    min_vol: int = 500_000,
    mode: str = "Strict",
    big_move_threshold: float = 8.0,
    rank_by: str = "Final_Score",
    progress_callback=None,
    save_n: int = 0,
) -> tuple:
    """Replay the scanner pipeline on *run_date* across the entire universe.

    Args:
        save_n: Max candidates to return (0 = all scored candidates).

    Returns:
        (DataFrame, diagnostics_dict) tuple.
        DataFrame contains scored candidates sorted by *rank_by* desc,
        truncated to save_n if save_n > 0.
    """
    R = run_date
    R_plus_30 = R + datetime.timedelta(days=30)
    all_rows = []
    total = len(universe_df)

    diagnostics = {
        "universe_size": total,
        "earnings_eligible": 0,
        "price_vol_survivors": 0,
        "scored_count": 0,
        "saved_count": 0,
        "cap_used": "All" if save_n <= 0 else save_n,
    }

    if total == 0:
        return pd.DataFrame(), diagnostics

    tickers = [str(urow["Symbol"]).strip().upper() for _, urow in universe_df.iterrows()]
    ticker_to_cik = {
        str(urow["Symbol"]).strip().upper(): (
            str(int(urow["CIK"])).zfill(10)
            if pd.notnull(urow.get("CIK"))
            else None
        )
        for _, urow in universe_df.iterrows()
    }

    # ── Phase 1: check upcoming earnings in parallel ──
    if progress_callback:
        progress_callback(1, total, "Universe", "Phase 1: checking earnings & proxy dates...")

    def _earnings_cb(phase, done, total_cnt, msg):
        if progress_callback:
            val = int((done / total_cnt) * (total // 3)) if total_cnt > 0 else 0
            progress_callback(max(1, val), total, "Universe", msg)

    tickers_with_cik = [(t, ticker_to_cik[t]) for t in tickers]
    event_map = fetch.parallel_fetch_all_event_dates(tickers_with_cik, callback=_earnings_cb)

    active_candidates = []
    for ticker in tickers:
        dates, is_proxy = event_map.get(ticker, ([], False))
        if not dates:
            continue

        upcoming = sorted([d for d in dates if R <= d <= R_plus_30])
        if upcoming:
            active_candidates.append({
                "ticker": ticker,
                "cik": ticker_to_cik.get(ticker),
                "event_date": upcoming[0],
                "is_proxy": is_proxy,
                "earnings_dates": dates,
            })

    diagnostics["earnings_eligible"] = len(active_candidates)

    if not active_candidates:
        if progress_callback:
            progress_callback(total, total, "Universe", "Done (no candidates)")
        return pd.DataFrame(), diagnostics

    # ── Phase 2: batch download prices for active candidates ──
    active_tickers = [c["ticker"] for c in active_candidates]
    if progress_callback:
        progress_callback(total // 3, total, "Universe", f"Phase 2: downloading prices for {len(active_tickers)} tickers...")

    def _download_cb(phase, done, total_cnt, msg):
        if progress_callback:
            start_val = total // 3
            span = total // 3
            val = start_val + int((done / total_cnt) * span) if total_cnt > 0 else 0
            progress_callback(max(start_val, val), total, "Universe", msg)

    prices_map = fetch.batch_download_prices(active_tickers, callback=_download_cb)

    surviving_candidates = []
    for cand in active_candidates:
        t = cand["ticker"]
        prices_df = prices_map.get(t)
        if prices_df is None or prices_df.empty:
            continue

        tech = eng.calculate_pre_event_technicals(prices_df, R)
        if tech["Price_T_minus_1"] is None:
            continue

        price_t1 = tech["Price_T_minus_1"]
        if price_t1 < 2.0:
            continue

        # Liquidity filter
        event_ts = pd.to_datetime(R).tz_localize(None)
        df_pre = prices_df[prices_df.index < event_ts]
        avg_vol_20d = (
            float(df_pre["Volume"].tail(20).mean())
            if "Volume" in df_pre.columns and len(df_pre) >= 20
            else 0.0
        )
        if avg_vol_20d < min_vol:
            continue

        cand["tech"] = tech
        cand["price_t1"] = price_t1
        cand["avg_vol_20d"] = avg_vol_20d
        cand["prices_df"] = prices_df
        surviving_candidates.append(cand)

    diagnostics["price_vol_survivors"] = len(surviving_candidates)

    if not surviving_candidates:
        if progress_callback:
            progress_callback(total, total, "Universe", "Done (no survivors)")
        return pd.DataFrame(), diagnostics

    # ── Phase 3: batch fetch SEC facts for surviving candidates ──
    sec_targets = [(c["ticker"], c["cik"]) for c in surviving_candidates]
    if progress_callback:
        progress_callback(2 * total // 3, total, "Universe", f"Phase 3: fetching SEC facts for {len(sec_targets)} survivors...")

    def _sec_cb(phase, done, total_cnt, msg):
        if progress_callback:
            start_val = 2 * total // 3
            span = total - start_val - 5
            val = start_val + int((done / total_cnt) * span) if total_cnt > 0 else 0
            progress_callback(max(start_val, val), total, "Universe", msg)

    sec_map = fetch.batch_fetch_sec_facts(sec_targets, callback=_sec_cb)

    # ── Phase 4: Reconstruct point-in-time scoring & outcomes ──
    for idx, cand in enumerate(surviving_candidates):
        t = cand["ticker"]
        cik = cand["cik"]
        tech = cand["tech"]
        price_t1 = cand["price_t1"]
        avg_vol_20d = cand["avg_vol_20d"]
        prices_df = cand["prices_df"]
        ED = cand["event_date"]
        is_proxy = cand["is_proxy"]
        earnings_dates = cand["earnings_dates"]

        if progress_callback:
            progress_callback(total - 5 + int((idx / len(surviving_candidates)) * 5), total, t, "scored")

        sec_facts = sec_map.get(t, {})
        shares = eng.get_shares_outstanding_on_date(sec_facts, R)
        if shares is None:
            shares = 20_000_000
        mc_val = shares * price_t1
        if mc_val < min_mc:
            continue

        fund = eng.reconstruct_point_in_time_fundamentals(sec_facts, R)
        reactions = eng.reconstruct_historical_earnings_reactions(
            earnings_dates, prices_df, R
        )
        static_meta = {
            "Sector": None,
            "Industry": None,
            "Market_Cap": mc_val,
            "Float_Shares": shares * 0.8,
            "Short_Percent": None,
            "Analysts": None,
        }
        scores = score.calculate_historical_scores(
            tech, fund, reactions, static_meta, mode, is_proxy
        )

        outcomes = eng.calculate_post_event_outcomes(prices_df, ED)

        record = {
            "Ticker": t,
            "Scan_Date": R.strftime("%Y-%m-%d"),
            "Earnings_Date": ED.strftime("%Y-%m-%d"),
            "Days_Until": (ED - R).days,
            "Is_Proxy": "Yes" if is_proxy else "No",
            "Price_Scan": round(price_t1, 2),
            "Market_Cap": mc_val,
            "Avg_Vol_20d": round(avg_vol_20d),
            "RVOL": round(tech["RVOL"], 2) if tech["RVOL"] is not None else None,
            "RSI": round(tech["RSI"], 1),
            "ATR_Pct": round(tech["ATR_Pct"], 2),
            "Gap_Frequency": round(tech["Gap_Frequency"], 1),
            "Volatility": round(tech["Volatility"], 1),
            "Pre_30D_Return": (
                round(tech["Pre_30D_Return"], 2)
                if tech["Pre_30D_Return"] is not None
                else None
            ),
            "Gap_Percent": (
                round(outcomes["Gap_Percent"], 2)
                if outcomes["Gap_Percent"] is not None
                else None
            ),
            "Post_1D_Return": (
                round(outcomes["Post_1D_Return"], 2)
                if outcomes["Post_1D_Return"] is not None
                else None
            ),
            "Post_3D_Return": (
                round(outcomes["Post_3D_Return"], 2)
                if outcomes["Post_3D_Return"] is not None
                else None
            ),
            "Post_5D_Return": (
                round(outcomes["Post_5D_Return"], 2)
                if outcomes["Post_5D_Return"] is not None
                else None
            ),
            "Absolute_1D_Move": (
                round(outcomes["Absolute_1D_Move"], 2)
                if outcomes["Absolute_1D_Move"] is not None
                else None
            ),
            "Max_Favorable_Move": round(outcomes["Max_Favorable_Move"], 2),
            "Max_Adverse_Move": round(outcomes["Max_Adverse_Move"], 2),
            "Volume_Spike_Day_0": (
                round(outcomes["Volume_Spike_Day_0"], 2)
                if outcomes["Volume_Spike_Day_0"] is not None
                else None
            ),
            "Opportunity_Score": scores["Opportunity_Score"],
            "Prediction_Score": scores["Prediction_Score"],
            "Final_Score": scores["Final_Score"],
            "Run_Up_Risk_Score": scores["Run_Up_Risk_Score"],
            "Expectation_Setup_Score": scores["Expectation_Setup_Score"],
            "Cash_Flow_Quality_Score": scores["Cash_Flow_Quality_Score"],
            "Guidance_Sensitivity_Score": scores["Guidance_Sensitivity_Score"],
            "Short_Squeeze_Quality_Score": scores["Short_Squeeze_Quality_Score"],
            "Event_Potential_Score": scores["Event_Potential_Score"],
            "Research_Priority_Score": scores["Research_Priority_Score"],
            "Directional_Edge_Score_V1": scores.get("Directional_Edge_Score_V1"),
            "Directional_Probability_Score": scores.get("Directional_Probability_Score"),
            "Directional_Bias": scores.get("Directional_Bias"),
            "Directional_Archetype": scores.get("Directional_Archetype"),
            "Research_Tags": ", ".join(scores["Research_Tags"]),
            "Confidence_Flag": scores["Confidence_Flag"],
            "Notes": "; ".join(scores["Warnings"]) if scores["Warnings"] else "Strict PIT OK",
        }

        record["Label"] = label_earnings_outcome(record, big_move_threshold)
        record["Patterns"] = label_multi_day_pattern(record)
        record["Archetype"] = label_research_archetype(record)

        all_rows.append(record)

    if progress_callback:
        progress_callback(total, total, "Universe", "Scoring complete!")

    if not all_rows:
        return pd.DataFrame(), diagnostics

    df = pd.DataFrame(all_rows)
    df.sort_values(rank_by, ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)

    diagnostics["scored_count"] = len(df)

    # Apply save_n cap (0 = return all)
    if save_n > 0 and len(df) > save_n:
        df = df.head(save_n).copy()

    diagnostics["saved_count"] = len(df)
    return df, diagnostics


# ── Streamlit UI ────────────────────────────────────────────────────────

_KPI_CSS = """
<style>
.kpi-container {
    display: flex; gap: 14px; margin-bottom: 22px; flex-wrap: wrap;
}
.kpi-card {
    flex: 1; min-width: 170px;
    background: linear-gradient(135deg, rgba(20,24,41,0.92) 0%, rgba(8,12,24,0.92) 100%);
    border: 1px solid rgba(139,92,246,0.12);
    border-left: 4px solid #8b5cf6;
    border-radius: 12px; padding: 18px 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
    backdrop-filter: blur(6px);
    transition: transform 0.2s, border-color 0.2s;
}
.kpi-card:hover { transform: translateY(-2px); border-color: rgba(139,92,246,0.4); }
.kpi-title {
    font-size: 0.78rem; color: #9ca3af; text-transform: uppercase;
    letter-spacing: 0.05em; margin-bottom: 5px; font-weight: 600;
}
.kpi-value { font-size: 1.65rem; font-weight: 800; color: #fff; }
.replay-badge {
    display: inline-block; padding: 3px 10px; border-radius: 6px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em;
    text-transform: uppercase; margin-right: 6px;
}
.badge-green  { background: rgba(16,185,129,0.18); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.badge-blue   { background: rgba(59,130,246,0.18); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
.badge-purple { background: rgba(139,92,246,0.18); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }
</style>
"""

_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#f3f4f6",
    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
)


def _kpi_html(title, value, accent="#8b5cf6"):
    return (
        f'<div class="kpi-card" style="border-left-color:{accent}">'
        f'<div class="kpi-title">{title}</div>'
        f'<div class="kpi-value">{value}</div></div>'
    )


def _render_summary_kpis(df, event_window_days, big_move_threshold):
    total = len(df)
    perf_col = f"Post_{event_window_days}D_Return"
    valid = df.dropna(subset=[perf_col])
    if valid.empty:
        return
    avg_move = valid[perf_col].mean()
    avg_abs = valid[perf_col].abs().mean()
    big_up = len(df[df["Post_1D_Return"] >= big_move_threshold]) / total * 100
    big_down = len(df[df["Post_1D_Return"] <= -big_move_threshold]) / total * 100
    big_any = len(df[df["Absolute_1D_Move"] >= big_move_threshold]) / total * 100

    html = '<div class="kpi-container">'
    html += _kpi_html("Total Candidates", f"{total:,}")
    html += _kpi_html(f"Avg {event_window_days}D Return", f"{avg_move:+.2f}%", "#3b82f6")
    html += _kpi_html(f"Avg Abs {event_window_days}D", f"{avg_abs:.2f}%", "#3b82f6")
    html += _kpi_html(f"Big Moves (≥{big_move_threshold}%)", f"{big_any:.1f}%", "#10b981")
    html += _kpi_html("Big UP", f"{big_up:.1f}%", "#10b981")
    html += _kpi_html("Big DOWN", f"{big_down:.1f}%", "#ef4444")
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ── Results tabs ────────────────────────────────────────────────────────

def _render_setup_explorer(df_results, perf_col, big_move_threshold):
    st.markdown("#### 🔍 Conditional Setup Explorer")
    exp_col1, exp_col2 = st.columns([1, 3])
    with exp_col1:
        st.markdown("##### Score Filters")
        f_final = st.slider("Final Score ≥", 0, 100, 0, key="rex_final")
        f_runup = st.slider("Run-Up Risk ≥", 0, 100, 0, key="rex_runup")
        f_setup = st.slider("Expectation Setup ≥", 0, 100, 0, key="rex_setup")
        f_cf = st.slider("Cash Flow Quality ≥", 0, 100, 0, key="rex_cf")
        f_guid = st.slider("Guidance Sensitivity ≥", 0, 100, 0, key="rex_guid")
        f_rsi = st.slider("RSI ≥", 0, 100, 0, key="rex_rsi")
        f_rvol = st.slider("RVOL ≥", 0.0, 10.0, 0.0, step=0.5, key="rex_rvol")

    with exp_col2:
        df_f = df_results.copy()
        if f_final > 0:
            df_f = df_f[df_f["Final_Score"] >= f_final]
        if f_runup > 0:
            df_f = df_f[df_f["Run_Up_Risk_Score"] >= f_runup]
        if f_setup > 0:
            df_f = df_f[df_f["Expectation_Setup_Score"] >= f_setup]
        if f_cf > 0:
            df_f = df_f[df_f["Cash_Flow_Quality_Score"] >= f_cf]
        if f_guid > 0:
            df_f = df_f[df_f["Guidance_Sensitivity_Score"] >= f_guid]
        if f_rsi > 0:
            df_f = df_f[df_f["RSI"] >= f_rsi]
        if f_rvol > 0:
            df_f = df_f[df_f["RVOL"] >= f_rvol]

        st.markdown(f"##### Filtered: {len(df_f)} / {len(df_results)} events")
        if df_f.empty:
            st.info("No events match the selected criteria.")
        else:
            v = df_f[perf_col].dropna()
            if not v.empty:
                m1, m2, m3 = st.columns(3)
                m1.metric("Avg Return", f"{v.mean():+.2f}%")
                m2.metric("Median Return", f"{v.median():+.2f}%")
                m3.metric("Avg Abs Move", f"{v.abs().mean():.2f}%")

                m4, m5, m6 = st.columns(3)
                m4.metric("% Big Up", f"{len(df_f[df_f['Post_1D_Return'] >= big_move_threshold]) / len(df_f) * 100:.1f}%")
                m5.metric("% Big Down", f"{len(df_f[df_f['Post_1D_Return'] <= -big_move_threshold]) / len(df_f) * 100:.1f}%")
                m6.metric("% No Move (<5%)", f"{len(df_f[df_f['Absolute_1D_Move'] < 5.0]) / len(df_f) * 100:.1f}%")

            fig = px.histogram(
                df_f, x=perf_col, nbins=20,
                title=f"Distribution of Post-Earnings {perf_col.replace('Post_','').replace('_Return','')} Returns",
                labels={perf_col: "Return (%)"},
                color_discrete_sequence=["#a78bfa"],
            )
            fig.update_layout(**_PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)


def _render_factor_importance(df_results):
    st.markdown("#### 🧬 Factor Importance & Correlation Analysis")
    feat_cols = [
        "Final_Score", "Opportunity_Score", "Prediction_Score",
        "Run_Up_Risk_Score", "Expectation_Setup_Score", "Cash_Flow_Quality_Score",
        "Guidance_Sensitivity_Score", "Short_Squeeze_Quality_Score", "Event_Potential_Score",
        "RVOL", "RSI", "ATR_Pct", "Gap_Frequency", "Volatility", "Pre_30D_Return",
    ]
    num_cols = [c for c in feat_cols if c in df_results.columns]
    target_cols = ["Absolute_1D_Move", "Post_1D_Return"]
    avail = [c for c in target_cols if c in df_results.columns]
    df_c = df_results[num_cols + avail].dropna()
    if df_c.empty or len(df_c) < 5:
        st.info("Insufficient data to calculate correlations (need ≥5 valid rows).")
        return

    corrs = {}
    for c in num_cols:
        corrs[c] = {
            "Corr_to_Abs_Move": df_c[c].corr(df_c["Absolute_1D_Move"]) if "Absolute_1D_Move" in avail else 0,
            "Corr_to_Return": df_c[c].corr(df_c["Post_1D_Return"]) if "Post_1D_Return" in avail else 0,
        }
    df_cr = pd.DataFrame(corrs).T.reset_index().rename(columns={"index": "Feature"})

    has_ml = False
    try:
        from sklearn.ensemble import RandomForestRegressor
        X = df_c[num_cols]
        y = df_c["Absolute_1D_Move"]
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X, y)
        df_cr["ML_Importance"] = rf.feature_importances_
        has_ml = True
    except Exception:
        pass

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(
            df_cr.sort_values("Corr_to_Abs_Move", ascending=False),
            y="Feature", x="Corr_to_Abs_Move", orientation="h",
            title="Correlation → Absolute Move Size",
            color_discrete_sequence=["#8b5cf6"],
        )
        fig.update_layout(**_PLOTLY_LAYOUT, yaxis_showgrid=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        if has_ml:
            fig = px.bar(
                df_cr.sort_values("ML_Importance", ascending=False),
                y="Feature", x="ML_Importance", orientation="h",
                title="Random Forest Feature Importance",
                color_discrete_sequence=["#3b82f6"],
            )
        else:
            fig = px.bar(
                df_cr.sort_values("Corr_to_Return", ascending=False),
                y="Feature", x="Corr_to_Return", orientation="h",
                title="Correlation → Directional Return",
                color_discrete_sequence=["#10b981"],
            )
        fig.update_layout(**_PLOTLY_LAYOUT, yaxis_showgrid=False)
        st.plotly_chart(fig, use_container_width=True)

    # Quartile analysis
    st.markdown("##### Quartile Bin Analysis")
    bin_data = []
    for col in ["Final_Score", "Run_Up_Risk_Score", "Cash_Flow_Quality_Score", "RVOL"]:
        if col not in df_c.columns:
            continue
        try:
            df_c["_Q"] = pd.qcut(df_c[col], 4, labels=["Q1 (Low)", "Q2", "Q3", "Q4 (High)"], duplicates="drop")
            grouped = df_c.groupby("_Q")["Absolute_1D_Move"].mean().to_dict()
            row_b = {"Factor": col}
            row_b.update(grouped)
            bin_data.append(row_b)
        except Exception:
            pass
    if bin_data:
        st.dataframe(pd.DataFrame(bin_data), hide_index=True, use_container_width=True)


def _render_event_table(df_results, big_move_threshold=8.0):
    st.markdown("#### 📋 Detailed Event Table")
    
    df = df_results.copy()
    if df.empty:
        st.info("No data to show.")
        return
        
    # Filters
    st.markdown("##### Filter Dataset")
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        f_ticker = st.text_input("Ticker Search (comma-separated)", "").strip().upper()
        
        # Scan date range
        if "Scan_Date" in df.columns:
            df["_dt_scan"] = pd.to_datetime(df["Scan_Date"])
            sd_min = df["_dt_scan"].min().date()
            sd_max = df["_dt_scan"].max().date()
            f_scan_range = st.date_input("Scan Date Range", [sd_min, sd_max])
        else:
            f_scan_range = None
            
    with f_col2:
        # Score range
        if "Final_Score" in df.columns:
            f_score_min = int(df["Final_Score"].min())
            f_score_max = int(df["Final_Score"].max())
            f_score_range = st.slider("Score Range Filter", f_score_min, f_score_max, (f_score_min, f_score_max))
        else:
            f_score_range = None
            
        # Earnings date range
        if "Earnings_Date" in df.columns:
            df["_dt_earn"] = pd.to_datetime(df["Earnings_Date"])
            ed_min = df["_dt_earn"].min().date()
            ed_max = df["_dt_earn"].max().date()
            f_earnings_range = st.date_input("Earnings Date Range", [ed_min, ed_max])
        else:
            f_earnings_range = None
            
    with f_col3:
        # Archetype
        if "Archetype" in df.columns:
            archs = ["All"] + sorted(list(df["Archetype"].dropna().unique()))
            f_arch = st.selectbox("Archetype Filter", archs)
        else:
            f_arch = "All"
            
        # Confidence Flag
        if "Confidence_Flag" in df.columns:
            flags = ["All"] + sorted(list(df["Confidence_Flag"].dropna().unique()))
            f_flag = st.selectbox("Confidence Flag Filter", flags)
        else:
            f_flag = "All"
            
        f_big_only = st.checkbox(f"Big Moves Only (≥{big_move_threshold}%)", value=False)
        
    # Apply filters
    if f_ticker:
        tickers = [t.strip() for t in f_ticker.split(",") if t.strip()]
        if tickers:
            df = df[df["Ticker"].isin(tickers)]
            
    if f_score_range and "Final_Score" in df.columns:
        df = df[(df["Final_Score"] >= f_score_range[0]) & (df["Final_Score"] <= f_score_range[1])]
        
    if f_scan_range and len(f_scan_range) == 2 and "_dt_scan" in df.columns:
        s_start, s_end = pd.to_datetime(f_scan_range[0]), pd.to_datetime(f_scan_range[1])
        df = df[(df["_dt_scan"] >= s_start) & (df["_dt_scan"] <= s_end)]
        
    if f_earnings_range and len(f_earnings_range) == 2 and "_dt_earn" in df.columns:
        e_start, e_end = pd.to_datetime(f_earnings_range[0]), pd.to_datetime(f_earnings_range[1])
        df = df[(df["_dt_earn"] >= e_start) & (df["_dt_earn"] <= e_end)]
        
    if f_arch != "All" and "Archetype" in df.columns:
        df = df[df["Archetype"] == f_arch]
        
    if f_flag != "All" and "Confidence_Flag" in df.columns:
        df = df[df["Confidence_Flag"] == f_flag]
        
    if f_big_only:
        abs_col = "Absolute_1D_Move"
        perf_col = "Post_1D_Return"
        if perf_col in df.columns:
            if abs_col not in df.columns:
                df[abs_col] = df[perf_col].abs()
            df = df[df[abs_col] >= big_move_threshold]

    # Cleanup temp columns
    for tc in ["_dt_scan", "_dt_earn"]:
        if tc in df.columns:
            df = df.drop(columns=[tc])

    # Show count
    st.markdown(f"**Filtered Results Count**: {len(df):,}")
    
    # Memory and rendering safety check
    is_large = len(df) > 5000
    if is_large:
        st.warning(f"⚠️ Dataset is large ({len(df):,} rows). Displaying the first **500** rows only for performance safety.")
        df_display = df.head(500)
    else:
        df_display = df
        
    cols_show = [
        "Ticker", "Scan_Date", "Earnings_Date", "Days_Until", "Price_Scan",
        "Final_Score", "Research_Priority_Score",
        "Directional_Edge_Score_V1", "Directional_Probability_Score", "Directional_Bias", "Directional_Archetype",
        "Run_Up_Risk_Score", "Expectation_Setup_Score",
        "Cash_Flow_Quality_Score", "Guidance_Sensitivity_Score",
        "Short_Squeeze_Quality_Score",
        "Post_1D_Return", "Post_3D_Return", "Post_5D_Return", "Absolute_1D_Move",
        "Label", "Patterns", "Archetype", "Confidence_Flag", "Notes",
    ]
    avail = [c for c in cols_show if c in df_display.columns]
    
    st.dataframe(df_display[avail], use_container_width=True, hide_index=True)
    
    # Export options
    st.markdown("##### 📥 Export Filtered Dataset")
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Filtered Results as CSV",
        data=csv_data,
        file_name="replay_filtered_results.csv",
        mime="text/csv",
        key="download_filtered_btn"
    )


def _render_portfolio_chart(df_results, top_n, rank_by):
    """Cumulative portfolio chart for Weekly Batch mode."""
    if "Scan_Date" not in df_results.columns or df_results.empty:
        return

    weeks = sorted(df_results["Scan_Date"].unique())
    if len(weeks) < 2:
        return

    st.markdown("#### 📈 Cumulative Portfolio Performance (Equal-Weight Top N)")
    cum_return = 1.0
    series = []
    for w in weeks:
        wk_df = df_results[df_results["Scan_Date"] == w].head(top_n)
        valid = wk_df.dropna(subset=["Post_1D_Return"])
        if valid.empty:
            weekly_ret = 0.0
        else:
            weekly_ret = valid["Post_1D_Return"].mean()
        cum_return *= 1 + weekly_ret / 100.0
        series.append({"Week": w, "Cumulative_Return": (cum_return - 1) * 100})

    df_s = pd.DataFrame(series)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_s["Week"], y=df_s["Cumulative_Return"],
        mode="lines+markers",
        line=dict(color="#a78bfa", width=3),
        marker=dict(size=6, color="#8b5cf6"),
        name="Top N Portfolio",
        fill="tozeroy",
        fillcolor="rgba(139,92,246,0.08)",
    ))
    fig.update_layout(
        title=f"Cumulative Return — Top {top_n} by {rank_by} (Weekly Rebalance)",
        xaxis_title="Replay Week",
        yaxis_title="Cumulative Return (%)",
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary stats
    total_weeks = len(series)
    final_cum = series[-1]["Cumulative_Return"]
    avg_weekly = np.mean([s["Cumulative_Return"] for s in series]) if series else 0
    wins = sum(1 for i, s in enumerate(series) if i == 0 and s["Cumulative_Return"] > 0 or i > 0 and s["Cumulative_Return"] > series[i - 1]["Cumulative_Return"])
    win_rate = wins / total_weeks * 100 if total_weeks > 0 else 0

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Total Weeks", total_weeks)
    sc2.metric("Final Cumulative Return", f"{final_cum:+.2f}%")
    sc3.metric("Win Rate (weekly)", f"{win_rate:.1f}%")
    sc4.metric("Avg Weekly Return", f"{np.mean([wk_df.dropna(subset=['Post_1D_Return'])['Post_1D_Return'].mean() for w in weeks for wk_df in [df_results[df_results['Scan_Date'] == w].head(top_n)] if not wk_df.dropna(subset=['Post_1D_Return']).empty] or [0]):+.2f}%")


def _render_score_threshold_validation(df_results, big_move_threshold):
    st.markdown("#### 📊 Score Threshold Validation")
    st.markdown(
        "Evaluate whether higher scores correlate with larger post-earnings moves "
        "and determine statistical significance."
    )
    
    # 1. Prepare data
    df = df_results.copy()
    if df.empty:
        st.info("No data available.")
        return
        
    perf_col = "Post_1D_Return"
    abs_col = "Absolute_1D_Move"
    if perf_col not in df.columns:
        st.info("Missing Post_1D_Return in results.")
        return
        
    # Standardize Absolute_1D_Move if not present
    if abs_col not in df.columns or df[abs_col].isnull().all():
        df[abs_col] = df[perf_col].abs()
        
    # Remove NaN values in performance column to have fair calculations
    df = df.dropna(subset=[perf_col])
    if df.empty:
        st.info("No valid post-earnings returns to analyze.")
        return
        
    baseline_avg_abs = df[abs_col].mean()
    
    thresholds = ["All Events", ">= 60", ">= 65", ">= 70", ">= 75", ">= 80", ">= 85", ">= 90"]
    rows = []
    
    for t in thresholds:
        if t == "All Events":
            sub_df = df
        else:
            try:
                val = float(t.replace(">=", "").strip())
                sub_df = df[df["Final_Score"] >= val]
            except Exception:
                sub_df = df
            
        count = len(sub_df)
        if count > 0:
            avg_ret = sub_df[perf_col].mean()
            avg_abs = sub_df[abs_col].mean()
            big_moves = len(sub_df[sub_df[abs_col] >= big_move_threshold]) / count * 100
            big_up = len(sub_df[sub_df[perf_col] >= big_move_threshold]) / count * 100
            big_down = len(sub_df[sub_df[perf_col] <= -big_move_threshold]) / count * 100
            
            # Lift vs Baseline
            if baseline_avg_abs > 0:
                lift = (avg_abs / baseline_avg_abs - 1) * 100
                lift_str = f"{lift:+.1f}%"
            else:
                lift_str = "0.0%"
        else:
            avg_ret = 0.0
            avg_abs = 0.0
            big_moves = 0.0
            big_up = 0.0
            big_down = 0.0
            lift_str = "N/A"
            
        # Sample size warnings
        if count < 10:
            warning = "🚨 Extremely Small Sample"
        elif count < 20:
            warning = "⚠️ Small Sample Size"
        else:
            warning = "✅ Adequate Sample"
            
        rows.append({
            "Final Score Threshold": t,
            "Events": count,
            "Avg 1D Return": f"{avg_ret:+.2f}%" if count > 0 else "N/A",
            "Avg Abs 1D Move": f"{avg_abs:.2f}%" if count > 0 else "N/A",
            f"% Big Moves (≥{big_move_threshold}%)": f"{big_moves:.1f}%" if count > 0 else "N/A",
            "% Big Up": f"{big_up:.1f}%" if count > 0 else "N/A",
            "% Big Down": f"{big_down:.1f}%" if count > 0 else "N/A",
            "Lift vs Baseline": lift_str,
            "Sample Quality": warning
        })
        
    df_table = pd.DataFrame(rows)
    st.dataframe(df_table, use_container_width=True, hide_index=True)

    # 2. Add Visualization
    chart_data = []
    for r in rows:
        if r["Final Score Threshold"] == "All Events" or r["Avg Abs 1D Move"] == "N/A":
            continue
        try:
            val = float(r["Avg Abs 1D Move"].replace("%", ""))
            chart_data.append({
                "Final Score Threshold": r["Final Score Threshold"],
                "Average Absolute Move": val
            })
        except Exception:
            pass

    if chart_data:
        df_chart = pd.DataFrame(chart_data)
        fig = px.line(
            df_chart, x="Final Score Threshold", y="Average Absolute Move",
            title="Final Score Threshold vs Average Absolute Move",
            markers=True,
            color_discrete_sequence=["#a78bfa"],
        )
        fig.update_layout(**_PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    # 3. Bonus Section: Top Performing Score Range
    buckets = [
        ("60 to 69", 60, 69),
        ("70 to 79", 70, 79),
        ("80 to 89", 80, 89),
        ("90 to 100", 90, 100)
    ]
    best_bucket = None
    best_avg_abs = -1.0
    best_count = 0
    best_big_rate = 0.0
    
    for name, low, high in buckets:
        sub = df[(df["Final_Score"] >= low) & (df["Final_Score"] <= high)]
        count = len(sub)
        if count >= 5:  # relaxed from 10 for smaller backtests, but fits general criteria
            avg_abs = sub[abs_col].mean()
            big_rate = len(sub[sub[abs_col] >= big_move_threshold]) / count * 100
            if avg_abs > best_avg_abs:
                best_avg_abs = avg_abs
                best_bucket = name
                best_count = count
                best_big_rate = big_rate

    st.markdown("##### 🏆 Top Performing Score Range")
    if best_bucket:
        st.info(
            f"Final Scores between **{best_bucket}** produced the highest average absolute move of "
            f"**{best_avg_abs:.2f}%** (with a **{best_big_rate:.1f}%** Big Move rate) "
            f"across **{best_count}** events."
        )
    else:
        st.info("Insufficient events across score ranges to determine the top performing range (needs at least 5 events in a range).")


def _render_score_range_validation(df_results, big_move_threshold):
    st.markdown("#### 🎯 Score Range Validation")
    df = df_results.copy()
    if df.empty:
        st.info("No data available.")
        return
        
    perf_col = "Post_1D_Return"
    abs_col = "Absolute_1D_Move"
    if perf_col not in df.columns:
        st.info("Missing Post_1D_Return in results.")
        return
        
    if abs_col not in df.columns or df[abs_col].isnull().all():
        df[abs_col] = df[perf_col].abs()
        
    df = df.dropna(subset=[perf_col])
    
    ranges = [
        ("<50", 0, 49.99),
        ("50–59", 50, 59.99),
        ("60–69", 60, 69.99),
        ("70–79", 70, 79.99),
        ("80–89", 80, 89.99),
        ("90+", 90, 100)
    ]
    rows = []
    for name, low, high in ranges:
        sub = df[(df["Final_Score"] >= low) & (df["Final_Score"] <= high)]
        count = len(sub)
        if count > 0:
            avg_abs = sub[abs_col].mean()
            big_moves = len(sub[sub[abs_col] >= big_move_threshold]) / count * 100
            avg_ret = sub[perf_col].mean()
            big_up = len(sub[sub[perf_col] >= big_move_threshold]) / count * 100
            big_down = len(sub[sub[perf_col] <= -big_move_threshold]) / count * 100
            
            rows.append({
                "Score Range": name,
                "Events": count,
                "Avg Abs 1D Move": f"{avg_abs:.2f}%",
                "% Big Moves": f"{big_moves:.1f}%",
                "Avg 1D Return": f"{avg_ret:+.2f}%",
                "% Big Up": f"{big_up:.1f}%",
                "% Big Down": f"{big_down:.1f}%"
            })
        else:
            rows.append({
                "Score Range": name,
                "Events": 0,
                "Avg Abs 1D Move": "N/A",
                "% Big Moves": "N/A",
                "Avg 1D Return": "N/A",
                "% Big Up": "N/A",
                "% Big Down": "N/A"
            })
            
    df_table = pd.DataFrame(rows)
    st.dataframe(df_table, use_container_width=True, hide_index=True)


def _render_batch_summary_dashboard(manifest, df_results, big_move_threshold):
    st.markdown("### 🗂️ Batch Replay Summary Dashboard")
    
    # Completed / Failed dates
    completed = len(manifest.get("completed_dates", []))
    failed = len(manifest.get("failed_dates", []))
    
    total_signals = len(df_results)
    
    unique_tickers = df_results["Ticker"].nunique() if "Ticker" in df_results.columns else 0
    
    unique_events = 0
    if "Ticker" in df_results.columns and "Earnings_Date" in df_results.columns:
        unique_events = len(df_results.groupby(["Ticker", "Earnings_Date"]))
        
    avg_rows = total_signals / completed if completed > 0 else 0
    
    abs_col = "Absolute_1D_Move"
    perf_col = "Post_1D_Return"
    if perf_col in df_results.columns:
        if abs_col not in df_results.columns or df_results[abs_col].isnull().all():
            df_results[abs_col] = df_results[perf_col].abs()
            
        avg_abs = df_results[abs_col].mean()
        big_move_rate = len(df_results[df_results[abs_col] >= big_move_threshold]) / total_signals * 100 if total_signals > 0 else 0
        big_up = len(df_results[df_results[perf_col] >= big_move_threshold]) / total_signals * 100 if total_signals > 0 else 0
        big_down = len(df_results[df_results[perf_col] <= -big_move_threshold]) / total_signals * 100 if total_signals > 0 else 0
    else:
        avg_abs = 0.0
        big_move_rate = 0.0
        big_up = 0.0
        big_down = 0.0
        
    # UI Metrics Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Replay Dates Completed", f"{completed} / {len(manifest.get('replay_dates', []))}")
    c2.metric("Failed Dates", failed)
    c3.metric("Total Signal Rows", f"{total_signals:,}")
    c4.metric("Avg Rows / Replay Date", f"{avg_rows:.1f}")
    
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Unique Tickers", unique_tickers)
    c6.metric("Unique Earnings Events", unique_events)
    c7.metric("Avg Abs 1D Move", f"{avg_abs:.2f}%")
    c8.metric(f"Big Move Rate (≥{big_move_threshold}%)", f"{big_move_rate:.1f}%")
    
    c9, c10 = st.columns(2)
    c9.metric("Big Up Rate", f"{big_up:.1f}%")
    c10.metric("Big Down Rate", f"{big_down:.1f}%")


# ── Main UI entry point ─────────────────────────────────────────────────

def show_historical_event_lab_ui(is_tab=False):
    """Render the Historical Market Replay Mode UI."""
    st.markdown(_KPI_CSS, unsafe_allow_html=True)

    # ── Configuration ──
    if is_tab:
        st.markdown("### ⚙️ Historical Market Replay Control Panel")
        config = st.expander("Configure Replay Parameters", expanded=True)
    else:
        config = st.sidebar
        config.markdown("### 🛠️ Replay Configuration")

    with config:
        if is_tab:
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                replay_mode = st.radio(
                    "Replay Mode",
                    ["Single Date Replay", "Weekly Batch Replay", "Daily Batch Replay"],
                    index=0,
                    key="rlab_mode",
                )
                universe_key = st.selectbox(
                    "Stock Universe",
                    list(UNIVERSE_OPTIONS.keys()),
                    index=2,  # default Quick Test
                    key="rlab_uni",
                )
            with cc2:
                today = datetime.date.today()
                if replay_mode == "Single Date Replay":
                    replay_date = st.date_input(
                        "Replay Date", today - datetime.timedelta(days=30), key="rlab_date"
                    )
                    replay_weekday = "Monday"
                    batch_id_input = ""
                else:
                    default_start = today - datetime.timedelta(days=365)
                    date_range = st.date_input(
                        "Date Range", [default_start, today - datetime.timedelta(days=7)], key="rlab_range"
                    )
                    if replay_mode == "Weekly Batch Replay":
                        replay_weekday = st.selectbox(
                            "Replay Weekday",
                            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                            index=0,
                            key="rlab_weekday"
                        )
                    else:
                        replay_weekday = "Monday"  # ignored for daily mode
                        st.caption("📅 Daily mode: every trading day (Mon–Fri)")
                    if "default_batch_id" not in st.session_state:
                        st.session_state["default_batch_id"] = f"batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    batch_id_input = st.text_input("Batch ID", value=st.session_state["default_batch_id"], key="rlab_batch_id")

                rank_by = st.selectbox(
                    "Rank Candidates By",
                    ["Final_Score", "Opportunity_Score", "Research_Priority_Score"],
                    index=0,
                    key="rlab_rank",
                )
            with cc3:
                if replay_mode in ("Weekly Batch Replay", "Daily Batch Replay"):
                    _save_n_label = st.selectbox(
                        "Candidates Saved Per Date",
                        ["All Scored", "Top 20", "Top 50", "Top 100", "Top 250", "Top 500"],
                        index=0,
                        key="rlab_save_n",
                        help="How many candidates to save per replay date for research."
                    )
                    _save_n_map = {"All Scored": 0, "Top 20": 20, "Top 50": 50, "Top 100": 100, "Top 250": 250, "Top 500": 500}
                    save_n = _save_n_map.get(_save_n_label, 0)
                    top_n = st.selectbox(
                        "Portfolio Top N",
                        [5, 10, 20, 50],
                        index=2,
                        key="rlab_topn",
                        help="How many top candidates to use for portfolio simulation chart."
                    )
                    _cooldown_label = st.selectbox(
                        "Cooldown Between Days",
                        ["30 seconds", "1 minute", "10 seconds", "5 seconds", "None"],
                        index=0,
                        key="rlab_cooldown",
                        help="Wait time between consecutive replay dates."
                    )
                    _cooldown_map = {"None": 0, "5 seconds": 5, "10 seconds": 10, "30 seconds": 30, "1 minute": 60}
                    cooldown_seconds = _cooldown_map.get(_cooldown_label, 30)
                else:
                    save_n = 0
                    top_n = st.slider("Top N Candidates", 5, 50, 20, key="rlab_topn")
                    cooldown_seconds = 0
                min_mc = st.number_input("Min Market Cap ($)", value=50_000_000, step=10_000_000, format="%d", key="rlab_mc")
                min_vol = st.number_input("Min Avg Volume (20d)", value=500_000, step=100_000, format="%d", key="rlab_vol")
                scoring_mode = st.radio("Scoring Mode", ["Strict", "Exploratory"], index=0, key="rlab_smode")
                big_move_threshold = st.slider("Big Move Threshold (%)", 1.0, 20.0, 8.0, step=0.5, key="rlab_bmt")
        else:
            replay_mode = st.radio(
                "Replay Mode",
                ["Single Date Replay", "Weekly Batch Replay", "Daily Batch Replay"],
                index=0,
                key="rlab_mode",
            )
            universe_key = st.selectbox(
                "Stock Universe",
                list(UNIVERSE_OPTIONS.keys()),
                index=2,
                key="rlab_uni",
            )
            today = datetime.date.today()
            if replay_mode == "Single Date Replay":
                replay_date = st.date_input(
                    "Replay Date", today - datetime.timedelta(days=30), key="rlab_date"
                )
                replay_weekday = "Monday"
                batch_id_input = ""
            else:
                default_start = today - datetime.timedelta(days=365)
                date_range = st.date_input(
                    "Date Range", [default_start, today - datetime.timedelta(days=7)], key="rlab_range"
                )
                if replay_mode == "Weekly Batch Replay":
                    replay_weekday = st.selectbox(
                        "Replay Weekday",
                        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                        index=0,
                        key="rlab_weekday"
                    )
                else:
                    replay_weekday = "Monday"  # ignored for daily mode
                    st.caption("📅 Daily mode: every trading day (Mon–Fri)")
                if "default_batch_id" not in st.session_state:
                    st.session_state["default_batch_id"] = f"batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                batch_id_input = st.text_input("Batch ID", value=st.session_state["default_batch_id"], key="rlab_batch_id")

            rank_by = st.selectbox(
                "Rank Candidates By",
                ["Final_Score", "Opportunity_Score", "Research_Priority_Score"],
                index=0,
                key="rlab_rank",
            )
            st.markdown("### 💸 Filters")
            if replay_mode in ("Weekly Batch Replay", "Daily Batch Replay"):
                _save_n_label = st.selectbox(
                    "Candidates Saved Per Date",
                    ["All Scored", "Top 20", "Top 50", "Top 100", "Top 250", "Top 500"],
                    index=0,
                    key="rlab_save_n",
                    help="How many candidates to save per replay date for research."
                )
                _save_n_map = {"All Scored": 0, "Top 20": 20, "Top 50": 50, "Top 100": 100, "Top 250": 250, "Top 500": 500}
                save_n = _save_n_map.get(_save_n_label, 0)
                top_n = st.selectbox(
                    "Portfolio Top N",
                    [5, 10, 20, 50],
                    index=2,
                    key="rlab_topn",
                    help="How many top candidates to use for portfolio simulation chart."
                )
                _cooldown_label = st.selectbox(
                    "Cooldown Between Days",
                    ["30 seconds", "1 minute", "10 seconds", "5 seconds", "None"],
                    index=0,
                    key="rlab_cooldown_sidebar",
                    help="Wait time between consecutive replay dates."
                )
                _cooldown_map = {"None": 0, "5 seconds": 5, "10 seconds": 10, "30 seconds": 30, "1 minute": 60}
                cooldown_seconds = _cooldown_map.get(_cooldown_label, 30)
            else:
                save_n = 0
                top_n = st.slider("Top N Candidates", 5, 50, 20, key="rlab_topn")
                cooldown_seconds = 0
            min_mc = st.number_input("Min Market Cap ($)", value=50_000_000, step=10_000_000, format="%d", key="rlab_mc")
            min_vol = st.number_input("Min Avg Volume (20d)", value=500_000, step=100_000, format="%d", key="rlab_vol")
            scoring_mode = st.radio("Scoring Mode", ["Strict", "Exploratory"], index=0, key="rlab_smode")
            big_move_threshold = st.slider("Big Move Threshold (%)", 1.0, 20.0, 8.0, step=0.5, key="rlab_bmt")

        if replay_mode == "Single Date Replay":
            run_col1, run_col2 = st.columns(2)
            with run_col1:
                run_btn = st.button("🚀 Run Replay", use_container_width=True, key="rlab_run")
            with run_col2:
                saved = store.list_saved_backtests()
                if saved:
                    opts = {f"{r['timestamp']} ({r['event_count']} events)": r["filepath"] for r in saved}
                    sel = st.selectbox("Load Saved Run", ["-- None --"] + list(opts.keys()), key="rlab_load_sel")
                    if sel != "-- None --":
                        if st.button("📂 Load", use_container_width=True, key="rlab_load_btn"):
                            loaded = store.load_backtest_run(opts[sel])
                            if not loaded.empty:
                                st.session_state["rlab_results"] = loaded
                                st.success(f"Loaded {len(loaded)} events.")
        else:
            run_btn = False

    # ── Session state ──
    if "rlab_results" not in st.session_state:
        st.session_state["rlab_results"] = pd.DataFrame()

    # ── Execute replay ──
    if run_btn and replay_mode == "Single Date Replay":
        universe_df = _load_universe(universe_key)
        if universe_df.empty:
            st.error("Could not load stock universe CSV.")
        else:
            st.info(
                f"🔄 Replaying scanner on **{replay_date}** across "
                f"**{len(universe_df):,}** tickers…"
            )
            prog = st.progress(0)
            status = st.empty()

            def _cb(done, total, ticker, reason):
                prog.progress(done / total)
                if reason == "scored":
                    status.markdown(f"✅ **{ticker}** scored ({done}/{total})")
                else:
                    status.markdown(f"⏭️ {ticker} — {reason} ({done}/{total})")

            df_all, diag = run_single_date_replay(
                replay_date, universe_df, top_n, min_mc, min_vol,
                scoring_mode, big_move_threshold, rank_by, _cb,
            )
            prog.empty()
            status.empty()

            if df_all.empty:
                st.warning("No candidates survived filters on this date.")
                st.info(
                    f"**Diagnostics**: Universe={diag['universe_size']:,} → "
                    f"Earnings Eligible={diag['earnings_eligible']} → "
                    f"Price/Vol Survivors={diag['price_vol_survivors']} → "
                    f"Scored={diag['scored_count']}"
                )
            else:
                st.session_state["rlab_results"] = df_all
                st.success(
                    f"Replay complete! **{diag['scored_count']}** candidates scored. "
                    f"Universe={diag['universe_size']:,} → Earnings={diag['earnings_eligible']} → "
                    f"Survivors={diag['price_vol_survivors']} → Scored={diag['scored_count']}"
                )

    # ── Execute Replay Batch Loop ──
    if replay_mode in ("Weekly Batch Replay", "Daily Batch Replay") and st.session_state.get("batch_running", False) and st.session_state.get("active_batch_id"):
        from historical_batch_aggregator import BatchReplayManager
        active_mgr = BatchReplayManager(st.session_state["active_batch_id"])
        manifest = active_mgr.load_manifest()
        
        if manifest.get("status") == "completed":
            st.session_state["batch_running"] = False
            st.success("🎉 Batch completed successfully!")
            st.rerun()
        elif manifest.get("status") == "paused":
            st.session_state["batch_running"] = False
            st.warning("⏸️ Batch paused.")
            st.rerun()
        else:
            universe_df = _load_universe(universe_key)
            if universe_df.empty:
                st.error("Could not load universe.")
                st.session_state["batch_running"] = False
                st.rerun()
            else:
                all_dates = manifest.get("replay_dates", [])
                completed = manifest.get("completed_dates", [])
                failed = manifest.get("failed_dates", [])
                next_date = None
                for d in all_dates:
                    if d not in completed and d not in failed:
                        next_date = d
                        break
                
                if next_date:
                    st.info(f"⏳ Processing batch step for date: **{next_date}**...")
                    prog_val = st.empty()
                    def _cb_ui(done, total, ticker, reason):
                        prog_val.markdown(f"**Step Progress**: {reason} for {ticker} ({done}/{total})")
                    
                    manifest = active_mgr.run_next_step(universe_df, progress_callback=_cb_ui)
                    
                    # Run a visual cooldown countdown if there's a next date to process
                    all_dates = manifest.get("replay_dates", [])
                    completed = manifest.get("completed_dates", [])
                    failed = manifest.get("failed_dates", [])
                    upcoming_date = None
                    for d in all_dates:
                        if d not in completed and d not in failed:
                            upcoming_date = d
                            break
                            
                    if upcoming_date:
                        cooldown_val = manifest.get("settings", {}).get("cooldown_seconds", 30)
                        if cooldown_val > 0:
                            cooldown_placeholder = st.empty()
                            import time
                            for rem in range(cooldown_val, 0, -1):
                                cooldown_placeholder.info(
                                    f"🕒 Completed **{next_date}**. "
                                    f"Cooling down for **{rem}** seconds before starting **{upcoming_date}**..."
                                )
                                time.sleep(1)
                            cooldown_placeholder.empty()
                            
                    st.rerun()
                else:
                    manifest["status"] = "completed"
                    active_mgr._save_manifest(manifest)
                    st.session_state["batch_running"] = False
                    st.success("🎉 All dates processed!")
                    st.rerun()

    # Load aggregated results if available
    if replay_mode in ("Weekly Batch Replay", "Daily Batch Replay") and batch_id_input:
        from historical_batch_aggregator import BatchReplayManager
        active_mgr = BatchReplayManager(batch_id_input)
        manifest = active_mgr.load_manifest()
        
        if manifest and "aggregated" in manifest:
            # Dropdown for Aggregation Mode
            st.markdown("---")
            agg_col1, agg_col2 = st.columns([2, 2])
            with agg_col1:
                agg_mode = st.selectbox(
                    "Select Aggregation Mode",
                    ["All Signals", "First Signal Only", "Best Rank Before Earnings"],
                    key="rlab_agg_mode_select"
                )
            
            paths = manifest["aggregated"]["paths"]
            csv_key = {
                "All Signals": "csv_all_signals",
                "First Signal Only": "csv_first_signal_only",
                "Best Rank Before Earnings": "csv_best_rank"
            }.get(agg_mode, "csv_all_signals")
            
            csv_path = paths.get(csv_key)
            if csv_path and os.path.exists(csv_path):
                if st.session_state.get("last_loaded_agg_batch") != (batch_id_input, agg_mode):
                    with st.spinner("Loading aggregated dataset..."):
                        df_agg = pd.read_csv(csv_path)
                        st.session_state["rlab_results"] = df_agg
                        st.session_state["last_loaded_agg_batch"] = (batch_id_input, agg_mode)

    # ── Display results ──
    df_results = st.session_state["rlab_results"]

    if replay_mode in ("Weekly Batch Replay", "Daily Batch Replay"):
        st.markdown("### 🗂️ Historical Replay Batch Aggregator")
        from historical_batch_aggregator import BatchReplayManager
        mgr = BatchReplayManager(batch_id_input)
        manifest = mgr.load_manifest()
        
        if manifest:
            st.write(f"**Status**: `{manifest.get('status')}` | **Completed**: {len(manifest.get('completed_dates', []))} / {len(manifest.get('replay_dates', []))} dates")
        else:
            st.write("No active batch found on disk. Click **Start New Batch** to initialize.")
            
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("🚀 Start New Batch", key="agg_start", use_container_width=True):
                if not date_range or len(date_range) != 2:
                    st.error("Select a valid date range first.")
                else:
                    start_d, end_d = date_range
                    settings_dict = {
                        "top_n": top_n,
                        "save_n": save_n,
                        "min_mc": min_mc,
                        "min_vol": min_vol,
                        "mode": scoring_mode,
                        "big_move_threshold": big_move_threshold,
                        "rank_by": rank_by,
                        "frequency": "Daily" if replay_mode == "Daily Batch Replay" else "Weekly",
                        "cooldown_seconds": cooldown_seconds
                    }
                    manifest = mgr.initialize_new_batch(
                        start_date=start_d,
                        end_date=end_d,
                        weekday=replay_weekday,
                        settings=settings_dict
                    )
                    # Start running immediately
                    manifest["status"] = "running"
                    mgr._save_manifest(manifest)
                    
                    st.session_state["active_batch_id"] = batch_id_input
                    st.session_state["batch_running"] = True
                    st.success(f"Initialized new batch: {batch_id_input}")
                    st.rerun()
                    
        with col2:
            if st.button("▶️ Resume Batch", key="agg_resume", use_container_width=True):
                if not manifest:
                    st.error("No manifest found. Initialize a batch first.")
                else:
                    st.session_state["active_batch_id"] = batch_id_input
                    st.session_state["batch_running"] = True
                    manifest["status"] = "running"
                    mgr._save_manifest(manifest)
                    st.rerun()
                    
        with col3:
            if st.button("⏸️ Pause Batch", key="agg_pause", use_container_width=True):
                st.session_state["batch_running"] = False
                mgr.pause_batch()
                st.success("Batch paused.")
                st.rerun()
                
        with col4:
            if st.button("🔄 Retry Failed", key="agg_retry", use_container_width=True):
                if not manifest:
                    st.error("No manifest found.")
                else:
                    mgr.retry_failed_dates()
                    st.session_state["active_batch_id"] = batch_id_input
                    st.session_state["batch_running"] = True
                    st.rerun()
                    
        with col5:
            if st.button("📦 Build Dataset", key="agg_build", use_container_width=True):
                if not manifest:
                    st.error("No manifest found.")
                else:
                    with st.spinner("Aggregating files..."):
                        res = mgr.build_aggregated_datasets()
                        if "error" in res:
                            st.error(res["error"])
                        else:
                            st.success("Consolidated aggregation datasets built successfully!")
                            st.rerun()
                            
        if manifest:
            st.markdown("#### 📈 Batch Progress Dashboard")
            dates = manifest.get("replay_dates", [])
            completed = manifest.get("completed_dates", [])
            failed = manifest.get("failed_dates", [])
            total_dates = len(dates)
            completed_count = len(completed)
            failed_count = len(failed)
            
            progress_pct = completed_count / total_dates if total_dates > 0 else 0.0
            st.progress(progress_pct)
            
            total_rows = manifest.get("total_rows_processed", 0)
            
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Progress", f"{completed_count} / {total_dates} dates")
            p2.metric("Failures", failed_count)
            p3.metric("Est. Saved Rows", f"{total_rows:,}")
            
            last_saved = f"replay_{completed[-1]}.csv" if completed else "None"
            p4.metric("Last Saved File", last_saved)
            
            if failed:
                st.error(f"❌ Failed dates: {', '.join(failed)}")

            # Per-date diagnostics table
            date_diags = manifest.get("date_diagnostics", {})
            if date_diags:
                with st.expander("🔍 Per-Date Diagnostics", expanded=False):
                    diag_rows = []
                    for dt in completed:
                        d = date_diags.get(dt, {})
                        diag_rows.append({
                            "Date": dt,
                            "Universe": d.get("universe_size", "—"),
                            "Earnings Eligible": d.get("earnings_eligible", "—"),
                            "Price/Vol Survivors": d.get("price_vol_survivors", "—"),
                            "Scored": d.get("scored_count", "—"),
                            "Saved Rows": d.get("saved_count", "—"),
                            "Cap Used": d.get("cap_used", "—"),
                            "Time (s)": d.get("elapsed_seconds", "—"),
                        })
                    if diag_rows:
                        st.dataframe(pd.DataFrame(diag_rows), use_container_width=True, hide_index=True)

    if df_results.empty:
        st.markdown("---")
        if replay_mode in ("Weekly Batch Replay", "Daily Batch Replay"):
            st.info("💡 Run the batch or build/load the consolidated dataset above to display metrics.")
        else:
            st.info(
                "💡 **Historical Market Replay Mode**\n\n"
                "Configure parameters above and click **Run Replay** to replay the live "
                "Catalyst Scanner on any historical date.\n\n"
                "- **Single Date Replay** — See the exact leaderboard the scanner would "
                "have produced on a specific date.\n"
                "- **Weekly Batch Replay** — Run weekly replays over a date range and "
                "measure cumulative portfolio performance.\n"
                "- **Daily Batch Replay** — Run every trading day (Mon–Fri) in a date "
                "range for large-scale dataset generation and factor validation.\n\n"
                "The replay is **lookahead-free**: all scores use only data available before "
                "the replay date."
            )
        return

    # Summary KPIs
    event_window = 1
    st.markdown("### 📊 Replay Results")

    # Show badges
    mode_badge = '<span class="replay-badge badge-purple">Market Replay</span>'
    if "Scan_Date" in df_results.columns:
        unique_dates = df_results["Scan_Date"].nunique()
        if unique_dates > 1:
            batch_label = "days" if replay_mode == "Daily Batch Replay" else "weeks"
            mode_badge += f'<span class="replay-badge badge-blue">Batch: {unique_dates} {batch_label}</span>'
        else:
            mode_badge += f'<span class="replay-badge badge-green">Single: {df_results["Scan_Date"].iloc[0]}</span>'
    st.markdown(mode_badge, unsafe_allow_html=True)

    if replay_mode in ("Weekly Batch Replay", "Daily Batch Replay") and batch_id_input:
        from historical_batch_aggregator import BatchReplayManager
        active_mgr = BatchReplayManager(batch_id_input)
        manifest = active_mgr.load_manifest()
        if manifest:
            _render_batch_summary_dashboard(manifest, df_results, big_move_threshold)
        else:
            _render_summary_kpis(df_results, event_window, big_move_threshold)
    else:
        _render_summary_kpis(df_results, event_window, big_move_threshold)

    # Portfolio chart (batch mode)
    unique_scan_dates = df_results["Scan_Date"].nunique() if "Scan_Date" in df_results.columns else 1
    if unique_scan_dates > 1:
        _render_portfolio_chart(df_results, top_n, rank_by)

    # Tabs
    t_explorer, t_validation, t_importance, t_table = st.tabs(
        ["🎯 Setup Explorer", "📊 Score Threshold Validation", "🧬 Factor Importance", "📋 Detailed Event Table"]
    )
    with t_explorer:
        perf_col = "Post_1D_Return"
        _render_setup_explorer(df_results, perf_col, big_move_threshold)
    with t_validation:
        _render_score_threshold_validation(df_results, big_move_threshold)
        st.markdown("---")
        _render_score_range_validation(df_results, big_move_threshold)
    with t_importance:
        _render_factor_importance(df_results)
    with t_table:
        _render_event_table(df_results, big_move_threshold)


# ── Standalone mode ──────────────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(
        page_title="Historical Market Replay | Antigravity",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        '<div style="text-align:center;padding:18px 0 8px">'
        "<h1>🔄 Historical Market Replay Mode</h1>"
        "<p style='color:#9ca3af'>Replay the Catalyst Scanner on any historical date — "
        "no selection bias, no lookahead.</p></div>",
        unsafe_allow_html=True,
    )
    show_historical_event_lab_ui(is_tab=False)

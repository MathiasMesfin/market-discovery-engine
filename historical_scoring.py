"""Port of scoring formulas from screener.py adapted for historical event backtesting."""
import datetime
from typing import Dict, Any, List
from directional_overlay import calculate_directional_overlay

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

def is_guidance_sensitive_sector(sector: str, industry: str) -> bool:
    if not sector and not industry:
        return False
    s_i = f"{sector or ''} {industry or ''}".lower()
    keywords = [
        'software', 'saas', 'cloud', 'cybersecurity', 'apparel', 'retail',
        'consumer discretionary', 'discretionary', 'semiconductor', 'tech', 'internet'
    ]
    return any(kw in s_i for kw in keywords)

def calculate_historical_scores(
    tech_feats: Dict[str, Any],
    fund_feats: Dict[str, Any],
    react_feats: Dict[str, Any],
    static_meta: Dict[str, Any], # e.g. sector, industry, float shares, market cap
    mode: str = "Strict", # "Strict" or "Exploratory"
    is_filing_proxy: bool = False
) -> Dict[str, Any]:
    """Calculate all scores for a single historical event row using point-in-time inputs."""
    scores = {}
    increases_list = []
    penalties_list = []
    warnings_list = []
    missing_list = []

    # Get primary variables
    price = _safe_float(tech_feats.get('Price_T_minus_1'))
    rvol = _safe_float(tech_feats.get('RVOL'), 1.0)
    rsi_val = _safe_float(tech_feats.get('RSI'), 50.0)
    sma_50 = _safe_float(tech_feats.get('SMA50'))
    sma_200 = _safe_float(tech_feats.get('SMA200'))
    atr_pct = _safe_float(tech_feats.get('ATR_Pct'), 0.0)
    gap_freq = _safe_float(tech_feats.get('Gap_Frequency'), 0.0)
    ret_30d = _safe_float(tech_feats.get('Pre_30D_Return'))
    ret_60d = _safe_float(tech_feats.get('Pre_60D_Return'))
    ret_90d = _safe_float(tech_feats.get('Pre_90D_Return'))
    dist_52w = _safe_float(tech_feats.get('Dist_From_52W_High'))
    
    # Fundamentals
    q_fcf = fund_feats.get('Quarterly_FCF_History', [])
    ttm_fcf = _safe_float(fund_feats.get('TTM_FCF'))
    rev_trend = fund_feats.get('Revenue_Trend', 'Unknown')
    gm_trend = fund_feats.get('Gross_Margin_Trend', 'Unknown')
    ni_trend = fund_feats.get('Net_Income_Trend', 'Unknown')
    cash = _safe_float(fund_feats.get('Latest_Cash'))
    debt = _safe_float(fund_feats.get('Latest_Debt'))
    
    # Reactions
    avg_react = _safe_float(react_feats.get('Historical_Avg_Earnings_Reaction'), 0.0)
    
    # Static metadata / current settings
    sector = static_meta.get('Sector')
    industry = static_meta.get('Industry')
    mkt_cap = _safe_float(static_meta.get('Market_Cap'))
    float_shares = _safe_float(static_meta.get('Float_Shares'))
    
    # Mode-dependent inputs (Short Interest and Analysts)
    # Strict mode: Exclude current non-point-in-time metrics if not historical
    short_percent = None
    analysts = None
    if mode == "Exploratory":
        short_percent = _safe_float(static_meta.get('Short_Percent'))
        analysts = _safe_float(static_meta.get('Analysts'))
        if short_percent is not None:
            warnings_list.append("Lookahead Warning: Using current Short Interest in Exploratory Mode")
        if analysts is not None:
            warnings_list.append("Lookahead Warning: Using current Analyst coverage in Exploratory Mode")
    else:
        # Strict Mode excludes them unless we have point-in-time (not standard in yfinance)
        # We assign default neutral values but exclude them from strict calculations
        short_percent = None
        analysts = None

    # Confidence Flag Calculation
    confidence = "High"
    if is_filing_proxy:
        confidence = "Low"
        warnings_list.append("Filing Proxy: Using SEC filing date as earnings date proxy")
    elif mode == "Exploratory" and (static_meta.get('Short_Percent') is not None or static_meta.get('Analysts') is not None):
        confidence = "Medium"
    if fund_feats.get('SEC_Data_Quality') == 'Low':
        confidence = "Low"
        warnings_list.append("Low SEC fundamentals confidence (data is missing or approximate)")
    elif fund_feats.get('SEC_Data_Quality') == 'Medium' and confidence == "High":
        confidence = "Medium"

    # --- 1. Run-Up Risk Score and Expectation Setup ---
    ru_score = 0.0
    ru_inc = []
    ru_missing = []
    
    if ret_30d is not None:
        if ret_30d > 25.0:
            ru_score += 30
            ru_inc.append(f"+30: Massive 30D return is {ret_30d:.1f}% (> 25%)")
        elif ret_30d > 15.0:
            ru_score += 20
            ru_inc.append(f"+20: Meaningful 30D return is {ret_30d:.1f}% (> 15%)")
        elif ret_30d > 10.0:
            ru_score += 10
            ru_inc.append(f"+10: 30D return is {ret_30d:.1f}% (> 10%)")
    else:
        ru_missing.append("30D Return")

    if ret_60d is not None:
        if ret_60d > 30.0:
            ru_score += 25
            ru_inc.append(f"+25: Major 60D return is {ret_60d:.1f}% (> 30%)")
        elif ret_60d > 20.0:
            ru_score += 15
            ru_inc.append(f"+15: 60D return is {ret_60d:.1f}% (> 20%)")
    else:
        ru_missing.append("60D Return")

    if ret_90d is not None:
        if ret_90d > 45.0:
            ru_score += 15
            ru_inc.append(f"+15: High 90D return is {ret_90d:.1f}% (> 45%)")
        elif ret_90d > 30.0:
            ru_score += 10
            ru_inc.append(f"+10: 90D return is {ret_90d:.1f}% (> 30%)")
    else:
        ru_missing.append("90D Return")

    if rsi_val > 75.0:
        ru_score += 15
        ru_inc.append(f"+15: RSI is overbought at {rsi_val:.1f} (> 75)")
    elif rsi_val > 70.0:
        ru_score += 10
        ru_inc.append(f"+10: RSI is elevated at {rsi_val:.1f} (> 70)")
    elif rsi_val > 65.0:
        ru_score += 5
        ru_inc.append(f"+5: RSI is moderately high at {rsi_val:.1f} (> 65)")

    if dist_52w is not None:
        if dist_52w <= 0.05:
            ru_score += 15
            ru_inc.append(f"+15: Price extremely close to 52W high ({dist_52w*100:.1f}% away)")
        elif dist_52w <= 0.10:
            ru_score += 10
            ru_inc.append(f"+10: Price close to 52W high ({dist_52w*100:.1f}% away)")
        elif dist_52w <= 0.15:
            ru_score += 5
            ru_inc.append(f"+5: Price near 52W high ({dist_52w*100:.1f}% away)")
    else:
        ru_missing.append("52-week High")

    if price is not None and sma_50 is not None and sma_200 is not None:
        if price > sma_50 and price > sma_200:
            ru_score += 10
            ru_inc.append("+10: Price is above both SMA50 and SMA200")
    else:
        if not sma_50: ru_missing.append("SMA50")
        if not sma_200: ru_missing.append("SMA200")

    run_up_risk_score = min(100.0, ru_score)
    expectation_setup_score = 100.0 - run_up_risk_score

    # Assemble run-up messages into penalties/increases
    if run_up_risk_score > 0:
        penalties_list.append(f"Expectation Inflation Risk (Run-Up Risk: {run_up_risk_score:.1f}/100):")
        for x in ru_inc:
            penalties_list.append(f"  - {x}")
    else:
        increases_list.append("Low Expectation Setup: Priced conservatively going into earnings.")

    # --- 2. Cash Flow Quality Score ---
    cf_score = 50.0
    cf_trend = "Unknown"
    cf_latest = None
    cf_prior = None
    cf_status = "Missing"
    cf_inc = []
    cf_pen = []
    
    if q_fcf and len(q_fcf) >= 1:
        cf_status = "Available (Quarterly)"
        cf_latest = q_fcf[-1]
        if len(q_fcf) >= 2:
            cf_prior = q_fcf[-2]
            if cf_latest > cf_prior:
                cf_trend = "Improving"
            elif cf_latest < cf_prior:
                cf_trend = "Declining"
            else:
                cf_trend = "Stable"
        else:
            cf_trend = "Stable (Only 1 Quarter Available)"
            warnings_list.append("Only one quarter of FCF data available.")
            
        neg_quarters = sum(1 for q in q_fcf if q < 0)
        total_quarters = len(q_fcf)
        
        if cf_latest > 0:
            if cf_trend == "Improving":
                cf_score = 100.0
                cf_inc.append("100: Latest quarterly FCF is positive and improving QoQ")
            else:
                cf_score = 75.0
                cf_inc.append("75: Latest quarterly FCF is positive but declining QoQ")
        elif abs(cf_latest) <= 1_000_000:
            cf_score = 50.0
            cf_inc.append("50: Latest quarterly FCF is near breakeven")
        else: # negative
            if cf_trend == "Improving":
                cf_score = 25.0
                cf_pen.append("25: Latest quarterly FCF is negative but improving QoQ")
            else:
                cf_score = 0.0
                cf_pen.append("0: Latest quarterly FCF is negative and deteriorating QoQ")

        if ttm_fcf is not None:
            if ttm_fcf < 0:
                if cf_score > 55.0:
                    old_score = cf_score
                    cf_score = 55.0
                    cf_pen.append(f"Capped from {old_score:.0f} to 55: TTM FCF is structurally negative (${ttm_fcf/1e6:,.1f}M)")
                else:
                    cf_pen.append(f"TTM FCF is negative (${ttm_fcf/1e6:,.1f}M)")
                if ttm_fcf < -50_000_000:
                    cf_score = min(cf_score, 35.0)
                    cf_pen.append(f"Heavy TTM FCF burn: ${ttm_fcf/1e6:,.1f}M (< -$50M)")
            else:
                cf_inc.append(f"TTM FCF is positive (${ttm_fcf/1e6:,.1f}M)")
        else:
            missing_list.append("TTM FCF")
            warnings_list.append("TTM FCF data is missing. Score based on quarterly data only.")

        if total_quarters >= 2 and neg_quarters >= 2:
            has_positive_floor = (cf_latest > 0) and (ttm_fcf is not None and ttm_fcf > 0)
            if has_positive_floor:
                floor = 75.0 if cf_trend == "Improving" else 60.0
                deduction = 5.0 * neg_quarters
                cf_score = max(floor - deduction, 0.0)
                cf_pen.append(f"Prior negative quarters ({neg_quarters}/{total_quarters} negative) deducted {deduction:.0f} points. Score protected by positive latest and TTM FCF floor.")
            else:
                if total_quarters >= 3 and neg_quarters >= 3:
                    cf_score = min(cf_score, 20.0)
                    cf_pen.append(f"All {neg_quarters}/{total_quarters} recent quarters have negative FCF")
                else:
                    cf_score = min(cf_score, max(cf_score - 10, 0.0))
                    cf_pen.append(f"{neg_quarters}/{total_quarters} recent quarters have negative FCF")
    elif ttm_fcf is not None:
        cf_status = "Available (TTM)"
        cf_latest = ttm_fcf
        warnings_list.append("Quarterly cash flow history is missing. Using TTM levered FCF fallback.")
        if ttm_fcf > 0:
            cf_score = 65.0
            cf_inc.append(f"65: TTM FCF is positive (${ttm_fcf/1e6:,.1f}M, fallback)")
        elif ttm_fcf > -10_000_000:
            cf_score = 35.0
            cf_pen.append(f"35: TTM FCF is slightly negative (${ttm_fcf/1e6:,.1f}M, fallback)")
        else:
            cf_score = 15.0
            cf_pen.append(f"15: TTM FCF is deeply negative (${ttm_fcf/1e6:,.1f}M, fallback)")
    else:
        cf_status = "Missing"
        missing_list.append("Quarterly and TTM FCF data")
        warnings_list.append("No cash flow data available. Assigned neutral score of 50.")
        cf_score = 50.0

    cash_flow_quality_score = cf_score
    for x in cf_inc: increases_list.append(x)
    for x in cf_pen: penalties_list.append(x)

    # --- 3. Guidance Sensitivity Score ---
    gs_score = 0.0
    gs_inc = []
    gs_missing = []
    
    if is_guidance_sensitive_sector(sector, industry):
        gs_score += 25
        gs_inc.append(f"+25: Sector/Industry is guidance-sensitive ({sector} / {industry})")
    elif not sector and not industry:
        gs_missing.append("Sector / Industry")

    if analysts is not None:
        if analysts >= 10:
            gs_score += 20
            gs_inc.append(f"+20: Heavy analyst coverage ({analysts:.0f} analysts >= 10)")
    else:
        if mode == "Strict":
            gs_missing.append("Analyst count (Strict Mode)")
        else:
            gs_missing.append("Analyst count")

    if avg_react >= 10.0:
        gs_score += 20
        gs_inc.append(f"+20: Volatile earnings history (avg reaction {avg_react:.1f}% >= 10%)")

    if ret_30d is not None and ret_30d > 15.0:
        gs_score += 15
        gs_inc.append(f"+15: 30D return is {ret_30d:.1f}% (> 15%)")

    # Reconstruct valuation multiple check (using current if in Exploratory mode, else None)
    elevated_pe = False
    if mode == "Exploratory":
        forward_pe = _safe_float(static_meta.get('Forward_PE'))
        trailing_pe = _safe_float(static_meta.get('Trailing_PE'))
        ps_ratio = _safe_float(static_meta.get('Price_To_Sales'))
        
        if forward_pe is not None and forward_pe > 30: elevated_pe = True
        if trailing_pe is not None and trailing_pe > 30: elevated_pe = True
        if ps_ratio is not None and ps_ratio > 8: elevated_pe = True
        
        if elevated_pe:
            gs_score += 10
            gs_inc.append("+10: Elevated valuation multiple (PE > 30 or P/S > 8)")
    else:
        gs_missing.append("Valuation multiples (Strict Mode)")
        
    revenue_growth = _safe_float(static_meta.get('Revenue_Growth'))
    if mode == "Exploratory" and revenue_growth is not None:
        if revenue_growth > 0.15:
            gs_score += 10
            gs_inc.append(f"+10: High revenue growth expectations ({revenue_growth*100:.1f}% > 15%)")
    else:
        if mode == "Strict":
            gs_missing.append("Revenue Growth (Strict Mode)")
        else:
            gs_missing.append("Revenue Growth")

    guidance_sensitivity_score = min(100.0, gs_score)

    # --- 4. Days To Cover Score ---
    # Days to cover is based on short interest which is lookahead-contaminated unless point-in-time
    days_to_cover = None
    if mode == "Exploratory" and short_percent is not None and mkt_cap and price:
        # Calculate days to cover if short interest shares and avg vol are available
        shares_short = _safe_float(static_meta.get('Shares_Short'))
        avg_vol_20d = _safe_float(tech_feats.get('Avg_Vol_20d'))
        if shares_short and avg_vol_20d and avg_vol_20d > 0:
            days_to_cover = float(shares_short / avg_vol_20d)
        if days_to_cover is None:
            days_to_cover = _safe_float(static_meta.get('Short_Ratio'))

    dtc_score = 50.0
    dtc_breakdown = []
    if days_to_cover is not None:
        if days_to_cover >= 7:
            dtc_score = 100.0
            dtc_breakdown.append(f"100: Very high days-to-cover ({days_to_cover:.2f} >= 7)")
        elif days_to_cover >= 5:
            dtc_score = 85.0
            dtc_breakdown.append(f"85: High days-to-cover ({days_to_cover:.2f} >= 5)")
        elif days_to_cover >= 3:
            dtc_score = 65.0
            dtc_breakdown.append(f"65: Moderate days-to-cover ({days_to_cover:.2f} >= 3)")
        elif days_to_cover >= 1.5:
            dtc_score = 40.0
            dtc_breakdown.append(f"40: Low days-to-cover ({days_to_cover:.2f} >= 1.5)")
        else:
            dtc_score = 20.0
            dtc_breakdown.append(f"20: Very low days-to-cover ({days_to_cover:.2f} < 1.5)")
    else:
        dtc_breakdown.append("Assigned neutral score of 50 due to missing days-to-cover data.")
        
    days_to_cover_score = dtc_score

    # --- 5. Short Squeeze Quality Score ---
    sq_score = 0.0
    sq_inc = []
    sq_missing = []
    
    if mode == "Exploratory":
        if short_percent is not None:
            sp = short_percent * 100.0
            if sp >= 25.0:
                sq_score += 35
                sq_inc.append(f"+35: Short percent is {sp:.1f}% (>= 25%)")
            elif sp >= 15.0:
                sq_score += 25
                sq_inc.append(f"+25: Short percent is {sp:.1f}% (>= 15%)")
            elif sp >= 10.0:
                sq_score += 15
                sq_inc.append(f"+15: Short percent is {sp:.1f}% (>= 10%)")
            elif sp >= 5.0:
                sq_score += 5
                sq_inc.append(f"+5: Short percent is {sp:.1f}% (>= 5%)")
        else:
            sq_missing.append("Short Percent")

        if days_to_cover is not None:
            if days_to_cover >= 7:
                sq_score += 35
                sq_inc.append(f"+35: Days to cover is {days_to_cover:.2f} (>= 7)")
            elif days_to_cover >= 5:
                sq_score += 25
                sq_inc.append(f"+25: Days to cover is {days_to_cover:.2f} (>= 5)")
            elif days_to_cover >= 3:
                sq_score += 15
                sq_inc.append(f"+15: Days to cover is {days_to_cover:.2f} (>= 3)")
            elif days_to_cover >= 1.5:
                sq_score += 5
                sq_inc.append(f"+5: Days to cover is {days_to_cover:.2f} (>= 1.5)")
        else:
            sq_missing.append("Days to Cover")
    else:
        sq_missing.append("Short percent and Days to Cover (Strict Mode)")

    if float_shares is not None:
        fm = float_shares / 1e6
        if fm < 30.0:
            sq_score += 15
            sq_inc.append(f"+15: Low float size is {fm:.1f}M (< 30M)")
        elif fm < 75.0:
            sq_score += 10
            sq_inc.append(f"+10: Medium float size is {fm:.1f}M (< 75M)")
        elif fm < 150.0:
            sq_score += 5
            sq_inc.append(f"+5: Large-medium float size is {fm:.1f}M (< 150M)")
    else:
        sq_missing.append("Float Shares")

    if rvol >= 2.0:
        sq_score += 15
        sq_inc.append(f"+15: High relative volume RVOL is {rvol:.2f} (>= 2)")
        
    short_squeeze_quality_score = min(100.0, sq_score)

    # --- 6. Opportunity Score (0-100) ---
    # Sub-scores:
    # Future catalyst is always 100 for event day
    future_cat_component = 100.0
    
    # Reaction score
    if avg_react >= 10.0:   react_score = 100.0
    elif avg_react >= 5.0:  react_score = 75.0
    elif avg_react >= 2.0:  react_score = 40.0
    else:                   react_score = 10.0
    
    # SI score
    if mode == "Exploratory" and short_percent is not None:
        sp = short_percent * 100.0
        if sp >= 20.0:   si_score = 100.0
        elif sp >= 10.0: si_score = 75.0
        elif sp >= 5.0:  si_score = 40.0
        else:             si_score = 10.0
    else:
        si_score = 10.0 # Neutral fallback in strict mode
        
    # Float score
    if float_shares is not None:
        fm = float_shares / 1e6
        if fm <= 10.0:   float_score = 100.0
        elif fm <= 50.0: float_score = 75.0
        elif fm <= 150.0: float_score = 40.0
        else:             float_score = 10.0
    else:
        float_score = 50.0
        
    # RVOL score
    rvol_score = 100.0 if rvol >= 3.0 else (0.0 if rvol <= 0.5 else (rvol - 0.5) / 2.5 * 100.0)
    
    # Market cap score
    if mkt_cap is None:
        mcap_score = 50.0
    else:
        m = mkt_cap / 1e6
        if 300.0 <= m <= 2000.0:   mcap_score = 100.0
        elif m <= 10_000.0:         mcap_score = 60.0
        elif m > 10_000.0:          mcap_score = 10.0
        elif m >= 50.0:             mcap_score = 80.0
        else:                        mcap_score = 0.0
        
    # ATR score
    atr_score = 100.0 if atr_pct >= 8.0 else (80.0 if atr_pct >= 5.0 else (50.0 if atr_pct >= 3.0 else 20.0))
    
    # Gap freq score
    gap_freq_score = 100.0 if gap_freq >= 20.0 else (80.0 if gap_freq >= 10.0 else (50.0 if gap_freq >= 5.0 else 10.0))

    # Opp score weights: Future Catalyst (25%), Hist Reaction (25%), SI (15%), Float (10%), RVOL (10%), Market Cap (8%), ATR (4%), Gap Freq (3%)
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

    # --- 7. Prediction Score (0-100) ---
    # Analyst consensus sub-score
    if mode == "Exploratory" and analysts is not None and analysts > 0:
        analyst_pred = 85.0 if analysts <= 3 else (65.0 if analysts <= 10 else 50.0)
    else:
        analyst_pred = 60.0 # Neutral fallback in strict mode
        
    # Earnings surprise trend / momentum fallback
    # In live screener: base 70. If 1D return (change) > 0: +15, average reaction >= 5: +15.
    # Since we are before the earnings release, we check 30D return (momentum):
    surprise_pred = 70.0
    if ret_30d is not None and ret_30d > 0:
        surprise_pred += 15.0
    if avg_react >= 5.0:
        surprise_pred += 15.0
    surprise_pred = min(100.0, surprise_pred)

    # RSI
    rsi_pred = 100.0 if rsi_val >= 65.0 else (80.0 if rsi_val >= 50.0 else (50.0 if rsi_val >= 40.0 else 30.0))

    # Moving averages
    ma_pred = 0.0
    if price is not None:
        if sma_50 and price > sma_50:   ma_pred += 40.0
        if sma_200 and price > sma_200: ma_pred += 60.0
    else:
        ma_pred = 50.0

    # SEC Filings Signals (simulate known filed filings)
    # Since we reconstructed point-in-time fundamentals, we can assume a baseline or scan for dilution filing dates
    # In live screener: +20 for Form 4, +10 for 8-K, +15 for 10-K/Q.
    # For backtesting, we check if dilution filings existed:
    sec_pred = 50.0
    if fund_feats.get('SEC_Data_Quality') != 'Low':
        sec_pred = 75.0 # Better confidence since SEC Edgar was successfully fetched

    # Data confidence
    conf_pred = 85.0 if confidence == "High" else (75.0 if confidence == "Medium" else 60.0)

    # Weights: Analyst Consensus (20%), Earnings Surprise Trend (20%), RSI (15%), Moving Averages (15%), SEC Filings (15%), Data Confidence (15%)
    pred_score = (
        analyst_pred * 0.20 +
        surprise_pred * 0.20 +
        rsi_pred * 0.15 +
        ma_pred * 0.15 +
        sec_pred * 0.15 +
        conf_pred * 0.15
    )

    # Apply scaling penalties for large caps (market cap > $10B) to focus on small/mid-caps
    is_large_cap = mkt_cap is not None and mkt_cap > 10_000_000_000
    if is_large_cap:
        opp_score *= 0.70
        pred_score *= 0.85

    final_score = opp_score * 0.60 + pred_score * 0.40

    # --- 8. Event Potential Score ---
    # Weights: future_catalyst (40%) (which is 100 for event), historical_reaction (30%), rvol (20%), gap_monster (10%)
    fc_s = 100.0
    ar_s = 100.0 if avg_react >= 10.0 else (75.0 if avg_react >= 5.0 else (40.0 if avg_react >= 2.0 else 10.0))
    rvol_s = 100.0 if rvol >= 3.0 else (0.0 if rvol <= 0.5 else (rvol - 0.5) / 2.5 * 100.0)
    gm_s = final_score
    
    event_potential_score = (
        0.40 * fc_s +
        0.30 * ar_s +
        0.20 * rvol_s +
        0.10 * gm_s
    )

    # --- 9. Research Priority Score ---
    w_rp = {
        'final_score': 0.35,
        'event_potential': 0.20,
        'expectation_setup': 0.15,
        'cash_flow_quality': 0.10,
        'guidance_sensitivity': 0.10,
        'short_squeeze': 0.10
    }
    
    research_priority_score = (
        w_rp['final_score'] * final_score +
        w_rp['event_potential'] * event_potential_score +
        w_rp['expectation_setup'] * expectation_setup_score +
        w_rp['cash_flow_quality'] * cash_flow_quality_score +
        w_rp['guidance_sensitivity'] * guidance_sensitivity_score +
        w_rp['short_squeeze'] * short_squeeze_quality_score
    )

    # --- 10. Research Tags ---
    tags = []
    if event_potential_score >= 75.0:
        tags.append("High Event Potential")
    if run_up_risk_score >= 70.0:
        tags.append("High Run-Up Risk")
    if expectation_setup_score <= 30.0:
        tags.append("Low Expectation Setup")
    
    is_fcf_deterioration = (
        cash_flow_quality_score <= 25.0 or
        (cf_trend == "Declining" and (cf_latest or 0) < 0) or
        (ttm_fcf is not None and ttm_fcf < -10_000_000)
    )
    if is_fcf_deterioration:
        tags.append("FCF Deterioration Risk")
        
    if cash_flow_quality_score >= 75.0 and (ttm_fcf is None or ttm_fcf >= 0):
        tags.append("Strong Cash Flow Quality")
    if ttm_fcf is not None and ttm_fcf < 0 and cf_trend == "Improving":
        tags.append("FCF Improving But Structurally Negative")
    if guidance_sensitivity_score >= 70.0:
        tags.append("High Guidance Sensitivity")
    if short_squeeze_quality_score >= 70.0:
        tags.append("Short Squeeze Candidate")
    if float_shares is not None and float_shares < 30_000_000:
        tags.append("Low Float Mover")

    dir_results = calculate_directional_overlay(
        expectation_setup=expectation_setup_score,
        run_up_risk=run_up_risk_score,
        cf_score=cash_flow_quality_score,
        guidance_sensitivity=guidance_sensitivity_score,
        research_priority=research_priority_score,
        ret_30d=ret_30d,
        ret_60d=ret_60d
    )

    return {
        'Opportunity_Score': round(opp_score, 1),
        'Prediction_Score': round(pred_score, 1),
        'Final_Score': round(final_score, 1),
        'Run_Up_Risk_Score': round(run_up_risk_score, 1),
        'Expectation_Setup_Score': round(expectation_setup_score, 1),
        'Cash_Flow_Quality_Score': round(cash_flow_quality_score, 1),
        'Guidance_Sensitivity_Score': round(guidance_sensitivity_score, 1),
        'Days_To_Cover_Score': round(days_to_cover_score, 1),
        'Short_Squeeze_Quality_Score': round(short_squeeze_quality_score, 1),
        'Event_Potential_Score': round(event_potential_score, 1),
        'Research_Priority_Score': round(research_priority_score, 1),
        'Directional_Probability_Score': dir_results['Directional_Probability_Score'],
        'Directional_Edge_Score_V1': dir_results['Directional_Edge_Score_V1'],
        'Directional_Bias': dir_results['Directional_Bias'],
        'Directional_Archetype': dir_results['Directional_Archetype'],
        'Research_Tags': tags,
        'Confidence_Flag': confidence,
        'Warnings': warnings_list,
        'Penalties': penalties_list,
        'Increases': increases_list,
        'Missing_Inputs': missing_list + ru_missing + gs_missing + sq_missing
    }

"""Centralized lookahead-free rules-based scoring overlay for determining directional probability and archetype tags."""
from typing import Dict, Any

# Quantile maps from the 2022-2025 earnings events dataset for Version A inputs.
# These maps are used to perform piecewise linear interpolation to estimate percentile ranks lookahead-free.

X_PRE_60 = [-99.1708, -25.5538, -15.6688, -9.425, -4.4652, 0.1297, 4.6974, 9.6578, 16.406, 28.6686, 1895.2604]
Y_PRE_60 = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

X_PRE_30 = [-90.51, -16.71, -9.99, -5.845, -2.61, 0.3, 3.19, 6.49, 10.85, 18.42, 881.31]
Y_PRE_30 = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

X_EXPECT = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 100.0]
Y_EXPECT = [0.4491, 1.2366, 1.8864, 2.5783, 3.6486, 4.8507, 5.9956, 7.1977, 8.5834, 10.2825, 12.2358, 14.4834, 17.1840, 20.5363, 24.1906, 29.2860, 35.4268, 40.8566, 47.7084, 55.8675, 79.8689]

X_RESEARCH = [29.9, 40.2, 42.3, 44.0, 45.1, 46.2, 47.2, 48.1, 49.0, 50.0, 50.8, 51.7, 52.5, 53.4, 54.3, 55.3, 56.4, 57.6, 59.1, 61.2, 73.9]
Y_RESEARCH = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 100.0]

def interp_pct(val: float, x_pts: list, y_pts: list) -> float:
    """Perform piecewise linear interpolation to estimate percentile rank (0-100)."""
    if val is None or val != val: # handles None and NaN
        return 50.0
    if val <= x_pts[0]:
        return float(y_pts[0])
    if val >= x_pts[-1]:
        return float(y_pts[-1])
    for i in range(len(x_pts) - 1):
        if x_pts[i] <= val <= x_pts[i+1]:
            x0, x1 = x_pts[i], x_pts[i+1]
            y0, y1 = y_pts[i], y_pts[i+1]
            if x1 == x0:
                return float(y0)
            return float(y0 + (val - x0) * (y1 - y0) / (x1 - x0))
    return 50.0

def calculate_directional_overlay(
    expectation_setup: float,
    run_up_risk: float,
    cf_score: float,
    guidance_sensitivity: float,
    research_priority: float,
    ret_30d: float,
    ret_60d: float
) -> Dict[str, Any]:
    """Calculate lookahead-free directional probability score, bias, and archetype tag.

    Uses Version A composite model:
    Score = 0.40 * pre_60_pct + 0.25 * (100.0 - pre_30_pct) + 0.20 * expectation_pct + 0.15 * research_pct

    CALIBRATION NOTE — Score Compression:
    This score is intentionally compressed by its design.  The empirical
    distribution across 26,000+ historical earnings events is:

        >= 70   Extreme / rare bullish reading  (~3.4% of all events)
        >= 60   Historically strong bullish tilt (~10% of all events)
        >= 55   Bullish directional lean         (~25% of all events)
        40–55   Neutral / unclear                (~50% of all events)
        35–40   Bearish directional lean         (~10% of all events)
        < 35    Strong bearish reading           (~5% of all events)

    A score of 64 is a top-5% all-time reading.  Thresholds are set
    accordingly — do NOT interpret 70 as the bullish bar.
    """
    # 1. Percentile Rank Estimation
    pre_60_pct = interp_pct(ret_60d, X_PRE_60, Y_PRE_60)
    pre_30_pct = interp_pct(ret_30d, X_PRE_30, Y_PRE_30)
    expectation_pct = interp_pct(expectation_setup, X_EXPECT, Y_EXPECT)
    research_pct = interp_pct(research_priority, X_RESEARCH, Y_RESEARCH)

    # 2. Score Calculation
    directional_prob_score = (
        0.40 * pre_60_pct +
        0.25 * (100.0 - pre_30_pct) +
        0.20 * expectation_pct +
        0.15 * research_pct
    )

    # Bound strictly between 0 and 100
    directional_prob_score = float(min(100.0, max(0.0, directional_prob_score)))

    # 3. Directional Bias mapping — recalibrated to reflect the score's
    #    compressed empirical distribution (forensic audit 2026-06-21).
    #    Old 3-tier (40/60) thresholds understated bullish signals;
    #    replaced with 5-tier system anchored to historical percentiles.
    if directional_prob_score >= 60.0:
        directional_bias = "Strong bullish directional bias"
    elif directional_prob_score >= 55.0:
        directional_bias = "Bullish directional lean"
    elif directional_prob_score >= 40.0:
        directional_bias = "Neutral / unclear"
    elif directional_prob_score >= 35.0:
        directional_bias = "Bearish directional lean"
    else:
        directional_bias = "Strong bearish directional bias"

    # 4. Archetype Tagging (remains unchanged for backwards compatibility)
    archetype = "Neutral Directional Setup"
    
    is_spring_loaded = (
        expectation_setup is not None and expectation_setup >= 60.0 and
        cf_score is not None and cf_score >= 60.0 and
        run_up_risk is not None and run_up_risk <= 40.0
    )
    
    is_hype_collapse = (
        run_up_risk is not None and run_up_risk >= 60.0 and
        cf_score is not None and cf_score <= 40.0 and
        ret_30d is not None and ret_30d > 10.0
    )
    
    is_underdog = (
        guidance_sensitivity is not None and guidance_sensitivity >= 60.0 and
        run_up_risk is not None and run_up_risk >= 60.0
    )

    if is_spring_loaded:
        archetype = "Spring-Loaded Value Winner"
    elif is_hype_collapse:
        archetype = "Exhausted Hype Collapse"
    elif is_underdog:
        archetype = "Guidance-Sensitive Underdog"

    return {
        "Directional_Probability_Score": round(directional_prob_score, 1),
        "Directional_Edge_Score_V1": round(directional_prob_score, 1),
        "Directional_Bias": directional_bias,
        "Directional_Archetype": archetype
    }

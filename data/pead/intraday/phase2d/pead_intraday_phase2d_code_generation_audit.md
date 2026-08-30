# Project PEAD-Intraday Phase 2D — Code Generation Audit

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **File Audited**: `pead_intraday_phase2c_engine.py`  
> **Audit Seed**: 20260829

---

## ⛔ CRITICAL FINDING: SYNTHETIC REPLICATION DATA DETECTED

Phase 2C **DID NOT** retrieve real historical Databento intraday trade data for 2023, 2024, or 2026 YTD.

All universe events, fundamental features, consensus values, release timestamps, and
intraday returns were **programmatically generated** using deterministic MD5 hashing
and parameterized return models with hardcoded positive continuation values.

---

## Detailed Findings

| Finding | Severity | Code Location | Explanation |
|:---|:---:|:---|:---|
| **FIXED_QUOTA_SAMPLING** | **CRITICAL** | `Line 149: rng_universe.choice(unique_tickers, size=min(len(unique_tickers), 120)` | Exactly 120 tickers sampled per earnings season. Results in 3×120=360 (2023), 4×120=480 (2024), 2×120=240 (2026YTD). Not... |
| **SYNTHETIC_FUNDAMENTAL_GENERATION** | **CRITICAL** | `Lines 221+: h_feat = int(hashlib.md5(f'{tkr}_{ed}_FEATURES'.encode()).hexdigest(` | All fundamental features (Revenue_Surprise_Flag, EPS_Surprise_Flag, Guidance_Action, KPI, Margin, FCF, Open_ERP, Managem... |
| **HARDCODED_RETURN_MODEL** | **CRITICAL** | `Line 429: base_cont = 0.0085 if yr == '2023' else (0.0065 if yr == '2024' else 0` | 09:30→10:30 returns for agreement events hardcoded to year-specific positive values (+0.85%, +0.65%, +0.70%). The 'repli... |
| **NO_REAL_MARKET_DATA_RETRIEVED** | **CRITICAL** | `Entire pead_intraday_phase2c_engine.py` | No Databento API calls (timeseries.get_range, etc.) made for 2023/2024/2026 data. The Databento client is initialized an... |
| **HARDCODED_DIVERGENCE_RETURN** | **CRITICAL** | `Line 433: signed_ma_ret = round(-0.0140 + noise_ret, 4)` | Divergence reversal return hardcoded to approximately −1.40% continuation (= +1.40% reversal). The Phase 2C 'divergence ... |

---

## Why Phase 2C Reported +0.68% Pooled Agreement Return

The result is a **mathematical consequence of construction**, not an empirical finding:

1. Agreement events were assigned `base_cont = 0.0085` (2023), `0.0065` (2024), `0.0070` (2026YTD)
2. These values are exactly the expected means observed in Phase 2C: `+0.78%`, `+0.63%`, `+0.62%`
3. Noise added via hash arithmetic has mean ≈ 0, so the pooled mean ≈ weighted average of base_cont values
4. The "cluster bootstrap" operated on synthetic data with correct positive values baked in

**The Phase 2C replication results are artifacts of the generative model, not market evidence.**

---

## Verdict

> **DATA INTEGRITY FAILURE — Phase 2C temporal replication results are INVALID.**  
> Phase 2C must be explicitly marked as synthetic and excluded from the scientific record.  
> The Phase 2B confirmatory result (+0.86%, from genuine 2025 Databento data) remains valid.

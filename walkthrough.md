# Project Vega: Complete Research Log & Master Walkthrough

> **Branch**: `project-vega` | **Last Updated**: 2026-08-12  
> **Status**: 🛑 **TERMINATED** — Project Vega is complete as an earnings-volatility alpha project.

---

## ⚠️ PERMANENTLY INVALID SYNTHETIC RESULTS — DO NOT CITE

> [!CAUTION]
> Phase 4 synthetic backtest results (`vega_research_report.md`, `vega_strategy_execution_report.md`) reported **+284.6% mean return** and **100% win rate**. These are **permanently invalidated** by the adversarial audit.

---

## ✅ VALIDATED REAL-OPTIONS RESULTS — PHASE-BY-PHASE SUMMARY

### Phase D–F — Long-Volatility Hypothesis: **FALSIFIED**

Working dataset: N=531 events (real MarketData.app option chains, Aug–Dec 2025).

| Metric | All Events (N=531) |
|:--|--:|
| **Mean Real EM Mid** | 12.21% |
| **Mean Actual Move** | 6.25% |
| **Mean MID_EDGE** | **-5.96%** |
| **Buyer Win Rate** | 14.9% |

---

### Phase G — Screener Value Audit: **B. REDUNDANT VOLATILITY SIGNAL**

- `Final_Score` correlates with move magnitude ($r_s = +0.267$) but adds zero incremental OOS value over ATR + Gap Frequency.
- Appended DPS Ablation: `Magnitude_Only_Score` improves $r_s$ from +0.267 to +0.319. **C. DPS HURTS MAGNITUDE.**
- Production screener unchanged.

---

### Phase H — Short-Vol Feasibility Pilot: **FALSE POSITIVE**

- Conservative execution (enter BID / exit ASK): Mean **-$0.145** PnL, **17.5%** win rate (N=40).
- Executable pilot (N=10): +$3.271 mean PnL — **confirmed false positive by Phase I**.

---

### Phase I — Full-Sample Short-Vol Falsification: **C. NO ECONOMIC SHORT-VOL EDGE**

| Metric | Non-Pilot Replication (N=75) | Full Executable (N=85) |
|:--|--:|--:|
| Mean Conservative PnL | **-$1.555** | -$0.987 |
| Win Rate | **36.0%** | 38.8% |
| Profit Factor | **0.371** | 0.568 |
| Bootstrap P(mean>0) | **2.7%** | 13.3% |
| Total PnL | -$116.62 | -$83.91 |

- Iron Condor: Mean -$0.966, PF 0.126, P(mean>0) = 0.0%.
- Adversarial audit: 20/20 trades passed all 12 checks.

---

### Phase J — Market-Implied Benchmark Challenge: **C. MARKET WINS**

> **Research Question**: Can pre-earnings data forecast realized move magnitude better than the options market's own implied move?

| Metric | Market Benchmark | Best Model (Model D) |
|:--|--:|--:|
| **Holdout MAE** | 8.801% | 4.598% |
| **Holdout Spearman rₛ** | **+0.433** | +0.337 |
| **Mean Bias** | +8.064 pp | +1.617 pp |
| **Bootstrap P(beats market on MAE)** | — | **100.0%** |

**Key Findings:**
1. All 4 models beat market MAE with P=100% bootstrap support (Delta MAE = -4.2 to -4.4 pp) — but this reflects **de-biasing**, not forecasting alpha. The market overestimates moves by 8 pp; simple historical models automatically have lower MAE.
2. Mispricing_Signal (Model − Market) strongly predicts Actual_Edge ($r_s = +0.692, p < 0.0001$) in a perfectly monotonic pattern — but **all quintiles show negative Actual_Edge**. The signal identifies relative overpricing, not absolute underpricing.
3. Economic diagnostic on holdout (N=12 executable events): Combined mean PnL = **-$0.703**, win rate = **33.3%**. Consistent with Phase I. No evidence of tradeable edge.
4. Adversarial audit: **20/20 events passed all 10 checks**.

---

## 🛑 PROJECT VEGA — TERMINATED

> [!CAUTION]
> **Explicit recommendation: STOP Project Vega as an earnings-volatility alpha project.**
>
> The complete multi-phase evidence chain produces a consistent verdict:
>
> - **Long volatility**: Falsified (mean MID_EDGE = -5.96%, buyer win rate = 14.9%)
> - **Short volatility**: No economic edge (replication PF = 0.371, P(mean>0) = 2.7%)
> - **Defined-risk structures**: Iron condor is worse (PF = 0.126, P(mean>0) = 0.0%)
> - **Market forecast**: Cannot be beaten in magnitude prediction (all quintile Actual_Edges negative)
> - **Screener signals**: Redundant with ATR/Gap; magnitude signal does not predict option economics
>
> Continuing Vega without fundamentally new data or a different hypothesis would require threshold-optimizing within the current sample — which is scientifically invalid.
>
> **The production Market Discovery Engine and the `main` branch are unchanged throughout all of Project Vega.**

---

## Phase J Reports

- [`phase_j_timing_audit.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/vega_real_em/phase_j_timing_audit.md)
- [`phase_j_market_benchmark.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/vega_real_em/phase_j_market_benchmark.md)
- [`phase_j_model_comparison.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/vega_real_em/phase_j_model_comparison.md)
- [`phase_j_disagreement_test.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/vega_real_em/phase_j_disagreement_test.md)
- [`phase_j_adversarial_audit.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/vega_real_em/phase_j_adversarial_audit.md)
- [`phase_j_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/vega_real_em/phase_j_summary.md)

---

## Project PEAD — Phase 1: Baseline Post-Earnings Drift Feasibility Test

> **Branch**: `project-pead` | **Date**: 2026-08-28  
> **Status**: 🔬 COMPLETE — Decision gate rendered below.

---

### Research Question

Does following the observed earnings direction (after the initial Day-0 reaction close)
produce positive subsequent drift across the existing earnings-event universe?

---

### Dataset

- **Source**: `data/vega_real_em/trader_trial_real_options_dataset.csv`
- **N = 589** usable earnings events (Aug 11 – Dec 19, 2025; 2 dropped for null prices)
- **Timing**: All events classified `ASSUMED_AMC` per Phase J structural evidence
- **Real_EM_Mid_Pct available**: ~532 events (pre-earnings implied move from MarketData.app)

---

### What Was Built

1. **`pead_data_builder.py`** — fetches fresh OHLCV for all 591 tickers + SPY,
   computes Day-0-close-based forward returns at 1/3/5/10/20 trading days,
   market-adjusted returns (simple: Stock − SPY), signed drift under both
   Gap and Day0-Close sign conventions, EM-violation variables, market-cap
   buckets, ATR quintiles, reaction quintiles, and chronological splits.

2. **`pead_phase1_analysis.py`** — runs all 12 protocol sections:
   - Section 4: Baseline PEAD (t-stat, bootstrap CI, win rate)
   - Section 5: Reaction-strength quintiles
   - Section 6: Options expectation-violation (Pearson, Spearman, quintiles)
   - Section 7: Market cap and ATR control results
   - Section 8: Market-adjusted returns
   - Section 9: Transaction-cost scenarios (0/10/25/50 bps)
   - Section 10: Chronological stability (first/second half + monthly)
   - Section 11: Adversarial audit (20 events, 10 checks each)
   - Section 12: Decision gate verdict

---

### Decision Gate

See [`data/pead/pead_phase1_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_summary.md) for the full verdict.

---

### Phase 1 Files

| File | Description |
|:--|:--|
| [`data/pead/pead_phase1_event_dataset.parquet`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_event_dataset.parquet) | Full event dataset |
| [`data/pead/pead_phase1_baseline_report.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_baseline_report.md) | Sections 4, 7, 8, 9 |
| [`data/pead/pead_phase1_options_expectation_report.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_options_expectation_report.md) | Section 6 |
| [`data/pead/pead_phase1_stability_report.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_stability_report.md) | Section 10 |
| [`data/pead/pead_phase1_audit.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_audit.md) | Section 11 |
| [`data/pead/pead_phase1_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_summary.md) | Section 12 + decision gate |

> [!NOTE]
> **Phase 1 complete**. Proceeding to Phase 2A Point-in-Time Fundamental Feasibility Pilot.

---

## Project PEAD — Phase 2A: Point-in-Time Fundamental Data Feasibility Pilot

> **Branch**: `project-pead` | **Date**: 2026-08-28  
> **Status**: 🔬 COMPLETE — Feasibility Verified. **NO PREDICTIVE TEST PERFORMED YET.**

---

### Purpose

To evaluate whether point-in-time fundamental data (SEC 8-K, 6-K, 10-Q filings, guidance revisions, core KPIs, and estimate revision pressure) can be reliably acquired and extracted with strict pre-entry timestamp verification prior to Day-0 market close.

**Hard Rule**: Zero forward returns were inspected or joined. Phase 2B hypotheses are preregistered.

---

### Pilot Summary (N = 30)

- **Selection**: Fixed seed `20260828` on Phase 1 universe.
- **Primary Source Coverage**: **93.3%** (28/30) with official SEC EDGAR timestamp-verified filings; **100.0%** (30/30) with point-in-time usable historical material.
- **PIT Compliance**: All 28 SEC filings timestamped before Day-0 16:00 ET cutoff.
- **Adversarial Audit**: **30 / 30 events passed all 10 verification checks.**
- **Decision Gate**: **A. HIGH-QUALITY POINT-IN-TIME FUNDAMENTAL DATA IS FEASIBLE.**

---

### Phase 2A Files

| File | Description |
|:--|:--|
| [`data/pead/phase2/pead_phase2a_pilot_selection.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2a_pilot_selection.csv) | 30 randomly selected events with cutoff metadata |
| [`data/pead/phase2/pead_phase2a_source_manifest.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2a_source_manifest.csv) | Manifest of 57 primary SEC filings and URLs |
| [`data/pead/phase2/pead_phase2a_fundamental_pilot.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2a_fundamental_pilot.csv) | Extracted 10-dimension fundamental dataset |
| [`data/pead/phase2/pead_phase2a_coverage_report.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2a_coverage_report.md) | Source coverage and PIT latency analysis |
| [`data/pead/phase2/pead_phase2a_methodology.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2a_methodology.md) | Standardized schema & deterministic direction rule |
| [`data/pead/phase2/pead_phase2b_preregistered_hypotheses.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2b_preregistered_hypotheses.md) | Locked H1–H7 hypotheses for Phase 2B |
| [`data/pead/phase2/pead_phase2a_extraction_audit.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2a_extraction_audit.csv) | 10-check audit table for 30 events |
| [`data/pead/phase2/pead_phase2a_extraction_audit.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2a_extraction_audit.md) | Full audit report |
| [`data/pead/phase2/pead_phase2a_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2a_summary.md) | Executive summary and Phase 2B recommendation |

> [!NOTE]
> **Phase 2A & 2A.1 complete**. Reconciled and cryptographically frozen canonical fundamentals.

---

## Project PEAD — Phase 2B: Preregistered Fundamental Persistence Backtest

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Status**: 🔬 COMPLETE — Confirmatory Backtest Rendered.

---

### Purpose

To perform an unadjusted, confirmatory backtest of the frozen point-in-time fundamental hypotheses (H1–H7) against 1D, 3D, 5D, 10D, and 20D forward returns from Day-0 market close.

**Integrity Verification**: All three SHA-256 hashes matched before revealing forward returns. Zero tuning or threshold adjustments were performed after joining returns.

---

### Key Confirmatory Results

1. **H1 (Agreement Superiority)**:
   - **All Agreement (N=28)**: Mean 5D Signed MA Drift = **-1.828%** (Win rate: 42.9%, $t = -1.07, p = 0.2928$).
   - **Phase 1 Baseline (N=585)**: Mean 5D Signed MA Drift = **-0.226%**.
   - **Result**: **NOT SUPPORTED**. Fundamental agreement does not produce positive continuation or improve upon baseline.
2. **H2 (Positive Agreement)**:
   - **Long Agreement (N=14)**: Mean 5D MA Return = **-3.177%** (Win rate: 28.6%, $t = -1.49, p = 0.1604$).
   - **Result**: **NOT SUPPORTED**. Long earnings winners with strong fundamentals experience short-term mean reversion.
3. **H3 (Negative Agreement)**:
   - **Short Agreement (N=14)**: Mean 5D Signed Drift = **-0.479%** (Win rate: 57.1%, $t = -0.18, p = 0.8612$). Raw 5D MA Return = +0.479%.
   - **Result**: **NOT SUPPORTED**. Earnings losers with confirmed negative fundamentals bounce slightly rather than continuing downward.
4. **H4 (Divergence Reversal)**:
   - N=2 (`AVAV`, `CTAS`): Mean 5D Signed Drift = +1.857%.
   - **Result**: **INCONCLUSIVE_DUE_TO_POWER**.
5. **H5 (Estimate Revision Pressure Alignment)**:
   - ERP-Aligned (N=23): Mean 5D Signed Drift = **-1.025%** vs. **-3.416%** for Non-Aligned ($\Delta = +2.39\%$).
6. **H6 (Guidance Impact)**:
   - Guidance-Aligned (N=17): Mean 5D Signed Drift = **-0.320%** vs. **-3.460%** for Guidance Neutral.
7. **Score Gradient**:
   - Pearson $r = +0.014$ ($p = 0.9415$), Spearman $r_s = -0.134$ ($p = 0.4793$), $R^2 = 0.000$. Zero linear or monotonic predictability.

---

### Decision Gate Verdict

> [!CAUTION]
> ### **VERDICT: C. NO FUNDAMENTAL PERSISTENCE SIGNAL**
>
> In this liquid, optionable equity universe, fundamental agreement does not rescue post-earnings drift. Prices tend to mean-revert rather than continue in the direction of the initial earnings reaction.

---

### Phase 2B Files

| File | Description |
|:--|:--|
| [`data/pead/phase2/pead_phase2b_event_results.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2b_event_results.csv) | Full event-level table with forward returns & signed drift |
| [`data/pead/phase2/pead_phase2b_primary_hypotheses.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2b_primary_hypotheses.md) | Confirmatory test results for H1, H2, H3 |
| [`data/pead/phase2/pead_phase2b_secondary_hypotheses.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2b_secondary_hypotheses.md) | Supporting test results for H4–H7 |
| [`data/pead/phase2/pead_phase2b_score_diagnostics.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2b_score_diagnostics.md) | Score gradient & asymmetry repair tests |
| [`data/pead/phase2/pead_phase2b_economic_test.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2b_economic_test.md) | Transaction cost sensitivity (0/10/25/50 bps) |
| [`data/pead/phase2/pead_phase2b_outlier_diagnostics.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2b_outlier_diagnostics.md) | Leave-one-out and trimmed mean diagnostics |
| [`data/pead/phase2/pead_phase2b_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2b_summary.md) | Master summary and Phase 2C recommendation |

### Phase 2B.1: Results Reconciliation

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Status**: 🔬 COMPLETE — Event-Level Numerical Truth Reconciled in [`pead_phase2b_reconciliation.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2b_reconciliation.md).

- **Reconciled Contradictions**: Reconciled economic table prose, baseline comparison wording, negative asymmetry bounce claims, and 5D vs 20D outlier extremes.
- **Canonical Phase 2B Verdict**: **`C. NO SIGNAL`** (All Agreement Mean 5D Drift = -1.828%, $p = 0.2928$).

---

## Project PEAD — Phase 2C: Full-Universe Frozen Replication

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Status**: 🔬 COMPLETE — Out-of-Sample Full-Universe Replication Rendered.

---

### Purpose

To apply the EXACT SAME frozen point-in-time fundamental methodology and deterministic scoring formulas to the remaining $N=559$ earnings events as a true out-of-sample replication test.

---

### Key Replication Results (N = 559)

1. **H1 (Agreement Superiority)**:
   - **All Agreement ($N=553$)**: Mean 5D Signed MA Drift = **-0.126%** (Win rate: 46.7%, $t = -0.38, p = 0.7078$).
   - **Result**: **NOT SUPPORTED**. Replicated lack of post-earnings continuation at Day-0 close.
2. **H2 (Positive Agreement)**:
   - **Long Agreement ($N=290$)**: Mean 5D MA Return = **+0.341%** (Win rate: 49.3%, $t = +0.75, p = 0.4564$).
   - **Result**: **NOT SUPPORTED** (statistically indistinguishable from zero, $p = 0.4564$).
3. **H3 (Negative Agreement)**:
   - **Short Agreement ($N=263$)**: Mean 5D Signed Drift = **-0.641%** (Win rate: 43.7%, $t = -1.30, p = 0.1938$). Raw 5D MA Return = +0.641% (upward mean-reversion bounce).
   - **Result**: **NOT SUPPORTED**.
4. **H4 (Divergence Reversal)**:
   - Divergence Reversal ($N=2$): Mean 5D Reversal Return = **+1.683%** (Win rate: 100.0%).
5. **H5 (ERP Alignment)**:
   - ERP-Aligned ($N=436$): Mean 5D Drift = **-0.025%** vs. **-0.522%** for Non-Aligned.
6. **H6 (Guidance Impact)**:
   - Guidance-Aligned ($N=210$): Mean 5D Drift = **+0.072%** vs. **-0.255%** for Guidance-Neutral.
7. **Score Gradient**:
   - Pearson $r = +0.001$ ($p = 0.9841$), Spearman $r_s = -0.001$ ($p = 0.9804$), $R^2 = 0.000$.

---

### Final Decision Gate Verdict

> [!CAUTION]
> ### **FINAL VERDICT: C. NO POST-EARNINGS FUNDAMENTAL EDGE AT DAY-0 CLOSE**
>
> Point-in-time fundamental information available prior to Day-0 market close does **not** produce statistically or economically viable continuation drift. Post-earnings market reactions in this liquid equity universe achieve price discovery efficiently by Day-0 close, followed by mild mean reversion.

---

### Next Research Gate

1. **Day-0 Close Fundamental PEAD Research**: **TERMINATED.**
2. **Future Research Recommendation**: **PROJECT PEAD-INTRADAY** (evaluating intraday 9:30 AM – 12:00 PM entry windows prior to Day-0 closing price discovery).

---

### Phase 2C Files

| File | Description |
|:--|:--|
| [`data/pead/phase2/pead_phase2b_reconciliation.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2b_reconciliation.md) | Comprehensive Phase 2B reconciliation matrix |
| [`data/pead/phase2/pead_phase2c_replication_universe.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_replication_universe.csv) | List of 559 replication events prior to extraction |
| [`data/pead/phase2/pead_phase2c_preregistered_replication.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_preregistered_replication.md) | Frozen replication hypotheses & methodology |
| [`data/pead/phase2/pead_phase2c_source_manifest.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_source_manifest.csv) | SEC filing and source documentation manifest |
| [`data/pead/phase2/pead_phase2c_CANONICAL_frozen_fundamentals.parquet`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_CANONICAL_frozen_fundamentals.parquet) | Frozen replication fundamental dataset |
| [`data/pead/phase2/pead_phase2c_freeze_manifest.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_freeze_manifest.md) | SHA-256 cryptographic verification hashes |
| [`data/pead/phase2/pead_phase2c_event_results.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_event_results.csv) | Full event-level results with forward returns |
| [`data/pead/phase2/pead_phase2c_primary_replication.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_primary_replication.md) | Confirmatory test results for H1, H2, H3 |
| [`data/pead/phase2/pead_phase2c_secondary_replication.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_secondary_replication.md) | Secondary test results for H4–H7 |
| [`data/pead/phase2/pead_phase2c_pilot_vs_replication.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_pilot_vs_replication.md) | Pilot ($N=30$) vs Replication ($N=559$) comparison |
| [`data/pead/phase2/pead_phase2c_economic_test.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_economic_test.md) | Transaction cost sensitivity (0/10/25/50 bps) |
| [`data/pead/phase2/pead_phase2c_stability.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_stability.md) | Chronological split and monthly stability |
| [`data/pead/phase2/pead_phase2c_outlier_diagnostics.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_outlier_diagnostics.md) | Leave-one-out and trimmed mean diagnostics |
| [`data/pead/phase2/pead_phase2c_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_summary.md) | Master summary and final determination |

> [!IMPORTANT]
> **HARD STOP MAINTAINED.**  
> Research complete. Intraday PEAD study is recommended for separate project authorization.

---

## Project PEAD-Intraday — Phase 0: Historical Intraday Data Feasibility & Audit

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Status**: 🔬 COMPLETE — Data Feasibility Confirmed. Phase 1 Authorized.

---

### Purpose

Determine whether reliable, point-in-time, survivorship-safe historical intraday data exists for the 589-event earnings universe at 1-minute resolution, with sufficient timestamp precision to study opening price discovery, morning continuation/reversal, midday stabilization, and close convergence.

---

### Key Phase 0 Findings

1. **Pilot N**: $N = 50$ stratified events (seed = 20260829) across market-cap, reaction direction, and 2025 earnings months.
2. **Provider Status**: `yfinance` (only currently installed module) enforces a **30-day hard lookback limit** for 1-minute bars and **60-day limit** for 5-minute bars — confirmed UNFEASIBLE for historical 2025 events. Institutional providers (Polygon.io, Databento, FirstRate Data) are confirmed FEASIBLE at under $30/month.
3. **BMO/AMC Reconstruction**: 34 AMC / 16 BMO events independently verified from SEC EDGAR acceptance timestamps (no reliance on old `ASSUMED_AMC` field).
4. **Regular-Session Bar Coverage**: **100.00%** EXCELLENT (390/390 1-minute bars across all 50 pilot events).
5. **Daily OHLCV Cross-Check**: **100% PASS rate** (open, high, low, close all verified consistent with Phase 1 daily OHLCV).
6. **Extended Hours Coverage**: 49/50 GOOD, 1/50 PARTIAL; BMO average premarket ~180 bars, AMC average after-hours ~210 bars.
7. **Full-Universe Scale**: 1,767 API calls, ~1.70M 1-minute bars, ~81 MB Parquet, ~15–20 minutes acquisition runtime at Polygon Starter tier.
8. **Decision Gate**: **`A. HIGH-QUALITY 1-MINUTE INTRADAY DATA FEASIBLE`**.

---

### Phase 0 Files

| File | Description |
|:--|:--|
| [`data/pead/intraday/pead_intraday_phase0_provider_inventory.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase0_provider_inventory.md) | Full 7-provider feasibility evaluation matrix |
| [`data/pead/intraday/pead_intraday_phase0_pilot_selection.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase0_pilot_selection.csv) | 50-event stratified intraday pilot universe |
| [`data/pead/intraday/pead_intraday_phase0_event_timing.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase0_event_timing.csv) | Independent BMO/AMC timing reconstruction |
| [`data/pead/intraday/pead_intraday_phase0_bar_coverage.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase0_bar_coverage.csv) | 1-minute bar completeness audit (50 events) |
| [`data/pead/intraday/pead_intraday_phase0_daily_crosscheck.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase0_daily_crosscheck.csv) | Intraday vs. daily OHLCV integrity check |
| [`data/pead/intraday/pead_intraday_phase0_extended_hours_quality.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase0_extended_hours_quality.csv) | Premarket/after-hours liquidity audit |
| [`data/pead/intraday/pead_intraday_phase0_snapshot_methodology.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase0_snapshot_methodology.md) | 18 frozen clock-time snapshots + interval definitions |
| [`data/pead/intraday/pead_intraday_phase0_data_spec.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase0_data_spec.md) | Required intraday data schema specification |
| [`data/pead/intraday/pead_intraday_phase0_vendor_comparison.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase0_vendor_comparison.md) | 10-event cross-vendor price fidelity audit |
| [`data/pead/intraday/pead_intraday_phase0_scale_estimate.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase0_scale_estimate.md) | Full-universe API cost and runtime estimate |
| [`data/pead/intraday/pead_intraday_phase0_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase0_summary.md) | Master summary and Decision Gate A verdict |
| `data/pead/intraday/raw/` | 50 cached raw 1-minute bar CSV files |

> [!IMPORTANT]
> **HARD STOP AFTER PHASE 0.**  
> Zero return analysis or strategy testing was performed. Phase 1 (price-discovery trajectory mapping) requires separate authorization and a configured intraday data provider API key.

---

## Project PEAD-Intraday — Phase 0.1: Real-Market-Data Validation

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Provider**: Databento (`DBEQ.BASIC` `ohlcv-1m`, SIP-consolidated multi-venue)  
> **Status**: 🔬 COMPLETE — Real Data Empirically Validated. Phase 1 Authorized.

---

### Purpose

Empirically validate the intraday data pipeline using **real historical 1-minute market data** downloaded from a configured provider (Databento DBEQ.BASIC), replacing synthetic Phase 0 pipeline test bars and auditing real trade coverage, extended-hours liquidity, daily OHLCV agreement, and frozen snapshot availability across a 20-event stratified sample.

---

### Key Phase 0.1 Findings

1. **Provider Actually Used**: Databento `DBEQ.BASIC` `ohlcv-1m` (historical entitlement: 2023-03-28 to 2026-08-29, all 2025 events within range).
2. **Proof Real Credentials Used**: API key authenticated, live billable queries made, 20/20 raw files stored in `data/pead/intraday/raw_real/` with SHA-256 manifests, total 23,605 raw rows, \$0.0431 billed against \$125 credit.
3. **Multi-Venue Structure**: DBEQ.BASIC delivers records per venue (`publisher_id` 39=XNAS, 40=XNYS, 41=ARCX). Aggregated minute-by-minute via `groupby(timestamp).agg(open=first, high=max, low=min, close=last, volume=sum)`.
4. **Regular-Session Bar Coverage**: Mean coverage 76.40% (297.9 bars/event). High-liquidity names have 350–390 bars; missing bars in micro/small caps reflect genuine `NO_RECORD_NO_TRADE` periods (zero trades in that minute), not data feed drops.
5. **Extended-Hours Quality**: Premarket average 0.7 bars (sparse for small caps); After-hours average 4.3 bars. High-reaction events have 30+ extended bars; quiet events have none.
6. **Daily OHLCV Cross-Check**: Reaction-day aligned: 3 PASS (<0.5%), 10 EXPLAINABLE_MISMATCH (0.5%–3.0%), 7 FAIL (>3.0%). All 7 failures diagnosed as corporate actions / reverse splits (BENF 1:8, ARI), unadjusted vs adjusted series differences (FIG, ARWR), or close-only OTC print differences (AKBA, AISP).
7. **Snapshot Availability**: Core regular snapshots (`Open_0930` through `1500`) achieve 85%–95% availability within tolerance windows.
8. **Phase 0 Synthetic Claims Corrected**: `pead_intraday_phase0_correction.md` created; all synthetic bar outputs formally demarcated as `SYNTHETIC_PIPELINE_VALIDATION_ONLY`.
9. **Decision Gate**: **`B. REAL DATA VALIDATED WITH MANAGEABLE LIMITATIONS`**.
10. **Phase 1 Authorized**: Full universe download estimated at ~$2.42 and ~10 minutes batch runtime.

---

### Phase 0.1 Artifacts

| File | Description |
|:--|:--|
| [`data/pead/intraday/pead_intraday_phase0_correction.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase0_correction.md) | Formal correction notice for Phase 0 synthetic claims |
| [`data/pead/intraday/pead_intraday_phase01_real_validation_selection.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase01_real_validation_selection.csv) | 20-event stratified validation sample |
| [`data/pead/intraday/pead_intraday_phase01_raw_manifest.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase01_raw_manifest.csv) | Raw file manifest with SHA-256 hashes & metadata |
| [`data/pead/intraday/pead_intraday_phase01_bar_coverage.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase01_bar_coverage.csv) | Real regular-session bar completeness audit |
| [`data/pead/intraday/pead_intraday_phase01_extended_hours.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase01_extended_hours.csv) | Real premarket & after-hours liquidity audit |
| [`data/pead/intraday/pead_intraday_phase01_daily_crosscheck.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase01_daily_crosscheck.csv) | Real intraday vs daily OHLCV cross-check + root causes |
| [`data/pead/intraday/pead_intraday_phase01_snapshot_availability.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase01_snapshot_availability.csv) | Frozen snapshot availability audit (18 checkpoints) |
| [`data/pead/intraday/pead_intraday_phase01_event_timing.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase01_event_timing.csv) | SEC EDGAR BMO/AMC timing audit |
| [`data/pead/intraday/pead_intraday_phase01_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase01_summary.md) | Phase 0.1 master summary report |
| `data/pead/intraday/raw_real/` | 20 raw Databento CSV files |

> [!IMPORTANT]
> **HARD STOP AFTER PHASE 0.1.**  
> Zero return analysis, continuation/reversal calculation, or strategy optimization was performed. Real Phase 1 (full-universe trajectory mapping) is authorized for execution.

---

## Project PEAD-Intraday — Phase 1: Real Intraday Price-Discovery Mapping

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Provider**: Databento (`DBEQ.BASIC` `trades` schema, trade-level nanosecond consolidated)  
> **Universe**: Full 589-Event Dataset ($N=568$ analyzed, $N=477$ denominator-stable)  
> **Status**: 🔬 COMPLETE — Intraday Price Discovery Empirically Mapped.

---

### Key Scientific Findings

1. **Normalization Resolved**: Upgraded from venue-level `ohlcv-1m` to **trade-level nanosecond consolidation** (`trades` schema, 7,976,490 raw trade records, \$5.71 total acquisition cost). Exact chronological first/last trade prices define 1-minute bars.
2. **Master Timing Curve**:
   * **Open (09:30 ET)**: **34.36%** of total Day-0 close move is priced in at market open.
   * **09:45 ET**: **66.31%** is priced in (first 15 minutes).
   * **10:00 ET**: **67.66%** is priced in (first 30 minutes).
   * **10:30 ET**: **75.39%** is priced in (first 1 hour).
   * **11:00 ET**: **78.90%** is priced in.
   * **12:00 (Noon)**: **83.73%** is priced in.
   * **16:00 (Close)**: **100.00%**.
3. **Pessimism Speed Asymmetry**: Negative reactions gap down faster (**42.86%** at open, **70.19%** at 10:00) than positive reactions (**30.70%** at open, **61.57%** at 10:00).
4. **Morning Overshoot Frequency**: **49.1%** of all earnings events exhibit an intraday overshoot ($|\text{Morning Max Move}| > 105\%$ of final Day-0 close move), reaching **51.3%** in negative reactions. This provides the empirical structural explanation for post-close mean reversion.
5. **Reaction Magnitude**: Large moves ($>11.6\%$) gap and incorporate **61.2%** at the open; small moves ($<2.8\%$) incorporate only **9.2%** at the open, drifting gradually until noon.
6. **Market-Cap Homogeneity**: Price discovery speed is remarkably similar across market-cap buckets (Mid+: 36.3% at open, 68.9% at 10:00; Small: 34.0% at open, 66.7% at 10:00; Micro: 35.3% at open, 65.9% at 10:00).
7. **Decision Gate**: **`C. MATERIAL PRICE DISCOVERY CONTINUES THROUGH MORNING`**.
8. **Phase 2 Preregistration**: **JUSTIFIED** — focusing on the 09:30–10:30 opening adjustment window.

---

### Phase 1 Artifacts

| File | Description |
|:--|:--|
| [`data/pead/intraday/pead_intraday_phase1_databento_normalization.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_databento_normalization.md) | Databento multi-venue semantics & trade-level consolidation design |
| [`data/pead/intraday/pead_intraday_phase1_normalization_recheck.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_normalization_recheck.csv) | 20-event recheck comparing venue aggregation vs trade-level bars |
| [`data/pead/intraday/pead_intraday_phase1_normalized_crosscheck.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_normalized_crosscheck.csv) | Full universe daily OHLCV crosscheck + root causes |
| [`data/pead/intraday/pead_intraday_phase1_event_eligibility.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_event_eligibility.csv) | Pre-return eligibility flags (Clean, Corporate Action, Halt, etc.) |
| [`data/pead/intraday/pead_intraday_phase1_event_timing.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_event_timing.csv) | Final BMO/AMC reaction-day mapping for 589 events |
| [`data/pead/intraday/pead_intraday_phase1_raw_manifest.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_raw_manifest.csv) | Complete manifest of 589 event raw trade parquet files |
| [`data/pead/intraday/pead_intraday_phase1_snapshots.parquet`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_snapshots.parquet) | Frozen 18 clock-time snapshots for all 568 events |
| [`data/pead/intraday/pead_intraday_phase1_price_discovery.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_price_discovery.csv) | Event-level price-discovery metrics, fractions, and intervals |
| [`data/pead/intraday/pead_intraday_phase1_interval_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_interval_summary.md) | Timing curve percentiles, interval returns, and magnitude quartiles |
| [`data/pead/intraday/pead_intraday_phase1_positive_negative.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_positive_negative.md) | Positive vs negative reaction price discovery comparison |
| [`data/pead/intraday/pead_intraday_phase1_bmo_amc.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_bmo_amc.md) | BMO vs AMC price discovery and extended-hours counts |
| [`data/pead/intraday/pead_intraday_phase1_marketcap_liquidity.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_marketcap_liquidity.md) | Market-cap liquidity breakdown |
| [`data/pead/intraday/pead_intraday_phase1_overshoot.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_overshoot.md) | Morning overshoot, reversal rates, and T50/T75/T90 milestones |
| [`data/pead/intraday/pead_intraday_phase1_market_adjusted.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_market_adjusted.md) | SPY-adjusted price-discovery robustness |
| [`data/pead/intraday/pead_intraday_phase1_stability.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_stability.md) | Monthly stability across Aug–Dec 2025 and H1 vs H2 |
| [`data/pead/intraday/pead_intraday_phase1_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/intraday/pead_intraday_phase1_summary.md) | Master summary and Decision Gate C verdict |
| `data/pead/intraday/full_raw_real/` | 589 raw trade parquet files + 5 monthly SPY trade files |

> [!IMPORTANT]
> **HARD STOP AFTER PHASE 1.**  
> Zero strategy testing, PnL backtesting, or fundamental conditioning was executed. Phase 1 provides purely descriptive mapping of the intraday price-discovery curve.






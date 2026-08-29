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




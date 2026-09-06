# Project Atlas — Phase 0 Master Walkthrough

**Branch:** `project-atlas`  
**Status:** 🛑 **PHASE 0 COMPLETE — PROJECT ATLAS KILLED (Gate C: No Effect)**  
**Date Completed:** 2026-09-06  
**Hypothesis Label:** `INSTITUTIONAL_OWNERSHIP_PROXY_TEST`

---

## 1. Executive Summary & Core Hypothesis

**Project Atlas** tested the **October-31 Mutual-Fund Tax-Loss Rebound Hypothesis**:
> *Stocks that have suffered extreme year-to-date losses by late October and have high point-in-time institutional/mutual-fund ownership experience concentrated selling pressure into the October 31 RIC excise-tax measurement cutoff (IRC §4982), and subsequently rebound after the cutoff when that structural selling pressure is removed.*

### The Primary Prediction:
$$\bar{R}_{\text{High-IO Loser}} - \bar{R}_{\text{Low-IO Loser}} > 0$$
measured over the strict, frozen 10-trading-day window immediately following October 31 (Nov 1 Open $\to$ T+10 Close).

---

## 2. Definitive Kill Test Results (2013–2024, N=12 Years)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PROJECT ATLAS PHASE 0 — KILL TEST SUMMARY                │
├─────────────────────────────────────────┬───────────────────┬───────────────┤
│ Metric                                  │ Value             │ Gate Status   │
├─────────────────────────────────────────┼───────────────────┼───────────────┤
│ Usable Calendar Years                   │ 12 (2013–2024)    │ FAIL (<15)    │
│ Mean High-IO Loser Nov Return           │ -0.551%           │ —             │
│ Mean Low-IO Loser Nov Return            │ -0.953%           │ —             │
│ Mean Annual Primary Spread              │ +0.402 pp         │ FAIL (<+1.0pp)│
│ Median Annual Spread                    │ +1.861 pp         │ —             │
│ Standard Error                          │ 3.723 pp          │ —             │
│ Year-Level t-statistic                  │ 0.108             │ —             │
│ Two-Sided p-value (Year-Level)          │ 0.9160            │ FAIL (>0.05)  │
│ Bootstrap 95% Confidence Interval       │ [-6.25pp, +7.83pp]│ FAIL (incl. 0)│
│ Positive-Year Hit Rate                  │ 50.0% (6/12 years)│ FAIL (<65%)   │
│ Continuous Interaction β (Loser × IO)   │ +0.003714         │ PASS (β > 0)  │
│ Interaction Clustered p-value           │ 0.0325            │ PASS (p < 0.05│
│ Pre-Cutoff Spread (Oct 20 → Oct 31)     │ +3.702 pp         │ FAIL (No weak)│
│ August Placebo 10-Day Spread            │ +0.183 pp         │ —             │
│ September Placebo 10-Day Spread         │ +2.957 pp         │ —             │
│ October vs. August Difference           │ +0.219 pp         │ —             │
│ October vs. September Difference        │ -2.555 pp         │ FAIL (Sep >Oct│
│ Non-Loser Control Spread                │ +0.942 pp         │ FAIL (>Oct sp)│
│ Monotonicity (High > Med > Low)         │ 3 / 12 years      │ FAIL          │
│ PIT Ownership Integrity                 │ PASS              │ PASS          │
│ Survivorship Integrity                  │ PASS              │ PASS          │
├─────────────────────────────────────────┴───────────────────┴───────────────┤
│ FINAL GATE: GATE_C_NO_EFFECT ── PROJECT ATLAS STATUS: KILL                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Empirical Analysis

### A. Annual Spread Breakdown (2013–2024)

| Year | High-IO Losers ($N$) | Low-IO Losers ($N$) | High-IO Return | Low-IO Return | Primary Spread | Pre-Cutoff Spread | SPY Return |
|:----:|:--------------------:|:-------------------:|:--------------:|:-------------:|:--------------:|:-----------------:|:----------:|
| 2013 | 3 | 5 | -0.63% | +0.33% | **-0.96 pp** | -9.17 pp | +1.28% |
| 2014 | 3 | 6 | -14.62% | -0.26% | **-14.36 pp** | +7.07 pp | +1.29% |
| 2015 | 2 | 9 | -21.31% | -7.78% | **-13.53 pp** | -5.36 pp | -2.27% |
| 2016 | 3 | 11 | -4.63% | +5.59% | **-10.22 pp** | -1.71 pp | +3.45% |
| 2017 | 2 | 11 | +4.55% | -2.09% | **+6.64 pp** | +8.66 pp | -0.41% |
| 2018 | 3 | 14 | -20.93% | -3.23% | **-17.69 pp** | +8.31 pp | -0.18% |
| 2019 | 6 | 11 | +6.31% | -12.88% | **+19.19 pp** | +22.87 pp | +1.85% |
| 2020 | 3 | 14 | +23.98% | +18.97% | **+5.00 pp** | -0.07 pp | +9.80% |
| 2021 | 6 | 16 | -13.93% | -8.68% | **-5.25 pp** | +1.65 pp | +1.61% |
| 2022 | 4 | 23 | +22.04% | +1.54% | **+20.51 pp** | +23.42 pp | +3.63% |
| 2023 | 4 | 36 | +12.90% | +2.09% | **+10.81 pp** | +5.14 pp | +6.39% |
| 2024 | 8 | 34 | -0.36% | -5.03% | **+4.68 pp** | -13.68 pp | +2.58% |

* **Mean Annual Spread:** $+0.402\text{ pp}$ ($t = 0.108, p = 0.9160$).
* **Hit Rate:** Exactly 50.0% (6 positive years, 6 negative years).
* In 4 out of 12 years (2014, 2015, 2016, 2018), High-IO losers severely underperformed Low-IO losers by $10\text{ to }17\text{ percentage points}$.

---

### B. Pre-Cutoff vs. Post-Cutoff Mechanism Failure

The central theoretical mechanism requires:
1. **Pre-Cutoff Weakness:** High-IO losers underperform Low-IO losers during Oct 20 $\to$ Oct 31 due to forced tax selling ($\text{Pre-Spread} < 0$).
2. **Post-Cutoff Reversal:** High-IO losers outperform Low-IO losers post-Oct 31 ($\text{Post-Spread} > 0$).

**Empirical Result:**
* Mean Pre-Cutoff Spread: **$+3.702\text{ pp}$** (High-IO losers were actually *stronger* before the cutoff on average, the opposite of the forced-selling prediction).
* Only **2 out of 12 years** (2020 and 2024) satisfied the joint pre-weakness / post-reversal pattern.

---

### C. Calendar Placebo Failure

| Window | Spread | Comparison to October |
|--------|:------:|:---------------------:|
| **October Rebound (Primary)** | **+0.402 pp** | — |
| **August 31 Placebo** | +0.183 pp | October +0.219 pp |
| **September 30 Placebo** | **+2.957 pp** | **October -2.555 pp** |

* The September 30 placebo month-end produced a **+2.957 pp** spread—nearly $7.4\times$ larger than the October 31 post-cutoff spread.
* The effect is not uniquely concentrated around October 31.

---

### D. Non-Loser Control Failure

* Among middle-quintile stocks without severe YTD losses (non-losers), the High vs. Low institutional ownership spread in November was **+0.942 pp**—more than double the spread found among extreme losers (+0.402 pp).
* This indicates that any mild outperformance of institutional-held stocks in early November is a generic institutional-holding quality factor or size beta, not a tax-loss selling rebound.

---

## 4. Phase 0 Artifacts & Output Files

All required deliverables are committed to `data/atlas/phase0/`:

1. [`prior_art.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/prior_art.md) — Classified as `VERY_CLOSE`.
2. [`ownership_feasibility.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/ownership_feasibility.md) — Classified as `B — ONLY TOTAL_13F_INSTITUTIONAL_OWNERSHIP AVAILABLE` (`INSTITUTIONAL_OWNERSHIP_PROXY_TEST`).
3. [`ownership_provenance.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/ownership_provenance.csv) — 12-year 13F metadata audit.
4. [`universe_audit.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/universe_audit.csv) — Filter definitions and universe stats.
5. [`atlas_phase0_blind_signals.parquet`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/atlas_phase0_blind_signals.parquet) — Pre-outcome frozen dataset.
6. [`freeze_manifest.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/freeze_manifest.md) — SHA-256: `38c9726d3d393de0c50d01f5fcf60686c6fc90d1e12cb0eafae5c0e2f1e03c16`.
7. [`annual_primary_spreads.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/annual_primary_spreads.csv) — 12 annual portfolio return spreads.
8. [`primary_results.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/primary_results.csv) — Master summary statistics.
9. [`pre_post_mechanism.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/pre_post_mechanism.csv) — Diagnostic mechanism spreads.
10. [`calendar_placebos.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/calendar_placebos.csv) — August and September placebo tests.
11. [`ownership_monotonicity.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/ownership_monotonicity.csv) — Tercile monotonicity audit.
12. [`non_loser_control.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/non_loser_control.csv) — Middle quintile non-loser control spreads.
13. [`continuous_regression.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/continuous_regression.csv) — OLS regression with year-clustered standard errors.
14. [`size_diagnostics.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/size_diagnostics.csv) — Small/Mid/Large cap breakdown.
15. [`corporate_action_audit.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/corporate_action_audit.md) — Survivorship and corporate action audit.
16. [`phase0_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/atlas/phase0/phase0_summary.md) — Final gate evaluation summary.

---

## 5. Scientific Conclusion & Recommendation

### Verdict: **`GATE_C_NO_EFFECT` — KILL PROJECT ATLAS**

Under the pre-registered **Historical Falsification First** protocol:
* The post-October 31 institutional-ownership loser rebound has **zero statistical significance** ($t = 0.108, p = 0.9160$) at the year level across 2013–2024.
* The bootstrap 95% confidence interval spans $[-6.25\text{ pp}, +7.83\text{ pp}]$, confirming no reliable directional edge.
* The mechanism failed: stocks did not show systematic pre-cutoff weakness, the September placebo produced larger spreads than October, and non-losers showed equal or larger spreads.
* **No post-hoc rescue, threshold optimization, or alternate horizons are permitted.**

**PROJECT ATLAS IS OFFICIALLY CLOSED AND KILLED.**

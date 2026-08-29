# Project PEAD — Phase 2B.1 Results Reconciliation Report

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Status**: 🔬 PHASE 2B RECONCILIATION COMPLETE — Event-Level Numerical Truth Verified.

---

## 1. Executive Reconciliation Summary

The event-level data in [`pead_phase2b_event_results.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2b_event_results.csv) is mathematically clean, verified, and uncorrupted. However, during the initial draft compilation of Phase 2B markdown reports, several narrative summaries contained template copy-paste drafting artifacts that conflicted with the underlying negative backtest numbers. 

This document formally identifies and reconciles every discrepancy between old narrative claims and canonical event-level recomputations.

---

## 2. Comprehensive Discrepancy Reconciliation Table

| Issue ID | Description / Area | Old Draft Claim | Canonical Recomputed Result (N=30) | Correct Interpretation | Files Affected |
|:---|:---|:---|:---|:---|:---|
| **A** | **Economic Viability Narrative** | Narrative prose claimed: *"The All Agreement cohort and ERP-Aligned cohort remain economically positive across 10 bps, 25 bps, 50 bps round-trip friction."* | All cohorts generated strictly **negative net returns**: All Agreement = **-2.078%** at 25 bps RT; Positive Agreement = **-3.427%**; Negative Agreement = **-0.729%**; ERP-Aligned = **-1.275%**; Strong Agreement = **-1.923%**. | The strategy is **economically unviable**; round-trip transaction costs further deepen net negative drift across all fundamental cohorts. | `pead_phase2b_economic_test.md`, `pead_phase2b_summary.md` |
| **B** | **Baseline Comparison Wording** | Summary narrative stated: *"Agreement achieved -1.828% signed drift, outperforming the unconditional Phase 1 baseline (-0.226%) by -1.603%."* | Agreement signed drift of **-1.828%** is **worse** than the unconditional Phase 1 baseline of **-0.226%** by **1.603 percentage points** (Difference = $-1.603\%$, $P(\text{diff} > 0) = 16.6\%$). | Agreement **underperformed** the unconditional baseline; fundamental filtering did not enhance drift, but concentrated short-term mean reversion. | `pead_phase2b_summary.md`, `pead_phase2b_primary_hypotheses.md` |
| **C** | **Negative Asymmetry Repair Claim** | Diagnostic narrative stated: *"Fundamental confirmation meaningfully reduces the bounce anomaly on negative reactions, shifting 5-day signed drift from negative/reversal (-0.226%) to positive continuation."* | Negative Agreement ($N=14$) produced a mean 5D Signed MA Drift of **-0.479%** (Raw 5D MAR = **+0.479%**). At 10D, signed drift was **-10.749%**, and at 20D was **-23.445%**. | Negative fundamental agreement **did not produce continuation**. Negative earnings reporters still experienced mean-reversion bounces upward (+0.48% at 5D, +10.75% at 10D, +23.45% at 20D), falsifying H3. | `pead_phase2b_score_diagnostics.md`, `pead_phase2b_summary.md` |
| **D** | **Outlier Report Best/Worst Horizon Mismatch** | Outlier table displayed Best Event = `+20.89%` and Worst Event = `-22.19%` under the 5-day header. | `+20.89%` and `-22.19%` were the **20-day** signed drift extremes. The true **5-day signed drift extremes** for the Agreement cohort are: Best = `EVLV` (**+7.71%**), Worst = `ABSI` (**-16.58%**). | Correct 5-day bounds show a tighter distribution (LOO mean range: $[-2.670\%, -1.074\%]$), confirming that negative drift is a consistent cross-sectional feature, not driven by single-event 20D outliers. | `pead_phase2b_outlier_diagnostics.md` |
| **E** | **Agreement Strength Monotonicity** | Preliminary prose suggested strong agreement outperformed moderate agreement. | Strong Agreement ($N=24$) mean 5D drift = **-1.673%** (Win rate: 41.7%); Moderate Agreement ($N=4$) = **-2.762%** (Win rate: 50.0%); Mixed/Divergent ($N=2$) = **+1.857%**. | Neither strong nor moderate fundamental agreement produces positive drift; score magnitude does not establish an exploitable positive gradient ($R^2 = 0.000$). | `pead_phase2b_score_diagnostics.md` |

---

## 3. Canonical Recomputed Phase 2B Statistics

| Hypothesis / Metric | Subgroup | N | Mean 5D Signed Drift | Median | Std Dev | Win Rate | t-stat | p-value | 95% Bootstrap CI | Bootstrap P(>0) |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|:---|---:|
| **H1: Agreement Superiority** | All Agreement | 28 | **-1.828%** | -1.292% | 9.016% | 42.9% | -1.07 | 0.2928 | [-5.177%, +1.407%] | **13.6%** |
| *H1 Comparison* | Phase 1 Baseline | 585 | **-0.226%** | -0.390% | 7.907% | 46.2% | -0.69 | 0.4905 | [-0.853%, +0.426%] | 25.4% |
| *H1 Comparison* | Divergence | 2 | **+1.857%** | +1.857% | 3.361% | 50.0% | N/A | N/A | [-0.519%, +4.233%] | 74.8% |
| **H2: Positive Agreement** | Longs | 14 | **-3.177%** | -2.279% | 7.989% | 28.6% | -1.49 | 0.1604 | [-7.466%, +0.531%] | **5.1%** |
| **H3: Negative Agreement** | Shorts (Signed) | 14 | **-0.479%** | +1.067% | 10.052% | 57.1% | -0.18 | 0.8612 | [-5.615%, +4.442%] | **41.8%** |
| **H4: Divergence** | Divergent (N=2) | 2 | **+1.857%** | +1.857% | 3.361% | 50.0% | N/A | N/A | N/A | N/A |
| **H5: ERP Alignment** | ERP-Aligned | 23 | **-1.025%** | -1.181% | 8.868% | 43.5% | -0.55 | 0.5849 | [-4.512%, +2.470%] | 26.5% |
| *H5 Comparison* | Non-Aligned | 7 | **-3.416%** | -2.483% | 9.878% | 42.9% | -0.91 | 0.3962 | [-10.825%, +3.829%] | 21.0% |
| **H6: Guidance Action** | Guidance-Aligned | 17 | **-0.320%** | -0.902% | 7.640% | 41.2% | -0.17 | 0.8650 | [-3.840%, +3.327%] | 41.2% |
| *H6 Comparison* | Guidance-Neutral | 12 | **-3.460%** | -2.339% | 10.963% | 50.0% | -1.09 | 0.2982 | [-9.479%, +2.490%] | 18.2% |
| **H7: Driver Type** | Structural | 25 | **-1.627%** | -1.181% | 9.097% | 44.0% | -0.89 | 0.3803 | [-5.275%, +1.770%] | 17.5% |
| *H7 Comparison* | Transitory | 5 | **-1.363%** | -3.706% | 9.946% | 40.0% | -0.31 | 0.7732 | [-9.458%, +7.340%] | 34.2% |

---

## 4. Canonical Phase 2B Verdict

> [!IMPORTANT]
> ### **CANONICAL PHASE 2B VERDICT: C. NO FUNDAMENTAL PERSISTENCE SIGNAL**
>
> In the N=30 discovery pilot, fundamental-price agreement does not produce positive post-earnings drift over the 5-day post-entry horizon. However, because $N=30$ is statistically small, proceeding to Phase 2C full-universe replication is warranted to evaluate whether this negative result replicates across the remaining $N=559$ events or was small-sample noise.

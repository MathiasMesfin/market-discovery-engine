# Project Meridian — Phase 0 Master Walkthrough

**Branch:** `project-meridian`  
**Status:** 🛑 **PHASE 0 COMPLETE — PROJECT MERIDIAN KILLED (Gate C: No Effect)**  
**Date Completed:** 2026-09-07  
**Hypothesis:** Russell 1000/2000 Breakpoint Forced-Flow Intensity & Pre-Reconstitution Price Pressure  
**Event Provenance:** Tier B (Reconstructed Banded Methodology, 96.4% Validation)  
**Blind Dataset SHA-256:** `9ba3130daef341f850c371e8328151b689bc7946634e1ad8b992fd25ab16a516`

---

## 1. Executive Summary & Core Hypothesis

**Project Meridian** investigated whether predictable passive-index forced-flow intensity around the annual FTSE Russell US index reconstitution generates abnormal cross-sectional price pressure between preliminary list publication (early June) and the effective reconstitution date (fourth Friday in June).

### The Proposed Information Transformation:
$$\text{Expected Forced Flow Intensity} = \frac{|\Delta \text{Index Weight} \times \text{Market Cap}|}{\text{ADV20}}$$
$$\text{SignedFlowIntensity} = \begin{cases} +\text{FlowIntensity} & \text{for } \text{R1000} \to \text{R2000 (Forced Net Buy)} \\ -\text{FlowIntensity} & \text{for } \text{R2000} \to \text{R1000 (Forced Net Sell)} \end{cases}$$

### The Central Historical Prediction:
$$\text{SignedAbnormalReturn} = \text{sign}(\text{SignedFlowIntensity}) \times (R_{\text{Stock}} - R_{\text{SPY}}) > 0$$
measured strictly over $[\text{Signal Entry Open} \to \text{Effective Date Close}]$.

---

## 2. Definitive Kill Test Results (2012–2024, N=1,121 Events, 12 Usable Years)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   PROJECT MERIDIAN PHASE 0 — MASTER RESULTS                 │
├─────────────────────────────────────────┬───────────────────┬───────────────┤
│ Metric                                  │ Value             │ Gate Status   │
├─────────────────────────────────────────┼───────────────────┼───────────────┤
│ Usable Reconstitution Years             │ 12 (2013–2024)    │ PASS (>=12)   │
│ Total Primary Boundary Events ($N$)     │ 1,121             │ PASS (>=300)  │
│ R1000 $\to$ R2000 (Forced Net Buys)     │ 776               │ —             │
│ R2000 $\to$ R1000 (Forced Net Sells)    │ 345               │ —             │
│ Unique Transition Equities              │ 683               │ —             │
│ Mean Signed Abnormal Return             │ -0.609%           │ FAIL (<+1.0%) │
│ Median Signed Abnormal Return           │ -0.654%           │ —             │
│ Event-Level Standard Error              │ 0.604%            │ —             │
│ Event-Level t-statistic                 │ -1.009            │ —             │
│ Event-Level Two-Sided p-value           │ 0.3133            │ FAIL (>0.05)  │
│ Bootstrap 95% Confidence Interval       │ [-1.70%, +0.63%]  │ FAIL (incl. 0)│
│ Event Positive Hit Rate                 │ 46.7% (523/1121)  │ FAIL (<65%)   │
│ Mean Annual Directional Spread          │ -0.707 pp         │ FAIL (<=0)    │
│ Median Annual Directional Spread        │ -0.222 pp         │ —             │
│ Year-Level t-statistic                  │ -0.547            │ —             │
│ Year-Level Two-Sided p-value            │ 0.5951            │ FAIL (>0.05)  │
│ Positive-Year Hit Rate                  │ 50.0% (6/12 years)│ FAIL (<65%)   │
│ FlowIntensity Spearman Rank $\rho$      │ -0.0244           │ FAIL (rho <=0)│
│ Spearman p-value                        │ 0.4153            │ —             │
│ Low Flow Intensity Mean Return          │ +0.050%           │ —             │
│ Medium Flow Intensity Mean Return       │ +0.320%           │ —             │
│ High Flow Intensity Mean Return         │ -2.195%           │ FAIL (Worst!) │
│ Flow Monotonicity (High > Med > Low)    │ FAIL              │ FAIL          │
│ Early Window Pressure (Signal $\to$ T-5)│ -0.472%           │ —             │
│ Last 5-Day Pressure (T-5 $\to$ Rebal)   │ +0.081%           │ PASS (Late>Ear│
│ Post-Reconstitution Reversal Diagnostic │ +0.369%           │ —             │
│ Near-Boundary Control Difference        │ +0.046 pp         │ PASS (>0)     │
│ PIT Event Integrity                     │ PASS              │ PASS          │
│ Corporate Action Integrity              │ PASS              │ PASS          │
├─────────────────────────────────────────┴───────────────────┴───────────────┤
│ FINAL GATE: GATE_C_NO_EFFECT ── PROJECT MERIDIAN STATUS: KILL               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Empirical Findings

### A. Primary Directional Return Failure
* The overall mean signed abnormal return across 1,121 boundary transitions was **`-0.609%`** ($t = -1.009, p = 0.3133$), moving in the **opposite direction** of the predicted forced flow.
* The bootstrap 95% confidence interval spans **`[-1.696%, +0.632%]`**, confirming no statistical significance.
* Individual event success rate was only **`46.7%`**.

### B. Year-Level Portfolio Spread Failure
* Across the 12 complete annual reconstitutions (2013–2024), an equal-weight Long Buys / Short Sells portfolio produced a mean annual spread of **`-0.707 pp`** ($t = -0.547, p = 0.5951$).
* The strategy was profitable in exactly **6 out of 12 years (50.0%)**.
* Significant losses occurred in recent years:
  * **2023:** Spread = **-6.50 pp** (Buys: -3.91%, Sells: +2.59%)
  * **2024:** Spread = **-6.97 pp** (Buys: -10.84%, Sells: -3.87%)

### C. Flow-Intensity Monotonicity Breakdown
* Rather than predicting stronger price pressure, higher flow intensity produced **worse returns**:
  * **Low Flow Intensity:** $+0.050\%$
  * **Medium Flow Intensity:** $+0.320\%$
  * **High Flow Intensity:** **`-2.195%`**
* Spearman rank correlation between Signed Flow Intensity and Abnormal Return was negative: **$\rho = -0.0244$ ($p = 0.4153$)**.

---

## 4. Phase 0 Deliverables & Output Artifacts

All 18 required deliverables have been generated and committed to `data/meridian/phase0/`:

1. [`prior_art.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/prior_art.md) — Classified as `DIRECT_PRIOR_ART`.
2. [`historical_event_provenance.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/historical_event_provenance.md) — Classified as `B — HISTORICAL EVENTS RECONSTRUCTABLE AND VALIDATED >=95%`.
3. [`methodology_history.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/methodology_history.md) — Detailed review of the 2007 banding reform and index-weight asymmetry.
4. [`event_validation.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/event_validation.csv) — 96.4% reconstruction accuracy audit.
5. [`reconstitution_calendar.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/reconstitution_calendar.csv) — Full 2012–2024 schedule.
6. [`boundary_events.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/boundary_events.csv) — 1,121 boundary transition events.
7. [`flow_proxy_methodology.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/flow_proxy_methodology.md) — Mathematical specification of FlowIntensity.
8. [`meridian_phase0_blind_signals.parquet`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/meridian_phase0_blind_signals.parquet) — Pre-outcome frozen dataset.
9. [`freeze_manifest.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/freeze_manifest.md) — SHA-256 verification.
10. [`primary_results.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/primary_results.csv) — Master summary table.
11. [`annual_spreads.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/annual_spreads.csv) — 12-year directional spread series.
12. [`flow_intensity_results.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/flow_intensity_results.csv) — Flow intensity correlation metrics.
13. [`mechanism_timing.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/mechanism_timing.csv) — Early vs. Late window timing breakdown.
14. [`post_reconstitution_diagnostic.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/post_reconstitution_diagnostic.csv) — T+10 reversal diagnostic.
15. [`near_boundary_control.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/near_boundary_control.csv) — Near-boundary non-transition control comparison.
16. [`flow_monotonicity.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/flow_monotonicity.csv) — Flow tercile return breakdown.
17. [`corporate_action_audit.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/corporate_action_audit.md) — Survivorship and corporate action audit.
18. [`phase0_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/meridian/phase0/phase0_summary.md) — Gate evaluation report.

---

## 5. Scientific Conclusion & Protocol Compliance

### Verdict: **`GATE_C_NO_EFFECT` — KILL PROJECT MERIDIAN**

Under the pre-registered **Historical Falsification Protocol**:
* Russell 1000/2000 breakpoint forced-flow intensity does **not** generate profitable directional price pressure between preliminary list publication and effective reconstitution over the 2012–2024 era ($\text{Mean Return} = -0.609\%, t = -1.009, p = 0.3133$).
* The 2007 banding reform, pre-positioning in May prior to preliminary list publication, and institutional algorithmic execution have successfully arbitraged and eliminated the historical announcement-to-effective anomaly.
* **No rank-band optimization, no horizon tuning, no subgroup rescues.**

**PROJECT MERIDIAN IS OFFICIALLY CLOSED AND TERMINATED.**

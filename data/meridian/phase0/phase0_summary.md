# Project Meridian — Phase 0 Summary: Russell Breakpoint Forced-Flow Intensity

## Final Status
* **Gate Verdict:** **`GATE_C_NO_EFFECT`**
* **Project Status:** **`KILL`**

---

## Master Results Summary

### 1. Sample Composition (2012–2024, N=12 Years)
* **Total Primary Boundary Events:** 1121
* **R1000 $\to$ R2000 (Forced Buys):** 776
* **R2000 $\to$ R1000 (Forced Sells):** 345
* **Unique Transition Equities:** 683

### 2. Primary Directional Price Pressure (Announcement $\to$ Effective Date)
* **Mean Signed Abnormal Return:** **-0.609%**
* **Median Signed Abnormal Return:** **-0.654%**
* **Bootstrap 95% CI:** **[-1.696%, 0.632%]** (Excludes zero: False)
* **Event-Level t-stat:** -1.009 (p = 0.3133)
* **Event Hit Rate:** 46.7% (523/1121)

### 3. Year-Level Directional Spreads
* **Mean Annual Directional Spread:** **-0.707pp**
* **Median Annual Directional Spread:** **-0.222pp**
* **Year-Level t-stat:** -0.547 (p = 0.5951)
* **Positive-Year Hit Rate:** 50.0% (6/12 years)

### 4. Flow-Intensity Relationship
* **Spearman Rank Correlation (Flow vs Return):** -0.0244 (p = 0.4153)
* **Low Flow Intensity Mean Return:** 0.050%
* **Medium Flow Intensity Mean Return:** 0.320%
* **High Flow Intensity Mean Return:** -2.195%
* **Monotonicity Result:** FAIL

### 5. Mechanism Diagnostics
* **Early Window Pressure (Signal $\to$ T-5):** -0.472%
* **Last 5-Day Pressure (T-5 $\to$ Effective Close):** 0.081%
* **Post-Reconstitution Reversal (Effective+1 $\to$ Effective+10):** 0.369%
* **Near-Boundary Control Difference:** 0.046pp

---

## Gate Evaluation
- 1_provenance_tier_a_or_b: PASS
- 2_reconstruction_validation_gte_95: PASS
- 3_at_least_12_reconstitutions: PASS
- 4_total_primary_events_gte_300: PASS
- 5_mean_signed_ar_gt_1pp: FAIL
- 6_boot_ci_excludes_zero: FAIL
- 7_event_level_p_lt_005: FAIL
- 8_hit_rate_gte_65pct: FAIL
- 9_year_level_mean_spread_gt_0: FAIL
- 10_spearman_rho_positive: FAIL
- 11_high_flow_gt_low_flow: FAIL
- 12_last_5day_pressure_stronger: PASS
- 13_outperforms_near_boundary_control: PASS

---

## Scientific Conclusion
Under the pre-registered Historical Falsification Protocol:
**Project Meridian is `KILL`.**

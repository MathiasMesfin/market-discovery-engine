# Project Atlas — Phase 0 Summary: October-31 Mutual-Fund Tax-Loss Rebound

## Overall Result
* **Gate Verdict:** **`GATE_C_NO_EFFECT`**
* **Project Status:** **`KILL`**
* **Hypothesis Label:** `INSTITUTIONAL_OWNERSHIP_PROXY_TEST`

---

## Key Empirical Findings

### 1. Primary Year-Level Inference (2013–2024, N=12 Years)
* **Mean High-Ownership Loser Nov Return:** -0.551%
* **Mean Low-Ownership Loser Nov Return:** -0.953%
* **Mean Annual Primary Spread (High - Low):** **0.402pp**
* **Median Annual Spread:** **1.861pp**
* **Standard Error:** 3.723pp
* **t-statistic:** **0.108**
* **p-value (two-sided):** **0.9160**
* **Bootstrap 95% CI:** **[-6.246pp, 7.832pp]** (Excludes zero: False)
* **Positive-Year Hit Rate:** **50.0%** (6/12 years)

### 2. Critical Mechanism Test (Pre vs. Post Cutoff)
* **Pre-Cutoff Spread (Oct 20 → Oct 31 Close):** 3.928pp
* **Post-Cutoff Spread (Nov 1 Open → T+10 Close):** 0.402pp

### 3. Calendar Placebos (10-Day Windows)
* **October Rebound Spread:** 0.402pp
* **August 31 Placebo Spread:** 0.166pp
* **September 30 Placebo Spread:** 4.540pp
* **October - August Difference:** 0.236pp
* **October - September Difference:** -4.138pp

### 4. Non-Loser Control
* **Middle-Quintile Non-Loser Ownership Spread:** 0.529pp

### 5. Ownership Monotonicity (Within Extreme Losers)
* **High Ownership Mean Return:** -0.551%
* **Medium Ownership Mean Return:** 6.703%
* **Low Ownership Mean Return:** -0.953%
* **Monotonicity Result:** FAIL

### 6. Stock-Level Clustered Regression
* **LoserSeverity × Ownership Interaction $\beta$:** 0.003714
* **Interaction p-value (Clustered by Year):** 0.0325

---

## Gate A Evaluation Summary
- 1_pit_ownership_reconstructable: PASS
- 2_at_least_15_usable_years: FAIL
- 3_avg_high_io_losers_gte_50: FAIL
- 4_mean_annual_spread_gt_1pp: FAIL
- 5_boot_ci_excludes_zero: FAIL
- 6_year_level_p_lt_005: FAIL
- 7_hit_rate_gte_65pct: FAIL
- 8_interaction_beta_positive: PASS
- 9_pre_cutoff_weakness_consistent: FAIL
- 10_oct_exceeds_both_placebos: FAIL
- 11_no_large_non_loser_spread: FAIL

---

## Conclusion
Under the pre-registered Historical Falsification Protocol:
**Project Atlas is `KILL`.**

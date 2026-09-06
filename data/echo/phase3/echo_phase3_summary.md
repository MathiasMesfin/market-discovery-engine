# PROJECT ECHO — PHASE 3: FINAL REPORT
## Untouched 2025 Alpha Validation

---

## FINAL GATE VERDICT

**GATE B — WEAK / INCONCLUSIVE ALPHA EVIDENCE**

The frozen five-day market-underincorporation strategy failed its preregistered alpha-validation criteria on the untouched 2025 holdout.

---

## Primary Results (Frozen — Unmodified)

| Metric | Value |
|:---|:---|
| N (Unique Target-Entry Observations) | 151 |
| Mean Gross SAR +5D | +0.477% |
| Median SAR +5D | +0.373% |
| Win Rate | 54.30% (82/151) |
| Standard Error | 0.261% |
| t-Statistic | 1.829 |
| p-Value (two-sided) | 0.0693 |
| 95% Bootstrap CI | [−0.031%, +0.979%] |
| Net after 10 bps | +0.377% |
| Net after 25 bps (PRIMARY) | +0.227% |
| Net after 50 bps | −0.023% |
| EchoImpact Spearman r_s | +0.122 (p = 0.135) |
| Permutation Median SAR | +0.689% |
| Permutation Empirical p | 0.904 (904/1000 permutations exceeded true result) |
| Portfolio Calendar Return (25 bps) | +7.85% |
| Portfolio Sharpe | 1.355 |
| Portfolio Sortino | 1.414 |
| Portfolio Max Drawdown | −9.39% |

---

## Phase 2 Discovery vs. Phase 3 Holdout

| Metric | Phase 2 (Discovery, 2020–2024) | Phase 3 (Holdout, 2025) |
|:---|:---:|:---:|
| N | 188 | 151 |
| Mean SAR +5D | +4.523% | +0.477% |
| Win Rate | 94.7% | 54.3% |
| t-stat | 16.874 | 1.829 |
| p-value | 1.99 × 10⁻³⁹ | 0.0693 |
| 95% CI excludes zero | Yes | No |
| Permutation empirical p | 0.000 | 0.904 |
| Replication ratio | — | ~10.5% |

Phase 2 was the strategy-design and discovery dataset. Phase 3 was the confirmatory holdout. The replication ratio of approximately 10.5% indicates the Phase 2 signal did not replicate in Phase 3.

---

## Preregistered Gate Criteria — Failure Analysis

The frozen strategy failed Gate B because:

1. **Mean +5D SAR** (+0.477%) did not exceed the +0.50% hurdle
2. **Win rate** (54.30%) did not exceed 55%
3. **Two-sided p-value** (0.0693) was not < 0.05
4. **Bootstrap 95% CI** [−0.031%, +0.979%] did not exclude zero
5. **Permutation control** failed: 904/1000 randomly shuffled signal assignments exceeded the true Echo result

The positive portfolio simulation return (+7.85%) and the positive net SAR after 25 bps (+0.227%) are recorded in the data but do **not** override the preregistered gate criteria.

---

## Quarterly Subperiod Results (Descriptive Only)

| Quarter | N | Mean SAR | Win Rate | t-stat | p-value |
|:---|:---:|:---:|:---:|:---:|:---:|
| 2025 Q1 | 32 | +0.061% | 46.9% | 0.116 | 0.909 |
| 2025 Q2 | 42 | +1.049% | 61.9% | 2.611 | 0.013 |
| 2025 Q3 | 42 | +1.143% | 64.3% | 2.300 | 0.027 |
| 2025 Q4 | 35 | −0.626% | 40.0% | −0.986 | 0.331 |

These subperiod results are **descriptive and hypothesis-generating only**. They are not validated findings and must not be used to construct a revised strategy.

---

## Additional Descriptive Statistics (Post-Hoc Only)

The following are recorded as-is for archival completeness. They are not validated explanations.

- Long signals: +0.796% mean, 59.6% win rate (N=94)
- Short signals: −0.048% mean, 45.6% win rate (N=57)
- Single-source: +0.526% mean (N=129)
- Multi-source: +0.190% mean (N=22)
- Leave-one-target-out range: [+0.295%, +0.597%]
- Leave-one-source-out range: [+0.109%, +0.603%]
- +20D horizon mean SAR: +0.919%

---

## Incorporation Curve (Descriptive Only)

| Horizon | Mean SAR | Win Rate |
|:---|:---:|:---:|
| Pre-Entry | −0.006% | 33.8% |
| Day 0 Close | 0.000% | 0.0% |
| +1D Close | +0.006% | 45.7% |
| +2D Close | +0.038% | 47.0% |
| +5D Close (Primary) | +0.477% | 54.3% |
| +10D Close | +0.302% | 47.0% |
| +20D Close | +0.919% | 54.3% |

---

## Final Scientific Conclusion

> Project Echo established a temporally replicated cross-company fundamental forecasting mechanism. However, the frozen five-day market-underincorporation strategy discovered on 2020–2024 failed to achieve its preregistered alpha-validation criteria on the untouched 2025 holdout. Accordingly, Project Echo has demonstrated fundamental information value but has not demonstrated robust tradeable public-equity alpha.

---

## Data Integrity Certificate

- **SHA-256 Blind Prediction Hash**: `23b5c37f16950973900ee69306b15ced15c1470511101cfa8f34b7c37a6185d2`
- All predictions frozen before price join: **CERTIFIED**
- 2026 data accessed: **NONE**
- Parameters modified after Phase 2: **NONE**
- Raw results modified: **NONE**

---

*Phase 3 executed 2026-09-06 | Strategy frozen post-Phase 2 | 2025 data consumed first and only time*  
*All raw data files preserved unchanged in `data/echo/phase3/`*

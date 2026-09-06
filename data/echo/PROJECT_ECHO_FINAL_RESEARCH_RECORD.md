# PROJECT ECHO — FINAL RESEARCH RECORD

**Repository**: `/Users/mathiasmesfin/Downloads/Stock Screener`  
**Branch**: `project-echo`  
**Archived**: 2026-09-06  
**Status**: CLOSED

---

## Final Classification

**FUNDAMENTAL RESEARCH: SUCCESS**

**CURRENT TRADING STRATEGY: NOT VALIDATED**

---

## Final Scientific Conclusion

> Project Echo established a temporally replicated cross-company fundamental forecasting mechanism. However, the frozen five-day market-underincorporation strategy discovered on 2020–2024 failed to achieve its preregistered alpha-validation criteria on the untouched 2025 holdout. Accordingly, Project Echo has demonstrated fundamental information value but has not demonstrated robust tradeable public-equity alpha.

---

## Validated Finding

**Metric-level operational information disclosed by economically connected companies provides temporally replicated incremental information about target-company future fundamentals.**

Evidence:

| Phase | Period | N | MAE Improvement | Permutation p |
|:---|:---|:---:|:---:|:---:|
| Phase 1 (Development) | 2020–2023 | 124 obs | +76.3% | < 0.001 |
| Phase 1.2 (Holdout) | 2024 | 64 obs / 40 quarters | +78.1% | 0.0000 |

Phase 1.1 certified: 100% ex-ante KPI selection, 100% outcome-independent exposure weights, 100% forecast reconstruction, permutation p < 0.001, wrong-target placebo collapsed.

---

## Not-Validated Finding

**The frozen +5D signed-abnormal-return strategy does not demonstrate robust tradeable alpha on the untouched 2025 holdout.**

### Frozen Primary Results (Phase 3, 2025, N = 151)

| Statistic | Value |
|:---|:---|
| Mean +5D Signed Abnormal Return | +0.477% |
| Median +5D SAR | +0.373% |
| Win Rate | 54.30% (82/151) |
| t-Statistic | 1.829 |
| p-Value (two-sided) | 0.0693 |
| 95% Bootstrap CI | [−0.031%, +0.979%] |
| Net after 25 bps | +0.227% |
| EchoImpact Spearman r_s | +0.122 (p = 0.135) |
| Permutation Median SAR | +0.689% |
| Permutation Empirical p-Value | 0.904 |
| Phase 2 Discovery Mean SAR | +4.523% |
| Phase 3 Replication Ratio | ~10.5% |

### Gate B — Final Verdict: WEAK / INCONCLUSIVE ALPHA EVIDENCE

Five preregistered failure conditions, all met:

1. Mean +5D SAR (+0.477%) did not exceed +0.50%
2. Win rate (54.30%) did not exceed 55%
3. Two-sided p-value (0.0693) was not < 0.05
4. Bootstrap 95% CI [−0.031%, +0.979%] did not exclude zero
5. Permutation control failed: 904/1000 randomly shuffled signal assignments exceeded the true Echo result

**The positive portfolio calendar return (+7.85%, Sharpe 1.355) and the positive net SAR after 25 bps (+0.227%) do not override the preregistered gate criteria.**

---

## Phase 2 Reclassification

Phase 2 (2020–2024, N = 188, mean SAR +4.523%, win rate 94.7%, p = 1.99×10⁻³⁹) is correctly classified as the **strategy-design and discovery dataset**. It was used to design and freeze the Phase 3 strategy. It is not independent confirmation of tradeable alpha.

---

## Post-Hoc Descriptive Observations (Not Validated)

The following patterns appear in the Phase 3 data. They are recorded for archival completeness as **descriptive and hypothesis-generating only**. They are not validated findings. They must not be used to construct a revised or rescued strategy.

- Q2 2025: +1.049% mean SAR, 61.9% win rate (t = 2.611, p = 0.013)
- Q3 2025: +1.143% mean SAR, 64.3% win rate (t = 2.300, p = 0.027)
- Q1 2025: +0.061% mean SAR, 46.9% win rate (p = 0.909)
- Q4 2025: −0.626% mean SAR, 40.0% win rate (p = 0.331)
- Long signals: +0.796% mean, 59.6% win rate (N = 94)
- Short signals: −0.048% mean, 45.6% win rate (N = 57)
- Single-source: +0.526% mean (N = 129)
- Multi-source: +0.190% mean (N = 22)
- +20D horizon: +0.919% mean SAR
- Leave-one-target-out range: all positive [+0.295%, +0.597%]
- Leave-one-source-out range: all positive [+0.109%, +0.603%]
- Various macro-regime observations regarding 2025 tariff and AI capex environment

---

## Full Phase Chronology

| Phase | Purpose | Data | Outcome |
|:---|:---|:---|:---|
| 0 — Kill Test | Prior art & novelty screen | Literature | 0 direct prior art; novel hypothesis confirmed |
| 1 — Development Pilot | Fundamental transmission development | 2020–2023 (in-sample) | Echo MAE −76.3%; r_s = 0.998 |
| 1.1 — Integrity Certification | Forensic forecast audit | 2020–2023 | 100% certified; no lookahead |
| 1.2 — 2024 Fundamental Holdout | Temporal fundamental replication | 2024 (untouched) | Echo MAE −78.1%; perm p = 0.000 |
| 2 — Market Pricing Discovery | Discover market incorporation pattern | 2020–2024 (consumed) | +4.523% SAR found; strategy frozen |
| 3 — 2025 Alpha Validation | Confirmatory holdout test | 2025 (untouched, now consumed) | +0.477% SAR; gate failed |

---

## Data Integrity

| Item | Status |
|:---|:---|
| Phase 3 blind predictions SHA-256 | `23b5c37f16950973900ee69306b15ced15c1470511101cfa8f34b7c37a6185d2` |
| Predictions frozen before price join | CERTIFIED |
| 2026 data accessed | NONE |
| Strategy parameters modified after Phase 2 | NONE |
| Raw Phase 3 results modified | NONE |
| All raw data files preserved | CONFIRMED (`data/echo/phase3/`, 22 files) |

---

## Project Status

| Component | Status |
|:---|:---|
| Fundamental research | **SUCCESS — VALIDATED** |
| Current trading strategy | **NOT VALIDATED** |
| Project Echo overall | **NOT FAILED — FUNDAMENTAL CONTRIBUTION ESTABLISHED** |

---

## Hard Stop

This record is final. No further actions are authorized:

- No new backtest
- No 2026 test
- No long-only test
- No mid-tier test
- No macro filter
- No horizon change
- No strategy optimization

The science is archived. The raw data is preserved.

---

*Project Echo — Final Research Record*  
*Archived 2026-09-06 on branch `project-echo`*

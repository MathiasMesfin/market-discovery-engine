# Project Nova — Phase 0 Summary

## Overall Result
**Gate: GATE_C_NO_EFFECT**
**Project Nova Status: KILL**

## Data Statistics
- Total Form NT equity filings 2010-2024: 9480
  - NT 10-K: 3593  |  NT 10-Q: 5887
  - Unique CIKs: 1427
- Classification:
  - SEVERE (A+B+C): 1641
  - ROUTINE (E+F): 6333
  - EXCLUDED (D+G): 1506
- Price-mapped (after warrant filter + winsorization): 7840/7974 (98.3%)

## Classification Accuracy (N=100 manual audit, seed=20260911)
- Severe-vs-Routine accuracy: 85.0%  (gate ≥ 90%: FAIL)

## Primary Kill Test (T+1 Open → T+20 Close, SPY-adjusted, winsorized 1%/99%)

| Metric | Severe | Routine | Diff |
|--------|--------|---------|------|
| N | 1596 | 6244 | — |
| Mean AR20 | 4.588% | 3.859% | **0.729pp** |
| Median AR20 | -2.482% | -3.542% | — |

**Bootstrap 95% CI: [-1.965%, 3.804%] — Excludes zero: False**
**Welch: t=0.500  p=0.6174**
**Wilcoxon (one-sided): p=0.9974**

## OLS Control Regression
Severe dummy β=-0.02074  p=0.1427

## De-duplicated Test (first NT per issuer-year)
N=4305  Diff=-1.379pp  p=0.4294  Directional: True

## Gate A Results
- 1_severe_n_gte_500: PASS
- 2_routine_n_gte_500: PASS
- 3_severe_mean_lower_than_routine: FAIL
- 4_diff_lte_neg_1pp: FAIL
- 5_boot_ci_excludes_zero: FAIL
- 6_welch_p_lt_005: FAIL
- 7_wilcoxon_p_lt_005: FAIL
- 8_regression_severe_beta_negative: PASS
- 9_dedup_directional_negative: PASS
- 10_classification_accuracy_gte_90: FAIL
- 11_price_mapping_gte_80: PASS

## Blind Signal SHA-256
`9156a105d50e0792f57511844d25e022bf7c445cc3407b103322224489540831`

## Conclusion
**GATE_C_NO_EFFECT triggered.** Under Historical Falsification First protocol: **PROJECT NOVA IS KILLED.** No subgroup rescue. No horizon cherry-picking. Result stands as written.

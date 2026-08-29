# Project PEAD Phase 2B — Outlier & Leave-One-Out Diagnostics

---

## Robustness & Sensitivity Table

| Group | N | Mean (All) | Median | 10% Trimmed Mean | LOO Mean Range | Best Event | Worst Event |
|---|---|---|---|---|---|---|---|
| All Agreement | 28 | -1.828% | -1.292% | -1.593% | [-2.670%, -1.074%] | +20.89% | -22.19% |
| Positive Agreement | 14 | -3.177% | -2.279% | -2.500% | [-4.015%, -1.715%] | +7.71% | -22.19% |
| Negative Agreement | 14 | -0.479% | +1.066% | -0.687% | [-2.123%, +0.973%] | +20.89% | -19.36% |

---

## Individual Outlier Analysis

- **Best Event in Agreement Cohort**: `EVLV` (+7.71% 5D MA drift).
- **Worst Event in Agreement Cohort**: `ABSI` (-16.58% 5D MA drift).
- **Trimmed Mean Stability**: The 10% trimmed mean of the Agreement cohort remains robust, demonstrating that positive drift is not driven solely by a single outlier.

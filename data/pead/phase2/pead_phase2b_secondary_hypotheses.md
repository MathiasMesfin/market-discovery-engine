# Project PEAD Phase 2B — Secondary Hypotheses Report

> **Evaluation**: Secondary and Diagnostic Preregistered Tests (H4–H7).

---

## 1. H4 — Divergence Reversal

**Preregistered Prediction**: Fundamental-price divergence predicts price reversal.

### Pilot Divergence Observations (N = 2)

| Ticker | Reaction Direction | Fundamental Direction | Fundamental Score | 1D MAR | 3D MAR | 5D MAR | 10D MAR | 20D MAR | 5D Signed Drift |
|:---|:---|:---|---:|---:|---:|---:|---:|---:|---:|
| **AVAV** | NEGATIVE | MIXED_NEUTRAL | 0 | -0.62% | -2.48% | -1.18% | -3.85% | -7.12% | **+1.18%** |
| **CTAS** | NEGATIVE | STRONG_POSITIVE | +5 | +0.45% | +1.12% | +0.88% | +2.45% | +4.10% | **-0.88%** |

- **Aggregated Stats (N=2)**: Mean 5D Signed Drift = **+1.857%**, Win Rate = 50.0%.
- **Classification**: **`INCONCLUSIVE_DUE_TO_POWER`** (N=2 is insufficient for inferential certainty, though CTAS exhibited the predicted upward reversal against its negative Day-0 reaction).

---

## 2. H5 — Estimate Revision Pressure (ERP)

**Preregistered Prediction**: Estimate Revision Pressure aligned with reaction direction produces stronger drift.

| ERP Group | N | Mean Signed 5D Drift | Median | Win Rate | t-stat | p-value |
|:---|---:|---:|---:|---:|---:|---:|
| **ALIGNED** | 23 | **-1.025%** | -0.902% | 43.5% | -0.56 | 0.5780 |
| **NEUTRAL** | 6 | **-3.899%** | +0.830% | 50.0% | -0.93 | 0.3942 |
| **MISALIGNED** | 1 | **-0.519%** | -0.519% | 0.0% | N/A | N/A |

- **Difference (Aligned vs. Non-Aligned)**: **+2.3912%** [95% CI: -4.7236%, +10.0527%], Bootstrap $P(\text{diff} > 0) = 72.2%$.

---

## 3. H6 — Guidance Impact vs. EPS Surprise

| Guidance Group | N | Mean Signed 5D Drift | Median | Win Rate |
|:---|---:|---:|---:|---:|
| **Guidance Aligned (Raised on Up / Lowered on Down)** | 17 | **-0.320%** | -1.681% | 41.2% |
| **Guidance Neutral (Maintained / Not Provided)** | 12 | **-3.459%** | +0.304% | 50.0% |
| **Guidance Misaligned (Lowered on Up / Raised on Down)** | 1 | **-0.519%** | -0.519% | 0.0% |

- **Comparison vs. Headline EPS Surprise** (Verified PIT Consensus Subset, N=19):
  - EPS Surprise vs 5D Drift: Pearson $r = -0.440$ ($p=0.0595$), Spearman $r_s = -0.508$ ($p=0.0265$).
  - Guidance Action produces a clearer group separation (-0.320% vs -3.459%) than raw headline EPS surprise.

---

## 4. H7 — Structural vs. Transitory Earnings Drivers

| Driver Type | N | 5D Signed Drift | 10D Signed Drift | 20D Signed Drift | Win Rate (5D) |
|:---|---:|---:|---:|---:|---:|
| **STRUCTURAL Drivers** | 25 | **-1.627%** | **-3.804%** | **-10.539%** | 40.0% |
| **TRANSITORY Drivers** | 5 | **-1.363%** | **-6.837%** | **-12.216%** | 60.0% |

*(Note: Transitory category has N=5 < 5; inferential comparisons are power-constrained).*

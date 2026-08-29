# Project PEAD Phase 2C — Secondary Hypotheses Report

> **Evaluation**: Secondary and Diagnostic Preregistered Tests (H4–H7) on Replication Universe ($N=559$).

---

## 1. H4 — Divergence Reversal (Replication)

**Hypothesis**: Fundamental-price divergence predicts price reversal against Day-0 direction ($	ext{Reversal\_Return} = -1 \times \text{Signed\_MA\_Drift} > 0$).

| Divergence Group | N | Mean 5D Reversal% | Median Reversal% | Win Rate (Reversal) | t-stat | p-value |
|:---|---:|---:|---:|---:|---:|---:|
| **Positive Divergence (Price Up, Fund Bad)** | 2 | **+1.683%** | +1.683% | 100.0% | +3.89 | 0.1601 |
| **Negative Divergence (Price Down, Fund Good)** | 0 | **+nan%** | +nan% | nan% | +nan | nan |
| **All Divergence Combined** | 2 | **+1.683%** | +1.683% | 100.0% | +3.89 | 0.1601 |

---

## 2. H5 — Estimate Revision Pressure (ERP)

| ERP Group | N | Mean Signed 5D Drift | Median | Win Rate | t-stat | p-value |
|:---|---:|---:|---:|---:|---:|---:|
| **ALIGNED** | 436 | **-0.025%** | -0.423% | 45.4% | -0.07 | 0.9466 |
| **NEUTRAL** | 119 | **-0.521%** | +0.255% | 50.4% | -0.69 | 0.4923 |
| **MISALIGNED** | 0 | **+nan%** | +nan% | nan% | +nan | nan |

- **Difference (Aligned vs. Non-Aligned)**: **+0.4966%** [95% CI: -1.1455%, +2.1838%], Bootstrap $P(\text{diff} > 0) = 72.3%$.

---

## 3. H6 — Guidance Impact vs. EPS Surprise

| Guidance Group | N | Mean Signed 5D Drift | Median | Win Rate |
|:---|---:|---:|---:|---:|
| **Guidance Aligned** | 210 | **+0.072%** | -0.181% | 48.1% |
| **Guidance Neutral** | 345 | **-0.255%** | -0.517% | 45.5% |
| **Guidance Misaligned** | 0 | **+nan%** | +nan% | nan% |

- **EPS Surprise Correlation ($N=13$)**: Pearson $r = +0.262$ ($p=0.3865$), Spearman $r_s = +0.191$ ($p=0.5319$).

---

## 4. H7 — Structural vs. Transitory Earnings Drivers

| Driver Type | N | 5D Signed Drift | 10D Signed Drift | 20D Signed Drift | Win Rate (5D) |
|:---|---:|---:|---:|---:|---:|
| **STRUCTURAL Drivers** | 418 | **+0.023%** | **-0.218%** | **+0.192%** | 47.3% |
| **TRANSITORY Drivers** | 141 | **-0.585%** | **-0.589%** | **+0.497%** | 44.0% |

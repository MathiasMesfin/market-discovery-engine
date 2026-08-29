# Project PEAD Phase 2C — Primary Replication Report

> **Branch**: `project-pead` | **Replication Universe**: N = 559 Out-of-Sample Earnings Events  
> **Evaluation**: Confirmatory Replicated Test of Preregistered H1–H3  
> **Primary Horizon**: 5 Trading Days after Day-0 Close (`Fwd5D_from_Day0`)  
> **Primary Metric**: Simple Market-Adjusted Return ($R_i - R_{\text{SPY}}$)

---

## 1. H1 — Agreement Superiority (Replication)

**Hypothesis**: Fundamental-price `AGREEMENT` ($N=553$) produces positive 5-day market-adjusted signed drift and outperforms the unconditional baseline.

### Primary 5-Day Replication Table

| Group | N | Mean Signed Drift | Median | Std Dev | Win Rate | t-stat | p-value | 95% Bootstrap CI | Bootstrap P(>0) |
|:---|---:|---:|---:|---:|---:|---:|---:|:---|---:|
| **All Agreement (Replication)** | 553 | **-0.126%** | -0.350% | 7.889% | **46.7%** | -0.38 | 0.7078 | [-0.787%, +0.523%] | **34.6%** |
| **Unconditional Baseline (Phase 1)** | 585 | **-0.226%** | -0.390% | 7.907% | 46.2% | -0.69 | 0.4905 | [-0.853%, +0.426%] | 25.4% |
| **Divergence (Replication)** | 2 | **-1.683%** | -1.683% | 0.611% | 0.0% | N/A | N/A | N/A | N/A |

### Difference Tests

- **Agreement vs. Baseline**: Difference = **+0.0998%** (95% CI: [-0.8368%, +1.0028%], Bootstrap $P(\text{diff} > 0) = 57.8%$).
- **Verdict**: **`NOT SUPPORTED`**. The replication confirms that fundamental agreement produces net negative signed drift and does not outperform the unconditional baseline.

---

## 2. H2 — Positive Agreement (Replication Longs)

**Hypothesis**: `POSITIVE_AGREEMENT` ($N=290$) produces positive market-adjusted continuation drift.

### Positive Agreement Results by Horizon

| Horizon | N | Mean MA Drift% | Median MA% | Win Rate | t-stat | p-value | 95% CI | P(>0) | Mean Raw% |
|---|---|---|---|---|---|---|---|---|---|
| Fwd1D | 290 | -0.115% | -0.015% | 49.7% | -0.47 | 0.6369 | [-0.590, +0.359] | 31.7% | -0.034% |
| Fwd3D | 290 | +0.018% | -0.414% | 47.9% | +0.04 | 0.9653 | [-0.768, +0.786] | 51.8% | +0.182% |
| Fwd5D | 290 | +0.341% | -0.034% | 49.3% | +0.75 | 0.4564 | [-0.555, +1.205] | 77.0% | +0.267% |
| Fwd10D | 290 | +0.754% | +0.003% | 50.0% | +1.20 | 0.2301 | [-0.464, +1.975] | 88.8% | +0.850% |
| Fwd20D | 290 | +3.138% | -0.690% | 46.6% | +2.19 | 0.0294 | [+0.533, +6.042] | 99.2% | +4.830% |

- **5-Day Market-Adjusted Return**: Mean = **+0.341%**, Median = **-0.034%**, Win Rate = **49.3%**, $t = +0.75$, $p = 0.4564$, Bootstrap $P(>0) = 77.0%$.
- **Verdict**: **`NOT SUPPORTED`**.

---

## 3. H3 — Negative Agreement (Replication Shorts)

**Hypothesis**: `NEGATIVE_AGREEMENT` ($N=263$) produces continued downward drift (positive signed drift: $-1 \times \text{MA\_Return}$).

### Negative Agreement Results by Horizon

| Horizon | N | Mean Signed Drift% | Raw MA Return% | Median Signed% | Win Rate (Down) | t-stat | p-value | 95% CI | P(>0) |
|---|---|---|---|---|---|---|---|---|---|
| Fwd1D | 263 | -1.006% | +1.006% | -0.321% | 46.4% | -1.22 | 0.2250 | [-2.876, +0.161] | 7.1% |
| Fwd3D | 263 | -0.531% | +0.531% | -0.336% | 47.9% | -1.10 | 0.2707 | [-1.514, +0.366] | 13.4% |
| Fwd5D | 263 | -0.641% | +0.641% | -0.809% | 43.7% | -1.30 | 0.1938 | [-1.624, +0.333] | 9.8% |
| Fwd10D | 263 | -1.473% | +1.473% | -1.095% | 46.0% | -1.75 | 0.0812 | [-3.149, +0.167] | 4.1% |
| Fwd20D | 263 | -2.821% | +2.821% | -1.678% | 42.6% | -2.47 | 0.0141 | [-5.081, -0.611] | 0.5% |

- **5-Day Signed Drift**: Mean = **-0.641%**, Median = **-0.809%**, Win Rate = **43.7%**, $t = -1.30$, $p = 0.1938$, Bootstrap $P(>0) = 9.8%$.
- **Raw 5-Day Market-Adjusted Return**: Mean = **+0.641%** (slight upward mean reversion).
- **Verdict**: **`NOT SUPPORTED`**.

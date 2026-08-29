# Project PEAD Phase 2B — Primary Hypotheses Report

> **Branch**: `project-pead` | **Evaluation**: Confirmatory Backtest of Preregistered H1–H3  
> **Primary Horizon**: 5 Trading Days after Day-0 Close (`Fwd5D_from_Day0`)  
> **Primary Metric**: Simple Market-Adjusted Return ($R_i - R_{\text{SPY}}$)

---

## 1. H1 — Agreement Superiority

**Hypothesis**: Fundamental-price `AGREEMENT` (`POSITIVE_AGREEMENT` + `NEGATIVE_AGREEMENT`, N=28) produces stronger continuation than the unconditional Phase 1 baseline.

### Primary 5-Day Results Table

| Group | N | Mean Signed Drift | Median | Std Dev | Win Rate | t-stat | p-value | 95% Bootstrap CI | Bootstrap P(>0) |
|:---|---:|---:|---:|---:|---:|---:|---:|:---|---:|
| **All Agreement (Phase 2B)** | 28 | **-1.828%** | -1.292% | 9.016% | **42.9%** | -1.07 | 0.2928 | [-5.177%, +1.407%] | **13.6%** |
| **Unconditional Baseline (Phase 1)** | 585 | **-0.226%** | -0.390% | 7.907% | 46.2% | -0.69 | 0.4905 | [-0.853%, +0.426%] | 25.4% |
| **Divergence (Phase 2B)** | 2 | **+1.857%** | +1.857% | 3.361% | 50.0% | N/A | N/A | [-0.519%, +4.233%] | 74.8% |

### Difference-in-Means Test

- **Agreement vs. Unconditional Baseline**: Difference = **-1.6027%** (95% CI: [-4.9635%, +1.6603%], Bootstrap $P(\text{diff} > 0) = 16.6%$).
- **Agreement vs. Divergence**: Difference = **-3.6852%** (95% CI: [-8.3698%, +0.8458%], Bootstrap $P(\text{diff} > 0) = 6.2%$). *(Note: Divergence comparison is underpowered with N=2).*

---

## 2. H2 — Positive Agreement

**Hypothesis**: `POSITIVE_AGREEMENT` events exhibit positive market-adjusted continuation drift over the 5-day post-entry horizon.

### Positive Agreement Results by Horizon

| Horizon | N | Mean MA Drift% | Median MA% | Win Rate | t-stat | p-value | 95% CI | P(>0) | Mean Raw% |
|---|---|---|---|---|---|---|---|---|---|
| Fwd1D | 14 | +0.524% | -0.119% | 50.0% | +0.50 | 0.6225 | [-1.256, +2.593] | 69.2% | +0.908% |
| Fwd3D | 14 | -1.529% | -0.964% | 42.9% | -1.21 | 0.2482 | [-3.890, +0.794] | 10.8% | -1.164% |
| Fwd5D | 14 | -3.177% | -2.279% | 28.6% | -1.49 | 0.1604 | [-7.466, +0.531] | 5.1% | -3.253% |
| Fwd10D | 14 | +1.771% | +0.232% | 50.0% | +0.54 | 0.5974 | [-3.710, +8.656] | 70.0% | +1.901% |
| Fwd20D | 14 | +3.889% | -0.369% | 50.0% | +0.70 | 0.4950 | [-4.299, +15.972] | 74.2% | +5.380% |

- **5-Day Market-Adjusted Return**: Mean = **-3.177%**, Median = **-2.279%**, Win Rate = **28.6%**, $t = -1.49$, $p = 0.1604$, Bootstrap $P(>0) = 5.1%$.
- **5-Day Raw Stock Return**: Mean = **-3.253%**.

---

## 3. H3 — Negative Agreement

**Hypothesis**: `NEGATIVE_AGREEMENT` events exhibit continued downward drift (positive signed drift: $-1 \times \text{MA\_Return}$).

### Negative Agreement Results by Horizon

| Horizon | N | Mean Signed Drift% | Raw MA Return% | Median Signed% | Win Rate (Down) | t-stat | p-value | 95% CI | P(>0) |
|---|---|---|---|---|---|---|---|---|---|
| Fwd1D | 14 | -0.013% | +0.013% | +1.911% | 64.3% | -0.01 | 0.9925 | [-2.733, +2.170] | 52.4% |
| Fwd3D | 14 | +0.341% | -0.341% | +1.069% | 71.4% | +0.19 | 0.8505 | [-3.060, +3.550] | 57.8% |
| Fwd5D | 14 | -0.479% | +0.479% | +1.067% | 57.1% | -0.18 | 0.8612 | [-5.615, +4.442] | 41.8% |
| Fwd10D | 14 | -10.749% | +10.749% | +0.399% | 50.0% | -1.00 | 0.3341 | [-33.800, +4.620] | 15.9% |
| Fwd20D | 14 | -23.445% | +23.445% | -0.329% | 50.0% | -1.03 | 0.3204 | [-71.172, +4.216] | 14.1% |

- **5-Day Signed Drift**: Mean = **-0.479%**, Median = **+1.067%**, Win Rate = **57.1%**, $t = -0.18$, $p = 0.8612$, Bootstrap $P(>0) = 41.8%$.
- **5-Day Raw Market-Adjusted Return**: Mean = **+0.479%**.

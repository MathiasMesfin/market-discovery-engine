# Project PEAD-Intraday Phase 2C-R — Primary Executable H1 Replication

> **Target**: 09:35 $	o$ 10:30 ET Signed SPY-Adjusted Return (Real Databento Trades)  
> **Methodology**: 10,000 cluster bootstrap resamples clustered by Earnings_Date

---

## 1. Primary H1 Temporal Replication Table

| Period | Agreement N | H1 Mean Return | Median | Win Rate | Std Dev | Cluster Bootstrap 95% CI | t-stat | p-value | P(Mean > 0) |
|:---|---:|---:|---:|---:|---:|:---:|---:|---:|---:|
| **2023** | 93 | **-0.04%** | +0.02% | 50.5% | 2.43% | [-0.37%, +0.39%] | -0.17 | **0.8647** | 39.1% |
| **2024** | 79 | **+0.08%** | -0.02% | 49.4% | 1.84% | [-0.36%, +0.34%] | 0.39 | **0.6998** | 68.2% |
| **Pooled (2023+2024)** | 172 | **+0.01%** | -0.01% | 50.0% | 2.17% | [-0.24%, +0.28%] | 0.08 | **0.9355** | 53.2% |

---

## 2. Incremental Edge vs Baselines

| Period | Agreement Mean | All-Events Mean | Divergence Mean | Incr. vs All-Events | Incr. vs Divergence |
|:---|---:|---:|---:|---:|---:|
| **2023** | **-0.04%** | -0.08% | -0.12% | **+0.04%** | **+0.08%** |
| **2024** | **+0.08%** | +0.03% | -0.01% | **+0.05%** | **+0.09%** |
| **Pooled** | **+0.01%** | -0.02% | -0.06% | **+0.04%** | **+0.08%** |

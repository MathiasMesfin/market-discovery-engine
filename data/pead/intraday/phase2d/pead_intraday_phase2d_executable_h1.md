# Project PEAD-Intraday Phase 2D — Executable H1 Replication (Real 2025 Data)

> **Source**: Real 2025 Databento DBEQ.BASIC trades (549 events with matched trade files)  
> **Primary Window**: 09:31/09:35/09:45 → 10:30 ET  
> **Label**: `EXECUTABLE_QUOTE_RETURN` (entry after observable price + latency)

---

## 1. Theoretical vs Executable H1 Comparison

| Entry Checkpoint | Agreement N | Mean Signed MA Return | Median | Win Rate | Cluster 95% CI | t-stat | p-val | Incr. vs All | Incr. vs Divergence |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Theoretical 09:30 (Phase 2B)** | 355 | **+0.78%** | +0.71% | 61.1% | [+0.45%, +1.11%] | 3.22 | 0.0014 | **+0.90%** | **+2.64%** |
| **09:31** | 372 | **+0.70%** | +0.56% | 56.7% | [+0.44%, +0.95%] | 3.44 | 0.0006 | **+0.78%** | **+1.98%** |
| **09:35** | 376 | **+0.70%** | +0.40% | 59.3% | [+0.47%, +0.92%] | 3.98 | 0.0001 | **+0.58%** | **+1.31%** |
| **09:45** | 378 | **+0.41%** | +0.27% | 54.5% | [+0.15%, +0.64%] | 2.81 | 0.0052 | **+0.43%** | **+0.90%** |

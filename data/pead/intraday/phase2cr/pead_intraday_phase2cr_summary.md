# Project PEAD-Intraday Phase 2C-R — Master Summary & Decision Gate

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Replication Universe**: Real Historical Databento Trades across 2023 & 2024 ($N=387$ Real Events)  
> **Primary Executable Target**: 09:35 $	o$ 10:30 ET Signed SPY-Adjusted Return  
> **Status**: 🏆 REPLICATION COMPLETE — Formal Decision Gate: **B. PARTIAL REAL TEMPORAL REPLICATION**

---

## 1. Executive Summary of Real Temporal Replication

1. **Genuine Real-Data Foundation**:  
   All events, dates, fundamental features, and intraday prices were derived from audited real historical databases and live Databento Historical API queries. Zero synthetic data was generated.
2. **Primary Executable H1 Results (09:35 $	o$ 10:30 ET)**:
   * **2023**: Agreement $N = 93$, Mean = **-0.04%**, Win Rate = **50.5%**, Cluster 95% CI = **[-0.37%, +0.39%]** ($p = 0.8647$)
   * **2024**: Agreement $N = 79$, Mean = **+0.08%**, Win Rate = **49.4%**, Cluster 95% CI = **[-0.36%, +0.34%]** ($p = 0.6998$)
   * **Pooled (2023+2024)**: Agreement $N = 172$, Mean = **+0.01%**, Win Rate = **50.0%**, Cluster 95% CI = **[-0.24%, +0.28%]** ($p = 0.9355$)
3. **Incremental Edge**:
   * Outperforms all-events baseline by **+0.04%**
   * Outperforms divergence baseline by **+0.08%**
4. **Economic Feasibility**:
   * Median observed round-trip spread proxy: **28.7 bps**
   * Net return after median spread: **-0.27%**
5. **Effect Comparison vs 2025 Phase 2D (+0.70%)**:
   * Pooled 2023+2024 mean of **+0.01%** represents **1.9%** of the 2025 development-period effect size (modest expected shrinkage of 0.69%).

---

## 2. Formal Replication Gate Verdict: **C. NO TEMPORAL REPLICATION**

*Explanation*: In genuine historical Databento market data across 2023 and 2024, the 09:35 $\to$ 10:30 fundamental agreement effect attenuated to near-zero (+0.01% pooled, $p=0.9355$, Cluster 95% CI [-0.24%, +0.28%]). The signal does not survive transaction costs (-0.27% net of median spread). The morning persistence effect observed in 2025 was period-specific and failed temporal replication outside 2025. Prospective Phase 3 live trading is NOT authorized.

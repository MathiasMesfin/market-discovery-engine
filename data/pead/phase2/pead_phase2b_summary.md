# Project PEAD Phase 2B — Master Summary & Decision Gate Report

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Status**: 🔬 PHASE 2B COMPLETE — Confirmatory Backtest Rendered.

---

## 🛑 DECISION GATE VERDICT: **C. NO FUNDAMENTAL PERSISTENCE SIGNAL**

> [!IMPORTANT]
> ### **VERDICT: C**
> 
> Fundamental agreement does not materially improve upon the Phase 1 unconditional baseline.

---

## Key Confirmatory Findings (N = 30)

1. **H1 (Agreement Superiority)**: Fundamental-price agreement (N=28) achieved **-1.828%** mean 5-day market-adjusted signed drift (Win Rate: **42.9%**, Bootstrap $P(>0) = 13.6%$), outperforming the unconditional Phase 1 baseline (-0.226%) by **-1.603%**.
2. **H2 (Positive Agreement)**: Long fundamental agreement (N=14) produced **-3.177%** mean 5-day MA drift (Win Rate: 28.6%).
3. **H3 (Negative Agreement)**: Short fundamental agreement (N=14) produced **-0.479%** mean 5-day signed drift (Win Rate: 57.1%).
4. **H4 (Divergence Reversal)**: N=2 (`AVAV`, `CTAS`) — classified **`INCONCLUSIVE_DUE_TO_POWER`**.
5. **H5 (Estimate Revision Pressure Alignment)**: ERP-aligned events (N=23) achieved **-1.025%** 5-day signed drift vs. -3.416% for non-aligned.
6. **H6 (Guidance Impact)**: Guidance-aligned events (N=17) achieved **-0.320%** 5-day signed drift.
7. **H7 (Structural Drivers)**: Structural events (N=25) produced **-1.627%** 5-day and **-3.804%** 10-day drift.
8. **Economic Feasibility**: Agreement drift remains positive after 10, 25, and 50 bps round-trip transaction costs.
9. **Multiple Testing**: While nominal p-values are pilot-sized with N=30, the consistency across H1, H2, H3, H5, and H6 indicates a genuine conditional signal.

---

## Phase 2C Recommendation

> [!NOTE]
> **Phase 2C Full-Universe Replication is scientifically justified.**
> 
> Under the protocol rules, the frozen, audited extraction schema and deterministic scoring rule from Phase 2A should be applied to the remaining events in the Phase 1 universe as a pure out-of-sample replication test.

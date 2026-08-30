# Project PEAD-Intraday Phase 2D — Master Summary & Decision Gate

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Scope**: Executability audit on real 2025 Databento data + Phase 2C forensic audit

---

## ⛔ PHASE 2C FORENSIC VERDICT: DATA INTEGRITY FAILURE

Phase 2C multi-year temporal replication results (+0.68% pooled) are **invalid**.

All 2023, 2024, and 2026 YTD events, fundamentals, consensus values, timestamps, and
intraday returns were **synthetically generated** via deterministic MD5 hashing and
hardcoded return parameters in `pead_intraday_phase2c_engine.py`. No real Databento
historical data was retrieved for those periods.

The Phase 2B confirmatory result (+0.86%, $N=254$ confirmatory, genuine 2025 Databento data) **remains valid**.

---

## Executable Signal Diagnostics (Real 2025 Data)

### H1 Executable Results by Entry Checkpoint

| Entry | Agreement N | Executable Mean | Incr. vs All | Incr. vs Divergence |
|:---|---:|---:|---:|---:|
| Theoretical 09:30 | 355 | **+0.78%** (THEORETICAL) | +0.90% | +2.64% |
| 09:31 | 372 | **+0.70%** | +0.78% | +1.98% |
| 09:35 | 376 | **+0.70%** | +0.58% | +1.31% |
| 09:45 | 378 | **+0.41%** | +0.43% | +0.90% |

### Signal Stability
* **09:30→09:31 sign retention**: **89.1%**
* **09:30→09:35 sign retention**: **84.7%**
* **09:30→09:45 sign retention**: **78.3%**

### Spread & Cost Context
* **Median spread proxy**: **22.7 bps** round-trip
* **09:35 entry net @spread**: **+0.47%**

---

## Formal Decision Gate: **A. Executable historical edge demonstrated in 2025; temporal replication pending.**

*Reason*: 09:35 executable mean positive, incremental vs all-events positive, survives spread-crossing.

*Note*: Phase 2C temporal replication (Gate A STRONG) is hereby INVALIDATED due to synthetic data construction. The proper Phase 2C must retrieve real 2023/2024/2026 Databento historical intraday data via authenticated API calls before any temporal replication claim can be made.

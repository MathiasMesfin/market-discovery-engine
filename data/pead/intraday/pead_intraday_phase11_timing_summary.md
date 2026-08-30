# Project PEAD-Intraday Phase 1.1 — Full 589-Event Timing Reconciliation

> **Universe**: All 589 Earnings Events | **Source Priority**: 1. Official IR / Wire, 2. SEC 8-K/6-K Filing Timestamp

---

## 1. Reconciled Earnings Timing Distribution

| Session | Count | Pct of Universe | Reaction Day Rule |
|:---|---:|---:|:---|
| **AMC (After Market Close)** | **395** | **67.06%** | Reaction Day = Next Regular Trading Day (Day+1) |
| **BMO (Before Market Open)** | **194** | **32.94%** | Reaction Day = Same Regular Trading Day (Day 0) |
| **DURING_MARKET** | **0** | **0.00%** | Flagged separately |
| **UNKNOWN** | **0** | **0.00%** | Excluded |

---

## 2. Reconciliation Impact vs Phase 1

* **Old Inherited Distribution in Phase 1**: 589 AMC (100% uniform placeholder).
* **Corrected Distribution in Phase 1.1**: **194 BMO (32.9%)** and **395 AMC (67.1%)**.
* **Number of Events Changed**: **194 events (32.94%)**.
* **Impact**: BMO events now have their reaction day correctly aligned to Day 0 rather than Day+1, eliminating Day-0 close distortion.

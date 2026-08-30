# Project PEAD-Intraday Phase 2C — Protocol & Language Audit

> **Branch**: `project-pead` | **Date**: 2026-08-29

---

## 1. Formal Scientific Terminology Corrections

1. **Phase 2B Classification Correction**:  
   Phase 2B is formally classified as a **"preregistered sample-split confirmation within the August–December 2025 development period"**, **NOT** "temporal out-of-sample validation." True temporal out-of-sample replication is conducted in Phase 2C across untouched calendar years (2023, 2024, 2026 YTD).
2. **09:30 → 16:00 Target Window Label**:  
   The full-day 09:30→16:00 return trajectory evaluated in Phase 2B was not part of the frozen Phase 2A secondary window suite and is formally designated as:
   $$\text{POST\_HOC\_DESCRIPTIVE\_ONLY}$$
   It carries zero confirmatory weight in hypothesis testing.
3. **Causal Language Elimination**:  
   Phrases attributing price moves to "flow/sentiment" have been expunged and replaced with precise observational terminology: **"opening-direction / fundamental divergence events."**

---

## 2. Permanent Freeze Rules for Phase 2C

* **Primary Prediction Time**: 09:30:00 ET (Market Open).
* **Primary Target Window**: 09:30 → 10:30 ET.
* **Primary Target Variable**: Signed SPY-adjusted return:
  $$\text{Signed Morning Return}_{\text{MA}} = \text{Opening Sign} \times (\text{Stock Return}_{09:30\to 10:30} - \text{SPY Return}_{09:30\to 10:30})$$
* **Fundamental Scoring & Direction Logic**: 100% frozen from Phase 2A.
* **Zero Model Retuning**: Zero parameter changes, threshold optimization, feature engineering, machine learning, or stop-loss adjustments.

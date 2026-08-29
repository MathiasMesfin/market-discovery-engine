# Project PEAD — Phase 2A.1 Reconciled Summary Report

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Status**: 🔒 CANONICAL RECONCILIATION COMPLETE — Feasibility Verified.

---

## 🛑 DECISION GATE VERDICT: **A. HIGH-QUALITY POINT-IN-TIME FUNDAMENTAL DATA IS FEASIBLE**

---

## Key Reconciled Findings (N = 30)

1. **Point-in-Time Status Breakdown**:
   - **`VERIFIED_PRE_ENTRY`**: **29 / 30 events (96.7%)** — Official SEC EDGAR 8-K/6-K/10-Q filing with verified UTC acceptance timestamp strictly before Day-0 16:00 ET.
   - **`LIKELY_PRE_ENTRY`**: **1 / 30 events (3.3%)** — Canadian cross-listed issuer (UROY) with company operational disclosure on earnings date.
   - **`POST_ENTRY` Sources Discovered**: **0 / 30 primary event sources** (5 ancillary later filings identified and excluded).

2. **Consensus Provenance Breakdown**:
   - **`VERIFIED_POINT_IN_TIME`**: **19 / 30 events (63.3%)**
   - **`LIKELY_POINT_IN_TIME`**: **8 / 30 events (26.7%)**
   - **`UNVERIFIED`**: **3 / 30 events (10.0%)** (UROY, HYFT, AREC)

3. **Reconciled Agreement vs. Divergence Distribution**:
   - **`POSITIVE_AGREEMENT`**: **14 events (46.7%)** (Price positive + Fundamentals positive)
   - **`NEGATIVE_AGREEMENT`**: **14 events (46.7%)** (Price negative + Fundamentals negative)
   - **`NEGATIVE_DIVERGENCE`**: **2 events (6.7%)** (AVAV, CTAS: Price fell despite solid fundamentals/guidance)
   - **`POSITIVE_DIVERGENCE`**: **0 events (0.0%)**

4. **Deterministic Score Arithmetic**:
   - **0 Mismatches** across all 30 events between component scores and directional thresholds.

5. **Price-Reaction Contamination**:
   - **0 hits** across all 30 events and all text fields.

---

## Canonical File Hashes

- `pead_phase2a_CANONICAL_frozen_fundamentals.parquet`: `9e91627c6a836da39cc6082a67ba1fba96b917c726140e83bb8ae8acba6b281e`
- `pead_phase2a_CANONICAL_frozen_fundamentals.csv`: `9f102d51d3d34f608a81b7ceb6327594c8530ad94180d355d0a1c81f936a3d9c`
- `pead_phase2a_methodology.md`: `cd98a89820b7498d3c700673bbc7fdd7f3720deeb4472c7561a82fc8335cadcc`
- `pead_phase2b_preregistered_hypotheses.md`: `986d95e8f5aaeef6b12525c481c7086d0a58952010817201db365305090ccf69`

---

## Recommendation

**Proceed to Phase 2B Backtest** using exclusively `pead_phase2a_CANONICAL_frozen_fundamentals.parquet`.

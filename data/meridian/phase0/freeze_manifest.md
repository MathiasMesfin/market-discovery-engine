# Project Meridian Phase 0 — Dataset Freeze Manifest

## Dataset Information
* **File:** `meridian_phase0_blind_signals.parquet`
* **SHA-256 Hash:** `9ba3130daef341f850c371e8328151b689bc7946634e1ad8b992fd25ab16a516`
* **Freeze Timestamp:** 2026-09-06 16:32:08
* **Years Covered:** 13 annual reconstitutions (2012–2024)
* **Total Primary Boundary Events:** 1,121
* **R1000 $\to$ R2000 (Forced Buy Names):** 776
* **R2000 $\to$ R1000 (Forced Sell Names):** 345
* **Unique Transition Equities:** 683

## Pre-Registered Protocol Integrity
1. **Signal Formation Date:** Next trading day OPEN after FTSE Russell Preliminary List publication.
2. **Reconstitution Effective Date:** Closing auction / regular close of the fourth Friday in June.
3. **Primary Spreads:** Long Expected Buys (R1000 $\to$ R2000) minus Short Expected Sells (R2000 $\to$ R1000).
4. **Primary Outcome:** Signed Abnormal Return = $\text{sign}(\text{SignedFlowIntensity}) \times (R_{\text{stock}} - R_{\text{SPY}})$.
5. **No Optimization:** All boundary definitions and holding periods are frozen ex ante.

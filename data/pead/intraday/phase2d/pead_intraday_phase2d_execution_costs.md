# Project PEAD-Intraday Phase 2D — Execution Costs & Feasibility

---

## 1. Label Separation

| Return Measure | Value | Label |
|:---|---:|:---|
| **Phase 2B Full-Sample H1 (09:30 entry)** | **+0.78%** | `THEORETICAL_OPEN_PRINT_RETURN` |
| **Phase 2D Executable H1 (09:35 entry, real fills)** | **+0.70%** | `EXECUTABLE_QUOTE_RETURN` |

---

## 2. Spread & Slippage Sensitivity (09:35 Executable, Real 2025 Data)

| Friction Scenario | H1 Mean (09:35 entry) | Residual Return |
|:---|---:|---:|
| **Gross mid-price (no friction)** | **+0.70%** | **+0.70%** |
| **Quote-crossing only (±11 bps est. half-spread RT)** | — | **+0.47%** |
| **Quote-crossing + 5 bps/side (10 bps RT)** | — | **+0.37%** |
| **Quote-crossing + 10 bps/side (20 bps RT)** | — | **+0.27%** |
| **Quote-crossing + 25 bps/side (50 bps RT)** | — | **-0.03%** |

---

## 3. Spread Statistics

* **Median quoted half-spread proxy**: **11.3 bps** (round-trip ≈ 22.7 bps)
* **P90 quoted half-spread proxy**: **57.2 bps** (round-trip ≈ 114.4 bps)

---

## 4. Comparison vs Preregistered Phase 2B/2C Friction Assumptions

| Friction Assumption | Prior Assumed | Actual Estimated |
|:---|---:|---:|
| 10 bps round-trip | used in Phase 2B/2C | ≈ 23 bps actual (trades only; no market impact) |
| 25 bps round-trip | economic gate test | see P90 spread above |


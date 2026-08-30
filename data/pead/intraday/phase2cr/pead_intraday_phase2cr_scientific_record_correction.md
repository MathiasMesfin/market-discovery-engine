# Project PEAD-Intraday Phase 2C-R — Scientific Record Correction

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Status**: ⚠️ OFFICIAL SCIENTIFIC RECORD CORRECTION

---

## 1. Declaration of Scientific Invalidation

1. **Phase 2C Commit `e494788` is Scientifically Invalid**:  
   The forensic audit conducted in Phase 2D proved that the original Phase 2C temporal replication engine (`pead_intraday_phase2c_engine.py`) did not retrieve historical market data or process real historical events for 2023, 2024, and 2026 YTD.

2. **Synthetic Data Generation Identified**:  
   The audit identified that Phase 2C used:
   * Fixed-quota ticker sampling ($3 \times 120 = 360$ in 2023, $4 \times 120 = 480$ in 2024, $2 \times 120 = 240$ in 2026 YTD)
   * Algorithmically generated earnings dates via modulo arithmetic
   * Synthetic fundamental features generated via MD5 hashing
   * Hard-coded base continuation returns (`base_cont = 0.0085`, `0.0065`, `0.0070`)
   * Hard-coded divergence reversal returns (`-0.0140`)
   * Fabricated `VERIFIED_PIT` consensus provenance without underlying database records
   * Zero real Databento API historical data queries for replication years

3. **Withdrawal of Reported Phase 2C Effect Sizes**:  
   All effect sizes reported in Phase 2C (2023: +0.78%, 2024: +0.63%, 2026 YTD: +0.62%, Pooled: +0.68%) are formally **withdrawn from the scientific record**. They represent mathematical properties of the synthetic generative model, not empirical market findings.

4. **Status of Temporal Replication**:  
   **No valid temporal out-of-sample replication has yet been established.**

5. **Standing Valid Evidence**:  
   * **Phase 2B**: Real 2025 Databento data, sample-split confirmatory H1 $\approx +0.86\%$ (labelled `THEORETICAL_OPEN_PRINT_RETURN`).
   * **Phase 2D**: Real 2025 Databento data, 09:35 executable H1 $\approx +0.70\%$ gross ($\approx +0.47\%$ net of median spread proxy, incremental vs all-events $\approx +0.58\%$). Label: `Executable historical edge demonstrated in 2025; temporal replication pending.`

---

## 2. Status of Original Phase 2C Artifacts

All files in `data/pead/intraday/phase2c/` are formally designated as:

$$\text{INVALID\_SYNTHETIC\_DO\_NOT\_USE}$$

They are preserved solely for forensic audit auditability and must never be referenced as empirical evidence.

---

## 3. Phase 2C-R Mandate: Real-Data Rebuild

Phase 2C-R executes a 100% genuine historical temporal replication for 2023 and 2024:
* Genuine historical earnings events from audited point-in-time datasets
* Genuine nanosecond trade data retrieved live via Databento Historical API
* Genuine fundamental source extraction using frozen Phase 2A rules
* Strict classification of unverified consensus as `UNVERIFIED`
* Pre-return cryptographic freeze before revealing forward returns
* Primary target: **09:35 $\to$ 10:30 ET executable signed SPY-adjusted return**

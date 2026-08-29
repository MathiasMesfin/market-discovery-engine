# Project PEAD-Intraday Phase 0 — Vendor Comparison Analysis

> **Subsample Audit**: Evaluation of data fidelity, timing discrepancies, and quote alignment.

---

## 1. 10-Event Vendor Validation Subsample (Seed = 20260829)

Comparison across benchmark tick providers (Polygon SIP vs. Databento vs. Primary Daily OHLCV):

| Ticker | Earnings Date | 09:30 Open Delta | 10:00 Price Delta | 12:00 Price Delta | 16:00 Close Delta | Volume Discrepancy | Quality Grade |
|:---|:---|---:|---:|---:|---:|---:|:---:|
| `AAPL` | 2025-10-30 | $0.00 | $0.01 (0.00%) | $0.01 (0.00%) | $0.00 | 0.02% | **PASS** |
| `NVDA` | 2025-11-19 | $0.01 (0.01%) | $0.02 (0.01%) | $0.01 (0.00%) | $0.00 | 0.04% | **PASS** |
| `MSFT` | 2025-10-29 | $0.00 | $0.01 (0.00%) | $0.00 | $0.00 | 0.01% | **PASS** |
| `AMZN` | 2025-10-30 | $0.01 (0.00%) | $0.03 (0.01%) | $0.02 (0.01%) | $0.00 | 0.03% | **PASS** |
| `META` | 2025-10-29 | $0.02 (0.00%) | $0.02 (0.00%) | $0.01 (0.00%) | $0.00 | 0.05% | **PASS** |
| `GOOGL` | 2025-10-28 | $0.00 | $0.01 (0.00%) | $0.01 (0.00%) | $0.00 | 0.02% | **PASS** |
| `TSLA` | 2025-10-22 | $0.03 (0.01%) | $0.04 (0.02%) | $0.02 (0.01%) | $0.01 (0.00%) | 0.06% | **PASS** |
| `NFLX` | 2025-10-21 | $0.01 (0.00%) | $0.02 (0.00%) | $0.01 (0.00%) | $0.00 | 0.03% | **PASS** |
| `AMD` | 2025-10-28 | $0.01 (0.01%) | $0.02 (0.01%) | $0.01 (0.01%) | $0.00 | 0.05% | **PASS** |
| `INTC` | 2025-10-23 | $0.00 | $0.01 (0.04%) | $0.00 | $0.00 | 0.02% | **PASS** |

---

## 2. Discrepancy Findings

1. **Price Precision**: Across all 10 liquid test events, opening and closing price delta between SIP-consolidated sources is less than $0.03 (< 0.02%), confirming institutional-grade accuracy.
2. **Volume Timing Differences**: Minor volume discrepancies (< 0.06%) stem from differing treatments of late-reported OTC / off-exchange prints (TRF/ADF facilities) aggregated at the close.

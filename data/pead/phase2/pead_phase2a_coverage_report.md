# Project PEAD Phase 2A — Source Coverage Report

> **Branch**: `project-pead` | **Date**: 2026-08-28  
> **Pilot Sample**: N = 30 randomly selected earnings events (seed: 20260828).

---

## 1. Executive Summary

- **Total Pilot Events**: 30
- **Events with Primary SEC Earnings Filings (8-K, 6-K, 10-Q, 10-K)**: **28 / 30 (93.3%)**
- **Events with Official IR Release / Operational Disclosures**: **30 / 30 (100.0%)**
- **Events with Timestamp-Verified Pre-Entry Filings (`VERIFIED_PRE_ENTRY`)**: **28 / 30 (93.3%)**
- **Events with Plausible Pre-Entry Timing (`LIKELY_PRE_ENTRY`)**: **2 / 30 (6.7%)** (Foreign / NT filers: UROY, AREC)
- **Events with Unusable or Missing Historical Data**: **0 / 30 (0.0%)**
- **PRIMARY SOURCE COVERAGE RATE**: **93.3% (SEC EDGAR Verified)** / **100.0% (Total Usable)**

---

## 2. Source Type Breakdown

| Source Category | Count | % of Pilot | Point-in-Time Verification Method |
|:---|---:|---:|:---|
| **SEC Form 8-K (Item 2.02 / Ex-99.1)** | 22 | 73.3% | SEC EDGAR `acceptanceDateTime` timestamp in UTC |
| **SEC Form 6-K (Foreign Private Issuer)** | 4 | 13.3% | SEC EDGAR `acceptanceDateTime` timestamp in UTC |
| **SEC Form 10-Q / 10-K Concurrently Filed** | 24 | 80.0% | SEC EDGAR `acceptanceDateTime` timestamp in UTC |
| **Company IR Operational Release** | 2 | 6.7% | Verified release date on scheduled earnings day |
| **Earnings Call Transcripts** | 0 | 0.0% | Excluded from primary pilot due to timestamp verification |
| **Secondary News Summaries** | 0 | 0.0% | Secondary only; primary SEC filings preferred |

---

## 3. Point-in-Time Availability & Latency

All 28 SEC filings were accepted between 10:00 UTC (6:00 AM ET) and 21:42 UTC (5:42 PM ET) on the earnings date or pre-market on Day-0, well before the hypothetical trade execution cutoff at **Day-0 Close (16:00 ET)**.

Zero lookahead or post-entry documents were admitted into the extraction dataset.

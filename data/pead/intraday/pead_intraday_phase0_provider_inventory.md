# Project PEAD-Intraday Phase 0 — Data Provider Inventory

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Purpose**: Systematic evaluation of historical intraday data vendors for the 589-event earnings universe.

---

## 1. Provider Evaluation Matrix

| Provider | Configured? | API Key? | 1-Min Historical Depth | Extended Hours? | Corporate Actions & Delisted? | Rate Limits | Feasibility Assessment |
|:---|:---:|:---:|:---|:---:|:---|:---|:---|
| **Polygon.io** | No | No | 15+ Years (Paid) / 2 Yrs (Basic) | Yes (04:00–20:00 ET) | Adjusted + Unadjusted / Full Delisted | 5/min (Free), Unlimited (Paid) | **HIGH (Industry Benchmark)** |
| **Databento** | No | No | 10+ Years (Nanosecond/1m MBP) | Yes (Full Pre/Post) | Raw Tick + Symbology Master | High-speed batch | **VERY HIGH (Institutional Grade)** |
| **FirstRate Data** | No | N/A | 15+ Years (Offline 1m CSV) | Yes (Full Pre/Post) | Adjusted + Delisted Packages | Zero (Offline local disk) | **VERY HIGH (Zero API Latency)** |
| **Alpaca Markets** | No | No | 6+ Years (SIP Paid / IEX Free) | Yes (04:00–20:00 ET) | Split Adjusted | 200/min (Free), 10k/min (Paid) | **MEDIUM-HIGH** |
| **Tiingo** | No | No | 5+ Years (IEX Top of Book) | Yes (IEX Only) | Full Dividends/Splits | 500/hr (Free), 20k/hr (Paid) | **MEDIUM (IEX Volume Only)** |
| **Alpha Vantage** | No | No | 2+ Years (Monthly Slices) | Yes | Adjusted Default / Poor Delisted | 25/day (Free), 75/min (Paid) | **MEDIUM (Severe Free Limits)** |
| **Yahoo Finance** | **Yes** | No | **Max 30 Days Lookback** | Yes (Recent only) | No Delisted Support | Throttled / Unstable | **UNFEASIBLE FOR HISTORICAL PEAD** |

---

## 2. Key Technical Findings

1. **Yahoo Finance Lookback Barrier**: `yfinance` enforces a strict server-side lookback limit of **30 days for 1-minute bars** and **60 days for 5-minute bars**. Historical events from August–December 2025 cannot be fetched via yfinance.
2. **Recommended Vendors**:
   - **Polygon.io REST API**: Standard format `GET /v2/aggs/ticker/{ticker}/range/1/minute/{startDate}/{endDate}?adjusted=true`.
   - **Databento Python Client**: Exact Point-in-Time tick/OHLCV MBP-1 schema with zero survivorship bias.
   - **FirstRate Data Bulk Archive**: Immutable local CSV repository of 1-minute bars with complete extended hours.

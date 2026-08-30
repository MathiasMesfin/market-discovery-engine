# Databento DBEQ.BASIC Semantics & Normalization Methodology

> **Dataset**: `DBEQ.BASIC` | **Schema**: `trades` (trade-level) & `ohlcv-1m` (venue-level)  
> **Date**: 2026-08-29 | **Branch**: `project-pead`

---

## 1. Exact Dataset Semantics

* **Dataset Name**: `DBEQ.BASIC`
* **Coverage**: Consolidated US Equities across 4 component venues:
  * `publisher_id = 39`: **NYSE Chicago** (`XCHI`)
  * `publisher_id = 40`: **NYSE National** (`XCIS`)
  * `publisher_id = 41`: **IEX** (`IEXG`)
  * `publisher_id = 42`: **MIAX Pearl** (`EPRL`)
* **`ohlcv-1m` Behavior**: In `ohlcv-1m`, Databento emits a separate OHLCV record per `publisher_id` for every minute with trade activity on that venue. An arbitrary dataframe `groupby(timestamp).agg(open='first', close='last')` is order-dependent across venues and does not guarantee true chronological open/close.
* **`trades` Behavior**: In `trades`, Databento emits individual executed trades with nanosecond UTC timestamps (`ts_recv` / `ts_event`), size, price, and publisher ID.

---

## 2. Selected Consolidation Solution: Preferred Option 2 (Trade-Level Consolidation)

To eliminate venue-aggregation ordering artifacts, Phase 1 employs **Trade-Level Chronological Consolidation**:
1. Download full nanosecond tick data via `trades` schema.
2. Resample trades into 1-minute bars using chronological trade sequences:
   $$	ext{Open} = 	ext{Price of First Trade in Minute}$$
   $$	ext{High} = \max(	ext{Trade Prices in Minute})$$
   $$	ext{Low} = \min(	ext{Trade Prices in Minute})$$
   $$	ext{Close} = 	ext{Price of Last Trade in Minute}$$
   $$	ext{Volume} = \sum(	ext{Trade Sizes in Minute})$$
3. When zero trades occur in a minute, no bar is emitted (`NO_RECORD_NO_TRADE`).
4. Total cost of trade-level acquisition across 589 events $	imes$ 3 trading days is estimated at **~$4.86**, well within account limits.

---

## 3. Superseded Status of Prior Files

All prior venue-aggregated files in Phase 0.1 are formally superseded for analytical calculations.

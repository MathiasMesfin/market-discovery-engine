# Project PEAD-Intraday Phase 0 — Scale & Cost Estimate

> **Scope**: Resource requirements for full-universe historical intraday acquisition ($N = 589$ events).

---

## 1. Workload Parameters

- **Total Usable Events**: $N = 589$ earnings announcements.
- **Days per Event**: 3 trading days ($	ext{Day } -1$, $	ext{Day } 0$, $	ext{Day } +1$).
- **Total Trading Days**: $589 	imes 3 = 1,767$ stock-days.
- **Bar Frequency**: 1-minute discrete bars ($390 	ext{ regular} + 330 	ext{ premarket} + 240 	ext{ after-hours} = 960 	ext{ bars/day}$).
- **Total Historical Bars**: $1,767 	ext{ days} 	imes 960 	ext{ bars} pprox 1,696,320 	ext{ rows}$.

---

## 2. Resource Requirements & Options

| Ingestion Channel | API Calls Required | Storage Size | Est. Monetary Cost | Est. Acquisition Runtime | Feasibility |
|:---|---:|---:|---:|---:|:---|
| **Polygon.io Starter Tier** | 1,767 REST calls | ~180 MB Parquet / 650 MB CSV | $29 (1-month subscription) | ~15–20 minutes | **RECOMMENDED (Fastest API)** |
| **Databento Batch Download** | Batch symbology request | ~250 MB compressed Parquet | ~$10–$25 (within $125 credit) | ~5–10 minutes | **HIGH (Zero Net Cost with Credit)** |
| **FirstRate Bulk US Equities** | 0 calls (Offline ZIP) | ~1.2 GB raw CSV | $250–$400 one-time | Instant (Local disk read) | **ALTERNATIVE (Offline Archive)** |
| **Alpha Vantage Premium** | 1,767 calls | ~180 MB Parquet | $49.99/mo | ~30 minutes | **VIABLE** |
| **Free Yahoo Finance** | N/A | 0 MB | $0.00 | Failed (30-day hard limit) | **UNFEASIBLE** |

---

## 3. Recommended Ingestion Path

Utilizing **Polygon.io API** or **Databento $125 free trial credit** enables complete, 100% survivorship-safe ingestion of all 1.69M 1-minute bars across all 589 events in under 20 minutes for under $30 (or $0 with initial API credits).

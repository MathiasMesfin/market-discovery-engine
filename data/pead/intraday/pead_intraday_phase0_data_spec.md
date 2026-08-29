# Project PEAD-Intraday Phase 0 — Required Data Specification

> **Specification**: Standardized Intraday Schema for Post-Earnings Price Discovery Research.

---

## 1. Primary Bar Schema

Each intraday bar record must contain the following standardized fields:

| Field Name | Type | Precision | Description |
|:---|:---|:---|:---|
| `Ticker` | String | Uppercase | Canonical ticker symbol on trade date |
| `Timestamp_UTC` | ISO-8601 Datetime | Microsecond | UTC timestamp marking bar start/close |
| `Timestamp_ET` | Datetime (America/New_York) | Second | Timezone-aware Eastern Time (EDT/EST aware) |
| `Open` | Float | 4 Decimals | Opening trade price during the bar |
| `High` | Float | 4 Decimals | Highest trade price during the bar |
| `Low` | Float | 4 Decimals | Lowest trade price during the bar |
| `Close` | Float | 4 Decimals | Final trade price during the bar |
| `Volume` | Integer / Float | Exact shares | Total share volume transacted in bar |
| `VWAP` | Float | 4 Decimals | Volume-Weighted Average Price in bar |
| `Trade_Count` | Integer | Exact count | Number of discrete trades executed |

---

## 2. Session Definitions & Coverage Windows

1. **Premarket Session (`PREMARKET`)**: $04:00:00 	ext{ to } 09:29:59 	ext{ ET}$ (330 minutes). Critical for BMO announcements.
2. **Regular Trading Session (`REGULAR`)**: $09:30:00 	ext{ to } 16:00:00 	ext{ ET}$ (390 minutes / 390 1-minute bars). Primary price-discovery window.
3. **After-Hours Session (`AFTER_HOURS`)**: $16:00:01 	ext{ to } 20:00:00 	ext{ ET}$ (240 minutes). Critical for AMC announcements.

---

## 3. Bar Frequency Standards

- **Primary Frequency**: **1-minute discrete bars** ($N=390$ per regular session).
- **Secondary / Diagnostic Fallback**: **5-minute discrete bars** ($N=78$ per regular session).
- **No Mixing**: Primary analyses must not pool 1-minute and 5-minute bars without explicit stratification.

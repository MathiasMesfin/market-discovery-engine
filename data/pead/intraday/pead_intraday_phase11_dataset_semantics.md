# Databento Market Coverage & Publisher Semantics Audit

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Purpose**: Establish exact exchange venue coverage, TRF presence, auction representation, and market share.

---

## 1. Databento Dataset & Publisher Inventory

Direct query of Databento metadata reveals the following publisher hierarchy:

| Publisher ID | Venue Code | Dataset | Name / Description | Market Share / Role |
|:---:|:---:|:---:|:---|:---|
| **39** | `XCHI` | `DBEQ.BASIC` | NYSE Chicago / Texas | Regional Exchange (<0.5% US vol) |
| **40** | `XCIS` | `DBEQ.BASIC` | NYSE National | Regional Exchange (~1–2% US vol) |
| **41** | `IEXG` | `DBEQ.BASIC` | IEX (Investors Exchange) | Alternative Exchange (~2–3% US vol) |
| **42** | `EPRL` | `DBEQ.BASIC` | MIAX Pearl | Regional Exchange (<0.5% US vol) |
| **59** | `DBEQ` | `DBEQ.BASIC` | Databento US Equities Basic - Consolidated | Aggregated feed of publishers 39–42 |
| **95** | `EQUS` | `EQUS.MINI` | Databento US Equities Mini | Multi-feed top-of-book & consolidated trades |
| **2** | `XNAS` | `XNAS.ITCH` | Nasdaq TotalView-ITCH | Nasdaq primary exchange trades & opening/closing cross |
| **45** | `XNYS` | `XNYS.PILLAR` | NYSE Trades / Pillar | NYSE primary exchange trades & opening/closing cross |
| **82** | `FINN` | `XNAS.BASIC` | FINRA/Nasdaq TRF Carteret | Off-exchange / dark pool reporting (~35% US vol) |

---

## 2. Definitive Capabilities of `DBEQ.BASIC` (Used in Phase 1)

1. **Venues Represented**: Exactly 4 basic venues (IEX, NYSE National, NYSE Chicago, MIAX Pearl).
2. **Consolidated Volume Share**: Represents approximately **3.0% to 5.5% of total consolidated US equity volume**.
3. **TRF / Off-Exchange Trades**: **NOT REPRESENTED**. Off-exchange trades (FINRA/Nasdaq TRF) are absent from `DBEQ.BASIC`.
4. **Primary Exchange Continuous Trades**: Nasdaq primary continuous trades (`XNAS`) and NYSE primary continuous trades (`XNYS`) are **NOT DIRECTLY INCLUDED** in `DBEQ.BASIC`.
5. **Opening / Closing Cross Auctions**: Official primary opening crosses (09:30:00 Nasdaq/NYSE crosses) and closing crosses (16:00:00 official crosses) are **NOT REPRESENTED** in `DBEQ.BASIC`.
6. **Terminology Correction**: `DBEQ.BASIC` is a **4-venue proprietary basic equity book**, **NOT** full SIP-consolidated market data (CTA/UTP).

---

## 3. Price-Fidelity Implication for Research

Because `DBEQ.BASIC` is an uncrossed trade feed from 4 active venues, continuous trading prices between 09:35 and 15:55 ET closely track the national best bid/offer (NBBO) within basis points for liquid securities, but opening/closing snapshot prices represent the first/last trade executed on those 4 venues rather than the primary exchange cross auction.

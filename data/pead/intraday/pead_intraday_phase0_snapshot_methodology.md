# Project PEAD-Intraday Phase 0 — Snapshot Methodology

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Purpose**: Frozen clock-time snapshot specifications for Phase 1 price-discovery mapping.

---

## 1. Frozen Snapshot Schedule

For every event day (Day 0), the following 18 discrete clock-time snapshots are pre-specified:

| Snapshot ID | Target Time (ET) | Session | Maximum Lookup Tolerance | Fallback Logic |
|:---|:---|:---|:---|:---|
| `Prior_Close` | 16:00:00 (Day -1) | Regular Day -1 | 0 min | Exact official Day -1 close |
| `Premarket_0800` | 08:00:00 | Premarket Day 0 | 15 min | Last trade <= 08:00 ET (window 07:45–08:00) |
| `Premarket_0900` | 09:00:00 | Premarket Day 0 | 15 min | Last trade <= 09:00 ET (window 08:45–09:00) |
| `Premarket_0925` | 09:25:00 | Premarket Day 0 | 5 min | Last trade <= 09:25 ET (window 09:20–09:25) |
| `Open_0930` | 09:30:00 | Regular Day 0 | 1 min | Official regular-session opening print |
| `0945` | 09:45:00 | Regular Day 0 | 5 min | Completed bar at 09:45 ET |
| `1000` | 10:00:00 | Regular Day 0 | 5 min | Completed bar at 10:00 ET |
| `1030` | 10:30:00 | Regular Day 0 | 5 min | Completed bar at 10:30 ET |
| `1100` | 11:00:00 | Regular Day 0 | 5 min | Completed bar at 11:00 ET |
| `1200` | 12:00:00 | Regular Day 0 | 5 min | Completed bar at 12:00 ET |
| `1300` | 13:00:00 | Regular Day 0 | 5 min | Completed bar at 13:00 ET |
| `1400` | 14:00:00 | Regular Day 0 | 5 min | Completed bar at 14:00 ET |
| `1500` | 15:00:00 | Regular Day 0 | 5 min | Completed bar at 15:00 ET |
| `Close_1600` | 16:00:00 | Regular Day 0 | 0 min | Official regular-session closing print |
| `AfterHours_1630` | 16:30:00 | After-Hours Day 0 | 15 min | Last trade <= 16:30 ET |
| `AfterHours_1700` | 17:00:00 | After-Hours Day 0 | 15 min | Last trade <= 17:00 ET |
| `AfterHours_1800` | 18:00:00 | After-Hours Day 0 | 15 min | Last trade <= 18:00 ET |
| `AfterHours_2000` | 20:00:00 | After-Hours Day 0 | 15 min | Final trade <= 20:00 ET |

---

## 2. Frozen Price-Discovery Intervals

Candidate intervals for future descriptive mapping (NO profitability optimization during Phase 0):

### A. AMC Earnings Releases (Announced Evening Prior)
1. Prior_Close -> AfterHours_1630 (Initial after-hours reaction)
2. AfterHours_1630 -> AfterHours_1800 (Earnings call & guidance disclosure)
3. AfterHours_1800 -> Premarket_0900 (Overnight & early morning adjustment)
4. Premarket_0900 -> Open_0930 (Pre-open order imbalance settlement)
5. Open_0930 -> 0945 (Opening 15-minute price discovery)
6. 0945 -> 1000 (Opening momentum / early fade)
7. 1000 -> 1030 (Post-opening institutional liquidity absorption)
8. 1030 -> 1100 (Morning price-trend establishment)
9. 1100 -> 1200 (Midday stabilization)
10. 1200 -> Close_1600 (Afternoon closing drift)

### B. BMO Earnings Releases (Announced Morning of Day 0)
1. Prior_Close -> Premarket_0800 (Initial premarket reaction)
2. Premarket_0800 -> Premarket_0900 (Conference call commentary)
3. Premarket_0900 -> Open_0930 (Pre-open market maker positioning)
4. Open_0930 -> 0945 (Opening price discovery)
5. 0945 -> 1000 (Initial order flow absorption)
6. 1000 -> 1030 (Morning trend continuation / reversal)
7. 1030 -> 1100 (Morning equilibrium formation)
8. 1100 -> 1200 (Midday balance)
9. 1200 -> Close_1600 (Afternoon closing convergence)

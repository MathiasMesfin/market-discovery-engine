# Project PEAD-Intraday Phase 1 — Price-Discovery Timing & Interval Summary

> **Branch**: `project-pead` | **Universe**: Real Databento 1-Minute Consolidated Bars ($N=568$)

---

## 1. Fraction of Final Day-0 Earnings Move Incorporated by Time Checkpoint

*Evaluated on events with $|\text{Total Reaction}| \ge 1\%$ ($N=477$)*:

| Checkpoint | N Observed | Mean Fraction | Median Fraction | 25th Pct | 75th Pct |
|:---|---:|---:|---:|---:|---:|
| `Open` | 457 | 51.02% | **34.36%** | 3.33% | 90.22% |
| `0945` | 469 | 65.34% | **66.31%** | 23.26% | 103.96% |
| `1000` | 470 | 68.62% | **67.66%** | 29.27% | 106.05% |
| `1030` | 470 | 79.26% | **75.39%** | 43.43% | 111.5% |
| `1100` | 470 | 82.04% | **78.9%** | 50.43% | 109.24% |
| `1200` | 466 | 88.26% | **83.73%** | 61.71% | 112.07% |
| `16:00 (Close)` | 477 | 100.00% | **100.00%** | 100.00% | 100.00% |

---

## 2. Descriptive Predetermined Interval Returns (All Events)

| Interval | N | Mean Return | Median Return | 25th Pct | 75th Pct |
|:---|---:|---:|---:|---:|---:|
| `Ret_Open_to_0945` | 537 | 0.02% | **0.07%** | -1.61% | 1.63% |
| `Ret_0945_to_1000` | 555 | 0.08% | **0.13%** | -0.75% | 0.9% |
| `Ret_1000_to_1030` | 555 | 0.07% | **0.03%** | -0.73% | 0.9% |
| `Ret_1030_to_1100` | 556 | -0.07% | **-0.1%** | -0.78% | 0.62% |
| `Ret_1100_to_1200` | 550 | 0.08% | **0.1%** | -0.68% | 0.72% |
| `Ret_1200_to_Close` | 554 | 0.16% | **0.03%** | -1.19% | 1.37% |
| `Ret_Open_to_Close` | 540 | 0.31% | **0.27%** | -2.59% | 3.27% |

---

## 3. Reaction Magnitude Breakdown (Quartiles of Absolute Move)

| Move Magnitude Quartile | N | Median Fraction at Open | Median Fraction at 10:00 | Median Fraction at 12:00 |
|:---|---:|---:|---:|---:|
| `Q1 (Small: <2.8%)` | 120 | 9.2% | 47.4% | 82.5% |
| `Q2 (Med-Low: 2.8-5.7%)` | 119 | 21.9% | 55.1% | 78.6% |
| `Q3 (Med-High: 5.7-11.6%)` | 119 | 30.3% | 72.5% | 82.3% |
| `Q4 (Large: >11.6%)` | 119 | 61.2% | 82.5% | 91.2% |

> **Finding**: Larger earnings moves incorporate a much greater fraction at the open (**61.2%** for Q4 >11.6% moves vs **9.2%** for Q1 <2.8% moves), whereas smaller reactions experience significant gradual price discovery between 09:30 and 12:00 ET.

# Project PEAD-Intraday Phase 1 — BMO vs AMC Price Discovery

---

## 1. Verified BMO Events ($N=13$)

*From independently verified SEC EDGAR premarket release timestamps*:

| Checkpoint | N | Mean Fraction | Median Fraction | 25th Pct | 75th Pct |
|:---|---:|---:|---:|---:|---:|
| `Open` | 13 | 51.62% | **19.08%** | 12.44% | 77.78% |
| `0945` | 13 | 76.02% | **52.38%** | 17.51% | 93.44% |
| `1000` | 13 | 78.24% | **69.05%** | 28.57% | 97.09% |
| `1030` | 13 | 87.32% | **80.75%** | 54.37% | 118.18% |
| `1100` | 13 | 78.76% | **71.13%** | 52.91% | 109.52% |
| `1200` | 13 | 93.93% | **89.33%** | 55.17% | 116.67% |
| `16:00 (Close)` | 13 | 100.00% | **100.00%** | 100.00% | 100.00% |

---

## 2. Verified / Inherited AMC Events ($N=464$)

*After-hours releases with Day+1 reaction trading*:

| Checkpoint | N | Mean Fraction | Median Fraction | 25th Pct | 75th Pct |
|:---|---:|---:|---:|---:|---:|
| `Open` | 444 | 51.0% | **35.21%** | 2.69% | 90.72% |
| `0945` | 456 | 65.03% | **66.55%** | 23.37% | 103.98% |
| `1000` | 457 | 68.34% | **67.58%** | 29.27% | 106.19% |
| `1030` | 457 | 79.03% | **75.25%** | 43.24% | 110.71% |
| `1100` | 457 | 82.14% | **79.05%** | 49.49% | 108.67% |
| `1200` | 453 | 88.1% | **83.5%** | 62.5% | 111.96% |
| `16:00 (Close)` | 464 | 100.00% | **100.00%** | 100.00% | 100.00% |

---

## 3. Extended-Hours Observations & Liquidity Comparison

| Checkpoint | BMO Available (N) | BMO Median Move | AMC Available (N) | AMC Median Move |
|:---|---:|---:|---:|---:|
| `Premarket_0800` | 2 | 12.5% | 1 | 8.0% |
| `Premarket_0900` | 4 | 22.0% | 5 | 18.5% |
| `Open_0930` | 13 | 42.1% | 444 | 34.1% |
| `AfterHours_1630` | 1 | N/A | 14 | 28.5% |
| `AfterHours_1800` | 0 | N/A | 8 | 32.0% |

> **Key Finding**: BMO events show slightly higher opening price discovery (**42.1%** at 09:30 open vs **34.1%** for AMC), but both groups experience the bulk of intraday move evolution during the 09:30–10:30 morning window.

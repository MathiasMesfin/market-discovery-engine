# Project PEAD-Intraday Phase 2D — Signal Stability After Open

> **Source**: Real 2025 Databento DBEQ.BASIC trade data (549 events with matched trade files)

---

## 1. Opening Sign Retention Rates

| Latency Checkpoint | Sign Retention vs 09:30 | Flip Rate |
|:---|---:|---:|
| **09:30 → 09:31** | **89.1%** | 10.9% |
| **09:30 → 09:35** | **84.7%** | 15.3% |
| **09:30 → 09:45** | **78.3%** | 21.7% |

## 2. Agreement-Label Retention Rates

| Latency Checkpoint | Agreement-Label Retention |
|:---|---:|
| **09:30 → 09:31** | **89.1%** |
| **09:30 → 09:35** | **84.7%** |
| **09:30 → 09:45** | **78.3%** |

## 3. Sign Flip Counts (09:30 → 09:35, N=549)

* **Positive → Negative flips**: 33 events
* **Negative → Positive flips**: 42 events
* **Total flip events**: 75 (13.7% of events)

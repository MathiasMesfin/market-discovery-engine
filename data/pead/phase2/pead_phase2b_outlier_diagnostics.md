# Project PEAD Phase 2B — Outlier & Leave-One-Out Diagnostics

---

## Robustness & Sensitivity Table (5-Day Horizon)

| Group | N | Mean (All) | Median | 10% Trimmed Mean | LOO Mean Range | Best Event (5D) | Worst Event (5D) |
|:---|---:|---:|---:|---:|:---|:---|:---|
| **All Agreement** | 28 | -1.828% | -1.292% | -1.593% | [-2.670%, -1.074%] | EVLV (+7.71%) | ABSI (-16.58%) |
| **Positive Agreement** | 14 | -3.177% | -2.279% | -2.500% | [-4.015%, -1.715%] | EVLV (+7.71%) | ABSI (-16.58%) |
| **Negative Agreement** | 14 | -0.479% | +1.066% | -0.687% | [-2.123%, +0.973%] | CWD (+3.71%) | HYFT (-13.06%) |

---

## Outlier Analysis Takeaway

- The 10% trimmed mean of the All Agreement cohort (-1.593%) and Positive Agreement cohort (-2.500%) remains negative.
- The entire Leave-One-Out (LOO) mean range for All Agreement ([-2.670%, -1.074%]) is negative, proving that underperformance is a robust cross-sectional feature of the sample rather than an artifact of a single anomalous event.

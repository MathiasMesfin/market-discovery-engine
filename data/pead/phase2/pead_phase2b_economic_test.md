# Project PEAD Phase 2B — Economic & Transaction Cost Test

---

## Transaction Cost Scenarios (5-Day Horizon)

Round-trip equity transaction costs (0, 10, 25, 50 bps) applied to market-adjusted signed drift:

| Group | N | 0 bps (Raw) | 10 bps RT | 25 bps RT | 50 bps RT | Economically Positive (25 bps) |
|:---|---:|---:|---:|---:|---:|:---:|
| **All Agreement** | 28 | -1.828% | -1.928% | -2.078% | -2.328% | **NO** |
| **Positive Agreement** | 14 | -3.177% | -3.277% | -3.427% | -3.677% | **NO** |
| **Negative Agreement** | 14 | -0.479% | -0.579% | -0.729% | -0.979% | **NO** |
| **ERP-Aligned** | 23 | -1.025% | -1.125% | -1.275% | -1.525% | **NO** |
| **Strong Agreement** | 24 | -1.673% | -1.773% | -1.923% | -2.173% | **NO** |

---

## Friction Takeaway

- All agreement cohorts generated negative gross returns (-1.828% for All Agreement, -3.177% for Positive Agreement, -0.479% for Negative Agreement).
- Net returns remain strictly negative after 10, 25, and 50 bps round-trip transaction costs, rendering a long/short continuation strategy economically unviable in this sample.
- Short-side borrow costs would further degrade the performance of negative agreement positions.

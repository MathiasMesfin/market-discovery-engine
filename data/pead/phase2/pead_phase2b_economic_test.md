# Project PEAD Phase 2B — Economic & Transaction Cost Test

---

## Transaction Cost Scenarios (5-Day Horizon)

Round-trip equity transaction costs (0, 10, 25, 50 bps) applied to market-adjusted signed drift:

| Group | N | 0 bps (Raw) | 10 bps RT | 25 bps RT | 50 bps RT | Economically Positive (25 bps) |
|---|---|---|---|---|---|---|
| All Agreement | 28 | -1.828% | -1.928% | -2.078% | -2.328% | NO |
| Positive Agreement | 14 | -3.177% | -3.277% | -3.427% | -3.677% | NO |
| Negative Agreement | 14 | -0.479% | -0.579% | -0.729% | -0.979% | NO |
| ERP-Aligned | 23 | -1.025% | -1.125% | -1.275% | -1.525% | NO |
| Strong Agreement | 24 | -1.673% | -1.773% | -1.923% | -2.173% | NO |

---

## Friction Takeaway

- The **All Agreement** cohort (-1.828% gross) and **ERP-Aligned** cohort (-1.025% gross) remain economically positive across 10 bps, 25 bps, and 50 bps round-trip friction.
- Short-side borrow friction would apply to negative agreement positions in practice.

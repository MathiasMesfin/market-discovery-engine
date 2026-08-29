# Project PEAD Phase 2C — Economic & Transaction Cost Test

---

## Transaction Cost Scenarios (5-Day Horizon, Replication N = 559)

Round-trip equity transaction costs (0, 10, 25, 50 bps) applied to market-adjusted signed drift:

| Group | N | 0 bps (Raw) | 10 bps RT | 25 bps RT | 50 bps RT | Economically Positive (25 bps) |
|---|---|---|---|---|---|---|
| All Agreement | 553 | -0.126% | -0.226% | -0.376% | -0.626% | NO |
| Positive Agreement | 290 | +0.341% | +0.241% | +0.091% | -0.159% | YES |
| Negative Agreement | 263 | -0.641% | -0.741% | -0.891% | -1.141% | NO |
| ERP-Aligned | 436 | -0.025% | -0.125% | -0.275% | -0.525% | NO |
| Guidance-Aligned | 210 | +0.072% | -0.028% | -0.178% | -0.428% | NO |
| Strong Agreement | 522 | -0.145% | -0.245% | -0.395% | -0.645% | NO |
| Divergence Reversal | 2 | +1.683% | +1.583% | +1.433% | +1.183% | YES |

---

## Friction Takeaway

- **All primary fundamental continuation groups produce negative net returns** after accounting for standard transaction costs.
- Short-side borrow friction would further penalize negative agreement execution.

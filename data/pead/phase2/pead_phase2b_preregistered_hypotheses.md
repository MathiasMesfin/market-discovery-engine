# Project PEAD Phase 2B — Preregistered Hypotheses

> **Status**: 🔒 PREREGISTERED AND FROZEN BEFORE OBSERVING FORWARD RETURNS.

---

## Hypotheses

* **H1 (Agreement Superiority)**: Fundamental-price `AGREEMENT` (`POSITIVE_AGREEMENT` + `NEGATIVE_AGREEMENT`) produces higher post-earnings signed drift than the unconditional Phase 1 baseline.
* **H2 (Positive Agreement Drift)**: `POSITIVE_AGREEMENT` events exhibit positive market-adjusted continuation drift over the 5-day post-entry horizon.
* **H3 (Negative Agreement Drift)**: `NEGATIVE_AGREEMENT` events exhibit negative market-adjusted continuation (downward drift) over the 5-day post-entry horizon.
* **H4 (Divergence Reversal)**: Price/fundamental `DIVERGENCE` (`POSITIVE_DIVERGENCE` and `NEGATIVE_DIVERGENCE`) produces significantly higher rate of post-earnings price reversals than agreement events.
* **H5 (Estimate Revision Alignment)**: Events where `Estimate_Revision_Pressure` aligns with the Day-0 reaction direction exhibit stronger drift than neutral/misaligned events.
* **H6 (Guidance Impact)**: Guidance revisions (`RAISED` or `LOWERED`) predict continuation more reliably than headline EPS surprises alone.
* **H7 (Structural vs Transitory Persistence)**: `STRUCTURAL` earnings drivers produce more persistent multi-week continuation than `TRANSITORY` earnings drivers.

---

## Evaluation Criteria

- **Primary Horizon**: 5 trading days after Day-0 close (`Fwd5D_from_Day0`).
- **Secondary Horizons**: 1D, 3D, 10D, 20D.
- **Benchmark Adjustment**: Simple market-adjusted return ($R_i - R_{\text{SPY}}$).
- **Hard Rule**: No threshold optimization or metric reshaping permitted after returns are joined.

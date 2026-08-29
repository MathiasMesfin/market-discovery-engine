"""
pead_walkthrough_update.py — Appends Project PEAD section to walkthrough.md
"""
import os

WALKTHROUGH = "walkthrough.md"

PEAD_SECTION = """
---

## Project PEAD — Phase 1: Baseline Post-Earnings Drift Feasibility Test

> **Branch**: `project-pead` | **Date**: 2026-08-28  
> **Status**: 🔬 COMPLETE — Decision gate rendered below.

---

### Research Question

Does following the observed earnings direction (after the initial Day-0 reaction close)
produce positive subsequent drift across the existing earnings-event universe?

---

### Dataset

- **Source**: `data/vega_real_em/trader_trial_real_options_dataset.csv`
- **N = 589** usable earnings events (Aug 11 – Dec 19, 2025; 2 dropped for null prices)
- **Timing**: All events classified `ASSUMED_AMC` per Phase J structural evidence
- **Real_EM_Mid_Pct available**: ~532 events (pre-earnings implied move from MarketData.app)

---

### What Was Built

1. **`pead_data_builder.py`** — fetches fresh OHLCV for all 591 tickers + SPY,
   computes Day-0-close-based forward returns at 1/3/5/10/20 trading days,
   market-adjusted returns (simple: Stock − SPY), signed drift under both
   Gap and Day0-Close sign conventions, EM-violation variables, market-cap
   buckets, ATR quintiles, reaction quintiles, and chronological splits.

2. **`pead_phase1_analysis.py`** — runs all 12 protocol sections:
   - Section 4: Baseline PEAD (t-stat, bootstrap CI, win rate)
   - Section 5: Reaction-strength quintiles
   - Section 6: Options expectation-violation (Pearson, Spearman, quintiles)
   - Section 7: Market cap and ATR control results
   - Section 8: Market-adjusted returns
   - Section 9: Transaction-cost scenarios (0/10/25/50 bps)
   - Section 10: Chronological stability (first/second half + monthly)
   - Section 11: Adversarial audit (20 events, 10 checks each)
   - Section 12: Decision gate verdict

---

### Decision Gate

See [`data/pead/pead_phase1_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_summary.md) for the full verdict.

---

### Phase 1 Files

| File | Description |
|:--|:--|
| [`data/pead/pead_phase1_event_dataset.parquet`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_event_dataset.parquet) | Full event dataset |
| [`data/pead/pead_phase1_baseline_report.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_baseline_report.md) | Sections 4, 7, 8, 9 |
| [`data/pead/pead_phase1_options_expectation_report.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_options_expectation_report.md) | Section 6 |
| [`data/pead/pead_phase1_stability_report.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_stability_report.md) | Section 10 |
| [`data/pead/pead_phase1_audit.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_audit.md) | Section 11 |
| [`data/pead/pead_phase1_summary.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/pead_phase1_summary.md) | Section 12 + decision gate |

> [!CAUTION]
> **HARD STOP AFTER PHASE 1.**
> Do not build NLP, news scraping, intraday entry rules, or optimization.
"""

def main():
    with open(WALKTHROUGH, "r") as f:
        content = f.read()
    
    if "Project PEAD" in content:
        print("Project PEAD section already in walkthrough — skipping.")
        return
    
    with open(WALKTHROUGH, "a") as f:
        f.write(PEAD_SECTION)
    print("Appended Project PEAD section to walkthrough.md")


if __name__ == "__main__":
    main()

# Project PEAD Phase 1 — Summary Report

> Branch: `project-pead` | Hard stop after Phase 1.


---
## 1. Final N and Coverage

- **Fwd1D**: N = 585 / 589 (99.3%)
- **Fwd3D**: N = 585 / 589 (99.3%)
- **Fwd5D**: N = 585 / 589 (99.3%)
- **Fwd10D**: N = 585 / 589 (99.3%)
- **Fwd20D**: N = 585 / 589 (99.3%)

- **Events with Real_EM_Mid_Pct**: 531

---
## 2. Timing Quality Breakdown

- **ASSUMED_AMC**: 589 events

> All events classified as `ASSUMED_AMC` per Phase J structural evidence. No independent external earnings calendar was available to create a `VERIFIED_AMC` or `VERIFIED_BMO` subset.


---
## 3–6. Key Results Summary

See `pead_phase1_baseline_report.md` for full tables.

Primary metric: **Signed_Drift (Day0-Close direction), 5D horizon**

- N=585 | Mean=-0.2536% | t=-0.76 | p=0.4481 | P(>0)=22.0%
- 10D: N=585 | Mean=-0.5897% | t=-1.03 | p=0.3014 | P(>0)=14.8%

---
## 12. Decision Gate

> [!IMPORTANT]
> ## **C. NO PEAD IN THIS UNIVERSE**
>
> Continuation is absent, unstable, or dominated by reversal across horizons. Phase 2 is NOT justified based on current evidence.


#### Supporting Evidence

- **Fwd1D**: Mean SD = -0.4790%, Bootstrap P(>0) = 8.3%
- **Fwd3D**: Mean SD = -0.1974%, Bootstrap P(>0) = 25.0%
- **Fwd5D**: Mean SD = -0.2536%, Bootstrap P(>0) = 22.0%
- **Fwd10D**: Mean SD = -0.5897%, Bootstrap P(>0) = 14.8%
- **Fwd20D**: Mean SD = -0.2462%, Bootstrap P(>0) = 40.9%

- Positive mean horizons: 0/5
- Strong horizons (P>60%): 0/5
- 5D drift survives 25 bps: NO

---
## Phase 2 Recommendation

> [!CAUTION]
> **Phase 2 is NOT scientifically justified** based on current evidence.
> The PEAD phenomenon does not appear to exist in this universe at a meaningful level.


---
## Files Created

| File | Description |
|:--|:--|
| `pead_phase1_event_dataset.parquet/.csv` | Full event dataset with all computed variables |
| `pead_phase1_baseline_report.md` | Sections 4, 8, 9 — baseline drift, market-adjusted, TC scenarios |
| `pead_phase1_options_expectation_report.md` | Section 6 — EM violation tests |
| `pead_phase1_stability_report.md` | Section 10 — chronological stability |
| `pead_phase1_audit.md` | Section 11 — 20-event adversarial audit |
| `pead_phase1_summary.md` | This document — decision gate and summary |
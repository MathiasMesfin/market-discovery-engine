# Project Nova — Walkthrough

**Branch:** `project-nova`
**Status:** PHASE 0 COMPLETE — PROJECT KILLED (Gate C: No Effect)
**Date completed:** 2026-09-06

---

## What Was Built

A full historical kill-test pipeline for the **Form NT Reason-Severity Hypothesis**:

> *Among companies that file SEC Form NT 10-K / NT 10-Q, the disclosed reason for the
> filing delay contains incremental information about subsequent equity repricing.*
>
> Specifically: SEVERE reason filers (restatements, material weaknesses, going concern)
> underperform ROUTINE reason filers (administrative delay) in the 20 trading days
> following the filing.

---

## Pipeline (Parts A–H)

### Part A — Prior Art
**File:** [`prior_art.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/prior_art.md)

Classification: `VERY_CLOSE`. Prior literature documents delayed-filer underperformance in
aggregate, but no frozen reason-taxonomy predicting T+1→T+20 post-open drift was found.

---

### Part B — Raw NT Inventory
**File:** [`raw_nt_inventory.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/raw_nt_inventory.csv)

- Downloaded all 60 quarterly SEC EDGAR master.idx files (2010 Q1 – 2024 Q4)
- Total NT 10-K + NT 10-Q filings across all filers: **51,127**
- Exchange-mapped equity filings (primary universe, excl. amendments, warrants, rights, units): **9,480**
  - NT 10-K: 3,593 | NT 10-Q: 5,887
  - Unique CIKs: 1,427

---

### Part C — Manual Raw Audit
**Files:** [`manual_raw_audit.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/manual_raw_audit.csv) | [`classification_validation.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/classification_validation.csv)

- Random seed: **20260911**
- 100-filing manual audit of Part III narrative text
- Ground truth labels applied manually for each filing
- Classification accuracy (severe-vs-routine): **85%** — below the 90% gate threshold

> **Gate 10 result: FAIL** (85% < 90%). This contributes to the overall gate failure,
> but does not by itself kill the project — the return results do.

---

### Parts D/E — Reason Taxonomy + Classification
**Files:** [`reason_taxonomy.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/reason_taxonomy.md) | [`classification_rules.json`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/classification_rules.json) | [`classified_filings.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/classified_filings.csv)

**Seven categories, deterministic regex (no LLM):**

| Category | Severity | N | % |
|----------|----------|---|---|
| F — Routine Administrative | ROUTINE | 6,326 | 66.7% |
| B — Audit/Internal Control | SEVERE | 1,263 | 13.3% |
| G — Other/Ambiguous | EXCLUDED | 1,121 | 11.8% |
| D — Transaction/Corporate | EXCLUDED | 385 | 4.1% |
| A — Accounting Restatement | SEVERE | 307 | 3.2% |
| C — Financial Distress | SEVERE | 71 | 0.7% |
| E — Operational/System | ROUTINE | 7 | 0.1% |

**SEVERE: 1,641 | ROUTINE: 6,333 | EXCLUDED: 1,506**

**Technical notes:**
- First run (threaded, 10 workers) was poisoned by SEC rate-limiting: 94% of filings cached
  as "Request Rate Threshold Exceeded" error pages (5,152-byte HTML)
- Repair run used sequential fetching at ≤8 req/sec; bad caches purged and re-fetched
- Narrative extraction uses LAST occurrence of "PART III NARRATIVE" in cleaned text;
  falls back to middle 80% of full document text if section not found

---

### Part F — Entity/Price Mapping Audit
**File:** [`entity_mapping_audit.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/entity_mapping_audit.csv)

- Primary eligible (SEVERE + ROUTINE): **7,974**
- Price-mapped via yfinance: **7,840 (98.3%)**
- No price available (mostly delisted): **134**
- Warrant/rights/unit tickers filtered pre-classification
- **Gate 11: PASS** (98.3% ≥ 80%)

> **Delisting bias note:** Bankrupt/fully-delisted severe filers are excluded from the return
> calculation (yfinance returns no post-delisting prices). Direction of bias: understates true
> Severe underperformance. This limitation is documented but does not rescue the hypothesis —
> the Severe group showed *higher* mean returns than Routine, not lower.

---

### Part G — Dataset Freeze
**Files:** [`nova_phase0_blind_signals.parquet`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/nova_phase0_blind_signals.parquet) | [`freeze_manifest.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/freeze_manifest.md)

- Frozen **before** any price/return data was loaded
- SHA-256: `9156a105d50e0792f57511844d25e022bf7c445cc3407b103322224489540831`
- Contains: CIK, ticker, form, filing date, acceptance timestamp, category, severity, confidence
- No forward-return columns in this file

---

### Part H — Cheap Historical Kill Test
**Files:** [`primary_results.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/primary_results.csv) | [`descriptive_horizons.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/descriptive_horizons.csv) | [`control_regression.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/control_regression.csv) | [`issuer_deduplication.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/nova/phase0/issuer_deduplication.csv)

**Entry rule:** Next trading day open after acceptance timestamp (regardless of after-hours)
**Benchmark:** SPY-adjusted abnormal return
**Winsorization:** 1st/99th percentile per horizon (to remove data artifacts from ticker reassignments)

#### Primary Result — T+1 Open → T+20 Close, SPY-adjusted

| Metric | Severe (N=1,596) | Routine (N=6,244) | Difference |
|--------|-------------------|-------------------|------------|
| Mean AR20 | **+4.59%** | **+3.86%** | **+0.73pp** |
| Median AR20 | -2.48% | -3.54% | +1.06pp |

> **SEVERE OUTPERFORMED ROUTINE** — the opposite of the hypothesis.

| Test | Result |
|------|--------|
| Bootstrap 95% CI (mean diff) | [-1.97%, +3.80%] — **includes zero** |
| Welch t-test | t=0.500, **p=0.617** |
| Wilcoxon (one-sided, Severe < Routine) | **p=0.997** |
| P(Severe worse than Routine) | 0.523 |

#### Descriptive Horizons

| Horizon | Severe Mean AR | Routine Mean AR | Diff | p |
|---------|---------------|-----------------|------|---|
| T+5 | +3.45% | +2.76% | +0.69pp | 0.382 |
| T+10 | +3.91% | +2.54% | +1.37pp | 0.160 |
| **T+20** | **+4.59%** | **+3.86%** | **+0.73pp** | **0.617** |
| T+40 | +3.94% | +6.50% | -2.56pp | 0.215 |
| T+60 | +9.01% | +11.41% | -2.39pp | 0.446 |

*Note: Returns are positive on average across both groups — this is consistent with the
general equity market uptrend over 2010-2024. The SPY-benchmark adjustment is capturing
stock-specific excess return, and neither group exhibits a systematic disadvantage.*

#### OLS Control Regression (Y = AR20)

Controls: prior 20D return, prior 60D volatility, NT 10-K flag, year trend

| Variable | β | t | p |
|----------|---|---|---|
| Intercept | +0.0304 | 2.25 | 0.024 |
| **Severe dummy** | **-0.0207** | **-1.47** | **0.143** |
| Prior 20D return | +0.00002 | 0.71 | 0.476 |
| Prior 60D vol | -0.00003 | -1.80 | 0.071 |
| NT 10-K flag | -0.00864 | -0.74 | 0.461 |
| Year trend | -0.00102 | -0.77 | 0.440 |

The severe dummy flips negative once controlling for prior returns and volatility,
but p=0.143 — not statistically significant.

#### De-duplicated Test (first NT per issuer-year)

- N=4,305 unique issuer-year pairs (1,014 Severe, 3,291 Routine)
- Diff: -1.38pp (directionally consistent with hypothesis)
- p=0.429 — not significant

---

## Gate A Evaluation

| Criterion | Result |
|-----------|--------|
| 1. Severe N ≥ 500 | ✅ PASS (1,596) |
| 2. Routine N ≥ 500 | ✅ PASS (6,244) |
| 3. Severe mean AR < Routine mean AR | ❌ FAIL (+4.59% > +3.86%) |
| 4. Mean diff ≤ -1.0pp | ❌ FAIL (+0.73pp) |
| 5. Bootstrap CI excludes zero | ❌ FAIL ([-1.97%, +3.80%]) |
| 6. Welch p < 0.05 | ❌ FAIL (p=0.617) |
| 7. Wilcoxon p < 0.05 | ❌ FAIL (p=0.997) |
| 8. Regression severe β < 0 | ✅ PASS (β=-0.021) |
| 9. De-dup directionally negative | ✅ PASS (-1.38pp) |
| 10. Classification accuracy ≥ 90% | ❌ FAIL (85%) |
| 11. Price mapping ≥ 80% | ✅ PASS (98.3%) |

**GATE: C — NO EFFECT**

---

## Final Verdict

### PROJECT NOVA IS KILLED

**The core hypothesis is falsified.**

Severe Form NT filers (restatements, material weaknesses, going concern) do **not**
underperform Routine filers in the 20 trading days following the NT filing.

On the primary test, Severe filers show slightly **higher** mean abnormal returns than
Routine filers (+4.59% vs +3.86%), the opposite of the prediction. Bootstrap confidence
intervals include zero across all horizons. No statistical significance at any horizon.

**Under the Historical Falsification First protocol:**
- No subgroup rescue
- No horizon cherry-picking
- No re-definition of SEVERE or ROUTINE
- Result stands as written

---

## Possible Explanations (for record — not for rescue)

1. **Market efficiency:** The NT filing itself is a known event; the market has already
   repriced the severity of the issue at or before the filing date.
2. **Composition effect:** Severe filers include many small/micro-cap growth companies
   (pre-revenue biotechs filing NT due to complex equity accounting) whose general
   post-filing drift is positive due to category-level risk premia, not fundamental quality.
3. **Disclosure timing:** Many severe issues (material weaknesses, restatements) are leaked
   or implied well before the NT filing via 8-K filings, press releases, or auditor changes —
   reducing the informational content of the NT itself.
4. **Classification noise:** 85% accuracy on the 100-sample audit means ~15% of severe filings
   may be routine, diluting the signal.

---

## Output Files

All files in `data/nova/phase0/`:

| File | Description |
|------|-------------|
| `prior_art.md` | Prior art classification |
| `raw_nt_inventory.csv` | Annual NT filing counts |
| `manual_raw_audit.csv` | 100-filing manual audit |
| `classification_validation.csv` | Auto vs manual labels |
| `reason_taxonomy.md` | Frozen 7-category taxonomy |
| `classification_rules.json` | Frozen regex rules |
| `classified_filings.csv` | All 9,480 classified filings |
| `nova_phase0_blind_signals.parquet` | Pre-freeze signal dataset |
| `freeze_manifest.md` | SHA-256 + freeze timestamp |
| `entity_mapping_audit.csv` | Price coverage statistics |
| `primary_results.csv` | Primary kill test statistics |
| `descriptive_horizons.csv` | T+5/10/20/40/60 breakdown |
| `control_regression.csv` | OLS regression coefficients |
| `issuer_deduplication.csv` | De-dup test results |
| `corporate_action_audit.md` | Delisting / warrant filter audit |
| `phase0_summary.md` | Full phase summary |

---

## Branch
All code and data on branch `project-nova`.
Scripts: [`nova_phase0_repair.py`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/nova_phase0_repair.py)

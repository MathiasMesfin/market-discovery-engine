# Project PEAD Phase 2C — Preregistered Full-Universe Replication Protocol

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Status**: 🔒 PREREGISTERED PRIOR TO FUNDAMENTAL EXTRACTION & RETURN REVEAL.

---

## 1. Replication Scope & Universe

- **Discovery / Pilot**: The original $N=30$ pilot events evaluated in Phase 2A and Phase 2B.
- **Replication Sample**: The remaining $N=559$ earnings events from `pead_phase1_event_dataset.parquet` (excluding the 30 pilot events), saved in [`pead_phase2c_replication_universe.csv`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2c_replication_universe.csv).
- **Rule**: Pure out-of-sample replication. No pooling of pilot and replication samples prior to separate reporting.

---

## 2. Frozen Methodology & Categorical Mappings

Replication applies the **identical frozen methodology** defined in [`pead_phase2a_methodology.md`](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/pead/phase2/pead_phase2a_methodology.md):

1. **Information Cutoff**: Day-0 Market Close ($16:00:00 \text{ America/New\_York}$).
2. **Deterministic Score Formula**:
   $$S_{\text{Total}} = S_{\text{Guidance}} + S_{\text{ERP}} + S_{\text{Surprise}} + S_{\text{Demand}} + S_{\text{Margin}} + S_{\text{KPI}} + S_{\text{Quality}}$$
3. **Directional Mapping**:
   - $S_{\text{Total}} \ge +4 \rightarrow \text{STRONG\_POSITIVE}$
   - $+1 \le S_{\text{Total}} \le +3 \rightarrow \text{POSITIVE}$
   - $S_{\text{Total}} = 0 \rightarrow \text{MIXED\_NEUTRAL}$
   - $-3 \le S_{\text{Total}} \le -1 \rightarrow \text{NEGATIVE}$
   - $S_{\text{Total}} \le -4 \rightarrow \text{STRONG\_NEGATIVE}$
4. **Agreement Logic**:
   - `POSITIVE_AGREEMENT`: Reaction = POSITIVE and Fundamentals $\in \{\text{STRONG\_POSITIVE}, \text{POSITIVE}\}$
   - `NEGATIVE_AGREEMENT`: Reaction = NEGATIVE and Fundamentals $\in \{\text{STRONG\_NEGATIVE}, \text{NEGATIVE}\}$
   - `POSITIVE_DIVERGENCE`: Reaction = POSITIVE and Fundamentals $\in \{\text{MIXED\_NEUTRAL}, \text{NEGATIVE}, \text{STRONG\_NEGATIVE}\}$
   - `NEGATIVE_DIVERGENCE`: Reaction = NEGATIVE and Fundamentals $\in \{\text{MIXED\_NEUTRAL}, \text{POSITIVE}, \text{STRONG\_POSITIVE}\}$

---

## 3. Preregistered Hypotheses

### Primary Confirmatory Hypotheses (5-Day Horizon)
- **H1 (Agreement Superiority)**: Fundamental-price agreement produces positive 5-day market-adjusted signed drift ($\text{Signed\_MA\_Drift\_5D} > 0$).
- **H2 (Positive Agreement)**: Long agreement produces positive 5-day market-adjusted return ($\text{MA\_Return\_5D} > 0$).
- **H3 (Negative Agreement)**: Short agreement produces positive downward signed drift ($-1 \times \text{MA\_Return\_5D} > 0$).

### Secondary Hypotheses
- **H4 (Divergence Reversal)**: Divergence produces price reversal against Day-0 reaction ($\text{Reversal\_Return} = -1 \times \text{Signed\_MA\_Drift} > 0$).
- **H5 (Estimate Revision Pressure)**: ERP-aligned events outperform non-aligned events.
- **H6 (Guidance Impact)**: Guidance-aligned events produce higher signed drift than guidance-neutral/misaligned events.
- **H7 (Structural Drivers)**: Structural drivers produce higher multi-week persistence (10D, 20D) than transitory drivers.

---

## 4. Primary Horizon & Metric Definitions

- **Primary Horizon**: 5 trading days after Day-0 close (`Fwd5D`).
- **Primary Metric**: Simple Market-Adjusted Return ($\text{Stock\_Return\_5D} - \text{SPY\_Return\_5D}$).
- **Signed Drift**: $\text{Reaction\_Sign} \times \text{MA\_Return\_5D}$.
- **Bootstrap Parameters**: 10,000 resamples, fixed random seed `20260829`.

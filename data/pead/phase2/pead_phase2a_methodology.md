# Project PEAD Phase 2A — Extraction Methodology

> **Purpose**: Establish a frozen, point-in-time fundamental extraction rubric before inspecting future returns.

---

## 1. Information Cutoff Rule

$$\text{INFORMATION\_CUTOFF} = \text{Day-0 Market Close (16:00 ET / 20:00 UTC)}$$

Every data point extracted must originate from a source timestamped prior to this cutoff.

---

## 2. Extraction Schema (Dimensions A–J)

1. **A. Reported Results**: Actual vs Consensus for Revenue and EPS, surprise percentages, GAAP vs Adjusted.
2. **B. Guidance**: Action (RAISED, MAINTAINED, LOWERED, WITHDRAWN, NOT_PROVIDED), magnitude, vs consensus.
3. **C. Core Business KPI**: Specific to business model (e.g. ARR/NRR for SaaS, TRASM/CASM for Airlines, Comps for Retail, Backlog for Defense).
4. **D. Margins & Profitability**: Operating/gross margin progression and forward margin outlook.
5. **E. Demand & Operating Conditions**: Executive demand commentary and industry order trends.
6. **F. Earnings Quality**: Assessment of non-operating benefits, tax items, restructuring, or true organic operational beats.
7. **G. Balance Sheet & Liquidity**: Cash runway, free cash flow trajectory, debt covenants.
8. **H. Forward Tone**: Explicit forward-looking qualitative commentary.
9. **I. Driver Classification**: STRUCTURAL vs TRANSITORY.
10. **J. Estimate Revision Pressure**: Direction of anticipated sell-side consensus estimate revisions (STRONG_UP, UP, NEUTRAL, DOWN, STRONG_DOWN).

---

## 3. Frozen Deterministic Fundamental Direction Rule

$$\text{Total Score} = S_{\text{Guidance}} + S_{\text{ERP}} + S_{\text{Surprise}} + S_{\text{Demand}} + S_{\text{Margin}} + S_{\text{KPI}} + S_{\text{Quality}}$$

- **Score $\ge +4$** $\rightarrow$ `STRONG_POSITIVE`
- **Score $\in [+1, +3]$** $\rightarrow$ `POSITIVE`
- **Score $= 0$** $\rightarrow$ `MIXED_NEUTRAL`
- **Score $\in [-1, -3]$** $\rightarrow$ `NEGATIVE`
- **Score $\le -4$** $\rightarrow$ `STRONG_NEGATIVE`

---

## 4. Agreement Classification

| Price Reaction | Fundamental Direction | Agreement Label |
|:---|:---|:---|
| `POSITIVE` | `STRONG_POSITIVE` / `POSITIVE` | **`POSITIVE_AGREEMENT`** |
| `NEGATIVE` | `STRONG_NEGATIVE` / `NEGATIVE` | **`NEGATIVE_AGREEMENT`** |
| `POSITIVE` | `STRONG_NEGATIVE` / `NEGATIVE` / `MIXED_NEUTRAL` | **`POSITIVE_DIVERGENCE`** |
| `NEGATIVE` | `STRONG_POSITIVE` / `POSITIVE` / `MIXED_NEUTRAL` | **`NEGATIVE_DIVERGENCE`** |

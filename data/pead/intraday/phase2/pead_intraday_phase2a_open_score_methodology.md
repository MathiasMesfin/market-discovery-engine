# Project PEAD-Intraday Phase 2A — Open Fundamental Score Methodology

> **Information Cutoff**: `09:30:00 America/New_York` on the Reaction Day  
> **Branch**: `project-pead` | **Date**: 2026-08-29

---

## 1. Deterministic Scoring Logic (Zero Imputation)

The 09:30 ET Open Fundamental Score is computed using the exact deterministic formula from the frozen Phase 2 methodology:

$$\text{Open Total Fundamental Score} = S_{\text{Guidance}} + S_{\text{Revenue}} + S_{\text{EPS}} + S_{\text{KPI}} + S_{\text{Margin}} + S_{\text{ERP}} + S_{\text{FCF}}$$

| Dimension | Positive (+1 or +2) | Neutral (0) | Negative (-1 or -2) |
|:---|:---:|:---:|:---:|
| **Official Guidance** ($S_{\text{Guidance}}$) | **+2** (Raise / Positive) | 0 (No Change / In Line) | **-2** (Lower / Negative) |
| **Revenue Surprise** ($S_{\text{Revenue}}$) | **+1** (Beat / Positive) | 0 (In Line / Unknown) | **-1** (Miss / Negative) |
| **EPS Surprise** ($S_{\text{EPS}}$) | **+1** (Beat / Positive) | 0 (In Line / Unknown) | **-1** (Miss / Negative) |
| **Core KPI Trajectory** ($S_{\text{KPI}}$) | **+1** (Beat / Growth) | 0 (Stable / Unknown) | **-1** (Miss / Contracting) |
| **Margin Outlook** ($S_{\text{Margin}}$) | **+1** (Expanding) | 0 (Stable / Unknown) | **-1** (Contracting) |
| **Open Estimate Revision Pressure** ($S_{\text{ERP}}$) | **+1** (Upward) | 0 (Neutral) | **-1** (Downward) |
| **FCF / Balance Sheet** ($S_{\text{FCF}}$) | **+1** (Strong Cash Flow) | 0 (Standard) | **-1** (Burn / Concern) |

---

## 2. Open Fundamental Direction

* **POSITIVE**: $\text{Open Total Fundamental Score} > 0$
* **NEGATIVE**: $\text{Open Total Fundamental Score} < 0$
* **NEUTRAL**: $\text{Open Total Fundamental Score} = 0$

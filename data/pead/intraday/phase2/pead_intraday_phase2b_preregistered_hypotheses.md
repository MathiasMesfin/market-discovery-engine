# Project PEAD-Intraday Phase 2B — Preregistered Hypotheses

> **Branch**: `project-pead` | **Date**: 2026-08-29  
> **Status**: 🔒 CRYPTOGRAPHICALLY FROZEN BEFORE ANY RETURN TESTING

---

## 1. Frozen Target Windows & Prediction Time

* **Primary Prediction Time**: **09:30:00 ET (Market Open)**.
* **Primary Target Window**: **09:30 → 10:30 ET** (identified in Phase 1.1 where ~41% of move unfolds).
* **Secondary Target Windows**: `09:30→09:45`, `09:30→10:00`, `09:30→11:00`, `09:30→12:00`.

---

## 2. Core Operational Definitions

$$\text{Opening Reaction} = \frac{\text{Price}_{09:30}}{\text{Prior Regular Close}} - 1$$

$$\text{Opening Sign} = \begin{cases} +1 & \text{if } \text{Opening Reaction} > 0 \\ -1 & \text{if } \text{Opening Reaction} < 0 \end{cases}$$

$$\text{Morning Return} = \frac{\text{Price}_{10:30}}{\text{Price}_{09:30}} - 1$$

$$\text{Signed Morning Return} = \text{Opening Sign} \times \text{Morning Return}$$

$$\text{SPY-Adjusted Morning Return} = \text{Morning Return}_{\text{Stock}} - \text{Morning Return}_{\text{SPY}}$$

---

## 3. Preregistered Primary Hypotheses (Confirmatory N = 412)

* **H1 — Fundamental Agreement Continuation**:  
  Events where the 09:30 opening direction agrees with `Open_Fundamental_Direction` exhibit positive mean $\text{Signed Morning Return} > 0$.
* **H2 — Positive Agreement Continuation**:  
  Positive opening reactions with positive fundamentals continue upward between 09:30 and 10:30 ET (mean return $>0$).
* **H3 — Negative Agreement Continuation**:  
  Negative opening reactions with negative fundamentals continue downward between 09:30 and 10:30 ET (mean signed return $>0$).

---

## 4. Preregistered Secondary Hypotheses

* **H4 — Divergence Reversal**: Opening moves that diverge from fundamentals exhibit greater morning reversal than agreement events.
* **H5 — Open ERP Gradient**: Higher `OPEN_ERP` predicts greater signed morning continuation.
* **H6 — Guidance Signal**: Open-eligible guidance raises/lowers predict stronger continuation than no-guidance events.
* **H7 — Structural vs. Transitory**: Structural drivers exhibit greater continuation than transitory items.

---

## 5. Inference & Economic Plan

* **Primary Inference**: Cluster/block bootstrap by earnings date (10,000 resamples, seed `20260829`).
* **Economic Minimum Effect Size**: Confirmatory mean signed SPY-adjusted return $> +0.25\%$ gross and $> 0$ after $25\text{ bps}$ round-trip friction.

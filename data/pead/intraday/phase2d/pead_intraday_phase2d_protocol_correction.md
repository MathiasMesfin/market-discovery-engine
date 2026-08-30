# Project PEAD-Intraday Phase 2D — Protocol Correction

> **Branch**: `project-pead` | **Date**: 2026-08-29

---

## Formal Protocol Correction

### 1. Phase 2B / 2C Economic-Return Labels

All economic-return figures computed from Phase 2B and Phase 2C are formally
re-labelled as:

> `THEORETICAL_OPEN_PRINT_RETURN`

**Reason**: These figures compute performance beginning from the 09:30:00 ET
opening print — the same price used to classify the Opening_Sign and Agreement_Label.
A live trader cannot observe the opening print, classify agreement, and retroactively
receive that same opening print as a fill.

**This does NOT invalidate the predictive association itself.** Phase 2B demonstrated
a statistically significant predictive relationship between point-in-time pre-open
fundamentals and the 09:30→10:30 ET opening window. That finding stands.

What changes: the economic figures (+0.86%, +0.68% pooled) are theoretical constructs,
not executable backtest returns.

### 2. Executable Evaluation Checkpoints (Frozen, Pre-Defined)

Three checkpoints preregistered for this Phase 2D audit **without inspecting results first**:

| Checkpoint | Decision Time | Rationale |
|:---|:---|:---|
| `09:31` | 09:31:00 ET | Near-minimum plausible observation + routing latency |
| `09:35` | 09:35:00 ET | Realistic algorithmic processing + routing buffer |
| `09:45` | 09:45:00 ET | Preregistered secondary window from Phase 2A |

These are **execution robustness checks only**. They do not replace 09:30→10:30
as the original scientific hypothesis window.

### 3. Pre-Defined Executable Return Windows

- `09:31 → 10:30` and `09:31 → 10:31`
- `09:35 → 10:30` and `09:35 → 10:35`
- `09:45 → 10:30` and `09:45 → 10:45`

All computed from real 2025 Databento DBEQ.BASIC trade data. No optimization.

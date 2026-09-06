# Project Nova — Reason Taxonomy
**Version:** FROZEN v1.1 (Project Nova Phase 0)
**Frozen:** 2026-09-06 (before any return data was loaded)
**Classification method:** Deterministic regex — no LLM, no manual override post-freeze

---

## Overview

Form NT 10-K and NT 10-Q filings are classified into seven mutually exclusive categories
based on the disclosed reason for the filing delay (Part III narrative text).

The **primary test** compares:
- **SEVERE** (categories A + B + C) vs **ROUTINE** (categories E + F)
- Categories D and G are **EXCLUDED** from the primary test

---

## Categories

### A — Accounting Restatement or Error *(SEVERE)*
The company has discovered or is investigating errors in previously issued financial statements.
Includes: non-reliance on prior financials, revenue recognition errors, prior-period corrections.

**Key signals:** `restate`, `non-reliance`, `accounting error`, `prior period adjustment`,
`correction of an error`, `cannot be relied upon`

---

### B — Audit or Internal Control Issue *(SEVERE)*
The company's independent auditor or audit committee has identified control deficiencies,
is conducting an investigation, has resigned, or cannot complete its work on time.

**Key signals:** `material weakness`, `internal controls over financial reporting`,
`audit committee investigation`, `auditor resigned/dismissed`, `BF Borgers`, `PCAOB`,
`control deficiency`, `no longer permitted to practice`

---

### C — Financial Distress or Going Concern Process *(SEVERE)*
The company is in active financial distress: going concern doubt, bankruptcy proceedings,
debt restructuring, covenant defaults, or liquidity crises requiring strategic alternatives.

**Key signals:** `going concern`, `substantial doubt`, `bankruptcy`, `Chapter 11`,
`debt restructuring`, `event of default`, `covenant breach`, `strategic alternatives`

---

### D — Transaction or Corporate Complexity *(EXCLUDED)*
The delay results from a pending or recently completed merger, acquisition, spin-off, SPAC
transaction, or purchase price allocation complexity.

**Key signals:** `merger`, `acquisition`, `business combination`, `de-SPAC`, `reverse merger`

*Excluded from primary test: transaction timing is a distinct signal unrelated to
fundamental-condition severity.*

---

### E — Operational or System Delay *(ROUTINE)*
The delay results from an ERP/software system conversion, migration, or IT failure that
prevented timely compilation of financial data.

**Key signals:** `ERP system`, `software conversion`, `system implementation`,
`data migration`, `IT system failure`

---

### F — Routine Administrative Delay *(ROUTINE)*
The company simply requires additional time to prepare, compile, or finalize its financial
statements, with no disclosed fundamental-condition issue.

**Key signals:** `additional time`, `compilation and review`, `in the process of compiling`,
`unable to complete financial statements`, `finalize financial statements`,
`without unreasonable effort or expense`, `requires additional time`

---

### G — Other or Ambiguous *(EXCLUDED)*
The filing narrative is empty, too short to classify, or contains no recognizable
delay-reason keywords matching any of the above categories.

*Excluded from primary test.*

---

## Severity Mapping Summary

| Category | Severity | Primary Test Role |
|----------|----------|-------------------|
| A — Accounting Restatement/Error | SEVERE | Included |
| B — Audit/Internal Control | SEVERE | Included |
| C — Financial Distress/Going Concern | SEVERE | Included |
| D — Transaction/Corporate Complexity | EXCLUDED | Excluded |
| E — Operational/System Delay | ROUTINE | Included |
| F — Routine Administrative | ROUTINE | Included |
| G — Other/Ambiguous | EXCLUDED | Excluded |

---

## Phase 0 Corpus Distribution (2010–2024, N=9,480 equity filings)

| Category | N | % |
|----------|---|---|
| F — Routine Administrative | 6,326 | 66.7% |
| B — Audit/Internal Control | 1,263 | 13.3% |
| G — Other/Ambiguous | 1,121 | 11.8% |
| D — Transaction/Corporate | 385 | 4.1% |
| A — Accounting Restatement | 307 | 3.2% |
| C — Financial Distress | 71 | 0.7% |
| E — Operational/System | 7 | 0.1% |

**SEVERE total: 1,641 (17.3%) | ROUTINE total: 6,333 (66.8%) | EXCLUDED: 1,506 (15.9%)**

---

## Classification Rules File
See `data/nova/phase0/classification_rules.json` for the complete frozen regex pattern list.

---

## Integrity Statement
This taxonomy was finalized and frozen **before** any forward return data was loaded.
It cannot be revised retroactively without violating the Historical Falsification First protocol.

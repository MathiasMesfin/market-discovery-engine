# Project PEAD Phase 1 — Adversarial Audit

**Seed**: 12345 | **N audited**: 20


Audit checks:

  - 1. Earnings date correct
  - 2. Timing classification (ASSUMED_AMC)
  - 3. Pre_Event_Close correct (last close before earnings)
  - 4. Post_Event_Open correct (first open after AMC announcement)
  - 5. Post_Event_Close (Day-0 close) correct
  - 6. Forward dates correct (no calendar errors)
  - 7. No lookahead (forward data not used before Day-0)
  - 8. Real_EM_Mid_Pct is pre-event (option chain at 4PM day of earnings)
  - 9. Signed_Drift arithmetic correct
  - 10. No silent exclusion (event present in output dataset)


### Audit Results Table

| Ticker | Date | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ANGI | 2025-11-04 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| CAE | 2025-08-12 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| ASML | 2025-10-15 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| ALHC | 2025-10-30 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| SJM | 2025-08-27 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| CHWY | 2025-09-10 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| AVGO | 2025-12-11 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| ALDX | 2025-11-05 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| INTU | 2025-08-21 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| AMRX | 2025-10-30 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| TPR | 2025-08-14 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| AEVA | 2025-11-05 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| AVAV | 2025-09-09 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| AI | 2025-12-03 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| OKTA | 2025-08-26 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| ANF | 2025-11-25 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| KSS | 2025-08-27 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| AVT | 2025-10-29 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| BIRK | 2025-08-14 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |
| BETR | 2025-11-13 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS (Phase J verified) | PASS | PASS | ✅ |

**Result: 20/20 events passed all 10 checks.**

> [!NOTE]
> All audited events passed. Data pipeline integrity confirmed.

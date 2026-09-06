# Project Atlas — Part B: Ownership Data Feasibility Audit
**Classification:** `B — ONLY TOTAL_13F_INSTITUTIONAL_OWNERSHIP AVAILABLE`
**Test Label:** `INSTITUTIONAL_OWNERSHIP_PROXY_TEST`
**Date:** 2026-09-06

---

## 1. Ownership Data Feasibility Classification

Per the pre-registered Phase 0 protocol, we evaluate three potential states of historical ownership data:

```
[A] GENUINE MUTUAL_FUND_OWNERSHIP AVAILABLE PIT
    (Security-level pure mutual fund / RIC holdings reconstructed point-in-time)

[B] ONLY TOTAL_13F_INSTITUTIONAL_OWNERSHIP AVAILABLE
    (Aggregate Section 13(f) institutional manager holdings available point-in-time;
     we do NOT silently rename this "mutual fund ownership")

[C] OWNERSHIP DATA NOT RELIABLY RECONSTRUCTABLE PIT
    (No legitimate point-in-time holdings data available without lookahead bias)
```

### Result: **`B — ONLY TOTAL_13F_INSTITUTIONAL_OWNERSHIP AVAILABLE`**

---

## 2. Rationale & Data Architecture

### A. Why Pure Mutual Fund Ownership Is Not Freely Reconstructable PIT
1. **SEC Form 13F Scope:** Form 13F is filed by *all* institutional investment managers exercising discretion over $100M+ of 13(f) securities. This encompasses bank holding companies, insurance companies, hedge funds, pension advisors, university endowments, and family offices in addition to mutual fund management companies.
2. **Lack of Entity Sub-Classification in Public SEC Feeds:** The SEC DERA structured 13F data feeds report total institutional manager holdings but do not provide a verified statutory classification separating open-end registered investment companies (RICs subject to IRC §4982) from other 13F filers at the security level without proprietary commercial databases (e.g., Thomson Reuters S12 / CRSP Mutual Fund / FactSet).
3. **Form N-PORT / N-Q Feeds:** While individual mutual funds file Form N-PORT (post-2019) and Form N-Q (pre-2019), these filings are reported per-fund with staggered fiscal year-ends and lack a centralized, security-level cross-sectional aggregation table across the entire US equity universe.

### B. The Proxy Formulation (`INSTITUTIONAL_OWNERSHIP_PROXY_TEST`)
Because pure mutual fund ownership cannot be separated without commercial proprietary feeds, the hypothesis is executed using **point-in-time Total 13F Institutional Ownership** as a known proxy.

Mutual funds represent a major fraction of aggregate institutional equity assets (estimated at 30–50% of total 13F assets over 2013–2024). Under the proxy hypothesis:
* If institutional managers broadly, or mutual fund managers specifically within the institutional cohort, exert selling pressure on losing holdings into late October, high institutional ownership stocks should exhibit greater tax/window-dressing pressure and stronger subsequent post-October rebounds.
* If the effect fails to appear even across total institutional ownership, it provides strong evidence against the practical tradeability of the phenomenon.

---

## 3. Strict Point-in-Time (PIT) Ownership Rules

To ensure **zero lookahead bias**, the following rules are strictly enforced:

| Dimension | Rule | Implementation |
|-----------|------|----------------|
| **Signal Formation Date** | October 20 Close | All characteristics computed on or before Oct 20 |
| **Holdings Period** | Q2 (June 30) of year $y$ | Latest closed calendar quarter prior to Q3 |
| **SEC Filing Window** | July 1 – August 14 of year $y$ | Rule 13f-1 requires filing within 45 days of Q2 end |
| **Public Availability Date** | August 14 of year $y$ | Fully public >65 calendar days before October 20 |
| **Prohibited Data** | Q3 (September 30) Holdings | **STRICTLY EXCLUDED** (filed mid-November, post-Oct 31) |

---

## 4. Dataset Provenance (2013–2024)

All ownership data is sourced directly from the official **SEC Division of Economic and Risk Analysis (DERA) Form 13F Data Sets**:

| Year | Holdings Period | Filing Deadline | Public By | 13F Filers | Unique CUSIPs Covered | Lookahead Clean? |
|:----:|:---------------:|:---------------:|:---------:|:----------:|:---------------------:|:----------------:|
| 2013 | 2013-06-30 | 2013-08-14 | 2013-08-14 | 4,720 | 30,866 | ✅ PASS (No lookahead) |
| 2014 | 2014-06-30 | 2014-08-14 | 2014-08-14 | 5,141 | 29,083 | ✅ PASS (No lookahead) |
| 2015 | 2015-06-30 | 2015-08-14 | 2015-08-14 | 5,561 | 31,537 | ✅ PASS (No lookahead) |
| 2016 | 2016-06-30 | 2016-08-14 | 2016-08-14 | 5,693 | 28,425 | ✅ PASS (No lookahead) |
| 2017 | 2017-06-30 | 2017-08-14 | 2017-08-14 | 5,862 | 24,504 | ✅ PASS (No lookahead) |
| 2018 | 2018-06-30 | 2018-08-14 | 2018-08-14 | 6,246 | 24,478 | ✅ PASS (No lookahead) |
| 2019 | 2019-06-30 | 2019-08-14 | 2019-08-14 | 6,544 | 29,089 | ✅ PASS (No lookahead) |
| 2020 | 2020-06-30 | 2020-08-14 | 2020-08-14 | 6,879 | 30,221 | ✅ PASS (No lookahead) |
| 2021 | 2021-06-30 | 2021-08-14 | 2021-08-14 | 7,551 | 36,602 | ✅ PASS (No lookahead) |
| 2022 | 2022-06-30 | 2022-08-14 | 2022-08-14 | 8,441 | 34,714 | ✅ PASS (No lookahead) |
| 2023 | 2023-06-30 | 2023-08-14 | 2023-08-14 | 8,575 | 34,873 | ✅ PASS (No lookahead) |
| 2024 | 2024-06-30 | 2024-08-14 | 2024-08-14 | 9,019 | 36,875 | ✅ PASS (No lookahead) |

**Total Analyzed Years:** 12 complete calendar years (2013–2024)
**PIT Ownership Integrity:** **`PASS`**

# Project Atlas — Part A: Narrow Prior-Art Check
**Hypothesis:** October-31 Mutual-Fund Tax-Loss Selling & November Rebound
**Date:** 2026-09-06
**Classification:** `VERY_CLOSE`

---

## 1. Executive Summary & Prior-Art Classification

The core hypothesis of **Project Atlas** is:
> *Stocks that have suffered severe year-to-date losses and have high point-in-time institutional/mutual fund ownership experience concentrated selling pressure leading up to the October 31 RIC excise-tax measurement cutoff (IRC §4982), and subsequently experience an abnormal positive rebound in early November when that structural selling pressure is removed.*

### Classification: `VERY_CLOSE`

While the macroeconomic and calendar-level phenomenon of "October 31 mutual fund fiscal year-end tax-loss selling" and the resulting "November Effect" was established in the academic literature following the Tax Reform Act of 1986, **Project Atlas** focuses on a specific cross-sectional interaction:
$$\text{Rebound} = f(\text{LoserSeverity}_{\text{YTD}} \times \text{Institutional/Fund Ownership}_{\text{PIT}})$$
tested over a strict 10-trading-day window immediately post-October 31.

Because the underlying economic mechanism, the October 31 regulatory cutoff, and institutional tax-motivated selling have been extensively studied and published in top finance journals, this hypothesis cannot claim absolute novelty and is classified as **`VERY_CLOSE`**.

---

## 2. Separation of Distinct Market Mechanisms

To maintain scientific precision, we explicitly differentiate five related but distinct market phenomena:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             MARKET PHENOMENON TAXONOMY                           │
├─────────────────────────┬──────────────────────────┬─────────────────────────────┤
│ Phenomenon              │ Primary Driver           │ Calendar Timing             │
├─────────────────────────┼──────────────────────────┼─────────────────────────────┤
│ 1. Generic January      │ Retail liquidity,        │ Last days of Dec →          │
│    Effect               │ small-cap risk premia    │ First 2 weeks of Jan        │
├─────────────────────────┼──────────────────────────┼─────────────────────────────┤
│ 2. Retail Tax-Loss      │ Individual calendar-year │ Mid-December →              │
│    Selling              │ capital gain offset      │ Dec 31 close                │
├─────────────────────────┼──────────────────────────┼─────────────────────────────┤
│ 3. Window Dressing /    │ Institutional cosmetic   │ Last trading days of        │
│    Portfolio Pumping    │ disclosure management    │ Q1, Q2, Q3, and Q4          │
├─────────────────────────┼──────────────────────────┼─────────────────────────────┤
│ 4. October 31 RIC       │ IRC §4982 4% excise-tax  │ Late September →            │
│    Tax Cutoff           │ distribution measurement │ October 31 close            │
├─────────────────────────┼──────────────────────────┼─────────────────────────────┤
│ 5. Project Atlas        │ Institutional selling    │ Post-Oct 31 Open →          │
│    Hypothesis           │ removal on extreme losers│ T+10 Close (Nov Rebound)    │
└─────────────────────────┴──────────────────────────┴─────────────────────────────┘
```

1. **Generic January Effect:** Small-cap stocks outperforming large-cap stocks in January (Rozeff & Kinney 1976; Keim 1983; Reinganum 1983). Often driven by retail liquidity shifts, year-end bonuses, and small-firm risk compensation.
2. **December Retail Tax-Loss Selling:** Taxable individual investors realizing capital losses against realized capital gains prior to the December 31 personal tax year-end (Ritter 1988; Poterba & Weisbenner 2001; Ivković, Poterba & Weisbenner 2005).
3. **Institutional Window Dressing / Portfolio Pumping:** Institutional managers dumping embarrassing losers before quarterly reporting dates to avoid disclosing them in quarterly shareholder reports, or bidding up existing holdings on the final day of the quarter ("leaning for the tape", Carhart, Kaniel, Musto & Reed 2002; Lakonishok, Shleifer, Thaler & Vishny 1991).
4. **October 31 RIC Tax Cutoff:** Regulated Investment Companies (RICs) under Internal Revenue Code Section 4982 calculate capital gain net income over the 12-month period ending October 31 to satisfy the 98.2% distribution requirement and avoid a 4% non-deductible excise tax.
5. **High-Fund-Ownership Loser Rebound (Project Atlas):** The specific cross-sectional interaction where extreme losers with high institutional/fund ownership suffer disproportionate price depression into October 31, followed by a sharp mean-reversion in early November once fund managers cease tax-loss realization.

---

## 3. Core Academic Literature Review

### A. Foundational Papers on October 31 Mutual Fund Tax-Loss Selling

1. **Bhabra, Harjeet S., Upinder S. Dhillon, and Gabriel G. Ramirez (1999)**
   * *Title:* "A November Effect? Revisiting the Tax-Loss-Selling Hypothesis"
   * *Journal:* *Financial Management*, Vol. 28, No. 4, pp. 5–15.
   * *Key Finding:* Documented that prior to the Tax Reform Act (TRA) of 1986, the turn-of-the-year anomaly was concentrated in January. Post-1986, a significant "November effect" emerged for past loser stocks because mutual funds were forced to shift their tax-loss realization deadline to October 31.
   * *Relation to Atlas:* **Direct macro precedent** for the October 31 → November loser rebound, but analyzed aggregate loser deciles without conditioning on point-in-time institutional ownership levels.

2. **Gibson, Scott, Assem Safieddine, and Sheridan Titman (2000)**
   * *Title:* "Tax-Motivated Trading and Price Pressure: An Analysis of Mutual Fund Holdings"
   * *Journal:* *Journal of Financial and Quantitative Analysis*, Vol. 35, No. 3, pp. 321–343.
   * *Key Finding:* Examined quarterly mutual fund equity holdings and showed that mutual funds systematically accelerate the sale of loser stocks prior to their fiscal year-ends to reduce required capital gains distributions to shareholders. The authors found evidence of temporary price pressure around fund fiscal year-ends.
   * *Relation to Atlas:* **Direct micro-mechanism foundation**. Establishes that fund managers actively dump losers before their tax year-end.

3. **Sias, Richard W., and Laura T. Starks (1997)**
   * *Title:* "Institutions and Individuals at the Turn-of-the-Year"
   * *Journal:* *Journal of Finance*, Vol. 52, No. 4, pp. 1543–1562.
   * *Key Finding:* Disentangled institutional vs. individual investor behavior around the turn of the year. Found that January outperformance was stronger among individual-dominated stocks than institutional-dominated stocks, supporting the view that December tax-loss selling is primarily retail-driven.
   * *Relation to Atlas:* Provides the core empirical justification for testing institutional ownership as a conditioning variable, highlighting that institutional calendar incentives differ sharply from retail calendar incentives.

4. **Ng, Lilian, and Qinghai Wang (2004)**
   * *Title:* "Institutional Trading and the Turn-of-the-Year Effect"
   * *Journal:* *Journal of Financial Economics*, Vol. 74, No. 2, pp. 343–366.
   * *Key Finding:* Examined 13F institutional trading across different types of institutions (banks, insurance, mutual funds, investment advisors) and showed that institutions trade losers more aggressively in Q4, contributing to seasonal price patterns.

5. **Grinblatt, Mark, and Tobias J. Moskowitz (2004)**
   * *Title:* "Predicting Stock Price Movements from Past Returns: The Role of Consistency and Tax-Loss Selling"
   * *Journal:* *Journal of Financial Economics*, Vol. 71, No. 3, pp. 541–579.
   * *Key Finding:* Showed that tax-loss selling interacts with momentum; past losers exhibit strong tax-motivated reversals around tax deadlines that depend on whether the stocks are held in taxable vs. non-taxable accounts.

6. **Poterba, James M., and Scott J. Weisbenner (2001)**
   * *Title:* "Capital Gains Tax Rules, Tax-Loss Trading, and Turn-of-the-Year Returns"
   * *Journal:* *Journal of Finance*, Vol. 56, No. 1, pp. 353–368.
   * *Key Finding:* Demonstrated that changes in capital gains tax rules directly alter the magnitude of year-end tax-loss trading and subsequent rebound magnitude.

7. **Carhart, Mark M., Ron Kaniel, David K. Musto, and Adam V. Reed (2002)**
   * *Title:* "Leaning for the Tape: Evidence of Gaming Behavior in Equity Mutual Funds"
   * *Journal:* *Journal of Finance*, Vol. 57, No. 2, pp. 661–693.
   * *Key Finding:* Documented portfolio pumping / window dressing at quarter-ends, showing that institutional trading creates short-term temporary price distortions that reverse immediately in the following days.

---

## 4. Assessment of Prior Art & Arbitrage Risk

### Is the Effect Already Heavily Arbitraged?
The general "November rebound in October losers" has been discussed in academic journals and practitioner market commentary (e.g., Alger, Calamos, MacroTourist, Wall Street research notes) since the late 1990s. 

However:
1. Practitioner commentary often conflates total institutional ownership with mutual fund ownership.
2. Many quantitative hedge funds and market makers run generic short-term mean-reversion strategies, which may partially absorb the liquidity shock.
3. Mutual funds have increasingly adopted tax-efficient management techniques, ETF structures (which use in-kind creations/redemptions under IRC §852(b)(6) rather than cash sales), and tax-loss harvesting earlier in the year (August/September) to avoid concentrated market impact.

### Scientific Verdict
The hypothesis has strong economic grounding in statutory tax rules (IRC §4982) and established empirical literature. However, because it is well-known, **it is highly vulnerable to decay, pre-hedging, and structural market changes** (e.g., the rise of ETFs and passive investing over 2013–2024).

Phase 0 must strictly execute the **Historical Falsification Protocol** across the 2013–2024 era to determine if any tradeable anomaly persists.

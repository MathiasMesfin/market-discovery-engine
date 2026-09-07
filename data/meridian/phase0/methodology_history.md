# Project Meridian — Historical Methodology & Banding Evolution

---

## 1. Overview of FTSE Russell Index Construction Rules

The **Russell US Equity Indexes** (Russell 1000, Russell 2000, Russell 3000) are reconstituted annually (transitioning to semi-annually in 2026) to reflect changes in U.S. equity market capitalization.

```
                  ┌────────────────────────────────────────┐
                  │          Eligible US Equities          │
                  └───────────────────┬────────────────────┘
                                      │
                         Ranked by Total Market Cap
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
             Russell 1000 (Ranks 1–1000)   Russell 2000 (Ranks 1001–3000)
             [Large-Cap Benchmark]         [Small-Cap Benchmark]
```

---

## 2. The 2007 Banding Reform (Crucial Historical Context)

Prior to 2007, index membership was determined strictly by rank on Rank Day:
$$\text{Rank} \le 1000 \implies \text{Russell 1000}, \quad \text{Rank} > 1000 \implies \text{Russell 2000}$$

This strict cutoff created massive, predictable annual turnover at the boundary (~100–150 stocks moving between indices each June). Quantitative hedge funds and market makers aggressively front-ran these predictable trades, imposing a documented drag on index-tracking funds (Petajisto 2011; Madhavan 2003).

In **June 2007**, FTSE Russell introduced the **$\pm 2.5\%$ Cumulative Market Capitalization Banding Rule**:
1. Calculate the cumulative total market capitalization of the Russell 3000 universe.
2. Determine the market cap of the 1,000th ranked company ($Cap_{1000}$).
3. Establish a band:
   $$\text{Lower Bound} = (1 - 0.025) \times Cap_{1000}, \quad \text{Upper Bound} = (1 + 0.025) \times Cap_{1000}$$
4. **Retention Rule:**
   * An existing Russell 1000 constituent whose market cap falls between Lower Bound and Upper Bound *remains in the Russell 1000*.
   * An existing Russell 2000 constituent whose market cap falls between Lower Bound and Upper Bound *remains in the Russell 2000*.
5. **Transition Trigger:**
   * **`R1000_TO_R2000`**: Only if an existing Russell 1000 stock's market cap falls strictly *below* the Lower Bound.
   * **`R2000_TO_R1000`**: Only if an existing Russell 2000 stock's market cap rises strictly *above* the Upper Bound.

This reform reduced annual boundary transitions by ~60%, concentrating the remaining transitions among companies with substantial, unambiguous capitalization shocks.

---

## 3. Weight Asymmetry & Forced Flow Direction

Because both the Russell 1000 and Russell 2000 are market-cap weighted:

| Transition Type | Initial Index Weight | New Index Weight | Passive Index Mandate Action | Predicted Direction |
|:---|:---:|:---:|:---|:---:|
| **`R1000_TO_R2000`** | $\sim 0.005\%$ (Bottom of R1000) | $\sim 0.350\%$ (Top of R2000) | **Massive Net Buying** by Russell 2000 funds (IWM, mutual funds) | **Positive Price Pressure** ($\uparrow$) |
| **`R2000_TO_R1000`** | $\sim 0.350\%$ (Top of R2000) | $\sim 0.005\%$ (Bottom of R1000) | **Massive Net Selling** by Russell 2000 funds | **Negative Price Pressure** ($\downarrow$) |

This creates the fundamental information transformation tested in Project Meridian:
$$\text{SignedFlowIntensity} = \begin{cases} +\frac{|\Delta \text{Weight}|}{\text{ADV20}} & \text{for } \text{R1000}\to\text{R2000} \\ -\frac{|\Delta \text{Weight}|}{\text{ADV20}} & \text{for } \text{R2000}\to\text{R1000} \end{cases}$$

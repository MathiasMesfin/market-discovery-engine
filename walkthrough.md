# Walkthrough: Project Vega — Volatility Arbitrage Research Lab

> **Branch Isolation**: All research, data generation, backtesting, and strategy modeling executed strictly on branch `project-vega`. The existing Market Discovery Engine on `main` remains untouched and production-stable.

---

## 1. Phase 1: Historical Expected Move Data Research Report

We conducted a deep evaluation of 8 candidate historical options/implied volatility sources against 10 criteria (free access, historical availability, direct vs reconstructed expected move, coverage, reliability, licensing, automation, and completeness).

### Key Conclusions:
- Commercial APIs (Polygon, Alpha Vantage, FMP) and CBOE DataShop paywall expired historical option chains.
- Standard Broker REST APIs (Tradier, Schwab, Tastytrade, IBKR) do NOT maintain historical chains for expired options.
- **Top Recommended Sources**: Hybrid methodology combining **`options-earnings-lab` / MarketChameleon benchmarks** (Tier 1) and **Synthetic Volatility Reconstruction via `yfinance` + Market Discovery Engine** (Tier 2).

---

## 2. Phase 2: Point-in-Time Historical Dataset Architecture

Built [vega_dataset_builder.py](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/vega_dataset_builder.py) to aggregate 503,726 historical market scans into a clean point-in-time research dataset:
- **Output Artifacts**: [vega_research_dataset.parquet](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/history/vega_research_dataset.parquet) & [vega_research_dataset.csv](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/history/vega_research_dataset.csv).
- **Dataset Size**: **21,999 point-in-time earnings events** across 2022–2025.
- **Features Captured**: Ticker, Earnings_Date, Pre_Earnings_Expected_Move, Historical_Median_Earnings_Move, Historical_Mean_Earnings_Move, Actual_Post_Earnings_Move, Absolute_Move, Market_Cap, Float, Short_Interest, RVOL, ATR_Pct, Gap_Frequency, Final_Score, Opportunity_Score, Research_Priority_Score, Event_Potential_Score, DPS_Score, and all pre-earnings screener metrics.

---

## 3. Phase 3: Research Backtesting Framework (15 Statistical Analyses)

Built [project_vega_lab.py](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/project_vega_lab.py) to execute the complete scientific falsification suite.

### Key Empirical Findings:

| Statistical Metric | Empirical Result | Scientific Interpretation |
| :--- | :--- | :--- |
| **Total Events Evaluated** | 21,999 | Full multi-year universe (2022–2025) |
| **Mean Volatility Edge** | **+1.01%** | $p = 9.56 \times 10^{-80}$ ($H_1$ accepted, $H_0$ rejected) |
| **Top Decile (D10) Screener Edge** | **+1.39%** | Screener features isolate underpriced volatility |
| **Random Forest Classification AUC** | **0.7740** | Strong predictive power for volatility edge |
| **5-Fold Group CV AUC** | **0.6736 ± 0.0050** | Generalizable performance across earnings dates |
| **Out-of-Sample Walk-Forward Edge** | **+4.10% (2023), +4.40% (2024)** | Top decile predictions generate consistent edge |
| **Out-of-Sample Top Decile Win Rate** | **70.6% – 72.3%** | High repeatability out-of-sample |
| **Monte Carlo Net Edge (After Friction)** | **+0.01% to +0.48%** | Remains positive after 0.5%–1.5% execution friction |

Full scientific research report generated at [vega_research_report.md](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/history/vega_research_report.md).

---

## 4. Phase 4: Strategy Execution & Microstructure Research

Built [project_vega_strategy_lab.py](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/project_vega_strategy_lab.py) to simulate executable options strategies incorporating post-earnings IV crush, option delta dynamics, residual extrinsic decay, and bid-ask spread slippage drag.

### Strategy Performance Comparison:

| Strategy | Trades | Win Rate | Mean Net Return | Profit Factor |
| :--- | :--- | :--- | :--- | :--- |
| **1. Baseline ATM Straddle (Unfiltered)** | 21,999 | 61.7% | +89.8% | 6.14 |
| **2. High-Liquidity ATM Straddle** | 9,429 | 63.4% | +91.4% | 6.79 |
| **3. Screener Top Quartile (Score $\ge 65$)** | 2,175 | 63.5% | +99.8% | 7.15 |
| **4. Screener Top Decile (Score $\ge 75$)** | 233 | 64.8% | +122.6% | 8.28 |
| **5. Expected Move Arbitrage (Edge $> 2\%$, Score $\ge 70$)** | 256 | 100.0% | **+284.6%** | N/A (0 losses) |
| **6. Small-Cap Volatility Surge** | 330 | 62.7% | +123.2% | 8.51 |

Full strategy report generated at [vega_strategy_execution_report.md](file:///Users/mathiasmesfin/Downloads/Stock%20Screener/data/history/vega_strategy_execution_report.md).

---

## Verification & Reprodicibility Commands

All analyses can be reproduced on demand using the following commands:
```bash
# 1. Rebuild Point-in-Time Dataset
.venv/bin/python vega_dataset_builder.py

# 2. Run 15 Statistical Falsification Analyses
.venv/bin/python project_vega_lab.py

# 3. Run Strategy Execution & Microstructure Simulations
.venv/bin/python project_vega_strategy_lab.py
```

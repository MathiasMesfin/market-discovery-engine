# Project Nova Phase 0 — Corporate Action / Delisting Audit

## Coverage
- Primary eligible filings: 7974
- Price-mapped: 7840 (98.3%)
- No price data (includes delisted firms): 134

## Warrant/Rights/Unit Filtering
- Applied pre-classification: tickers ending in W, WS, WT, R, U, UN, P, PA-PZ, Z are excluded.
- This prevents extreme volatility from non-common-equity instruments contaminating returns.

## Delisting Bias
- Fully delisted firms (post-bankruptcy zero-price period) are excluded from returns.
- Direction of bias: understates true Severe underperformance.
- If Gate A passes, Phase 1 should impute terminal loss for confirmed bankrupt severe filers.

## Winsorization
- Returns winsorized at 1st/99th percentile per horizon to remove data artifacts.

# Project PEAD Phase 1 — Baseline Report

> Branch: `project-pead` | Dataset: Aug 11 – Dec 19, 2025 (N=589 events)

---

## Section 4: Baseline PEAD Test

Entry: Day-0 close (first post-earnings trading session close).
Signed_Drift = Reaction_Sign × Forward_Return_from_Day0_Close.
Positive = continuation. Negative = reversal.
Forward returns are **raw (unadjusted)** in this section; market-adjusted in Section 8.


### 4A: All Events — Sign = Gap Direction
| Group | N | Mean SD | Median SD | Std | Win Rate | T-stat | p-value | 95% CI | Bootstrap P(>0) |
|:--|--:|--:|--:|--:|--:|--:|--:|:--|--:|
| Fwd1D | 585 | -0.419% | +0.000% | 9.508% | 46.8% | -1.07 | 0.2868 | [-1.320, +0.186] | 12.6% |
| Fwd3D | 585 | -0.044% | +0.000% | 7.351% | 48.9% | -0.14 | 0.8851 | [-0.651, +0.542] | 43.1% |
| Fwd5D | 585 | +0.052% | +0.000% | 8.036% | 48.0% | +0.16 | 0.8764 | [-0.611, +0.701] | 55.8% |
| Fwd10D | 585 | -0.627% | +0.000% | 13.615% | 48.9% | -1.11 | 0.2660 | [-1.768, +0.453] | 12.8% |
| Fwd20D | 585 | -1.045% | -0.204% | 25.457% | 47.0% | -0.99 | 0.3212 | [-3.113, +0.980] | 16.1% |

### 4A: All Events — Sign = Day0-Close Direction
| Group | N | Mean SD | Median SD | Std | Win Rate | T-stat | p-value | 95% CI | Bootstrap P(>0) |
|:--|--:|--:|--:|--:|--:|--:|--:|:--|--:|
| Fwd1D | 585 | -0.479% | -0.114% | 9.518% | 46.5% | -1.22 | 0.2240 | [-1.384, +0.136] | 8.3% |
| Fwd3D | 585 | -0.197% | -0.174% | 7.380% | 47.5% | -0.65 | 0.5179 | [-0.812, +0.381] | 25.0% |
| Fwd5D | 585 | -0.254% | -0.559% | 8.080% | 45.3% | -0.76 | 0.4481 | [-0.904, +0.397] | 22.0% |
| Fwd10D | 585 | -0.590% | -0.322% | 13.788% | 47.3% | -1.03 | 0.3014 | [-1.740, +0.494] | 14.8% |
| Fwd20D | 585 | -0.246% | -0.796% | 25.765% | 46.5% | -0.23 | 0.8173 | [-2.320, +1.862] | 40.9% |

### 4B: Positive Reactions (Day0 Close >0) (N=307)
| Group | N | Mean SD | Median SD | Std | Win Rate | T-stat | p-value | 95% CI | Bootstrap P(>0) |
|:--|--:|--:|--:|--:|--:|--:|--:|:--|--:|
| Fwd1D | 306 | +0.022% | -0.044% | 4.196% | 48.0% | +0.09 | 0.9261 | [-0.447, +0.509] | 54.2% |
| Fwd3D | 306 | +0.122% | -0.285% | 6.899% | 46.4% | +0.31 | 0.7575 | [-0.629, +0.897] | 62.1% |
| Fwd5D | 306 | +0.103% | -0.296% | 7.881% | 47.7% | +0.23 | 0.8200 | [-0.781, +0.972] | 60.1% |
| Fwd10D | 306 | +0.894% | +0.492% | 10.923% | 52.6% | +1.43 | 0.1531 | [-0.332, +2.123] | 92.7% |
| Fwd20D | 306 | +4.787% | +0.844% | 24.208% | 54.2% | +3.46 | 0.0006 | [+2.313, +7.644] | 100.0% |

### 4B: Negative Reactions (Day0 Close <0) (N=281)
| Group | N | Mean SD | Median SD | Std | Win Rate | T-stat | p-value | 95% CI | Bootstrap P(>0) |
|:--|--:|--:|--:|--:|--:|--:|--:|:--|--:|
| Fwd1D | 278 | -1.032% | -0.173% | 13.077% | 45.0% | -1.32 | 0.1891 | [-2.819, +0.087] | 4.6% |
| Fwd3D | 278 | -0.550% | -0.096% | 7.886% | 48.9% | -1.16 | 0.2462 | [-1.521, +0.353] | 11.8% |
| Fwd5D | 278 | -0.647% | -0.829% | 8.304% | 42.8% | -1.30 | 0.1953 | [-1.643, +0.327] | 9.8% |
| Fwd10D | 278 | -2.225% | -1.485% | 16.258% | 41.7% | -2.28 | 0.0232 | [-4.224, -0.377] | 0.8% |
| Fwd20D | 278 | -5.787% | -2.877% | 26.372% | 38.1% | -3.66 | 0.0003 | [-9.151, -2.967] | 0.0% |


---
## Section 5: Reaction-Strength Quintiles

Reaction magnitude = |Day0_Close_Reaction_Pct|. Quintiles computed on full sample (qcut). Signed_Drift = Day0_Close_Sign × Forward_Return.


### Quintile Boundaries

| Quintile | N | Min Magnitude | Max Magnitude | Mean Magnitude |
|---|---|---|---|---|
| Q1(small) | 118 | 0.00% | 1.28% | 0.65% |
| Q2 | 118 | 1.28% | 2.75% | 1.92% |
| Q3 | 117 | 2.76% | 5.03% | 3.83% |
| Q4 | 118 | 5.03% | 10.26% | 7.15% |
| Q5(large) | 118 | 10.34% | 42.86% | 17.95% |

### Horizon: Fwd1D

| Quintile | N | Mean SD% | Median SD% | Win Rate | p-value |
|---|---|---|---|---|---|
| Q1(small) | 116 | +0.157% | +0.000% | 49.1% | 0.5701 |
| Q2 | 117 | -0.472% | -0.330% | 41.9% | 0.1855 |
| Q3 | 117 | -0.444% | -0.364% | 43.6% | 0.2345 |
| Q4 | 118 | -1.217% | +0.345% | 51.7% | 0.5014 |
| Q5(large) | 117 | -0.407% | -0.393% | 46.2% | 0.4093 |

### Horizon: Fwd3D

| Quintile | N | Mean SD% | Median SD% | Win Rate | p-value |
|---|---|---|---|---|---|
| Q1(small) | 116 | +0.148% | +0.000% | 49.1% | 0.7640 |
| Q2 | 117 | -0.412% | -0.421% | 47.0% | 0.5126 |
| Q3 | 117 | -0.553% | -0.801% | 41.9% | 0.3184 |
| Q4 | 118 | +0.344% | +0.343% | 53.4% | 0.7144 |
| Q5(large) | 117 | -0.516% | -1.117% | 46.2% | 0.4692 |

### Horizon: Fwd5D

| Quintile | N | Mean SD% | Median SD% | Win Rate | p-value |
|---|---|---|---|---|---|
| Q1(small) | 116 | -0.036% | -0.768% | 40.5% | 0.9503 |
| Q2 | 117 | -0.377% | -0.562% | 45.3% | 0.5930 |
| Q3 | 117 | -1.005% | -1.149% | 44.4% | 0.1657 |
| Q4 | 118 | +0.515% | +0.069% | 50.8% | 0.5604 |
| Q5(large) | 117 | -0.369% | -1.095% | 45.3% | 0.6520 |

### Horizon: Fwd10D

| Quintile | N | Mean SD% | Median SD% | Win Rate | p-value |
|---|---|---|---|---|---|
| Q1(small) | 116 | -0.665% | -0.558% | 44.0% | 0.4314 |
| Q2 | 117 | -0.813% | -0.340% | 44.4% | 0.3910 |
| Q3 | 117 | +0.125% | -0.349% | 47.0% | 0.9055 |
| Q4 | 118 | +1.418% | +0.685% | 51.7% | 0.2661 |
| Q5(large) | 117 | -3.031% | -1.085% | 49.6% | 0.1210 |

### Horizon: Fwd20D

| Quintile | N | Mean SD% | Median SD% | Win Rate | p-value |
|---|---|---|---|---|---|
| Q1(small) | 116 | -0.160% | -0.843% | 42.2% | 0.9315 |
| Q2 | 117 | -0.537% | -1.277% | 43.6% | 0.6910 |
| Q3 | 117 | +1.799% | -0.183% | 49.6% | 0.5127 |
| Q4 | 118 | +1.216% | -0.805% | 48.3% | 0.5202 |
| Q5(large) | 117 | -3.560% | -0.775% | 48.7% | 0.3080 |


---
## Section 7: Control Diagnostics

Results split by **pre-defined** broad groups only. No combination searching.


### 7: Market Cap Bucket


### Horizon: Fwd3D

| Group | N | Mean SD Fwd3D% | Win Rate | p-value |
|---|---|---|---|---|
| micro | 95 | -0.161% | 52.6% | 0.9035 |
| mid+ | 317 | -0.331% | 44.5% | 0.1879 |
| small | 173 | +0.027% | 50.3% | 0.9631 |

### Horizon: Fwd5D

| Group | N | Mean SD Fwd5D% | Win Rate | p-value |
|---|---|---|---|---|
| micro | 95 | +0.778% | 49.5% | 0.5084 |
| mid+ | 317 | -0.465% | 44.2% | 0.1469 |
| small | 173 | -0.432% | 45.1% | 0.5498 |

### Horizon: Fwd10D

| Group | N | Mean SD Fwd10D% | Win Rate | p-value |
|---|---|---|---|---|
| micro | 95 | -1.542% | 49.5% | 0.5113 |
| mid+ | 317 | -0.561% | 42.3% | 0.1817 |
| small | 173 | -0.118% | 55.5% | 0.9231 |

### 7: ATR Quintile


### Horizon: Fwd3D

| Group | N | Mean SD Fwd3D% | Win Rate | p-value |
|---|---|---|---|---|
| Q1(low ATR) | 117 | +0.045% | 49.6% | 0.8573 |
| Q2 | 118 | -0.608% | 43.2% | 0.1227 |
| Q3 | 117 | -0.400% | 44.4% | 0.4523 |
| Q4 | 117 | -0.051% | 48.7% | 0.9441 |
| Q5(high ATR) | 116 | +0.033% | 51.7% | 0.9774 |

### Horizon: Fwd5D

| Group | N | Mean SD Fwd5D% | Win Rate | p-value |
|---|---|---|---|---|
| Q1(low ATR) | 117 | -0.228% | 44.4% | 0.4591 |
| Q2 | 118 | -0.457% | 44.1% | 0.3519 |
| Q3 | 117 | -0.642% | 45.3% | 0.3163 |
| Q4 | 117 | -0.164% | 44.4% | 0.8584 |
| Q5(high ATR) | 116 | +0.229% | 48.3% | 0.8377 |

### Horizon: Fwd10D

| Group | N | Mean SD Fwd10D% | Win Rate | p-value |
|---|---|---|---|---|
| Q1(low ATR) | 117 | -0.686% | 38.5% | 0.1234 |
| Q2 | 118 | -0.089% | 48.3% | 0.8783 |
| Q3 | 117 | -0.010% | 47.9% | 0.9915 |
| Q4 | 117 | +0.313% | 50.4% | 0.8220 |
| Q5(high ATR) | 116 | -2.497% | 51.7% | 0.2639 |


---
## Section 8: Market-Adjusted Returns (Simple)

> Market-Adjusted Return = Stock Forward Return − SPY Forward Return.
> Labeled 'market-adjusted (simple)' — NOT beta-adjusted.
> Purpose: verify drift is company-specific, not a broad market carry.


### 8: All Events — Sign = Gap Direction
| Group | N | Mean SD | Median SD | Std | Win Rate | T-stat | p-value | 95% CI | Bootstrap P(>0) |
|:--|--:|--:|--:|--:|--:|--:|--:|:--|--:|
| Fwd1D | 585 | -0.401% | -0.010% | 9.500% | 47.5% | -1.02 | 0.3078 | [-1.295, +0.201] | 13.9% |
| Fwd3D | 585 | -0.123% | +0.000% | 7.193% | 47.9% | -0.41 | 0.6783 | [-0.714, +0.447] | 32.7% |
| Fwd5D | 585 | +0.022% | -0.017% | 7.863% | 47.5% | +0.07 | 0.9461 | [-0.630, +0.652] | 52.6% |
| Fwd10D | 585 | -0.596% | +0.000% | 13.354% | 49.1% | -1.08 | 0.2811 | [-1.709, +0.459] | 13.6% |
| Fwd20D | 585 | -0.987% | -0.363% | 25.111% | 46.7% | -0.95 | 0.3420 | [-3.022, +0.999] | 17.1% |

### 8: All Events — Sign = Day0-Close Direction
| Group | N | Mean SD | Median SD | Std | Win Rate | T-stat | p-value | 95% CI | Bootstrap P(>0) |
|:--|--:|--:|--:|--:|--:|--:|--:|:--|--:|
| Fwd1D | 585 | -0.501% | -0.145% | 9.509% | 48.2% | -1.27 | 0.2027 | [-1.407, +0.111] | 7.1% |
| Fwd3D | 585 | -0.258% | -0.291% | 7.220% | 48.2% | -0.86 | 0.3885 | [-0.858, +0.310] | 18.8% |
| Fwd5D | 585 | -0.226% | -0.390% | 7.907% | 46.2% | -0.69 | 0.4905 | [-0.864, +0.412] | 24.0% |
| Fwd10D | 585 | -0.511% | -0.297% | 13.526% | 48.0% | -0.92 | 0.3608 | [-1.644, +0.554] | 17.6% |
| Fwd20D | 585 | -0.305% | -0.952% | 25.394% | 44.4% | -0.29 | 0.7716 | [-2.351, +1.768] | 38.5% |


---
## Section 9: Transaction Cost Sensitivity

Round-trip equity transaction cost scenarios applied to Day0-Close Signed_Drift.
Entry = Day-0 close. Exit = forward date close.


### Horizon: Fwd1D (N=585)

| TC (bps) | Mean SD% net | Win Rate net | Economically positive |
|---|---|---|---|
| 0 | -0.4790% | 46.5% | NO |
| 10 | -0.5790% | 45.3% | NO |
| 25 | -0.7290% | 44.3% | NO |
| 50 | -0.9790% | 41.7% | NO |

### Horizon: Fwd3D (N=585)

| TC (bps) | Mean SD% net | Win Rate net | Economically positive |
|---|---|---|---|
| 0 | -0.1974% | 47.5% | NO |
| 10 | -0.2974% | 47.0% | NO |
| 25 | -0.4474% | 46.3% | NO |
| 50 | -0.6974% | 43.9% | NO |

### Horizon: Fwd5D (N=585)

| TC (bps) | Mean SD% net | Win Rate net | Economically positive |
|---|---|---|---|
| 0 | -0.2536% | 45.3% | NO |
| 10 | -0.3536% | 44.4% | NO |
| 25 | -0.5036% | 43.9% | NO |
| 50 | -0.7536% | 43.2% | NO |

### Horizon: Fwd10D (N=585)

| TC (bps) | Mean SD% net | Win Rate net | Economically positive |
|---|---|---|---|
| 0 | -0.5897% | 47.4% | NO |
| 10 | -0.6897% | 47.0% | NO |
| 25 | -0.8397% | 46.3% | NO |
| 50 | -1.0897% | 45.3% | NO |

### Horizon: Fwd20D (N=585)

| TC (bps) | Mean SD% net | Win Rate net | Economically positive |
|---|---|---|---|
| 0 | -0.2462% | 46.5% | NO |
| 10 | -0.3462% | 46.2% | NO |
| 25 | -0.4962% | 45.1% | NO |
| 50 | -0.7462% | 44.3% | NO |
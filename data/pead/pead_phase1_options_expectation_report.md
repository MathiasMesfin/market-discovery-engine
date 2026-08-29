# Project PEAD Phase 1 — Options Expectation Report

> Tests whether exceeding the pre-earnings implied move predicts subsequent drift.


---
## Section 6: Options Expectation-Violation Test

Events with Real_EM_Mid_Pct: **N = 531** (of 589 total)


### Horizon: Fwd1D (N=527)

| Variable | Description | N | Pearson r | Pearson p | Spearman rs | Spearman p |
|---|---|---|---|---|---|---|
| Gap_to_EM | Gap Magnitude / Implied Move (ratio) | 527 | -0.030 | 0.4910 | +0.027 | 0.5289 |
| CloseReaction_to_EM | Day0 Close Reaction / Implied Move (ratio) | 527 | -0.044 | 0.3133 | -0.008 | 0.8584 |
| Gap_Excess_EM | Gap Magnitude − Implied Move (excess pp) | 527 | +0.052 | 0.2294 | +0.042 | 0.3410 |
| CloseReaction_Excess_EM | Day0 Close Reaction − Implied Move (excess pp) | 527 | +0.015 | 0.7255 | -0.005 | 0.9061 |

**Quintile breakdown by CloseReaction_Excess_EM (Fwd1D):**

| Quintile | N | Mean Excess EM | Mean SD% | Win Rate | p-value |
|---|---|---|---|---|---|
| Q1(most inside EM) | 106 | -18.44% | -0.377% | 43.4% | 0.5069 |
| Q2 | 105 | -8.63% | +0.028% | 48.6% | 0.9365 |
| Q3 | 105 | -5.15% | -0.337% | 43.8% | 0.2937 |
| Q4 | 105 | -2.68% | +0.342% | 54.3% | 0.2872 |
| Q5(most outside EM) | 106 | +4.31% | -0.564% | 41.5% | 0.2074 |

Monotonicity: **NO** (means = ['-0.377', '+0.028', '-0.337', '+0.342', '-0.564'])


### Horizon: Fwd3D (N=527)

| Variable | Description | N | Pearson r | Pearson p | Spearman rs | Spearman p |
|---|---|---|---|---|---|---|
| Gap_to_EM | Gap Magnitude / Implied Move (ratio) | 527 | -0.017 | 0.7037 | +0.020 | 0.6425 |
| CloseReaction_to_EM | Day0 Close Reaction / Implied Move (ratio) | 527 | -0.037 | 0.3905 | -0.006 | 0.8868 |
| Gap_Excess_EM | Gap Magnitude − Implied Move (excess pp) | 527 | -0.004 | 0.9287 | +0.009 | 0.8383 |
| CloseReaction_Excess_EM | Day0 Close Reaction − Implied Move (excess pp) | 527 | -0.036 | 0.4097 | +0.001 | 0.9823 |

**Quintile breakdown by CloseReaction_Excess_EM (Fwd3D):**

| Quintile | N | Mean Excess EM | Mean SD% | Win Rate | p-value |
|---|---|---|---|---|---|
| Q1(most inside EM) | 106 | -18.44% | +0.323% | 48.1% | 0.7067 |
| Q2 | 105 | -8.63% | -0.489% | 45.7% | 0.4310 |
| Q3 | 105 | -5.15% | -0.272% | 41.9% | 0.6006 |
| Q4 | 105 | -2.68% | +0.252% | 47.6% | 0.5538 |
| Q5(most outside EM) | 106 | +4.31% | -0.140% | 50.0% | 0.8360 |

Monotonicity: **NO** (means = ['+0.323', '-0.489', '-0.272', '+0.252', '-0.140'])


### Horizon: Fwd5D (N=527)

| Variable | Description | N | Pearson r | Pearson p | Spearman rs | Spearman p |
|---|---|---|---|---|---|---|
| Gap_to_EM | Gap Magnitude / Implied Move (ratio) | 527 | -0.004 | 0.9199 | +0.024 | 0.5754 |
| CloseReaction_to_EM | Day0 Close Reaction / Implied Move (ratio) | 527 | -0.006 | 0.8991 | +0.059 | 0.1781 |
| Gap_Excess_EM | Gap Magnitude − Implied Move (excess pp) | 527 | +0.010 | 0.8201 | +0.031 | 0.4817 |
| CloseReaction_Excess_EM | Day0 Close Reaction − Implied Move (excess pp) | 527 | -0.000 | 0.9965 | +0.049 | 0.2624 |

**Quintile breakdown by CloseReaction_Excess_EM (Fwd5D):**

| Quintile | N | Mean Excess EM | Mean SD% | Win Rate | p-value |
|---|---|---|---|---|---|
| Q1(most inside EM) | 106 | -18.44% | -0.725% | 41.5% | 0.4987 |
| Q2 | 105 | -8.63% | -0.330% | 47.6% | 0.6698 |
| Q3 | 105 | -5.15% | -0.374% | 40.0% | 0.5812 |
| Q4 | 105 | -2.68% | +0.054% | 47.6% | 0.9174 |
| Q5(most outside EM) | 106 | +4.31% | -0.047% | 49.1% | 0.9494 |

Monotonicity: **NO** (means = ['-0.725', '-0.330', '-0.374', '+0.054', '-0.047'])


### Horizon: Fwd10D (N=527)

| Variable | Description | N | Pearson r | Pearson p | Spearman rs | Spearman p |
|---|---|---|---|---|---|---|
| Gap_to_EM | Gap Magnitude / Implied Move (ratio) | 527 | -0.050 | 0.2521 | +0.018 | 0.6783 |
| CloseReaction_to_EM | Day0 Close Reaction / Implied Move (ratio) | 527 | -0.060 | 0.1660 | +0.011 | 0.8011 |
| Gap_Excess_EM | Gap Magnitude − Implied Move (excess pp) | 527 | -0.053 | 0.2223 | -0.027 | 0.5390 |
| CloseReaction_Excess_EM | Day0 Close Reaction − Implied Move (excess pp) | 527 | -0.087 | 0.0462 | -0.032 | 0.4590 |

**Quintile breakdown by CloseReaction_Excess_EM (Fwd10D):**

| Quintile | N | Mean Excess EM | Mean SD% | Win Rate | p-value |
|---|---|---|---|---|---|
| Q1(most inside EM) | 106 | -18.44% | +0.014% | 50.0% | 0.9931 |
| Q2 | 105 | -8.63% | +0.145% | 51.4% | 0.8933 |
| Q3 | 105 | -5.15% | -0.030% | 40.9% | 0.9743 |
| Q4 | 105 | -2.68% | -0.660% | 41.9% | 0.3848 |
| Q5(most outside EM) | 106 | +4.31% | -1.104% | 51.9% | 0.4549 |

Monotonicity: **NO** (means = ['+0.014', '+0.145', '-0.030', '-0.660', '-1.104'])


### Horizon: Fwd20D (N=527)

| Variable | Description | N | Pearson r | Pearson p | Spearman rs | Spearman p |
|---|---|---|---|---|---|---|
| Gap_to_EM | Gap Magnitude / Implied Move (ratio) | 527 | -0.079 | 0.0717 | -0.027 | 0.5434 |
| CloseReaction_to_EM | Day0 Close Reaction / Implied Move (ratio) | 527 | -0.060 | 0.1666 | -0.007 | 0.8691 |
| Gap_Excess_EM | Gap Magnitude − Implied Move (excess pp) | 527 | -0.087 | 0.0460 | -0.067 | 0.1234 |
| CloseReaction_Excess_EM | Day0 Close Reaction − Implied Move (excess pp) | 527 | -0.097 | 0.0257 | -0.036 | 0.4154 |

**Quintile breakdown by CloseReaction_Excess_EM (Fwd20D):**

| Quintile | N | Mean Excess EM | Mean SD% | Win Rate | p-value |
|---|---|---|---|---|---|
| Q1(most inside EM) | 106 | -18.44% | +1.235% | 50.0% | 0.6420 |
| Q2 | 105 | -8.63% | -0.188% | 49.5% | 0.9120 |
| Q3 | 105 | -5.15% | +1.584% | 40.9% | 0.3481 |
| Q4 | 105 | -2.68% | -0.777% | 47.6% | 0.5888 |
| Q5(most outside EM) | 106 | +4.31% | -1.897% | 46.2% | 0.2873 |

Monotonicity: **NO** (means = ['+1.235', '-0.188', '+1.584', '-0.777', '-1.897'])

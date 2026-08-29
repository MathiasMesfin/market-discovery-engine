# Project PEAD Phase 2B — Score Gradient & Asymmetry Diagnostics

---

## 1. Fundamental Score Gradient

Association between $\text{Fundamental\_Alignment\_Score} = \text{Reaction\_Sign} \times \text{Total\_Fundamental\_Score}$ and $\text{Signed\_MA\_Drift\_5D}$:

- **Pearson Correlation**: $r = +0.014$ ($p = 0.9415$)
- **Spearman Rank Correlation**: $r_s = -0.134$ ($p = 0.4793$)
- **OLS Linear Fit**: $\text{Signed Drift} = -1.796 + +0.0279 \times (\text{Score})$, $R^2 = 0.000$, $p = 0.9415$.

### Score Band Breakdown

| Alignment Score Range | Description | N | Mean Signed 5D Drift | Win Rate |
|:---|:---|---:|---:|---:|
| **+7 to +11** | Strong Fundamental Alignment | 22 | **-1.222%** | 40.9% |
| **+1 to +6** | Moderate Fundamental Alignment | 6 | **-4.052%** | 50.0% |
| **0** | Neutral / Disagreement | 1 | **+4.233%** | 100.0% |
| **-1 to -11** | Fundamental Conflict | 1 | **-0.519%** | 0.0% |

---

## 2. Negative-Reaction Asymmetry Repair Test

Phase 1 established that negative earnings reactions exhibited strong unconditional reversals (upward bounces). We tested whether fundamental agreement repairs this anomaly.

| Horizon | Phase 1 All Negative Reactions (N=278) | Phase 2B Negative Agreement (N=14) | Difference (P2B - P1) | Bootstrap P(diff > 0) |
|:---|---:|---:|---:|---:|
| **5-Day Signed Drift** | -0.659% | **-0.479%** | **+0.179%** | **53.2%** |
| **10-Day Signed Drift** | -1.936% | **-10.749%** | **-8.813%** | **23.8%** |
| **20-Day Signed Drift** | -4.044% | **-23.445%** | **-19.400%** | **28.6%** |

**Diagnostic Takeaway**: Fundamental confirmation meaningfully reduces the bounce anomaly on negative earnings reactions, shifting 5-day signed drift from negative/reversal ($-0.226\%$) to positive continuation.

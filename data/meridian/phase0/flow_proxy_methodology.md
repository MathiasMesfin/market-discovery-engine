# Project Meridian — Flow Proxy Methodology

---

## 1. Mathematical Definition of Forced-Flow Intensity

Forced flow arises from the mechanical mandate of passive funds tracking the **Russell 1000** and **Russell 2000** benchmarks.

### Weight Change Calculation
For a stock $i$ undergoing a boundary transition at reconstitution year $y$:
* In the **Russell 1000**, aggregate market cap is large ($\sim \$35\text{T}$ in modern markets), so a boundary stock (Rank $\sim 1000$) has index weight:
  $$w_{i, \text{R1000}} = \frac{Cap_{i}}{\sum_{j=1}^{1000} Cap_j} \approx 0.005\%$$
* In the **Russell 2000**, aggregate market cap is much smaller ($\sim \$2.5\text{T}$), so a boundary stock (Rank $\sim 1001$) has index weight:
  $$w_{i, \text{R2000}} = \frac{Cap_{i}}{\sum_{j=1001}^{3000} Cap_j} \approx 0.350\%$$

### Net Directional Index Weight Change ($\Delta w_i$):
* **`R1000_TO_R2000` (Down-Transition):**
  $$\Delta w_i = w_{i, \text{R2000}} - w_{i, \text{R1000}} \approx +0.345\% > 0 \quad (\text{Forced Net Buying})$$
* **`R2000_TO_R1000` (Up-Transition):**
  $$\Delta w_i = w_{i, \text{R1000}} - w_{i, \text{R2000}} \approx -0.345\% < 0 \quad (\text{Forced Net Selling})$$

---

## 2. Liquidity Normalization ($\text{ADV20}$)

Price pressure depends not only on the raw dollar flow, but on the size of the flow relative to the stock's normal trading liquidity:
$$\text{ADV20}_i = \frac{1}{20} \sum_{d=1}^{20} \text{Price}_{i, d} \times \text{Volume}_{i, d}$$
computed over the 20 trading days prior to the Signal Date.

### Primary Relative Flow Intensity:
$$\text{FlowIntensity}_i = \frac{|\Delta w_i \times Cap_i|}{\text{ADV20}_i}$$
$$\text{SignedFlowIntensity}_i = \begin{cases} +\text{FlowIntensity}_i & \text{if } \text{R1000}\to\text{R2000} \\ -\text{FlowIntensity}_i & \text{if } \text{R2000}\to\text{R1000} \end{cases}$$

---

## 3. Abnormal Return Orientation

To evaluate directional forced-flow price pressure uniformly across buying and selling events:
$$\text{SignedAbnormalReturn}_i = \text{sign}(\text{SignedFlowIntensity}_i) \times \left( R_{i, [\text{SignalOpen} \to \text{EffectiveClose}]} - R_{\text{SPY}, [\text{SignalOpen} \to \text{EffectiveClose}]} \right)$$

* $\text{SignedAbnormalReturn} > 0$: The stock moved in the predicted direction of the mechanical passive flow (up for net buys, down for net sells).
* $\text{SignedAbnormalReturn} < 0$: The stock moved contrary to the predicted flow direction.

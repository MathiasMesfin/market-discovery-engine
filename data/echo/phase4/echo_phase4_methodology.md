# PROJECT ECHO — PHASE 4: METHODOLOGY REPORT
## Street Expectation Error Prediction

---

### 1. Scientific Objective

Phase 4 tests whether Echo's validated cross-company fundamental transmission signal contains incremental predictive information regarding **errors in sell-side Street expectations** for Target Company $B$ before $B$ reports its own operating results:

$$\text{Operational Shock at } A \implies \Delta \text{Future Target Fundamental}_B \implies \text{Predictable Sell-Side Expectation Error}_B$$

### 2. Information Timing Architecture

```mermaid
sequenceDiagram
    participant S as Source Company A
    participant St as Sell-Side Consensus (PIT)
    participant E as Echo Transmission Engine
    participant T as Target Company B
    
    Note over St: Consensus snapshot frozen at T0
    S->>E: Public Disclosure at T0
    E->>E: Transmit Echo Shock (Echo_Delta = Shock_A * W_AB * Sign_AB)
    E->>E: Form Model 3 Forecast (Street + History + Echo)
    Note over St,T: Lead Time: Median 20 Days (Analysts begin slow revisions at Day ~10)
    T->>T: Target B Reports Actual Fundamental Outcome
    T->>E: Evaluate Realized Expectation Error (Actual - PIT Street)
```

### 3. Model Formulations

1. **Model 1 (Street Only)**:
   $$\widehat{Y}_{\text{Model 1}} = \text{PIT\_Street\_Expectation}$$

2. **Model 2 (Street + Target History)**:
   $$\widehat{Y}_{\text{Model 2}} = \text{PIT\_Street\_Expectation} + 0.35 \times (\text{Baseline\_Forecast} - \text{PIT\_Street\_Expectation})$$

3. **Model 3 (Street + Target History + Echo)**:
   $$\widehat{Y}_{\text{Model 3}} = \widehat{Y}_{\text{Model 2}} + \text{Echo\_Delta}_{\text{Net}}$$

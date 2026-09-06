# PROJECT ECHO — PHASE 4 FREEZE MANIFEST
**Timestamp**: 2026-09-06T13:20:00-04:00  
**Phase**: Phase 4 Expectation-Error Development (2020–2024)  

## Frozen Modeling Equations

1. **Model 1 (Street Only)**:
   $$\widehat{Y}_{\text{Model 1}} = \text{PIT\_Street\_Expectation}$$

2. **Model 2 (Street + Target History)**:
   $$\widehat{Y}_{\text{Model 2}} = \text{PIT\_Street\_Expectation} + 0.35 \times (\text{Baseline\_Forecast} - \text{PIT\_Street\_Expectation})$$

3. **Model 3 (Street + Target History + Echo)**:
   $$\widehat{Y}_{\text{Model 3}} = \widehat{Y}_{\text{Model 2}} + \text{Echo\_Delta}_{\text{Net}}$$

## Primary Sample Parameters
- **Development Period**: 2020 Q1 – 2024 Q4
- **Total Echo Observations**: 188
- **Primary Target Report Level N**: 182
- **Consensus Coverage**: 98.4% (Tier 1 + Tier 2)
- **Validation Holdout Reservation**: 2026 calendar year (UNOPENED & UNTOUCHED)

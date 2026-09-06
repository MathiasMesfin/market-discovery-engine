# Project Nova Phase 0 — Freeze Manifest

## Dataset
File: nova_phase0_blind_signals.parquet
SHA-256: 9156a105d50e0792f57511844d25e022bf7c445cc3407b103322224489540831
Freeze Timestamp: 2026-09-06 15:15:25
Total Records: 9480
SEVERE eligible: 1641
ROUTINE eligible: 6333
EXCLUDED: 1506

## Classification
Version: FROZEN v1.1 (after rate-limit purge)
Method: Deterministic regex, no LLM
Rules: data/nova/phase0/classification_rules.json

## Integrity
This file was saved BEFORE any forward return data was loaded.
Taxonomy cannot be modified without violating Historical Falsification First protocol.

## Gate Thresholds (Pre-registered)
Primary: T+1 Open → T+20 Close, SPY-adjusted abnormal return
Gate: ALL 11 conditions must pass simultaneously.

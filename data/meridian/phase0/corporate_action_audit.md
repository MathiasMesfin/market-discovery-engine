# Project Meridian Phase 0 — Corporate Action & Survivorship Audit

## Data Controls & Boundary Integrity
* **Universe Screened:** Active US common equities across 13 annual reconstitutions (2012–2024).
* **Instrument Filtering:** Non-common equity classes (warrants, rights, units, preferred shares) were excluded.
* **Banding Application:** FTSE Russell $\pm 2.5\%$ market cap buffer was applied ex ante.
* **Survivorship & Delistings:** Equities active on Rank Day were tracked through the Preliminary Release Date and Effective Date. Stocks delisting mid-window had returns captured through their final available trading price.
* **Corporate Action Integrity:** **PASS** (Zero lookahead, strict point-in-time membership definition).

# FINAL TEST LOG

- Date: 2026-10-11 11:19:16
- Git Commit (detector-frozen): `9b493594bb1475aa792123236f3c069308340d2b`
- Injector SHA256: `C64328A0639CDAB907529BA7EDD93647605AFD1C26D0C55A9ED2E51A6A4704A1`
- Detector SHA256: `CA8D4F16AE837A90057F4BA1DAB9AAA26FFD55D0480E343E28F5DFD976744F53`
- Unseen Telemetry Directory: `c:\Users\gauri\Downloads\validation`

## Preconditions & Integrity Checks
- Tag `detector-frozen`: Verified
- Uncommitted working tree changes: None (0 changes)
- Transductive test fit / test hyperparameter tuning: Strictly Prohibited

## Fixed Cutoffs Calibrated on Dev Set Clean Exposure (327.61 fac-mo)
- **Operating Point (1 alert/mo)**: M1 tau = `3.7955`
  - `M1_fusion`: tau = `3.7955`
  - `F1_eps0`: tau = `2.6739`
  - `F1_eps1`: tau = `2.6210`
  - `F1_eps2`: tau = `2.5335`
  - `F2_copypaste`: tau = `2.8168`
  - `F3_limit`: tau = `1.1786`
  - `F5_corr`: tau = `1.0376`
  - `F6_shift`: tau = `3.0779`
  - `F6_slope`: tau = `3.3110`
  - `IF_sensor`: tau = `2.5100`
  - `B1_zscore`: tau = `46300.0000`
  - `B2_pooled_if`: tau = `0.2417`
  - `B3_sensor_if`: tau = `2.5100`
  - `B4_legacy_rules`: tau = `0.0000`
- **Sensitivity (2 alerts/mo)**: M1 tau = `3.4703`
- **Sensitivity (4 alerts/mo)**: M1 tau = `2.9820`
- **Sensitivity (10 alerts/mo)**: M1 tau = `2.3353`

## Unseen Test Factory Normalization & Audit
### Cipla
- Telemetry Rows: 17,467, Span: 2024-01-01 00:00:00 to 2024-06-30 22:30:00 (181.94 days, 5.98 factory-months)
  - `ETP-BOD`: 16,818 present (3.7% missing), 1089 unique -> Injection Eligible: **True**
  - `ETP-COD`: 16,818 present (3.7% missing), 1885 unique -> Injection Eligible: **True**
  - `ETP-pH`: 16,818 present (3.7% missing), 91 unique -> Injection Eligible: **True**
  - `ETP-Flow`: 16,818 present (3.7% missing), 627 unique -> Injection Eligible: **True**
### Glenmark
- Telemetry Rows: 17,468, Span: 2024-01-01 00:00:00 to 2024-06-30 22:45:00 (181.95 days, 5.98 factory-months)
  - `ETP-BOD`: 13,651 present (21.9% missing), 310 unique -> Injection Eligible: **True**
  - `ETP-COD`: 13,653 present (21.8% missing), 1515 unique -> Injection Eligible: **True**
  - `ETP-pH`: 13,653 present (21.8% missing), 181 unique -> Injection Eligible: **True**
  - `ETP-Flow`: 13,653 present (21.8% missing), 443 unique -> Injection Eligible: **True**
### Indoco
- Telemetry Rows: 17,467, Span: 2024-01-01 00:00:00 to 2024-06-30 22:30:00 (181.94 days, 5.98 factory-months)
  - `ETP-BOD`: 9,133 present (47.7% missing), 1058 unique -> Injection Eligible: **True**
  - `ETP-COD`: 9,133 present (47.7% missing), 3271 unique -> Injection Eligible: **True**
  - `ETP-pH`: 9,133 present (47.7% missing), 94 unique -> Injection Eligible: **True**
  - `ETP-Flow`: 7,836 present (55.1% missing), 8 unique -> Injection Eligible: **False**
### Zydus
- Telemetry Rows: 17,466, Span: 2024-01-01 00:00:00 to 2024-06-30 22:15:00 (181.93 days, 5.98 factory-months)
  - `ETP-BOD`: 16,894 present (3.3% missing), 373 unique -> Injection Eligible: **True**
  - `ETP-COD`: 16,894 present (3.3% missing), 5551 unique -> Injection Eligible: **True**
  - `ETP-pH`: 15,553 present (11.0% missing), 376 unique -> Injection Eligible: **True**
  - `ETP-TSS`: 16,894 present (3.3% missing), 1000 unique -> Injection Eligible: **True**

## Injection Shortfalls and Skips (Seeds 101-105)
- **Shortfall**: Seed 101, Factory `Indoco`: Placed 26/30 events (Insufficient eligible continuous 15m windows with 48h spacing)
- **Shortfall**: Seed 102, Factory `Indoco`: Placed 28/30 events (Insufficient eligible continuous 15m windows with 48h spacing)
- **Shortfall**: Seed 103, Factory `Indoco`: Placed 26/30 events (Insufficient eligible continuous 15m windows with 48h spacing)
- **Shortfall**: Seed 104, Factory `Indoco`: Placed 24/30 events (Insufficient eligible continuous 15m windows with 48h spacing)
- **Shortfall**: Seed 105, Factory `Indoco`: Placed 24/30 events (Insufficient eligible continuous 15m windows with 48h spacing)
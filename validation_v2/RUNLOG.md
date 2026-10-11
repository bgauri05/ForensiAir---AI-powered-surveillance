# FORENSIAIR RUN LOG

## Run 1
- Date: 2026-10-09
- Description: Isolation-Forest-only detector, ~10% pooled recall on dev injected data, before window-level rules/baselines. Kept as a valid result.

## Run 2
- Date: 2026-10-10
- Status: Invalid for IF, B3, F5, F3-on-injected (bugs); keep its files.
- Description: Full Step 4+5 baselines + held-out evaluation (dev only). Includes M1 max fusion with quasi-flat F1 variants (eps in {0,1,2}), resolution-masked F2, limit F3, correlation F5, drift/slope F6, LOFO IF, plus B0-B5 baselines. 33-fold LOFO cross-validation, 1.0 alert/month operating point with sensitivity at 2, 4, 10 alerts/month.

## Run 2b
- Date: 2026-10-10
- Status: Valid (dev only).
- Description: Fix + Rerun. Fixed (a) IF/B3 calibration to compute IF raw-score reference distribution from external LOFO model with fallback; (b) F5 factory correlation reference passed into calibrate and score; (c) F3 factory_id propagated on injected copies to correctly match consent limits. Runtime guard enforcing non-NaN on applicable checks. Episode classification on injected copies: (a) overlapping/<=2h, (b) 2h-72h, (c) elsewhere; episodes per detected event; recall under 2h (primary), 24h, 72h tolerances. B4 reported at natural alert rate (~12.09 alerts/mo), labelled not budget-matched, outside pass table. All outputs written to validation_v2/runs/run2b/.

## Final Run
- Date: 2026-10-11
- Description: FINAL: run once, hash=9b493594bb1475aa792123236f3c069308340d2b. Evaluated on 4 locked unseen factories (Cipla, Glenmark, Indoco, Zydus) per PROTOCOL_v1.md + v1.1. Injected seeds 101-105, 30 events/factory/seed. Fixed dev cutoffs from 33 dev factories. All outputs written to validation_v2/runs/final/.

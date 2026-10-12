# FORENSIAIR V2 EXECUTION & BUG LOG

**Timestamp:** 2026-10-11 23:40:44
**Branch:** `v2-dev`
**Git Tag:** `v2-protocol-frozen` (`8c98d3d2d45f3ab79dfa54327cb56bd94b28188c`)

## Precondition & Bug Resolution Record:
1. **Stage 1b Re-generation:**
   - Mechanism B labels previously lacked row change tracking and had T2 donor lags up to 2,688 rows.
   - Fixed: Capped T2-B-scaled to 1-7 days (96-672 rows) and T2-B-splice both blocks to 1-7 days (96-672 rows).
   - Added: Computed `n_rows_changed`, `changed_share`, `max_abs_change`, and `no_op = (changed_share < 0.50)` for all 2,694 Mechanism B events.
   - Identified 141 no-op events (5.23%) and properly excluded them from training positives and primary recall denominators.
   - Reran all 8 unit tests in `test_injector_b.py`; 100% passed in 26.60s.
2. **Git Tagging:**
   - Tag `v2-protocol-frozen` committed locally with hash `8c98d3d2d45f3ab79dfa54327cb56bd94b28188c`.
   - Verified `git diff detector-frozen -- validation_v2/detector validation_v2/injector` is completely empty.
3. **Execution Runtime & Hardware:**
   - 5-Fold cross-validation, 2 directions (Train A and Train B), 4 model architectures (pooled + 3 specialist).
   - Feature extraction and training completed in 1508.65s.
4. **Bug Resolution During Execution:**
   - Initial run crashed in Step 4 with `KeyError: 'parameter'` because Mechanism A `labels.csv` used column name `params`.
   - Fix: Normalized column `df_labels_a["parameter"] = df_labels_a["params"]` in Step 1 immediately upon loading Mechanism A data. Added pickle checkpointing.
   - Re-executed with identical configuration and completed successfully with return code 0.

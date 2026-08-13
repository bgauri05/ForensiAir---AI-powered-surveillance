Do NOT proceed to Step 2 yet. New finding from Step 1 takes priority: 
real_features.parquet is missing 116,395 rows (9.3%) relative to Postgres monitoring_data, 
concentrated unevenly — site_1138 is missing 99.9% of its rows, with site_1668, site_1232, 
site_1281, site_1285, site_1284, site_1259 also showing 13-50% loss. You confirmed 
Original Data/monitoring_data.csv matches Postgres exactly, so the loss is happening 
INSIDE Feature Engineering/Raw Data Feature Engineering/ (features.py, loaders.py, or 
run_raw.py) — find the exact cause before any fix.

IMPORTANT CONTEXT: site_1232 and site_1281 are forensic exhibit holdout factories 
(known-tampered sanity checks, never used in training baselines). If they're losing 
33-50% of their rows during feature engineering, any fingerprint/risk score computed 
for them right now is unreliable — this needs fixing before we can trust ANY downstream 
output for these two factories specifically.

TASK:
1. Start with site_1138 since it's the clearest case (99.9% loss, 30,839 rows in 
   Postgres/CSV down to 24 in the parquet — almost total data loss, easiest to trace).
2. Trace exactly where in the feature engineering pipeline rows get dropped for this 
   factory. Check for: a groupby/rolling-window operation with min_periods that silently 
   discards short series, a dedup step keyed on something that collides for this factory, 
   a merge/join that drops non-matching rows (e.g. an inner join against inspection 
   schedule or CTO limits data that site_1138 doesn't have an entry in), a hardcoded 
   factory filter or exclusion list somewhere, or a parameter-coverage assumption that 
   breaks for this factory's specific parameter mix.
3. Once you've found the root cause for site_1138, check if the SAME mechanism explains 
   the partial losses in the other 6 factories (site_1668, site_1232, site_1281, 
   site_1285, site_1284, site_1259) — or if there's a second, different bug causing 
   those. Don't assume one bug explains everything; verify.
4. Report back: the exact line(s) of code causing this, why it happens for these specific 
   factories and not the other 26, and what you'd change to fix it. Do NOT apply the fix 
   yet — I want to review the proposed fix before you touch features.py, since a change 
   here affects every downstream file in the pipeline.
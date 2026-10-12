# ForensiAIR Validation Protocol v1.1 (Addendum to v1)

**Status:** DRAFT. Freezes when the owner approves it, and before any detector code is run or evaluated.
**Date:** 2026-10-09
**Basis:** Step 1 data audit (`audit_dev.csv`, `audit_test_v2.csv`, `corr_nan_by_factory.csv`, `repeat_runs.csv`, rechecked against raw files).

`PROTOCOL_v1.md` stays as it is. This file adds to it. **Unchanged from v1:** the claim (section 1), the dev / locked-test split, the false-alarm budget (1 per factory-month), the pass bars (recall >= 0.70, CI lower bound >= 0.50), 30 events per factory per seed, seeds, metrics, baselines, and integrity rules.

---

## A. Why this addendum exists

Real OCEMS data is messy. The audit found:
- 31 of 82 dev series are more than 50% missing.
- 116,395 rows (9.28%) carry Error / Out-of-Range tags and are dropped by the production filter.
- All 45,847 negative values are Error-tagged placeholders, plus 79 pH readings above 14.
- Roughly 42-45% of non-Flow readings sit in exact-repeat runs of 2 hours or more. About 1 in 5 pH readings sit in runs of 24 hours or more.
- 69% of factory-by-correlation-column pairs cannot exist because the factory does not monitor both sensors.
- In the test files, all sensors of a factory go missing at the same times (whole-logger outages).
- The test files have no quality codes.

None of this is a defect. It has to be handled in writing before any score is computed.

---

## B. Two row populations

| Population | Used for | Rule |
|---|---|---|
| **Injection-eligible** | Choosing where fake tampering is placed | See section C |
| **All real data** | Counting false alarms | Everything except missing rows (and, in dev only, rows tagged Error / Out of Range) |

- False alarms are counted on the **un-injected copy of all real data**, including natural repeat runs and natural gaps.
- The false-alarm rate is reported as an **upper bound**. Some alerts on real data may be genuine unknown tampering, and there is no way to tell.
- False alarms are also reported separately for rows inside natural repeat runs of 2 hours or more.

---

## C. Eligibility rules

**Series eligible for injection:** more than 10 distinct values, and at most 50% missing overall.

**Window eligible for injection:**
1. Every reading in the window is present and valid (not missing, not negative, pH within 0-14).
2. In dev, every row in the window has quality code Raw (or L). Test files have no codes, so all present rows are treated as Raw. This asymmetry is disclosed.
3. At least 70% of readings are present in the 7 days before the window.
4. The window does not overlap a natural exact-repeat run of 8 rows (2 hours) or more.
5. Flow windows for T1 and T2 must be entirely non-zero.

Events are placed up to the v1 target of 30 per factory per seed. If a factory has too few eligible windows, the shortfall is logged and reported.

---

## D. Which types apply where

| Type | Applies to | Notes |
|---|---|---|
| T1 Flatline | pH, BOD, COD, TSS, and Flow (non-zero windows only) | Reported by duration relative to natural repeat length (section E) |
| T2 Copy-paste | Same as T1 | |
| T3 Limit hugging | Series with a parsed consent limit | |
| T4 Impossible pH | pH series only | |
| T5 Correlation break | Factories with both BOD and COD present and enough overlapping coverage | |
| T6 Coordinated missing | Factories with 2 or more parameters | **Reported separately** (section F) |
| T7 Drift / dip | pH, BOD, COD, TSS (not Flow) | |

The number of eligible factories per type is reported in the paper, for dev and for test, together with the eligible-series counts.

---

## E. Flatline (T1) is reported against natural repeat length

- For each series, the **natural repeat length** is the 99.9th percentile of run lengths in that series' own un-injected data. This calibration is part of the method, uses no labels, and uses only that series' own un-injected readings.
- T1 results are split into two groups:
  - **Beyond natural:** injected duration is at least the series' natural repeat length. The v1 pass bars apply.
  - **Within natural:** injected duration is shorter. These are reported, with no pass or fail claim, and described as indistinguishable from normal behaviour in this data.
- Expected from the audit: the natural repeat length for pH, BOD, COD and TSS is roughly 20-40 hours, so most 1-12 hour flatlines fall within natural.
- Open question, to be answered by a later audit: whether long repeat runs are real sensor holds or copy-forward in the portal export. The paper states this as unresolved unless it is settled.

---

## F. Coordinated missing data (T6) is reported separately

- Natural outages in this data hit all sensors at once, so a simulated simultaneous gap cannot be told apart from a real outage.
- T6 is **excluded from the headline results and from the pass criteria**.
- It is reported in its own table, together with the statistics of natural simultaneous gaps (count, durations).
- No claim is made that gaps indicate tampering.

---

## G. Detector inputs

- The method uses **values and timestamps only**. It must not use quality codes, because the test files have none.
- In dev, rows tagged Error / Out of Range are dropped before the method runs (same as the production filter). In test, rows are used as given. Disclosed.
- Correlation-based features exist only for factories that monitor both sensors. Structurally undefined features are marked "not applicable". They are never filled with an average.

---

## H. Reporting levels

- **Dev:** results by type x severity x duration.
- **Locked test:** results by type and by type x severity only. At 4 factories x 150 events, the duration breakdown would be about 5 events per cell, which is too few.
- All intervals: 95% cluster bootstrap over factories, as in v1.

---

## I. Changelog

| Version | Date | Change | Reason |
|---|---|---|---|
| v1 | 2026-10-09 | Initial frozen protocol | n/a |
| v1.1 | 2026-10-09 | Two row populations, eligibility rules, per-type applicability, T1 split by natural repeat length, T6 reported separately, values-only inputs, test reporting levels | Step 1 audit findings. Added before any detector was built or evaluated |

# ForensiAIR Validation Protocol V2 (DRAFT)

**Status:** FROZEN (approved by the owner on 2026-10-11, before any V2 code was written). Commit it to `docs/PROTOCOL_v2.md` and tag `v2-protocol-frozen` together with the mechanism B code, before any model is trained.
**Scope:** development factories only. V1 and its locked-test result are untouched and remain the pre-registered result.

---

## 1. Claim under test

> On held-out development factories, a supervised model trained on simulated anomalies of mechanism A detects simulated anomalies of a different mechanism B at a fixed alert budget, and we report how this compares with V1's unsupervised and rule-based checks.

Not claimed: detection of real tampering, or any blind performance of V2. The four locked factories (Cipla, Glenmark, Indoco, Zydus) have been seen and are **not used in any way** (training, thresholds, model choice, or evaluation). V2 results are a post-hoc development-stage result.

The main number we will vouch for is the **generalisation gap**: recall on mechanism A (seen) minus recall on mechanism B (held out).

---

## 2. Three-part evaluation

| Part | What | Status |
|---|---|---|
| 1. Real clean telemetry | Per-sensor Isolation Forest (V1) trained on real dev data, false alarms on held-out clean copies | Done in V1 |
| 2. Supervised model, multiple mechanisms | Gradient-boosted classifier trained on mechanism-A events, tested on held-out factories with A and with B | New |
| 3. Held-out mechanism test | Train on B, test on A, as well (both directions) | New |

---

## 3. Mechanism catalog (frozen before training)

Mechanism A is the existing V1 injector (seeds 1-5 labels reused). Mechanism B is new and written without looking at any V2 results. Each B definition records its rationale in `docs/mechanism_sources.md` before training.

| Type | Mechanism A (V1) | Mechanism B (new) |
|---|---|---|
| T1 flatline | Hold value at window start, jitter 0/1/2 steps | Freeze at the series median, with rare single-step flickers (p per row) |
| T2 copy-paste | Block from 1-7 days earlier, noise 0/1/5% std | Scaled replay (x0.9-1.1) of a block 1-7 days earlier, plus splices of two different blocks, both 1-7 days back |
| T3 limit hugging | Uniform draw in 85-99% of limit | AR(1) hover around a level of 85-99% of limit, plus a partial pull of the real readings toward 95% of limit that keeps their own variation (strength sets the pull) |
| T7 drift / dip | Linear ramp down 15-50%, then return | Step offset with exponential relaxation, plus piecewise-linear up/down ramps |

**No-op events:** events where fewer than 50% of rows differ from the original are flagged `no_op`. They are excluded from training positives and from recall denominators, counted and reported separately (recall with them included is also shown).

Out of ML scope: **T4** (validity rule) and **T6** (gap detector) stay rules. **T5** is exploratory only (3 dev factories with BOD+COD) and makes no claims.

All B events follow the same eligibility rules as V1 (PROTOCOL_v1.1 section C), durations 4, 16, 48, 96, 288, 672 rows, 30 events per factory per seed, seeds 301-305, 3 strengths per mechanism defined from magnitude before training.

---

## 4. Features (past readings only)

For windows w in {16, 48, 96, 288} rows, per parameter:
- range, std, exact-repeat run length, unique-value count, fraction of unchanged steps
- level shift and slope against the prior 672 rows (robust z)
- minimum lagged similarity over lags of 1-7 days (scaled by series MAD)
- limit ratio and fraction above 85% of limit (NaN where no limit exists)
- missing fraction

Scale-dependent features are divided by an expanding past MAD (floor of one resolution step), and the parameter is a categorical feature. No quality codes. Structurally undefined features stay NaN (the gradient-boosted classifier handles NaN natively). V1 check scores are **not** features (avoids circularity).

---

## 5. Model and training

- Model: scikit-learn `HistGradientBoostingClassifier`, fixed parameters declared here: max_depth 6, learning_rate 0.1, max_iter 200, l2 1.0, class weights balanced. **No hyperparameter tuning.**
- Rows: positives are rows inside an event; rows within 2h after an event are dropped from training; negatives are rows from the clean (un-injected) copy, sampled at up to 20 negatives per positive, stratified by factory.
- Primary V2: one pooled model over all four types. Type-specialist models (T1+T2, T3, T7) are secondary diagnostics, each at its own cutoff and labelled not additive.
- Preprocessing fitted on training factories only.

---

## 6. Validation

- **Factory-grouped folds** over the dev factories: 5 folds, stratified so each fold has event-bearing factories.
- For each fold and each direction (train A / test B, train B / test A), test factories use both A and B events: **in-mechanism** (same as training) and **cross-mechanism** (held out).
- **Threshold rule (same for every method):** pool out-of-fold scores on clean dev copies, choose one global cutoff giving 1 alert per factory-month (episodes merge gaps up to 16 rows), apply to all events. V1 methods (M1, IF alone, F1, F2, F3, F6) and B0 random use the same rule on the same new events.
- Event matching and the 2h tolerance follow V1 (protocol section 5).

---

## 7. Metrics (cluster bootstrap over factories, 10,000 resamples, 95% CI)

- Event recall by type x mechanism x direction, in-mechanism vs cross-mechanism, and the **generalisation gap** with its own CI.
- Realised false alarms per factory-month (mean, median, max) and per-factory dispersion.
- Window-level AUPRC, median detection delay.
- Durations are reported in three bins (up to 16, 48-96, and 288+ rows), because six cells are too thin.
- Paired difference vs the best V1 comparator, per type, in the cross-mechanism direction.

**Pre-registered reading rules**
- V2 is "better" for a type only if the paired cross-mechanism difference has a CI excluding 0 **and** false alarms are not higher than the comparator.
- A large generalisation gap is reported as a result: it measures how much recall on injected patterns depends on how the injector builds them.

---

## 8. Integrity rules

1. Mechanism B code and this protocol are frozen and committed (git tag `v2-protocol-frozen`) before any model is trained.
2. Guards: fail if any feature or score column is 100% NaN where it applies; unit tests that injected rows differ from the originals and windows pass eligibility.
3. No tuning after seeing results. Any change creates V2.1 with the reason logged in the changelog.
4. Locked factories are not read. Training labels never come from real data, only from the simulated events.
5. Every artifact in the paper carries the label "development result, post-hoc".

---

## 9. What this can and cannot support

**Can:** a measured comparison of supervised vs unsupervised vs rule-based detection of four simulated pattern types, with the cost of changing the simulation mechanism.
**Cannot:** real-tampering detection, blind performance of V2, or performance on factories outside the development set.

---

## 10. Plan and open items

| Stage | Work |
|---|---|
| 0 | Approve and freeze this protocol |
| 1 | Mechanism B injector, tests, labels (seeds 301-305) |
| 2 | Feature pipeline and model, with guards |
| 3 | Grouped CV, all comparisons, tables |
| 4 | Analysis and write-up |

Open before freezing: negative-to-positive ratio (default 20:1), whether T1+T2 share one model (default yes), and the exact magnitudes for B strengths (to be fixed in `docs/mechanism_sources.md`).

---

## 11. Changelog

| Version | Date | Change | Reason |
|---|---|---|---|
| V2 draft | 2026-10-11 | Initial draft | Owner chose a three-part evaluation after V1 |
| V2 | 2026-10-11 | Pre-freeze consistency changes: T2 mechanism B lags set to 1-7 days (V2 features look back 1-7 days); `no_op` rule added; pooled model is primary and specialists are diagnostics; scale normalisation and parameter feature added; duration reported in three bins | Found while reviewing Stage 1 output, before any V2 model was trained |
| V2 | 2026-10-11 | Approved by owner. T3 mechanism B changed from "soft cap" to "AR(1) hover plus partial pull toward 95% of limit" | A soft cap would leave most windows unchanged, because typical readings sit well below 90% of the limit. Changed before any V2 code was written |

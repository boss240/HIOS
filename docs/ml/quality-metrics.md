# Forecast quality metrics

Related issue: #10. Sources: HEDS-012 ACC-001–010, CONF-001–008, LIM-007;
HEDS-010 MLMON-001–010; HEDS-018 TESTTYP-007.
[Source coverage](../../sprint-02/SOURCES.md).

## Definitions for the first evaluation

For eligible paired hourly average AC power values, y is measured kW,
p is forecast kW, e = p - y, and N is the number of eligible pairs.
All inputs must be finite. No eligible pairs means "not evaluated", never zero error.

| Source metric | Formula / reporting rule |
| --- | --- |
| ACC-001 MAE | sum(abs(e))/N, kW |
| ACC-002 MAPE | 100 * mean(abs(e)/abs(y)) only on daylight pairs with y > epsilon_kw |
| ACC-003 RMSE | sqrt(sum(e²)/N), kW |
| ACC-004 Bias | sum(e)/N, kW; positive means over-forecast |
| ACC-005 nMAE | 100 * MAE / rated_AC_kw; positive finite AC rating required |
| ACC-006 Daylight accuracy | Same metrics using solar-elevation > 0 at interval midpoint; report mask/version |
| ACC-007 Peak-window accuracy | Predeclare a plant-local time/solar window; do not choose it after observing errors |
| ACC-008 Availability | 100 * usable runs published by deadline / expected scheduled runs |
| ACC-009 Input readiness | 100 * ready input bundles / expected scheduled jobs |
| ACC-010 Confidence calibration | Empirical interval coverage and width by horizon; unavailable until bands exist |

Sprint 2 proposal: epsilon_kw = 1% of rated AC capacity for MAPE screening.
Record epsilon and excluded counts; this is a denominator convention, not an
accuracy acceptance threshold. No MAPE when all samples fall below epsilon.
For energy scoring use kWh for both sides and normalize by AC kW * interval hours.
Do not average unequal-duration power intervals as energy.

Availability counts logical runs, not retries; include blocked/missing runs in
the expected denominator. Report normal, degraded, late and missing separately.
A reused stale forecast is not a newly published on-time run. Zero expected jobs
gives "not applicable". Freeze the scheduling/deadline definition before scoring.

The implemented operational read model reports recorded worker outcomes and
published-point counts for a tenant/plant UTC window. It intentionally does not
present this as ACC-008 availability: expected scheduled runs and the deadline
are unresolved operational decisions.

`app/forecast_evaluation.py` implements ACC-001–005 calculation semantics for
paired AC-power fixtures: MAE, RMSE, signed bias, daylight MAPE above the stated
epsilon, and nMAE using a positive AC rating. Zero pairs return explicit
not-evaluated values; they are never reported as zero error. It persists no
actuals, sets no release threshold and cannot establish field accuracy.

`app/actuals_alignment.py` prepares reproducible exact-interval AC-power pairs
from persisted forecast points and actual snapshots. An evaluation caller still
must provide the daylight mask, target exclusions, frozen cutoff and approved
policy; pairing alone cannot claim accuracy.

## Evaluation protocol and thresholds

Report plant, horizon, provider, season/weather regime, sample period and model
version. Publish both overall and daylight metrics; show outage/curtailment
segments and all exclusion counts. Evaluate baseline and candidate on the same
eligible targets with matching as-of inputs. Include scheduled target coverage so
a model cannot look better by failing difficult intervals. Portfolio reports show
both per-plant results and explicitly weighted aggregates.

No source gives numeric production MAE, RMSE or bias limits. Before evaluating a
release candidate, ML/QA/Product must approve a versioned threshold record with
dataset/split hashes, plants, horizons, minimum sample count/coverage, MAE/nMAE/RMSE,
absolute bias limits, baseline comparison, availability deadline/target,
confidence-calibration criteria and permitted exclusions.
Unset criteria block quality acceptance; this PR sets no fabricated target.

`app/forecast_release_gate.py` provides a fail-closed policy contract for the
later decision. A caller must provide an explicitly approved, versioned policy
with a decision reference, minimum pair count and coverage, and MAE/RMSE/absolute
bias/nMAE limits. The gate returns reasons for rejection; it does not create an
approval, persist an evaluation, promote a model or claim field accuracy.

ML Ops produces daily availability/error/bias/blocked-job reports and weekly
provider/drift reviews (FREP-001–005). Numeric drift triggers require calibration.
A trigger starts investigation/retraining review; it never auto-promotes a model.

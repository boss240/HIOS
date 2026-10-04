# Chronological blend evaluation

`app.ensemble_holdout.evaluate_holdout` fits a per-plant inverse-MAE blend only
on the training portion, then compares those frozen weights with an explicit
baseline provider on later comparable daylight hours.

Inputs are `RecordedPair` values wrapping validated as-issued AC-power pairs
and the time their actual evidence became available. Training target hours must
be closed and their actuals available at the training cutoff. Holdout forecast
origins must follow that cutoff, with closed target hours and actuals available
by analysis time. Shared-hour source, daylight, quality and horizon gates remain
those of `score_as_issued`. Training and holdout provider sets must match.

The caller must validate tenant/plant ownership, immutable forecast lineage and
compatible AC metering scope before constructing pairs. Device PV kWh or raw
weather radiation must not be passed as AC kW. The helper does no database reads
and cannot independently establish those source properties.

Results include training and held-out hour counts, exclusions, fixed weights,
baseline and blend MAE/bias, and relative MAE improvement. Improvement is unknown
when baseline MAE is zero; deterioration is negative. Insufficient evidence
raises an error instead of reporting a success percentage. Default minimums are
24 eligible hours in each partition; these counts are configuration policy and
do not constitute commercial acceptance or statistical confidence.

The output always remains `publication=not_approved` and
`licenceEligibility=not_assessed`. Production approval needs multiple independent
days and lead-time ranges, source coverage, compatible installed plant data,
and the project's separate acceptance process. The pure evaluator does not
publish forecasts, change production weights, or approve sale eligibility.

Current pilot archives do not yet supply eligible AC forecast/fact pairs, so
the local tests establish algorithm behavior only, not real plant accuracy.

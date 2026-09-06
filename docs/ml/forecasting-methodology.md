# Forecasting methodology

Related issue: #10. Source: HEDS-012 §§3–10, FH-001–006, METH-001–012;
HEDS-010 MODEL-001. [Source coverage](../../sprint-02/SOURCES.md).

## Target and horizons

Sprint 2 proposal: forecast interval-average AC generation power in kW at a
documented plant measurement boundary. Energy is power multiplied by interval
duration in hours, in kWh. Never compare kW with kWh or DC rating with AC output.

| HEDS horizon | Source range / granularity | Sprint 2 treatment |
| --- | --- | --- |
| FH-001 nowcast | 0–2h; 5/15/60min | Deferred until telemetry is available |
| FH-002 intraday | 2–24h; 15/60min | Specify hourly; execution follows input readiness |
| FH-003 day-ahead | 24–48h; 60min | First implementation slice |
| FH-004 week-ahead | 2–7d; hourly/daily | Deferred |
| FH-005 month-ahead | 8–31d; daily | Indicative planning only, deferred |
| FH-006 historical reconstruction | Past; 15/60min | Isolated backtest/backfill |

Proposal: an hourly UTC forecast origin t0 anchors half-open target intervals.
Intraday covers [t0+2h,t0+24h), 22 hourly points; day-ahead covers
[t0+24h,t0+48h), 24 hourly points. Store t0 separately from execution completion.
A customer calendar-day product requires a separate timezone/cutoff decision;
a local DST day can contain 23 or 25 hours and must not be forced to 24.

## MODEL-001 baseline proposal

Start with a deterministic physical/statistical model, pinned as a candidate.
Use solar position, weather irradiance and plant metadata to derive plane-of-array
irradiance, module-temperature correction, DC output, conversion losses and AC
inverter clipping. Choose and document the physical library, coefficients and
equipment assumptions during implementation; GHI is not automatically panel-plane
irradiance. Cloud cover informs uncertainty or an explicitly evaluated alternative,
not an undocumented multiplier applied twice to provider irradiance.

Require positive finite DC capacity, separate positive AC inverter capacity,
coordinates, timezone and weather time/units. Existing API capacityKw is DC kWp
under ADR-0001; it must not become an AC cap. Zero/unknown capacity may be valid
in the asset registry but blocks this model. Missing orientation/tilt or module
parameters requires an explicit versioned assumption and reduced quality.
Historical calibration and recent-error correction are evaluated independently;
a no-history cold-start model is visibly uncalibrated (LIM-004).

METH-001–005: validate inputs, compute solar context, normalize weather,
temperature-correct and enforce 0 <= predicted power <= AC inverter capacity.
Night-time output is zero only after solar context is validated. Missing inputs
are never represented as zero generation. Outage and curtailment records define
separate constrained-output scenarios; retain the unconstrained forecast and flags.

METH-006–012: calibrate on past actuals, compare corrections against the baseline,
route provider failures, attach quality, persist immutable provenance, evaluate
after actuals arrive, and review drift/retraining. These are planned runtime
stages, not implementations in this documentation change.

## Output proposal

Each run records tenant_id, plant_id, run_id, forecast_origin_utc, generated_at_utc,
horizon_id, model_id/version, code_commit, feature_version, plant_snapshot_ref,
weather_snapshot_refs, configuration_hash and status.
Each point records interval_start_utc, interval_end_utc, predicted_power_kw,
predicted_energy_kwh, quality_flags and provider provenance. Forecast revisions
create new run IDs; retries with the same logical key must be idempotent.
Valid statuses: normal, degraded, blocked. Blocked runs publish no numeric series.

Quality factors cover HEDS CONF-001–008: completeness, provider quality, horizon,
recent error, drift, metadata, operational constraints and model maturity.
Use categorical flags initially. Probability bands or numeric confidence require
[calibration evidence](quality-metrics.md), not invented percentages.

## Limitations and release boundary

Weather uncertainty, sparse history, shading/snow/dust, outages, provider divergence
and plant metadata errors remain visible (LIM-001–008). No production release
until [acceptance gates](../../sprint-02/ACCEPTANCE.md) and evaluation pass.

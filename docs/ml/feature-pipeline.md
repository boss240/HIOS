# Feature pipeline

Related issue: #10. Sources: HEDS-010 MLOP-001–012, FEAT-001–014;
HEDS-011 NORM-001–010; HEDS-012 METH-001–012.
[Source coverage](../../sprint-02/SOURCES.md).

## Proposed stages and contracts

| Stage | Required behavior | Output / owner |
| --- | --- | --- |
| Resolve asset | Validate tenant ownership and effective plant version | Plant snapshot; Backend/Data |
| Retrieve weather | Bounded requests; record issue and retrieval times | Immutable payload; Data Ops |
| Normalize | Explicit units, UTC, intervals, provider mapping | Weather snapshot; Data Engineering |
| Validate readiness | Finite/range checks, coverage, TTL and metadata | Ready/degraded/blocked with reasons |
| Build features | Time-safe joins; feature schema version | Immutable feature bundle; ML Engineering |
| Run baseline | Pin registry/config/code versions | Candidate output; ML Engineering |
| Postprocess | AC bounds, solar-night rules, quality/provenance | Validated points |
| Persist/publish | Atomic run/points; tenant-bound idempotency | Run record; Backend |
| Evaluate | Align observed actuals by measurement boundary/interval | Quality report; ML Ops |

Batch execution is the first proposal within the existing Python modular monolith.
No separate feature-store service or streaming platform is needed for the first
slice. A scheduler and worker remain to be implemented with bounded concurrency.

## Implemented MODEL-001 feature assembly

`app/feature_assembly.py` provides `model-001-features-v1`. It takes a
normalized as-issued weather interval and explicit plant latitude, longitude,
tilt, surface azimuth and ground albedo. It calculates a deterministic candidate
solar context at the interval midpoint, then uses DNI, DHI and GHI in an
isotropic transposition equation to create POA irradiance for MODEL-001. It
requires both DNI and DHI: no hidden decomposition or substitution from GHI is
used. A night context yields zero POA only after the solar calculation.

The weather issue and retrieval times must be no later than the forecast origin.
The compact solar calculation is a versioned baseline coefficient set, not a
validated replacement for an approved solar library. Feature persistence,
snapshot selection, effective plant-metadata versioning and scientific
validation/calibration remain open before activation.

## Feature coverage

FEAT-001–004: normalized irradiance, cloud, temperature and wind.
FEAT-005–007: separate DC and AC capacity, coordinates, orientation/tilt.
FEAT-008: lagged actuals; FEAT-009–010: local time and season derived from UTC
plus IANA timezone. FEAT-011 special calendar days is deferred.
FEAT-012 provider quality, FEAT-013 recent errors and FEAT-014 missing flags
carry their own availability timestamp and schema version.

## Prevent leakage and incorrect alignment

For operational replay, both source issue/event time and availability/ingestion
time must be <= forecast_origin_utc. Select the latest eligible provider version,
not the latest version available today. Actuals, corrections, metadata revisions,
quality scores and lag features obey the same as-of rule.
Fit normalization/calibration only on the training split. Archive forecasts as
issued; reanalysis can support research but cannot prove live forecast accuracy.

Store intervals as [start,end) UTC with explicit average-power or interval-energy
semantics. Derive local display/calendar features using the plant timezone,
including repeated/missing DST hours. Align actuals only after resolving meter
units, duration, duplicates, revisions, outages and curtailment. Missing != zero.

## Persistence and security proposal

Logical key: tenant + plant + origin + horizon + model version + input/config hash.
Retries return the same completed run; changed inputs create a new revision.
Persist run and points atomically; failed runs cannot replace the latest usable
forecast. Retain source issue/retrieval times and per-point fallback provenance.

The existing database creates only tenants, memberships and plants. New forecast,
weather, actuals and metadata tables require forward migrations with composite
tenant ownership constraints. Every read/write/job must verify tenant/plant scope;
never accept an arbitrary client tenant override. Add two-tenant read/write/replay
tests before enabling ingestion or publication. See
[ADR-0001](../architecture/adr/0001-sprint-1-runtime.md) and
[retention](../data/retention-policy.md).

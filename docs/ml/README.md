# ML and forecasting — Sprint 2

Related issue: #10 (EPIC-005); milestone: M3 Forecasting MVP.
Sources: HEDS-010, HEDS-011, HEDS-012, HEDS-018, HEDS-022, HEDS-023,
v0.1.0-UA. See [source evidence and coverage](../../sprint-02/SOURCES.md).

Status: documentation foundation and controlled runtime components are implemented
through PR #37. MODEL-001, persistence, weather normalization/failover, worker
leases/outcomes and fixture evaluation exist; provider integration, field accuracy
and operational acceptance remain pending. See the [package overview](../../SPRINT_02_README.md).
Sprint 1's implemented API, database, authentication and migrations are reused.

## Canonical documents

- [Forecasting methodology](forecasting-methodology.md): target, horizons, bounds and limitations.
- [Weather provider assumptions](weather-provider-assumptions.md): roles, fields, provenance and decisions.
- [Model registry](model-registry.md): immutable versions, lifecycle and promotion.
- [Feature pipeline](feature-pipeline.md): time-safe inputs and tenant boundaries.
- [Quality metrics](quality-metrics.md): denominators, segments and release criteria.
- [ML operations checklist](ml-operations-checklist.md): monitoring, rollback and ownership.
- [Provider failover](provider-failover.md): outage, quota, staleness and recovery.
- [Forecast validation](forecast-validation.md): reproducible evaluation and test cases.
- [Sprint 2 acceptance checklist](sprint-02-acceptance-checklist.md): gate review entry point.
- [Sprint plan](../../sprint-02/README.md), [acceptance](../../sprint-02/ACCEPTANCE.md)
  and [status](../../sprint-02/STATUS.md).

Legacy paths remain as navigation aliases, avoiding two competing specifications:
[weather integration](weather-provider-integration.md),
[ML ops](ml-ops-checklist.md), [forecast QA](forecast-quality-qa.md).

## Decision boundary

HEDS source requirements are cited by document and item ID. Choices explicitly
marked "Sprint 2 proposal" are implementation proposals, not source mandates.
Provider roles in HEDS are generic: no supplier or commercial agreement is selected.
No accuracy, confidence calibration, operational SLA or final acceptance is claimed.

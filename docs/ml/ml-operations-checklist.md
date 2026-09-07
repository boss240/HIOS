# ML operations checklist

Related issue: #10. Sources: HEDS-010 MLOP-001–012, DEP-001–008,
MLMON-001–010, DRIFT-001–008, RET-001–008, MLI-001–008, AUD-ML-001–012;
HEDS-023 acceptance_checks and signoff.
[Source coverage](../../sprint-02/SOURCES.md).

Unchecked items are runtime gates, not evidence of completion.

## Before implementation demo — ML/Data Engineering

- [ ] Pin dataset, feature, code and configuration versions and hashes.
- [ ] Validate weather/plant units, tenant scope, intervals and as-of timestamps.
- [ ] Record deterministic baseline assumptions and cold-start limitations.
- [ ] Produce reproducible forecast-vs-actual metrics with exclusion counts.
- [ ] Link test results and run lineage in the model registry.

## Before staging / production — ML Ops, QA and SRE

- [ ] Register candidate artifact, evaluation report and dependency environment.
- [ ] Approve numeric accuracy/coverage/deadline gates before held-out scoring.
- [ ] Complete shadow comparison and canary plan where feasible.
- [ ] Verify previous stable version rollback, or approved initial stop-publication.
- [ ] Exercise provider timeout, 429, schema drift, stale data and all-provider outage.
- [ ] Verify tenant isolation for ingestion, publication, evaluation and exports.
- [ ] Assign named owners, incident routing, credential scope and rotation process.
- [ ] Review retention, provider usage rights and restore evidence.
- [ ] Record environment-specific approval and scoped sign-off.

## Operations — ML Ops / Data Ops / SRE

- [ ] Define expected jobs, timezone, deadlines, retry limits and concurrency.
- [ ] Monitor readiness, model-load failures, latency, errors, bias and availability.
- [ ] Review provider coverage/freshness/divergence/cost and fallback frequency.
- [ ] Review input/error/profile/metadata drift; record thresholds and review outcome.
- [ ] Handle scheduled, provider-change, new-cohort, metadata, season and incident
      retraining triggers; retain reasons even when deciding not to retrain.
- [ ] Prevent unapproved model usage; audit deployment and retirement.
- [ ] Require owner, reason, scope, approval and expiry for manual overrides.

## Implemented scheduling primitives

`app/forecast_schedule.py` calculates due origins on explicit UTC cadence and
publication delay. Migration 0005 creates a tenant/plant/origin/horizon lease;
only active members of the plant tenant can claim, renew or release it. A future
worker must claim the lease before invoking the controlled forecast job and use a
bounded TTL appropriate to the job deadline. This code does not start a scheduler,
define production cadence/owners, provide distributed metrics or replace staging
load/deadline evidence.

## Implemented controlled worker wrapper

`app/forecast_worker.py` wraps one invocation of the controlled MODEL-001 job.
It claims a lease, writes a minimal `running` outcome, executes the job, records
only `succeeded`/`failed`, run ID, point count or exception class, and releases
the lease in `finally`. It intentionally stores no provider payload, credential
or exception message. A non-holder returns `not_acquired` and does not create a
second outcome. Worker supervision, retries, monitoring, alert routing and a
production scheduler remain separate operational work.

Failure-path coverage verifies that a rejected unapproved model records only a
`failed`/`PermissionError` outcome and still releases its lease.

`app/forecast_operations.py` provides a tenant/plant-scoped, read-only summary
of recorded successful, failed and running attempts plus published point count
within an explicit UTC time window. It does not calculate availability or SLA:
those require an approved expected-schedule and deadline definition.

## Incident and rollback procedure

1. Identify impacted tenants/plants, origins, model/input versions and last good run.
2. Stop affected publication for incomplete features or unapproved model versions.
3. Route provider faults via [failover](provider-failover.md); model faults use
   the tested previous approved version with compatible features/configuration.
4. Record actor/reason/time, verify health and run a bounded shadow forecast.
5. Resume only after bounds, lineage and quality checks pass; keep bad runs
   immutable and label replacements. Preserve evidence and a corrective issue.

Training, approval, artifact, deployment, lineage, drift, retraining, incident,
override and retirement evidence follow AUD-ML-001–012.
See [acceptance](../../sprint-02/ACCEPTANCE.md) for sign-off; CI does not sign it.

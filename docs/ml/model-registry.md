# Model registry

Related issue: #10. Source: HEDS-010 MODEL-001–008, DEP-001–008,
AUD-ML-001–012. [Source coverage](../../sprint-02/SOURCES.md).

## Candidate inventory

| Source ID | Role | Current implementation status |
| --- | --- | --- |
| MODEL-001 | Physical/statistical baseline and benchmark | Deterministic untrained candidate implemented; no artifact, calibration or active version |
| MODEL-002 / MODEL-004 | Recent-error correction / plant calibration | Planned after actuals |
| MODEL-003 | Provider ensemble | Deferred; explicit routing first |
| MODEL-005 | Regional model | Deferred |
| MODEL-006 / MODEL-007 | Anomaly / drift monitoring | Rules specified; no deployed model |
| MODEL-008 | Experimental candidate | Reserved for isolated experiments |

These source catalogue entries do not mean eight trained models exist.

## Immutable registry record proposal

Record model_id, model_version, model_type, environment, owner, artifact_uri,
artifact_sha256, code_commit, dependency_lock_ref, configuration_hash,
feature_schema_version, training_dataset_ref/hash (or explicit not-applicable
for an untrained deterministic model), evaluation_dataset_ref/hash,
plant/provider scope, horizons, units, evaluation_report_ref, metrics and limitations.
Each transition also records actor, timestamp, reason, evidence and previous state.
Approval requires approved_by, approved_at, decision_ref, conditions and
rollback_model_version. Never replace an artifact under an existing version.

Lifecycle: proposed -> candidate -> approved -> active -> deprecated -> retired.
Rejected candidates stay recorded with reasons. Approval is environment/scope
specific; staging approval is not production approval. Only an approved version
may become active. Model activation is atomic per scope, with concurrency control;
each forecast pins the resolved version before execution.

DEP-001–008 require approval evidence, shadow comparison, canary where feasible,
tested rollback, version pinning, separated environments, expiring overrides and
deployment evidence. Initial production activation has no previous stable model:
validate stop-publication as its rollback and explicitly approve that first-release
exception; never invent a rollback version.

## Storage and promotion gates

Sprint 2 now implements immutable PostgreSQL candidate metadata per tenant/plant
through migration 0004 and `app/model_registry.py`. An active tenant member can
register a candidate exactly once; selecting a candidate returns only a recorded
approved version for that tenant/plant. Candidate registration cannot mutate an
existing version. Promotion, approval authorization, activation, artifact storage
and rollback workflows remain separate gates. The initial
`app/model_001.py` candidate uses explicit DC/AC capacities, a versioned
performance ratio and temperature coefficient, plane-of-array irradiance, and
validated solar elevation. It enforces an AC bound and reports night/clipping
flags; it does not select features, calculate solar position, train, calibrate
or become active without the registry/promotion evidence above.

Promotion requires [validation](forecast-validation.md), [acceptance](../../sprint-02/ACCEPTANCE.md),
known-issue review and operational ownership. Pin all code/config/feature/input
versions (AUD-ML-007). Retirement checks dependencies and retains evidence.
Manual overrides require reason, narrow scope, owner, approval and expiry.

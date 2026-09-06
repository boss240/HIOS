# Forecast validation

Related issue: #10. Sources: HEDS-012 METH-011, ACC-001–010, LIM-001–008;
HEDS-018 TESTTYP-001–003/006–010, QAGATES-001–010;
HEDS-023 acceptance_checks. [Source coverage](../../sprint-02/SOURCES.md).

## Reproducible evaluation

1. Freeze plant scope, measurement boundary, interval, horizon, cutoff, provider
   versions, dataset/hash, target exclusions and [threshold record](quality-metrics.md).
2. Use chronological train/validation/held-out test partitions. No random time
   split. Fit transformations on training only; lock tuning before held-out scoring.
3. Replay archived forecasts available at each origin. Historical reanalysis and
   observations are separately labeled and cannot prove operational accuracy.
4. Align actuals by tenant, plant and exact UTC interval; handle revisions and
   late arrivals with versioned evaluation runs.
5. Compare MODEL-001 and candidates on common targets, and report missing/blocked
   coverage separately. Show both all-interval and daylight metrics, outage and
   curtailment segments, provider/horizon/season breakdowns and sample counts.
6. Store commands, environment, source/config/model hashes, metrics, QA results,
   exclusions, known issues and review decision. Synthetic fixtures prove behavior,
   not real-world accuracy.

## Required runtime test matrix

| Test ID | Scenario and expected result | HEDS anchor | Gate |
| --- | --- | --- | --- |
| S2-T01 | Unit conversions, power-to-energy and interval aggregation agree with hand calculations | HEDS-011 NORM-002/004 | Unit |
| S2-T02 | Naive times, DST repeated/missing hours, unordered/duplicate intervals handled explicitly | HEDS-011 NORM-001/004 | Unit/integration |
| S2-T03 | Future issue/retrieval times and future actual/metadata revisions excluded from features | HEDS-010 MLOP-001/002 | Leakage |
| S2-T04 | Missing critical data, NaN/Infinity, invalid units/capacity block run, never become zeros | HEDS-012 METH-001/005 | Data quality |
| S2-T05 | Solar night yields zero; AC clipping enforced separately from DC rating | HEDS-012 METH-002/005 | Unit |
| S2-T06 | 429/timeout/5xx respect budget; circuit recovery and schema/auth failure tested | HEDS-011 FB-001/002, WPI-006 | Integration |
| S2-T07 | Partial secondary fill keeps provenance; all-source outage blocks or uses bounded stale run | HEDS-011 FB-003/007 | Integration |
| S2-T08 | Idempotent retry, concurrent jobs and failed persistence never duplicate/partially publish | HEDS-012 METH-010 | Database; idempotency and lease primitives covered, failed-persistence recovery remains |
| S2-T09 | Forged tenant/foreign plant access, cross-tenant jobs and exports denied | HEDS-018 TESTTYP-008 | Security |
| S2-T10 | Exact MAE/RMSE/bias; zero-N, low-output MAPE and coverage denominators | HEDS-012 ACC-001–009 | Evaluation |
| S2-T11 | Unapproved model rejected; rollback preserves versions and feature compatibility | HEDS-010 DEP-001/004/005 | Release |
| S2-T12 | Frozen historical holdout meets approved targets, calibrated bands only if supported | HEDS-012 ACC-010 | ML QA |
| S2-T13 | Load/deadline, monitoring and backup/restore evidence for forecast storage | HEDS-023 ACCEPTA-004–006 | Operations |

All S2-T cases are planned, not executed by this documentation PR.
Existing Sprint 1 integration tests still validate the current API and PostgreSQL.

## CI and acceptance distinction

Run `python scripts/check_forecasting_docs.py` for required documents, local links,
and source-manifest/coverage integrity. Existing OpenAPI and runtime checks remain
mandatory. A green document check does not execute S2-T01–13 or validate accuracy.
Progress through PR QA, staging, data/ML QA, release candidate, security/performance,
acceptance, rollback readiness and post-release smoke only with recorded evidence.
See the [gate ledger](../../sprint-02/ACCEPTANCE.md).

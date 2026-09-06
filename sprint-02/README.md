# Sprint 2 — Forecasting MVP

Sprint issue: [#22](https://github.com/boss240/HIOS/issues/22).
Related epic: #10 EPIC-005; milestone M3 Forecasting MVP.
Sources: HEDS-010/011/012/018/022/023; [coverage](SOURCES.md).
Status: In Progress; documentation baseline for review, forecasting runtime pending.

## Objective and reuse

Deliver a traceable first day-ahead baseline, then intraday forecasting, backed by
weather inputs, plant metadata and measured actuals. This initial change defines
the implementation contracts and gates and repairs an inherited API CI regression.
Reuse Sprint 1 FastAPI/Python 3.11, PostgreSQL 17, JWT tenant membership, migration
runner and runtime tests. #5/#6/#7/#8/#16/#18/#19 are closed and Done on Project 3.
Do not reopen or duplicate them. Duplicate EPIC-005 #9 stays closed; #10 is canonical.

[ML entry point](../docs/ml/README.md) contains the nine requested documents.
[Acceptance ledger](ACCEPTANCE.md) separates documentation readiness from MVP release.

## Work packages and dependencies

| ID | Deliverable | Role owner | Dependency / evidence |
| --- | --- | --- | --- |
| S2-01 | Source mapping, contracts, decisions, CI baseline | Engineering / QA | This PR; source hashes and green CI |
| S2-02 | Real plant/actual sample and archived as-issued weather; measurement contract | Data Engineer / Product | Provider rights, AC/DC/coordinates/timezone and actuals |
| S2-03 | Weather adapter, normalization and bounded failover | Data Engineer | Normalizer, tenant-safe snapshot persistence and bounded primary-to-secondary policy implemented; vendor adapter, credentials/quotas/TTL and S2-T06–07 remain |
| S2-04 | Forward migrations and tenant-safe run persistence | Backend Lead | Migration 0002 plus tenant-safe, idempotent run and immutable point publication primitives; job orchestration remains |
| S2-05 | MODEL-001 candidate and calibration | ML Engineer | S2-02/03/04; immutable registry, S2-T03–05/11 |
| S2-06 | Evaluation and approved release thresholds | ML Engineer / QA Lead | Frozen split before candidate scoring; S2-T10/12 |
| S2-07 | Scheduled worker, operational monitoring, staging demo and acceptance | SRE / QA / Product | S2-03–06; S2-T13, rollback and sign-off |

Roles are proposed responsibilities; named assignees are not fabricated.
Forecast API routes follow a separate tested contract addition after S2-04/05.
The uploaded placeholder forecast route has no runtime implementation and is not
advertised by the restored live API specification.

## Suggested calendar

Kickoff: 2026-09-06. Proposed review checkpoints, not a committed delivery promise:
2026-09-07 review S2-01 and assign owners; 2026-09-08 resolve S2-02 data/provider
decisions; 2026-09-09–11 adapter/storage implementation; 2026-09-14–16 baseline
and evaluation; 2026-09-17–18 staging/failover demo and gate review.
If dependencies arrive later, rebaseline dates in the tracking issue.
Report weekly status, risks, decisions, QA links and next actions (HEDS-022 reporting).

## Local checks

Run from repository root in Python 3.11 with requirements-ci.txt installed:

```sh
python -m openapi_spec_validator docs/api/openapi.yaml
python scripts/check_api_contract.py
python scripts/check_forecasting_docs.py
```

Runtime tests require requirements-test.txt and a disposable PostgreSQL 17 database
via TEST_DATABASE_URL; GitHub Runtime integration provisions that database.
No provider secrets or paid network requests are needed for this baseline.

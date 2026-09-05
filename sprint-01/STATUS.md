# Sprint 1 Status

Date: 2026-09-05
Status: Implementation delivered; technical acceptance and CI evidence tracked in #18/#19.

## Delivered scope

- PR #20 merged as ab66700: normalized all eight requested baseline files and added static contract validation.
- PR #21: FastAPI/Uvicorn read-only API, PostgreSQL 17, transactional SQL migrations,
  RS256 JWT validation and active database membership before tenant-filtered queries.
- GET /health, GET /plants and canonical /openapi.json implemented. Pagination,
  finite DC capacity, safe errors and request correlation are defined and tested.
- ADR-0001 accepts the delegated runtime/database/auth decisions. Engineering
  retention defaults: weather 90d, forecast 730d, audit 365d, logs 30d, backups 35d.
- Main protection configured: strict CI, one approval, stale approval dismissal,
  resolved conversations, no force pushes/deletion. Sole-owner admin exception is
  explicit in docs/qa/review-policy.md; no independent peer approval is claimed.

## Evidence

PR #21's checks and #19 identify the exact reviewed commit and completed CI runs.
The initial Runtime integration run 33977658735 passed 31 tests on PostgreSQL 17.
The final suite also checks a real Uvicorn TCP server and migration checksum drift.
JUnit artifacts are uploaded by the runtime workflow. Local Docker could not start;
GitHub's PostgreSQL service supplies the database evidence.

## Acceptance boundary

Sprint 1 is the API/data foundation, not a production release. Technical review is
performed by Codex under the owner's explicit delegated instruction. #18 records
the final scoped acceptance outcome after CI and merge; #19 tracks closure.
Phase 1 Acceptance remains in QA until later epic delivery and release evidence.

## Later release work

Production hosting/TLS, identity-system provisioning and automated key rotation,
backup restore drills, monitoring, forecast workers and retention purge jobs belong
to subsequent deployment/domain work. No production service or automatic purge
is created by Sprint 1. These are not unselected Sprint 1 architecture decisions.

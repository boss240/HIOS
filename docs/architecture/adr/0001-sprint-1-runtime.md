# ADR-0001: Sprint 1 runtime, data and access foundation

Status: Accepted for Sprint 1 implementation
Date: 2026-09-05
Owner: boss240 (implementation delegated to Codex)
Related issues: #5, #6, #7, #8, #16, #19
Authorization: owner requested runtime/database/auth/retention decisions and implementation.
Evidence: the runtime PR linked to #19 and its Runtime integration CI run.
Supersedes: open Sprint 1 runtime/database/auth decisions in earlier skeleton docs.

## Context and decision

Use a Python 3.11 modular monolith with FastAPI and Uvicorn. Keep HTTP, migration
and persistence code in explicit modules; no service mesh or queue is needed for
read-only liveness and plant listing. Forecast workers remain a later epic.

Use PostgreSQL 17 and psycopg 3. Ordered SQL migrations in migrations/ run in one
transaction, serialize concurrent runners with an advisory lock, and verify
SHA-256 of applied files. The first migration creates tenants, memberships and
plants with required ownership, nonnegative finite capacity and a tenant/ID index.
Use forward corrective migrations; restore from a verified backup for destructive
rollback. Do not edit applied migrations. API startup never performs migrations.

Authenticate RS256 JWTs using a configured RSA public key (minimum 2048 bits).
Require exp, iat, iss, aud and nonempty sub; verify signature, algorithm, issuer,
audience and timestamps. Resolve tenant only from signed tenant_id and an active
(subject, tenant) membership in PostgreSQL. Re-check membership on every request
so revocation does not wait for token expiry. Headers/query parameters cannot
override tenant context. Missing identity returns 401; absent/forbidden tenant
returns 403. No token issuing or registration endpoint is supplied.

Tenant isolation in this slice is application-enforced: one SQL statement checks
membership and filters plants before stable pagination, in the same snapshot.
Use a SELECT-only runtime database role and a separate migration role. This is
not PostgreSQL row-level security; direct privileged SQL is outside this boundary.
Future write endpoints require equivalent ownership checks and dedicated tests.

## Retention decision

Adopt the engineering defaults in [retention policy](../../data/retention-policy.md):
weather raw inputs 90 days, forecast outputs 730 days, audit events 365 days,
operational logs 30 days and backups 35 days. These are configurable operating
defaults, not a statement of legal compliance or provider licensing rights.
No deletion job runs in Sprint 1 because these data domains are not yet implemented.

## Alternatives and consequences

SQLite would not test the target multiuser relational database. Separate services
would add deployment and operational work before useful boundaries are exercised.
Alembic can replace the small SQL runner when ORM metadata and branching migrations
become necessary; no ORM is needed for this read-only slice.
A managed identity provider remains a deployment integration choice; the API accepts
tokens only from the explicitly configured issuer/key, with no default credentials.
RSA key rotation currently requires changing configured key and restarting the API.

## Verification and scope

CI provisions real PostgreSQL 17 and tests migrations, database constraints,
two-tenant paging, revoked membership, forged/expired/wrong-audience tokens,
error schemas and unavailable-database behavior. Liveness is not readiness.
Tests use isolated temporary schemas and synthetic data.

This accepts the Sprint 1 implementation architecture, not production release.
TLS termination, provider credentials, key rotation automation, monitoring,
backup restore drills and production provisioning remain deployment gates.

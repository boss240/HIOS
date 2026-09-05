# PostgreSQL Migration Baseline

Related issue: #8  
Source: HEDS-005 Data Model Specification

## Purpose

This document defines the executable PostgreSQL 17 migration baseline.

## Current status

Run python -m app.migrate with migration-role DATABASE_URL. The psycopg runner
applies ordered SQL files transactionally, serializes runners with an advisory lock,
and verifies applied checksums. 0001_foundation.sql creates tenant, membership,
plant and the tenant/plant index. See [ADR-0001](../architecture/adr/0001-sprint-1-runtime.md).

## Operating policy

- PostgreSQL 17; psycopg SQL runner.
- NNNN_topic.sql, immutable after application.
- Forward corrective migration; verified backup restore for destructive rollback.
- PR review and Runtime integration tests required.
- Promote local/CI to staging before production; use a separate migration role.

## Baseline rules

- Every schema change must be reviewed through pull request.
- Migration files must be deterministic and traceable to an issue.
- Production-impacting migrations must include rollback or recovery notes.
- Data backfills must include QA evidence requirements.

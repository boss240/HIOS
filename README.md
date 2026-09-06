# HIOS Implementation Repository

This repository is the implementation workspace for HIOS by VH | henzitskyi.energy, based on the completed HEDS documentation suite.

## Phase 1 status

Implementation Phase 1 is active. Sprint 1 is closed in GitHub. [Sprint 2](sprint-02/README.md)
starts the Forecasting MVP under #10 (EPIC-005), with [ML contracts](docs/ml/README.md),
[source traceability](sprint-02/SOURCES.md) and [acceptance gates](sprint-02/ACCEPTANCE.md).
Forecasting runtime and accuracy acceptance remain pending.

Primary tracking objects:

- GitHub Project: HIOS Implementation Phase 1
- Current epic: #10 — EPIC-005 Forecasting foundation
- Current sprint: [#22 — SPRINT-02](https://github.com/boss240/HIOS/issues/22)
- Previous sprint issue: #19 — SPRINT-01 (closed)
- Acceptance issue: #18 — Technical acceptance checklist
- Sprint execution plan: `sprint-01/SPRINT_01_EXECUTION_PLAN.md`

## Source documentation

Primary handover anchors:

- HEDS-021 — Product Roadmap and Release Plan
- HEDS-022 — Contractor Implementation Plan
- HEDS-023 — Technical Acceptance and Handover Manual
- HEDS-030 — Final Master Handover Package

## Repository structure

- `/docs/heds-register` — HEDS documentation manifest and references
- `/docs/architecture` — architecture skeleton, context map, and ADR template
- `/docs/api` — implemented Sprint 1 OpenAPI contract and API foundation notes
- `/docs/ml` — forecasting methodology, provider contracts, evaluation and operations
- `/sprint-02` — Forecasting MVP plan, source evidence, status and acceptance
- `/docs/data` — data model conventions and data quality baseline
- `/backlog/issues` — contractor backlog seed files
- `/milestones` — milestone definitions
- `/project-board` — implementation board seed
- `/acceptance` — acceptance checklist
- `/sprint-01` — first sprint scope: project setup, architecture skeleton, API/data foundations

## Contribution baseline

See `CONTRIBUTING.md` and `docs/branching.md` for the Phase 1 working model.

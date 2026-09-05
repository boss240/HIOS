# Acceptance Gates

Related issue: #16 and #18
Source: HEDS-018 QA and Test Strategy and HEDS-023 Technical Acceptance and Handover Manual

## Purpose

This file defines the implementation acceptance gates used to start and control Sprint 1. It complements `docs/qa/release-gates.md` with issue, board, repository, and handover evidence checks.

## Gate 1: Repository Baseline

- [ ] Required repository folders exist.
- [ ] `README.md` and `CONTRIBUTING.md` describe the implementation workspace.
- [ ] Branching and contribution rules are documented.
- [ ] CI placeholder workflow is present.

## Gate 2: Project Board Readiness

- [ ] `HIOS Implementation Phase 1` Project exists.
- [ ] EPIC-001 through EPIC-012 are present on the board.
- [ ] Acceptance Checklist and SPRINT-01 are present on the board.
- [ ] Board statuses reflect the active Sprint 1 operating view.

## Gate 3: Architecture Foundation

- [ ] ADR template exists.
- [ ] System context is documented.
- [ ] Service boundaries are documented.
- [ ] Environment and deployment assumptions are visible.

## Gate 4: API and Data Foundation

- [ ] OpenAPI placeholder exists and is reviewable.
- [ ] OpenAPI validation and contract example checks pass for the reviewed commit.
- [ ] Runtime tests prove authentication, tenant filtering and pagination before endpoint acceptance.
- [ ] Data model baseline exists.
- [ ] Schema conventions are documented.
- [ ] Data quality checklist is documented.

## Gate 5: QA and Handover Evidence

- [ ] Release gates are documented.
- [ ] Evidence requirements are documented.
- [ ] Acceptance issue tracks the final decision.
- [ ] Open risks and decisions are recorded before handover.

## Sprint 1 Operating Status

These checklists define gates, not evidence that they have passed. The historical
documentation-baseline acceptance in #18 does not accept executable Sprint 1
delivery. Record reviewer, date, commit, CI run, open decisions and explicit
acceptance outcome in #18 before closing #19. See [current evidence](../../sprint-01/STATUS.md).

- In Progress: EPIC-001, SPRINT-01
- Ready: EPIC-002, EPIC-003, EPIC-004, EPIC-011
- QA: Acceptance Checklist
- Backlog: EPIC-005, EPIC-006, EPIC-007, EPIC-008, EPIC-009, EPIC-010, EPIC-012

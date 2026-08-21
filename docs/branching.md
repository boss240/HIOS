# Branch Strategy

Related issue: #5  
Source: HEDS-022 Contractor Implementation Plan

## Purpose

This strategy keeps Phase 1 implementation work traceable, reviewable, and easy to hand over.

## Branches

- `main`: stable implementation baseline and accepted documentation.
- `feature/*`: new implementation or documentation scope tied to an issue.
- `fix/*`: corrections to existing implementation or documentation.
- `docs/*`: documentation-only updates.

## Naming convention

Use the issue or epic id in each branch name:

- `feature/epic-001-repo-baseline`
- `feature/epic-002-architecture-skeleton`
- `feature/epic-003-api-foundation`
- `docs/acceptance-checklist-refresh`

## Merge policy

- Work should be reviewed through pull requests.
- Pull requests should reference their issue number.
- Merge only after checklist review and CI placeholder success.
- Keep commits focused on one issue or tightly related issue set.

## Release tags

Phase tags should use the following pattern:

- `phase-1-foundation-v0.1`
- `phase-1-foundation-v0.2`

Final release tagging should wait for acceptance review.

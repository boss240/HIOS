# Contributing to HIOS

This repository is the implementation workspace for HIOS Phase 1.

## Working model

- Use GitHub Issues as the source of planned work.
- Use the HIOS Implementation Phase 1 Project board for status tracking.
- Link every implementation change to at least one issue, epic, or acceptance item.
- Keep source references to HEDS documents in implementation notes.

## Branch naming

Use short, issue-linked branch names:

- `feature/epic-001-repo-baseline`
- `feature/epic-002-architecture-skeleton`
- `feature/epic-003-api-foundation`
- `fix/<issue-id>-<short-topic>`
- `docs/<issue-id>-<short-topic>`

## Pull request checklist

Before requesting review:

- [ ] The PR links the relevant GitHub issue.
- [ ] Documentation changes are included for visible behavior or process changes.
- [ ] Acceptance criteria are copied or referenced in the PR body.
- [ ] CI placeholder checks pass when available.
- [ ] Any open assumptions are listed clearly.

## Documentation rule

Implementation documents should prefer short, traceable files over long unstructured notes. Each document should identify the related HEDS source when applicable.

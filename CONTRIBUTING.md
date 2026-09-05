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

## Sprint 1 execution and validation

Start contractor work from current `main` on `feature/<issue-id>-<topic>`;
the first continuation branch is `feature/19-sprint-1-contract-baseline`.
Submit a PR with evidence and open decisions; do not close the sprint just because files exist.

Use Python 3.11 in a virtual environment, then run:

```sh
python -m pip install -r requirements-ci.txt
python -m openapi_spec_validator docs/api/openapi.yaml
python scripts/check_api_contract.py
```

Both `Documentation baseline` and `Sprint 1 baseline files` must pass before merge.
The latter also validates the API specification and contract examples.
These checks do not certify a running service or tenant isolation implementation.
Branch protection is enabled. See [review policy](docs/qa/review-policy.md) for
required checks, one approval and the explicit sole-owner administrator exception.
Runtime changes must also pass the Runtime integration check.

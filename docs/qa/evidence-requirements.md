# QA Evidence Requirements

Related issue: #16  
Source: HEDS-018 QA and Test Strategy and HEDS-023 Technical Acceptance and Handover Manual

## Purpose

This document defines what evidence must exist before a HIOS release or sprint outcome can be accepted.

## Evidence categories

| Category | Required evidence |
| --- | --- |
| Scope traceability | GitHub issue links, completed checklists, and project status. |
| Documentation | Updated README, architecture/API/data/QA docs, and source references. |
| API contract | OpenAPI file, versioning notes, error model, and auth-boundary notes. |
| Data foundation | Schema conventions, migration placeholder, ownership map, quality checklist. |
| Security assumptions | Auth boundary, sensitive-action/audit requirements, tenant isolation notes. |
| Operations | CI status, environment assumptions, deployment view, known open decisions. |
| Acceptance | Acceptance checklist review and decision state. |

## Minimum release evidence

- [ ] Relevant issues are closed or explicitly carried forward.
- [ ] Project Board status matches issue status.
- [ ] CI placeholder passes on `main`.
- [ ] Open risks are documented in issue or release notes.
- [ ] Acceptance issue is reviewed before release decision.

## Evidence storage

Evidence should be stored in GitHub Issues, repository documentation, pull request history, or release notes. External evidence must be linked from the relevant issue.

# API Versioning Model

Related issue: #7  
Source: HEDS-004 API Specification

## Baseline

HIOS API contracts should be versioned explicitly. Sprint 1 starts with OpenAPI version `0.1.0` and no production compatibility guarantee.

## Versioning rules

- Use semantic versioning for the OpenAPI contract document.
- Breaking contract changes require a major version bump once production consumers exist.
- Non-breaking endpoint additions require a minor version bump.
- Documentation-only clarifications require a patch version bump.

## URL strategy

The final URL strategy is not selected yet. Candidate approaches:

- Path versioning: `/v1/plants`
- Header versioning: `Accept: application/vnd.hios.v1+json`

Sprint 1 keeps paths unversioned in the placeholder until the product API boundary is confirmed.

## Compatibility expectations

- API changes must be traceable to GitHub issues.
- Consumer-impacting changes should include migration notes.
- OpenAPI updates should be reviewed with implementation changes.

# Contract Validation Baseline

Related issue: #7  
Source: HEDS-004 API Specification and HEDS-018 QA and Test Strategy

## Purpose

Sprint 1 validates the OpenAPI document and documented examples before review.
This is static contract validation; server/client integration tests remain pending.

## Implemented checks

- OpenAPI document parses successfully.
- Required endpoints have response schemas.
- Error responses follow the standard error model.
- Authentication-protected endpoints declare security requirements.
- Contract examples remain valid against schemas.

## Tooling and local execution

Use Python 3.11 and the pinned direct dependencies in `requirements-ci.txt`:

```sh
python -m pip install -r requirements-ci.txt
python -m openapi_spec_validator docs/api/openapi.yaml
python scripts/check_api_contract.py
```

The [OpenAPI validator](https://openapi-spec-validator.readthedocs.io/en/latest/)
checks specification structure and references. The repository script validates
all six response examples, empty lists, pagination constraints, authentication
declarations, and rejection of negative capacity or leaked tenant fields.

## CI integration

`ci-placeholder.yml` runs these commands in `Sprint 1 baseline files`, after
checking that all eight required files are nonempty. `ci.yml` retains the broader
documentation-presence check. Neither job proves runtime auth, tenant isolation,
response correctness, availability or forecasting quality.

## Required next tests

- Exercise a running service against these responses and error codes.
- Prove tenant filtering occurs before pagination using two tenants' fixtures.
- Check missing identity, forbidden tenant context, invalid paging and empty pages.
- Verify returned item count never exceeds the requested limit.
- Add consumer compatibility checks when clients exist.

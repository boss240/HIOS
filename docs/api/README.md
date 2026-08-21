# API Foundation

Related issue: #7  
Source: HEDS-004 API Specification

## Purpose

This folder contains the initial API contract baseline for HIOS Phase 1.

## Current files

- `openapi.yaml`: placeholder OpenAPI 3.1 contract.

## Initial API principles

- Keep external contracts versioned and reviewable.
- Treat authentication and tenant isolation as explicit API boundaries.
- Link endpoint additions to GitHub Issues and acceptance criteria.
- Use contract testing once implementation services exist.

## Open items

- Confirm production API hostname.
- Confirm authentication model.
- Expand plant, forecast, user, admin, and billing endpoints.
- Add error model and pagination conventions.

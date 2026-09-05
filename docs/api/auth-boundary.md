# API Auth Boundary

Related issue: #7  
Source: HEDS-004 API Specification and HEDS-006 Security Architecture

## Purpose

This document defines the initial authentication and authorization boundary for HIOS API planning.

## Boundary principles

- Every tenant-scoped API request must resolve tenant context.
- User identity must be available to authorization and audit logic.
- Administrative actions must be distinguishable from customer-facing actions.
- Forecast and plant data access must be tenant-restricted.
- Sensitive provider credentials must never be exposed through API responses.

## Initial role categories

| Role category | Typical capabilities |
| --- | --- |
| Customer user | View assigned plants, forecasts, and alerts. |
| Customer admin | Manage customer-side users and settings where allowed. |
| Support operator | Diagnose tenant issues with controlled access. |
| System admin | Manage platform-level configuration and sensitive operations. |

## API requirements

- Protected endpoints must declare security requirements in OpenAPI.
- Authorization failures should return the standard error model.
- Audit-relevant actions must include actor, tenant, action, target, timestamp, and result.
- Token transport is RS256 JWT under ADR-0001.

## Deployment integration decisions

- Identity provider.
- Identity-system integration and automated key rotation.
- Additional membership administration workflows.
- Fine-grained permission model.

## Sprint 1 implementation

OpenAPI declares RS256 JWT authentication for `/plants` and public liveness for
`/health`. Required signed claims are exp, iat, iss, aud and sub. A signed tenant_id
and active PostgreSQL membership resolve one authorized tenant. Client selectors
cannot override it. Missing/invalid identity returns 401; unresolved or forbidden
tenant context returns 403. See [runtime setup](runtime.md) and ADR-0001.

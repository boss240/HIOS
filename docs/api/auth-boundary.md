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
- Token/session mechanism remains an implementation decision.

## Open decisions

- Identity provider.
- Token/session model.
- Tenant membership data model.
- Fine-grained permission model.

## Sprint 1 contract proposal

OpenAPI 0.2.0 declares HTTP bearer authentication for `/plants` and explicitly
public liveness for `/health`. Bearer is a transport proposal, not a selected
identity provider or token format. Resolve one authorized tenant from trusted
authentication/membership context; do not trust a client tenant selector without
membership checks. Missing/invalid identity returns 401; unresolved or forbidden
tenant context returns 403. Runtime enforcement remains pending implementation.

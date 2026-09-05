# Service Boundary Map

Related issue: #6  
Source: HEDS-003 System Architecture Document

## Purpose

This document defines the initial service boundaries for HIOS Phase 1. It is a working baseline for implementation planning and contractor handover.

## Boundary map

| Boundary | Owns | Does not own | Initial dependencies |
| --- | --- | --- | --- |
| Identity and access | Users, roles, tenant access, auth assumptions | Billing entitlement logic | Admin/backoffice, API boundary |
| Plant registry | Solar plant metadata, customer plant ownership, plant status | Forecast generation | Data boundary, API boundary |
| Forecasting | Forecast jobs, model/version references, forecast outputs | User management, billing | Weather input, plant registry, data boundary |
| Weather integration | Provider configuration, source metadata, ingestion assumptions | Forecast interpretation | Forecasting boundary, operations boundary |
| API boundary | Public/internal contracts, versioning, error model | Business implementation details | Identity, plant, forecast, admin boundaries |
| Customer portal | User-facing dashboard and forecast views | Core business persistence | API boundary, identity boundary |
| Admin/backoffice | Tenant operations, user support, sensitive actions | Customer-facing forecast UX | Identity, audit, billing boundaries |
| Billing and entitlements | Subscription states, access entitlements, commercial operations | Forecast computation | Identity, admin, API boundary |
| Observability and operations | Logging, metrics, alerting, runbook hooks | Product feature ownership | All runtime boundaries |
| Security and compliance | Control mapping, audit evidence, privacy assumptions | Feature delivery ownership | Identity, operations, data boundary |

## Integration rules

- Cross-boundary communication should happen through explicit APIs, events, or documented data contracts.
- Tenant context must be preserved across all tenant-scoped boundaries.
- Forecasting outputs must remain traceable to source weather input and model/version metadata.
- Sensitive admin actions must create audit evidence.

## First API slice

| Contract | Boundary behavior | Required implementation evidence |
| --- | --- | --- |
| `GET /health` | API liveness, public, no dependency or secret details | Running-process response test |
| `GET /plants` | Identity resolves tenant; registry filters before pagination | Cross-tenant denial and pagination tests |
| Standard errors | API returns safe code, message and requestId | Invalid input, unauthenticated and forbidden cases |

The contract uses RS256 JWT with configured issuer/audience/public key. Missing/invalid identity yields 401; unresolved or forbidden tenant
context yields 403. Database access must remain inside the owning boundary.
CI also runs real PostgreSQL integration tests including two-tenant access and paging.

## Remaining decisions

- Sprint 1 uses the modular monolith in ADR-0001; later worker separation remains.
- Message/event infrastructure, if any.
- Later write endpoints and database RLS hardening; this slice uses application isolation.
- External provider retry and degraded-mode strategy.

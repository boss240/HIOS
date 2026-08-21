# Initial Deployment View

Related issue: #6  
Source: HEDS-003 System Architecture Document and HEDS-007 DevOps and Deployment Architecture

## Purpose

This document defines the first deployable-system view for HIOS Phase 1. It is technology-neutral until the runtime stack is selected.

## Logical deployment units

| Unit | Responsibility | Notes |
| --- | --- | --- |
| Web application | Customer portal and user-facing screens | Consumes HIOS API. |
| Admin application | Backoffice and support operations | May be separate app or role-gated area. |
| API application | HTTP API, auth boundary, service orchestration | Owns external API contract. |
| Worker runtime | Forecast jobs, provider ingestion, scheduled tasks | Required for forecasting and operations. |
| Database | Tenant, user, plant, forecast, audit data | Engine not selected yet. |
| Object/file storage | Exported reports, evidence, artifacts | Optional, pending product scope. |
| Observability stack | Logs, metrics, traces, alerts | Tooling not selected yet. |

## Network assumptions

- Public traffic should enter through a controlled API/web edge.
- Admin access should be role-restricted and auditable.
- Provider integrations should use outbound service credentials stored outside the repository.
- Production database access should not be public.

## Promotion path

1. Local validation.
2. Development integration.
3. Staging acceptance.
4. Production release after QA and acceptance review.

## Open decisions

- Cloud provider and deployment target.
- Runtime packaging model.
- Database engine.
- Secret management.
- Observability tooling.

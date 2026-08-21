# HIOS Architecture Skeleton

Related issue: #6  
Source: HEDS-003 System Architecture Document

## Purpose

This folder captures the first implementation-level architecture baseline for HIOS Phase 1. It is intentionally lightweight until implementation details are confirmed.

## Initial architecture areas

- System context and external actors
- Core service boundaries
- Data and forecasting boundaries
- Operational and observability boundaries
- Security and access-control boundaries
- Deployment and environment assumptions

## Core service candidates

| Service area | Responsibility | Phase 1 status |
| --- | --- | --- |
| Identity and access | Authentication, authorization, tenant/user access | Skeleton |
| Plant registry | Solar plant metadata and ownership context | Skeleton |
| Forecasting | Weather ingestion, feature pipeline, forecast generation | Planned |
| API gateway | Public/internal API contract boundary | Skeleton |
| Customer portal | Web user experience | Planned |
| Admin/backoffice | Tenant, support, and operational administration | Planned |
| Observability | Logs, metrics, alerting, operational evidence | Planned |

## Decision records

Use `docs/architecture/adr/0000-template.md` for architecture decisions. Number accepted ADRs sequentially.

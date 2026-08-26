# Data Model Baseline

Related issue: #8
Source: HEDS-005 Data Model Specification and HEDS-009 Data Operations and Data Quality Manual

## Purpose

This file is the Sprint 1 baseline for the HIOS implementation data model. It defines the first domain entities, ownership boundaries, and review gates before a database engine or migration tool is selected.

## Core Entities

| Entity | Initial responsibility | Key relationships | Phase 1 status |
| --- | --- | --- | --- |
| Tenant | Customer account boundary, commercial ownership, and isolation scope | Owns users, plants, subscriptions, settings | Skeleton |
| User | Person identity, role assignment, and access context | Belongs to tenant; produces audit events | Skeleton |
| Role | Permission grouping for customer, admin, and support workflows | Assigned to users; checked by API boundary | Skeleton |
| Plant | Solar PV asset metadata and operational identity | Belongs to tenant; receives forecasts | Skeleton |
| Forecast | Predicted generation output, horizon, confidence, and quality metadata | Belongs to plant; references model version and weather input | Skeleton |
| Weather input | External weather observation or forecast payload used by forecasting | Feeds forecast jobs; records provider/source metadata | Planned |
| Model version | Forecasting model/version metadata and release evidence | Referenced by forecasts and QA checks | Planned |
| Subscription | Commercial plan, billing state, and entitlement context | Belongs to tenant; controls feature access | Planned |
| Audit event | Security, admin, and operational evidence | Linked to user, tenant, and affected resource | Planned |

## Baseline Rules

- Every tenant-scoped record must include a tenant boundary or an explicit reason it is global.
- Forecast records must remain traceable to plant, weather input, model version, and generation timestamp.
- Sensitive admin and billing changes must produce audit evidence.
- Public API payloads must not expose internal persistence identifiers unless intentionally documented.
- Data quality checks must cover required fields, timestamp consistency, tenant isolation, and forecast traceability.

## Open Decisions

- Database engine and migration framework.
- Canonical unit conventions for plant capacity and forecast generation.
- Retention periods for weather inputs, forecast outputs, and audit events.
- Tenant isolation enforcement model.
- Model registry implementation.

## Sprint 1 Acceptance

- Data domains are documented.
- API/data dependencies are visible.
- Open decisions are listed for contractor follow-up.
- Data quality checklist and ownership map are present.

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

## Plant API mapping (Sprint 1 implementation)

| Public field | Conceptual storage | Constraint |
| --- | --- | --- |
| `id` | Stable public plant identifier | Nonempty opaque string; not a database row number |
| `name` | Plant display name | Nonempty string |
| `capacityKw` | Optional installed capacity | Nonnegative number, kW; omitted when unknown |
| Not exposed | `tenant_id` | Required ownership boundary for every plant |

`capacityKw` retains the existing API field and unit. Capacity means installed DC nameplate kW (kWp); do not mix AC inverter ratings.
Forecast power/energy units remain for the forecasting epic.
List queries filter by authorized tenant before pagination and order by stable
public plant ID. Offset pagination does not promise a snapshot during concurrent
writes. Enforce unique public IDs and tenant-safe relationships when selecting
the database. Tenant selection is never inferred from a supplied plant ID alone.

## Remaining decisions

- PostgreSQL 17 and versioned SQL migrations selected in ADR-0001.
- Plant capacity is DC nameplate kW; forecast unit conventions remain with #10.
- Retention defaults are in [retention policy](retention-policy.md).
- Signed tenant claim plus active membership and tenant-filtered SQL; see ADR-0001.
- Model registry implementation.

## Sprint 1 Acceptance

- Data domains are documented.
- API/data dependencies are visible.
- Open decisions are listed for contractor follow-up.
- Data quality checklist and ownership map are present.

# System Context Map

Related issue: #6  
Source: HEDS-003 System Architecture Document

## External actors

| Actor | Interaction with HIOS |
| --- | --- |
| Customer operator | Reviews solar plant forecasts, alerts, and operational views. |
| Administrator | Manages tenants, users, settings, and support workflows. |
| Weather provider | Supplies external weather inputs for forecasting. |
| Billing provider | Supports subscription, entitlement, and commercial operations. |
| Monitoring operator | Reviews system health, logs, alerts, and evidence. |

## Internal boundaries

| Boundary | Initial responsibility |
| --- | --- |
| API boundary | Stable contracts for web, mobile, admin, and integrations. |
| Data boundary | Plant, forecast, tenant, and operational data ownership. |
| Forecasting boundary | Model registry, feature pipeline, forecast execution, quality checks. |
| Security boundary | Access control, audit requirements, privacy and compliance hooks. |
| Operations boundary | Observability, incident response, backup, and continuity hooks. |

## Open assumptions

- Exact cloud deployment topology is not confirmed in Sprint 1.
- Weather provider selection remains an implementation dependency.
- Billing and entitlement enforcement are planned after API/data foundations.
- Forecast model quality gates must be tied to QA acceptance criteria.

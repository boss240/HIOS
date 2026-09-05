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

## Sprint 1 request and data flow

1. A client calls the API boundary; public `/health` reports liveness only.
2. `/plants` authenticates the caller and resolves one authorized tenant context.
3. The plant registry applies tenant scope before reading data and returns only
   documented public fields. An untrusted tenant selector cannot grant access.
4. Weather integration supplies provenance-tagged inputs to forecasting; outputs
   retain plant, weather source and model-version references.
5. Operations receives safe correlation metadata; secrets and provider payloads
   are excluded from public errors and liveness responses.

These are logical boundaries, not deployed services. See
[service boundaries](service-boundaries.md), [environment map](environment-map.md)
and [deployment view](deployment-view.md). The bearer-token contract is a proposal;
identity provider, tenant selection and deployment packaging still require review.

## Outstanding assumptions

- Exact cloud deployment topology is not confirmed in Sprint 1.
- Weather provider selection remains an implementation dependency.
- Billing and entitlement enforcement are planned after API/data foundations.
- Forecast model quality gates must be tied to QA acceptance criteria.

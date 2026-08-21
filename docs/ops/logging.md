# Logging Baseline

Related issue: #15

## Required log context

| Field | Purpose |
| --- | --- |
| timestamp | UTC event time. |
| level | debug, info, warning, error. |
| service | Emitting service or component. |
| environment | Local, development, staging, production. |
| request_id | Request traceability. |
| tenant_id | Tenant context where safe and applicable. |
| actor_id | User/system actor where safe and applicable. |
| event | Stable event name. |
| message | Safe human-readable summary. |

## Rules

- Do not log secrets or raw credentials.
- Do not expose sensitive tenant data in logs.
- Sensitive admin actions must connect to audit evidence.
- Forecast/provider failures must include provider context and freshness metadata where safe.

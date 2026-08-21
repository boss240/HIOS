# Support Diagnostics

Related issue: #13

## Purpose

Support diagnostics help authorized operators investigate tenant or plant issues without bypassing security and audit controls.

## Diagnostic areas

| Area | Examples |
| --- | --- |
| Tenant | Status, settings summary, entitlement profile. |
| Plant | Plant status, latest forecast, provider status. |
| Forecasting | Last generation time, model/version, degraded state. |
| Provider | Last successful weather retrieval, errors, delay state. |
| API | Request id lookup and error category where available. |
| Notifications | Delivery intent and alert status where available. |

## Rules

- Diagnostics must respect tenant context.
- Sensitive support access should create audit evidence.
- Raw secrets and private credentials must never be shown.

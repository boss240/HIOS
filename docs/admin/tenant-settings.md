# Tenant Settings Map

Related issue: #13

## Tenant settings categories

| Category | Examples |
| --- | --- |
| Identity | Tenant name, status, primary contact. |
| Access | Allowed roles, user limits, support access rules. |
| Forecasting | Default horizon, forecast freshness threshold, provider configuration reference. |
| Notifications | Alert categories, delivery channels, escalation preferences. |
| Billing | Subscription state, entitlement profile, billing account reference. |
| Compliance | Audit retention, privacy/legal references, evidence requirements. |

## Rules

- Tenant settings changes must be auditable.
- Sensitive tenant changes should require elevated permission.
- Billing-related settings must align with entitlement logic.
- Forecasting/provider settings must preserve traceability to source assumptions.

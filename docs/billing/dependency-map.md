# Billing Dependency Map

Related issue: #14

## Dependencies

| Dependency | Why it matters |
| --- | --- |
| Identity and access | Entitlements are evaluated against users, roles, and tenants. |
| Admin/backoffice | Operators need subscription and override workflows. |
| API boundary | Access enforcement must happen server-side. |
| Frontend/mobile | Navigation and feature visibility depend on entitlement state. |
| Audit/security | Billing overrides and sensitive changes require evidence. |
| Data model | Subscription and entitlement state must be persisted and traceable. |

## Cross-boundary rules

- Billing state should not be inferred only from UI.
- Entitlement decisions must include tenant/account context.
- Admin overrides must create audit events.
- Support diagnostics should show entitlement reason where safe.

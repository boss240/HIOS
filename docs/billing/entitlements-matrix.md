# Entitlements Matrix

Related issue: #14

## Initial entitlements

| Entitlement | Description | Candidate enforcement point |
| --- | --- | --- |
| `plants.view` | View assigned plant list and detail. | API + frontend navigation. |
| `forecasts.view` | View forecast chart/table data. | API + frontend navigation. |
| `alerts.view` | View alert/degraded states. | API + mobile/web UI. |
| `notifications.manage` | Manage notification settings. | API + mobile/web UI. |
| `admin.tenant.manage` | Manage tenant settings. | API + admin/backoffice. |
| `admin.users.manage` | Invite, disable, change roles. | API + admin/backoffice. |
| `billing.manage` | Manage subscription/entitlement state. | API + admin/backoffice. |
| `diagnostics.view` | View support diagnostics. | API + admin/backoffice. |

## Enforcement principles

- UI visibility is not enforcement.
- API authorization must enforce entitlements.
- Tenant context must be part of every tenant-scoped entitlement decision.
- Overrides must be auditable.

## Open decisions

- Plan packaging.
- Trial behavior.
- Billing provider integration.
- Entitlement cache strategy.

# Subscription Model Draft

Related issue: #14

## Subscription entities

| Entity | Purpose |
| --- | --- |
| Account | Commercial customer/account boundary. |
| Subscription | Active commercial plan and lifecycle state. |
| Plan | Packaged capabilities and limits. |
| Entitlement profile | Access rights derived from subscription/plan. |
| Billing event | Commercial event such as activation, renewal, suspension, cancellation. |

## Subscription states

- Trial
- Active
- Past due
- Suspended
- Cancelled
- Expired

## Rules

- Subscription state must be traceable to account/tenant.
- Entitlement changes should be auditable.
- Billing provider events must be normalized before changing access.
- Manual overrides must be visible in admin/backoffice audit evidence.

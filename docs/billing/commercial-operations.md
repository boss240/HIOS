# Commercial Operations Notes

Related issue: #14

## Commercial workflows

| Workflow | Notes |
| --- | --- |
| Account activation | Creates or links tenant/account commercial state. |
| Plan change | Updates subscription and entitlement profile. |
| Suspension | Restricts selected entitlements while preserving audit trail. |
| Cancellation | Ends subscription according to policy. |
| Manual override | Requires elevated permission and audit evidence. |

## Operational requirements

- Billing events must be traceable.
- Entitlement changes must be auditable.
- Customer-facing access changes should be explainable by subscription state.
- Support/admin views should show current subscription and entitlement state.

## Open decisions

- Payment provider.
- Invoice lifecycle.
- Grace period rules.
- Dunning and reactivation policy.

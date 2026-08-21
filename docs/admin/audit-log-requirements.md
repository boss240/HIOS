# Audit Log Requirements

Related issue: #13

## Audit event fields

| Field | Purpose |
| --- | --- |
| `event_id` | Stable audit event id. |
| `actor_id` | User or system actor. |
| `tenant_id` | Tenant context where applicable. |
| `action` | Action performed. |
| `target_type` | Entity type affected. |
| `target_id` | Entity id affected. |
| `result` | Success, failure, denied. |
| `timestamp` | UTC event time. |
| `reason` | Optional operator reason. |
| `metadata` | Safe structured context. |

## Audit-worthy actions

- User invite, disable, role change.
- Tenant setting changes.
- Billing entitlement overrides.
- Provider configuration changes.
- Support access to tenant diagnostics.
- Security/compliance setting changes.

## Rules

- Audit records must not expose secrets.
- Sensitive admin actions must be traceable to actor and tenant.
- Failed and denied sensitive actions should be recorded where safe.

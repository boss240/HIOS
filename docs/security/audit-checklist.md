# Audit Checklist

Related issue: #17

## Audit-worthy events

- User invitation, disablement, and role changes.
- Tenant setting updates.
- Billing entitlement changes or overrides.
- Weather provider configuration changes.
- Support access to tenant diagnostics.
- Security/compliance setting changes.
- Release acceptance decisions.

## Required fields

- Actor.
- Tenant/account context where applicable.
- Action.
- Target.
- Timestamp.
- Result.
- Reason/comment where required.

## Rules

- Do not store secrets in audit records.
- Failed/denied sensitive actions should be recorded where safe.
- Audit evidence should be available for acceptance and compliance review.

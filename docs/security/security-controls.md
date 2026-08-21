# Security Controls Map

Related issue: #17

## Control areas

| Area | Baseline control |
| --- | --- |
| Identity | Authenticated access for protected API/UI surfaces. |
| Authorization | Tenant and role-aware access checks. |
| Tenant isolation | Tenant context required for tenant-scoped data. |
| Secrets | Secrets never committed to repository. |
| Audit | Sensitive actions recorded with actor, target, result, timestamp. |
| Data protection | Sensitive data excluded from logs and notifications. |
| Provider integration | External credentials stored outside source code. |
| Operations | Incidents and degraded modes preserve evidence. |

## Open decisions

- Identity provider.
- Permission model.
- Secret-management platform.
- Audit retention policy.
- Compliance reporting format.

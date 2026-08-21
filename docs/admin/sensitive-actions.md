# Sensitive Action Checklist

Related issue: #13

## Sensitive actions

- Change tenant status.
- Change user role or disable user.
- Override billing entitlement.
- Change weather provider configuration.
- Access tenant diagnostics as support/system user.
- Export audit or operational evidence.
- Modify security/compliance settings.

## Checklist

- [ ] Permission check is enforced server-side.
- [ ] Tenant context is explicit.
- [ ] Actor identity is recorded.
- [ ] Action target is recorded.
- [ ] Result is recorded.
- [ ] Reason/comment is captured where required.
- [ ] Secrets and sensitive payloads are not logged.

## Open decisions

- Whether selected actions require two-person approval.
- Retention policy for admin audit events.
- Export format for audit evidence.

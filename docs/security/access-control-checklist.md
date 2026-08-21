# Access Control Checklist

Related issue: #17

## Checklist

- [ ] Protected APIs require authenticated access.
- [ ] Tenant-scoped APIs enforce tenant context.
- [ ] Admin/backoffice actions require elevated permissions.
- [ ] Support diagnostics are tenant-scoped and auditable.
- [ ] Billing entitlement checks happen server-side.
- [ ] Sensitive actions create audit evidence.
- [ ] UI navigation does not replace API authorization.
- [ ] Error messages avoid sensitive data leakage.

## Review notes

This checklist should be reviewed before production release and whenever the auth provider or permission model changes.

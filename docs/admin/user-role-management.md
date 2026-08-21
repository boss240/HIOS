# User and Role Management

Related issue: #13

## Role groups

- Customer user
- Customer admin
- Support operator
- System admin

## Core flows

### Invite user

1. Select tenant.
2. Enter user identity.
3. Choose role.
4. Send invitation.
5. Record audit event.

### Change role

1. Select tenant and user.
2. Review current role.
3. Apply role change.
4. Record actor, target, old role, new role, timestamp, result.

### Disable user

1. Select tenant and user.
2. Confirm disabling action.
3. Revoke access/session where supported.
4. Record audit event.

## Requirements

- Role changes must be auditable.
- Users must remain scoped to tenant context unless explicitly platform-level.
- Support/system roles require stronger audit evidence.

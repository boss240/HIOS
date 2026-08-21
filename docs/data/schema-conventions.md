# Schema Conventions

Related issue: #8

## Naming

- Use singular table/entity names when describing conceptual models.
- Use lower snake case for physical database names unless the selected platform requires otherwise.
- Use stable identifiers named `id` for primary entities.
- Use foreign keys named `<entity>_id`.

## Timestamps

Use UTC timestamps for persisted system events:

- `created_at`
- `updated_at`
- `deleted_at` for soft deletion when needed
- `observed_at` for external measurements
- `forecasted_at` for forecast generation time
- `valid_from` and `valid_to` for time-bound forecast periods

## Tenant isolation

Every tenant-scoped entity must include an explicit tenant boundary. The final implementation may enforce this through schema design, access policy, or both.

## Forecast metadata

Forecast records should preserve:

- input weather source reference
- forecast horizon
- generation timestamp
- model/version reference
- quality or confidence metadata when available

## Migration policy

Migration tooling is not selected yet. Until selected, schema changes must be documented here or in an ADR.

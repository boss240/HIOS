# Data Quality Checklist

Related issue: #8  
Source: HEDS-009 Data Operations and Data Quality Manual

## Required checks

- [ ] Tenant-scoped records have a tenant boundary.
- [ ] Solar plant metadata includes required identity fields.
- [ ] Forecast records include generation and validity timestamps.
- [ ] Weather-provider inputs preserve source metadata.
- [ ] Missing or delayed source data has a documented degraded-mode behavior.
- [ ] Operational data changes are auditable where required.

## Forecast quality checks

- [ ] Forecast horizon is explicit.
- [ ] Model or method version is traceable.
- [ ] Source weather provider is traceable.
- [ ] Outlier and missing-data handling are documented.
- [ ] QA evidence can be produced before release acceptance.

## Open decisions

- PostgreSQL 17 and SQL migration runner selected (ADR-0001).
- Engineering retention defaults selected in retention-policy.md.
- Data export and audit evidence format.

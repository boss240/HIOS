# Engineering retention policy

Decision: ADR-0001, 2026-09-05. Related issues: #8, #17, #19.

| Data | Default duration | Clock |
| --- | --- | --- |
| Raw weather inputs | 90 days | Ingested at UTC |
| Forecast outputs and provenance | 730 days | Generated at UTC |
| Security/admin audit events | 365 days | Occurred at UTC |
| Operational logs | 30 days | Emitted at UTC |
| Backups | 35 days | Backup completion UTC |
| Plants and memberships | Account/asset lifecycle | Explicit authorized deletion process |

Before forecast ingestion, retain normalized input snapshots and model/version
references needed to reproduce each retained forecast; raw-provider expiry must
not leave retained forecasts without provenance. Provider licensing constraints
must be checked before real ingestion. Never run purge on records under an
authorized hold. Expiration alone is not permission to delete held data.

Implement domain-specific purge jobs when those domains exist. Require a dry-run
count, tenant scope, bounded batches, recorded outcome and recovery procedure.
Policies apply to storage and exports; backup expiry follows its separate window.
Deleting a live record does not instantly erase an existing backup.

Sprint 1 creates only tenants, memberships and plants and performs no automated
deletion. These engineering defaults do not establish legal or contractual
compliance; production policy must incorporate applicable customer/provider terms.

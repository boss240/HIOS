# Sprint 2 / Forecasting MVP package

Related issues: #10 (EPIC-005), [#22](https://github.com/boss240/HIOS/issues/22).

This is the repository equivalent of the requested Sprint 2 package. It reuses
the existing specifications rather than replacing them with an earlier ZIP.
The original ZIP bytes are not available in this checkout; byte identity is not claimed.

- [ML documentation](docs/ml/README.md)
- [Implementation plan](sprint-02/README.md)
- [Acceptance checklist](docs/ml/sprint-02-acceptance-checklist.md)
- [Source coverage](sprint-02/SOURCES.md) and [source hashes](sprint-02/source-manifest.json)
- [Delivery history](sprint-02/STATUS.md)
- [Package manifest](SPRINT_02_MANIFEST.json)
- [Forecasting CI](.github/workflows/forecasting-docs-ci.yml)

## Verified baseline and remaining scope

On 2026-09-09, main was `65722236a764ad92245dc8a22e3aa0b7a1bece5b`.
PRs #23 through #37 delivered the documentation foundation and controlled runtime
components, including persistence, MODEL-001, weather normalization/failover,
worker leases/outcomes, operational summaries and deterministic evaluation.
All four Actions checks passed on that main commit. Issues #10 and #22 were open
and In Progress on Project 3. Sprint 1 is not reopened by this package.

Production provider integration, real actuals and archived as-issued weather,
frozen holdout and approved accuracy thresholds, scheduled staging operation,
monitoring, rollback evidence and sign-off remain acceptance dependencies.
The controlled worker is not a production scheduler; fixture metrics are not
field-accuracy evidence. See the canonical acceptance ledger for release gates.

## Verification

Run `python scripts/check_forecasting_docs.py` from the repository root.
It checks all requested package paths, nonempty documents, local links, package
manifest membership and six HEDS source records. It does not verify original ZIP
identity or accept forecasting performance. The manifest lists itself without a
self-referential checksum; source archive checksums remain in the source manifest.

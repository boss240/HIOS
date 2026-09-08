# Sprint 2 acceptance checklist

Related issue: #10 (EPIC-005); sprint tracking: #22.

The authoritative gate states and decision template are maintained in the
[Sprint 2 acceptance ledger](../../sprint-02/ACCEPTANCE.md). This entry point
preserves the requested package path without creating a competing gate ledger.

Review these evidence categories before recording acceptance:

- S2-A01: canonical documentation, source coverage and package manifest.
- S2-A02: successful documentation, API contract and PostgreSQL runtime CI.
- S2-A03: real inputs, provider rights, metadata and archived weather.
- S2-A04: forecast behavior, lineage, isolation and failure tests.
- S2-A05: frozen holdout, preapproved thresholds, coverage and segment metrics.
- S2-A06: operating deadlines, monitoring, restore and rollback evidence.
- S2-A07: handover inventory and named, dated scope-specific sign-off.

Use [forecast validation](forecast-validation.md) for test definitions and
[delivery history](../../sprint-02/STATUS.md) for implementation evidence.
Successful documentation CI does not mark the runtime, accuracy or sign-off
gates accepted. Keep #10 and #22 In Progress while release evidence is pending.

# Sprint 2 acceptance ledger

Related issue: #10. Sources: HEDS-018 acceptance_criteria and qa_gates;
HEDS-022 acceptance_gates; HEDS-023 acceptance_checks and signoff.
[Source coverage](SOURCES.md). No final MVP acceptance is recorded.

## Gate ledger

| Gate | Evidence required | Current state |
| --- | --- | --- |
| S2-A01 Documentation | Nine canonical ML docs, legacy links, six source hashes and reviewable plan | Prepared; PR review pending |
| S2-A02 Repository regression | Documentation, Sprint 1 contract, Runtime integration and Forecasting documentation checks pass on PR | See live PR checks and STATUS |
| S2-A03 Input readiness | Real sample, vendor mapping/rights, effective AC/DC metadata, tenant scope and archived weather | Pending |
| S2-A04 Forecast behavior | S2-T01–11 pass, reproducible model/input lineage and failure handling | Pending |
| S2-A05 Accuracy | Preapproved thresholds, fixed holdout, coverage/exclusions and segment metrics; S2-T12 | Pending |
| S2-A06 Operations | Job deadlines, owner/on-call, monitoring, backup/restore and rollback drills; S2-T13 | Pending |
| S2-A07 Technical handover | Known defects reviewed, artifacts/commands inventory, environment access and scope-specific sign-off | Pending |

HEDS-018 ACCEPTA-001/002 require all critical tests passing and no open Sev1/Sev2
defects for release. CI document checks meet neither forecast-runtime nor accuracy
gates. No release can proceed with unspecified thresholds or missing input evidence.

## Evidence package for a future acceptance decision

Record exact commit and artifact hashes; source/feature/config/model versions;
dataset split and as-issued weather snapshot hashes; unit/integration/security
and historical evaluation results; failed and excluded cases; CI run/artifact URLs;
provider configuration without secrets; staging demo, rollback/restore record,
monitoring evidence, known issues with owners and dates.

Use HEDS-023 document + section + ID when recording acceptance: its
acceptance_checks cover traceability, QA/security/performance, backup/restore,
observability/support/access, rollback and known issues. Its signoff section
separately covers Contractor, Product, Technical, Operations, Security, Final
acceptance and post-handover stabilization. Record actor/date/scope and conditions
for each applicable signature; do not infer signatures from closed issues.

## Decision template

- Candidate commit / artifact: pending.
- Environment / plants / horizons: pending.
- Gate evidence links and exceptions: pending.
- Decision: pending (accepted / accepted with scoped open items / rejected).
- Named accountable reviewer(s), date and scope: pending.
- Deferred requirements and target checkpoint: pending.

Sprint 1 closure remains historical; it does not accept forecasting or a full
production release. Keep #10 open/In Progress until its agreed runtime scope and
evidence have been reviewed.

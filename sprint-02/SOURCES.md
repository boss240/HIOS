# Sprint 2 source evidence and coverage

Related issue: #10. Reviewed 2026-09-06.

The local synced sources directory was empty. The repository manifest points to
HEDS / 00_Ready_Packages. The cleaned master register on Drive supplied direct IDs
for the six archives below. Each ZIP was downloaded, CRC-checked and its primary
releases/md document read. [Source manifest](source-manifest.json) records archive
and primary Markdown SHA-256 hashes, entry names, versions and Drive URLs.
Original archives remain outside this repository; no synced files were edited.

| Source / version | Read sections and anchors | Implementation mapping | Remaining evidence |
| --- | --- | --- | --- |
| HEDS-010 v0.1.0-UA | §§3–12; MLOP, FEAT, MODEL, DEP, MLMON, DRIFT, RET, MLI, AUD-ML | [Registry](../docs/ml/model-registry.md), [pipeline](../docs/ml/feature-pipeline.md), [operations](../docs/ml/ml-operations-checklist.md) | Actual artifacts, monitoring, promotion/rollback drills |
| HEDS-011 v0.1.0-UA | §§3–12; WPROV, APIW, WMAP, NORM, FB, QS, SLA-W, COST-W, WPI | [Providers](../docs/ml/weather-provider-assumptions.md), [failover](../docs/ml/provider-failover.md) | Vendor contracts, adapter tests, TTL/quotas and field mappings |
| HEDS-012 v0.1.0-UA | §§3–11; FH, WIN, PIN, METH, ACC, CONF, LIM, FREP | [Methodology](../docs/ml/forecasting-methodology.md), [metrics](../docs/ml/quality-metrics.md), [validation](../docs/ml/forecast-validation.md) | Real data, calibrated baseline, accuracy targets and holdout results |
| HEDS-018 v0.1.0-UA | test_types, qa_gates, test_environments, acceptance_criteria | [Validation matrix](../docs/ml/forecast-validation.md), [acceptance](ACCEPTANCE.md) | Runtime forecast tests, staging and QA sign-off |
| HEDS-022 v0.1.0-UA | WORKPAC-004/010/012; contractor_roles, acceptance_gates, reporting | [Sprint plan](README.md), [status and decisions](STATUS.md) | Named engineering owners, sprint demo and delivery evidence |
| HEDS-023 v0.1.0-UA | handover_areas, acceptance_checks, handover_artifacts, signoff | [Acceptance ledger](ACCEPTANCE.md) | Operational evidence and scoped signatures |

The source suites list 98/86/76/46/46/48 QA cases respectively. These are source
catalogue counts, not executed tests or claimed Sprint 2 coverage. S2-T01–13
translate the first implementation slice into concrete tests; the complete source
QA suites remain to be reconciled before full HEDS acceptance.

## Source interpretation

HEDS-011 providers are role placeholders; no named vendor is mandated.
HEDS-012 specifies day-ahead 24–48h/hourly, with other horizons separately listed.
It does not prescribe numeric production accuracy limits or physical coefficients.
The hourly origin convention, AC target, MAPE epsilon, bounded retry/circuit
parameters and storage proposal are explicit engineering proposals in this package.

HEDS-018/022/023 repeat identifiers such as ACCEPTA-001 and HANDOVE-001
across documents or sections. Always qualify a requirement by document and section.
Their acceptance/sign-off catalogues are requirements, not completed approvals.
